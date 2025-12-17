"""
Mode 2 审计事件定义.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M3(完整审计), M7(回放一致)

V4PRO Scenarios:
- MODE2.AUDIT.INTENT_CREATED: 意图创建审计
- MODE2.AUDIT.PLAN_CREATED: 计划创建审计
- MODE2.AUDIT.SLICE_SENT: 分片发送审计
- MODE2.AUDIT.SLICE_FILLED: 分片成交审计
- MODE2.AUDIT.INTENT_COMPLETED: 意图完成审计

审计事件链 (军规级要求):
    INTENT_CREATED -> PLAN_CREATED -> SLICE_SENT* -> SLICE_FILLED* -> INTENT_COMPLETED

军规级要求:
- 每个事件必须包含 intent_id 用于追溯 (M3)
- 所有时间戳必须使用毫秒精度 (M7)
- 事件必须包含完整上下文信息 (M3)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.execution.mode2.intent import OrderIntent


class Mode2AuditEventType(str, Enum):
    """Mode 2 审计事件类型.

    V4PRO Scenario: MODE2.AUDIT.*

    事件类型按执行生命周期排列:
    - INTENT_CREATED: 意图创建(策略层输出)
    - INTENT_REJECTED: 意图被拒绝(幂等检查失败等)
    - PLAN_CREATED: 执行计划创建
    - SLICE_SCHEDULED: 分片调度
    - SLICE_SENT: 分片订单发送
    - SLICE_ACK: 分片订单确认
    - SLICE_PARTIAL_FILL: 分片部分成交
    - SLICE_FILLED: 分片完全成交
    - SLICE_REJECTED: 分片被拒绝
    - SLICE_CANCELLED: 分片被取消
    - PLAN_PAUSED: 计划暂停
    - PLAN_RESUMED: 计划恢复
    - PLAN_CANCELLED: 计划取消
    - INTENT_COMPLETED: 意图执行完成
    - INTENT_FAILED: 意图执行失败
    """

    INTENT_CREATED = "MODE2.INTENT_CREATED"
    INTENT_REJECTED = "MODE2.INTENT_REJECTED"
    PLAN_CREATED = "MODE2.PLAN_CREATED"
    SLICE_SCHEDULED = "MODE2.SLICE_SCHEDULED"
    SLICE_SENT = "MODE2.SLICE_SENT"
    SLICE_ACK = "MODE2.SLICE_ACK"
    SLICE_PARTIAL_FILL = "MODE2.SLICE_PARTIAL_FILL"
    SLICE_FILLED = "MODE2.SLICE_FILLED"
    SLICE_REJECTED = "MODE2.SLICE_REJECTED"
    SLICE_CANCELLED = "MODE2.SLICE_CANCELLED"
    PLAN_PAUSED = "MODE2.PLAN_PAUSED"
    PLAN_RESUMED = "MODE2.PLAN_RESUMED"
    PLAN_CANCELLED = "MODE2.PLAN_CANCELLED"
    INTENT_COMPLETED = "MODE2.INTENT_COMPLETED"
    INTENT_FAILED = "MODE2.INTENT_FAILED"


@dataclass
class Mode2AuditEvent:
    """Mode 2 审计事件.

    V4PRO Scenario: MODE2.AUDIT.*
    军规覆盖: M3(完整审计), M7(回放一致)

    所有 Mode 2 执行事件的统一格式。

    Attributes:
        event_type: 事件类型
        intent_id: 意图ID(幂等键)
        ts: 事件时间戳(毫秒)
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        instrument: 合约代码
        side: 交易方向
        offset: 开平方向
        qty: 数量
        price: 价格
        filled_qty: 成交数量
        filled_price: 成交价格
        remaining_qty: 剩余数量
        algo: 执行算法
        reason: 事件原因/说明
        error_code: 错误码
        error_msg: 错误信息
        metadata: 扩展元数据
    """

    event_type: Mode2AuditEventType
    intent_id: str
    ts: int = field(default_factory=lambda: int(time.time() * 1000))
    plan_id: str = ""
    client_order_id: str = ""
    slice_index: int = -1
    instrument: str = ""
    side: str = ""
    offset: str = ""
    qty: int = 0
    price: float = 0.0
    filled_qty: int = 0
    filled_price: float = 0.0
    remaining_qty: int = 0
    algo: str = ""
    reason: str = ""
    error_code: str = ""
    error_msg: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典(用于 JSONL 序列化).

        Returns:
            包含所有字段的字典
        """
        return {
            "event_type": self.event_type.value,
            "intent_id": self.intent_id,
            "ts": self.ts,
            "plan_id": self.plan_id,
            "client_order_id": self.client_order_id,
            "slice_index": self.slice_index,
            "instrument": self.instrument,
            "side": self.side,
            "offset": self.offset,
            "qty": self.qty,
            "price": self.price,
            "filled_qty": self.filled_qty,
            "filled_price": self.filled_price,
            "remaining_qty": self.remaining_qty,
            "algo": self.algo,
            "reason": self.reason,
            "error_code": self.error_code,
            "error_msg": self.error_msg,
            "metadata": self.metadata,
        }


def create_intent_created_event(intent: OrderIntent) -> Mode2AuditEvent:
    """创建意图创建事件.

    V4PRO Scenario: MODE2.AUDIT.INTENT_CREATED

    Args:
        intent: 交易意图

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.INTENT_CREATED,
        intent_id=intent.intent_id,
        ts=int(time.time() * 1000),
        instrument=intent.instrument,
        side=intent.side.value,
        offset=intent.offset.value,
        qty=intent.target_qty,
        price=intent.limit_price or 0.0,
        algo=intent.algo.value,
        reason=f"策略 {intent.strategy_id} 创建交易意图",
        metadata={
            "strategy_id": intent.strategy_id,
            "decision_hash": intent.decision_hash,
            "urgency": intent.urgency.value,
            "signal_ts": intent.signal_ts,
            "expire_ts": intent.expire_ts,
            "parent_intent_id": intent.parent_intent_id,
        },
    )


def create_intent_rejected_event(
    intent: OrderIntent,
    error_code: str,
    error_msg: str,
) -> Mode2AuditEvent:
    """创建意图拒绝事件.

    V4PRO Scenario: MODE2.AUDIT.INTENT_REJECTED

    Args:
        intent: 交易意图
        error_code: 错误码
        error_msg: 错误信息

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.INTENT_REJECTED,
        intent_id=intent.intent_id,
        ts=int(time.time() * 1000),
        instrument=intent.instrument,
        side=intent.side.value,
        offset=intent.offset.value,
        qty=intent.target_qty,
        algo=intent.algo.value,
        error_code=error_code,
        error_msg=error_msg,
        reason=f"意图被拒绝: {error_msg}",
        metadata={
            "strategy_id": intent.strategy_id,
        },
    )


def create_plan_created_event(
    intent: OrderIntent,
    plan_id: str,
    slice_count: int,
    algo: str,
) -> Mode2AuditEvent:
    """创建计划创建事件.

    V4PRO Scenario: MODE2.AUDIT.PLAN_CREATED

    Args:
        intent: 交易意图
        plan_id: 计划ID
        slice_count: 分片数量
        algo: 执行算法

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.PLAN_CREATED,
        intent_id=intent.intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        instrument=intent.instrument,
        side=intent.side.value,
        offset=intent.offset.value,
        qty=intent.target_qty,
        price=intent.limit_price or 0.0,
        algo=algo,
        reason=f"创建执行计划, 分片数={slice_count}",
        metadata={
            "slice_count": slice_count,
            "strategy_id": intent.strategy_id,
            "urgency": intent.urgency.value,
        },
    )


def create_slice_sent_event(
    intent_id: str,
    plan_id: str,
    client_order_id: str,
    slice_index: int,
    instrument: str,
    side: str,
    offset: str,
    qty: int,
    price: float,
) -> Mode2AuditEvent:
    """创建分片发送事件.

    V4PRO Scenario: MODE2.AUDIT.SLICE_SENT

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        instrument: 合约代码
        side: 交易方向
        offset: 开平方向
        qty: 数量
        price: 价格

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.SLICE_SENT,
        intent_id=intent_id,
        plan_id=plan_id,
        client_order_id=client_order_id,
        slice_index=slice_index,
        ts=int(time.time() * 1000),
        instrument=instrument,
        side=side,
        offset=offset,
        qty=qty,
        price=price,
        reason=f"发送分片订单 #{slice_index}",
    )


def create_slice_ack_event(
    intent_id: str,
    plan_id: str,
    client_order_id: str,
    slice_index: int,
    exchange_order_id: str = "",
) -> Mode2AuditEvent:
    """创建分片确认事件.

    V4PRO Scenario: MODE2.AUDIT.SLICE_ACK

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        exchange_order_id: 交易所订单ID

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.SLICE_ACK,
        intent_id=intent_id,
        plan_id=plan_id,
        client_order_id=client_order_id,
        slice_index=slice_index,
        ts=int(time.time() * 1000),
        reason=f"分片订单 #{slice_index} 已确认",
        metadata={
            "exchange_order_id": exchange_order_id,
        },
    )


def create_slice_filled_event(
    intent_id: str,
    plan_id: str,
    client_order_id: str,
    slice_index: int,
    filled_qty: int,
    filled_price: float,
    remaining_qty: int,
    is_partial: bool = False,
) -> Mode2AuditEvent:
    """创建分片成交事件.

    V4PRO Scenario: MODE2.AUDIT.SLICE_FILLED / MODE2.AUDIT.SLICE_PARTIAL_FILL

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        filled_qty: 本次成交数量
        filled_price: 成交价格
        remaining_qty: 剩余数量
        is_partial: 是否部分成交

    Returns:
        审计事件
    """
    event_type = (
        Mode2AuditEventType.SLICE_PARTIAL_FILL if is_partial else Mode2AuditEventType.SLICE_FILLED
    )
    return Mode2AuditEvent(
        event_type=event_type,
        intent_id=intent_id,
        plan_id=plan_id,
        client_order_id=client_order_id,
        slice_index=slice_index,
        ts=int(time.time() * 1000),
        filled_qty=filled_qty,
        filled_price=filled_price,
        remaining_qty=remaining_qty,
        reason=f"分片 #{slice_index} {'部分成交' if is_partial else '完全成交'}",
    )


def create_slice_rejected_event(
    intent_id: str,
    plan_id: str,
    client_order_id: str,
    slice_index: int,
    error_code: str,
    error_msg: str,
) -> Mode2AuditEvent:
    """创建分片拒绝事件.

    V4PRO Scenario: MODE2.AUDIT.SLICE_REJECTED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        error_code: 错误码
        error_msg: 错误信息

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.SLICE_REJECTED,
        intent_id=intent_id,
        plan_id=plan_id,
        client_order_id=client_order_id,
        slice_index=slice_index,
        ts=int(time.time() * 1000),
        error_code=error_code,
        error_msg=error_msg,
        reason=f"分片 #{slice_index} 被拒绝: {error_msg}",
    )


def create_slice_cancelled_event(
    intent_id: str,
    plan_id: str,
    client_order_id: str,
    slice_index: int,
    reason: str = "",
) -> Mode2AuditEvent:
    """创建分片取消事件.

    V4PRO Scenario: MODE2.AUDIT.SLICE_CANCELLED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        client_order_id: 客户订单ID
        slice_index: 分片索引
        reason: 取消原因

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.SLICE_CANCELLED,
        intent_id=intent_id,
        plan_id=plan_id,
        client_order_id=client_order_id,
        slice_index=slice_index,
        ts=int(time.time() * 1000),
        reason=reason or f"分片 #{slice_index} 已取消",
    )


def create_plan_paused_event(
    intent_id: str,
    plan_id: str,
    reason: str = "",
) -> Mode2AuditEvent:
    """创建计划暂停事件.

    V4PRO Scenario: MODE2.AUDIT.PLAN_PAUSED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        reason: 暂停原因

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.PLAN_PAUSED,
        intent_id=intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        reason=reason or "执行计划已暂停",
    )


def create_plan_resumed_event(
    intent_id: str,
    plan_id: str,
    reason: str = "",
) -> Mode2AuditEvent:
    """创建计划恢复事件.

    V4PRO Scenario: MODE2.AUDIT.PLAN_RESUMED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        reason: 恢复原因

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.PLAN_RESUMED,
        intent_id=intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        reason=reason or "执行计划已恢复",
    )


def create_plan_cancelled_event(
    intent_id: str,
    plan_id: str,
    filled_qty: int,
    remaining_qty: int,
    reason: str = "",
) -> Mode2AuditEvent:
    """创建计划取消事件.

    V4PRO Scenario: MODE2.AUDIT.PLAN_CANCELLED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        filled_qty: 已成交数量
        remaining_qty: 未成交数量
        reason: 取消原因

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.PLAN_CANCELLED,
        intent_id=intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        filled_qty=filled_qty,
        remaining_qty=remaining_qty,
        reason=reason or "执行计划已取消",
    )


def create_intent_completed_event(
    intent_id: str,
    plan_id: str,
    filled_qty: int,
    avg_price: float,
    total_cost: float,
    slice_count: int,
    elapsed_seconds: float,
) -> Mode2AuditEvent:
    """创建意图完成事件.

    V4PRO Scenario: MODE2.AUDIT.INTENT_COMPLETED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        filled_qty: 成交总量
        avg_price: 平均成交价格
        total_cost: 总成本
        slice_count: 分片数量
        elapsed_seconds: 执行耗时(秒)

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.INTENT_COMPLETED,
        intent_id=intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        filled_qty=filled_qty,
        filled_price=avg_price,
        reason=f"意图执行完成, 成交量={filled_qty}, 均价={avg_price:.4f}",
        metadata={
            "total_cost": total_cost,
            "slice_count": slice_count,
            "elapsed_seconds": elapsed_seconds,
        },
    )


def create_intent_failed_event(
    intent_id: str,
    plan_id: str,
    filled_qty: int,
    remaining_qty: int,
    error_code: str,
    error_msg: str,
) -> Mode2AuditEvent:
    """创建意图失败事件.

    V4PRO Scenario: MODE2.AUDIT.INTENT_FAILED

    Args:
        intent_id: 意图ID
        plan_id: 计划ID
        filled_qty: 已成交数量
        remaining_qty: 未成交数量
        error_code: 错误码
        error_msg: 错误信息

    Returns:
        审计事件
    """
    return Mode2AuditEvent(
        event_type=Mode2AuditEventType.INTENT_FAILED,
        intent_id=intent_id,
        plan_id=plan_id,
        ts=int(time.time() * 1000),
        filled_qty=filled_qty,
        remaining_qty=remaining_qty,
        error_code=error_code,
        error_msg=error_msg,
        reason=f"意图执行失败: {error_msg}",
    )
