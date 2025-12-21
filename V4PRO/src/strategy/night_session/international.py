"""国际市场联动套利策略 (军规级 v4.0).

V4PRO Platform Component - 国际市场联动套利策略
V4 SPEC: M1军规 - 单一信号源

策略逻辑:
1. 监测国际市场走势 (CME, LME等)
2. 计算价差和相关性
3. 识别联动机会
4. 执行跨市场套利

军规覆盖:
- M1: 单一信号源 - 信号源唯一性保证
- M15: 夜盘跨日处理 - 夜盘时段特殊处理

示例:
    >>> from src.strategy.night_session import InternationalLinkageStrategy
    >>> strategy = InternationalLinkageStrategy()
    >>> signal = strategy.generate_signal(market_data)
    >>> print(signal.direction)
    SignalDirection.LONG
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar

from src.strategy.night_session.gap_flash import (
    MarketContext,
    NightSessionStrategy,
    StrategySignal,
)
from src.strategy.single_signal_source import (
    SignalDirection,
    SignalPriority,
    SignalType,
    TradingSignal,
)
from src.strategy.types import MarketState, TargetPortfolio


class ArbitrageType(Enum):
    """套利类型枚举.

    属性:
        LONG_DOMESTIC: 做多国内，做空国际（国内价格相对便宜）
        SHORT_DOMESTIC: 做空国内，做多国际（国内价格相对贵）
        NO_ARBITRAGE: 无套利机会
    """

    LONG_DOMESTIC = "LONG_DOMESTIC"  # 做多国内
    SHORT_DOMESTIC = "SHORT_DOMESTIC"  # 做空国内
    NO_ARBITRAGE = "NO_ARBITRAGE"  # 无套利


class LinkageState(Enum):
    """策略状态枚举.

    属性:
        MONITORING: 监测状态，等待套利机会
        POSITION_OPEN: 已建仓
        POSITION_CLOSING: 正在平仓
        COOLDOWN: 冷却期，等待重新入场
    """

    MONITORING = "MONITORING"  # 监测中
    POSITION_OPEN = "POSITION_OPEN"  # 已建仓
    POSITION_CLOSING = "POSITION_CLOSING"  # 平仓中
    COOLDOWN = "COOLDOWN"  # 冷却期


@dataclass(frozen=True, slots=True)
class LinkedMarket:
    """联动市场对配置 (不可变).

    属性:
        product_name: 产品名称（如铜、黄金、原油）
        domestic_symbol: 国内合约代码
        foreign_symbol: 国际合约代码
        exchange_rate_symbol: 汇率代码（可选）
        unit_ratio: 单位转换比例（国际/国内）
        default_correlation: 默认相关性
    """

    product_name: str
    domestic_symbol: str
    foreign_symbol: str
    exchange_rate_symbol: str = "USDCNY"
    unit_ratio: float = 1.0
    default_correlation: float = 0.8


@dataclass(frozen=True, slots=True)
class SpreadInfo:
    """价差信息 (不可变).

    属性:
        domestic_price: 国内价格
        foreign_price: 国际价格（已换算为人民币）
        raw_foreign_price: 国际价格（原始货币）
        exchange_rate: 汇率
        spread: 价差（国内 - 国际换算后）
        spread_ratio: 价差比例
        z_score: 标准化Z分数
        timestamp: 计算时间戳
    """

    domestic_price: float
    foreign_price: float
    raw_foreign_price: float
    exchange_rate: float
    spread: float
    spread_ratio: float
    z_score: float
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于审计).

        返回:
            包含价差信息的字典
        """
        return {
            "domestic_price": round(self.domestic_price, 4),
            "foreign_price": round(self.foreign_price, 4),
            "raw_foreign_price": round(self.raw_foreign_price, 4),
            "exchange_rate": round(self.exchange_rate, 4),
            "spread": round(self.spread, 4),
            "spread_ratio": round(self.spread_ratio, 6),
            "z_score": round(self.z_score, 4),
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CorrelationInfo:
    """相关性信息 (不可变).

    属性:
        correlation: 皮尔逊相关系数
        window_size: 计算窗口大小
        sample_count: 样本数量
        is_stable: 相关性是否稳定
        timestamp: 计算时间戳
    """

    correlation: float
    window_size: int
    sample_count: int
    is_stable: bool
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        返回:
            包含相关性信息的字典
        """
        return {
            "correlation": round(self.correlation, 4),
            "window_size": self.window_size,
            "sample_count": self.sample_count,
            "is_stable": self.is_stable,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class ArbitrageOpportunity:
    """套利机会信息 (不可变).

    属性:
        arb_type: 套利类型
        spread_info: 价差信息
        correlation_info: 相关性信息
        expected_return: 预期收益率
        confidence: 置信度
        entry_price: 建议入场价格
        target_price: 目标价格
        stop_price: 止损价格
        reason: 套利原因
    """

    arb_type: ArbitrageType
    spread_info: SpreadInfo
    correlation_info: CorrelationInfo
    expected_return: float
    confidence: float
    entry_price: float
    target_price: float
    stop_price: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        返回:
            包含套利机会信息的字典
        """
        return {
            "arb_type": self.arb_type.value,
            "spread_info": self.spread_info.to_dict(),
            "correlation_info": self.correlation_info.to_dict(),
            "expected_return": round(self.expected_return, 6),
            "confidence": round(self.confidence, 4),
            "entry_price": round(self.entry_price, 4),
            "target_price": round(self.target_price, 4),
            "stop_price": round(self.stop_price, 4),
            "reason": self.reason,
        }


@dataclass
class InternationalLinkageConfig:
    """国际联动策略配置.

    属性:
        entry_z_threshold: 入场Z分数阈值
        exit_z_threshold: 出场Z分数阈值
        stop_z_threshold: 止损Z分数阈值
        min_correlation: 最小相关性阈值
        correlation_window: 相关性计算窗口
        spread_window: 价差计算窗口
        min_confidence: 最小置信度阈值
        cooldown_seconds: 冷却期秒数
        max_position_per_leg: 每腿最大仓位
        default_exchange_rate: 默认汇率
    """

    entry_z_threshold: float = 2.0
    exit_z_threshold: float = 0.5
    stop_z_threshold: float = 4.0
    min_correlation: float = 0.6
    correlation_window: int = 60
    spread_window: int = 100
    min_confidence: float = 0.5
    cooldown_seconds: float = 300.0
    max_position_per_leg: int = 10
    default_exchange_rate: float = 7.2


class InternationalLinkageStrategy(NightSessionStrategy):
    """国际市场联动套利策略 (军规 M1).

    策略逻辑:
    1. 监测国际市场走势 (CME, LME等)
    2. 计算价差和相关性
    3. 识别联动机会
    4. 执行跨市场套利

    核心方法:
    - calculate_spread: 计算国内外价差
    - check_correlation: 检查价格相关性
    - detect_arbitrage_opportunity: 检测套利机会
    - generate_signal: 生成交易信号

    军规覆盖:
    - M1: 单一信号源
    - M15: 夜盘跨日处理
    """

    VERSION: ClassVar[str] = "4.0.0"
    STRATEGY_ID: ClassVar[str] = "international_linkage"

    # 联动市场配置
    LINKED_MARKETS: ClassVar[dict[str, LinkedMarket]] = {
        "copper": LinkedMarket(
            product_name="铜",
            domestic_symbol="SHFE.CU",
            foreign_symbol="LME.CA",
            exchange_rate_symbol="USDCNY",
            unit_ratio=1.0,
            default_correlation=0.85,
        ),
        "gold": LinkedMarket(
            product_name="黄金",
            domestic_symbol="SHFE.AU",
            foreign_symbol="COMEX.GC",
            exchange_rate_symbol="USDCNY",
            unit_ratio=31.1035,  # 盎司转克
            default_correlation=0.90,
        ),
        "oil": LinkedMarket(
            product_name="原油",
            domestic_symbol="INE.SC",
            foreign_symbol="NYMEX.CL",
            exchange_rate_symbol="USDCNY",
            unit_ratio=1.0,
            default_correlation=0.80,
        ),
    }

    def __init__(
        self,
        config: InternationalLinkageConfig | None = None,
        product: str = "copper",
    ) -> None:
        """初始化国际市场联动套利策略.

        参数:
            config: 策略配置
            product: 产品类型（copper/gold/oil）
        """
        super().__init__(strategy_id=self.STRATEGY_ID)

        # 策略配置
        self._config = config or InternationalLinkageConfig()
        self._product = product

        # 获取联动市场配置
        self._linked_market = self.LINKED_MARKETS.get(
            product,
            self.LINKED_MARKETS["copper"],
        )

        # 状态变量
        self._state = LinkageState.MONITORING
        self._current_opportunity: ArbitrageOpportunity | None = None

        # 价格历史数据（用于计算统计量）
        self._domestic_prices: list[float] = []
        self._foreign_prices: list[float] = []
        self._spread_history: list[float] = []

        # 当前汇率
        self._exchange_rate = self._config.default_exchange_rate

        # 冷却期管理
        self._cooldown_start: float | None = None

        # 仓位跟踪
        self._position: int = 0

        # 统计量缓存
        self._spread_mean: float = 0.0
        self._spread_std: float = 0.0

    # ========================================
    # 核心计算方法
    # ========================================

    def calculate_spread(
        self,
        domestic: float,
        foreign: float,
        exchange_rate: float | None = None,
    ) -> float:
        """计算国内外价差.

        将国际价格换算为人民币后，计算与国内价格的价差。

        参数:
            domestic: 国内价格
            foreign: 国际价格（原始货币）
            exchange_rate: 汇率（默认使用配置汇率）

        返回:
            价差 = 国内价格 - 国际换算价格

        示例:
            >>> strategy = InternationalLinkageStrategy()
            >>> spread = strategy.calculate_spread(70000.0, 9500.0, 7.2)
            >>> print(spread)  # 70000 - 9500 * 7.2 = 1600
        """
        if exchange_rate is None:
            exchange_rate = self._exchange_rate

        # 换算国际价格为人民币
        # 考虑单位转换比例
        foreign_cny = foreign * exchange_rate * self._linked_market.unit_ratio

        # 计算价差
        spread = domestic - foreign_cny

        return spread

    def check_correlation(
        self,
        domestic_prices: list[float],
        foreign_prices: list[float],
    ) -> float:
        """计算国内外价格相关性.

        使用皮尔逊相关系数衡量价格联动程度。

        参数:
            domestic_prices: 国内价格序列
            foreign_prices: 国际价格序列

        返回:
            皮尔逊相关系数 (-1 到 1)

        注意:
            - 相关性越高，套利机会越可靠
            - 相关性低于阈值时，不应进行套利

        示例:
            >>> domestic = [100.0, 101.0, 102.0, 101.5, 103.0]
            >>> foreign = [10.0, 10.1, 10.2, 10.15, 10.3]
            >>> corr = strategy.check_correlation(domestic, foreign)
            >>> print(corr)  # 接近 1.0
        """
        n = len(domestic_prices)

        # 样本数量不足
        if n < 2 or n != len(foreign_prices):
            return self._linked_market.default_correlation

        # 计算均值
        mean_d = sum(domestic_prices) / n
        mean_f = sum(foreign_prices) / n

        # 计算协方差和方差
        cov = 0.0
        var_d = 0.0
        var_f = 0.0

        for i in range(n):
            dd = domestic_prices[i] - mean_d
            df = foreign_prices[i] - mean_f
            cov += dd * df
            var_d += dd * dd
            var_f += df * df

        # 避免除零
        if var_d <= 0 or var_f <= 0:
            return self._linked_market.default_correlation

        # 计算相关系数
        correlation = cov / math.sqrt(var_d * var_f)

        # 限制范围
        return max(-1.0, min(1.0, correlation))

    def detect_arbitrage_opportunity(
        self,
        spread: float,
        correlation: float,
    ) -> bool:
        """检测套利机会.

        基于价差Z分数和相关性判断是否存在套利机会。

        参数:
            spread: 当前价差
            correlation: 当前相关性

        返回:
            是否存在套利机会

        逻辑:
            1. 相关性必须足够高（表明价格联动稳定）
            2. 价差Z分数必须超过入场阈值（表明偏离均值足够大）
            3. 预期价差会回归均值

        示例:
            >>> opportunity = strategy.detect_arbitrage_opportunity(
            ...     spread=1500.0,
            ...     correlation=0.85
            ... )
            >>> if opportunity:
            ...     print("发现套利机会！")
        """
        # 条件1: 相关性检查
        if correlation < self._config.min_correlation:
            return False

        # 条件2: 计算Z分数
        if self._spread_std <= 0:
            return False

        z_score = (spread - self._spread_mean) / self._spread_std

        # 条件3: Z分数超过入场阈值
        if abs(z_score) < self._config.entry_z_threshold:
            return False

        return True

    # ========================================
    # 信号生成方法
    # ========================================

    def generate_signal(self, market_data: MarketState) -> StrategySignal:
        """生成交易信号 (军规 M1: 单一信号源).

        基于国际市场联动分析生成套利交易信号。

        参数:
            market_data: 市场数据状态

        返回:
            策略信号

        流程:
            1. 获取国内外价格
            2. 计算价差和相关性
            3. 检测套利机会
            4. 生成交易信号
        """
        now = time.time()

        # 获取价格数据
        domestic_symbol = self._linked_market.domestic_symbol
        foreign_symbol = self._linked_market.foreign_symbol
        exchange_rate_symbol = self._linked_market.exchange_rate_symbol

        domestic_price = market_data.prices.get(domestic_symbol, 0.0)
        foreign_price = market_data.prices.get(foreign_symbol, 0.0)
        exchange_rate = market_data.prices.get(
            exchange_rate_symbol,
            self._config.default_exchange_rate,
        )

        # 更新汇率
        if exchange_rate > 0:
            self._exchange_rate = exchange_rate

        # 价格无效，返回平仓信号
        if domestic_price <= 0 or foreign_price <= 0:
            return self._create_flat_signal(domestic_symbol)

        # 更新价格历史
        self._update_price_history(domestic_price, foreign_price)

        # 计算价差
        spread = self.calculate_spread(domestic_price, foreign_price)
        self._update_spread_statistics(spread)

        # 计算相关性
        correlation = self.check_correlation(
            self._domestic_prices,
            self._foreign_prices,
        )

        # 创建价差信息
        spread_info = SpreadInfo(
            domestic_price=domestic_price,
            foreign_price=foreign_price * self._exchange_rate * self._linked_market.unit_ratio,
            raw_foreign_price=foreign_price,
            exchange_rate=self._exchange_rate,
            spread=spread,
            spread_ratio=spread / domestic_price if domestic_price > 0 else 0.0,
            z_score=self._calculate_z_score(spread),
            timestamp=now,
        )

        # 创建相关性信息
        correlation_info = CorrelationInfo(
            correlation=correlation,
            window_size=self._config.correlation_window,
            sample_count=len(self._domestic_prices),
            is_stable=correlation >= self._config.min_correlation,
            timestamp=now,
        )

        # 检查冷却期
        if self._is_in_cooldown(now):
            return self._create_flat_signal_with_info(
                domestic_symbol,
                spread_info,
                "冷却期中，等待重新入场",
            )

        # 处理不同状态
        if self._state == LinkageState.MONITORING:
            return self._handle_monitoring_state(
                domestic_symbol,
                spread_info,
                correlation_info,
            )
        elif self._state == LinkageState.POSITION_OPEN:
            return self._handle_position_state(
                domestic_symbol,
                spread_info,
                correlation_info,
            )
        else:
            return self._create_flat_signal(domestic_symbol)

    def _handle_monitoring_state(
        self,
        symbol: str,
        spread_info: SpreadInfo,
        correlation_info: CorrelationInfo,
    ) -> StrategySignal:
        """处理监测状态.

        参数:
            symbol: 合约代码
            spread_info: 价差信息
            correlation_info: 相关性信息

        返回:
            策略信号
        """
        z_score = spread_info.z_score

        # 检测套利机会
        has_opportunity = self.detect_arbitrage_opportunity(
            spread_info.spread,
            correlation_info.correlation,
        )

        if not has_opportunity:
            return self._create_flat_signal_with_info(
                symbol,
                spread_info,
                "无套利机会",
            )

        # 确定套利方向和目标
        if z_score > self._config.entry_z_threshold:
            # 价差过大（国内相对贵）-> 做空国内
            arb_type = ArbitrageType.SHORT_DOMESTIC
            direction = SignalDirection.SHORT
            target_spread = self._spread_mean + self._spread_std * self._config.exit_z_threshold
            stop_spread = self._spread_mean + self._spread_std * self._config.stop_z_threshold
            reason = f"价差Z分数={z_score:.2f}，国内相对高估，做空套利"
        elif z_score < -self._config.entry_z_threshold:
            # 价差过小（国内相对便宜）-> 做多国内
            arb_type = ArbitrageType.LONG_DOMESTIC
            direction = SignalDirection.LONG
            target_spread = self._spread_mean - self._spread_std * self._config.exit_z_threshold
            stop_spread = self._spread_mean - self._spread_std * self._config.stop_z_threshold
            reason = f"价差Z分数={z_score:.2f}，国内相对低估，做多套利"
        else:
            return self._create_flat_signal_with_info(
                symbol,
                spread_info,
                "Z分数未超过入场阈值",
            )

        # 计算预期收益和置信度
        expected_return = abs(spread_info.spread - target_spread) / spread_info.domestic_price
        confidence = self._calculate_confidence(
            z_score,
            correlation_info.correlation,
            len(self._spread_history),
        )

        # 置信度检查
        if confidence < self._config.min_confidence:
            return self._create_flat_signal_with_info(
                symbol,
                spread_info,
                f"置信度不足: {confidence:.2f} < {self._config.min_confidence:.2f}",
            )

        # 计算目标价和止损价
        target_price, stop_price = self._calculate_target_and_stop(
            spread_info.domestic_price,
            spread_info.spread,
            target_spread,
            stop_spread,
            direction,
        )

        # 创建套利机会
        opportunity = ArbitrageOpportunity(
            arb_type=arb_type,
            spread_info=spread_info,
            correlation_info=correlation_info,
            expected_return=expected_return,
            confidence=confidence,
            entry_price=spread_info.domestic_price,
            target_price=target_price,
            stop_price=stop_price,
            reason=reason,
        )

        # 更新状态
        self._state = LinkageState.POSITION_OPEN
        self._current_opportunity = opportunity

        # 返回信号
        return StrategySignal(
            direction=direction,
            entry_price=spread_info.domestic_price,
            target_price=target_price,
            stop_price=stop_price,
            confidence=confidence,
            strength=min(1.0, abs(z_score) / self._config.stop_z_threshold),
            gap_info=None,
            timestamp=time.time(),
            reason=reason,
        )

    def _handle_position_state(
        self,
        symbol: str,
        spread_info: SpreadInfo,
        correlation_info: CorrelationInfo,
    ) -> StrategySignal:
        """处理持仓状态.

        参数:
            symbol: 合约代码
            spread_info: 价差信息
            correlation_info: 相关性信息

        返回:
            策略信号
        """
        if self._current_opportunity is None:
            self._state = LinkageState.MONITORING
            return self._create_flat_signal(symbol)

        z_score = spread_info.z_score
        arb_type = self._current_opportunity.arb_type

        # 检查止盈条件
        if arb_type == ArbitrageType.LONG_DOMESTIC:
            if z_score >= -self._config.exit_z_threshold:
                return self._close_position(symbol, spread_info, "止盈: 价差回归")
            if z_score < -self._config.stop_z_threshold:
                return self._close_position(symbol, spread_info, "止损: 价差继续扩大")
        else:  # SHORT_DOMESTIC
            if z_score <= self._config.exit_z_threshold:
                return self._close_position(symbol, spread_info, "止盈: 价差回归")
            if z_score > self._config.stop_z_threshold:
                return self._close_position(symbol, spread_info, "止损: 价差继续扩大")

        # 检查相关性崩溃
        if not correlation_info.is_stable:
            return self._close_position(
                symbol,
                spread_info,
                f"相关性崩溃: {correlation_info.correlation:.2f}",
            )

        # 保持仓位
        direction = (
            SignalDirection.LONG
            if arb_type == ArbitrageType.LONG_DOMESTIC
            else SignalDirection.SHORT
        )

        return StrategySignal(
            direction=direction,
            entry_price=self._current_opportunity.entry_price,
            target_price=self._current_opportunity.target_price,
            stop_price=self._current_opportunity.stop_price,
            confidence=self._current_opportunity.confidence,
            strength=min(1.0, abs(z_score) / self._config.stop_z_threshold),
            gap_info=None,
            timestamp=time.time(),
            reason="保持套利仓位",
        )

    def _close_position(
        self,
        symbol: str,
        spread_info: SpreadInfo,
        reason: str,
    ) -> StrategySignal:
        """平仓并进入冷却期.

        参数:
            symbol: 合约代码
            spread_info: 价差信息
            reason: 平仓原因

        返回:
            平仓信号
        """
        self._state = LinkageState.COOLDOWN
        self._cooldown_start = time.time()
        self._current_opportunity = None

        return StrategySignal(
            direction=SignalDirection.FLAT,
            entry_price=spread_info.domestic_price,
            target_price=spread_info.domestic_price,
            stop_price=spread_info.domestic_price,
            confidence=1.0,
            strength=0.0,
            gap_info=None,
            timestamp=time.time(),
            reason=reason,
        )

    # ========================================
    # 辅助方法
    # ========================================

    def _update_price_history(
        self,
        domestic: float,
        foreign: float,
    ) -> None:
        """更新价格历史.

        参数:
            domestic: 国内价格
            foreign: 国际价格
        """
        self._domestic_prices.append(domestic)
        self._foreign_prices.append(foreign)

        # 限制历史长度
        window = self._config.correlation_window
        if len(self._domestic_prices) > window:
            self._domestic_prices = self._domestic_prices[-window:]
            self._foreign_prices = self._foreign_prices[-window:]

    def _update_spread_statistics(self, spread: float) -> None:
        """更新价差统计量.

        参数:
            spread: 当前价差
        """
        self._spread_history.append(spread)

        # 限制历史长度
        window = self._config.spread_window
        if len(self._spread_history) > window:
            self._spread_history = self._spread_history[-window:]

        # 计算均值和标准差
        n = len(self._spread_history)
        if n < 2:
            self._spread_mean = spread
            self._spread_std = 0.0
            return

        self._spread_mean = sum(self._spread_history) / n
        variance = sum((s - self._spread_mean) ** 2 for s in self._spread_history) / n
        self._spread_std = math.sqrt(variance) if variance > 0 else 0.0

    def _calculate_z_score(self, spread: float) -> float:
        """计算价差Z分数.

        参数:
            spread: 当前价差

        返回:
            Z分数
        """
        if self._spread_std <= 0:
            return 0.0
        return (spread - self._spread_mean) / self._spread_std

    def _calculate_confidence(
        self,
        z_score: float,
        correlation: float,
        sample_count: int,
    ) -> float:
        """计算信号置信度.

        参数:
            z_score: Z分数
            correlation: 相关性
            sample_count: 样本数量

        返回:
            置信度 (0-1)
        """
        # 基础置信度
        confidence = 0.3

        # Z分数因子（越极端越有信心）
        z_factor = min(1.0, abs(z_score) / self._config.stop_z_threshold)
        confidence += z_factor * 0.25

        # 相关性因子
        corr_factor = max(0.0, correlation - self._config.min_correlation)
        corr_factor = corr_factor / (1.0 - self._config.min_correlation)
        confidence += corr_factor * 0.25

        # 样本数量因子
        sample_factor = min(1.0, sample_count / self._config.spread_window)
        confidence += sample_factor * 0.2

        return max(0.0, min(1.0, confidence))

    def _calculate_target_and_stop(
        self,
        current_price: float,
        current_spread: float,
        target_spread: float,
        stop_spread: float,
        direction: SignalDirection,
    ) -> tuple[float, float]:
        """计算目标价和止损价.

        参数:
            current_price: 当前价格
            current_spread: 当前价差
            target_spread: 目标价差
            stop_spread: 止损价差
            direction: 交易方向

        返回:
            (目标价, 止损价)
        """
        # 价差变化对应的价格变化
        target_price_change = target_spread - current_spread
        stop_price_change = stop_spread - current_spread

        if direction == SignalDirection.LONG:
            target_price = current_price + target_price_change
            stop_price = current_price + stop_price_change
        else:
            target_price = current_price - target_price_change
            stop_price = current_price - stop_price_change

        return target_price, stop_price

    def _is_in_cooldown(self, now: float) -> bool:
        """检查是否在冷却期.

        参数:
            now: 当前时间戳

        返回:
            是否在冷却期
        """
        if self._state != LinkageState.COOLDOWN:
            return False

        if self._cooldown_start is None:
            return False

        elapsed = now - self._cooldown_start
        if elapsed >= self._config.cooldown_seconds:
            # 冷却期结束
            self._state = LinkageState.MONITORING
            self._cooldown_start = None
            return False

        return True

    def _create_flat_signal(self, symbol: str) -> StrategySignal:
        """创建平仓信号.

        参数:
            symbol: 合约代码

        返回:
            平仓信号
        """
        return StrategySignal(
            direction=SignalDirection.FLAT,
            entry_price=0.0,
            target_price=0.0,
            stop_price=0.0,
            confidence=0.0,
            strength=0.0,
            gap_info=None,
            timestamp=time.time(),
            reason="无信号",
        )

    def _create_flat_signal_with_info(
        self,
        symbol: str,
        spread_info: SpreadInfo,
        reason: str,
    ) -> StrategySignal:
        """创建带信息的平仓信号.

        参数:
            symbol: 合约代码
            spread_info: 价差信息
            reason: 原因

        返回:
            平仓信号
        """
        return StrategySignal(
            direction=SignalDirection.FLAT,
            entry_price=spread_info.domestic_price,
            target_price=spread_info.domestic_price,
            stop_price=spread_info.domestic_price,
            confidence=0.0,
            strength=0.0,
            gap_info=None,
            timestamp=time.time(),
            reason=reason,
        )

    # ========================================
    # Strategy 接口实现
    # ========================================

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        """处理市场Tick数据.

        参数:
            state: 当前市场状态

        返回:
            目标投资组合
        """
        # 生成信号
        signal = self.generate_signal(state)

        # 获取国内合约代码
        domestic_symbol = self._linked_market.domestic_symbol

        # 转换信号为目标仓位
        target_qty = 0
        if signal.direction == SignalDirection.LONG:
            target_qty = self._config.max_position_per_leg
        elif signal.direction == SignalDirection.SHORT:
            target_qty = -self._config.max_position_per_leg

        # 更新仓位跟踪
        self._position = target_qty

        return TargetPortfolio(
            target_net_qty={domestic_symbol: target_qty} if target_qty != 0 else {},
            model_version=self.VERSION,
            features_hash=self._compute_features_hash(signal),
        )

    def _compute_features_hash(self, signal: StrategySignal) -> str:
        """计算特征哈希值.

        参数:
            signal: 策略信号

        返回:
            SHA256哈希值前16位
        """
        features = (
            f"{signal.entry_price:.6f}|"
            f"{signal.direction.value}|"
            f"{signal.confidence:.6f}|"
            f"{signal.timestamp:.0f}"
        )
        return hashlib.sha256(features.encode()).hexdigest()[:16]

    # ========================================
    # 属性访问
    # ========================================

    @property
    def state(self) -> LinkageState:
        """获取当前策略状态."""
        return self._state

    @property
    def config(self) -> InternationalLinkageConfig:
        """获取策略配置."""
        return self._config

    @property
    def linked_market(self) -> LinkedMarket:
        """获取联动市场配置."""
        return self._linked_market

    @property
    def current_opportunity(self) -> ArbitrageOpportunity | None:
        """获取当前套利机会."""
        return self._current_opportunity

    @property
    def spread_mean(self) -> float:
        """获取价差均值."""
        return self._spread_mean

    @property
    def spread_std(self) -> float:
        """获取价差标准差."""
        return self._spread_std

    @property
    def exchange_rate(self) -> float:
        """获取当前汇率."""
        return self._exchange_rate

    def get_state_dict(self) -> dict[str, Any]:
        """获取策略状态字典.

        返回:
            包含策略状态的字典
        """
        return {
            "strategy_id": self.STRATEGY_ID,
            "version": self.VERSION,
            "state": self._state.value,
            "product": self._product,
            "linked_market": {
                "product_name": self._linked_market.product_name,
                "domestic_symbol": self._linked_market.domestic_symbol,
                "foreign_symbol": self._linked_market.foreign_symbol,
                "exchange_rate_symbol": self._linked_market.exchange_rate_symbol,
                "unit_ratio": self._linked_market.unit_ratio,
            },
            "exchange_rate": self._exchange_rate,
            "spread_mean": round(self._spread_mean, 4),
            "spread_std": round(self._spread_std, 4),
            "sample_count": len(self._spread_history),
            "position": self._position,
            "current_opportunity": (
                self._current_opportunity.to_dict()
                if self._current_opportunity
                else None
            ),
            "config": {
                "entry_z_threshold": self._config.entry_z_threshold,
                "exit_z_threshold": self._config.exit_z_threshold,
                "stop_z_threshold": self._config.stop_z_threshold,
                "min_correlation": self._config.min_correlation,
                "correlation_window": self._config.correlation_window,
                "spread_window": self._config.spread_window,
                "min_confidence": self._config.min_confidence,
                "cooldown_seconds": self._config.cooldown_seconds,
                "max_position_per_leg": self._config.max_position_per_leg,
            },
        }

    def reset(self) -> None:
        """重置策略状态."""
        self._state = LinkageState.MONITORING
        self._current_opportunity = None
        self._domestic_prices.clear()
        self._foreign_prices.clear()
        self._spread_history.clear()
        self._spread_mean = 0.0
        self._spread_std = 0.0
        self._cooldown_start = None
        self._position = 0

    def create_trading_signal(
        self,
        symbol: str,
        strategy_signal: StrategySignal,
    ) -> TradingSignal:
        """创建M1合规的交易信号.

        参数:
            symbol: 合约代码
            strategy_signal: 策略信号

        返回:
            TradingSignal交易信号
        """
        return self._signal_source.create_signal(
            symbol=symbol,
            direction=strategy_signal.direction,
            strength=strategy_signal.strength,
            confidence=strategy_signal.confidence,
            signal_type=SignalType.ENTRY,
            priority=SignalPriority.NORMAL,
            metadata={
                "strategy": self.STRATEGY_ID,
                "product": self._product,
                "target_price": strategy_signal.target_price,
                "stop_price": strategy_signal.stop_price,
                "reason": strategy_signal.reason,
                "current_opportunity": (
                    self._current_opportunity.to_dict()
                    if self._current_opportunity
                    else None
                ),
            },
        )
