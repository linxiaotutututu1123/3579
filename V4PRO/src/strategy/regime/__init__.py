"""
市场状态引擎模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: D7-P0 市场状态引擎

军规覆盖:
- M1: 单一信号源 - 状态输出为策略权重调整的唯一依据
- M6: 熔断保护联动 - 极端状态触发熔断检查
- M19: 风险归因 - 状态贡献度追踪

功能模块:
- states: 状态定义 (TRENDING/RANGING/VOLATILE/EXTREME)
- indicators: 指标计算 (ATR/ADX/波动率/成交量)
- transitions: 转换逻辑 (状态转换检测与执行)
- detector: 状态检测器 (核心检测器，与联邦集成)

市场状态引擎功能:
├── 状态识别
│   ├── TRENDING (趋势) - 明确方向性运动
│   ├── RANGING (震荡) - 区间波动无明确方向
│   ├── VOLATILE (波动) - 高波动但方向不确定
│   └── EXTREME (极端) - 异常市场条件
│
├── 状态转换检测
│   ├── 基于波动率 - ATR、历史波动率百分位
│   ├── 基于成交量 - 成交量比率、激增检测
│   └── 基于价格模式 - ADX、突破检测
│
└── 与策略联邦集成
    └── 状态 -> 策略权重调整

示例:
    >>> from src.strategy.regime import (
    ...     MarketRegimeDetector,
    ...     MarketRegime,
    ...     RegimeState,
    ... )
    >>>
    >>> # 创建检测器
    >>> detector = MarketRegimeDetector()
    >>>
    >>> # 从K线检测状态
    >>> bars = [{"high": 101, "low": 99, "close": 100, "volume": 1000}, ...]
    >>> state = detector.detect_from_bars(bars)
    >>>
    >>> # 获取策略权重
    >>> weight = detector.get_strategy_weight("trend_following")
"""

from __future__ import annotations

from src.strategy.regime.detector import (
    DetectorConfig,
    MarketRegimeDetector,
    RegimeFederationAdapter,
    create_regime_detector,
    detect_regime_from_prices,
)
from src.strategy.regime.indicators import (
    IndicatorConfig,
    IndicatorResult,
    RegimeIndicators,
    calculate_atr,
    calculate_indicators,
    calculate_volatility,
)
from src.strategy.regime.states import (
    MarketRegime,
    RegimeConfig,
    RegimeState,
    RegimeStrength,
    RegimeTransition,
    RegimeWeightConfig,
    TrendDirection,
    create_regime_state,
    get_strategy_weight_multiplier,
)
from src.strategy.regime.transitions import (
    TransitionCondition,
    TransitionEngine,
    TransitionRule,
    create_transition_engine,
)


__all__ = [
    # 状态定义
    "MarketRegime",
    "RegimeConfig",
    "RegimeState",
    "RegimeStrength",
    "RegimeTransition",
    "RegimeWeightConfig",
    "TrendDirection",
    # 指标计算
    "IndicatorConfig",
    "IndicatorResult",
    "RegimeIndicators",
    # 转换逻辑
    "TransitionCondition",
    "TransitionEngine",
    "TransitionRule",
    # 检测器
    "DetectorConfig",
    "MarketRegimeDetector",
    "RegimeFederationAdapter",
    # 便捷函数
    "calculate_atr",
    "calculate_indicators",
    "calculate_volatility",
    "create_regime_detector",
    "create_regime_state",
    "create_transition_engine",
    "detect_regime_from_prices",
    "get_strategy_weight_multiplier",
]
