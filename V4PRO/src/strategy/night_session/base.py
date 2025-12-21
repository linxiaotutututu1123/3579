"""夜盘基础模块 (军规级 v4.0).

V4PRO Platform Component - 夜盘时段配置与管理基础设施
V4 SPEC: M1军规 - 单一信号源, M15军规 - 夜盘跨日处理

本模块提供夜盘交易的核心基础设施:
- NightSessionConfig: 夜盘配置类(时间段、品种过滤)
- NightSessionManager: 夜盘时段管理器
- 时间判断: 判断当前是否为夜盘时段
- 跨日处理: M15军规夜盘跨日处理逻辑
- 国际市场联动: 与外盘时间对齐

军规覆盖:
- M1: 单一信号源 - 配置唯一性保证
- M15: 夜盘跨日处理 - 跨日时段正确归属

示例:
    >>> from src.strategy.night_session.base import NightSessionConfig, NightSessionManager
    >>> config = NightSessionConfig()
    >>> manager = NightSessionManager(config)
    >>> is_night = manager.is_night_session(1703088000.0)
    >>> print(is_night)
    True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Any, ClassVar


class InternationalMarket(Enum):
    """国际市场枚举.

    属性:
        COMEX: 纽约商品交易所 (黄金、白银、铜)
        NYMEX: 纽约商业交易所 (原油、天然气)
        LME: 伦敦金属交易所 (有色金属)
        CME: 芝加哥商业交易所 (农产品、外汇)
        ICE: 洲际交易所 (能源、软商品)
    """

    COMEX = "COMEX"  # 纽约商品交易所
    NYMEX = "NYMEX"  # 纽约商业交易所
    LME = "LME"  # 伦敦金属交易所
    CME = "CME"  # 芝加哥商业交易所
    ICE = "ICE"  # 洲际交易所


class SessionType(Enum):
    """交易时段类型枚举.

    属性:
        DAY: 日盘时段 (09:00-15:00)
        NIGHT: 夜盘时段 (21:00-次日02:30)
        CLOSED: 休市时段
    """

    DAY = "DAY"  # 日盘
    NIGHT = "NIGHT"  # 夜盘
    CLOSED = "CLOSED"  # 休市


@dataclass(frozen=True, slots=True)
class TimeRange:
    """时间范围 (不可变).

    属性:
        start: 开始时间 (HH:MM格式的time对象)
        end: 结束时间 (HH:MM格式的time对象)
        crosses_midnight: 是否跨午夜
    """

    start: time
    end: time
    crosses_midnight: bool = False

    def contains(self, t: time) -> bool:
        """判断时间是否在范围内.

        参数:
            t: 待检查的时间

        返回:
            是否在时间范围内
        """
        if self.crosses_midnight:
            # 跨午夜: 21:00-02:30 -> 判断 t >= 21:00 OR t <= 02:30
            return t >= self.start or t <= self.end
        # 不跨午夜: 09:00-15:00 -> 判断 start <= t <= end
        return self.start <= t <= self.end


@dataclass(frozen=True, slots=True)
class NightSessionConfig:
    """夜盘配置类 (不可变).

    包含夜盘交易的核心配置:
    - 时间段配置: 夜盘开始/结束时间
    - 品种过滤: 支持夜盘交易的品种列表
    - 国际市场联动: 与外盘时间对齐配置

    属性:
        night_start: 夜盘开始时间 (默认21:00)
        night_end: 夜盘结束时间 (默认02:30)
        allowed_symbols: 允许夜盘交易的品种列表
        linked_markets: 联动的国际市场列表
        timezone_offset: 时区偏移(小时, 北京时间为+8)
    """

    VERSION: ClassVar[str] = "1.0.0"

    night_start: time = field(default_factory=lambda: time(21, 0))
    night_end: time = field(default_factory=lambda: time(2, 30))
    allowed_symbols: tuple[str, ...] = field(default_factory=lambda: (
        "AU", "AG", "CU", "AL", "ZN", "PB", "NI", "SN",  # 贵金属/有色
        "RB", "HC", "BU", "RU", "FU", "SC",  # 黑色/能化
    ))
    linked_markets: tuple[InternationalMarket, ...] = field(default_factory=lambda: (
        InternationalMarket.COMEX,
        InternationalMarket.LME,
        InternationalMarket.NYMEX,
    ))
    timezone_offset: int = 8  # 北京时间 UTC+8

    def is_symbol_allowed(self, symbol: str) -> bool:
        """检查品种是否允许夜盘交易.

        参数:
            symbol: 品种代码 (如 AU2312, ag2401)

        返回:
            是否允许夜盘交易
        """
        prefix = "".join(c for c in symbol if c.isalpha()).upper()
        return prefix in self.allowed_symbols

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于序列化).

        返回:
            配置字典
        """
        return {
            "version": self.VERSION,
            "night_start": self.night_start.isoformat(),
            "night_end": self.night_end.isoformat(),
            "allowed_symbols": list(self.allowed_symbols),
            "linked_markets": [m.value for m in self.linked_markets],
            "timezone_offset": self.timezone_offset,
        }


class NightSessionManager:
    """夜盘时段管理器.

    提供夜盘时段判断和跨日处理功能:
    - 时间判断: 判断当前是否为夜盘时段
    - 跨日处理: M15军规夜盘跨日处理逻辑
    - 交易日归属: 夜盘归属下一个交易日
    - 国际市场联动: 与外盘时间对齐

    军规覆盖:
    - M15: 夜盘跨日处理 - 正确归属交易日
    """

    VERSION: ClassVar[str] = "1.0.0"

    def __init__(self, config: NightSessionConfig | None = None) -> None:
        """初始化夜盘时段管理器.

        参数:
            config: 夜盘配置, 为None时使用默认配置
        """
        self._config = config or NightSessionConfig()
        self._night_range = TimeRange(
            start=self._config.night_start,
            end=self._config.night_end,
            crosses_midnight=True,
        )

    @property
    def config(self) -> NightSessionConfig:
        """获取配置."""
        return self._config

    def is_night_session(self, timestamp: float) -> bool:
        """判断是否为夜盘时段.

        参数:
            timestamp: Unix时间戳 (秒)

        返回:
            是否为夜盘时段
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        local_hour = (dt.hour + self._config.timezone_offset) % 24
        local_time = time(local_hour, dt.minute)
        return self._night_range.contains(local_time)

    def get_session_type(self, timestamp: float) -> SessionType:
        """获取交易时段类型.

        参数:
            timestamp: Unix时间戳 (秒)

        返回:
            交易时段类型 (DAY/NIGHT/CLOSED)
        """
        if self.is_night_session(timestamp):
            return SessionType.NIGHT
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        local_hour = (dt.hour + self._config.timezone_offset) % 24
        if 9 <= local_hour < 15:
            return SessionType.DAY
        return SessionType.CLOSED

    def get_trading_date(self, timestamp: float) -> str:
        """获取交易日归属 (M15军规 - 跨日处理).

        夜盘归属规则:
        - 21:00-23:59 归属次日
        - 00:00-02:30 归属当日

        参数:
            timestamp: Unix时间戳 (秒)

        返回:
            交易日 (YYYY-MM-DD格式)
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        local_hour = (dt.hour + self._config.timezone_offset) % 24
        local_dt = datetime.fromtimestamp(
            timestamp + self._config.timezone_offset * 3600, tz=timezone.utc
        )
        # M15军规: 21:00-23:59 夜盘归属次日
        if local_hour >= 21:
            next_day = local_dt + timedelta(days=1)
            return next_day.strftime("%Y-%m-%d")
        return local_dt.strftime("%Y-%m-%d")

    def get_international_market_status(
        self, timestamp: float
    ) -> dict[InternationalMarket, bool]:
        """获取国际市场开盘状态 (用于联动).

        参数:
            timestamp: Unix时间戳 (秒)

        返回:
            各国际市场开盘状态字典
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        utc_hour = dt.hour
        status: dict[InternationalMarket, bool] = {}
        # COMEX/NYMEX: 纽约时间 (UTC-5), 18:00-17:00
        ny_hour = (utc_hour - 5) % 24
        status[InternationalMarket.COMEX] = not (17 <= ny_hour < 18)
        status[InternationalMarket.NYMEX] = not (17 <= ny_hour < 18)
        # LME: 伦敦时间 (UTC+0), 01:00-19:00
        status[InternationalMarket.LME] = 1 <= utc_hour < 19
        # CME: 芝加哥时间 (UTC-6), 17:00-16:00
        cme_hour = (utc_hour - 6) % 24
        status[InternationalMarket.CME] = not (16 <= cme_hour < 17)
        # ICE: 纽约时间, 20:00-18:00
        status[InternationalMarket.ICE] = not (18 <= ny_hour < 20)
        return status

    def is_aligned_with_international(self, timestamp: float) -> bool:
        """检查是否与国际市场时间对齐.

        当联动的国际市场有任一开盘时，认为时间对齐。

        参数:
            timestamp: Unix时间戳 (秒)

        返回:
            是否与国际市场对齐
        """
        status = self.get_international_market_status(timestamp)
        return any(status.get(m, False) for m in self._config.linked_markets)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于审计).

        返回:
            管理器状态字典
        """
        return {"version": self.VERSION, "config": self._config.to_dict()}
