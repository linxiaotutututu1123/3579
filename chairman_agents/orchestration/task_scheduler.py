"""任务调度器模块.

本模块提供任务调度功能，支持：
- 基于优先级的任务调度
- 依赖感知调度
- 调度策略可插拔
- 任务队列管理

核心类:
    SchedulingStrategy: 调度策略枚举
    ScheduledTask: 已调度任务包装
    TaskScheduler: 任务调度器实现
    TaskSchedulerProtocol: 调度器协议接口

Example:
    >>> scheduler = TaskScheduler(strategy=SchedulingStrategy.PRIORITY_FIRST)
    >>> await scheduler.submit(task1)
    >>> await scheduler.submit(task2)
    >>> next_task = await scheduler.next()
"""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from chairman_agents.core.exceptions import DependencyError
from chairman_agents.core.types import Task, TaskId, TaskPriority, TaskStatus
from chairman_agents.orchestration.dependency_resolver import (
    DependencyResolver,
    ResolutionResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


# =============================================================================
# 枚举定义
# =============================================================================


class SchedulingStrategy(Enum):
    """调度策略枚举.

    Strategies:
        FIFO: 先进先出，按提交顺序执行
        PRIORITY_FIRST: 优先级优先，高优先级任务先执行
        SHORTEST_FIRST: 最短任务优先，预估时间短的先执行
        DEPENDENCY_AWARE: 依赖感知，自动处理依赖关系
        BALANCED: 平衡策略，综合考虑优先级和依赖
    """

    FIFO = "fifo"
    """先进先出策略"""

    PRIORITY_FIRST = "priority_first"
    """优先级优先策略"""

    SHORTEST_FIRST = "shortest_first"
    """最短任务优先策略"""

    DEPENDENCY_AWARE = "dependency_aware"
    """依赖感知策略"""

    BALANCED = "balanced"
    """平衡策略"""


class SchedulerState(Enum):
    """调度器状态枚举.

    States:
        IDLE: 空闲状态
        RUNNING: 运行中
        PAUSED: 暂停
        STOPPED: 已停止
    """

    IDLE = "idle"
    """空闲状态"""

    RUNNING = "running"
    """运行中"""

    PAUSED = "paused"
    """暂停"""

    STOPPED = "stopped"
    """已停止"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass(order=True)
class ScheduledTask:
    """已调度任务包装器.

    用于优先级队列的任务包装，支持比较排序。

    Attributes:
        priority_value: 优先级数值（用于排序）
        submit_time: 提交时间
        sequence: 提交序列号（保证稳定排序）
        task: 原始任务对象
        scheduled_at: 调度时间
        execution_deadline: 执行截止时间
        retry_count: 重试次数
        metadata: 额外元数据
    """

    priority_value: int = field(compare=True)
    """优先级数值，数值越小优先级越高"""

    submit_time: float = field(compare=True)
    """提交时间戳"""

    sequence: int = field(compare=True)
    """提交序列号"""

    task: Task = field(compare=False)
    """原始任务对象"""

    scheduled_at: datetime = field(default_factory=datetime.now, compare=False)
    """调度时间"""

    execution_deadline: datetime | None = field(default=None, compare=False)
    """执行截止时间"""

    retry_count: int = field(default=0, compare=False)
    """重试次数"""

    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
    """额外元数据"""

    @classmethod
    def from_task(
        cls,
        task: Task,
        sequence: int,
        *,
        priority_override: int | None = None,
    ) -> ScheduledTask:
        """从 Task 创建 ScheduledTask.

        Args:
            task: 原始任务
            sequence: 序列号
            priority_override: 优先级覆盖值（可选）

        Returns:
            包装后的 ScheduledTask
        """
        priority_value = priority_override if priority_override is not None else task.priority.value
        return cls(
            priority_value=priority_value,
            submit_time=datetime.now().timestamp(),
            sequence=sequence,
            task=task,
        )


@dataclass
class SchedulerStats:
    """调度器统计信息.

    Attributes:
        total_submitted: 总提交任务数
        total_scheduled: 总调度任务数
        total_completed: 总完成任务数
        total_failed: 总失败任务数
        current_queue_size: 当前队列大小
        average_wait_time: 平均等待时间（秒）
        average_execution_time: 平均执行时间（秒）
    """

    total_submitted: int = 0
    """总提交任务数"""

    total_scheduled: int = 0
    """总调度任务数"""

    total_completed: int = 0
    """总完成任务数"""

    total_failed: int = 0
    """总失败任务数"""

    current_queue_size: int = 0
    """当前队列大小"""

    average_wait_time: float = 0.0
    """平均等待时间（秒）"""

    average_execution_time: float = 0.0
    """平均执行时间（秒）"""


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class TaskSchedulerProtocol(Protocol):
    """任务调度器协议.

    定义任务调度器的标准接口。

    Example:
        >>> class MyScheduler(TaskSchedulerProtocol):
        ...     async def submit(self, task: Task) -> None:
        ...         # 实现提交逻辑
        ...         pass
    """

    async def submit(self, task: Task) -> None:
        """提交任务到调度器.

        Args:
            task: 要提交的任务
        """
        ...

    async def submit_batch(self, tasks: Sequence[Task]) -> None:
        """批量提交任务.

        Args:
            tasks: 任务列表
        """
        ...

    async def next(self) -> Task | None:
        """获取下一个待执行任务.

        Returns:
            下一个任务，队列为空时返回 None
        """
        ...

    async def cancel(self, task_id: TaskId) -> bool:
        """取消任务.

        Args:
            task_id: 要取消的任务 ID

        Returns:
            是否取消成功
        """
        ...

    async def pause(self) -> None:
        """暂停调度器."""
        ...

    async def resume(self) -> None:
        """恢复调度器."""
        ...


# =============================================================================
# 调度器实现
# =============================================================================


class TaskScheduler:
    """任务调度器.

    提供灵活的任务调度功能：
    - 多种调度策略
    - 依赖关系处理
    - 优先级队列
    - 任务生命周期管理

    Attributes:
        strategy: 当前调度策略
        state: 调度器状态
        dependency_resolver: 依赖解析器
        max_queue_size: 最大队列大小

    Example:
        >>> scheduler = TaskScheduler(
        ...     strategy=SchedulingStrategy.BALANCED,
        ...     max_queue_size=1000,
        ... )
        >>> await scheduler.start()
        >>> await scheduler.submit(task)
        >>> next_task = await scheduler.next()
    """

    def __init__(
        self,
        strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIRST,
        *,
        max_queue_size: int = 10000,
        enable_dependency_resolution: bool = True,
    ) -> None:
        """初始化任务调度器.

        Args:
            strategy: 调度策略
            max_queue_size: 最大队列大小
            enable_dependency_resolution: 是否启用依赖解析
        """
        self.strategy = strategy
        self.state = SchedulerState.IDLE
        self.max_queue_size = max_queue_size
        self._enable_dependency_resolution = enable_dependency_resolution

        # 内部状态
        self._queue: list[ScheduledTask] = []
        self._sequence_counter = 0
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition()

        # 任务跟踪
        self._pending_tasks: dict[TaskId, ScheduledTask] = {}
        self._running_tasks: dict[TaskId, ScheduledTask] = {}
        self._completed_tasks: dict[TaskId, ScheduledTask] = {}
        self._failed_tasks: dict[TaskId, ScheduledTask] = {}

        # 依赖解析器
        self.dependency_resolver = DependencyResolver() if enable_dependency_resolution else None

        # 统计信息
        self._stats = SchedulerStats()

        # 回调函数
        self._on_task_scheduled: list[Callable[[Task], None]] = []
        self._on_task_completed: list[Callable[[Task], None]] = []
        self._on_task_failed: list[Callable[[Task, Exception], None]] = []

    async def start(self) -> None:
        """启动调度器."""
        async with self._lock:
            if self.state == SchedulerState.STOPPED:
                # 重新初始化
                self._queue.clear()
                self._pending_tasks.clear()
            self.state = SchedulerState.RUNNING

    async def stop(self) -> None:
        """停止调度器."""
        async with self._lock:
            self.state = SchedulerState.STOPPED

    async def pause(self) -> None:
        """暂停调度器.

        暂停后不会调度新任务，但已运行的任务会继续执行。
        """
        async with self._lock:
            if self.state == SchedulerState.RUNNING:
                self.state = SchedulerState.PAUSED

    async def resume(self) -> None:
        """恢复调度器."""
        async with self._lock:
            if self.state == SchedulerState.PAUSED:
                self.state = SchedulerState.RUNNING

    async def submit(self, task: Task) -> None:
        """提交单个任务到调度器.

        Args:
            task: 要提交的任务

        Raises:
            RuntimeError: 队列已满时抛出
        """
        async with self._lock:
            if len(self._queue) >= self.max_queue_size:
                raise RuntimeError(f"调度队列已满，最大容量: {self.max_queue_size}")

            # 依赖解析
            if self.dependency_resolver and task.dependencies:
                await self.dependency_resolver.add_task(task)

            scheduled_task = self._create_scheduled_task(task)
            self._enqueue(scheduled_task)
            self._pending_tasks[task.id] = scheduled_task
            self._stats.total_submitted += 1
            self._stats.current_queue_size = len(self._queue)

            # 触发回调
            for callback in self._on_task_scheduled:
                callback(task)

    async def submit_batch(self, tasks: Sequence[Task]) -> None:
        """批量提交任务.

        批量提交比逐个提交更高效，特别是需要依赖解析时。

        Args:
            tasks: 任务列表

        Raises:
            RuntimeError: 队列空间不足时抛出
        """
        async with self._lock:
            if len(self._queue) + len(tasks) > self.max_queue_size:
                raise RuntimeError(
                    f"队列空间不足，需要 {len(tasks)} 个位置，"
                    f"当前可用 {self.max_queue_size - len(self._queue)}"
                )

            # 依赖解析
            if self.dependency_resolver:
                result = await self.dependency_resolver.resolve(tasks)
                if not result.success:
                    if result.circular_dependencies:
                        raise DependencyError(
                            "检测到循环依赖",
                            dependency_type="circular",
                            dependency_chain=result.circular_dependencies[0],
                        )
                    if result.missing_dependencies:
                        raise DependencyError(
                            "存在缺失的依赖",
                            dependency_type="missing",
                            blocking_tasks=list(result.missing_dependencies),
                        )

            for task in tasks:
                scheduled_task = self._create_scheduled_task(task)
                self._enqueue(scheduled_task)
                self._pending_tasks[task.id] = scheduled_task
                self._stats.total_submitted += 1

            self._stats.current_queue_size = len(self._queue)

    async def next(self, timeout: float | None = None) -> Task | None:
        """获取下一个待执行任务.

        根据调度策略返回最合适的任务。

        Args:
            timeout: 等待超时时间（秒），None 表示不等待

        Returns:
            下一个任务，或在超时/无任务时返回 None
        """
        async with self._lock:
            if self.state != SchedulerState.RUNNING:
                return None

            task = await self._dequeue_next(timeout)
            if task:
                self._stats.total_scheduled += 1
                self._running_tasks[task.id] = self._pending_tasks.pop(task.id)
                task.status = TaskStatus.ASSIGNED
                task.started_at = datetime.now()

            return task

    async def peek(self) -> Task | None:
        """查看下一个任务但不移除.

        Returns:
            下一个任务，队列为空时返回 None
        """
        async with self._lock:
            if not self._queue:
                return None
            return self._queue[0].task

    async def cancel(self, task_id: TaskId) -> bool:
        """取消任务.

        只能取消尚未开始执行的任务。

        Args:
            task_id: 要取消的任务 ID

        Returns:
            是否取消成功
        """
        async with self._lock:
            if task_id not in self._pending_tasks:
                return False

            # 从队列中移除
            self._queue = [st for st in self._queue if st.task.id != task_id]
            heapq.heapify(self._queue)

            scheduled_task = self._pending_tasks.pop(task_id)
            scheduled_task.task.status = TaskStatus.CANCELLED
            self._stats.current_queue_size = len(self._queue)

            return True

    async def cancel_all(self) -> int:
        """取消所有待处理任务.

        Returns:
            取消的任务数量
        """
        async with self._lock:
            count = len(self._queue)
            for scheduled_task in self._queue:
                scheduled_task.task.status = TaskStatus.CANCELLED
            self._queue.clear()
            self._pending_tasks.clear()
            self._stats.current_queue_size = 0
            return count

    async def mark_completed(self, task_id: TaskId) -> None:
        """标记任务为已完成.

        Args:
            task_id: 完成的任务 ID
        """
        async with self._lock:
            if task_id in self._running_tasks:
                scheduled_task = self._running_tasks.pop(task_id)
                scheduled_task.task.status = TaskStatus.COMPLETED
                scheduled_task.task.completed_at = datetime.now()
                self._completed_tasks[task_id] = scheduled_task
                self._stats.total_completed += 1

                # 更新依赖状态
                if self.dependency_resolver:
                    newly_ready = await self.dependency_resolver.mark_completed(task_id)
                    # 可以在这里触发新可执行任务的通知

                # 触发回调
                for callback in self._on_task_completed:
                    callback(scheduled_task.task)

    async def mark_failed(
        self,
        task_id: TaskId,
        error: Exception | None = None,
    ) -> None:
        """标记任务为失败.

        Args:
            task_id: 失败的任务 ID
            error: 导致失败的异常（可选）
        """
        async with self._lock:
            if task_id in self._running_tasks:
                scheduled_task = self._running_tasks.pop(task_id)
                scheduled_task.task.status = TaskStatus.FAILED
                self._failed_tasks[task_id] = scheduled_task
                self._stats.total_failed += 1

                # 更新依赖状态
                if self.dependency_resolver:
                    await self.dependency_resolver.mark_failed(task_id)

                # 触发回调
                for callback in self._on_task_failed:
                    callback(scheduled_task.task, error or Exception("任务执行失败"))

    async def retry(self, task_id: TaskId, max_retries: int = 3) -> bool:
        """重试失败的任务.

        Args:
            task_id: 要重试的任务 ID
            max_retries: 最大重试次数

        Returns:
            是否成功加入重试队列
        """
        async with self._lock:
            if task_id not in self._failed_tasks:
                return False

            scheduled_task = self._failed_tasks.get(task_id)
            if scheduled_task and scheduled_task.retry_count < max_retries:
                scheduled_task.retry_count += 1
                scheduled_task.task.status = TaskStatus.PENDING
                self._enqueue(scheduled_task)
                self._pending_tasks[task_id] = scheduled_task
                del self._failed_tasks[task_id]
                return True

            return False

    async def get_task_status(self, task_id: TaskId) -> TaskStatus | None:
        """获取任务状态.

        Args:
            task_id: 任务 ID

        Returns:
            任务状态，任务不存在时返回 None
        """
        async with self._lock:
            if task_id in self._pending_tasks:
                return self._pending_tasks[task_id].task.status
            if task_id in self._running_tasks:
                return self._running_tasks[task_id].task.status
            if task_id in self._completed_tasks:
                return TaskStatus.COMPLETED
            if task_id in self._failed_tasks:
                return TaskStatus.FAILED
            return None

    async def get_queue_snapshot(self) -> list[Task]:
        """获取当前队列快照.

        Returns:
            队列中所有任务的副本列表
        """
        async with self._lock:
            return [st.task for st in self._queue]

    def on_task_scheduled(self, callback: Callable[[Task], None]) -> None:
        """注册任务调度回调.

        Args:
            callback: 任务被调度时调用的函数
        """
        self._on_task_scheduled.append(callback)

    def on_task_completed(self, callback: Callable[[Task], None]) -> None:
        """注册任务完成回调.

        Args:
            callback: 任务完成时调用的函数
        """
        self._on_task_completed.append(callback)

    def on_task_failed(self, callback: Callable[[Task, Exception], None]) -> None:
        """注册任务失败回调.

        Args:
            callback: 任务失败时调用的函数
        """
        self._on_task_failed.append(callback)

    @property
    def stats(self) -> SchedulerStats:
        """获取调度器统计信息."""
        self._stats.current_queue_size = len(self._queue)
        return self._stats

    @property
    def is_empty(self) -> bool:
        """检查队列是否为空."""
        return len(self._queue) == 0

    @property
    def queue_size(self) -> int:
        """获取当前队列大小."""
        return len(self._queue)

    def _create_scheduled_task(self, task: Task) -> ScheduledTask:
        """创建 ScheduledTask 包装.

        Args:
            task: 原始任务

        Returns:
            包装后的 ScheduledTask
        """
        self._sequence_counter += 1
        priority_value = self._calculate_priority(task)
        return ScheduledTask(
            priority_value=priority_value,
            submit_time=datetime.now().timestamp(),
            sequence=self._sequence_counter,
            task=task,
        )

    def _calculate_priority(self, task: Task) -> int:
        """计算任务的调度优先级.

        根据调度策略计算综合优先级值。

        Args:
            task: 任务对象

        Returns:
            优先级值（越小越优先）
        """
        if self.strategy == SchedulingStrategy.FIFO:
            return 0  # FIFO 不区分优先级
        elif self.strategy == SchedulingStrategy.PRIORITY_FIRST:
            return task.priority.value
        elif self.strategy == SchedulingStrategy.SHORTEST_FIRST:
            # 使用预估时间作为优先级
            return int(task.estimated_hours * 100)
        elif self.strategy == SchedulingStrategy.DEPENDENCY_AWARE:
            # 依赖少的优先
            base_priority = task.priority.value
            dependency_penalty = len(task.dependencies) * 10
            return base_priority + dependency_penalty
        elif self.strategy == SchedulingStrategy.BALANCED:
            # 综合考虑多个因素
            base_priority = task.priority.value * 100
            complexity_factor = task.complexity * 10
            dependency_penalty = len(task.dependencies) * 50
            return base_priority + complexity_factor + dependency_penalty
        return task.priority.value

    def _enqueue(self, scheduled_task: ScheduledTask) -> None:
        """将任务加入队列.

        Args:
            scheduled_task: 已调度的任务
        """
        heapq.heappush(self._queue, scheduled_task)

    async def _dequeue_next(self, timeout: float | None = None) -> Task | None:
        """从队列中取出下一个任务.

        Args:
            timeout: 等待超时时间

        Returns:
            下一个可执行的任务
        """
        if not self._queue:
            return None

        # 如果启用了依赖解析，需要检查依赖是否满足
        if self.dependency_resolver:
            ready_tasks = await self.dependency_resolver.get_ready_tasks()
            ready_ids = {t.id for t in ready_tasks}

            # 找到队列中第一个就绪的任务
            for i, scheduled_task in enumerate(self._queue):
                if scheduled_task.task.id in ready_ids or not scheduled_task.task.dependencies:
                    # 移除并返回
                    self._queue.pop(i)
                    heapq.heapify(self._queue)
                    self._stats.current_queue_size = len(self._queue)
                    return scheduled_task.task

            # 没有就绪的任务
            return None

        # 简单策略：直接弹出队首
        scheduled_task = heapq.heappop(self._queue)
        self._stats.current_queue_size = len(self._queue)
        return scheduled_task.task


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "SchedulingStrategy",
    "SchedulerState",
    "ScheduledTask",
    "SchedulerStats",
    "TaskSchedulerProtocol",
    "TaskScheduler",
]
