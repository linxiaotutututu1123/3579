"""
涨跌停处理模块 - LimitPriceHandler (军规级 v4.0).

V4PRO Platform Component - Phase 9 市场数据层
V4 SPEC: 涨跌停检测与价格调整
V4 Scenarios: CHINA.LIMIT.STATE_DETECT, CHINA.LIMIT.PRICE_ADJUST

军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板

功能特性:
- 检测合约当前涨跌停状态
- 价格合法性验证
- 订单价格自动调整（限制在涨跌停范围内）
- 支持实时行情驱动的状态更新
- 提供涨跌停距离计算

期货涨跌停板规则:
- 涨停价 = 昨结算价 * (1 + 涨跌停幅度)
- 跌停价 = 昨结算价 * (1 - 涨跌停幅度)
- 价格需按最小变动价位修正（涨停向下取整，跌停向上取整）

示例:
    >>> handler = LimitPriceHandler()
    >>> state = handler.detect_limit_state(
    ...     current_price=4620.0,
    ...     last_settle=4400.0,
    ...     limit_pct=0.05,
    ...     symbol="rb2501",
    ... )
    >>> if state == LimitState.AT_LIMIT_UP:
    ...     print("合约处于涨停状态")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LimitState(Enum):
    """涨跌停状态枚举.

    属性:
        NORMAL: 正常交易状态
        NEAR_LIMIT_UP: 接近涨停（距离涨停价<1%）
        AT_LIMIT_UP: 涨停状态
        NEAR_LIMIT_DOWN: 接近跌停（距离跌停价<1%）
        AT_LIMIT_DOWN: 跌停状态
    """

    NORMAL = "NORMAL"
    NEAR_LIMIT_UP = "NEAR_LIMIT_UP"
    AT_LIMIT_UP = "AT_LIMIT_UP"
    NEAR_LIMIT_DOWN = "NEAR_LIMIT_DOWN"
    AT_LIMIT_DOWN = "AT_LIMIT_DOWN"

    def is_at_limit(self) -> bool:
        """是否处于涨跌停状态."""
        return self in (LimitState.AT_LIMIT_UP, LimitState.AT_LIMIT_DOWN)

    def is_near_limit(self) -> bool:
        """是否接近涨跌停状态."""
        return self in (LimitState.NEAR_LIMIT_UP, LimitState.NEAR_LIMIT_DOWN)

    def is_bullish_limit(self) -> bool:
        """是否为涨停方向（涨停或接近涨停）."""
        return self in (LimitState.AT_LIMIT_UP, LimitState.NEAR_LIMIT_UP)

    def is_bearish_limit(self) -> bool:
        """是否为跌停方向（跌停或接近跌停）."""
        return self in (LimitState.AT_LIMIT_DOWN, LimitState.NEAR_LIMIT_DOWN)


class PriceValidationResult(Enum):
    """价格验证结果枚举."""

    VALID = "VALID"  # 价格有效
    ABOVE_LIMIT_UP = "ABOVE_LIMIT_UP"  # 超过涨停价
    BELOW_LIMIT_DOWN = "BELOW_LIMIT_DOWN"  # 低于跌停价
    INVALID_PRICE = "INVALID_PRICE"  # 无效价格（非正数）
    INVALID_SETTLE = "INVALID_SETTLE"  # 无效结算价
    AT_LIMIT = "AT_LIMIT"  # 处于涨跌停价（可能被限制）


@dataclass(frozen=True)
class LimitHandlerConfig:
    """涨跌停处理器配置.

    属性:
        default_limit_pct: 默认涨跌停幅度 (如 0.05 表示 5%)
        near_limit_threshold: 接近涨跌停的阈值 (如 0.01 表示 1%)
        allow_limit_price_order: 是否允许以涨跌停价下单
        auto_adjust_price: 是否自动调整超限价格到涨跌停价
        default_tick_size: 默认最小变动价位
        price_tolerance: 价格比较容差 (用于浮点数比较)
    """

    default_limit_pct: float = 0.05
    near_limit_threshold: float = 0.01
    allow_limit_price_order: bool = True
    auto_adjust_price: bool = True
    default_tick_size: float = 1.0
    price_tolerance: float = 1e-6


# 中国期货市场各品种涨跌停幅度配置
# 来源: 各交易所规则 (2025年)
PRODUCT_LIMIT_PCT: dict[str, float] = {
    # 股指期货 (CFFEX) - +/-10%
    "if": 0.10,
    "ih": 0.10,
    "ic": 0.10,
    "im": 0.10,
    # 国债期货 (CFFEX) - +/-2%
    "t": 0.02,
    "tf": 0.02,
    "ts": 0.02,
    "tl": 0.02,
    # 贵金属 (SHFE) - 6%
    "au": 0.06,
    "ag": 0.06,
    # 有色金属 (SHFE) - 5%
    "cu": 0.05,
    "al": 0.05,
    "zn": 0.05,
    "pb": 0.05,
    "ni": 0.05,
    "sn": 0.05,
    "ao": 0.05,
    # 黑色系 (SHFE/DCE) - 4%
    "rb": 0.04,
    "hc": 0.04,
    "ss": 0.04,
    "i": 0.04,
    "j": 0.04,
    "jm": 0.04,
    # 能源化工 (SHFE/DCE/CZCE/INE) - 5%
    "bu": 0.05,
    "ru": 0.05,
    "sp": 0.05,
    "nr": 0.05,
    "sc": 0.05,
    "lu": 0.05,
    "fu": 0.05,
    "l": 0.05,
    "v": 0.05,
    "pp": 0.05,
    "eg": 0.05,
    "eb": 0.05,
    "pg": 0.05,
    "ma": 0.05,
    "ta": 0.05,
    "sa": 0.05,
    "ur": 0.05,
    "pf": 0.05,
    "fg": 0.05,
    # 农产品 (DCE/CZCE) - 4%
    "c": 0.04,
    "cs": 0.04,
    "a": 0.04,
    "b": 0.04,
    "m": 0.04,
    "y": 0.04,
    "p": 0.04,
    "jd": 0.04,
    "lh": 0.04,
    "rr": 0.04,
    "wh": 0.04,
    "ri": 0.04,
    "pm": 0.04,
    "cf": 0.04,
    "sr": 0.04,
    "oi": 0.04,
    "rm": 0.04,
    "rs": 0.04,
    "ap": 0.04,
    "cj": 0.04,
    "pk": 0.04,
    # 新能源 (GFEX) - 5%
    "lc": 0.05,
    "si": 0.05,
}

# 品种最小变动价位配置 (2025年)
PRODUCT_TICK_SIZE: dict[str, float] = {
    # 股指期货 (CFFEX)
    "if": 0.2,
    "ih": 0.2,
    "ic": 0.2,
    "im": 0.2,
    # 国债期货 (CFFEX)
    "t": 0.005,
    "tf": 0.005,
    "ts": 0.005,
    "tl": 0.01,
    # 贵金属 (SHFE)
    "au": 0.02,
    "ag": 1.0,
    # 有色金属 (SHFE)
    "cu": 10.0,
    "al": 5.0,
    "zn": 5.0,
    "pb": 5.0,
    "ni": 10.0,
    "sn": 10.0,
    "ao": 1.0,
    # 黑色系 (SHFE/DCE)
    "rb": 1.0,
    "hc": 1.0,
    "ss": 5.0,
    "i": 0.5,
    "j": 0.5,
    "jm": 0.5,
    # 能源化工
    "bu": 1.0,
    "ru": 5.0,
    "sp": 2.0,
    "nr": 5.0,
    "sc": 0.1,
    "lu": 1.0,
    "fu": 1.0,
    "l": 1.0,
    "v": 1.0,
    "pp": 1.0,
    "eg": 1.0,
    "eb": 1.0,
    "pg": 1.0,
    "ma": 1.0,
    "ta": 2.0,
    "sa": 1.0,
    "ur": 1.0,
    "pf": 2.0,
    "fg": 1.0,
    # 农产品
    "c": 1.0,
    "cs": 1.0,
    "a": 1.0,
    "b": 1.0,
    "m": 1.0,
    "y": 2.0,
    "p": 2.0,
    "jd": 1.0,
    "lh": 5.0,
    "rr": 1.0,
    "wh": 1.0,
    "ri": 1.0,
    "pm": 1.0,
    "cf": 5.0,
    "sr": 1.0,
    "oi": 1.0,
    "rm": 1.0,
    "rs": 1.0,
    "ap": 1.0,
    "cj": 5.0,
    "pk": 2.0,
    # 新能源 (GFEX)
    "lc": 50.0,
    "si": 5.0,
}


@dataclass
class LimitPriceInfo:
    """涨跌停价格信息.

    属性:
        symbol: 合约代码
        limit_up: 涨停价
        limit_down: 跌停价
        last_settle: 昨结算价
        limit_pct: 涨跌停幅度
        tick_size: 最小变动价位
        current_price: 当前价格（可选）
        current_state: 当前涨跌停状态（可选）
    """

    symbol: str
    limit_up: float
    limit_down: float
    last_settle: float
    limit_pct: float
    tick_size: float = 1.0
    current_price: float | None = None
    current_state: LimitState | None = None

    @property
    def limit_range(self) -> float:
        """涨跌停价格范围（涨停价 - 跌停价）."""
        return self.limit_up - self.limit_down

    @property
    def limit_range_pct(self) -> float:
        """涨跌停范围百分比（相对于昨结算价）."""
        if self.last_settle > 0:
            return self.limit_range / self.last_settle
        return 0.0

    def distance_to_limit_up(self, price: float) -> float:
        """到涨停价的距离（绝对值）."""
        return self.limit_up - price

    def distance_to_limit_down(self, price: float) -> float:
        """到跌停价的距离（绝对值）."""
        return price - self.limit_down

    def distance_to_limit_up_pct(self, price: float) -> float:
        """到涨停价的距离（百分比）."""
        if self.last_settle > 0:
            return self.distance_to_limit_up(price) / self.last_settle
        return 0.0

    def distance_to_limit_down_pct(self, price: float) -> float:
        """到跌停价的距离（百分比）."""
        if self.last_settle > 0:
            return self.distance_to_limit_down(price) / self.last_settle
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "symbol": self.symbol,
            "limit_up": self.limit_up,
            "limit_down": self.limit_down,
            "last_settle": self.last_settle,
            "limit_pct": self.limit_pct,
            "tick_size": self.tick_size,
            "current_price": self.current_price,
            "current_state": self.current_state.value if self.current_state else None,
            "limit_range": self.limit_range,
            "limit_range_pct": self.limit_range_pct,
        }


@dataclass
class PriceValidationOutput:
    """价格验证输出.

    属性:
        result: 验证结果枚举
        original_price: 原始价格
        adjusted_price: 调整后价格（如果进行了调整）
        limit_info: 涨跌停价格信息
        message: 验证消息
        was_adjusted: 是否进行了价格调整
    """

    result: PriceValidationResult
    original_price: float
    adjusted_price: float
    limit_info: LimitPriceInfo
    message: str = ""
    was_adjusted: bool = False

    @property
    def is_valid(self) -> bool:
        """价格是否有效（可下单）."""
        return self.result in (
            PriceValidationResult.VALID,
            PriceValidationResult.AT_LIMIT,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "original_price": self.original_price,
            "adjusted_price": self.adjusted_price,
            "limit_info": self.limit_info.to_dict(),
            "message": self.message,
            "was_adjusted": self.was_adjusted,
            "is_valid": self.is_valid,
        }


@dataclass
class SymbolLimitState:
    """合约涨跌停状态缓存.

    属性:
        symbol: 合约代码
        state: 当前涨跌停状态
        limit_info: 涨跌停价格信息
        update_ts: 最后更新时间戳
        consecutive_limit_count: 连续涨跌停次数
    """

    symbol: str
    state: LimitState
    limit_info: LimitPriceInfo
    update_ts: float = 0.0
    consecutive_limit_count: int = 0


class LimitPriceHandler:
    """涨跌停处理器 (军规级 v4.0).

    军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板

    V4 Scenarios:
    - CHINA.LIMIT.STATE_DETECT: 涨跌停状态检测
    - CHINA.LIMIT.PRICE_ADJUST: 价格调整

    功能:
    - 检测合约当前涨跌停状态
    - 验证订单价格合法性
    - 自动调整超限价格到涨跌停范围内
    - 缓存合约涨跌停状态

    示例:
        >>> handler = LimitPriceHandler()
        >>> state = handler.detect_limit_state(
        ...     current_price=4620.0,
        ...     last_settle=4400.0,
        ...     limit_pct=0.05,
        ...     symbol="rb2501",
        ... )
        >>> print(state)
        LimitState.AT_LIMIT_UP
    """

    def __init__(
        self,
        config: LimitHandlerConfig | None = None,
        product_limits: dict[str, float] | None = None,
        product_tick_sizes: dict[str, float] | None = None,
    ) -> None:
        """初始化涨跌停处理器.

        参数:
            config: 处理器配置
            product_limits: 品种涨跌停幅度覆盖配置
            product_tick_sizes: 品种最小变动价位覆盖配置
        """
        self._config = config or LimitHandlerConfig()
        self._product_limits = product_limits or PRODUCT_LIMIT_PCT.copy()
        self._product_tick_sizes = product_tick_sizes or PRODUCT_TICK_SIZE.copy()

        # 状态缓存
        self._state_cache: dict[str, SymbolLimitState] = {}

        # 统计信息
        self._stats = _LimitHandlerStats()

    @property
    def config(self) -> LimitHandlerConfig:
        """获取配置."""
        return self._config

    @property
    def stats(self) -> dict[str, Any]:
        """获取统计信息."""
        return self._stats.to_dict()

    def get_limit_pct(self, symbol: str) -> float:
        """获取品种的涨跌停幅度.

        参数:
            symbol: 合约代码 (如 "rb2501")

        返回:
            涨跌停幅度 (如 0.05 表示 5%)
        """
        product = self._extract_product(symbol)
        return self._product_limits.get(product, self._config.default_limit_pct)

    def get_tick_size(self, symbol: str) -> float:
        """获取品种的最小变动价位.

        参数:
            symbol: 合约代码

        返回:
            最小变动价位
        """
        product = self._extract_product(symbol)
        return self._product_tick_sizes.get(product, self._config.default_tick_size)

    def calculate_limit_prices(
        self,
        last_settle: float,
        symbol: str = "",
        limit_pct: float | None = None,
        tick_size: float | None = None,
    ) -> LimitPriceInfo:
        """计算涨跌停价格.

        参数:
            last_settle: 昨结算价
            symbol: 合约代码 (用于查找品种涨跌停幅度和tick_size)
            limit_pct: 涨跌停幅度 (None则根据品种查找)
            tick_size: 最小变动价位 (None则根据品种查找)

        返回:
            涨跌停价格信息
        """
        # 确定涨跌停幅度
        if limit_pct is None:
            limit_pct = self.get_limit_pct(symbol) if symbol else self._config.default_limit_pct

        # 确定tick_size
        if tick_size is None:
            tick_size = self.get_tick_size(symbol) if symbol else self._config.default_tick_size

        # 计算原始涨跌停价格
        raw_limit_up = last_settle * (1 + limit_pct)
        raw_limit_down = last_settle * (1 - limit_pct)

        # 按tick_size修正 (涨停向下取整，跌停向上取整)
        if tick_size > 0:
            limit_up = self._round_down(raw_limit_up, tick_size)
            limit_down = self._round_up(raw_limit_down, tick_size)
        else:
            limit_up = raw_limit_up
            limit_down = raw_limit_down

        return LimitPriceInfo(
            symbol=symbol,
            limit_up=limit_up,
            limit_down=limit_down,
            last_settle=last_settle,
            limit_pct=limit_pct,
            tick_size=tick_size,
        )

    def detect_limit_state(
        self,
        current_price: float,
        last_settle: float,
        symbol: str = "",
        limit_pct: float | None = None,
        tick_size: float | None = None,
    ) -> LimitState:
        """检测当前价格的涨跌停状态.

        军规 M13: 涨跌停感知
        V4 Scenario: CHINA.LIMIT.STATE_DETECT

        参数:
            current_price: 当前价格
            last_settle: 昨结算价
            symbol: 合约代码
            limit_pct: 涨跌停幅度
            tick_size: 最小变动价位

        返回:
            涨跌停状态枚举
        """
        self._stats.detection_count += 1

        # 参数验证
        if current_price <= 0 or last_settle <= 0:
            return LimitState.NORMAL

        # 获取涨跌停价格
        limit_info = self.calculate_limit_prices(
            last_settle, symbol, limit_pct, tick_size
        )

        # 检测涨跌停状态
        state = self._determine_limit_state(current_price, limit_info)

        # 更新缓存
        if symbol:
            limit_info.current_price = current_price
            limit_info.current_state = state
            self._update_state_cache(symbol, state, limit_info)

        # 更新统计
        if state.is_at_limit():
            self._stats.limit_hit_count += 1
        elif state.is_near_limit():
            self._stats.near_limit_count += 1

        return state

    def validate_order_price(
        self,
        order_price: float,
        last_settle: float,
        symbol: str = "",
        limit_pct: float | None = None,
        tick_size: float | None = None,
        auto_adjust: bool | None = None,
    ) -> PriceValidationOutput:
        """验证订单价格是否在涨跌停范围内.

        军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板
        V4 Scenario: CHINA.LIMIT.PRICE_ADJUST

        参数:
            order_price: 订单价格
            last_settle: 昨结算价
            symbol: 合约代码
            limit_pct: 涨跌停幅度
            tick_size: 最小变动价位
            auto_adjust: 是否自动调整价格 (None则使用配置默认值)

        返回:
            价格验证输出
        """
        self._stats.validation_count += 1

        # 确定是否自动调整
        should_adjust = (
            auto_adjust if auto_adjust is not None else self._config.auto_adjust_price
        )

        # 验证订单价格
        if order_price <= 0:
            self._stats.rejection_count += 1
            return PriceValidationOutput(
                result=PriceValidationResult.INVALID_PRICE,
                original_price=order_price,
                adjusted_price=order_price,
                limit_info=LimitPriceInfo(
                    symbol=symbol,
                    limit_up=0.0,
                    limit_down=0.0,
                    last_settle=last_settle,
                    limit_pct=0.0,
                ),
                message=f"无效订单价格: {order_price}",
            )

        # 验证昨结算价
        if last_settle <= 0:
            self._stats.rejection_count += 1
            return PriceValidationOutput(
                result=PriceValidationResult.INVALID_SETTLE,
                original_price=order_price,
                adjusted_price=order_price,
                limit_info=LimitPriceInfo(
                    symbol=symbol,
                    limit_up=0.0,
                    limit_down=0.0,
                    last_settle=last_settle,
                    limit_pct=0.0,
                ),
                message=f"无效昨结算价: {last_settle}",
            )

        # 获取涨跌停价格
        limit_info = self.calculate_limit_prices(
            last_settle, symbol, limit_pct, tick_size
        )

        # 检查是否超过涨停价
        if order_price > limit_info.limit_up + self._config.price_tolerance:
            if should_adjust:
                self._stats.adjustment_count += 1
                return PriceValidationOutput(
                    result=PriceValidationResult.VALID,
                    original_price=order_price,
                    adjusted_price=limit_info.limit_up,
                    limit_info=limit_info,
                    message=f"订单价格 {order_price} 超过涨停价 {limit_info.limit_up}，已调整",
                    was_adjusted=True,
                )
            self._stats.rejection_count += 1
            return PriceValidationOutput(
                result=PriceValidationResult.ABOVE_LIMIT_UP,
                original_price=order_price,
                adjusted_price=order_price,
                limit_info=limit_info,
                message=f"订单价格 {order_price} 超过涨停价 {limit_info.limit_up}",
            )

        # 检查是否低于跌停价
        if order_price < limit_info.limit_down - self._config.price_tolerance:
            if should_adjust:
                self._stats.adjustment_count += 1
                return PriceValidationOutput(
                    result=PriceValidationResult.VALID,
                    original_price=order_price,
                    adjusted_price=limit_info.limit_down,
                    limit_info=limit_info,
                    message=f"订单价格 {order_price} 低于跌停价 {limit_info.limit_down}，已调整",
                    was_adjusted=True,
                )
            self._stats.rejection_count += 1
            return PriceValidationOutput(
                result=PriceValidationResult.BELOW_LIMIT_DOWN,
                original_price=order_price,
                adjusted_price=order_price,
                limit_info=limit_info,
                message=f"订单价格 {order_price} 低于跌停价 {limit_info.limit_down}",
            )

        # 检查是否刚好等于涨停价或跌停价
        at_limit_up = abs(order_price - limit_info.limit_up) < self._config.price_tolerance
        at_limit_down = abs(order_price - limit_info.limit_down) < self._config.price_tolerance

        if at_limit_up or at_limit_down:
            if not self._config.allow_limit_price_order:
                self._stats.rejection_count += 1
                limit_type = "涨停" if at_limit_up else "跌停"
                return PriceValidationOutput(
                    result=PriceValidationResult.AT_LIMIT,
                    original_price=order_price,
                    adjusted_price=order_price,
                    limit_info=limit_info,
                    message=f"订单价格等于{limit_type}价，不允许{limit_type}价下单",
                )
            # 允许涨跌停价下单
            return PriceValidationOutput(
                result=PriceValidationResult.AT_LIMIT,
                original_price=order_price,
                adjusted_price=order_price,
                limit_info=limit_info,
                message="订单价格等于涨跌停价，允许下单",
            )

        # 通过验证
        return PriceValidationOutput(
            result=PriceValidationResult.VALID,
            original_price=order_price,
            adjusted_price=order_price,
            limit_info=limit_info,
            message="价格验证通过",
        )

    def adjust_price_to_limit(
        self,
        price: float,
        last_settle: float,
        symbol: str = "",
        limit_pct: float | None = None,
        tick_size: float | None = None,
    ) -> tuple[float, bool]:
        """将价格调整到涨跌停范围内.

        参数:
            price: 原始价格
            last_settle: 昨结算价
            symbol: 合约代码
            limit_pct: 涨跌停幅度
            tick_size: 最小变动价位

        返回:
            (调整后价格, 是否进行了调整)
        """
        if price <= 0 or last_settle <= 0:
            return price, False

        limit_info = self.calculate_limit_prices(
            last_settle, symbol, limit_pct, tick_size
        )

        # 超过涨停价
        if price > limit_info.limit_up + self._config.price_tolerance:
            return limit_info.limit_up, True

        # 低于跌停价
        if price < limit_info.limit_down - self._config.price_tolerance:
            return limit_info.limit_down, True

        return price, False

    def get_cached_state(self, symbol: str) -> SymbolLimitState | None:
        """获取缓存的涨跌停状态.

        参数:
            symbol: 合约代码

        返回:
            缓存的状态信息，不存在返回None
        """
        return self._state_cache.get(symbol)

    def get_all_at_limit_symbols(self) -> list[str]:
        """获取所有处于涨跌停状态的合约代码."""
        return [
            symbol
            for symbol, state in self._state_cache.items()
            if state.state.is_at_limit()
        ]

    def get_all_near_limit_symbols(self) -> list[str]:
        """获取所有接近涨跌停状态的合约代码."""
        return [
            symbol
            for symbol, state in self._state_cache.items()
            if state.state.is_near_limit()
        ]

    def clear_cache(self) -> None:
        """清空状态缓存."""
        self._state_cache.clear()

    def reset_stats(self) -> None:
        """重置统计信息."""
        self._stats = _LimitHandlerStats()

    def _determine_limit_state(
        self,
        price: float,
        limit_info: LimitPriceInfo,
    ) -> LimitState:
        """确定价格的涨跌停状态.

        参数:
            price: 当前价格
            limit_info: 涨跌停价格信息

        返回:
            涨跌停状态
        """
        tolerance = self._config.price_tolerance

        # 涨停
        if abs(price - limit_info.limit_up) < tolerance:
            return LimitState.AT_LIMIT_UP

        # 跌停
        if abs(price - limit_info.limit_down) < tolerance:
            return LimitState.AT_LIMIT_DOWN

        # 接近涨停
        distance_to_up = limit_info.distance_to_limit_up_pct(price)
        if 0 < distance_to_up < self._config.near_limit_threshold:
            return LimitState.NEAR_LIMIT_UP

        # 接近跌停
        distance_to_down = limit_info.distance_to_limit_down_pct(price)
        if 0 < distance_to_down < self._config.near_limit_threshold:
            return LimitState.NEAR_LIMIT_DOWN

        return LimitState.NORMAL

    def _update_state_cache(
        self,
        symbol: str,
        state: LimitState,
        limit_info: LimitPriceInfo,
    ) -> None:
        """更新状态缓存.

        参数:
            symbol: 合约代码
            state: 涨跌停状态
            limit_info: 涨跌停价格信息
        """
        import time

        existing = self._state_cache.get(symbol)
        consecutive_count = 0

        if existing:
            # 计算连续涨跌停次数
            if state.is_at_limit() and existing.state.is_at_limit():
                consecutive_count = existing.consecutive_limit_count + 1
            elif state.is_at_limit():
                consecutive_count = 1

        self._state_cache[symbol] = SymbolLimitState(
            symbol=symbol,
            state=state,
            limit_info=limit_info,
            update_ts=time.time(),
            consecutive_limit_count=consecutive_count,
        )

    def _extract_product(self, symbol: str) -> str:
        """从合约代码提取品种代码.

        参数:
            symbol: 合约代码 (如 "rb2501", "IF2501")

        返回:
            品种代码 (如 "rb", "if")
        """
        if not symbol:
            return ""

        product = ""
        for char in symbol:
            if char.isalpha():
                product += char
            elif char.isdigit() and product:
                break

        return product.lower()

    def _round_down(self, price: float, tick_size: float) -> float:
        """向下取整到tick_size.

        参数:
            price: 原始价格
            tick_size: 最小变动价位

        返回:
            修正后的价格
        """
        if tick_size <= 0:
            return price
        return int(price / tick_size) * tick_size

    def _round_up(self, price: float, tick_size: float) -> float:
        """向上取整到tick_size.

        参数:
            price: 原始价格
            tick_size: 最小变动价位

        返回:
            修正后的价格
        """
        if tick_size <= 0:
            return price
        return math.ceil(price / tick_size) * tick_size


@dataclass
class _LimitHandlerStats:
    """涨跌停处理器统计信息."""

    detection_count: int = 0
    validation_count: int = 0
    rejection_count: int = 0
    adjustment_count: int = 0
    limit_hit_count: int = 0
    near_limit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "detection_count": self.detection_count,
            "validation_count": self.validation_count,
            "rejection_count": self.rejection_count,
            "adjustment_count": self.adjustment_count,
            "limit_hit_count": self.limit_hit_count,
            "near_limit_count": self.near_limit_count,
            "rejection_rate": (
                self.rejection_count / self.validation_count
                if self.validation_count > 0
                else 0.0
            ),
            "adjustment_rate": (
                self.adjustment_count / self.validation_count
                if self.validation_count > 0
                else 0.0
            ),
        }


# ============================================================================
# 便捷函数
# ============================================================================

_default_handler: LimitPriceHandler | None = None


def get_default_handler() -> LimitPriceHandler:
    """获取默认涨跌停处理器 (单例).

    返回:
        默认的LimitPriceHandler实例
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = LimitPriceHandler()
    return _default_handler


def detect_limit_state(
    current_price: float,
    last_settle: float,
    symbol: str = "",
    limit_pct: float | None = None,
) -> LimitState:
    """检测涨跌停状态 (便捷函数).

    军规 M13: 涨跌停感知

    参数:
        current_price: 当前价格
        last_settle: 昨结算价
        symbol: 合约代码
        limit_pct: 涨跌停幅度

    返回:
        涨跌停状态枚举
    """
    handler = get_default_handler()
    return handler.detect_limit_state(current_price, last_settle, symbol, limit_pct)


def validate_and_adjust_price(
    order_price: float,
    last_settle: float,
    symbol: str = "",
    limit_pct: float | None = None,
) -> tuple[float, bool, str]:
    """验证并调整订单价格 (便捷函数).

    军规 M13: 涨跌停感知

    参数:
        order_price: 订单价格
        last_settle: 昨结算价
        symbol: 合约代码
        limit_pct: 涨跌停幅度

    返回:
        (调整后价格, 是否有效, 消息)
    """
    handler = get_default_handler()
    result = handler.validate_order_price(order_price, last_settle, symbol, limit_pct)
    return result.adjusted_price, result.is_valid, result.message


def calculate_limit_prices(
    last_settle: float,
    symbol: str = "",
    limit_pct: float | None = None,
) -> tuple[float, float]:
    """计算涨跌停价格 (便捷函数).

    参数:
        last_settle: 昨结算价
        symbol: 合约代码
        limit_pct: 涨跌停幅度

    返回:
        (涨停价, 跌停价)
    """
    handler = get_default_handler()
    info = handler.calculate_limit_prices(last_settle, symbol, limit_pct)
    return info.limit_up, info.limit_down
