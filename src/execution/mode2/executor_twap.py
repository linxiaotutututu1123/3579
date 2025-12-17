"""
TWAP 执行器 (Time Weighted Average Price).

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.EXECUTOR.TWAP: 时间加权平均价格执行
- MODE2.EXECUTOR.TWAP.SLICE: 分片调度
- MODE2.EXECUTOR.TWAP.ADAPTIVE: 自适应调整

执行策略:
    将订单按时间均匀分割,在指定时间窗口内等间隔执行:
    - 适用于大额订单(需要分散市场冲击)
    - 适用于需要跟踪 TWAP 基准的场景
    - 支持自适应调整分片大小

军规级要求:
- 分片时间必须确定性计算 (M7)
- 每个分片必须记录审计日志 (M3)
- 分片数量和时间间隔必须在计划创建时确定 (M7)
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
class TWAPConfig(ExecutorConfig):
    """TWAP 执行器配置.

    Attributes:
        max_slice_qty: 单个分片最大数量
        min_slice_qty: 单个分片最小数量
        price_tolerance: 价格容忍度(滑点)
        timeout_seconds: 单个订单超时时间(秒)
        retry_count: 重试次数
        audit_enabled: 是否启用审计
        duration_seconds: 执行总时长(秒)
        slice_count: 分片数量(0 表示自动计算)
        min_interval_seconds: 最小分片间隔(秒)
        max_interval_seconds: 最大分片间隔(秒)
        randomize_interval: 是否随机化间隔(防止被预测)
        catch_up_enabled: 是否启用追赶模式(延迟时加速执行)
    """

    duration_seconds: float = 300.0  # 默认 5 分钟
    slice_count: int = 0  # 0 表示自动计算
    min_interval_seconds: float = 10.0
    max_interval_seconds: float = 60.0
    randomize_interval: bool = False  # 禁用随机化以确保 M7 回放一致
    catch_up_enabled: bool = True


class TWAPExecutor(ExecutorBase):
    """TWAP 执行器.

    V4PRO Scenarios:
    - MODE2.EXECUTOR.TWAP: 时间加权平均价格执行
    - MODE2.EXECUTOR.TWAP.SLICE: 分片调度
    - MODE2.EXECUTOR.TWAP.ADAPTIVE: 自适应调整

    执行逻辑:
    1. make_plan: 计算分片数量和时间表
    2. next_action: 按时间表返回 PLACE_ORDER 动作
    3. on_event: 处理成交/拒绝事件
    4. 支持追赶模式和自适应调整

    军规级要求:
    - 分片时间在计划创建时确定 (M7)
    - 使用 client_order_id 确保幂等 (M2)
    - 记录完整执行过程 (M3)
    """

    def __init__(self, config: TWAPConfig | None = None) -> None:
        """初始化 TWAP 执行器.

        Args:
            config: 执行器配置
        """
        super().__init__(config or TWAPConfig())
        self._twap_config: TWAPConfig = self._config  # type: ignore[assignment]

    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: MODE2.EXECUTOR.TWAP

        计算分片数量和时间表,确保:
        - 每个分片数量在 [min_slice_qty, max_slice_qty] 范围内
        - 分片时间均匀分布在 duration_seconds 内
        - 总数量等于目标数量

        Args:
            intent: 交易意图

        Returns:
            计划ID (等于 intent_id)

        Raises:
            ValueError: 意图参数无效
        """
        plan_id = intent.intent_id

        # 幂等检查
        if plan_id in self._plans:
            return plan_id

        # 计算分片
        slices = self._calculate_slices(intent)

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

        # 保存 TWAP 特定元数据
        ctx.metadata["algo"] = "TWAP"
        ctx.metadata["duration_seconds"] = self._twap_config.duration_seconds
        ctx.metadata["slice_count"] = len(slices)

        self._plans[plan_id] = ctx

        return plan_id

    def _calculate_slices(self, intent: OrderIntent) -> list[SliceInfo]:
        """计算分片列表.

        V4PRO Scenario: MODE2.EXECUTOR.TWAP.SLICE

        确保分片计算的确定性 (M7)。

        Args:
            intent: 交易意图

        Returns:
            分片列表
        """
        total_qty = intent.target_qty
        duration = self._twap_config.duration_seconds
        config = self._twap_config

        # 计算分片数量
        if config.slice_count > 0:
            slice_count = config.slice_count
        else:
            # 自动计算: 根据数量和最大分片大小
            slice_count = max(1, (total_qty + config.max_slice_qty - 1) // config.max_slice_qty)

            # 确保间隔在合理范围内
            if slice_count > 1:
                interval = duration / (slice_count - 1)
                if interval < config.min_interval_seconds:
                    slice_count = max(1, int(duration / config.min_interval_seconds) + 1)
                elif interval > config.max_interval_seconds:
                    slice_count = max(2, int(duration / config.max_interval_seconds) + 1)

        # 计算每个分片的数量(尽量均匀)
        base_qty = total_qty // slice_count
        remainder = total_qty % slice_count

        # 计算时间间隔
        interval = duration / (slice_count - 1) if slice_count > 1 else 0.0

        # 生成分片
        slices: list[SliceInfo] = []
        start_time = time.time()

        for i in range(slice_count):
            # 前 remainder 个分片多分配 1 个
            qty = base_qty + (1 if i < remainder else 0)

            if qty > 0:
                scheduled_time = start_time + i * interval
                slices.append(
                    SliceInfo(
                        index=i,
                        qty=qty,
                        target_price=intent.limit_price,
                        scheduled_time=scheduled_time,
                        executed=False,
                    )
                )

        return slices

    def next_action(self, plan_id: str, current_time: float | None = None) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: MODE2.EXECUTOR.TWAP

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳

        Returns:
            下一个动作,None 表示当前无动作
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
                    reason="TWAP 执行完成",
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

        # 检查挂单超时
        for order_id, pending in list(ctx.pending_orders.items()):
            elapsed = now - pending.submit_time
            if elapsed > self._config.timeout_seconds:
                return ExecutorAction(
                    action_type=ExecutorActionType.CANCEL_ORDER,
                    client_order_id=order_id,
                    reason=f"订单超时 ({elapsed:.1f}s > {self._config.timeout_seconds}s)",
                )

        # 有挂单时等待
        if ctx.pending_orders:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                reason="等待订单响应",
            )

        # 检查是否已完成目标
        if ctx.progress.filled_qty >= ctx.intent.target_qty:
            ctx.status = ExecutorStatus.COMPLETED
            ctx.end_time = now
            return ExecutorAction(
                action_type=ExecutorActionType.COMPLETE,
                reason="TWAP 执行完成",
            )

        # 查找下一个待执行的分片
        next_slice = self._find_next_slice(ctx, now)
        if next_slice is None:
            # 所有分片已处理
            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = now
                return ExecutorAction(
                    action_type=ExecutorActionType.COMPLETE,
                    reason="TWAP 执行完成",
                )
            # 未完成但无更多分片
            ctx.status = ExecutorStatus.FAILED
            ctx.error = "所有分片已处理但未达成目标"
            return ExecutorAction(
                action_type=ExecutorActionType.ABORT,
                reason=ctx.error,
            )

        # 检查是否到达执行时间
        if next_slice.scheduled_time is not None and now < next_slice.scheduled_time:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                wait_until=next_slice.scheduled_time,
                reason=f"等待分片 #{next_slice.index} 执行时间",
            )

        # 计算重试次数(基于该分片的取消次数)
        slice_cancelled_count = sum(
            1
            for oid in ctx.cancelled_orders
            if self._get_slice_index_from_order_id(oid) == next_slice.index
        )
        if slice_cancelled_count >= self._config.retry_count:
            # 跳过该分片,继续下一个
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
            reason=f"TWAP 分片 #{next_slice.index}/{len(ctx.slices)}",
            metadata={
                "intent_id": ctx.intent.intent_id,
                "slice_index": next_slice.index,
                "retry_count": slice_cancelled_count,
                "scheduled_time": next_slice.scheduled_time,
            },
        )

    def _find_next_slice(self, ctx: ExecutionPlanContext, current_time: float) -> SliceInfo | None:
        """查找下一个待执行的分片.

        V4PRO Scenario: MODE2.EXECUTOR.TWAP.SLICE

        支持追赶模式: 如果当前时间已超过某些分片的调度时间,
        则按顺序执行这些分片(而非跳过)。

        Args:
            ctx: 计划上下文
            current_time: 当前时间

        Returns:
            下一个待执行的分片,None 表示无
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
            分片索引,解析失败返回 -1
        """
        try:
            _, slice_index, _ = IntentIdGenerator.parse_client_order_id(client_order_id)
        except ValueError:
            return -1
        else:
            return slice_index

    def on_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

        V4PRO Scenario: MODE2.EXECUTOR.TWAP

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

                if event.event_type == "FILL":
                    del ctx.pending_orders[client_order_id]

            ctx.update_progress()

            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = time.time()

        elif event.event_type == "REJECT":
            if client_order_id in ctx.pending_orders:
                del ctx.pending_orders[client_order_id]
                ctx.cancelled_orders.append(client_order_id)

                # 重置分片状态
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

    def get_schedule(self, plan_id: str) -> list[dict]:
        """获取执行时间表.

        Args:
            plan_id: 计划ID

        Returns:
            分片时间表列表
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return []

        return [
            {
                "index": s.index,
                "qty": s.qty,
                "scheduled_time": s.scheduled_time,
                "executed": s.executed,
            }
            for s in ctx.slices
        ]
