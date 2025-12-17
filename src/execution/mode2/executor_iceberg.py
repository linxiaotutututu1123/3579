"""
冰山单执行器 (Iceberg Executor).

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.EXECUTOR.ICEBERG: 冰山单执行
- MODE2.EXECUTOR.ICEBERG.DISPLAY: 显示量控制
- MODE2.EXECUTOR.ICEBERG.REFRESH: 自动补单

执行策略:
    隐藏真实订单规模，只显示部分数量:
    - 显示量 (display_qty): 市场可见的挂单数量
    - 总量 (total_qty): 实际需要成交的总数量
    - 每次显示量成交后自动补单
    - 适用于大额订单（防止暴露交易意图）

军规级要求:
- 显示量在计划创建时确定 (M7)
- 每次补单必须记录审计日志 (M3)
- 补单逻辑必须确定性 (M7)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from src.execution.mode2.executor_base import (
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
    TERMINAL_STATUSES,
)
from src.execution.mode2.intent import IntentIdGenerator, OrderIntent


@dataclass
class IcebergConfig(ExecutorConfig):
    """冰山单执行器配置.

    Attributes:
        max_slice_qty: 单个分片最大数量（作为显示量上限）
        min_slice_qty: 单个分片最小数量（作为显示量下限）
        price_tolerance: 价格容忍度（滑点）
        timeout_seconds: 单个订单超时时间（秒）
        retry_count: 重试次数
        audit_enabled: 是否启用审计
        display_qty: 显示量（0 表示使用 max_slice_qty）
        display_qty_ratio: 显示量占总量比例（当 display_qty=0 时使用）
        refresh_on_partial: 部分成交时是否补单
        min_refresh_qty: 最小补单数量
        price_improvement: 是否启用价格改善（追单）
    """

    display_qty: int = 0  # 0 表示自动计算
    display_qty_ratio: float = 0.1  # 默认显示 10%
    refresh_on_partial: bool = True  # 部分成交时补单
    min_refresh_qty: int = 1  # 最小补单数量
    price_improvement: bool = False  # 暂不支持追单


class IcebergExecutor(ExecutorBase):
    """冰山单执行器.

    V4PRO Scenarios:
    - MODE2.EXECUTOR.ICEBERG: 冰山单执行
    - MODE2.EXECUTOR.ICEBERG.DISPLAY: 显示量控制
    - MODE2.EXECUTOR.ICEBERG.REFRESH: 自动补单

    执行逻辑:
    1. make_plan: 计算显示量和分片
    2. next_action: 返回显示量大小的 PLACE_ORDER
    3. on_event: 成交后自动补单
    4. 重复直到总量完成

    军规级要求:
    - 显示量在计划创建时确定 (M7)
    - 使用 client_order_id 确保幂等 (M2)
    - 记录完整执行过程 (M3)
    """

    def __init__(self, config: IcebergConfig | None = None) -> None:
        """初始化冰山单执行器.

        Args:
            config: 执行器配置
        """
        super().__init__(config or IcebergConfig())
        self._iceberg_config: IcebergConfig = self._config  # type: ignore

    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: MODE2.EXECUTOR.ICEBERG

        计算显示量并创建分片列表。

        Args:
            intent: 交易意图

        Returns:
            计划ID (等于 intent_id)
        """
        plan_id = intent.intent_id

        # 幂等检查
        if plan_id in self._plans:
            return plan_id

        # 计算显示量
        display_qty = self._calculate_display_qty(intent.target_qty)

        # 计算分片数量
        slice_count = (intent.target_qty + display_qty - 1) // display_qty

        # 生成分片列表
        slices = self._generate_slices(intent, display_qty, slice_count)

        # 创建计划上下文
        ctx = ExecutionPlanContext(
            plan_id=plan_id,
            intent=intent,
            status=ExecutorStatus.PENDING,
            slices=slices,
            current_slice_index=0,
        )
        ctx.progress.total_qty = intent.target_qty
        ctx.progress.slice_count = len(slices)
        ctx.start_time = time.time()
        ctx.progress.start_time = ctx.start_time

        # 保存冰山单特定元数据
        ctx.metadata["algo"] = "ICEBERG"
        ctx.metadata["display_qty"] = display_qty
        ctx.metadata["slice_count"] = len(slices)

        self._plans[plan_id] = ctx

        return plan_id

    def _calculate_display_qty(self, total_qty: int) -> int:
        """计算显示量.

        V4PRO Scenario: MODE2.EXECUTOR.ICEBERG.DISPLAY

        Args:
            total_qty: 总数量

        Returns:
            显示量
        """
        config = self._iceberg_config

        if config.display_qty > 0:
            # 使用配置的固定显示量
            display_qty = config.display_qty
        else:
            # 按比例计算
            display_qty = max(1, int(total_qty * config.display_qty_ratio))

        # 确保在合理范围内
        display_qty = max(config.min_slice_qty, min(display_qty, config.max_slice_qty))

        # 确保不超过总量
        display_qty = min(display_qty, total_qty)

        return display_qty

    def _generate_slices(
        self, intent: OrderIntent, display_qty: int, slice_count: int
    ) -> list[SliceInfo]:
        """生成分片列表.

        V4PRO Scenario: MODE2.EXECUTOR.ICEBERG

        Args:
            intent: 交易意图
            display_qty: 显示量
            slice_count: 分片数量

        Returns:
            分片列表
        """
        total_qty = intent.target_qty
        slices: list[SliceInfo] = []
        remaining = total_qty

        for i in range(slice_count):
            qty = min(display_qty, remaining)
            if qty > 0:
                slices.append(
                    SliceInfo(
                        index=i,
                        qty=qty,
                        target_price=intent.limit_price,
                        scheduled_time=None,  # 冰山单不预设时间
                        executed=False,
                    )
                )
                remaining -= qty

        return slices

    def next_action(
        self, plan_id: str, current_time: float | None = None
    ) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: MODE2.EXECUTOR.ICEBERG

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳

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
                    reason="冰山单执行完成",
                )
            elif ctx.status == ExecutorStatus.CANCELLED:
                return ExecutorAction(
                    action_type=ExecutorActionType.ABORT,
                    reason="计划已取消",
                )
            else:
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

        # 检查挂单超时
        for order_id, pending in list(ctx.pending_orders.items()):
            elapsed = now - pending.submit_time
            if elapsed > self._config.timeout_seconds:
                return ExecutorAction(
                    action_type=ExecutorActionType.CANCEL_ORDER,
                    client_order_id=order_id,
                    reason=f"订单超时 ({elapsed:.1f}s)",
                )

        # 冰山单关键逻辑: 同一时间只有一个显示量在市场上
        if ctx.pending_orders:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                reason="等待当前显示量成交",
            )

        # 检查是否已完成目标
        if ctx.progress.filled_qty >= ctx.intent.target_qty:
            ctx.status = ExecutorStatus.COMPLETED
            ctx.end_time = now
            return ExecutorAction(
                action_type=ExecutorActionType.COMPLETE,
                reason="冰山单执行完成",
            )

        # 查找下一个待执行的分片
        next_slice = self._find_next_slice(ctx)
        if next_slice is None:
            # 所有预定分片已执行，检查是否需要额外补单
            remaining = ctx.intent.target_qty - ctx.progress.filled_qty
            if remaining > 0:
                # 创建补单分片
                new_slice = SliceInfo(
                    index=len(ctx.slices),
                    qty=min(remaining, ctx.metadata.get("display_qty", remaining)),
                    target_price=ctx.intent.limit_price,
                    scheduled_time=None,
                    executed=False,
                )
                ctx.slices.append(new_slice)
                next_slice = new_slice
            else:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = now
                return ExecutorAction(
                    action_type=ExecutorActionType.COMPLETE,
                    reason="冰山单执行完成",
                )

        # 计算重试次数
        slice_cancelled_count = sum(
            1 for oid in ctx.cancelled_orders
            if self._get_slice_index_from_order_id(oid) == next_slice.index
        )
        if slice_cancelled_count >= self._config.retry_count:
            next_slice.executed = True
            ctx.current_slice_index = next_slice.index + 1
            return self.next_action(plan_id, now)

        # 生成 client_order_id
        client_order_id = IntentIdGenerator.generate_client_order_id(
            intent_id=ctx.intent.intent_id,
            slice_index=next_slice.index,
            retry_count=slice_cancelled_count,
        )

        # 计算下单数量
        remaining_qty = ctx.intent.target_qty - ctx.progress.filled_qty
        order_qty = min(next_slice.qty, remaining_qty)

        if order_qty <= 0:
            next_slice.executed = True
            ctx.current_slice_index = next_slice.index + 1
            return self.next_action(plan_id, now)

        # 更新状态
        if ctx.status == ExecutorStatus.PENDING:
            ctx.status = ExecutorStatus.RUNNING

        # 记录挂单
        ctx.pending_orders[client_order_id] = PendingOrder(
            client_order_id=client_order_id,
            qty=order_qty,
            price=next_slice.target_price or 0.0,
            submit_time=now,
            retry_count=slice_cancelled_count,
        )

        # 标记分片已执行
        next_slice.executed = True
        ctx.current_slice_index = next_slice.index + 1

        # 返回下单动作
        return ExecutorAction(
            action_type=ExecutorActionType.PLACE_ORDER,
            client_order_id=client_order_id,
            instrument=ctx.intent.instrument,
            side=ctx.intent.side,
            offset=ctx.intent.offset,
            price=next_slice.target_price,
            qty=order_qty,
            reason=f"冰山单显示量 #{next_slice.index} (显示{order_qty}/总{ctx.intent.target_qty})",
            metadata={
                "intent_id": ctx.intent.intent_id,
                "slice_index": next_slice.index,
                "retry_count": slice_cancelled_count,
                "display_qty": ctx.metadata.get("display_qty"),
                "hidden_qty": ctx.intent.target_qty - ctx.progress.filled_qty - order_qty,
            },
        )

    def _find_next_slice(self, ctx: ExecutionPlanContext) -> SliceInfo | None:
        """查找下一个待执行的分片.

        Args:
            ctx: 计划上下文

        Returns:
            下一个待执行的分片，None 表示无
        """
        for slice_info in ctx.slices:
            if not slice_info.executed:
                return slice_info
        return None

    def _get_slice_index_from_order_id(self, client_order_id: str) -> int:
        """从 client_order_id 解析分片索引.

        Args:
            client_order_id: 客户订单ID

        Returns:
            分片索引，解析失败返回 -1
        """
        try:
            _, slice_index, _ = IntentIdGenerator.parse_client_order_id(client_order_id)
            return slice_index
        except ValueError:
            return -1

    def on_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

        V4PRO Scenario: MODE2.EXECUTOR.ICEBERG.REFRESH

        关键: 成交后自动触发补单逻辑。

        Args:
            plan_id: 计划ID
            event: 订单事件
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return

        client_order_id = event.client_order_id

        if event.event_type == "ACK":
            pass

        elif event.event_type in ("PARTIAL_FILL", "FILL"):
            pending = ctx.pending_orders.get(client_order_id)
            if pending:
                filled_order = FilledOrder(
                    client_order_id=client_order_id,
                    filled_qty=event.filled_qty,
                    avg_price=event.filled_price,
                    fill_time=event.ts,
                )
                ctx.filled_orders.append(filled_order)

                # 完全成交时移除挂单（触发补单）
                if event.event_type == "FILL":
                    del ctx.pending_orders[client_order_id]
                elif event.event_type == "PARTIAL_FILL":
                    # 部分成交时根据配置决定是否补单
                    if self._iceberg_config.refresh_on_partial:
                        # 更新挂单数量
                        pending.qty = event.remaining_qty

            ctx.update_progress()

            # 检查是否完成
            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = time.time()

        elif event.event_type == "REJECT":
            if client_order_id in ctx.pending_orders:
                del ctx.pending_orders[client_order_id]
                ctx.cancelled_orders.append(client_order_id)

                slice_index = self._get_slice_index_from_order_id(client_order_id)
                if 0 <= slice_index < len(ctx.slices):
                    ctx.slices[slice_index].executed = False
                    ctx.current_slice_index = min(ctx.current_slice_index, slice_index)

        elif event.event_type == "CANCEL_ACK":
            if client_order_id in ctx.pending_orders:
                del ctx.pending_orders[client_order_id]
                ctx.cancelled_orders.append(client_order_id)

                slice_index = self._get_slice_index_from_order_id(client_order_id)
                if 0 <= slice_index < len(ctx.slices):
                    ctx.slices[slice_index].executed = False
                    ctx.current_slice_index = min(ctx.current_slice_index, slice_index)

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

        Args:
            plan_id: 计划ID

        Returns:
            需要撤销的 client_order_id 列表
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return []
        return list(ctx.pending_orders.keys())

    def get_iceberg_status(self, plan_id: str) -> dict | None:
        """获取冰山单状态.

        Args:
            plan_id: 计划ID

        Returns:
            冰山单状态字典
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return None

        ctx.update_progress()
        display_qty = ctx.metadata.get("display_qty", 0)
        visible_qty = sum(p.qty for p in ctx.pending_orders.values())

        return {
            "total_qty": ctx.intent.target_qty,
            "filled_qty": ctx.progress.filled_qty,
            "remaining_qty": ctx.intent.target_qty - ctx.progress.filled_qty,
            "display_qty": display_qty,
            "visible_qty": visible_qty,
            "hidden_qty": ctx.intent.target_qty - ctx.progress.filled_qty - visible_qty,
            "slice_count": len(ctx.slices),
            "completed_slices": sum(1 for s in ctx.slices if s.executed),
        }
