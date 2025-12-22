"""
多维收益归因模块 (军规级 v4.0).

V4PRO Platform Component - Phase 10 多维收益归因
V4 SPEC: SS25 多维归因分析, SS26 SHAP可解释性

军规覆盖:
- M19: 风险归因 - 每笔亏损必须有归因分析

本模块提供:
- SHAPAttributor: SHAP归因分析器
- AttributionResult: 多维归因结果
- FactorContribution: 因子贡献
- TimeAttribution: 时间归因
- StrategyBreakdown: 策略分解

示例:
    >>> from src.risk.attribution import (
    ...     SHAPAttributor,
    ...     AttributionResult,
    ...     MarketFactor,
    ...     StrategyFactor,
    ...     create_shap_attributor,
    ... )
    >>> attributor = create_shap_attributor()
    >>> result = attributor.attribute_returns(returns, factor_data)
"""

from src.risk.attribution.shap_attribution import (
    # 枚举
    AttributionMethod,
    MarketFactor,
    StrategyFactor,
    TimeDimension,
    # 数据类
    AttributionResult,
    FactorContribution,
    StrategyBreakdown,
    TimeAttribution,
    # 核心类
    SHAPAttributor,
    # 便捷函数
    attribute_portfolio_returns,
    create_shap_attributor,
    get_factor_summary,
    get_strategy_summary,
    get_time_summary,
)

__all__ = [
    # 枚举
    "AttributionMethod",
    "MarketFactor",
    "StrategyFactor",
    "TimeDimension",
    # 数据类
    "AttributionResult",
    "FactorContribution",
    "StrategyBreakdown",
    "TimeAttribution",
    # 核心类
    "SHAPAttributor",
    # 便捷函数
    "attribute_portfolio_returns",
    "create_shap_attributor",
    "get_factor_summary",
    "get_strategy_summary",
    "get_time_summary",
]
