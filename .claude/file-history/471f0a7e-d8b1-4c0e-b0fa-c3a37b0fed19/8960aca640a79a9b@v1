"""
VWAP 执行器 (Volume Weighted Average Price).

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.EXECUTOR.VWAP: 成交量加权平均价格执行
- MODE2.EXECUTOR.VWAP.PROFILE: 成交量分布曲线
- MODE2.EXECUTOR.VWAP.ADAPTIVE: 自适应调整

执行策略:
    根据历史成交量分布曲线分配订单:
    - 高成交量时段分配更多数量
    - 低成交量时段分配更少数量
    - 适用于需要跟踪 VWAP 基准的场景

军规级要求:
- 成交量曲线必须在计划创建时确定 (M7)
- 每个分片必须记录审计日志 (M3)
- 分片分配必须确定性计算 (M7)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

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


# 中国期货市场默认成交量分布曲线（按 30 分钟时段）
# 基于中国期货市场实际交易特征:
# - 开盘 30 分钟成交活跃
# - 午盘相对平稳
# - 尾盘成交增加
DEFAULT_VOLUME_PROFILE = [
    0.15,  # 09:00-09:30 开盘活跃期
    0.10,  # 09:30-10:00
    0.08,  # 10:00-10:30 (含 10:15 休息)
    0.07,  # 10:30-11:00
    0.06,  # 11:00-11:30 午盘前
    0.06,  # 13:30-14:00 午盘开始
    0.08,  # 14:00-14:30
    0.10,  # 14:30-15:00 尾盘活跃
    0.15,  # 夜盘开盘 21:00-21:30
    0.08,  # 夜盘 21:30-22:00
    0.07,  # 夜盘后续
]


@dataclass
class VWAPConfig(ExecutorConfig):
    """VWAP 执行器配置.

    Attributes:
        max_slice_qty: 单个分片最大数量
        min_slice_qty: 单个分片最小数量
        price_tolerance: 价格容忍度（滑点）
        timeout_seconds: 单个订单超时时间（秒）
        retry_count: 重试次数
        audit_enabled: 是否启用审计
        duration_seconds: 执行总时长（秒）
        volume_profile: 成交量分布曲线（各时段占比列表）
        min_slice_qty_ratio: 最小分片占比（防止分片过小）
        participation_rate: 参与率上限（占市场成交量的比例）
    """

    duration_seconds: float = 300.0  # 默认 5 分钟
    volume_profile: list[float] = field(default_factory=lambda: DEFAULT_VOLUME_PROFILE.copy())
    min_slice_qty_ratio: float = 0.02  # 最小分片占总量 2%
    participation_rate: float = 0.10  # 最大参与率 10%


class VWAPExecutor(ExecutorBase):
    """VWAP 执行器.

    V4PRO Scenarios:
    - MODE2.EXECUTOR.VWAP: 成交量加权平均价格执行
    - MODE2.EXECUTOR.VWAP.PROFILE: 成交量分布曲线
    - MODE2.EXECUTOR.VWAP.ADAPTIVE: 自适应调整

    执行逻辑:
    1. make_plan: 根据成交量曲线计算分片
    2. next_action: 按时间表返回 PLACE_ORDER 动作
    3. on_event: 处理成交/拒绝事件

    军规级要求:
    - 成交量曲线在计划创建时确定 (M7)
    - 使用 client_order_id 确保幂等 (M2)
    - 记录完整执行过程 (M3)
    """

    def __init__(self, config: VWAPConfig | None = None) -> None:
        """初始化 VWAP 执行器.

        Args:
            config: 执行器配置
        """
        super().__init__(config or VWAPConfig())
        self._vwap_config: VWAPConfig = self._config  # type: ignore

    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: MODE2.EXECUTOR.VWAP

        根据成交量分布曲线分配订单数量。

        Args:
            intent: 交易意图

        Returns:
            计划ID (等于 intent_id)
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

        # 保存 VWAP 特定元数据
        ctx.metadata["algo"] = "VWAP"
        ctx.metadata["duration_seconds"] = self._vwap_config.duration_seconds
        ctx.metadata["slice_count"] = len(slices)
        ctx.metadata["volume_profile"] = self._vwap_config.volume_profile

        self._plans[plan_id] = ctx

        return plan_id

    def _calculate_slices(self, intent: OrderIntent) -> list[SliceInfo]:
        """计算分片列表.

        V4PRO Scenario: MODE2.EXECUTOR.VWAP.PROFILE

        根据成交量分布曲线分配订单数量，确保:
        - 高成交量时段分配更多
        - 每个分片数量在合理范围内
        - 总数量等于目标数量

        Args:
            intent: 交易意图

        Returns:
            分片列表
        """
        total_qty = intent.target_qty
        duration = self._vwap_config.duration_seconds
        profile = self._vwap_config.volume_profile
        config = self._vwap_config

        # 归一化成交量分布
        profile_sum = sum(profile)
        if profile_sum <= 0:
            # 如果分布无效，使用均匀分布
            normalized_profile = [1.0 / len(profile)] * len(profile)
        else:
            normalized_profile = [p / profile_sum for p in profile]

        # 计算分片数量（根据执行时长和分布时段数）
        slice_count = len(normalized_profile)
        interval = duration / slice_count if slice_count > 0 else duration

        # 计算每个分片的数量
        min_slice_qty = max(1, int(total_qty * config.min_slice_qty_ratio))
        slices: list[SliceInfo] = []
        start_time = time.time()
        allocated_qty = 0

        for i, weight in enumerate(normalized_profile):
            # 计算该分片的目标数量
            target_slice_qty = int(total_qty * weight)

            # 确保不小于最小分片数量
            slice_qty = max(min_slice_qty, target_slice_qty)

            # 确保不超过剩余数量
            remaining = total_qty - allocated_qty
            slice_qty = min(slice_qty, remaining)

            if slice_qty > 0:
                scheduled_time = start_time + i * interval
                slices.append(
                    SliceInfo(
                        index=i,
                        qty=slice_qty,
                        target_price=intent.limit_price,
                        scheduled_time=scheduled_time,
                        executed=False,
                    )
                )
                allocated_qty += slice_qty

        # 处理尾差（分配到最后一个分片）
        if allocated_qty < total_qty and slices:
            slices[-1].qty += total_qty - allocated_qty
        elif allocated_qty > total_qty and slices:
            # 如果超分配，从后往前减少
            excess = allocated_qty - total_qty
            for s in reversed(slices):
                reduce = min(excess, s.qty - 1)
                s.qty -= reduce
                excess -= reduce
                if excess <= 0:
                    break

        # 移除数量为 0 的分片
        slices = [s for s in slices if s.qty > 0]

        # 重新编号
        for i, s in enumerate(slices):
            s.index = i

        return slices

    def next_action(
        self, plan_id: str, current_time: float | None = None
    ) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: MODE2.EXECUTOR.VWAP

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
                    reason="VWAP 执行完成",
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
                reason="VWAP 执行完成",
            )

        # 查找下一个待执行的分片
        next_slice = self._find_next_slice(ctx)
        if next_slice is None:
            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = now
                return ExecutorAction(
                    action_type=ExecutorActionType.COMPLETE,
                    reason="VWAP 执行完成",
                )
            else:
                ctx.status = ExecutorStatus.FAILED
                ctx.error = "所有分片已处理但未达成目标"
                return ExecutorAction(
                    action_type=ExecutorActionType.ABORT,
                    reason=ctx.error,
                )

        # 检查执行时间
        if next_slice.scheduled_time is not None and now < next_slice.scheduled_time:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                wait_until=next_slice.scheduled_time,
                reason=f"等待分片 #{next_slice.index} 执行时间",
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
            reason=f"VWAP 分片 #{next_slice.index}/{len(ctx.slices)}",
            metadata={
                "intent_id": ctx.intent.intent_id,
                "slice_index": next_slice.index,
                "retry_count": slice_cancelled_count,
                "volume_weight": self._vwap_config.volume_profile[next_slice.index]
                if next_slice.index < len(self._vwap_config.volume_profile)
                else 0.0,
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

        V4PRO Scenario: MODE2.EXECUTOR.VWAP

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

    def get_schedule(self, plan_id: str) -> list[dict[str, Any]]:
        """获取执行时间表（含成交量权重）.

        Args:
            plan_id: 计划ID

        Returns:
            分片时间表列表
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return []

        profile = self._vwap_config.volume_profile
        return [
            {
                "index": s.index,
                "qty": s.qty,
                "scheduled_time": s.scheduled_time,
                "executed": s.executed,
                "volume_weight": profile[s.index] if s.index < len(profile) else 0.0,
            }
            for s in ctx.slices
        ]

    def set_volume_profile(self, profile: list[float]) -> None:
        """设置成交量分布曲线.

        用于动态更新成交量分布。注意：只影响新创建的计划，
        不影响已有计划（M7 回放一致性）。

        Args:
            profile: 成交量分布曲线（各时段占比列表）
        """
        self._vwap_config.volume_profile = profile.copy()
