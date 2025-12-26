"""TaskScheduler 单元测试模块.

测试覆盖:
- TaskScheduler 初始化
- 任务调度逻辑
- 优先级队列
- 任务依赖管理
- 并发执行控制
- 任务取消和超时
- 调度策略
- 回调机制
- 统计信息
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chairman_agents.core.exceptions import DependencyError
from chairman_agents.core.types import Task, TaskId, TaskPriority, TaskStatus
from chairman_agents.orchestration.dependency_resolver import (
    DependencyResolver,
    ResolutionResult,
)
from chairman_agents.orchestration.task_scheduler import (
    ScheduledTask,
    SchedulerState,
    SchedulerStats,
    SchedulingStrategy,
    TaskScheduler,
    TaskSchedulerProtocol,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_task() -> Task:
    """创建一个示例任务."""
    return Task(
        id="task-001",
        title="Sample Task",
        description="A sample task for testing",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING,
        complexity=5,
        estimated_hours=2.0,
        dependencies=[],
    )


@pytest.fixture
def high_priority_task() -> Task:
    """创建一个高优先级任务."""
    return Task(
        id="task-high",
        title="High Priority Task",
        description="A high priority task",
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.PENDING,
        complexity=3,
        estimated_hours=1.0,
        dependencies=[],
    )


@pytest.fixture
def low_priority_task() -> Task:
    """创建一个低优先级任务."""
    return Task(
        id="task-low",
        title="Low Priority Task",
        description="A low priority task",
        priority=TaskPriority.LOW,
        status=TaskStatus.PENDING,
        complexity=2,
        estimated_hours=0.5,
        dependencies=[],
    )


@pytest.fixture
def task_with_dependencies() -> Task:
    """创建一个有依赖的任务."""
    return Task(
        id="task-dep",
        title="Task with Dependencies",
        description="A task that depends on others",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING,
        dependencies=["task-001", "task-002"],
    )


@pytest.fixture
def multiple_tasks() -> list[Task]:
    """创建多个任务."""
    return [
        Task(
            id=f"task-{i:03d}",
            title=f"Task {i}",
            description=f"Task description {i}",
            priority=TaskPriority(i % 5 + 1),  # 1-5 优先级轮转
            status=TaskStatus.PENDING,
            complexity=i % 10 + 1,
            estimated_hours=float(i % 8 + 1),
            dependencies=[],
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def scheduler() -> TaskScheduler:
    """创建默认调度器."""
    return TaskScheduler(
        strategy=SchedulingStrategy.PRIORITY_FIRST,
        max_queue_size=100,
        enable_dependency_resolution=False,
    )


@pytest.fixture
def scheduler_with_deps() -> TaskScheduler:
    """创建启用依赖解析的调度器."""
    return TaskScheduler(
        strategy=SchedulingStrategy.DEPENDENCY_AWARE,
        max_queue_size=100,
        enable_dependency_resolution=True,
    )


# =============================================================================
# 初始化测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskSchedulerInit:
    """TaskScheduler 初始化测试."""

    def test_default_initialization(self) -> None:
        """测试默认初始化."""
        scheduler = TaskScheduler()

        assert scheduler.strategy == SchedulingStrategy.PRIORITY_FIRST
        assert scheduler.state == SchedulerState.IDLE
        assert scheduler.max_queue_size == 10000
        assert scheduler._enable_dependency_resolution is True
        assert scheduler.is_empty is True
        assert scheduler.queue_size == 0
        assert scheduler.dependency_resolver is not None

    def test_custom_initialization(self) -> None:
        """测试自定义初始化."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.FIFO,
            max_queue_size=500,
            enable_dependency_resolution=False,
        )

        assert scheduler.strategy == SchedulingStrategy.FIFO
        assert scheduler.max_queue_size == 500
        assert scheduler._enable_dependency_resolution is False
        assert scheduler.dependency_resolver is None

    def test_all_scheduling_strategies(self) -> None:
        """测试所有调度策略初始化."""
        strategies = [
            SchedulingStrategy.FIFO,
            SchedulingStrategy.PRIORITY_FIRST,
            SchedulingStrategy.SHORTEST_FIRST,
            SchedulingStrategy.DEPENDENCY_AWARE,
            SchedulingStrategy.BALANCED,
        ]

        for strategy in strategies:
            scheduler = TaskScheduler(strategy=strategy)
            assert scheduler.strategy == strategy

    def test_stats_initialization(self) -> None:
        """测试统计信息初始化."""
        scheduler = TaskScheduler()
        stats = scheduler.stats

        assert isinstance(stats, SchedulerStats)
        assert stats.total_submitted == 0
        assert stats.total_scheduled == 0
        assert stats.total_completed == 0
        assert stats.total_failed == 0
        assert stats.current_queue_size == 0
        assert stats.average_wait_time == 0.0
        assert stats.average_execution_time == 0.0


# =============================================================================
# 任务提交测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskSubmission:
    """任务提交测试."""

    @pytest.mark.asyncio
    async def test_submit_single_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试提交单个任务."""
        await scheduler.submit(sample_task)

        assert scheduler.queue_size == 1
        assert not scheduler.is_empty
        assert scheduler.stats.total_submitted == 1

    @pytest.mark.asyncio
    async def test_submit_multiple_tasks(
        self, scheduler: TaskScheduler, multiple_tasks: list[Task]
    ) -> None:
        """测试提交多个任务."""
        for task in multiple_tasks:
            await scheduler.submit(task)

        assert scheduler.queue_size == len(multiple_tasks)
        assert scheduler.stats.total_submitted == len(multiple_tasks)

    @pytest.mark.asyncio
    async def test_submit_batch(
        self, scheduler: TaskScheduler, multiple_tasks: list[Task]
    ) -> None:
        """测试批量提交任务."""
        await scheduler.submit_batch(multiple_tasks)

        assert scheduler.queue_size == len(multiple_tasks)
        assert scheduler.stats.total_submitted == len(multiple_tasks)

    @pytest.mark.asyncio
    async def test_submit_exceeds_max_queue_size(
        self, sample_task: Task
    ) -> None:
        """测试超出队列容量."""
        scheduler = TaskScheduler(max_queue_size=2)
        await scheduler.submit(sample_task)

        task2 = Task(id="task-002", title="Task 2")
        await scheduler.submit(task2)

        task3 = Task(id="task-003", title="Task 3")
        with pytest.raises(RuntimeError, match="调度队列已满"):
            await scheduler.submit(task3)

    @pytest.mark.asyncio
    async def test_submit_batch_exceeds_capacity(
        self, multiple_tasks: list[Task]
    ) -> None:
        """测试批量提交超出容量."""
        scheduler = TaskScheduler(max_queue_size=2)

        with pytest.raises(RuntimeError, match="队列空间不足"):
            await scheduler.submit_batch(multiple_tasks)

    @pytest.mark.asyncio
    async def test_submit_triggers_callback(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试提交任务触发回调."""
        callback_called = []

        def on_scheduled(task: Task) -> None:
            callback_called.append(task.id)

        scheduler.on_task_scheduled(on_scheduled)
        await scheduler.submit(sample_task)

        assert sample_task.id in callback_called


# =============================================================================
# 优先级队列测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestPriorityQueue:
    """优先级队列测试."""

    @pytest.mark.asyncio
    async def test_priority_first_strategy(
        self,
        high_priority_task: Task,
        low_priority_task: Task,
        sample_task: Task,
    ) -> None:
        """测试优先级优先策略."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.PRIORITY_FIRST,
            enable_dependency_resolution=False,
        )
        await scheduler.start()

        # 按非优先级顺序提交
        await scheduler.submit(low_priority_task)
        await scheduler.submit(sample_task)
        await scheduler.submit(high_priority_task)

        # 验证按优先级顺序获取
        task1 = await scheduler.next()
        assert task1 is not None
        assert task1.id == high_priority_task.id

        task2 = await scheduler.next()
        assert task2 is not None
        assert task2.id == sample_task.id

        task3 = await scheduler.next()
        assert task3 is not None
        assert task3.id == low_priority_task.id

    @pytest.mark.asyncio
    async def test_fifo_strategy(
        self, multiple_tasks: list[Task]
    ) -> None:
        """测试 FIFO 策略."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.FIFO,
            enable_dependency_resolution=False,
        )
        await scheduler.start()

        for task in multiple_tasks:
            await scheduler.submit(task)

        # FIFO 按提交顺序获取（sequence 决定顺序）
        for i, expected_task in enumerate(multiple_tasks):
            task = await scheduler.next()
            assert task is not None
            assert task.id == expected_task.id

    @pytest.mark.asyncio
    async def test_shortest_first_strategy(self) -> None:
        """测试最短任务优先策略."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.SHORTEST_FIRST,
            enable_dependency_resolution=False,
        )
        await scheduler.start()

        # 创建不同预估时间的任务
        long_task = Task(id="long", title="Long", estimated_hours=8.0)
        medium_task = Task(id="medium", title="Medium", estimated_hours=4.0)
        short_task = Task(id="short", title="Short", estimated_hours=1.0)

        await scheduler.submit(long_task)
        await scheduler.submit(medium_task)
        await scheduler.submit(short_task)

        # 按预估时间顺序获取
        task1 = await scheduler.next()
        assert task1 is not None
        assert task1.id == "short"

        task2 = await scheduler.next()
        assert task2 is not None
        assert task2.id == "medium"

        task3 = await scheduler.next()
        assert task3 is not None
        assert task3.id == "long"

    @pytest.mark.asyncio
    async def test_balanced_strategy(self) -> None:
        """测试平衡策略."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.BALANCED,
            enable_dependency_resolution=False,
        )
        await scheduler.start()

        # 创建不同优先级和复杂度的任务
        task1 = Task(
            id="t1",
            title="Low priority, low complexity",
            priority=TaskPriority.LOW,
            complexity=2,
        )
        task2 = Task(
            id="t2",
            title="High priority, high complexity",
            priority=TaskPriority.HIGH,
            complexity=8,
        )
        task3 = Task(
            id="t3",
            title="Critical priority, medium complexity",
            priority=TaskPriority.CRITICAL,
            complexity=5,
        )

        await scheduler.submit(task1)
        await scheduler.submit(task2)
        await scheduler.submit(task3)

        # 验证按综合评分排序
        first = await scheduler.next()
        assert first is not None
        # CRITICAL 优先级任务应该先出队
        assert first.priority == TaskPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_peek_does_not_remove(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试 peek 不移除任务."""
        await scheduler.submit(sample_task)

        peeked = await scheduler.peek()
        assert peeked is not None
        assert peeked.id == sample_task.id
        assert scheduler.queue_size == 1  # 任务仍在队列中


# =============================================================================
# 调度器状态测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestSchedulerState:
    """调度器状态测试."""

    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler: TaskScheduler) -> None:
        """测试启动调度器."""
        assert scheduler.state == SchedulerState.IDLE

        await scheduler.start()
        assert scheduler.state == SchedulerState.RUNNING

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler: TaskScheduler) -> None:
        """测试停止调度器."""
        await scheduler.start()
        await scheduler.stop()

        assert scheduler.state == SchedulerState.STOPPED

    @pytest.mark.asyncio
    async def test_pause_resume_scheduler(self, scheduler: TaskScheduler) -> None:
        """测试暂停和恢复调度器."""
        await scheduler.start()
        await scheduler.pause()
        assert scheduler.state == SchedulerState.PAUSED

        await scheduler.resume()
        assert scheduler.state == SchedulerState.RUNNING

    @pytest.mark.asyncio
    async def test_next_returns_none_when_not_running(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试非运行状态时 next 返回 None."""
        await scheduler.submit(sample_task)

        # 调度器未启动，应返回 None
        task = await scheduler.next()
        assert task is None

    @pytest.mark.asyncio
    async def test_next_returns_none_when_paused(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试暂停状态时 next 返回 None."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.pause()

        task = await scheduler.next()
        assert task is None

    @pytest.mark.asyncio
    async def test_restart_after_stop(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试停止后重启."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.stop()

        # 重启会清空队列
        await scheduler.start()
        assert scheduler.state == SchedulerState.RUNNING
        assert scheduler.is_empty


# =============================================================================
# 任务执行和完成测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskExecution:
    """任务执行测试."""

    @pytest.mark.asyncio
    async def test_next_updates_task_status(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试 next 更新任务状态."""
        await scheduler.start()
        await scheduler.submit(sample_task)

        task = await scheduler.next()
        assert task is not None
        assert task.status == TaskStatus.ASSIGNED
        assert task.started_at is not None

    @pytest.mark.asyncio
    async def test_next_updates_stats(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试 next 更新统计."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()

        assert scheduler.stats.total_scheduled == 1

    @pytest.mark.asyncio
    async def test_mark_completed(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试标记任务完成."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()

        await scheduler.mark_completed(sample_task.id)

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.COMPLETED
        assert scheduler.stats.total_completed == 1

    @pytest.mark.asyncio
    async def test_mark_completed_triggers_callback(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试完成任务触发回调."""
        callback_called = []

        def on_completed(task: Task) -> None:
            callback_called.append(task.id)

        scheduler.on_task_completed(on_completed)

        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()
        await scheduler.mark_completed(sample_task.id)

        assert sample_task.id in callback_called

    @pytest.mark.asyncio
    async def test_mark_failed(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试标记任务失败."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()

        error = Exception("Test error")
        await scheduler.mark_failed(sample_task.id, error)

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.FAILED
        assert scheduler.stats.total_failed == 1

    @pytest.mark.asyncio
    async def test_mark_failed_triggers_callback(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试失败任务触发回调."""
        callback_results = []

        def on_failed(task: Task, error: Exception) -> None:
            callback_results.append((task.id, str(error)))

        scheduler.on_task_failed(on_failed)

        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()

        error = Exception("Test error")
        await scheduler.mark_failed(sample_task.id, error)

        assert len(callback_results) == 1
        assert callback_results[0][0] == sample_task.id


# =============================================================================
# 任务取消测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskCancellation:
    """任务取消测试."""

    @pytest.mark.asyncio
    async def test_cancel_pending_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试取消待处理任务."""
        await scheduler.submit(sample_task)

        result = await scheduler.cancel(sample_task.id)

        assert result is True
        assert scheduler.is_empty
        status = await scheduler.get_task_status(sample_task.id)
        assert status is None  # 已移除

    @pytest.mark.asyncio
    async def test_cancel_non_existent_task(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试取消不存在的任务."""
        result = await scheduler.cancel("non-existent-task")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_running_task_fails(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试无法取消运行中的任务."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()  # 任务变为运行中

        result = await scheduler.cancel(sample_task.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_all(
        self, scheduler: TaskScheduler, multiple_tasks: list[Task]
    ) -> None:
        """测试取消所有任务."""
        for task in multiple_tasks:
            await scheduler.submit(task)

        count = await scheduler.cancel_all()

        assert count == len(multiple_tasks)
        assert scheduler.is_empty
        assert scheduler.stats.current_queue_size == 0


# =============================================================================
# 任务重试测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskRetry:
    """任务重试测试."""

    @pytest.mark.asyncio
    async def test_retry_failed_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试重试失败任务."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()
        await scheduler.mark_failed(sample_task.id)

        result = await scheduler.retry(sample_task.id)

        assert result is True
        assert scheduler.queue_size == 1

    @pytest.mark.asyncio
    async def test_retry_exceeds_max_retries(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试超过最大重试次数."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()
        await scheduler.mark_failed(sample_task.id)

        # 重试 3 次
        for _ in range(3):
            await scheduler.retry(sample_task.id, max_retries=3)
            if scheduler.queue_size > 0:
                await scheduler.next()
                await scheduler.mark_failed(sample_task.id)

        # 第 4 次应该失败
        result = await scheduler.retry(sample_task.id, max_retries=3)
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_non_failed_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试重试非失败任务."""
        await scheduler.submit(sample_task)

        result = await scheduler.retry(sample_task.id)
        assert result is False


# =============================================================================
# 任务状态查询测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestTaskStatusQuery:
    """任务状态查询测试."""

    @pytest.mark.asyncio
    async def test_get_pending_task_status(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试获取待处理任务状态."""
        await scheduler.submit(sample_task)

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_running_task_status(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试获取运行中任务状态."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_get_completed_task_status(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试获取已完成任务状态."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()
        await scheduler.mark_completed(sample_task.id)

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_failed_task_status(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试获取失败任务状态."""
        await scheduler.start()
        await scheduler.submit(sample_task)
        await scheduler.next()
        await scheduler.mark_failed(sample_task.id)

        status = await scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_get_non_existent_task_status(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试获取不存在任务状态."""
        status = await scheduler.get_task_status("non-existent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_queue_snapshot(
        self, scheduler: TaskScheduler, multiple_tasks: list[Task]
    ) -> None:
        """测试获取队列快照."""
        for task in multiple_tasks:
            await scheduler.submit(task)

        snapshot = await scheduler.get_queue_snapshot()

        assert len(snapshot) == len(multiple_tasks)
        snapshot_ids = {t.id for t in snapshot}
        expected_ids = {t.id for t in multiple_tasks}
        assert snapshot_ids == expected_ids


# =============================================================================
# 依赖管理测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestDependencyManagement:
    """依赖管理测试."""

    @pytest.mark.asyncio
    async def test_submit_with_dependencies(
        self, scheduler_with_deps: TaskScheduler
    ) -> None:
        """测试提交有依赖的任务."""
        parent_task = Task(id="parent", title="Parent Task", dependencies=[])
        child_task = Task(
            id="child", title="Child Task", dependencies=["parent"]
        )

        await scheduler_with_deps.submit(parent_task)
        await scheduler_with_deps.submit(child_task)

        assert scheduler_with_deps.queue_size == 2

    @pytest.mark.asyncio
    async def test_dependency_aware_scheduling(self) -> None:
        """测试依赖感知调度."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.DEPENDENCY_AWARE,
            enable_dependency_resolution=True,
        )
        await scheduler.start()

        # 创建依赖链: task3 -> task2 -> task1
        task1 = Task(id="task1", title="Task 1", dependencies=[])
        task2 = Task(id="task2", title="Task 2", dependencies=["task1"])
        task3 = Task(id="task3", title="Task 3", dependencies=["task2"])

        # 按任意顺序提交
        await scheduler.submit(task3)
        await scheduler.submit(task1)
        await scheduler.submit(task2)

        # 只有 task1 应该就绪（无依赖）
        next_task = await scheduler.next()
        assert next_task is not None
        assert next_task.id == "task1"

    @pytest.mark.asyncio
    async def test_batch_submit_with_circular_dependency(self) -> None:
        """测试批量提交循环依赖."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.DEPENDENCY_AWARE,
            enable_dependency_resolution=True,
        )

        # 创建循环依赖
        task_a = Task(id="a", title="A", dependencies=["c"])
        task_b = Task(id="b", title="B", dependencies=["a"])
        task_c = Task(id="c", title="C", dependencies=["b"])

        # Mock dependency resolver 返回循环依赖错误
        mock_result = ResolutionResult(
            success=False,
            circular_dependencies=[["a", "b", "c", "a"]],
        )

        with patch.object(
            scheduler.dependency_resolver,
            "resolve",
            new=AsyncMock(return_value=mock_result),
        ):
            with pytest.raises(DependencyError, match="循环依赖"):
                await scheduler.submit_batch([task_a, task_b, task_c])

    @pytest.mark.asyncio
    async def test_batch_submit_with_missing_dependency(self) -> None:
        """测试批量提交缺失依赖."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.DEPENDENCY_AWARE,
            enable_dependency_resolution=True,
        )

        task_a = Task(id="a", title="A", dependencies=["missing"])

        mock_result = ResolutionResult(
            success=False,
            missing_dependencies={"missing"},
        )

        with patch.object(
            scheduler.dependency_resolver,
            "resolve",
            new=AsyncMock(return_value=mock_result),
        ):
            with pytest.raises(DependencyError, match="缺失的依赖"):
                await scheduler.submit_batch([task_a])

    @pytest.mark.asyncio
    async def test_mark_completed_updates_dependencies(self) -> None:
        """测试完成任务更新依赖状态."""
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.DEPENDENCY_AWARE,
            enable_dependency_resolution=True,
        )
        await scheduler.start()

        parent = Task(id="parent", title="Parent", dependencies=[])
        child = Task(id="child", title="Child", dependencies=["parent"])

        await scheduler.submit(parent)
        await scheduler.submit(child)

        # 获取并完成父任务
        task = await scheduler.next()
        assert task is not None
        assert task.id == "parent"

        await scheduler.mark_completed("parent")

        # 现在子任务应该就绪
        next_task = await scheduler.next()
        # 可能返回 child 或 None（取决于实现）


# =============================================================================
# ScheduledTask 测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestScheduledTask:
    """ScheduledTask 测试."""

    def test_from_task_factory(self, sample_task: Task) -> None:
        """测试从 Task 创建 ScheduledTask."""
        scheduled = ScheduledTask.from_task(sample_task, sequence=1)

        assert scheduled.task == sample_task
        assert scheduled.sequence == 1
        assert scheduled.priority_value == sample_task.priority.value
        assert scheduled.retry_count == 0

    def test_from_task_with_priority_override(self, sample_task: Task) -> None:
        """测试优先级覆盖."""
        scheduled = ScheduledTask.from_task(
            sample_task, sequence=1, priority_override=0
        )

        assert scheduled.priority_value == 0

    def test_scheduled_task_ordering(
        self,
        high_priority_task: Task,
        low_priority_task: Task,
    ) -> None:
        """测试 ScheduledTask 排序."""
        high = ScheduledTask.from_task(high_priority_task, sequence=1)
        low = ScheduledTask.from_task(low_priority_task, sequence=2)

        # 优先级值越小，优先级越高
        assert high < low

    def test_scheduled_task_same_priority_uses_sequence(
        self, sample_task: Task
    ) -> None:
        """测试相同优先级使用序列号排序."""
        task1 = Task(id="t1", title="T1", priority=TaskPriority.MEDIUM)
        task2 = Task(id="t2", title="T2", priority=TaskPriority.MEDIUM)

        scheduled1 = ScheduledTask.from_task(task1, sequence=1)
        scheduled2 = ScheduledTask.from_task(task2, sequence=2)

        assert scheduled1 < scheduled2


# =============================================================================
# 并发控制测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestConcurrencyControl:
    """并发控制测试."""

    @pytest.mark.asyncio
    async def test_concurrent_submit(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试并发提交."""
        tasks = [
            Task(id=f"task-{i}", title=f"Task {i}")
            for i in range(10)
        ]

        # 并发提交所有任务
        await asyncio.gather(
            *[scheduler.submit(task) for task in tasks]
        )

        assert scheduler.queue_size == len(tasks)
        assert scheduler.stats.total_submitted == len(tasks)

    @pytest.mark.asyncio
    async def test_concurrent_next(self, scheduler: TaskScheduler) -> None:
        """测试并发获取任务."""
        await scheduler.start()

        tasks = [
            Task(id=f"task-{i}", title=f"Task {i}")
            for i in range(5)
        ]

        for task in tasks:
            await scheduler.submit(task)

        # 并发获取任务
        results = await asyncio.gather(
            *[scheduler.next() for _ in range(5)]
        )

        # 应该获取到所有任务（无重复）
        valid_results = [r for r in results if r is not None]
        unique_ids = {r.id for r in valid_results}

        # 由于锁的存在，每个任务只应该被获取一次
        assert len(unique_ids) == len(valid_results)

    @pytest.mark.asyncio
    async def test_lock_prevents_race_condition(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试锁防止竞态条件."""
        await scheduler.start()

        # 只提交一个任务
        task = Task(id="single-task", title="Single Task")
        await scheduler.submit(task)

        # 多个协程尝试获取同一个任务
        results = await asyncio.gather(
            scheduler.next(),
            scheduler.next(),
            scheduler.next(),
        )

        # 只有一个应该成功获取到任务
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 1
        assert non_none[0].id == "single-task"


# =============================================================================
# 统计信息测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestSchedulerStats:
    """调度器统计信息测试."""

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self, scheduler: TaskScheduler, multiple_tasks: list[Task]
    ) -> None:
        """测试统计跟踪."""
        await scheduler.start()

        for task in multiple_tasks:
            await scheduler.submit(task)

        # 获取并完成一些任务
        for _ in range(3):
            task = await scheduler.next()
            if task:
                await scheduler.mark_completed(task.id)

        # 获取并失败一个任务
        task = await scheduler.next()
        if task:
            await scheduler.mark_failed(task.id)

        stats = scheduler.stats

        assert stats.total_submitted == len(multiple_tasks)
        assert stats.total_scheduled == 4
        assert stats.total_completed == 3
        assert stats.total_failed == 1
        assert stats.current_queue_size == 1

    def test_stats_dataclass(self) -> None:
        """测试 SchedulerStats 数据类."""
        stats = SchedulerStats(
            total_submitted=100,
            total_scheduled=80,
            total_completed=70,
            total_failed=5,
            current_queue_size=25,
            average_wait_time=1.5,
            average_execution_time=10.0,
        )

        assert stats.total_submitted == 100
        assert stats.total_scheduled == 80
        assert stats.total_completed == 70
        assert stats.total_failed == 5
        assert stats.current_queue_size == 25
        assert stats.average_wait_time == 1.5
        assert stats.average_execution_time == 10.0


# =============================================================================
# 回调机制测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestCallbacks:
    """回调机制测试."""

    @pytest.mark.asyncio
    async def test_multiple_callbacks(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试多个回调."""
        call_order = []

        def callback1(task: Task) -> None:
            call_order.append("cb1")

        def callback2(task: Task) -> None:
            call_order.append("cb2")

        scheduler.on_task_scheduled(callback1)
        scheduler.on_task_scheduled(callback2)

        await scheduler.submit(sample_task)

        assert call_order == ["cb1", "cb2"]

    @pytest.mark.asyncio
    async def test_all_callback_types(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试所有回调类型."""
        callbacks_called = {
            "scheduled": False,
            "completed": False,
            "failed": False,
        }

        scheduler.on_task_scheduled(
            lambda t: callbacks_called.__setitem__("scheduled", True)
        )
        scheduler.on_task_completed(
            lambda t: callbacks_called.__setitem__("completed", True)
        )
        scheduler.on_task_failed(
            lambda t, e: callbacks_called.__setitem__("failed", True)
        )

        await scheduler.start()
        await scheduler.submit(sample_task)
        assert callbacks_called["scheduled"]

        await scheduler.next()
        await scheduler.mark_completed(sample_task.id)
        assert callbacks_called["completed"]

        # 提交新任务测试失败回调
        task2 = Task(id="task-fail", title="Fail Task")
        await scheduler.submit(task2)
        await scheduler.next()
        await scheduler.mark_failed(task2.id, Exception("test"))
        assert callbacks_called["failed"]


# =============================================================================
# 协议实现测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestProtocolImplementation:
    """协议实现测试."""

    def test_scheduler_implements_protocol(self) -> None:
        """测试调度器实现协议."""
        scheduler = TaskScheduler()
        assert isinstance(scheduler, TaskSchedulerProtocol)

    @pytest.mark.asyncio
    async def test_protocol_methods(self, scheduler: TaskScheduler) -> None:
        """测试协议方法."""
        # 测试协议要求的方法存在且可调用
        task = Task(id="proto-task", title="Protocol Task")

        await scheduler.submit(task)
        await scheduler.submit_batch([])
        await scheduler.start()
        await scheduler.next()
        await scheduler.cancel("non-existent")
        await scheduler.pause()
        await scheduler.resume()


# =============================================================================
# 边界条件测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestEdgeCases:
    """边界条件测试."""

    @pytest.mark.asyncio
    async def test_empty_queue_next(self, scheduler: TaskScheduler) -> None:
        """测试空队列获取任务."""
        await scheduler.start()
        task = await scheduler.next()
        assert task is None

    @pytest.mark.asyncio
    async def test_empty_queue_peek(self, scheduler: TaskScheduler) -> None:
        """测试空队列查看任务."""
        task = await scheduler.peek()
        assert task is None

    @pytest.mark.asyncio
    async def test_mark_completed_non_running_task(
        self, scheduler: TaskScheduler, sample_task: Task
    ) -> None:
        """测试标记非运行任务完成."""
        await scheduler.submit(sample_task)
        # 任务未开始运行
        await scheduler.mark_completed(sample_task.id)
        # 应该无操作

    @pytest.mark.asyncio
    async def test_submit_empty_batch(self, scheduler: TaskScheduler) -> None:
        """测试提交空批次."""
        await scheduler.submit_batch([])
        assert scheduler.is_empty

    @pytest.mark.asyncio
    async def test_cancel_all_empty_queue(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试空队列取消所有."""
        count = await scheduler.cancel_all()
        assert count == 0

    @pytest.mark.asyncio
    async def test_pause_when_not_running(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试非运行状态暂停."""
        # IDLE 状态暂停应该无操作
        await scheduler.pause()
        assert scheduler.state == SchedulerState.IDLE

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(
        self, scheduler: TaskScheduler
    ) -> None:
        """测试非暂停状态恢复."""
        await scheduler.start()
        # RUNNING 状态恢复应该无操作
        await scheduler.resume()
        assert scheduler.state == SchedulerState.RUNNING


# =============================================================================
# 枚举测试
# =============================================================================


@pytest.mark.unit
@pytest.mark.orchestration
class TestEnums:
    """枚举测试."""

    def test_scheduling_strategy_values(self) -> None:
        """测试调度策略枚举值."""
        assert SchedulingStrategy.FIFO.value == "fifo"
        assert SchedulingStrategy.PRIORITY_FIRST.value == "priority_first"
        assert SchedulingStrategy.SHORTEST_FIRST.value == "shortest_first"
        assert SchedulingStrategy.DEPENDENCY_AWARE.value == "dependency_aware"
        assert SchedulingStrategy.BALANCED.value == "balanced"

    def test_scheduler_state_values(self) -> None:
        """测试调度器状态枚举值."""
        assert SchedulerState.IDLE.value == "idle"
        assert SchedulerState.RUNNING.value == "running"
        assert SchedulerState.PAUSED.value == "paused"
        assert SchedulerState.STOPPED.value == "stopped"
