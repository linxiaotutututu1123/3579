"""
Auto Order Execution Module.

V3PRO+ Platform Component - Phase 2
V2 SPEC: Chapter 5

Exports:
- OrderContext: 订单标识映射
- OrderState, OrderEvent, OrderFSM: 订单状态机
- TimeoutManager: 超时管理
- RetryPolicy: 重试策略
- ExecContext: 执行上下文
- PositionTracker: 持仓追踪
- AutoOrderEngine: 自动下单引擎
"""

from src.execution.auto.engine import AutoOrderEngine
from src.execution.auto.exec_context import ExecContext
from src.execution.auto.order_context import OrderContext
from src.execution.auto.position_tracker import PositionTracker, ReconcileResult
from src.execution.auto.retry import RetryPolicy
from src.execution.auto.state_machine import OrderEvent, OrderFSM, OrderState
from src.execution.auto.timeout import TimeoutManager


__all__ = [
    "AutoOrderEngine",
    "ExecContext",
    "OrderContext",
    "OrderEvent",
    "OrderFSM",
    "OrderState",
    "PositionTracker",
    "ReconcileResult",
    "RetryPolicy",
    "TimeoutManager",
]
