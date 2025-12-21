"""
风险管理模块 (军规级 v4.2).

V4PRO Platform Component - Phase 7/10 中国期货市场特化
V4 SPEC: §15 Phase 10, §22 VaR风控增强, §23 压力测试场景, §24 模型可解释性

功能特性:
- 风险管理器 (RiskManager)
- VaR计算器 (VaRCalculator)
- 动态VaR引擎 (DynamicVaREngine) [v4.2新增]
- 中国期货压力测试 (StressTester)
- 风险归因引擎 (RiskAttributionEngine) [v4.1新增]

军规覆盖:
- M6: 熔断保护 - 极端风险预警
- M13: 涨跌停感知 - 涨跌停调整VaR
- M16: 保证金监控 - 流动性调整VaR
- M19: 风险归因 - SHAP因子分析
"""

from src.risk.attribution import (
    AttributionMethod,
    AttributionResult,
    FactorContribution,
    FactorType,
    RiskAttributionEngine,
    attribute_trade_loss,
    create_attribution_engine,
    get_factor_summary,
)
from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceCheck,
    ConfidenceContext,
    ConfidenceLevel,
    ConfidenceResult,
    TaskType,
    assess_pre_execution,
    assess_signal,
    format_confidence_report,
)
from src.risk.dynamic_var import (
    DynamicVaREngine,
    DynamicVaRResult,
    GPDParameters,
    LiquidityMetrics,
    RiskLevel,
    VaRMethod,
    create_dynamic_var_engine,
    quick_evt_var,
    quick_limit_var,
)
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import Decision, RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState
from src.risk.stress_test_china import (
    HYPOTHETICAL_SCENARIOS,
    STRESS_SCENARIOS,
    ImpactLevel,
    PositionExposure,
    RiskAction,
    ScenarioType,
    StressScenario,
    StressTester,
    StressTestResult,
    StressTestSummary,
    get_all_scenarios,
    get_default_tester,
    get_scenario_by_name,
    run_stress_test,
)


__all__ = [
    "HYPOTHETICAL_SCENARIOS",
    "STRESS_SCENARIOS",
    "AccountSnapshot",
    "AttributionMethod",
    "AttributionResult",
    "Decision",
    # 动态VaR引擎 (v4.2)
    "DynamicVaREngine",
    "DynamicVaRResult",
    "FactorContribution",
    "FactorType",
    "GPDParameters",
    "ImpactLevel",
    "LiquidityMetrics",
    "PositionExposure",
    "RiskAction",
    "RiskAttributionEngine",
    "RiskConfig",
    "RiskEvent",
    "RiskEventType",
    "RiskLevel",
    "RiskManager",
    "RiskMode",
    "RiskState",
    "ScenarioType",
    "StressScenario",
    "StressTestResult",
    "StressTestSummary",
    "StressTester",
    "VaRMethod",
    "attribute_trade_loss",
    "create_attribution_engine",
    "create_dynamic_var_engine",
    "get_all_scenarios",
    "get_default_tester",
    "get_factor_summary",
    "get_scenario_by_name",
    "quick_evt_var",
    "quick_limit_var",
    "run_stress_test",
]
