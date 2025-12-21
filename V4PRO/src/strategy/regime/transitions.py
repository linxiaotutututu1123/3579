"""
市场状态转换逻辑模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: D7-P0 市场状态引擎

军规覆盖:
- M3: 状态转换审计日志
- M6: 极端状态触发熔断检查

功能特性:
- 状态转换规则定义
- 转换条件检测
- 转换历史追踪
- 状态持续性验证

示例:
    >>> from src.strategy.regime.transitions import TransitionEngine
    >>> engine = TransitionEngine()
    >>> new_state = engine.evaluate_transition(current_state, indicators)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from src.strategy.regime.indicators import IndicatorResult
from src.strategy.regime.states import (
    MarketRegime,
    RegimeConfig,
    RegimeState,
    RegimeStrength,
    RegimeTransition,
    TrendDirection,
)


if TYPE_CHECKING:
    pass


class AuditLogger(Protocol):
    """审计日志协议.

    M3军规: 所有状态转换必须写入审计日志.
    """

    def log(
        self,
        event_type: str,
        from_state: str,
        to_state: str,
        trigger_reason: str,
        details: dict[str, Any],
    ) -> None:
        """记录审计日志."""
        ...


class CircuitBreakerCallback(Protocol):
    """熔断器回调协议.

    M6军规: 极端状态触发熔断检查.
    """

    def on_extreme_regime(self, regime_state: RegimeState) -> None:
        """极端状态回调."""
        ...


@dataclass
class TransitionRule:
    """状态转换规则.

    属性:
        from_states: 允许的源状态列表
        to_state: 目标状态
        condition_name: 条件名称
        priority: 规则优先级 (越小越高)
    """

    from_states: tuple[MarketRegime, ...]
    to_state: MarketRegime
    condition_name: str
    priority: int = 0

    def matches_source(self, current: MarketRegime) -> bool:
        """检查是否匹配源状态."""
        return current in self.from_states


@dataclass
class TransitionCondition:
    """转换条件检测结果.

    属性:
        should_transition: 是否应该转换
        target_regime: 目标状态
        confidence: 置信度
        reasons: 触发原因列表
        indicators: 触发指标值
    """

    should_transition: bool = False
    target_regime: MarketRegime | None = None
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    indicators: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "should_transition": self.should_transition,
            "target_regime": self.target_regime.name if self.target_regime else None,
            "confidence": round(self.confidence, 4),
            "reasons": self.reasons,
            "indicators": {k: round(v, 4) for k, v in self.indicators.items()},
        }


class TransitionEngine:
    """状态转换引擎.

    V4 SPEC D7-P0: 状态转换检测

    功能:
    - 基于波动率的转换检测
    - 基于成交量的转换检测
    - 基于价格模式的转换检测
    - 转换历史追踪
    - 审计日志支持 (M3军规)

    军规合规:
    - M3: 每次转换记录审计日志
    - M6: 极端状态触发熔断检查
    """

    # 状态持续计数阈值
    MIN_REGIME_DURATION: ClassVar[int] = 3

    def __init__(
        self,
        config: RegimeConfig | None = None,
        audit_logger: AuditLogger | None = None,
        circuit_breaker_callback: CircuitBreakerCallback | None = None,
    ) -> None:
        """初始化转换引擎.

        Args:
            config: 状态检测配置
            audit_logger: 审计日志记录器 (M3军规)
            circuit_breaker_callback: 熔断器回调 (M6军规)
        """
        self._config = config or RegimeConfig()
        self._audit_logger = audit_logger
        self._circuit_breaker_callback = circuit_breaker_callback

        # 当前状态
        self._current_regime: MarketRegime = MarketRegime.RANGING
        self._regime_duration: int = 0
        self._last_transition_time: float = time.time()

        # 转换历史
        self._transition_history: deque[RegimeTransition] = deque(maxlen=100)
        self._transition_count: int = 0

        # 状态稳定性检测
        self._regime_votes: deque[MarketRegime] = deque(maxlen=self.MIN_REGIME_DURATION)

    @property
    def current_regime(self) -> MarketRegime:
        """当前市场状态."""
        return self._current_regime

    @property
    def regime_duration(self) -> int:
        """当前状态持续周期数."""
        return self._regime_duration

    @property
    def transition_count(self) -> int:
        """转换次数."""
        return self._transition_count

    @property
    def transition_history(self) -> list[RegimeTransition]:
        """转换历史."""
        return list(self._transition_history)

    def evaluate_transition(
        self,
        indicators: IndicatorResult,
    ) -> tuple[MarketRegime, float, list[str]]:
        """评估是否需要状态转换.

        Args:
            indicators: 指标计算结果

        Returns:
            (目标状态, 置信度, 原因列表) 元组
        """
        if not indicators.is_valid:
            return self._current_regime, 0.5, ["指标无效"]

        # 检测各类条件
        extreme_condition = self._check_extreme_condition(indicators)
        volatile_condition = self._check_volatile_condition(indicators)
        trending_condition = self._check_trending_condition(indicators)
        ranging_condition = self._check_ranging_condition(indicators)

        # 按优先级选择目标状态
        # 极端 > 高波动 > 趋势 > 震荡
        conditions = [
            (extreme_condition, 0),
            (volatile_condition, 1),
            (trending_condition, 2),
            (ranging_condition, 3),
        ]

        best_condition: TransitionCondition | None = None
        for condition, _priority in conditions:
            if condition.should_transition and condition.confidence > 0.4:
                if (
                    best_condition is None
                    or condition.confidence > best_condition.confidence
                ):
                    best_condition = condition

        if best_condition and best_condition.target_regime:
            target = best_condition.target_regime
            confidence = best_condition.confidence
            reasons = best_condition.reasons
        else:
            # 保持当前状态
            target = self._current_regime
            confidence = 0.5
            reasons = ["无明确状态信号"]

        return target, confidence, reasons

    def update_state(
        self,
        indicators: IndicatorResult,
    ) -> RegimeState:
        """更新状态 (带转换检测).

        Args:
            indicators: 指标计算结果

        Returns:
            新的市场状态
        """
        target, confidence, reasons = self.evaluate_transition(indicators)

        # 投票机制确保状态稳定性
        self._regime_votes.append(target)

        # 检查是否应该转换
        should_transition = self._should_execute_transition(target, confidence)

        if should_transition and target != self._current_regime:
            self._execute_transition(target, confidence, reasons, indicators)
        else:
            self._regime_duration += 1

        # 构建状态对象
        trend_direction = self._determine_trend_direction(indicators)
        strength = RegimeStrength.from_confidence(confidence)

        state = RegimeState(
            regime=self._current_regime,
            strength=strength,
            confidence=confidence,
            trend_direction=trend_direction,
            volatility_percentile=indicators.volatility_percentile,
            volume_percentile=indicators.volume_percentile,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            metadata={
                "duration": self._regime_duration,
                "reasons": reasons,
                "indicators": indicators.to_dict(),
            },
        )

        return state

    def _check_extreme_condition(
        self,
        indicators: IndicatorResult,
    ) -> TransitionCondition:
        """检测极端状态条件.

        Args:
            indicators: 指标结果

        Returns:
            转换条件
        """
        reasons: list[str] = []
        score = 0.0

        # 波动率极端高
        if indicators.volatility_percentile > 95:
            reasons.append(f"波动率百分位极高: {indicators.volatility_percentile:.1f}")
            score += 0.4

        # ATR极端高
        if indicators.atr_percentile > 95:
            reasons.append(f"ATR百分位极高: {indicators.atr_percentile:.1f}")
            score += 0.3

        # 成交量激增
        if indicators.volume_ratio > self._config.volume_surge_threshold * 1.5:
            reasons.append(f"成交量激增: {indicators.volume_ratio:.2f}x")
            score += 0.2

        # 价格区间异常
        if indicators.price_range_ratio > self._config.atr_multiplier_extreme:
            reasons.append(f"价格区间异常: {indicators.price_range_ratio:.2f}x")
            score += 0.2

        should_transition = score >= 0.5
        confidence = min(score, 1.0)

        return TransitionCondition(
            should_transition=should_transition,
            target_regime=MarketRegime.EXTREME if should_transition else None,
            confidence=confidence,
            reasons=reasons,
            indicators={
                "volatility_percentile": indicators.volatility_percentile,
                "atr_percentile": indicators.atr_percentile,
                "volume_ratio": indicators.volume_ratio,
                "price_range_ratio": indicators.price_range_ratio,
            },
        )

    def _check_volatile_condition(
        self,
        indicators: IndicatorResult,
    ) -> TransitionCondition:
        """检测高波动状态条件.

        Args:
            indicators: 指标结果

        Returns:
            转换条件
        """
        reasons: list[str] = []
        score = 0.0

        # 波动率偏高
        if indicators.volatility_percentile > 75:
            reasons.append(f"波动率偏高: {indicators.volatility_percentile:.1f}")
            score += 0.3

        # ATR偏高
        if indicators.atr_percentile > 75:
            reasons.append(f"ATR偏高: {indicators.atr_percentile:.1f}")
            score += 0.2

        # ADX不高 (无明确趋势)
        if indicators.adx < self._config.trend_strength_threshold * 100:
            reasons.append(f"无明确趋势: ADX={indicators.adx:.1f}")
            score += 0.2

        # 价格区间较大
        if indicators.price_range_ratio > self._config.atr_multiplier_volatile:
            reasons.append(f"区间较大: {indicators.price_range_ratio:.2f}x")
            score += 0.2

        should_transition = score >= 0.5
        confidence = min(score, 1.0)

        return TransitionCondition(
            should_transition=should_transition,
            target_regime=MarketRegime.VOLATILE if should_transition else None,
            confidence=confidence,
            reasons=reasons,
            indicators={
                "volatility_percentile": indicators.volatility_percentile,
                "adx": indicators.adx,
                "price_range_ratio": indicators.price_range_ratio,
            },
        )

    def _check_trending_condition(
        self,
        indicators: IndicatorResult,
    ) -> TransitionCondition:
        """检测趋势状态条件.

        Args:
            indicators: 指标结果

        Returns:
            转换条件
        """
        reasons: list[str] = []
        score = 0.0

        # ADX较高
        adx_threshold = self._config.trend_strength_threshold * 100
        if indicators.adx > adx_threshold:
            reasons.append(f"趋势强度高: ADX={indicators.adx:.1f}")
            score += 0.4

        # DI有明确方向
        di_diff = abs(indicators.plus_di - indicators.minus_di)
        if di_diff > 10:
            direction = "上涨" if indicators.plus_di > indicators.minus_di else "下跌"
            reasons.append(f"方向明确: {direction}, DI差={di_diff:.1f}")
            score += 0.3

        # 趋势强度指标
        if indicators.trend_strength > 0.5:
            reasons.append(f"趋势强度: {indicators.trend_strength:.2f}")
            score += 0.2

        # 波动率适中
        if 30 < indicators.volatility_percentile < 75:
            reasons.append(f"波动率适中: {indicators.volatility_percentile:.1f}")
            score += 0.1

        should_transition = score >= 0.5
        confidence = min(score, 1.0)

        return TransitionCondition(
            should_transition=should_transition,
            target_regime=MarketRegime.TRENDING if should_transition else None,
            confidence=confidence,
            reasons=reasons,
            indicators={
                "adx": indicators.adx,
                "plus_di": indicators.plus_di,
                "minus_di": indicators.minus_di,
                "trend_strength": indicators.trend_strength,
            },
        )

    def _check_ranging_condition(
        self,
        indicators: IndicatorResult,
    ) -> TransitionCondition:
        """检测震荡状态条件.

        Args:
            indicators: 指标结果

        Returns:
            转换条件
        """
        reasons: list[str] = []
        score = 0.0

        # ADX较低
        adx_threshold = self._config.ranging_threshold * 100
        if indicators.adx < adx_threshold:
            reasons.append(f"无趋势: ADX={indicators.adx:.1f}")
            score += 0.4

        # DI无明确方向
        di_diff = abs(indicators.plus_di - indicators.minus_di)
        if di_diff < 10:
            reasons.append(f"方向不明: DI差={di_diff:.1f}")
            score += 0.2

        # 波动率正常或偏低
        if indicators.volatility_percentile < 60:
            reasons.append(f"波动率正常: {indicators.volatility_percentile:.1f}")
            score += 0.2

        # 价格区间正常
        if indicators.price_range_ratio < self._config.atr_multiplier_volatile:
            reasons.append(f"区间正常: {indicators.price_range_ratio:.2f}x")
            score += 0.1

        # 突破得分接近0
        if abs(indicators.breakout_score) < 0.3:
            reasons.append(f"无突破: 得分={indicators.breakout_score:.2f}")
            score += 0.1

        should_transition = score >= 0.4
        confidence = min(score, 1.0)

        return TransitionCondition(
            should_transition=should_transition,
            target_regime=MarketRegime.RANGING if should_transition else None,
            confidence=confidence,
            reasons=reasons,
            indicators={
                "adx": indicators.adx,
                "volatility_percentile": indicators.volatility_percentile,
                "breakout_score": indicators.breakout_score,
            },
        )

    def _should_execute_transition(
        self,
        target: MarketRegime,
        confidence: float,
    ) -> bool:
        """判断是否应该执行转换.

        Args:
            target: 目标状态
            confidence: 置信度

        Returns:
            是否应该转换
        """
        # 置信度门槛
        if confidence < 0.5:
            return False

        # 状态持续性检查 (避免频繁切换)
        if self._regime_duration < self._config.min_regime_duration:
            # 除非是转向极端状态
            if target != MarketRegime.EXTREME:
                return False

        # 投票一致性检查
        if len(self._regime_votes) >= self.MIN_REGIME_DURATION:
            vote_counts = {}
            for vote in self._regime_votes:
                vote_counts[vote] = vote_counts.get(vote, 0) + 1

            # 需要超过半数投票一致
            majority = len(self._regime_votes) // 2 + 1
            if vote_counts.get(target, 0) < majority:
                return False

        return True

    def _execute_transition(
        self,
        target: MarketRegime,
        confidence: float,
        reasons: list[str],
        indicators: IndicatorResult,
    ) -> None:
        """执行状态转换.

        Args:
            target: 目标状态
            confidence: 置信度
            reasons: 触发原因
            indicators: 指标值
        """
        from_state = self._current_regime
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        # 创建转换记录
        transition = RegimeTransition(
            from_state=from_state,
            to_state=target,
            trigger_reason="; ".join(reasons),
            trigger_indicators=indicators.to_dict(),
            timestamp=timestamp,
        )

        # 更新状态
        self._current_regime = target
        self._regime_duration = 0
        self._transition_count += 1
        self._last_transition_time = time.time()
        self._transition_history.append(transition)

        # M3军规: 审计日志
        if self._audit_logger:
            self._audit_logger.log(
                event_type="REGIME_TRANSITION",
                from_state=from_state.name,
                to_state=target.name,
                trigger_reason="; ".join(reasons),
                details={
                    "confidence": confidence,
                    "indicators": indicators.to_dict(),
                    "transition_count": self._transition_count,
                },
            )

        # M6军规: 极端状态触发熔断检查
        if target == MarketRegime.EXTREME and self._circuit_breaker_callback:
            regime_state = RegimeState(
                regime=target,
                strength=RegimeStrength.from_confidence(confidence),
                confidence=confidence,
                volatility_percentile=indicators.volatility_percentile,
                volume_percentile=indicators.volume_percentile,
                timestamp=timestamp,
            )
            self._circuit_breaker_callback.on_extreme_regime(regime_state)

    def _determine_trend_direction(
        self,
        indicators: IndicatorResult,
    ) -> TrendDirection:
        """确定趋势方向.

        Args:
            indicators: 指标结果

        Returns:
            趋势方向
        """
        if self._current_regime != MarketRegime.TRENDING:
            return TrendDirection.NEUTRAL

        if indicators.trend_direction > 0:
            return TrendDirection.UP
        if indicators.trend_direction < 0:
            return TrendDirection.DOWN

        return TrendDirection.NEUTRAL

    def force_state(
        self,
        regime: MarketRegime,
        reason: str = "forced",
    ) -> None:
        """强制设置状态 (仅用于测试/恢复).

        Args:
            regime: 目标状态
            reason: 原因
        """
        from_state = self._current_regime
        self._current_regime = regime
        self._regime_duration = 0
        self._transition_count += 1
        self._regime_votes.clear()

        if self._audit_logger:
            self._audit_logger.log(
                event_type="REGIME_FORCE",
                from_state=from_state.name,
                to_state=regime.name,
                trigger_reason=f"force:{reason}",
                details={"forced": True},
            )

    def reset(self) -> None:
        """重置引擎状态."""
        self._current_regime = MarketRegime.RANGING
        self._regime_duration = 0
        self._transition_count = 0
        self._transition_history.clear()
        self._regime_votes.clear()
        self._last_transition_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "current_regime": self._current_regime.name,
            "regime_duration": self._regime_duration,
            "transition_count": self._transition_count,
            "last_transition_time": self._last_transition_time,
            "config": self._config.to_dict(),
        }


# ============================================================
# 便捷函数
# ============================================================


def create_transition_engine(
    config: RegimeConfig | None = None,
    audit_logger: AuditLogger | None = None,
) -> TransitionEngine:
    """创建转换引擎.

    Args:
        config: 状态配置
        audit_logger: 审计日志记录器

    Returns:
        转换引擎实例
    """
    return TransitionEngine(config=config, audit_logger=audit_logger)
