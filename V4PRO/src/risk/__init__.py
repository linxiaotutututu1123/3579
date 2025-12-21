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
from src.risk.confidence_api import (
    ConfidenceAPI,
    ConfidenceAPIRequest,
    ConfidenceAPIResponse,
    StatisticsResponse,
    TrendResponse,
    assess_from_json,
    create_api,
    quick_assess,
)
from src.risk.confidence_ml import (
    ConfidenceMLP,
    ConfidenceMLPredictor,
    FeatureConfig,
    MLEnhancedAssessor,
    TrainingConfig,
    TrainingResult,
    create_ml_enhanced_assessor,
    create_ml_predictor,
    extract_features,
    get_feature_dim,
    quick_ml_predict,
)
from src.risk.confidence_monitor import (
    AlertRecord,
    ConfidenceMonitor,
    ConfidenceMonitorConfig,
    create_confidence_monitor,
    quick_monitor_check,
)
from src.risk.dynamic_var import (
    # 自适应VaR调度器 (D8设计)
    AdaptiveVaRConfig,
    AdaptiveVaRScheduler,
    # 动态VaR引擎核心
    DynamicVaREngine,
    DynamicVaRResult,
    EventType,
    GPDParameters,
    LiquidityMetrics,
    MarketRegime,
    PerformanceMetrics,
    RiskLevel,
    VaRMethod,
    VaRScheduleState,
    create_adaptive_var_scheduler,
    create_dynamic_var_engine,
    get_regime_from_volatility,
    quick_adaptive_var,
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
    # 自适应VaR调度器 (D8设计)
    "AdaptiveVaRConfig",
    "AdaptiveVaRScheduler",
    # 告警记录 (v4.4)
    "AlertRecord",
    "AttributionMethod",
    "AttributionResult",
    # 置信度API (v4.4)
    "ConfidenceAPI",
    "ConfidenceAPIRequest",
    "ConfidenceAPIResponse",
    # 置信度评估 (v4.3)
    "ConfidenceAssessor",
    "ConfidenceCheck",
    "ConfidenceContext",
    "ConfidenceLevel",
    # 置信度ML (v4.4)
    "ConfidenceMLP",
    "ConfidenceMLPredictor",
    # 置信度监控 (v4.4)
    "ConfidenceMonitor",
    "ConfidenceMonitorConfig",
    "ConfidenceResult",
    "Decision",
    # 动态VaR引擎 (v4.2)
    "DynamicVaREngine",
    "DynamicVaRResult",
    # 事件触发器类型 (D8)
    "EventType",
    "FactorContribution",
    "FactorType",
    # 特征配置 (v4.4)
    "FeatureConfig",
    "GPDParameters",
    "ImpactLevel",
    "LiquidityMetrics",
    # 市场状态枚举 (D8)
    "MarketRegime",
    # ML增强评估器 (v4.4)
    "MLEnhancedAssessor",
    # 性能指标 (D8)
    "PerformanceMetrics",
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
    # 统计响应 (v4.4)
    "StatisticsResponse",
    "StressScenario",
    "StressTestResult",
    "StressTestSummary",
    "StressTester",
    "TaskType",
    # 训练配置 (v4.4)
    "TrainingConfig",
    "TrainingResult",
    # 趋势响应 (v4.4)
    "TrendResponse",
    "VaRMethod",
    # VaR调度状态 (D8)
    "VaRScheduleState",
    "assess_from_json",
    "assess_pre_execution",
    "assess_signal",
    "attribute_trade_loss",
    "create_attribution_engine",
    # 自适应VaR工厂函数 (D8)
    "create_adaptive_var_scheduler",
    # 置信度API工厂 (v4.4)
    "create_api",
    # 置信度监控工厂 (v4.4)
    "create_confidence_monitor",
    "create_dynamic_var_engine",
    # ML工厂函数 (v4.4)
    "create_ml_enhanced_assessor",
    "create_ml_predictor",
    # 特征提取 (v4.4)
    "extract_features",
    "format_confidence_report",
    "get_all_scenarios",
    "get_default_tester",
    "get_factor_summary",
    # 特征维度 (v4.4)
    "get_feature_dim",
    # 市场状态辅助函数 (D8)
    "get_regime_from_volatility",
    "get_scenario_by_name",
    # 快速VaR计算函数
    "quick_adaptive_var",
    # 快速API评估 (v4.4)
    "quick_assess",
    "quick_evt_var",
    "quick_limit_var",
    # 快速ML预测 (v4.4)
    "quick_ml_predict",
    # 快速监控检查 (v4.4)
    "quick_monitor_check",
    "run_stress_test",
]
