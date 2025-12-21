"""
市场状态定义模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: D7-P0 市场状态引擎

军规覆盖:
- M1: 单一信号源 - 状态输出为策略权重调整依据
- M6: 熔断保护联动 - 极端状态触发熔断检查

功能特性:
- 四种市场状态定义
- 状态元数据描述
- 状态强度量化

示例:
    >>> from src.strategy.regime.states import (
    ...     MarketRegime,
    ...     RegimeStrength,
    ... )
    >>> regime = MarketRegime.TRENDING
    >>> strength = RegimeStrength.STRONG
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, ClassVar


class MarketRegime(IntEnum):
    """市场状态枚举.

    V4 SPEC D7-P0: 四种核心市场状态

    状态定义:
    - TRENDING: 趋势状态 - 明确方向性运动
    - RANGING: 震荡状态 - 区间波动无明确方向
    - VOLATILE: 波动状态 - 高波动但方向不确定
    - EXTREME: 极端状态 - 异常市场条件
    """

    TRENDING = 0  # 趋势状态
    RANGING = 1  # 震荡状态
    VOLATILE = 2  # 波动状态
    EXTREME = 3  # 极端状态

    def __str__(self) -> str:
        """返回状态名称."""
        return self.name

    @property
    def description(self) -> str:
        """获取状态描述."""
        descriptions = {
            MarketRegime.TRENDING: "明确方向性趋势运动",
            MarketRegime.RANGING: "区间震荡无明确方向",
            MarketRegime.VOLATILE: "高波动不确定方向",
            MarketRegime.EXTREME: "异常极端市场条件",
        }
        return descriptions.get(self, "未知状态")

    @property
    def is_risky(self) -> bool:
        """是否为高风险状态."""
        return self in (MarketRegime.VOLATILE, MarketRegime.EXTREME)

    @property
    def default_weight_multiplier(self) -> float:
        """默认权重乘数.

        用于策略联邦权重调整.
        """
        multipliers = {
            MarketRegime.TRENDING: 1.0,  # 正常权重
            MarketRegime.RANGING: 0.7,  # 降低权重
            MarketRegime.VOLATILE: 0.5,  # 大幅降低
            MarketRegime.EXTREME: 0.2,  # 最低权重
        }
        return multipliers.get(self, 1.0)


class RegimeStrength(Enum):
    """状态强度枚举.

    量化市场状态的强度/确定性.
    """

    WEAK = "WEAK"  # 弱 (信号不明确)
    MODERATE = "MODERATE"  # 中等 (信号较明确)
    STRONG = "STRONG"  # 强 (信号非常明确)

    @property
    def confidence_range(self) -> tuple[float, float]:
        """获取置信度范围."""
        ranges = {
            RegimeStrength.WEAK: (0.0, 0.4),
            RegimeStrength.MODERATE: (0.4, 0.7),
            RegimeStrength.STRONG: (0.7, 1.0),
        }
        return ranges.get(self, (0.0, 1.0))

    @classmethod
    def from_confidence(cls, confidence: float) -> RegimeStrength:
        """从置信度值获取强度等级.

        Args:
            confidence: 置信度 (0-1)

        Returns:
            对应的强度等级
        """
        if confidence >= 0.7:
            return cls.STRONG
        if confidence >= 0.4:
            return cls.MODERATE
        return cls.WEAK


class TrendDirection(Enum):
    """趋势方向枚举.

    仅在 TRENDING 状态下有效.
    """

    UP = "UP"  # 上涨趋势
    DOWN = "DOWN"  # 下跌趋势
    NEUTRAL = "NEUTRAL"  # 无趋势/中性


@dataclass(frozen=True, slots=True)
class RegimeState:
    """市场状态快照 (不可变).

    属性:
        regime: 市场状态类型
        strength: 状态强度
        confidence: 检测置信度 (0-1)
        trend_direction: 趋势方向 (仅TRENDING状态有效)
        volatility_percentile: 波动率百分位 (0-100)
        volume_percentile: 成交量百分位 (0-100)
        timestamp: 检测时间戳
        metadata: 附加元数据
    """

    regime: MarketRegime
    strength: RegimeStrength
    confidence: float
    trend_direction: TrendDirection = TrendDirection.NEUTRAL
    volatility_percentile: float = 50.0
    volume_percentile: float = 50.0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证参数."""
        if not 0 <= self.confidence <= 1:
            object.__setattr__(
                self, "confidence", max(0.0, min(1.0, self.confidence))
            )
        if not 0 <= self.volatility_percentile <= 100:
            object.__setattr__(
                self, "volatility_percentile",
                max(0.0, min(100.0, self.volatility_percentile))
            )
        if not 0 <= self.volume_percentile <= 100:
            object.__setattr__(
                self, "volume_percentile",
                max(0.0, min(100.0, self.volume_percentile))
            )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "regime": self.regime.name,
            "regime_value": self.regime.value,
            "strength": self.strength.value,
            "confidence": round(self.confidence, 4),
            "trend_direction": self.trend_direction.value,
            "volatility_percentile": round(self.volatility_percentile, 2),
            "volume_percentile": round(self.volume_percentile, 2),
            "timestamp": self.timestamp,
            "is_risky": self.regime.is_risky,
            "weight_multiplier": self.regime.default_weight_multiplier,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "REGIME_STATE",
            **self.to_dict(),
            "metadata": self.metadata,
        }

    @property
    def is_stable(self) -> bool:
        """是否为稳定状态.

        TRENDING 和 RANGING 被认为是稳定状态.
        """
        return self.regime in (MarketRegime.TRENDING, MarketRegime.RANGING)

    @property
    def should_reduce_exposure(self) -> bool:
        """是否应该减少敞口.

        高风险状态或低置信度时建议减少敞口.
        """
        return self.regime.is_risky or self.confidence < 0.5

    @property
    def weight_multiplier(self) -> float:
        """获取权重乘数.

        结合状态类型和置信度计算.
        """
        base_multiplier = self.regime.default_weight_multiplier
        confidence_factor = 0.5 + 0.5 * self.confidence
        return base_multiplier * confidence_factor


@dataclass(frozen=True, slots=True)
class RegimeTransition:
    """状态转换记录 (不可变).

    属性:
        from_state: 原状态
        to_state: 目标状态
        trigger_reason: 触发原因
        trigger_indicators: 触发指标值
        timestamp: 转换时间戳
    """

    from_state: MarketRegime
    to_state: MarketRegime
    trigger_reason: str
    trigger_indicators: dict[str, float] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "from_state": self.from_state.name,
            "to_state": self.to_state.name,
            "trigger_reason": self.trigger_reason,
            "trigger_indicators": self.trigger_indicators,
            "timestamp": self.timestamp,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "REGIME_TRANSITION",
            **self.to_dict(),
        }


@dataclass
class RegimeConfig:
    """状态检测配置.

    属性:
        volatility_window: 波动率计算窗口
        trend_window: 趋势检测窗口
        volume_window: 成交量分析窗口
        atr_multiplier_extreme: 极端状态ATR倍数阈值
        trend_strength_threshold: 趋势强度阈值
        ranging_threshold: 震荡检测阈值
    """

    # 窗口配置
    volatility_window: int = 20
    trend_window: int = 50
    volume_window: int = 20

    # 阈值配置
    atr_multiplier_extreme: float = 2.5  # ATR超过均值2.5倍判定为极端
    atr_multiplier_volatile: float = 1.5  # ATR超过均值1.5倍判定为高波动
    trend_strength_threshold: float = 0.3  # ADX/趋势强度阈值
    ranging_threshold: float = 0.15  # 震荡判定阈值
    volume_surge_threshold: float = 2.0  # 成交量激增阈值

    # 状态持续性
    min_regime_duration: int = 5  # 最小状态持续K线数
    transition_smoothing: float = 0.3  # 转换平滑系数

    # 军规相关
    extreme_circuit_breaker_check: bool = True  # 极端状态检查熔断

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "volatility_window": self.volatility_window,
            "trend_window": self.trend_window,
            "volume_window": self.volume_window,
            "atr_multiplier_extreme": self.atr_multiplier_extreme,
            "atr_multiplier_volatile": self.atr_multiplier_volatile,
            "trend_strength_threshold": self.trend_strength_threshold,
            "ranging_threshold": self.ranging_threshold,
            "volume_surge_threshold": self.volume_surge_threshold,
            "min_regime_duration": self.min_regime_duration,
            "transition_smoothing": self.transition_smoothing,
            "extreme_circuit_breaker_check": self.extreme_circuit_breaker_check,
        }


# ============================================================
# 策略权重配置映射
# ============================================================


@dataclass
class RegimeWeightConfig:
    """状态-策略权重配置.

    定义不同市场状态下各类策略的权重调整.
    """

    # 趋势跟踪策略权重
    TREND_FOLLOWING_WEIGHTS: ClassVar[dict[MarketRegime, float]] = {
        MarketRegime.TRENDING: 1.2,  # 增强
        MarketRegime.RANGING: 0.5,  # 大幅降低
        MarketRegime.VOLATILE: 0.7,  # 降低
        MarketRegime.EXTREME: 0.3,  # 最低
    }

    # 均值回复策略权重
    MEAN_REVERSION_WEIGHTS: ClassVar[dict[MarketRegime, float]] = {
        MarketRegime.TRENDING: 0.5,  # 降低
        MarketRegime.RANGING: 1.2,  # 增强
        MarketRegime.VOLATILE: 0.8,  # 略降
        MarketRegime.EXTREME: 0.3,  # 最低
    }

    # 套利策略权重
    ARBITRAGE_WEIGHTS: ClassVar[dict[MarketRegime, float]] = {
        MarketRegime.TRENDING: 0.9,  # 正常
        MarketRegime.RANGING: 1.0,  # 正常
        MarketRegime.VOLATILE: 1.1,  # 略增 (波动增加套利机会)
        MarketRegime.EXTREME: 0.5,  # 降低 (风险控制)
    }

    # 混合/机器学习策略权重
    ML_STRATEGY_WEIGHTS: ClassVar[dict[MarketRegime, float]] = {
        MarketRegime.TRENDING: 1.0,
        MarketRegime.RANGING: 1.0,
        MarketRegime.VOLATILE: 0.7,
        MarketRegime.EXTREME: 0.4,
    }

    @classmethod
    def get_weight(
        cls,
        strategy_type: str,
        regime: MarketRegime,
    ) -> float:
        """获取策略权重.

        Args:
            strategy_type: 策略类型 (trend/mean_reversion/arbitrage/ml)
            regime: 市场状态

        Returns:
            权重乘数
        """
        weight_maps = {
            "trend": cls.TREND_FOLLOWING_WEIGHTS,
            "trend_following": cls.TREND_FOLLOWING_WEIGHTS,
            "mean_reversion": cls.MEAN_REVERSION_WEIGHTS,
            "reversion": cls.MEAN_REVERSION_WEIGHTS,
            "arbitrage": cls.ARBITRAGE_WEIGHTS,
            "arb": cls.ARBITRAGE_WEIGHTS,
            "ml": cls.ML_STRATEGY_WEIGHTS,
            "machine_learning": cls.ML_STRATEGY_WEIGHTS,
        }

        weight_map = weight_maps.get(strategy_type.lower(), cls.ML_STRATEGY_WEIGHTS)
        return weight_map.get(regime, 1.0)


# ============================================================
# 便捷函数
# ============================================================


def create_regime_state(
    regime: MarketRegime,
    confidence: float,
    volatility_percentile: float = 50.0,
    volume_percentile: float = 50.0,
    trend_direction: TrendDirection = TrendDirection.NEUTRAL,
) -> RegimeState:
    """创建市场状态.

    Args:
        regime: 市场状态类型
        confidence: 检测置信度
        volatility_percentile: 波动率百分位
        volume_percentile: 成交量百分位
        trend_direction: 趋势方向

    Returns:
        RegimeState 实例
    """
    strength = RegimeStrength.from_confidence(confidence)
    return RegimeState(
        regime=regime,
        strength=strength,
        confidence=confidence,
        trend_direction=trend_direction,
        volatility_percentile=volatility_percentile,
        volume_percentile=volume_percentile,
        timestamp=datetime.now().isoformat(),  # noqa: DTZ005
    )


def get_strategy_weight_multiplier(
    strategy_type: str,
    regime_state: RegimeState,
) -> float:
    """获取策略权重乘数.

    Args:
        strategy_type: 策略类型
        regime_state: 市场状态

    Returns:
        综合权重乘数
    """
    base_weight = RegimeWeightConfig.get_weight(strategy_type, regime_state.regime)
    confidence_factor = 0.5 + 0.5 * regime_state.confidence
    return base_weight * confidence_factor
