"""
守护模块 (军规级 v4.0).

V4PRO Platform Component - Phase 1 + Phase 7 中国期货特化 + Phase 10 熔断增强
V4 SPEC: §6 Guardian, §12 Phase 7, D2 熔断-恢复闭环

功能特性:
- 守护主循环 (GuardianMonitor)
- 状态机 (GuardianFSM)
- 动作执行器 (GuardianActions)
- 冷启动恢复 (ColdStartRecovery)
- 触发器管理器 (TriggerManager)
- 中国期货触发器 (LimitPrice/Margin/Delivery)
- 熔断-恢复状态机 (CircuitBreaker) - V4 SPEC D2
- 熔断触发器 (DailyLoss/PositionLoss/MarginUsage/ConsecutiveLoss) - V4 SPEC D2
- 渐进式恢复执行器 (GradualRecoveryExecutor) - V4 SPEC D2
- 熔断恢复闭环控制器 (CircuitBreakerController) - V4 SPEC D2

军规覆盖:
- M3: 审计日志完整，状态转换全记录
- M6: 熔断保护机制完整，状态机设计完善
- M13: 涨跌停感知
- M15: 夜盘跨日处理
- M16: 保证金实时监控
"""

from src.guardian.actions import (
    ActionResult,
    ActionStatus,
    ActionType,
    GuardianActions,
)
from src.guardian.circuit_breaker import (
    VALID_CIRCUIT_BREAKER_TRANSITIONS,
    AuditRecord,
    CircuitBreaker,
    CircuitBreakerEvent,
    CircuitBreakerManager,
    CircuitBreakerMetrics,
    CircuitBreakerState,
    DefaultAuditLogger,
    RecoveryConfig,
    RecoveryProgress,
    TriggerCheckResult,
    TriggerThresholds,
)
from src.guardian.circuit_breaker import TransitionError as CircuitBreakerTransitionError
from src.guardian.circuit_breaker_controller import (
    CircuitBreakerController,
    ControllerStatus,
    create_default_controller,
)
from src.guardian.circuit_breaker_triggers import (
    CircuitBreakerRiskTrigger,
    ConsecutiveLossTrigger,
    DailyLossTrigger,
    MarginUsageTrigger,
    PositionLossTrigger,
    RiskMetricsCollector,
    create_circuit_breaker_triggers,
    register_circuit_breaker_triggers,
)
from src.guardian.gradual_recovery import (
    DefaultAlertSender,
    DefaultPositionScaler,
    GradualRecoveryExecutor,
    RecoveryCoordinator,
    RecoveryEvent,
    RecoveryStage,
)
from src.guardian.gradual_recovery import RecoveryStatus as GradualRecoveryStatus
from src.guardian.monitor import GuardianCheckResult, GuardianMonitor
from src.guardian.recovery import ColdStartRecovery, RecoveryState, RecoveryStatus
from src.guardian.state_machine import (
    VALID_TRANSITIONS,
    GuardianFSM,
    GuardianMode,
    TransitionError,
)
from src.guardian.triggers import (
    BaseTrigger,
    LegImbalanceTrigger,
    OrderStuckTrigger,
    PositionDriftTrigger,
    QuoteStaleTrigger,
    TriggerManager,
    TriggerResult,
)
from src.guardian.triggers_china import (
    DeliveryApproachingTrigger,
    DeliveryInfo,
    LimitPriceInfo,
    LimitPriceStatus,
    LimitPriceTrigger,
    MarginInfo,
    MarginLevel,
    MarginTrigger,
    create_default_china_triggers,
    register_china_triggers,
)


__all__ = [
    # Circuit Breaker (熔断-恢复状态机) - V4 SPEC D2
    "VALID_CIRCUIT_BREAKER_TRANSITIONS",
    "AuditRecord",
    "CircuitBreaker",
    "CircuitBreakerEvent",
    "CircuitBreakerManager",
    "CircuitBreakerMetrics",
    "CircuitBreakerState",
    "CircuitBreakerTransitionError",
    "DefaultAuditLogger",
    "RecoveryConfig",
    "RecoveryProgress",
    "TriggerCheckResult",
    "TriggerThresholds",
    # Guardian FSM (原状态机)
    "VALID_TRANSITIONS",
    "ActionResult",
    "ActionStatus",
    "ActionType",
    "BaseTrigger",
    "ColdStartRecovery",
    "DeliveryApproachingTrigger",
    "DeliveryInfo",
    "GuardianActions",
    "GuardianCheckResult",
    "GuardianFSM",
    "GuardianMode",
    "GuardianMonitor",
    "LegImbalanceTrigger",
    "LimitPriceInfo",
    "LimitPriceStatus",
    "LimitPriceTrigger",
    "MarginInfo",
    "MarginLevel",
    "MarginTrigger",
    "OrderStuckTrigger",
    "PositionDriftTrigger",
    "QuoteStaleTrigger",
    "RecoveryState",
    "RecoveryStatus",
    "TransitionError",
    "TriggerManager",
    "TriggerResult",
    "create_default_china_triggers",
    "register_china_triggers",
]
