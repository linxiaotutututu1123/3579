"""
风险管理模块 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §15 Phase 10, §22 VaR风控增强, §23 压力测试场景

功能特性:
- 风险管理器 (RiskManager)
- VaR计算器 (VaRCalculator)
- 中国期货压力测试 (StressTester)

军规覆盖:
- M6: 熔断保护
- M19: 风险归因
"""

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
    "Decision",
    "ImpactLevel",
    "PositionExposure",
    "RiskAction",
    "RiskConfig",
    "RiskEvent",
    "RiskEventType",
    "RiskManager",
    "RiskMode",
    "RiskState",
    "ScenarioType",
    "StressScenario",
    "StressTestResult",
    "StressTestSummary",
    "StressTester",
    "get_all_scenarios",
    "get_default_tester",
    "get_scenario_by_name",
    "run_stress_test",
]
