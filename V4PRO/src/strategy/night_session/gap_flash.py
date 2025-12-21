"""夜盘跳空闪电战策略 (军规级 v4.0).

V4PRO Platform Component - 夜盘跳空闪电战策略
V4 SPEC: M1军规 - 单一信号源, M15军规 - 夜盘跨日处理

策略逻辑:
1. 监测夜盘开盘跳空
2. 判断跳空方向和幅度
3. 结合国际市场走势验证
4. 快速入场捕捉跳空回补

军规覆盖:
- M1: 单一信号源 - 信号源唯一性保证
- M15: 夜盘跨日处理 - 夜盘时段特殊处理

示例:
    >>> from src.strategy.night_session import NightGapFlashStrategy
    >>> strategy = NightGapFlashStrategy(gap_threshold=0.01)
    >>> gap_info = strategy.detect_gap(prev_close=5000.0, open_price=5100.0)
    >>> print(gap_info.direction)
    GapDirection.UP
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar

from src.strategy.base import Strategy
from src.strategy.single_signal_source import (
    SignalDirection,
    SignalPriority,
    SignalSource,
    SignalType,
    TradingSignal,
    create_signal_source,
)
from src.strategy.types import Bar1m, MarketState, TargetPortfolio


class GapDirection(Enum):
    """跳空方向枚举.

    属性:
        UP: 向上跳空 (开盘价 > 前收盘价)
        DOWN: 向下跳空 (开盘价 < 前收盘价)
        NONE: 无跳空 (开盘价接近前收盘价)
    """

    UP = "UP"  # 向上跳空
    DOWN = "DOWN"  # 向下跳空
    NONE = "NONE"  # 无跳空


class StrategyState(Enum):
    """策略状态枚举.

    属性:
        WAITING: 等待跳空信号
        ACTIVE: 已入场，持有仓位
        CLOSED: 已平仓
        STOPPED: 止损触发
    """

    WAITING = "WAITING"  # 等待跳空信号
    ACTIVE = "ACTIVE"  # 已入场
    CLOSED = "CLOSED"  # 已平仓
    STOPPED = "STOPPED"  # 止损


@dataclass(frozen=True, slots=True)
class GapInfo:
    """跳空信息 (不可变).

    属性:
        direction: 跳空方向
        gap_size: 跳空幅度 (绝对值)
        gap_percent: 跳空百分比 (相对于前收盘价)
        prev_close: 前收盘价
        open_price: 开盘价
        timestamp: 检测时间戳
        is_significant: 是否为显著跳空 (超过阈值)
    """

    direction: GapDirection
    gap_size: float
    gap_percent: float
    prev_close: float
    open_price: float
    timestamp: float
    is_significant: bool

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于审计).

        返回:
            包含跳空信息的字典
        """
        return {
            "direction": self.direction.value,
            "gap_size": round(self.gap_size, 4),
            "gap_percent": round(self.gap_percent, 6),
            "prev_close": self.prev_close,
            "open_price": self.open_price,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "is_significant": self.is_significant,
        }


@dataclass(frozen=True, slots=True)
class MarketContext:
    """市场上下文信息 (不可变).

    属性:
        international_trend: 国际市场趋势 (-1到1, 正数表示看涨)
        volatility: 波动率
        volume_ratio: 成交量比率 (相对于平均)
        is_night_session: 是否为夜盘时段
        session_start_time: 交易时段开始时间
        correlation_score: 与国际市场相关性得分
    """

    international_trend: float
    volatility: float
    volume_ratio: float
    is_night_session: bool
    session_start_time: float
    correlation_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        返回:
            包含市场上下文的字典
        """
        return {
            "international_trend": round(self.international_trend, 4),
            "volatility": round(self.volatility, 6),
            "volume_ratio": round(self.volume_ratio, 4),
            "is_night_session": self.is_night_session,
            "session_start_time": self.session_start_time,
            "correlation_score": round(self.correlation_score, 4),
        }


@dataclass(frozen=True, slots=True)
class StrategySignal:
    """策略信号 (不可变).

    属性:
        direction: 信号方向 (LONG/SHORT/FLAT)
        entry_price: 建议入场价格
        target_price: 目标价格 (止盈)
        stop_price: 止损价格
        confidence: 置信度 (0-1)
        strength: 信号强度 (0-1)
        gap_info: 关联的跳空信息
        timestamp: 信号生成时间戳
        reason: 信号生成原因
    """

    direction: SignalDirection
    entry_price: float
    target_price: float
    stop_price: float
    confidence: float
    strength: float
    gap_info: GapInfo | None
    timestamp: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于审计).

        返回:
            包含策略信号的字典
        """
        return {
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_price": self.stop_price,
            "confidence": round(self.confidence, 4),
            "strength": round(self.strength, 4),
            "gap_info": self.gap_info.to_dict() if self.gap_info else None,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "reason": self.reason,
        }


class NightSessionStrategy(Strategy, ABC):
    """夜盘策略基类.

    提供夜盘策略的通用功能：
    - 夜盘时段检测
    - 跨日处理 (M15军规)
    - 信号源管理 (M1军规)
    """

    VERSION: ClassVar[str] = "1.0.0"

    def __init__(self, strategy_id: str = "night_session") -> None:
        """初始化夜盘策略基类.

        参数:
            strategy_id: 策略ID
        """
        self._strategy_id = strategy_id
        self._signal_source: SignalSource = create_signal_source(
            strategy_id=strategy_id
        )

    @property
    def signal_source(self) -> SignalSource:
        """获取信号源."""
        return self._signal_source

    @abstractmethod
    def on_tick(self, state: MarketState) -> TargetPortfolio:
        """处理市场Tick数据.

        参数:
            state: 当前市场状态

        返回:
            目标投资组合
        """
        raise NotImplementedError


class NightGapFlashStrategy(NightSessionStrategy):
    """夜盘跳空闪电战策略 (军规 M1, M15).

    策略逻辑:
    1. 监测夜盘开盘跳空
    2. 判断跳空方向和幅度
    3. 结合国际市场走势验证
    4. 快速入场捕捉跳空回补

    核心参数:
    - gap_threshold: 跳空阈值 (默认1%)
    - take_profit_ratio: 止盈比例 (默认50%回补)
    - stop_loss_ratio: 止损比例 (默认150%反向)
    - min_confidence: 最小置信度阈值
    """

    VERSION: ClassVar[str] = "1.0.0"
    STRATEGY_ID: ClassVar[str] = "night_gap_flash"

    # 默认配置
    DEFAULT_GAP_THRESHOLD: ClassVar[float] = 0.01  # 1%跳空阈值
    DEFAULT_TAKE_PROFIT_RATIO: ClassVar[float] = 0.5  # 50%回补止盈
    DEFAULT_STOP_LOSS_RATIO: ClassVar[float] = 1.5  # 150%反向止损
    DEFAULT_MIN_CONFIDENCE: ClassVar[float] = 0.6  # 最小置信度
    DEFAULT_MAX_HOLD_BARS: ClassVar[int] = 30  # 最大持仓K线数

    def __init__(
        self,
        gap_threshold: float = 0.01,
        take_profit_ratio: float = 0.5,
        stop_loss_ratio: float = 1.5,
        min_confidence: float = 0.6,
        max_hold_bars: int = 30,
        symbol: str = "",
    ) -> None:
        """初始化夜盘跳空闪电战策略.

        参数:
            gap_threshold: 跳空阈值 (默认1%)
            take_profit_ratio: 止盈比例 (相对于跳空幅度)
            stop_loss_ratio: 止损比例 (相对于跳空幅度)
            min_confidence: 最小置信度阈值
            max_hold_bars: 最大持仓K线数
            symbol: 交易合约代码
        """
        super().__init__(strategy_id=self.STRATEGY_ID)

        # 策略参数
        self.gap_threshold = max(0.001, min(0.1, gap_threshold))
        self.take_profit_ratio = max(0.1, min(1.0, take_profit_ratio))
        self.stop_loss_ratio = max(0.5, min(3.0, stop_loss_ratio))
        self.min_confidence = max(0.0, min(1.0, min_confidence))
        self.max_hold_bars = max(1, max_hold_bars)
        self.symbol = symbol

        # 状态变量
        self._state = StrategyState.WAITING
        self._current_gap: GapInfo | None = None
        self._current_signal: StrategySignal | None = None
        self._entry_bar_count: int = 0
        self._prev_close: float | None = None
        self._session_open_detected: bool = False

    def detect_gap(self, prev_close: float, open_price: float) -> GapInfo:
        """检测跳空.

        参数:
            prev_close: 前收盘价
            open_price: 开盘价

        返回:
            GapInfo跳空信息

        异常:
            ValueError: 价格无效
        """
        # 验证价格
        if prev_close <= 0 or open_price <= 0:
            raise ValueError(
                f"价格无效: prev_close={prev_close}, open_price={open_price}"
            )

        # 计算跳空
        gap_size = open_price - prev_close
        gap_percent = gap_size / prev_close

        # 判断跳空方向
        if gap_percent > self.gap_threshold:
            direction = GapDirection.UP
        elif gap_percent < -self.gap_threshold:
            direction = GapDirection.DOWN
        else:
            direction = GapDirection.NONE

        # 判断是否显著
        is_significant = abs(gap_percent) >= self.gap_threshold

        return GapInfo(
            direction=direction,
            gap_size=abs(gap_size),
            gap_percent=abs(gap_percent),
            prev_close=prev_close,
            open_price=open_price,
            timestamp=time.time(),
            is_significant=is_significant,
        )

    def should_enter(self, gap: GapInfo, market_context: MarketContext) -> bool:
        """判断是否应该入场.

        入场条件:
        1. 跳空必须显著 (超过阈值)
        2. 夜盘时段
        3. 国际市场趋势不与跳空方向一致 (预期回补)
        4. 波动率在合理范围内
        5. 成交量充足

        参数:
            gap: 跳空信息
            market_context: 市场上下文

        返回:
            是否应该入场
        """
        # 条件1: 跳空必须显著
        if not gap.is_significant:
            return False

        # 条件2: 必须是夜盘时段
        if not market_context.is_night_session:
            return False

        # 条件3: 国际市场趋势验证
        # 如果向上跳空，但国际市场看跌 -> 预期回补向下，可入场做空
        # 如果向下跳空，但国际市场看涨 -> 预期回补向上，可入场做多
        trend = market_context.international_trend
        if gap.direction == GapDirection.UP and trend >= 0.3:
            # 国际市场也看涨，跳空可能继续，不入场
            return False
        if gap.direction == GapDirection.DOWN and trend <= -0.3:
            # 国际市场也看跌，跳空可能继续，不入场
            return False

        # 条件4: 波动率检查 (避免极端波动)
        if market_context.volatility > 0.05:  # 5%以上波动率过高
            return False

        # 条件5: 成交量检查
        if market_context.volume_ratio < 0.5:  # 成交量过低
            return False

        return True

    def calculate_target(self, gap: GapInfo) -> float:
        """计算止盈目标价.

        目标价为跳空回补的一定比例。

        参数:
            gap: 跳空信息

        返回:
            目标价格
        """
        # 计算目标回补幅度
        target_move = gap.gap_size * self.take_profit_ratio

        if gap.direction == GapDirection.UP:
            # 向上跳空，做空，目标价向下
            return gap.open_price - target_move
        elif gap.direction == GapDirection.DOWN:
            # 向下跳空，做多，目标价向上
            return gap.open_price + target_move
        else:
            return gap.open_price

    def _calculate_stop_loss(self, gap: GapInfo) -> float:
        """计算止损价.

        止损价为跳空反向的一定比例。

        参数:
            gap: 跳空信息

        返回:
            止损价格
        """
        # 计算止损幅度
        stop_move = gap.gap_size * self.stop_loss_ratio

        if gap.direction == GapDirection.UP:
            # 向上跳空，做空，止损价向上
            return gap.open_price + stop_move
        elif gap.direction == GapDirection.DOWN:
            # 向下跳空，做多，止损价向下
            return gap.open_price - stop_move
        else:
            return gap.open_price

    def _calculate_confidence(
        self, gap: GapInfo, market_context: MarketContext
    ) -> float:
        """计算信号置信度.

        基于以下因素:
        1. 跳空幅度 (适中最佳)
        2. 国际市场反向程度
        3. 波动率
        4. 成交量
        5. 与国际市场相关性

        参数:
            gap: 跳空信息
            market_context: 市场上下文

        返回:
            置信度 (0-1)
        """
        confidence = 0.5  # 基础置信度

        # 跳空幅度因子 (1%-3%最佳)
        gap_factor = min(1.0, gap.gap_percent / 0.02)
        if gap.gap_percent > 0.03:
            gap_factor = max(0.3, 1.0 - (gap.gap_percent - 0.03) / 0.05)
        confidence += gap_factor * 0.2

        # 国际市场反向因子
        trend = market_context.international_trend
        if gap.direction == GapDirection.UP:
            # 向上跳空，国际市场越看跌越好
            trend_factor = max(0.0, -trend)
        else:
            # 向下跳空，国际市场越看涨越好
            trend_factor = max(0.0, trend)
        confidence += trend_factor * 0.15

        # 波动率因子 (低波动率更稳定)
        vol_factor = max(0.0, 1.0 - market_context.volatility / 0.03)
        confidence += vol_factor * 0.1

        # 成交量因子
        vol_ratio_factor = min(1.0, market_context.volume_ratio / 1.5)
        confidence += vol_ratio_factor * 0.05

        # 相关性因子
        corr_factor = market_context.correlation_score
        confidence += corr_factor * 0.05

        return max(0.0, min(1.0, confidence))

    def _calculate_strength(self, gap: GapInfo) -> float:
        """计算信号强度.

        基于跳空幅度计算。

        参数:
            gap: 跳空信息

        返回:
            信号强度 (0-1)
        """
        # 跳空越大，信号越强，但有上限
        strength = min(1.0, gap.gap_percent / 0.05)
        return max(0.0, strength)

    def generate_signal(
        self,
        prev_close: float,
        open_price: float,
        market_context: MarketContext,
    ) -> StrategySignal:
        """生成交易信号.

        参数:
            prev_close: 前收盘价
            open_price: 开盘价
            market_context: 市场上下文

        返回:
            StrategySignal策略信号
        """
        # 检测跳空
        gap = self.detect_gap(prev_close, open_price)

        # 判断是否入场
        if not self.should_enter(gap, market_context):
            return StrategySignal(
                direction=SignalDirection.FLAT,
                entry_price=open_price,
                target_price=open_price,
                stop_price=open_price,
                confidence=0.0,
                strength=0.0,
                gap_info=gap,
                timestamp=time.time(),
                reason="入场条件不满足",
            )

        # 计算信号参数
        target = self.calculate_target(gap)
        stop = self._calculate_stop_loss(gap)
        confidence = self._calculate_confidence(gap, market_context)
        strength = self._calculate_strength(gap)

        # 置信度检查
        if confidence < self.min_confidence:
            return StrategySignal(
                direction=SignalDirection.FLAT,
                entry_price=open_price,
                target_price=target,
                stop_price=stop,
                confidence=confidence,
                strength=strength,
                gap_info=gap,
                timestamp=time.time(),
                reason=f"置信度不足: {confidence:.2f} < {self.min_confidence:.2f}",
            )

        # 确定方向
        if gap.direction == GapDirection.UP:
            direction = SignalDirection.SHORT  # 做空回补
            reason = f"向上跳空{gap.gap_percent*100:.2f}%，做空捕捉回补"
        elif gap.direction == GapDirection.DOWN:
            direction = SignalDirection.LONG  # 做多回补
            reason = f"向下跳空{gap.gap_percent*100:.2f}%，做多捕捉回补"
        else:
            direction = SignalDirection.FLAT
            reason = "无显著跳空"

        return StrategySignal(
            direction=direction,
            entry_price=open_price,
            target_price=target,
            stop_price=stop,
            confidence=confidence,
            strength=strength,
            gap_info=gap,
            timestamp=time.time(),
            reason=reason,
        )

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        """处理市场Tick数据.

        参数:
            state: 当前市场状态

        返回:
            目标投资组合
        """
        if not self.symbol:
            return self._make_flat_portfolio()

        # 获取价格
        current_price = state.prices.get(self.symbol, 0.0)
        if current_price <= 0:
            return self._make_flat_portfolio()

        # 获取K线数据
        bars = state.bars_1m.get(self.symbol, [])
        if not bars:
            return self._make_flat_portfolio()

        # 处理状态机
        target_qty = self._process_state(current_price, bars)

        return TargetPortfolio(
            target_net_qty={self.symbol: target_qty} if target_qty != 0 else {},
            model_version=self.VERSION,
            features_hash=self._compute_features_hash(current_price),
        )

    def _process_state(
        self, current_price: float, bars: list[Bar1m] | Any
    ) -> int:
        """处理策略状态机.

        参数:
            current_price: 当前价格
            bars: K线数据

        返回:
            目标仓位
        """
        if self._state == StrategyState.WAITING:
            return self._handle_waiting_state(bars)
        elif self._state == StrategyState.ACTIVE:
            return self._handle_active_state(current_price)
        else:
            return 0

    def _handle_waiting_state(self, bars: list[Bar1m] | Any) -> int:
        """处理等待状态.

        参数:
            bars: K线数据

        返回:
            目标仓位
        """
        # 需要至少2根K线
        if len(bars) < 2:
            return 0

        # 检测是否为交易时段开始 (简化逻辑)
        if not self._session_open_detected:
            # 记录前收盘价
            self._prev_close = bars[-2]["close"]
            self._session_open_detected = True

        # 检测跳空 (使用第一根K线的开盘价)
        if self._prev_close is None:
            return 0

        open_price = bars[-1]["open"]

        # 创建简化的市场上下文
        market_context = MarketContext(
            international_trend=0.0,  # 默认中性
            volatility=0.02,  # 默认2%波动
            volume_ratio=1.0,  # 默认正常成交量
            is_night_session=True,  # 假设是夜盘
            session_start_time=time.time(),
            correlation_score=0.5,
        )

        # 生成信号
        signal = self.generate_signal(self._prev_close, open_price, market_context)

        if signal.direction != SignalDirection.FLAT:
            self._current_gap = signal.gap_info
            self._current_signal = signal
            self._state = StrategyState.ACTIVE
            self._entry_bar_count = 0

            # 返回目标仓位
            if signal.direction == SignalDirection.LONG:
                return 1
            elif signal.direction == SignalDirection.SHORT:
                return -1

        return 0

    def _handle_active_state(self, current_price: float) -> int:
        """处理持仓状态.

        参数:
            current_price: 当前价格

        返回:
            目标仓位
        """
        if self._current_signal is None:
            self._state = StrategyState.WAITING
            return 0

        self._entry_bar_count += 1

        # 检查止盈
        if self._current_signal.direction == SignalDirection.LONG:
            if current_price >= self._current_signal.target_price:
                self._state = StrategyState.CLOSED
                self._reset()
                return 0
            if current_price <= self._current_signal.stop_price:
                self._state = StrategyState.STOPPED
                self._reset()
                return 0
        elif self._current_signal.direction == SignalDirection.SHORT:
            if current_price <= self._current_signal.target_price:
                self._state = StrategyState.CLOSED
                self._reset()
                return 0
            if current_price >= self._current_signal.stop_price:
                self._state = StrategyState.STOPPED
                self._reset()
                return 0

        # 检查最大持仓时间
        if self._entry_bar_count >= self.max_hold_bars:
            self._state = StrategyState.CLOSED
            self._reset()
            return 0

        # 保持仓位
        if self._current_signal.direction == SignalDirection.LONG:
            return 1
        elif self._current_signal.direction == SignalDirection.SHORT:
            return -1

        return 0

    def _reset(self) -> None:
        """重置策略状态."""
        self._current_gap = None
        self._current_signal = None
        self._entry_bar_count = 0
        self._prev_close = None
        self._session_open_detected = False
        self._state = StrategyState.WAITING

    def _make_flat_portfolio(self) -> TargetPortfolio:
        """创建空仓投资组合.

        返回:
            空仓目标投资组合
        """
        return TargetPortfolio(
            target_net_qty={},
            model_version=self.VERSION,
            features_hash="flat",
        )

    def _compute_features_hash(self, price: float) -> str:
        """计算特征哈希值.

        参数:
            price: 当前价格

        返回:
            SHA256哈希值前16位
        """
        features = f"{price:.6f}|{self._state.value}|{time.time():.0f}"
        return hashlib.sha256(features.encode()).hexdigest()[:16]

    def create_trading_signal(
        self, symbol: str, strategy_signal: StrategySignal
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
                "gap_info": (
                    strategy_signal.gap_info.to_dict()
                    if strategy_signal.gap_info
                    else None
                ),
                "target_price": strategy_signal.target_price,
                "stop_price": strategy_signal.stop_price,
                "reason": strategy_signal.reason,
            },
        )

    # === 属性访问 ===

    @property
    def state(self) -> StrategyState:
        """获取当前策略状态."""
        return self._state

    @property
    def current_gap(self) -> GapInfo | None:
        """获取当前跳空信息."""
        return self._current_gap

    @property
    def current_signal(self) -> StrategySignal | None:
        """获取当前策略信号."""
        return self._current_signal

    def get_state_dict(self) -> dict[str, Any]:
        """获取策略状态字典.

        返回:
            包含策略状态的字典
        """
        return {
            "strategy_id": self.STRATEGY_ID,
            "version": self.VERSION,
            "state": self._state.value,
            "symbol": self.symbol,
            "gap_threshold": self.gap_threshold,
            "take_profit_ratio": self.take_profit_ratio,
            "stop_loss_ratio": self.stop_loss_ratio,
            "min_confidence": self.min_confidence,
            "max_hold_bars": self.max_hold_bars,
            "entry_bar_count": self._entry_bar_count,
            "current_gap": (
                self._current_gap.to_dict() if self._current_gap else None
            ),
            "current_signal": (
                self._current_signal.to_dict() if self._current_signal else None
            ),
        }
