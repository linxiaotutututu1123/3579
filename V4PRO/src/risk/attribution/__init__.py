"""
多维收益归因模块 (军规级 v4.6).

V4PRO Platform Component - Phase 7/10 风险归因与多维分析
V4 SPEC: SS23 风险归因, SS24 模型可解释性, SS25 多维归因分析, SS26 SHAP可解释性

军规覆盖:
- M19: 风险归因 - 每笔亏损必须有归因分析

本模块提供:
- RiskAttributionEngine: 风险归因引擎 (v4.1)
- SHAPAttributor: SHAP多维归因分析器 (v4.6 Phase 10)
- AttributionResult: 归因结果
- FactorContribution: 因子贡献
- TimeAttribution: 时间归因
- StrategyBreakdown: 策略分解

示例:
    >>> from src.risk.attribution import (
    ...     RiskAttributionEngine,
    ...     SHAPAttributor,
    ...     create_shap_attributor,
    ... )
    >>> # 风险归因
    >>> engine = RiskAttributionEngine()
    >>> result = engine.attribute_trade(trade_id, symbol, pnl, features)
    >>>
    >>> # 多维收益归因
    >>> attributor = create_shap_attributor()
    >>> result = attributor.attribute_returns(returns, factor_data)
"""

# ============================================================
# 原有风险归因 (v4.1)
# ============================================================
from src.risk.attribution.base import (
    # 枚举
    AttributionMethod,
    FactorType,
    # 数据类
    AttributionResult,
    FactorContribution,
    FeatureGroup,
    # 核心类
    RiskAttributionEngine,
    # 便捷函数
    attribute_trade_loss,
    create_attribution_engine,
    get_factor_summary,
)

# ============================================================
# SHAP多维归因 (v4.6 Phase 10)
# ============================================================
from src.risk.attribution.shap_attribution import (
    # 枚举 (使用别名避免冲突)
    AttributionMethod as SHAPAttributionMethod,
    MarketFactor,
    StrategyFactor,
    TimeDimension,
    # 数据类 (使用别名避免冲突)
    AttributionResult as SHAPAttributionResult,
    FactorContribution as SHAPFactorContribution,
    StrategyBreakdown,
    TimeAttribution,
    # 核心类
    SHAPAttributor,
    # 便捷函数
    attribute_portfolio_returns,
    create_shap_attributor,
    get_factor_summary as get_shap_factor_summary,
    get_strategy_summary,
    get_time_summary,
)

__all__ = [
    # ============================================================
    # 原有风险归因 (v4.1)
    # ============================================================
    # 枚举
    "AttributionMethod",
    "FactorType",
    # 数据类
    "AttributionResult",
    "FactorContribution",
    "FeatureGroup",
    # 核心类
    "RiskAttributionEngine",
    # 便捷函数
    "attribute_trade_loss",
    "create_attribution_engine",
    "get_factor_summary",
    # ============================================================
    # SHAP多维归因 (v4.6 Phase 10)
    # ============================================================
    # 枚举
    "MarketFactor",
    "SHAPAttributionMethod",
    "StrategyFactor",
    "TimeDimension",
    # 数据类
    "SHAPAttributionResult",
    "SHAPFactorContribution",
    "StrategyBreakdown",
    "TimeAttribution",
    # 核心类
    "SHAPAttributor",
    # 便捷函数
    "attribute_portfolio_returns",
    "create_shap_attributor",
    "get_shap_factor_summary",
    "get_strategy_summary",
    "get_time_summary",
]
