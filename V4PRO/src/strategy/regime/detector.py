"""
市场状态检测器模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: D7-P0 市场状态引擎

军规覆盖:
- M1: 单一信号源 - 状态输出为策略权重调整依据
- M6: 熔断保护联动 - 极端状态触发熔断检查
- M19: 风险归因 - 状态贡献度追踪

功能特性:
- 统一状态检测接口
- 与策略联邦集成
- 状态-策略权重映射
- 审计日志完整记录

示例:
    >>> from src.strategy.regime import MarketRegimeDetector
    >>> detector = MarketRegimeDetector()
    >>> state = detector.detect(prices)
    >>> weight_multiplier = detector.get_strategy_weight("trend_following")
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import numpy as np

from src.strategy.regime.indicators import IndicatorConfig, RegimeIndicators
from src.strategy.regime.states import (
    MarketRegime,
    RegimeConfig,
    RegimeState,
    RegimeTransition,
    create_regime_state,
    get_strategy_weight_multiplier,
)
from src.strategy.regime.transitions import TransitionEngine


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from src.strategy.types import Bar1m


class AuditLogger(Protocol):
    """审计日志协议."""

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


class CircuitBreakerInterface(Protocol):
    """熔断器接口协议.

    M6军规: 与熔断器联动.
    """

    def check_extreme_conditions(self, regime_state: RegimeState) -> bool:
        """检查极端条件.

        Args:
            regime_state: 市场状态

        Returns:
            是否应该触发熔断
        """
        ...


class FederationInterface(Protocol):
    """策略联邦接口协议.

    M1军规: 与策略联邦集成.
    """

    def update_regime_weights(
        self,
        regime: MarketRegime,
        weight_multipliers: dict[str, float],
    ) -> None:
        """更新状态权重.

        Args:
            regime: 市场状态
            weight_multipliers: 策略权重乘数
        """
        ...


@dataclass
class DetectorConfig:
    """检测器配置.

    属性:
        regime_config: 状态检测配置
        indicator_config: 指标计算配置
        enable_federation_integration: 是否启用联邦集成
        enable_circuit_breaker_check: 是否启用熔断检查
        history_size: 状态历史大小
    """

    regime_config: RegimeConfig = field(default_factory=RegimeConfig)
    indicator_config: IndicatorConfig = field(default_factory=IndicatorConfig)
    enable_federation_integration: bool = True
    enable_circuit_breaker_check: bool = True
    history_size: int = 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "regime_config": self.regime_config.to_dict(),
            "indicator_config": self.indicator_config.to_dict(),
            "enable_federation_integration": self.enable_federation_integration,
            "enable_circuit_breaker_check": self.enable_circuit_breaker_check,
            "history_size": self.history_size,
        }


class MarketRegimeDetector:
    """市场状态检测器.

    V4 SPEC D7-P0: 市场状态引擎核心

    功能:
    - 从价格/成交量数据检测市场状态
    - 与策略联邦集成，输出权重调整
    - 与熔断器联动，极端状态触发检查
    - 完整审计日志支持

    军规合规:
    - M1: 单一信号源 - 状态为策略权重调整的唯一依据
    - M6: 熔断保护 - 极端状态触发熔断检查
    - M19: 风险归因 - 状态贡献度追踪

    示例:
        >>> detector = MarketRegimeDetector()
        >>> bars = [{"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}]
        >>> state = detector.detect_from_bars(bars)
        >>> weight = detector.get_strategy_weight("trend_following")
    """

    # 最小数据长度
    MIN_BARS_REQUIRED: ClassVar[int] = 30

    def __init__(
        self,
        config: DetectorConfig | None = None,
        audit_logger: AuditLogger | None = None,
        federation: FederationInterface | None = None,
        circuit_breaker: CircuitBreakerInterface | None = None,
    ) -> None:
        """初始化检测器.

        Args:
            config: 检测器配置
            audit_logger: 审计日志记录器
            federation: 策略联邦接口 (M1军规)
            circuit_breaker: 熔断器接口 (M6军规)
        """
        self._config = config or DetectorConfig()
        self._audit_logger = audit_logger
        self._federation = federation
        self._circuit_breaker = circuit_breaker

        # 核心组件
        self._indicators = RegimeIndicators(self._config.indicator_config)
        self._transition_engine = TransitionEngine(
            config=self._config.regime_config,
            audit_logger=audit_logger,
            circuit_breaker_callback=self._on_extreme_regime,
        )

        # 状态历史
        self._state_history: deque[RegimeState] = deque(
            maxlen=self._config.history_size
        )

        # 统计
        self._detection_count: int = 0
        self._extreme_count: int = 0
        self._last_detection_time: float = 0.0

        # 策略权重缓存
        self._strategy_weights: dict[str, float] = {}
        self._weights_last_update: float = 0.0

        # 回调
        self._on_regime_change_callbacks: list[
            Callable[[RegimeState, RegimeState | None], None]
        ] = []

    @property
    def current_regime(self) -> MarketRegime:
        """当前市场状态."""
        return self._transition_engine.current_regime

    @property
    def current_state(self) -> RegimeState | None:
        """当前状态对象."""
        if self._state_history:
            return self._state_history[-1]
        return None

    @property
    def detection_count(self) -> int:
        """检测次数."""
        return self._detection_count

    @property
    def extreme_count(self) -> int:
        """极端状态次数."""
        return self._extreme_count

    def detect(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray | None = None,
    ) -> RegimeState:
        """检测市场状态.

        Args:
            high: 最高价数组
            low: 最低价数组
            close: 收盘价数组
            volume: 成交量数组 (可选)

        Returns:
            市场状态
        """
        self._detection_count += 1
        self._last_detection_time = time.time()

        # 计算指标
        indicators = self._indicators.calculate(high, low, close, volume)

        # 更新状态
        state = self._transition_engine.update_state(indicators)

        # 记录历史
        previous_state = self._state_history[-1] if self._state_history else None
        self._state_history.append(state)

        # 统计极端状态
        if state.regime == MarketRegime.EXTREME:
            self._extreme_count += 1

        # 检测状态变化
        if previous_state and previous_state.regime != state.regime:
            self._on_regime_changed(state, previous_state)

        # 更新策略权重
        self._update_strategy_weights(state)

        return state

    def detect_from_bars(
        self,
        bars: Sequence[Mapping[str, float] | Bar1m],
    ) -> RegimeState:
        """从K线数据检测市场状态.

        Args:
            bars: K线数据列表 (dict或Bar1m)

        Returns:
            市场状态
        """
        if len(bars) < self.MIN_BARS_REQUIRED:
            return create_regime_state(
                regime=self.current_regime,
                confidence=0.3,
                volatility_percentile=50.0,
                volume_percentile=50.0,
            )

        # 提取价格数据
        high = np.array([b["high"] for b in bars])
        low = np.array([b["low"] for b in bars])
        close = np.array([b["close"] for b in bars])

        # 提取成交量 (如果有)
        volume = None
        if "volume" in bars[0]:
            volume = np.array([b.get("volume", 0) for b in bars])

        return self.detect(high, low, close, volume)

    def get_strategy_weight(self, strategy_type: str) -> float:
        """获取策略权重乘数.

        M1军规: 策略权重由状态决定

        Args:
            strategy_type: 策略类型 (trend/mean_reversion/arbitrage/ml)

        Returns:
            权重乘数
        """
        current_state = self.current_state
        if current_state is None:
            return 1.0

        return get_strategy_weight_multiplier(strategy_type, current_state)

    def get_all_strategy_weights(self) -> dict[str, float]:
        """获取所有策略类型的权重.

        Returns:
            策略类型 -> 权重乘数 字典
        """
        current_state = self.current_state
        if current_state is None:
            return {
                "trend_following": 1.0,
                "mean_reversion": 1.0,
                "arbitrage": 1.0,
                "ml": 1.0,
            }

        return {
            "trend_following": get_strategy_weight_multiplier("trend_following", current_state),
            "mean_reversion": get_strategy_weight_multiplier("mean_reversion", current_state),
            "arbitrage": get_strategy_weight_multiplier("arbitrage", current_state),
            "ml": get_strategy_weight_multiplier("ml", current_state),
        }

    def register_regime_change_callback(
        self,
        callback: Callable[[RegimeState, RegimeState | None], None],
    ) -> None:
        """注册状态变化回调.

        Args:
            callback: 回调函数 (新状态, 旧状态)
        """
        self._on_regime_change_callbacks.append(callback)

    def get_state_history(self, limit: int = 10) -> list[RegimeState]:
        """获取状态历史.

        Args:
            limit: 返回数量限制

        Returns:
            状态历史列表
        """
        history = list(self._state_history)
        return history[-limit:]

    def get_transition_history(self, limit: int = 10) -> list[RegimeTransition]:
        """获取转换历史.

        Args:
            limit: 返回数量限制

        Returns:
            转换历史列表
        """
        return self._transition_engine.transition_history[-limit:]

    def get_regime_distribution(self) -> dict[str, float]:
        """获取状态分布.

        Returns:
            状态 -> 占比 字典
        """
        if not self._state_history:
            return {}

        counts: dict[MarketRegime, int] = {}
        for state in self._state_history:
            counts[state.regime] = counts.get(state.regime, 0) + 1

        total = len(self._state_history)
        return {
            regime.name: count / total
            for regime, count in counts.items()
        }

    def _on_regime_changed(
        self,
        new_state: RegimeState,
        old_state: RegimeState,
    ) -> None:
        """状态变化处理.

        Args:
            new_state: 新状态
            old_state: 旧状态
        """
        # 通知回调
        for callback in self._on_regime_change_callbacks:
            try:
                callback(new_state, old_state)
            except Exception:
                pass  # 忽略回调错误

        # 审计日志
        if self._audit_logger:
            self._audit_logger.log(
                event_type="REGIME_CHANGED",
                from_state=old_state.regime.name,
                to_state=new_state.regime.name,
                trigger_reason="state_transition",
                details={
                    "new_confidence": new_state.confidence,
                    "old_confidence": old_state.confidence,
                    "detection_count": self._detection_count,
                },
            )

    def _on_extreme_regime(self, regime_state: RegimeState) -> None:
        """极端状态回调.

        M6军规: 触发熔断检查

        Args:
            regime_state: 极端状态
        """
        if self._circuit_breaker and self._config.enable_circuit_breaker_check:
            self._circuit_breaker.check_extreme_conditions(regime_state)

    def _update_strategy_weights(self, state: RegimeState) -> None:
        """更新策略权重.

        M1军规: 状态决定策略权重

        Args:
            state: 当前状态
        """
        weights = self.get_all_strategy_weights()
        self._strategy_weights = weights
        self._weights_last_update = time.time()

        # 通知策略联邦
        if self._federation and self._config.enable_federation_integration:
            self._federation.update_regime_weights(state.regime, weights)

    def force_regime(
        self,
        regime: MarketRegime,
        reason: str = "forced",
    ) -> None:
        """强制设置状态 (仅用于测试/恢复).

        Args:
            regime: 目标状态
            reason: 原因
        """
        self._transition_engine.force_state(regime, reason)

    def reset(self) -> None:
        """重置检测器."""
        self._indicators.reset()
        self._transition_engine.reset()
        self._state_history.clear()
        self._detection_count = 0
        self._extreme_count = 0
        self._strategy_weights.clear()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        current = self.current_state
        return {
            "current_regime": self.current_regime.name,
            "current_state": current.to_dict() if current else None,
            "detection_count": self._detection_count,
            "extreme_count": self._extreme_count,
            "strategy_weights": self._strategy_weights,
            "regime_distribution": self.get_regime_distribution(),
            "transition_count": self._transition_engine.transition_count,
            "config": self._config.to_dict(),
        }


# ============================================================
# 策略联邦集成适配器
# ============================================================


class RegimeFederationAdapter:
    """状态-联邦适配器.

    M1军规: 状态与策略联邦集成

    将市场状态转换为策略联邦的权重调整信号.
    """

    def __init__(
        self,
        detector: MarketRegimeDetector,
    ) -> None:
        """初始化适配器.

        Args:
            detector: 市场状态检测器
        """
        self._detector = detector
        self._strategy_type_mapping: dict[str, str] = {}

    def register_strategy_type(
        self,
        strategy_id: str,
        strategy_type: str,
    ) -> None:
        """注册策略类型映射.

        Args:
            strategy_id: 策略ID
            strategy_type: 策略类型 (trend/mean_reversion/arbitrage/ml)
        """
        self._strategy_type_mapping[strategy_id] = strategy_type

    def get_weight_multiplier(self, strategy_id: str) -> float:
        """获取策略权重乘数.

        Args:
            strategy_id: 策略ID

        Returns:
            权重乘数
        """
        strategy_type = self._strategy_type_mapping.get(strategy_id, "ml")
        return self._detector.get_strategy_weight(strategy_type)

    def get_all_multipliers(self) -> dict[str, float]:
        """获取所有策略的权重乘数.

        Returns:
            策略ID -> 权重乘数 字典
        """
        return {
            sid: self.get_weight_multiplier(sid)
            for sid in self._strategy_type_mapping
        }

    @property
    def current_regime(self) -> MarketRegime:
        """当前市场状态."""
        return self._detector.current_regime

    @property
    def should_reduce_exposure(self) -> bool:
        """是否应该减少敞口."""
        state = self._detector.current_state
        return state.should_reduce_exposure if state else False


# ============================================================
# 便捷函数
# ============================================================


def create_regime_detector(
    config: DetectorConfig | None = None,
    audit_logger: AuditLogger | None = None,
) -> MarketRegimeDetector:
    """创建市场状态检测器.

    Args:
        config: 检测器配置
        audit_logger: 审计日志记录器

    Returns:
        检测器实例
    """
    return MarketRegimeDetector(config=config, audit_logger=audit_logger)


def detect_regime_from_prices(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray | None = None,
) -> RegimeState:
    """从价格数据检测市场状态.

    Args:
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量

    Returns:
        市场状态
    """
    detector = MarketRegimeDetector()
    return detector.detect(high, low, close, volume)
