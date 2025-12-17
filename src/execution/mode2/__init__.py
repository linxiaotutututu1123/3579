"""
Mode 2 交易执行管道模块.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M1(单一信号源), M2(幂等执行), M3(完整审计), M7(回放一致)

V4PRO Scenarios:
- MODE2.INTENT.IDEMPOTENT: intent_id 幂等键确保同一意图不重复执行
- MODE2.INTENT.REPLAY: 回放时相同输入产生相同 intent_id
- MODE2.ENGINE.SUBMIT: 意图提交与幂等检查
- MODE2.ENGINE.DISPATCH: 执行器分发
- MODE2.EXECUTOR.TWAP: 时间加权平均价格执行
- MODE2.EXECUTOR.VWAP: 成交量加权平均价格执行
- MODE2.EXECUTOR.ICEBERG: 冰山单执行

核心组件:
- OrderIntent: 策略层输出的交易意图
- IntentIdGenerator: 幂等键生成器
- ExecutionEngine: 执行引擎
- Executor: 执行器接口 (Immediate/TWAP/VWAP/Iceberg)
"""

from __future__ import annotations

from src.execution.mode2.audit_events import (
    Mode2AuditEvent,
    Mode2AuditEventType,
    create_intent_completed_event,
    create_intent_created_event,
    create_intent_failed_event,
    create_intent_rejected_event,
    create_plan_cancelled_event,
    create_plan_created_event,
    create_plan_paused_event,
    create_plan_resumed_event,
    create_slice_ack_event,
    create_slice_cancelled_event,
    create_slice_filled_event,
    create_slice_rejected_event,
    create_slice_sent_event,
)
from src.execution.mode2.engine import (
    ExecutionEngine,
    ExecutionEngineConfig,
    ExecutionPlan,
    ExecutionPlanStatus,
)
from src.execution.mode2.executor_base import (
    TERMINAL_STATUSES,
    ExecutionPlanContext,
    ExecutionProgress,
    ExecutorAction,
    ExecutorActionType,
    ExecutorBase,
    ExecutorConfig,
    ExecutorStatus,
    FilledOrder,
    OrderEvent,
    PendingOrder,
    SliceInfo,
)
from src.execution.mode2.executor_iceberg import IcebergConfig, IcebergExecutor
from src.execution.mode2.executor_immediate import ImmediateConfig, ImmediateExecutor
from src.execution.mode2.executor_twap import TWAPConfig, TWAPExecutor
from src.execution.mode2.executor_vwap import VWAPConfig, VWAPExecutor
from src.execution.mode2.intent import (
    AlgoType,
    IntentIdGenerator,
    IntentRegistry,
    Offset,
    OrderIntent,
    Side,
    Urgency,
)


__all__ = [
    "TERMINAL_STATUSES",
    "AlgoType",
    "ExecutionEngine",
    "ExecutionEngineConfig",
    "ExecutionPlan",
    "ExecutionPlanContext",
    "ExecutionPlanStatus",
    "ExecutionProgress",
    "ExecutorAction",
    "ExecutorActionType",
    "ExecutorBase",
    "ExecutorConfig",
    "ExecutorStatus",
    "FilledOrder",
    "IcebergConfig",
    "IcebergExecutor",
    "ImmediateConfig",
    "ImmediateExecutor",
    "IntentIdGenerator",
    "IntentRegistry",
    "Mode2AuditEvent",
    "Mode2AuditEventType",
    "Offset",
    "OrderEvent",
    "OrderIntent",
    "PendingOrder",
    "Side",
    "SliceInfo",
    "TWAPConfig",
    "TWAPExecutor",
    "Urgency",
    "VWAPConfig",
    "VWAPExecutor",
    "create_intent_completed_event",
    "create_intent_created_event",
    "create_intent_failed_event",
    "create_intent_rejected_event",
    "create_plan_cancelled_event",
    "create_plan_created_event",
    "create_plan_paused_event",
    "create_plan_resumed_event",
    "create_slice_ack_event",
    "create_slice_cancelled_event",
    "create_slice_filled_event",
    "create_slice_rejected_event",
    "create_slice_sent_event",
]

__version__ = "4.2.0"
