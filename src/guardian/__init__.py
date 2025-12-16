"""
守护模块 (军规级 v4.0).

V4PRO Platform Component - Phase 1 + Phase 7 中国期货特化
V4 SPEC: §6 Guardian, §12 Phase 7

功能特性:
- 守护主循环 (GuardianMonitor)
- 状态机 (GuardianFSM)
- 动作执行器 (GuardianActions)
- 冷启动恢复 (ColdStartRecovery)
- 触发器管理器 (TriggerManager)
- 中国期货触发器 (LimitPrice/Margin/Delivery)

军规覆盖:
- M6: 熔断保护
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
    "VALID_TRANSITIONS",
    "create_default_china_triggers",
    "register_china_triggers",
]
