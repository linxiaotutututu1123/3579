"""
行为伪装拆单算法.

V4PRO Platform Component - Behavioral Disguise Order Splitter
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- SPLITTER.BEHAVIORAL.RANDOM: 随机化分片时间
- SPLITTER.BEHAVIORAL.SIZE_VARIANCE: 分片大小变化
- SPLITTER.BEHAVIORAL.NOISE: 交易噪声注入

设计原则:
- 隐藏真实交易意图,防止市场跟踪
- 模拟散户交易行为模式
- 保持确定性(M7回放一致)通过固定随机种子
- 军规合规的同时实现行为伪装
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

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


class DisguisePattern(str, Enum):
    """伪装模式枚举.

    Attributes:
        RETAIL: 散户模式 - 小额随机交易
        INSTITUTIONAL: 机构模式 - 大额间隔交易
        HYBRID: 混合模式 - 随机切换
        ADAPTIVE: 自适应模式 - 根据市场状态调整
    """

    RETAIL = "RETAIL"
    INSTITUTIONAL = "INSTITUTIONAL"
    HYBRID = "HYBRID"
    ADAPTIVE = "ADAPTIVE"


class NoiseType(str, Enum):
    """噪声类型枚举.

    Attributes:
        NONE: 无噪声
        TIMING: 时间噪声
        SIZE: 大小噪声
        BOTH: 时间和大小噪声
    """

    NONE = "NONE"
    TIMING = "TIMING"
    SIZE = "SIZE"
    BOTH = "BOTH"


@dataclass
class BehavioralConfig(ExecutorConfig):
    """行为伪装执行器配置.

    Attributes:
        max_slice_qty: 单个分片最大数量
        min_slice_qty: 单个分片最小数量
        price_tolerance: 价格容忍度
        timeout_seconds: 订单超时时间
        retry_count: 重试次数
        audit_enabled: 是否启用审计
        pattern: 伪装模式
        noise_type: 噪声类型
        duration_seconds: 执行总时长
        min_interval_seconds: 最小间隔时间
        max_interval_seconds: 最大间隔时间
        size_variance: 分片大小变异系数 (0.0-1.0)
        timing_variance: 时间间隔变异系数 (0.0-1.0)
        min_slices: 最少分片数量
        max_slices: 最多分片数量
        enable_fake_cancels: 是否启用假撤单
        fake_cancel_ratio: 假撤单比例
    """

    pattern: DisguisePattern = DisguisePattern.RETAIL
    noise_type: NoiseType = NoiseType.BOTH
    duration_seconds: float = 300.0
    min_interval_seconds: float = 5.0
    max_interval_seconds: float = 60.0
    size_variance: float = 0.3
    timing_variance: float = 0.4
    min_slices: int = 5
    max_slices: int = 20
    enable_fake_cancels: bool = False
    fake_cancel_ratio: float = 0.1


@dataclass
class DisguiseState:
    """伪装状态.

    用于跟踪伪装执行的内部状态。

    Attributes:
        random_seed: 随机种子(用于M7回放一致性)
        rng: 随机数生成器实例
        current_pattern: 当前使用的伪装模式
        pattern_switch_count: 模式切换次数
        fake_cancel_count: 假撤单次数
    """

    random_seed: int
    rng: random.Random = field(init=False)
    current_pattern: DisguisePattern = DisguisePattern.RETAIL
    pattern_switch_count: int = 0
    fake_cancel_count: int = 0

    def __post_init__(self) -> None:
        """初始化随机数生成器."""
        self.rng = random.Random(self.random_seed)


class BehavioralDisguiseExecutor(ExecutorBase):
    """行为伪装执行器.

    V4PRO Scenarios:
    - SPLITTER.BEHAVIORAL.RANDOM: 随机化分片时间
    - SPLITTER.BEHAVIORAL.SIZE_VARIANCE: 分片大小变化
    - SPLITTER.BEHAVIORAL.NOISE: 交易噪声注入

    执行逻辑:
    1. make_plan: 生成带有随机化特征的分片计划
    2. next_action: 按伪装时间表执行
    3. on_event: 处理事件并更新伪装状态

    军规级要求:
    - 使用确定性随机种子保证回放一致 (M7)
    - 幂等执行 (M2)
    - 完整审计日志 (M3)
    """

    def __init__(self, config: BehavioralConfig | None = None) -> None:
        """初始化行为伪装执行器.

        Args:
            config: 执行器配置
        """
        super().__init__(config or BehavioralConfig())
        self._behavioral_config: BehavioralConfig = self._config  # type: ignore[assignment]
        self._disguise_states: dict[str, DisguiseState] = {}

    def _generate_seed(self, intent: OrderIntent) -> int:
        """生成确定性随机种子.

        V4PRO Scenario: MODE2.INTENT.REPLAY

        使用 intent_id 生成确定性种子,确保回放一致性。

        Args:
            intent: 交易意图

        Returns:
            随机种子
        """
        # 使用 intent_id 的哈希值作为种子
        hash_bytes = hashlib.sha256(intent.intent_id.encode()).digest()
        return int.from_bytes(hash_bytes[:8], byteorder="big")

    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: SPLITTER.BEHAVIORAL.RANDOM

        生成带有行为伪装特征的分片计划。

        Args:
            intent: 交易意图

        Returns:
            计划ID
        """
        plan_id = intent.intent_id

        # 幂等检查
        if plan_id in self._plans:
            return plan_id

        # 生成确定性随机种子
        seed = self._generate_seed(intent)
        disguise_state = DisguiseState(
            random_seed=seed,
            current_pattern=self._behavioral_config.pattern,
        )
        self._disguise_states[plan_id] = disguise_state

        # 计算分片
        slices = self._calculate_disguised_slices(intent, disguise_state)

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

        # 保存元数据
        ctx.metadata["algo"] = "BEHAVIORAL"
        ctx.metadata["pattern"] = self._behavioral_config.pattern.value
        ctx.metadata["noise_type"] = self._behavioral_config.noise_type.value
        ctx.metadata["random_seed"] = seed
        ctx.metadata["slice_count"] = len(slices)

        self._plans[plan_id] = ctx

        return plan_id

    def _calculate_disguised_slices(
        self,
        intent: OrderIntent,
        state: DisguiseState,
    ) -> list[SliceInfo]:
        """计算带伪装特征的分片.

        V4PRO Scenarios:
        - SPLITTER.BEHAVIORAL.SIZE_VARIANCE: 分片大小变化
        - SPLITTER.BEHAVIORAL.NOISE: 噪声注入

        Args:
            intent: 交易意图
            state: 伪装状态

        Returns:
            分片列表
        """
        total_qty = intent.target_qty
        config = self._behavioral_config
        rng = state.rng

        # 确定分片数量(随机化)
        base_slices = max(
            config.min_slices,
            min(config.max_slices, total_qty // config.max_slice_qty),
        )

        # 根据模式调整分片数量
        if state.current_pattern == DisguisePattern.RETAIL:
            # 散户模式: 更多小额分片
            slice_count = int(base_slices * rng.uniform(1.2, 1.5))
        elif state.current_pattern == DisguisePattern.INSTITUTIONAL:
            # 机构模式: 较少大额分片
            slice_count = int(base_slices * rng.uniform(0.6, 0.8))
        elif state.current_pattern == DisguisePattern.HYBRID:
            # 混合模式: 随机分片数
            slice_count = int(base_slices * rng.uniform(0.8, 1.2))
        else:
            slice_count = base_slices

        slice_count = max(1, min(slice_count, config.max_slices))

        # 生成分片大小(带变异)
        slice_sizes = self._generate_varied_sizes(
            total_qty, slice_count, state
        )

        # 生成分片时间(带变异)
        slice_times = self._generate_varied_times(
            len(slice_sizes), state
        )

        # 创建分片
        slices: list[SliceInfo] = []
        for i, (qty, scheduled_time) in enumerate(zip(slice_sizes, slice_times)):
            if qty > 0:
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

    def _generate_varied_sizes(
        self,
        total_qty: int,
        slice_count: int,
        state: DisguiseState,
    ) -> list[int]:
        """生成变异分片大小.

        V4PRO Scenario: SPLITTER.BEHAVIORAL.SIZE_VARIANCE

        Args:
            total_qty: 总数量
            slice_count: 分片数量
            state: 伪装状态

        Returns:
            分片大小列表
        """
        config = self._behavioral_config
        rng = state.rng

        if config.noise_type in (NoiseType.SIZE, NoiseType.BOTH):
            variance = config.size_variance
        else:
            variance = 0.0

        # 生成随机权重
        weights = []
        for _ in range(slice_count):
            weight = rng.uniform(1.0 - variance, 1.0 + variance)
            weights.append(max(0.1, weight))

        # 归一化并分配数量
        total_weight = sum(weights)
        sizes = []
        allocated = 0

        for i, weight in enumerate(weights):
            if i == len(weights) - 1:
                # 最后一个分片分配剩余数量
                size = total_qty - allocated
            else:
                size = int(total_qty * weight / total_weight)
                # 确保在范围内
                size = max(config.min_slice_qty, min(size, config.max_slice_qty))

            if size > 0:
                sizes.append(size)
                allocated += size

        # 调整尾差
        if allocated < total_qty and sizes:
            sizes[-1] += total_qty - allocated
        elif allocated > total_qty and sizes:
            excess = allocated - total_qty
            for i in range(len(sizes) - 1, -1, -1):
                reduce = min(excess, sizes[i] - 1)
                sizes[i] -= reduce
                excess -= reduce
                if excess <= 0:
                    break

        return [s for s in sizes if s > 0]

    def _generate_varied_times(
        self,
        slice_count: int,
        state: DisguiseState,
    ) -> list[float]:
        """生成变异分片时间.

        V4PRO Scenario: SPLITTER.BEHAVIORAL.RANDOM

        Args:
            slice_count: 分片数量
            state: 伪装状态

        Returns:
            分片调度时间列表
        """
        config = self._behavioral_config
        rng = state.rng

        if config.noise_type in (NoiseType.TIMING, NoiseType.BOTH):
            variance = config.timing_variance
        else:
            variance = 0.0

        start_time = time.time()
        times: list[float] = []
        current_time = start_time

        for i in range(slice_count):
            if i == 0:
                # 第一个分片立即执行
                times.append(current_time)
            else:
                # 计算基础间隔
                base_interval = config.duration_seconds / slice_count

                # 应用变异
                if variance > 0:
                    interval = base_interval * rng.uniform(
                        1.0 - variance, 1.0 + variance
                    )
                else:
                    interval = base_interval

                # 限制间隔范围
                interval = max(
                    config.min_interval_seconds,
                    min(interval, config.max_interval_seconds),
                )

                current_time += interval
                times.append(current_time)

        return times

    def next_action(
        self, plan_id: str, current_time: float | None = None
    ) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: SPLITTER.BEHAVIORAL

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳

        Returns:
            下一个动作
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
                    reason="行为伪装执行完成",
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
                    reason=f"订单超时 ({elapsed:.1f}s)",
                )

        # 有挂单时等待
        if ctx.pending_orders:
            return ExecutorAction(
                action_type=ExecutorActionType.WAIT,
                reason="等待订单响应",
            )

        # 检查是否完成
        if ctx.progress.filled_qty >= ctx.intent.target_qty:
            ctx.status = ExecutorStatus.COMPLETED
            ctx.end_time = now
            return ExecutorAction(
                action_type=ExecutorActionType.COMPLETE,
                reason="行为伪装执行完成",
            )

        # 查找下一个待执行分片
        next_slice = self._find_next_slice(ctx)
        if next_slice is None:
            if ctx.progress.filled_qty >= ctx.intent.target_qty:
                ctx.status = ExecutorStatus.COMPLETED
                ctx.end_time = now
                return ExecutorAction(
                    action_type=ExecutorActionType.COMPLETE,
                    reason="行为伪装执行完成",
                )
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
            1
            for oid in ctx.cancelled_orders
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

        # 获取伪装模式信息
        disguise_state = self._disguise_states.get(plan_id)
        pattern = disguise_state.current_pattern.value if disguise_state else "UNKNOWN"

        # 返回下单动作
        return ExecutorAction(
            action_type=ExecutorActionType.PLACE_ORDER,
            client_order_id=client_order_id,
            instrument=ctx.intent.instrument,
            side=ctx.intent.side,
            offset=ctx.intent.offset,
            price=next_slice.target_price,
            qty=order_qty,
            reason=f"行为伪装分片 #{next_slice.index}/{len(ctx.slices)} ({pattern})",
            metadata={
                "intent_id": ctx.intent.intent_id,
                "slice_index": next_slice.index,
                "retry_count": slice_cancelled_count,
                "pattern": pattern,
                "scheduled_time": next_slice.scheduled_time,
            },
        )

    def _find_next_slice(self, ctx: ExecutionPlanContext) -> SliceInfo | None:
        """查找下一个待执行分片.

        Args:
            ctx: 计划上下文

        Returns:
            下一个待执行的分片
        """
        for slice_info in ctx.slices:
            if not slice_info.executed:
                return slice_info
        return None

    def _get_slice_index_from_order_id(self, client_order_id: str) -> int:
        """从订单ID解析分片索引.

        Args:
            client_order_id: 客户订单ID

        Returns:
            分片索引
        """
        try:
            _, slice_index, _ = IntentIdGenerator.parse_client_order_id(client_order_id)
        except ValueError:
            return -1
        return slice_index

    def on_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

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

        elif (
            event.event_type in {"REJECT", "CANCEL_ACK"}
            and client_order_id in ctx.pending_orders
        ):
            del ctx.pending_orders[client_order_id]
            ctx.cancelled_orders.append(client_order_id)

            slice_index = self._get_slice_index_from_order_id(client_order_id)
            if 0 <= slice_index < len(ctx.slices):
                ctx.slices[slice_index].executed = False
                ctx.current_slice_index = min(ctx.current_slice_index, slice_index)

    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消计划.

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

        # 清理伪装状态
        if plan_id in self._disguise_states:
            del self._disguise_states[plan_id]

        return True

    def get_status(self, plan_id: str) -> ExecutorStatus | None:
        """获取计划状态.

        Args:
            plan_id: 计划ID

        Returns:
            状态
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
            进度
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return None

        ctx.update_progress()
        return ctx.progress

    def get_disguise_info(self, plan_id: str) -> dict[str, Any] | None:
        """获取伪装信息.

        Args:
            plan_id: 计划ID

        Returns:
            伪装信息字典
        """
        ctx = self._plans.get(plan_id)
        state = self._disguise_states.get(plan_id)
        if ctx is None or state is None:
            return None

        return {
            "plan_id": plan_id,
            "random_seed": state.random_seed,
            "current_pattern": state.current_pattern.value,
            "pattern_switch_count": state.pattern_switch_count,
            "fake_cancel_count": state.fake_cancel_count,
            "slice_count": len(ctx.slices),
            "executed_slices": sum(1 for s in ctx.slices if s.executed),
        }
