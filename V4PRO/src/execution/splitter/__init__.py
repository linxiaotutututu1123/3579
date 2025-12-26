"""
智能拆单模块.

V4PRO Platform Component - Intelligent Order Splitter
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致), M12(双重确认)

V4PRO Scenarios:
- SPLITTER.SELECTOR: 智能算法选择
- SPLITTER.SPLIT: 大额订单拆分
- SPLITTER.CONFIRM: 与确认机制集成 (M12)
- SPLITTER.BEHAVIORAL.*: 行为伪装
- SPLITTER.METRICS.*: 执行质量指标

支持的拆单算法:
- TWAP: 时间加权平均价格
- VWAP: 成交量加权平均价格
- ICEBERG: 冰山订单
- BEHAVIORAL: 行为伪装

执行质量目标 (D7-P1):
- 滑点: <=0.1%
- 成交率: >=95%
- 执行延迟: <=100ms
"""

from src.execution.splitter.metrics import (
    MetricStatus,
    ExecutionTargets,
    DEFAULT_TARGETS,
    SlippageMetric,
    FillRateMetric,
    LatencyMetric,
    ExecutionMetrics,
    MetricsCollector,
)
from src.execution.splitter.behavioral_disguise import (
    DisguisePattern,
    NoiseType,
    BehavioralConfig,
    DisguiseState,
    BehavioralDisguiseExecutor,
)
from src.execution.splitter.order_splitter import (
    SplitAlgorithm,
    OrderSizeCategory,
    LiquidityLevel,
    SessionPhase,
    MarketContext,
    SplitterConfig,
    AlgorithmScore,
    SplitPlan,
    ConfirmationCallback,
    AlgorithmSelector,
    OrderSplitter,
    ALGORITHM_DECISION_TREE,
)

__all__ = [
    # metrics.py exports
    "MetricStatus",
    "ExecutionTargets",
    "DEFAULT_TARGETS",
    "SlippageMetric",
    "FillRateMetric",
    "LatencyMetric",
    "ExecutionMetrics",
    "MetricsCollector",
    # behavioral_disguise.py exports
    "DisguisePattern",
    "NoiseType",
    "BehavioralConfig",
    "DisguiseState",
    "BehavioralDisguiseExecutor",
    # order_splitter.py exports
    "SplitAlgorithm",
    "OrderSizeCategory",
    "LiquidityLevel",
    "SessionPhase",
    "MarketContext",
    "SplitterConfig",
    "AlgorithmScore",
    "SplitPlan",
    "ConfirmationCallback",
    "AlgorithmSelector",
    "OrderSplitter",
    "ALGORITHM_DECISION_TREE",
]
