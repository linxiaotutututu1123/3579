"""
风险管理模块 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §15 Phase 10, §22 VaR风控增强, §23 压力测试场景, §24 模型可解释性

功能特性:
- 风险管理器 (RiskManager)
- VaR计算器 (VaRCalculator)
- 中国期货压力测试 (StressTester)
- 风险归因引擎 (RiskAttributionEngine) [v4.1新增]

军规覆盖:
- M6: 熔断保护
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
    "AccountSnapshot",
    "AttributionMethod",
    "AttributionResult",
    "Decision",
    "FactorContribution",
    "FactorType",
    "HYPOTHETICAL_SCENARIOS",
    "ImpactLevel",
    "PositionExposure",
    "RiskAction",
    "RiskAttributionEngine",
    "RiskConfig",
    "RiskEvent",
    "RiskEventType",
    "RiskManager",
    "RiskMode",
    "RiskState",
    "STRESS_SCENARIOS",
    "ScenarioType",
    "StressScenario",
    "StressTestResult",
    "StressTestSummary",
    "StressTester",
    "attribute_trade_loss",
    "create_attribution_engine",
    "get_all_scenarios",
    "get_default_tester",
    "get_factor_summary",
    "get_scenario_by_name",
    "run_stress_test",
]
