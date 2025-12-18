"""
Mode 2 交易执行管道模块.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M1(单一信号源), M2(幂等执行), M3(完整审计), M7(回放一致)

核心组件:
- OrderIntent: 策略层输出的交易意图
- IntentIdGenerator: 幂等键生成器
- ExecutionEngine: 执行引擎
- Executor: 执行器接口 (TWAP/VWAP/Iceberg)
"""

from __future__ import annotations

from src.execution.mode2.intent import (
    AlgoType,
    IntentIdGenerator,
    OrderIntent,
    Urgency,
)
from src.execution.mode2.engine import (
    ExecutionEngine,
    ExecutionEngineConfig,
    ExecutionPlan,
)
from src.execution.mode2.executor_base import (
    ExecutorAction,
    ExecutorActionType,
    ExecutorBase,
    ExecutorConfig,
    ExecutorStatus,
)
from src.execution.mode2.executor_twap import TWAPExecutor, TWAPConfig
from src.execution.mode2.executor_vwap import VWAPExecutor, VWAPConfig
from src.execution.mode2.executor_iceberg import IcebergExecutor, IcebergConfig
from src.execution.mode2.executor_immediate import ImmediateExecutor
from src.execution.mode2.audit_events import (
    Mode2AuditEvent,
    Mode2AuditEventType,
    create_intent_created_event,
    create_plan_created_event,
    create_slice_sent_event,
    create_slice_filled_event,
    create_intent_completed_event,
)

__all__ = [
    # Intent
    "OrderIntent",
    "IntentIdGenerator",
    "AlgoType",
    "Urgency",
    # Engine
    "ExecutionEngine",
    "ExecutionEngineConfig",
    "ExecutionPlan",
    # Executor Base
    "ExecutorBase",
    "ExecutorConfig",
    "ExecutorAction",
    "ExecutorActionType",
    "ExecutorStatus",
    # Executors
    "TWAPExecutor",
    "TWAPConfig",
    "VWAPExecutor",
    "VWAPConfig",
    "IcebergExecutor",
    "IcebergConfig",
    "ImmediateExecutor",
    # Audit
    "Mode2AuditEvent",
    "Mode2AuditEventType",
    "create_intent_created_event",
    "create_plan_created_event",
    "create_slice_sent_event",
    "create_slice_filled_event",
    "create_intent_completed_event",
]

__version__ = "4.2.0"
