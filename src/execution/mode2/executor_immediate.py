"""
立即执行器 (ImmediateExecutor).

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.EXECUTOR.IMMEDIATE: 立即全量执行
- MODE2.EXECUTOR.IMMEDIATE.RETRY: 立即执行重试机制

执行策略:
    一次性下单全部数量，适用于:
    - 小额订单（市场冲击可忽略）
    - 高紧急度订单（CRITICAL urgency）
    - 流动性充足的合约

军规级要求:
- 订单必须使用 client_order_id 幂等键 (M2)
- 所有动作必须记录审计日志 (M3)
- 下单前必须通过成本检查 (M5)
- 相同输入必须产生相同执行计划 (M7)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

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
from src.execution.mode2.intent import IntentIdGenerator, OrderIntent


@dataclass
class ImmediateConfig(ExecutorConfig):
    """立即执行器配置.

    继承 ExecutorConfig 的所有配置项。

    Attributes:
        max_slice_qty: 单个分片最大数量（立即执行时为全量）
        min_slice_qty: 单个分片最小数量
        price_tolerance: 价格容忍度（滑点）
        timeout_seconds: 单个订单超时时间（秒）
        retry_count: 重试次数
        audit_enabled: 是否启用审计
    """

    # 使用基类默认配置


class ImmediateExecutor(ExecutorBase):
    """立即执行器.

    V4PRO Scenarios:
    - MODE2.EXECUTOR.IMMEDIATE: 立即全量执行
    - MODE2.EXECUTOR.IMMEDIATE.RETRY: 立即执行重试机制

    执行逻辑:
    1. make_plan: 创建单分片计划（全量）
    2. next_action: 返回 PLACE_ORDER 动作
    3. on_event: 处理成交/拒绝事件
    4. 支持超时重试机制

    军规级要求:
    - 使用 intent_id 作为 plan_id (M2)
    - 使用 client_order_id 确保幂等 (M2)
    - 记录完整执行过程 (M3)
    """

    def __init__(self, config: ImmediateConfig | None = None) -> None:
        """初始化立即执行器.

        Args:
            config: 执行器配置
        """
        super().__init__(config or ImmediateConfig())

    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: MODE2.EXECUTOR.IMMEDIATE

        创建单分片计划，一次性下单全部数量。

        Args:
            intent: 交易意图

        Returns:
            计划ID (等于 intent_id)

        Raises:
            ValueError: 意图参数无效
        """
        plan_id = intent.intent_id

        # 幂等检查：如果计划已存在，直接返回
        if plan_id in self._plans:
            return plan_id

        # 创建单分片
        slices = [
            SliceInfo(
                index=0,
                qty=intent.target_qty,
                target_price=intent.limit_price,
                scheduled_time=time.time(),
                executed=False,
            )
        ]

        # 创建计划上下文
        ctx = ExecutionPlanContext(
            plan_id=plan_id,
            intent=intent,
            status=ExecutorStatus.PENDING,
            slices=slices,
            current_slice_index=0,
        )
        ctx.progress.total_qty = intent.target_qty
        ctx.progress.slice_count = 1
        ctx.start_time = time.time()
        ctx.progress.start_time = ctx.start_time

        self._plans[plan_id] = ctx

        return plan_id

    def next_action(self, plan_id: str, current_time: float | None = None) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: MODE2.EXECUTOR.IMMEDIATE

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳（用于超时检查）

        Returns:
            下一个动作，None 表示当前无动作
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return None

        now = current_time or time.time()

        # 终态检查
        if ctx.status in TERMINAL_STATUSES:
            if ctx.status == ExecutorStatus.COMPLETED:
                return ExecutorAction(
                    action_type=ExecutorActionType.COMPLETE,
                    reason="执行完成",
                )
            if ctx.status == ExecutorStatus.CANCELLED:
                return ExecutorAction(
                    action_type=ExecutorActionType.ABORT,
                    reason="计划已取消",
                )
            return ExecutorAction(
                action_type=ExecutorActionType.ABORT,
                reason=ctx.error or "执行失败",
            )

        # 暂停状态
        if ctx.status == ExecutorStatus.PAUSED:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                reason="计划已暂停",
            )

        # 检查是否有挂单中的订单
        if ctx.pending_orders:
            # 检查超时
            for order_id, pending in list(ctx.pending_orders.items()):
                elapsed = now - pending.submit_time
                if elapsed > self._config.timeout_seconds:
                    # 超时，需要撤单
                    return ExecutorAction(
                        action_type=ExecutorActionType.CANCEL_ORDER,
                        client_order_id=order_id,
                        reason=f"订单超时 ({elapsed:.1f}s > {self._config.timeout_seconds}s)",
                    )

            # 等待挂单响应
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                reason="等待订单响应",
            )

        # 检查是否已完成
        if ctx.progress.filled_qty >= ctx.intent.target_qty:
            ctx.status = ExecutorStatus.COMPLETED
            ctx.end_time = now
            return ExecutorAction(
                action_type=ExecutorActionType.COMPLETE,
                reason="执行完成",
            )

        # 获取当前分片
        if ctx.current_slice_index >= len(ctx.slices):
            # 所有分片已处理但未完成目标
            if ctx.progress.filled_qty < ctx.intent.target_qty:
                ctx.status = ExecutorStatus.FAILED
                ctx.error = "所有分片已处理但未达成目标"
            return ExecutorAction(
                action_type=ExecutorActionType.ABORT,
                reason=ctx.error or "执行中止",
            )

        current_slice = ctx.slices[ctx.current_slice_index]

        # 检查分片是否已执行
        if current_slice.executed:
            ctx.current_slice_index += 1
            return self.next_action(plan_id, now)

        # 计算重试次数
        retry_count = len(ctx.cancelled_orders)
        if retry_count >= self._config.retry_count:
            ctx.status = ExecutorStatus.FAILED
            ctx.error = f"重试次数超限 ({retry_count} >= {self._config.retry_count})"
            return ExecutorAction(
                action_type=ExecutorActionType.ABORT,
                reason=ctx.error,
            )

        # 生成 client_order_id
        client_order_id = IntentIdGenerator.generate_client_order_id(
            intent_id=ctx.intent.intent_id,
            slice_index=current_slice.index,
            retry_count=retry_count,
        )

        # 计算实际下单数量（减去已成交数量）
        remaining_qty = ctx.intent.target_qty - ctx.progress.filled_qty
        order_qty = min(current_slice.qty, remaining_qty)

        if order_qty <= 0:
            ctx.status = ExecutorStatus.COMPLETED
            ctx.end_time = now
            return ExecutorAction(
                action_type=ExecutorActionType.COMPLETE,
                reason="执行完成（无剩余数量）",
            )

        # 更新状态
        if ctx.status == ExecutorStatus.PENDING:
            ctx.status = ExecutorStatus.RUNNING

        # 记录挂单
        ctx.pending_orders[client_order_id] = PendingOrder(
            client_order_id=client_order_id,
            qty=order_qty,
            price=current_slice.target_price or 0.0,
            submit_time=now,
            retry_count=retry_count,
        )

        # 标记分片已执行
        current_slice.executed = True

        # 返回下单动作
        return ExecutorAction(
            action_type=ExecutorActionType.PLACE_ORDER,
            client_order_id=client_order_id,
            instrument=ctx.intent.instrument,
            side=ctx.intent.side,
            offset=ctx.intent.offset,
            price=current_slice.target_price,
            qty=order_qty,
            reason=f"立即执行: 分片#{current_slice.index}, 重试#{retry_count}",
            metadata={
                "intent_id": ctx.intent.intent_id,
                "slice_index": current_slice.index,
                "retry_count": retry_count,
            },
        )

    def on_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

        V4PRO Scenario: MODE2.EXECUTOR.IMMEDIATE

        Args:
            plan_id: 计划ID
            event: 订单事件
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return

        client_order_id = event.client_order_id

        # 处理不同事件类型
        if event.event_type == "ACK":
            # 订单确认，无需特殊处理
            pass

        elif event.event_type in ("PARTIAL_FILL", "FILL"):
            # 成交事件
            pending = ctx.pending_orders.get(client_order_id)
            if pending:
                # 记录成交
                filled_order = FilledOrder(
                    client_order_id=client_order_id,
                    filled_qty=event.filled_qty,
                    avg_price=event.filled_price,
                    fill_time=event.ts,
                )
                ctx.filled_orders.append(filled_order)

                # 完全成交时移除挂单
                if event.event_type == "FILL":
                    del ctx.pending_orders[client_order_id]

            # 更新进度
            ctx.update_progress()

            # 检查是否完成
            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = time.time()

        elif event.event_type == "REJECT":
            # 订单被拒绝
            if client_order_id in ctx.pending_orders:
                del ctx.pending_orders[client_order_id]
                ctx.cancelled_orders.append(client_order_id)

                # 重置分片状态以便重试
                if ctx.current_slice_index < len(ctx.slices):
                    ctx.slices[ctx.current_slice_index].executed = False

        elif event.event_type == "CANCEL_ACK":
            # 撤单确认
            if client_order_id in ctx.pending_orders:
                del ctx.pending_orders[client_order_id]
                ctx.cancelled_orders.append(client_order_id)

                # 重置分片状态以便重试
                if ctx.current_slice_index < len(ctx.slices):
                    ctx.slices[ctx.current_slice_index].executed = False

        elif event.event_type == "CANCEL_REJECT":
            # 撤单被拒绝（可能订单已成交）
            pass

    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消计划.

        V4PRO Scenario: MODE2.EXECUTOR.CANCEL

        Args:
            plan_id: 计划ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return False

        if ctx.status in TERMINAL_STATUSES:
            return False

        ctx.status = ExecutorStatus.CANCELLED
        ctx.error = reason or "用户取消"
        ctx.end_time = time.time()

        return True

    def get_status(self, plan_id: str) -> ExecutorStatus | None:
        """获取计划状态.

        Args:
            plan_id: 计划ID

        Returns:
            状态或 None
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return None
        return ctx.status

    def get_progress(self, plan_id: str) -> ExecutionProgress | None:
        """获取执行进度.

        Args:
            plan_id: 计划ID

        Returns:
            进度或 None
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return None

        ctx.update_progress()
        return ctx.progress

    def get_pending_cancel_orders(self, plan_id: str) -> list[str]:
        """获取需要撤销的挂单列表.

        用于计划取消时撤销所有挂单。

        Args:
            plan_id: 计划ID

        Returns:
            需要撤销的 client_order_id 列表
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return []
        return list(ctx.pending_orders.keys())
