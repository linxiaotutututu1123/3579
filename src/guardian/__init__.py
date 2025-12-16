"""
守护模块.

V3PRO+ Platform Component - Phase 1
V2 SPEC: 第 6 章 Guardian

Exports:
    GuardianMonitor: 守护主循环
    GuardianFSM: 状态机
    GuardianMode: 状态枚举
    GuardianActions: 动作执行器
    ColdStartRecovery: 冷启动恢复
    TriggerManager: 触发器管理器
    各类触发器
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


__all__ = [
    "ActionResult",
    "ActionStatus",
    "ActionType",
    "BaseTrigger",
    "ColdStartRecovery",
    "GuardianActions",
    "GuardianCheckResult",
    "GuardianFSM",
    "GuardianMode",
    "GuardianMonitor",
    "LegImbalanceTrigger",
    "OrderStuckTrigger",
    "PositionDriftTrigger",
    "QuoteStaleTrigger",
    "RecoveryState",
    "RecoveryStatus",
    "TransitionError",
    "TriggerManager",
    "TriggerResult",
    "VALID_TRANSITIONS",
]
