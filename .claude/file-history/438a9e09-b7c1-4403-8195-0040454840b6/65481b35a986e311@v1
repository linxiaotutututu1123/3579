"""
OrderTrail - 订单轨迹事件

V3PRO+ Platform Component - Phase 1
V2 SPEC: 7.1

军规级要求:
- 订单全生命周期追踪
- 状态转移可审计
- 成交明细完整
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class OrderEventType(str, Enum):
    """订单事件类型."""

    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_CANCEL_REJECTED = "ORDER_CANCEL_REJECTED"
    ORDER_EXPIRED = "ORDER_EXPIRED"


@dataclass
class OrderStateEvent:
    """订单状态变更事件.

    记录订单在 FSM 中的状态转移。

    Attributes:
        ts: 时间戳
        run_id: 运行 ID
        exec_id: 执行 ID
        order_local_id: 本地订单 ID
        order_ref: CTP 订单引用
        order_sys_id: 交易所系统号
        symbol: 合约代码
        state_from: 原状态
        state_to: 目标状态
        trigger_event: 触发事件
        details: 详细信息
    """

    ts: float
    run_id: str
    exec_id: str
    order_local_id: str
    symbol: str
    state_from: str
    state_to: str
    trigger_event: str
    order_ref: str | None = None
    order_sys_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "ORDER_STATE"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        return data


@dataclass
class ExecEvent:
    """执行事件.

    记录订单提交、撤销等执行操作。

    Attributes:
        ts: 时间戳
        run_id: 运行 ID
        exec_id: 执行 ID
        action: 操作类型 (submit/cancel/modify)
        order_local_id: 本地订单 ID
        symbol: 合约代码
        side: 方向 (BUY/SELL)
        offset: 开平标志 (OPEN/CLOSE/CLOSE_TODAY)
        price: 委托价格
        qty: 委托数量
        order_type: 订单类型 (LIMIT/MARKET)
        result: 执行结果 (success/failed)
        error_code: 错误代码
        error_msg: 错误信息
    """

    ts: float
    run_id: str
    exec_id: str
    action: str
    order_local_id: str
    symbol: str
    side: str
    offset: str
    price: float
    qty: int
    order_type: str = "LIMIT"
    result: str = "success"
    error_code: str | None = None
    error_msg: str | None = None

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "EXEC"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        return data


@dataclass
class TradeEvent:
    """成交事件.

    记录订单成交明细。

    Attributes:
        ts: 时间戳
        run_id: 运行 ID
        exec_id: 执行 ID
        trade_id: 成交编号
        order_local_id: 本地订单 ID
        order_sys_id: 交易所系统号
        symbol: 合约代码
        side: 方向
        offset: 开平标志
        price: 成交价格
        qty: 成交数量
        commission: 手续费
        exchange_ts: 交易所时间戳
    """

    ts: float
    run_id: str
    exec_id: str
    trade_id: str
    order_local_id: str
    symbol: str
    side: str
    offset: str
    price: float
    qty: int
    order_sys_id: str | None = None
    commission: float = 0.0
    exchange_ts: float | None = None

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "TRADE"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        return data
