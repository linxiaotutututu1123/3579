"""
OrderFSM - 订单状态机.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.3
V2 Scenarios:
- FSM.STRICT.TRANSITIONS: 严格模式所有转移
- FSM.TOLERANT.IDEMPOTENT: 容错模式幂等处理
- FSM.CANCEL_WHILE_FILL: 撤单途中成交
- FSM.STATUS_4_MAPPING: OrderStatus='4' 映射

军规级要求:
- 状态机是订单状态唯一真相源
- 严格模式：非法转移抛异常
- 容错模式：非法转移忽略并记录
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, ClassVar


class OrderState(Enum):
    """订单状态枚举.

    14 个状态，6 个终态。
    """

    # 非终态
    CREATED = "CREATED"  # 已创建，未提交
    SUBMITTING = "SUBMITTING"  # 提交中，等待 ack
    PENDING = "PENDING"  # 已报，等待成交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    CANCEL_SUBMITTING = "CANCEL_SUBMITTING"  # 撤单提交中
    QUERYING = "QUERYING"  # 查询中（超时后）
    RETRY_PENDING = "RETRY_PENDING"  # 等待重试
    CHASE_PENDING = "CHASE_PENDING"  # 等待追价

    # 终态
    FILLED = "FILLED"  # 全部成交
    CANCELLED = "CANCELLED"  # 已撤单
    PARTIAL_CANCELLED = "PARTIAL_CANCELLED"  # 部分成交已撤
    CANCEL_REJECTED = "CANCEL_REJECTED"  # 撤单被拒
    REJECTED = "REJECTED"  # 报单被拒
    ERROR = "ERROR"  # 错误


class OrderEvent(Enum):
    """订单事件枚举."""

    # 提交相关
    SUBMIT = "SUBMIT"  # 提交订单
    ACK = "ACK"  # 收到确认
    REJECT = "REJECT"  # 报单被拒

    # 成交相关
    PARTIAL_FILL = "PARTIAL_FILL"  # 部分成交
    FILL = "FILL"  # 全部成交

    # 撤单相关
    CANCEL_REQUEST = "CANCEL_REQUEST"  # 请求撤单
    CANCEL_ACK = "CANCEL_ACK"  # 撤单确认
    CANCEL_REJECT = "CANCEL_REJECT"  # 撤单被拒

    # 超时相关
    ACK_TIMEOUT = "ACK_TIMEOUT"  # Ack 超时
    FILL_TIMEOUT = "FILL_TIMEOUT"  # Fill 超时
    CANCEL_TIMEOUT = "CANCEL_TIMEOUT"  # Cancel 超时

    # 重试/追价
    RETRY = "RETRY"  # 重试
    CHASE = "CHASE"  # 追价
    RETRY_COMPLETE = "RETRY_COMPLETE"  # 重试完成
    CHASE_COMPLETE = "CHASE_COMPLETE"  # 追价完成

    # 特殊
    QUERY = "QUERY"  # 查询
    QUERY_RESULT = "QUERY_RESULT"  # 查询结果
    STATUS_4 = "STATUS_4"  # CTP OrderStatus='4'
    ERROR_OCCURRED = "ERROR_OCCURRED"  # 发生错误


# 终态集合
TERMINAL_STATES = frozenset(
    [
        OrderState.FILLED,
        OrderState.CANCELLED,
        OrderState.PARTIAL_CANCELLED,
        OrderState.CANCEL_REJECTED,
        OrderState.REJECTED,
        OrderState.ERROR,
    ]
)

# 可撤单状态
CANCELLABLE_STATES = frozenset(
    [
        OrderState.PENDING,
        OrderState.PARTIAL_FILLED,
    ]
)


class OrderFSM:
    """订单状态机.

    V2 Scenarios:
    - FSM.STRICT.TRANSITIONS: 严格模式所有转移
    - FSM.TOLERANT.IDEMPOTENT: 容错模式幂等处理
    - FSM.CANCEL_WHILE_FILL: 撤单途中成交
    - FSM.STATUS_4_MAPPING: OrderStatus='4' 映射

    支持两种模式:
    - strict: 非法转移抛出 ValueError
    - tolerant: 非法转移忽略并调用回调
    """

    # 状态转移表: (当前状态, 事件) -> 目标状态
    TRANSITIONS: ClassVar[dict[tuple[OrderState, OrderEvent], OrderState]] = {
        # CREATED 状态
        (OrderState.CREATED, OrderEvent.SUBMIT): OrderState.SUBMITTING,
        # SUBMITTING 状态
        (OrderState.SUBMITTING, OrderEvent.ACK): OrderState.PENDING,
        (OrderState.SUBMITTING, OrderEvent.REJECT): OrderState.REJECTED,
        (OrderState.SUBMITTING, OrderEvent.ACK_TIMEOUT): OrderState.QUERYING,
        (OrderState.SUBMITTING, OrderEvent.FILL): OrderState.FILLED,
        (OrderState.SUBMITTING, OrderEvent.PARTIAL_FILL): OrderState.PARTIAL_FILLED,
        # PENDING 状态
        (OrderState.PENDING, OrderEvent.PARTIAL_FILL): OrderState.PARTIAL_FILLED,
        (OrderState.PENDING, OrderEvent.FILL): OrderState.FILLED,
        (OrderState.PENDING, OrderEvent.CANCEL_REQUEST): OrderState.CANCEL_SUBMITTING,
        (OrderState.PENDING, OrderEvent.FILL_TIMEOUT): OrderState.CANCEL_SUBMITTING,
        # PARTIAL_FILLED 状态
        (OrderState.PARTIAL_FILLED, OrderEvent.PARTIAL_FILL): OrderState.PARTIAL_FILLED,
        (OrderState.PARTIAL_FILLED, OrderEvent.FILL): OrderState.FILLED,
        (
            OrderState.PARTIAL_FILLED,
            OrderEvent.CANCEL_REQUEST,
        ): OrderState.CANCEL_SUBMITTING,
        (
            OrderState.PARTIAL_FILLED,
            OrderEvent.FILL_TIMEOUT,
        ): OrderState.CANCEL_SUBMITTING,
        (OrderState.PARTIAL_FILLED, OrderEvent.CHASE): OrderState.CHASE_PENDING,
        # CANCEL_SUBMITTING 状态
        (OrderState.CANCEL_SUBMITTING, OrderEvent.CANCEL_ACK): OrderState.CANCELLED,
        (
            OrderState.CANCEL_SUBMITTING,
            OrderEvent.CANCEL_REJECT,
        ): OrderState.CANCEL_REJECTED,
        (
            OrderState.CANCEL_SUBMITTING,
            OrderEvent.FILL,
        ): OrderState.FILLED,  # 撤单途中成交
        (
            OrderState.CANCEL_SUBMITTING,
            OrderEvent.PARTIAL_FILL,
        ): OrderState.PARTIAL_CANCELLED,
        (OrderState.CANCEL_SUBMITTING, OrderEvent.CANCEL_TIMEOUT): OrderState.QUERYING,
        (
            OrderState.CANCEL_SUBMITTING,
            OrderEvent.STATUS_4,
        ): OrderState.ERROR,  # STATUS_4 无成交
        # QUERYING 状态
        (OrderState.QUERYING, OrderEvent.QUERY_RESULT): OrderState.PENDING,
        (OrderState.QUERYING, OrderEvent.FILL): OrderState.FILLED,
        (OrderState.QUERYING, OrderEvent.CANCEL_ACK): OrderState.CANCELLED,
        (OrderState.QUERYING, OrderEvent.ERROR_OCCURRED): OrderState.ERROR,
        # RETRY_PENDING 状态
        (OrderState.RETRY_PENDING, OrderEvent.RETRY_COMPLETE): OrderState.SUBMITTING,
        (OrderState.RETRY_PENDING, OrderEvent.ERROR_OCCURRED): OrderState.ERROR,
        # CHASE_PENDING 状态
        (OrderState.CHASE_PENDING, OrderEvent.CHASE_COMPLETE): OrderState.SUBMITTING,
        (OrderState.CHASE_PENDING, OrderEvent.ERROR_OCCURRED): OrderState.ERROR,
    }

    def __init__(
        self,
        initial_state: OrderState = OrderState.CREATED,
        mode: str = "tolerant",
        on_invalid_transition: Callable[[OrderState, OrderEvent, str], None]
        | None = None,
    ) -> None:
        """初始化状态机.

        Args:
            initial_state: 初始状态
            mode: 模式 (strict/tolerant)
            on_invalid_transition: 非法转移回调 (状态, 事件, 原因)
        """
        self._state = initial_state
        self._mode = mode
        self._on_invalid_transition = on_invalid_transition
        self._transition_count = 0
        self._filled_qty = 0

    @property
    def state(self) -> OrderState:
        """当前状态."""
        return self._state

    @property
    def mode(self) -> str:
        """模式."""
        return self._mode

    @property
    def transition_count(self) -> int:
        """转移次数."""
        return self._transition_count

    @property
    def filled_qty(self) -> int:
        """已成交数量."""
        return self._filled_qty

    def is_terminal(self) -> bool:
        """是否终态."""
        return self._state in TERMINAL_STATES

    def can_cancel(self) -> bool:
        """是否可撤单."""
        return self._state in CANCELLABLE_STATES

    def transition(self, event: OrderEvent, filled_qty: int = 0) -> OrderState:
        """执行状态转移.

        V2 Scenarios:
        - FSM.STRICT.TRANSITIONS: 严格模式所有转移
        - FSM.TOLERANT.IDEMPOTENT: 容错模式幂等处理

        Args:
            event: 事件
            filled_qty: 成交数量（用于部分成交）

        Returns:
            转移后的状态

        Raises:
            ValueError: 严格模式下非法转移
        """
        # 终态后忽略所有事件 (容错模式幂等)
        if self.is_terminal():
            reason = f"Terminal state {self._state.value}, ignoring {event.value}"
            self._handle_invalid_transition(event, reason)
            return self._state

        key = (self._state, event)
        target = self.TRANSITIONS.get(key)

        if target is None:
            reason = f"No transition from {self._state.value} on {event.value}"
            self._handle_invalid_transition(event, reason)
            return self._state

        # 更新成交数量
        if event in (OrderEvent.PARTIAL_FILL, OrderEvent.FILL):
            self._filled_qty += filled_qty

        # 特殊处理: STATUS_4 有成交时转 PARTIAL_CANCELLED
        if event == OrderEvent.STATUS_4 and self._filled_qty > 0:
            target = OrderState.PARTIAL_CANCELLED

        self._state = target
        self._transition_count += 1

        return self._state

    def _handle_invalid_transition(self, event: OrderEvent, reason: str) -> None:
        """处理非法转移.

        Args:
            event: 事件
            reason: 原因
        """
        if self._on_invalid_transition:
            self._on_invalid_transition(self._state, event, reason)

        if self._mode == "strict":
            raise ValueError(reason)

    def reset(self, initial_state: OrderState = OrderState.CREATED) -> None:
        """重置状态机.

        Args:
            initial_state: 初始状态
        """
        self._state = initial_state
        self._transition_count = 0
        self._filled_qty = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "state": self._state.value,
            "mode": self._mode,
            "is_terminal": self.is_terminal(),
            "can_cancel": self.can_cancel(),
            "transition_count": self._transition_count,
            "filled_qty": self._filled_qty,
        }


def handle_cancel_while_fill(fsm: OrderFSM, event: OrderEvent) -> OrderState:
    """处理撤单途中成交.

    V2 Scenario: FSM.CANCEL_WHILE_FILL

    当订单处于 CANCEL_SUBMITTING 状态时收到成交:
    - FILL -> 转为 FILLED（忽略后续撤单确认）
    - PARTIAL_FILL -> 转为 PARTIAL_CANCELLED

    Args:
        fsm: 状态机
        event: 事件

    Returns:
        转移后状态
    """
    return fsm.transition(event)


def handle_status_4(fsm: OrderFSM, has_fills: bool) -> OrderState:
    """处理 CTP OrderStatus='4'.

    V2 Scenario: FSM.STATUS_4_MAPPING

    OrderStatus='4' 表示订单已报未成交被撤销:
    - 无成交: 转为 ERROR + reduce-only
    - 有成交: 转为 PARTIAL_CANCELLED

    Args:
        fsm: 状态机
        has_fills: 是否有成交

    Returns:
        转移后状态
    """
    return fsm.transition(OrderEvent.STATUS_4)
