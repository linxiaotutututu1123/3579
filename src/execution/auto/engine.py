"""
AutoOrderEngine - 自动下单引擎.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.4
V2 Scenarios:
- EXEC.ENGINE.PIPELINE: 订单提交管线
- EXEC.CANCEL_REPRICE.TIMEOUT: 追价超时撤单
- EXEC.PARTIAL.REPRICE: 部分成交追价

军规级要求:
- 整合 FSM + Timeout + Retry
- 所有订单事件写入审计
- 支持追价和重试
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.execution.auto.order_context import OrderContext, OrderContextRegistry
from src.execution.auto.retry import RetryConfig, RetryPolicy, RetryReason
from src.execution.auto.state_machine import (
    OrderEvent,
    OrderFSM,
    OrderState,
)
from src.execution.auto.timeout import TimeoutConfig, TimeoutManager, TimeoutType


if TYPE_CHECKING:
    from src.execution.broker import Broker


@dataclass
class EngineConfig:
    """引擎配置.

    Attributes:
        timeout_config: 超时配置
        retry_config: 重试配置
        enable_reprice: 是否启用追价
    """

    timeout_config: TimeoutConfig | None = None
    retry_config: RetryConfig | None = None
    enable_reprice: bool = True


@dataclass
class OrderResult:
    """订单结果.

    Attributes:
        local_id: 本地订单 ID
        state: 最终状态
        filled_qty: 成交数量
        avg_price: 平均价格
        error: 错误信息
    """

    local_id: str
    state: OrderState
    filled_qty: int = 0
    avg_price: float = 0.0
    error: str | None = None

    def is_success(self) -> bool:
        """是否成功."""
        return self.state == OrderState.FILLED

    def is_partial(self) -> bool:
        """是否部分成交."""
        return self.state == OrderState.PARTIAL_CANCELLED and self.filled_qty > 0


class AutoOrderEngine:
    """自动下单引擎.

    V2 Scenarios:
    - EXEC.ENGINE.PIPELINE: 订单提交管线
    - EXEC.CANCEL_REPRICE.TIMEOUT: 追价超时撤单
    - EXEC.PARTIAL.REPRICE: 部分成交追价

    整合订单状态机、超时管理、重试策略。
    """

    def __init__(
        self,
        broker: Broker | None = None,
        config: EngineConfig | None = None,
        on_order_event: Callable[[str, OrderState, OrderEvent], None] | None = None,
    ) -> None:
        """初始化自动下单引擎.

        Args:
            broker: Broker 实例
            config: 引擎配置
            on_order_event: 订单事件回调 (local_id, state, event)
        """
        self._broker = broker
        self._config = config or EngineConfig()
        self._on_order_event = on_order_event

        self._registry = OrderContextRegistry()
        self._fsm_map: dict[str, OrderFSM] = {}
        self._timeout_mgr = TimeoutManager(
            config=self._config.timeout_config,
            on_timeout=self._on_timeout,
        )
        self._retry_policy = RetryPolicy(config=self._config.retry_config)

        self._results: dict[str, OrderResult] = {}

    @property
    def registry(self) -> OrderContextRegistry:
        """订单注册表."""
        return self._registry

    @property
    def timeout_manager(self) -> TimeoutManager:
        """超时管理器."""
        return self._timeout_mgr

    @property
    def retry_policy(self) -> RetryPolicy:
        """重试策略."""
        return self._retry_policy

    def submit(self, ctx: OrderContext) -> str:
        """提交订单.

        V2 Scenario: EXEC.ENGINE.PIPELINE

        Args:
            ctx: 订单上下文

        Returns:
            本地订单 ID
        """
        local_id = ctx.local_id
        ctx.created_at = time.time()

        # 注册订单
        self._registry.register(ctx)

        # 创建状态机
        fsm = OrderFSM(mode="tolerant", on_invalid_transition=self._on_invalid_transition)
        self._fsm_map[local_id] = fsm

        # 转为 SUBMITTING
        fsm.transition(OrderEvent.SUBMIT)
        self._emit_event(local_id, fsm.state, OrderEvent.SUBMIT)

        # 注册 ACK 超时
        self._timeout_mgr.register_ack_timeout(local_id)

        # 实际提交（如果有 broker）
        if self._broker:
            try:
                order_ref = self._broker.place_order(
                    symbol=ctx.symbol,
                    direction=ctx.direction,
                    offset=ctx.offset,
                    qty=ctx.qty,
                    price=ctx.price,
                )
                if order_ref:
                    self._registry.update_order_ref(local_id, order_ref)
            except Exception as e:
                self._handle_submit_error(local_id, str(e))

        return local_id

    def cancel(self, local_id: str) -> bool:
        """撤单.

        Args:
            local_id: 本地订单 ID

        Returns:
            是否成功发起撤单
        """
        fsm = self._fsm_map.get(local_id)
        if fsm is None:
            return False

        if not fsm.can_cancel():
            return False

        # 转为 CANCEL_SUBMITTING
        fsm.transition(OrderEvent.CANCEL_REQUEST)
        self._emit_event(local_id, fsm.state, OrderEvent.CANCEL_REQUEST)

        # 取消 FILL 超时，注册 CANCEL 超时
        self._timeout_mgr.cancel_timeout(local_id, TimeoutType.FILL)
        self._timeout_mgr.register_cancel_timeout(local_id)

        # 实际撤单（如果有 broker）
        if self._broker:
            ctx = self._registry.get_by_local_id(local_id)
            if ctx and ctx.order_sys_id:
                self._broker.cancel_order(ctx.order_sys_id)
            elif ctx and ctx.order_ref:
                self._broker.cancel_order_by_ref(ctx.order_ref)

        return True

    def on_rtn_order(
        self,
        local_id: str,
        order_sys_id: str | None = None,
        status: str = "",
        filled_qty: int = 0,
    ) -> None:
        """处理订单回报.

        Args:
            local_id: 本地订单 ID
            order_sys_id: 交易所系统号
            status: CTP 订单状态
            filled_qty: 成交数量
        """
        fsm = self._fsm_map.get(local_id)
        if fsm is None:
            return

        # 更新 order_sys_id
        if order_sys_id:
            self._registry.update_order_sys_id(local_id, order_sys_id)

        # 根据 CTP 状态确定事件
        event = self._map_ctp_status_to_event(status, filled_qty, fsm.filled_qty)
        if event is None:
            return

        # 执行转移
        fsm.transition(event, filled_qty)
        self._emit_event(local_id, fsm.state, event)

        # 更新超时
        self._update_timeout_on_event(local_id, event, fsm.state)

        # 终态处理
        if fsm.is_terminal():
            self._finalize_order(local_id, fsm)

    def on_rtn_trade(
        self,
        local_id: str,
        trade_id: str,
        volume: int,
        price: float,
    ) -> None:
        """处理成交回报.

        Args:
            local_id: 本地订单 ID
            trade_id: 成交 ID
            volume: 成交量
            price: 成交价
        """
        fsm = self._fsm_map.get(local_id)
        if fsm is None:
            return

        ctx = self._registry.get_by_local_id(local_id)
        if ctx is None:
            return

        # 更新成交
        total_filled = fsm.filled_qty + volume

        if total_filled >= ctx.qty:
            event = OrderEvent.FILL
        else:
            event = OrderEvent.PARTIAL_FILL

        fsm.transition(event, volume)
        self._emit_event(local_id, fsm.state, event)

        # 部分成交追价
        if event == OrderEvent.PARTIAL_FILL and self._config.enable_reprice:
            self._handle_partial_fill(local_id, fsm, ctx)

        # 终态处理
        if fsm.is_terminal():
            self._finalize_order(local_id, fsm)

    def check_timeouts(self, now: float | None = None) -> list[str]:
        """检查超时.

        Args:
            now: 当前时间戳

        Returns:
            超时的订单 ID 列表
        """
        expired = self._timeout_mgr.check_expired(now)
        return [e.local_id for e in expired]

    def get_state(self, local_id: str) -> OrderState | None:
        """获取订单状态.

        Args:
            local_id: 本地订单 ID

        Returns:
            订单状态或 None
        """
        fsm = self._fsm_map.get(local_id)
        return fsm.state if fsm else None

    def get_result(self, local_id: str) -> OrderResult | None:
        """获取订单结果.

        Args:
            local_id: 本地订单 ID

        Returns:
            订单结果或 None
        """
        return self._results.get(local_id)

    def get_active_orders(self) -> list[str]:
        """获取活动订单.

        Returns:
            活动订单 ID 列表
        """
        return [
            local_id
            for local_id, fsm in self._fsm_map.items()
            if not fsm.is_terminal()
        ]

    def _on_timeout(self, local_id: str, timeout_type: TimeoutType) -> None:
        """超时回调.

        Args:
            local_id: 本地订单 ID
            timeout_type: 超时类型
        """
        fsm = self._fsm_map.get(local_id)
        if fsm is None:
            return

        if timeout_type == TimeoutType.ACK:
            fsm.transition(OrderEvent.ACK_TIMEOUT)
            self._emit_event(local_id, fsm.state, OrderEvent.ACK_TIMEOUT)
        elif timeout_type == TimeoutType.FILL:
            # V2 Scenario: EXEC.CANCEL_REPRICE.TIMEOUT
            fsm.transition(OrderEvent.FILL_TIMEOUT)
            self._emit_event(local_id, fsm.state, OrderEvent.FILL_TIMEOUT)
            # 触发撤单
            self.cancel(local_id)
        elif timeout_type == TimeoutType.CANCEL:
            fsm.transition(OrderEvent.CANCEL_TIMEOUT)
            self._emit_event(local_id, fsm.state, OrderEvent.CANCEL_TIMEOUT)

    def _on_invalid_transition(
        self, state: OrderState, event: OrderEvent, reason: str
    ) -> None:
        """非法转移回调.

        Args:
            state: 当前状态
            event: 事件
            reason: 原因
        """
        # 可以记录日志或触发告警

    def _emit_event(self, local_id: str, state: OrderState, event: OrderEvent) -> None:
        """触发事件回调.

        Args:
            local_id: 本地订单 ID
            state: 状态
            event: 事件
        """
        if self._on_order_event:
            self._on_order_event(local_id, state, event)

    def _update_timeout_on_event(
        self, local_id: str, event: OrderEvent, state: OrderState
    ) -> None:
        """根据事件更新超时.

        Args:
            local_id: 本地订单 ID
            event: 事件
            state: 状态
        """
        if event == OrderEvent.ACK:
            # ACK 收到，取消 ACK 超时，注册 FILL 超时
            self._timeout_mgr.cancel_timeout(local_id, TimeoutType.ACK)
            self._timeout_mgr.register_fill_timeout(local_id)
        elif event in (OrderEvent.FILL, OrderEvent.CANCEL_ACK):
            # 终态，取消所有超时
            self._timeout_mgr.cancel_all_for_order(local_id)

    def _handle_submit_error(self, local_id: str, error: str) -> None:
        """处理提交错误.

        Args:
            local_id: 本地订单 ID
            error: 错误信息
        """
        fsm = self._fsm_map.get(local_id)
        if fsm:
            fsm.transition(OrderEvent.REJECT)
            self._emit_event(local_id, fsm.state, OrderEvent.REJECT)
            self._finalize_order(local_id, fsm, error=error)

    def _handle_partial_fill(
        self, local_id: str, fsm: OrderFSM, ctx: OrderContext
    ) -> None:
        """处理部分成交（追价）.

        V2 Scenario: EXEC.PARTIAL.REPRICE

        Args:
            local_id: 本地订单 ID
            fsm: 状态机
            ctx: 订单上下文
        """
        # 检查是否应该重试追价
        if not self._retry_policy.should_retry(local_id, RetryReason.FILL_TIMEOUT):
            return

        # 追价逻辑由外部处理或在这里实现
        fsm.transition(OrderEvent.CHASE)
        self._emit_event(local_id, fsm.state, OrderEvent.CHASE)

    def _finalize_order(
        self, local_id: str, fsm: OrderFSM, error: str | None = None
    ) -> None:
        """完成订单.

        Args:
            local_id: 本地订单 ID
            fsm: 状态机
            error: 错误信息
        """
        self._timeout_mgr.cancel_all_for_order(local_id)

        result = OrderResult(
            local_id=local_id,
            state=fsm.state,
            filled_qty=fsm.filled_qty,
            error=error,
        )
        self._results[local_id] = result

    def _map_ctp_status_to_event(
        self, status: str, filled_qty: int, prev_filled: int
    ) -> OrderEvent | None:
        """映射 CTP 状态到事件.

        Args:
            status: CTP 订单状态
            filled_qty: 成交数量
            prev_filled: 之前成交数量

        Returns:
            订单事件或 None
        """
        # CTP 订单状态:
        # '0': 全部成交
        # '1': 部分成交还在队列中
        # '2': 部分成交不在队列中
        # '3': 未成交还在队列中 (已接受)
        # '4': 未成交不在队列中 (已撤销/错误)
        # '5': 撤单中
        # 'a': 未触发
        # 'b': 已触发

        if status == "0":
            return OrderEvent.FILL
        if status == "1":
            if filled_qty > prev_filled:
                return OrderEvent.PARTIAL_FILL
            return OrderEvent.ACK
        if status == "2":
            return OrderEvent.PARTIAL_FILL
        if status == "3":
            return OrderEvent.ACK
        if status == "4":
            return OrderEvent.STATUS_4
        if status == "5":
            return None  # 撤单中，等待确认

        return None

    def __len__(self) -> int:
        """返回活动订单数量."""
        return len(self.get_active_orders())
