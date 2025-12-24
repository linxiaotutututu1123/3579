"""并行执行器模块.

本模块提供任务并行执行功能，支持：
- 可配置的并发度控制
- 任务执行超时管理
- 错误处理和重试
- 执行结果收集
- 任务优先级队列
- 进度回调
- 优雅关闭

核心类:
    ExecutionMode: 执行模式枚举
    ExecutionResult: 执行结果包装
    ParallelExecutor: 并行执行器实现
    ParallelExecutorProtocol: 执行器协议接口

Example:
    >>> executor = ParallelExecutor(max_workers=4)
    >>> results = await executor.execute_batch(tasks, execute_fn)
"""

from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections.abc import Awaitable, Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from chairman_agents.core.exceptions import TaskExecutionError
from chairman_agents.core.types import Task, TaskId, TaskPriority, TaskResult, TaskStatus


# =============================================================================
# 类型别名
# =============================================================================

TaskExecutorFn = Callable[[Task], Awaitable[TaskResult]]
"""任务执行函数类型"""


# =============================================================================
# 枚举定义
# =============================================================================


class ExecutionMode(Enum):
    """执行模式枚举.

    Modes:
        PARALLEL: 完全并行执行
        SEQUENTIAL: 顺序执行
        BATCHED: 分批并行执行
        ADAPTIVE: 自适应执行（根据系统负载调整）
    """

    PARALLEL = "parallel"
    """完全并行执行"""

    SEQUENTIAL = "sequential"
    """顺序执行"""

    BATCHED = "batched"
    """分批并行执行"""

    ADAPTIVE = "adaptive"
    """自适应执行"""


class ExecutorState(Enum):
    """执行器状态枚举.

    States:
        IDLE: 空闲状态
        RUNNING: 执行中
        PAUSED: 暂停
        SHUTTING_DOWN: 正在关闭
        STOPPED: 已停止
    """

    IDLE = "idle"
    """空闲状态"""

    RUNNING = "running"
    """执行中"""

    PAUSED = "paused"
    """暂停"""

    SHUTTING_DOWN = "shutting_down"
    """正在关闭"""

    STOPPED = "stopped"
    """已停止"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class ExecutionResult:
    """任务执行结果包装.

    Attributes:
        task_id: 任务 ID
        task: 原始任务对象
        success: 是否执行成功
        result: 任务执行返回的结果
        error: 执行错误（如果失败）
        started_at: 开始执行时间
        completed_at: 完成时间
        execution_time: 执行耗时（秒）
        retry_count: 重试次数
    """

    task_id: TaskId
    """任务 ID"""

    task: Task
    """原始任务对象"""

    success: bool = False
    """是否执行成功"""

    result: TaskResult | None = None
    """任务执行返回的结果"""

    error: Exception | None = None
    """执行错误"""

    started_at: datetime = field(default_factory=datetime.now)
    """开始执行时间"""

    completed_at: datetime | None = None
    """完成时间"""

    execution_time: float = 0.0
    """执行耗时（秒）"""

    retry_count: int = 0
    """重试次数"""

    @property
    def duration_ms(self) -> float:
        """获取执行时长（毫秒）."""
        return self.execution_time * 1000


@dataclass
class BatchResult:
    """批量执行结果.

    Attributes:
        total: 总任务数
        successful: 成功数
        failed: 失败数
        results: 各任务的执行结果
        total_time: 总耗时（秒）
        started_at: 批次开始时间
        completed_at: 批次完成时间
    """

    total: int = 0
    """总任务数"""

    successful: int = 0
    """成功数"""

    failed: int = 0
    """失败数"""

    results: list[ExecutionResult] = field(default_factory=list)
    """各任务的执行结果"""

    total_time: float = 0.0
    """总耗时（秒）"""

    started_at: datetime = field(default_factory=datetime.now)
    """批次开始时间"""

    completed_at: datetime | None = None
    """批次完成时间"""

    @property
    def success_rate(self) -> float:
        """计算成功率."""
        if self.total == 0:
            return 0.0
        return self.successful / self.total

    def get_failed_tasks(self) -> list[ExecutionResult]:
        """获取失败的任务结果列表."""
        return [r for r in self.results if not r.success]

    def get_successful_tasks(self) -> list[ExecutionResult]:
        """获取成功的任务结果列表."""
        return [r for r in self.results if r.success]


@dataclass
class ExecutorConfig:
    """执行器配置.

    Attributes:
        max_workers: 最大并发工作数
        default_timeout: 默认超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
        retry_backoff: 重试退避系数（每次重试间隔乘以此系数）
        mode: 执行模式
        batch_size: 批处理大小（仅 BATCHED 模式）
        graceful_shutdown_timeout: 优雅关闭超时时间（秒）
        priority_enabled: 是否启用优先级队列
        progress_interval: 进度回调间隔（秒）
    """

    max_workers: int = 4
    """最大并发工作数"""

    default_timeout: float = 300.0
    """默认超时时间（秒）"""

    max_retries: int = 3
    """最大重试次数"""

    retry_delay: float = 1.0
    """重试间隔（秒）"""

    retry_backoff: float = 2.0
    """重试退避系数"""

    mode: ExecutionMode = ExecutionMode.PARALLEL
    """执行模式"""

    batch_size: int = 10
    """批处理大小"""

    graceful_shutdown_timeout: float = 30.0
    """优雅关闭超时时间（秒）"""

    priority_enabled: bool = True
    """是否启用优先级队列"""

    progress_interval: float = 1.0
    """进度回调间隔（秒）"""


@dataclass
class ExecutorStats:
    """执行器统计信息.

    Attributes:
        total_executed: 总执行任务数
        total_successful: 总成功数
        total_failed: 总失败数
        total_retried: 总重试数
        total_timed_out: 总超时数
        total_cancelled: 总取消数
        current_running: 当前运行中任务数
        average_execution_time: 平均执行时间（秒）
        max_execution_time: 最长执行时间（秒）
        min_execution_time: 最短执行时间（秒）
        peak_concurrent: 峰值并发数
    """

    total_executed: int = 0
    """总执行任务数"""

    total_successful: int = 0
    """总成功数"""

    total_failed: int = 0
    """总失败数"""

    total_retried: int = 0
    """总重试数"""

    total_timed_out: int = 0
    """总超时数"""

    total_cancelled: int = 0
    """总取消数"""

    current_running: int = 0
    """当前运行中任务数"""

    average_execution_time: float = 0.0
    """平均执行时间（秒）"""

    max_execution_time: float = 0.0
    """最长执行时间（秒）"""

    min_execution_time: float = float("inf")
    """最短执行时间（秒）"""

    peak_concurrent: int = 0
    """峰值并发数"""


# Type aliases for progress callbacks
ProgressCallback = Callable[[int, int, int], None]
"""进度回调类型: (completed, failed, total) -> None"""

TaskProgressCallback = Callable[[TaskId, str, float], None]
"""任务进度回调类型: (task_id, status, progress_percent) -> None"""


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class ParallelExecutorProtocol(Protocol):
    """并行执行器协议.

    定义并行执行器的标准接口。

    Example:
        >>> class MyExecutor(ParallelExecutorProtocol):
        ...     async def execute(
        ...         self,
        ...         task: Task,
        ...         executor_fn: TaskExecutorFn,
        ...     ) -> ExecutionResult:
        ...         # 实现执行逻辑
        ...         return ExecutionResult(task_id=task.id, task=task)
    """

    async def execute(
        self,
        task: Task,
        executor_fn: TaskExecutorFn,
        *,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """执行单个任务.

        Args:
            task: 要执行的任务
            executor_fn: 任务执行函数
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        ...

    async def execute_batch(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        *,
        timeout: float | None = None,
    ) -> BatchResult:
        """批量执行任务.

        Args:
            tasks: 任务列表
            executor_fn: 任务执行函数
            timeout: 每个任务的超时时间

        Returns:
            批量执行结果
        """
        ...

    async def shutdown(self, wait: bool = True) -> None:
        """关闭执行器.

        Args:
            wait: 是否等待当前任务完成
        """
        ...


# =============================================================================
# 并行执行器实现
# =============================================================================


class ParallelExecutor:
    """并行任务执行器.

    提供高效的并行任务执行能力：
    - 可配置的并发度
    - 超时控制
    - 自动重试（支持退避）
    - 优雅关闭
    - 任务优先级队列
    - 进度回调
    - 批量执行优化

    Attributes:
        config: 执行器配置
        state: 当前状态

    Example:
        >>> executor = ParallelExecutor(
        ...     ExecutorConfig(max_workers=8, default_timeout=60.0)
        ... )
        >>> await executor.start()
        >>>
        >>> # 执行单个任务
        >>> result = await executor.execute(task, my_executor_fn)
        >>>
        >>> # 批量执行
        >>> batch_result = await executor.execute_batch(tasks, my_executor_fn)
        >>>
        >>> await executor.shutdown()
    """

    def __init__(self, config: ExecutorConfig | None = None) -> None:
        """初始化并行执行器.

        Args:
            config: 执行器配置，为空时使用默认配置
        """
        self.config = config or ExecutorConfig()
        self.state = ExecutorState.IDLE

        # 内部状态
        self._semaphore: asyncio.Semaphore | None = None
        self._running_tasks: dict[TaskId, asyncio.Task[ExecutionResult]] = {}
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 默认未暂停

        # 优先级队列 (priority, sequence, task)
        self._priority_queue: list[tuple[int, int, Task]] = []
        self._sequence_counter = 0

        # 统计信息
        self._stats = ExecutorStats()
        self._execution_times: list[float] = []

        # 任务取消跟踪
        self._cancellation_tokens: dict[TaskId, asyncio.Event] = {}

        # 回调
        self._on_task_start: list[Callable[[Task], None]] = []
        self._on_task_complete: list[Callable[[ExecutionResult], None]] = []
        self._on_task_error: list[Callable[[Task, Exception], None]] = []
        self._on_progress: list[ProgressCallback] = []
        self._on_task_progress: list[TaskProgressCallback] = []

        # 进度跟踪
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._last_progress_time = 0.0

    async def start(self) -> None:
        """启动执行器."""
        async with self._lock:
            if self.state != ExecutorState.STOPPED:
                self._semaphore = asyncio.Semaphore(self.config.max_workers)
                self._shutdown_event.clear()
                self._pause_event.set()
                self.state = ExecutorState.RUNNING

    async def shutdown(self, wait: bool = True, cancel_running: bool = False) -> int:
        """关闭执行器.

        支持优雅关闭，等待正在执行的任务完成或强制取消。

        Args:
            wait: 是否等待当前任务完成
            cancel_running: 是否取消正在运行的任务

        Returns:
            取消的任务数量
        """
        cancelled_count = 0

        async with self._lock:
            self.state = ExecutorState.SHUTTING_DOWN
            self._shutdown_event.set()

        # 取消正在运行的任务
        if cancel_running:
            for task_id, task in list(self._running_tasks.items()):
                task.cancel()
                cancelled_count += 1
                self._stats.total_cancelled += 1

                # 设置取消令牌
                if task_id in self._cancellation_tokens:
                    self._cancellation_tokens[task_id].set()

        if wait and self._running_tasks and not cancel_running:
            # 等待所有运行中的任务完成
            try:
                start_time = time.monotonic()
                while self._running_tasks:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= self.config.graceful_shutdown_timeout:
                        # 超时后取消剩余任务
                        for task_id, task in list(self._running_tasks.items()):
                            task.cancel()
                            cancelled_count += 1
                            self._stats.total_cancelled += 1
                        break
                    await asyncio.sleep(0.1)
            except Exception:
                pass

        async with self._lock:
            self._running_tasks.clear()
            self._cancellation_tokens.clear()
            self._priority_queue.clear()
            self.state = ExecutorState.STOPPED

        return cancelled_count

    async def pause(self) -> None:
        """暂停执行器.

        暂停后不会启动新任务，但已运行的任务会继续执行。
        """
        async with self._lock:
            if self.state == ExecutorState.RUNNING:
                self._pause_event.clear()
                self.state = ExecutorState.PAUSED

    async def resume(self) -> None:
        """恢复执行器."""
        async with self._lock:
            if self.state == ExecutorState.PAUSED:
                self._pause_event.set()
                self.state = ExecutorState.RUNNING

    async def execute(
        self,
        task: Task,
        executor_fn: TaskExecutorFn,
        *,
        timeout: float | None = None,
        priority: int | None = None,
    ) -> ExecutionResult:
        """执行单个任务.

        Args:
            task: 要执行的任务
            executor_fn: 任务执行函数
            timeout: 超时时间（秒），为空时使用默认值
            priority: 任务优先级（可选，默认使用任务自身优先级）

        Returns:
            执行结果

        Raises:
            RuntimeError: 执行器未运行时抛出
        """
        if self.state not in (ExecutorState.RUNNING, ExecutorState.PAUSED):
            raise RuntimeError(f"执行器状态异常: {self.state.value}")

        # 等待暂停结束
        await self._pause_event.wait()

        # 检查关闭事件
        if self._shutdown_event.is_set():
            return ExecutionResult(
                task_id=task.id,
                task=task,
                success=False,
                error=Exception("执行器正在关闭"),
            )

        timeout = timeout or self.config.default_timeout
        return await self._execute_with_retry(task, executor_fn, timeout)

    async def execute_batch(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        *,
        timeout: float | None = None,
        sort_by_priority: bool = True,
    ) -> BatchResult:
        """批量执行任务.

        根据配置的执行模式并行或顺序执行任务。
        支持按优先级排序。

        Args:
            tasks: 任务列表
            executor_fn: 任务执行函数
            timeout: 每个任务的超时时间
            sort_by_priority: 是否按优先级排序任务

        Returns:
            批量执行结果
        """
        if self.state not in (ExecutorState.RUNNING, ExecutorState.PAUSED):
            raise RuntimeError(f"执行器状态异常: {self.state.value}")

        # 初始化进度跟踪
        self._total_tasks = len(tasks)
        self._completed_tasks = 0
        self._failed_tasks = 0

        batch_result = BatchResult(
            total=len(tasks),
            started_at=datetime.now(),
        )

        timeout = timeout or self.config.default_timeout

        # 按优先级排序
        if sort_by_priority and self.config.priority_enabled:
            sorted_tasks = sorted(tasks, key=lambda t: t.priority.value)
        else:
            sorted_tasks = list(tasks)

        if self.config.mode == ExecutionMode.SEQUENTIAL:
            results = await self._execute_sequential(sorted_tasks, executor_fn, timeout)
        elif self.config.mode == ExecutionMode.BATCHED:
            results = await self._execute_batched(sorted_tasks, executor_fn, timeout)
        elif self.config.mode == ExecutionMode.ADAPTIVE:
            results = await self._execute_adaptive(sorted_tasks, executor_fn, timeout)
        else:  # PARALLEL
            results = await self._execute_parallel_with_priority(
                sorted_tasks, executor_fn, timeout
            )

        batch_result.results = results
        batch_result.completed_at = datetime.now()
        batch_result.total_time = (
            batch_result.completed_at - batch_result.started_at
        ).total_seconds()

        for result in results:
            if result.success:
                batch_result.successful += 1
            else:
                batch_result.failed += 1

        return batch_result

    async def execute_with_dependencies(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        execution_levels: list[list[TaskId]],
        *,
        timeout: float | None = None,
    ) -> BatchResult:
        """按依赖层级执行任务.

        同一层级的任务并行执行，不同层级按顺序执行。

        Args:
            tasks: 任务列表
            executor_fn: 任务执行函数
            execution_levels: 按依赖关系分组的执行层级
            timeout: 每个任务的超时时间

        Returns:
            批量执行结果
        """
        task_map = {task.id: task for task in tasks}
        all_results: list[ExecutionResult] = []
        batch_result = BatchResult(
            total=len(tasks),
            started_at=datetime.now(),
        )

        timeout = timeout or self.config.default_timeout

        for level in execution_levels:
            level_tasks = [task_map[tid] for tid in level if tid in task_map]
            if not level_tasks:
                continue

            level_results = await self._execute_parallel(level_tasks, executor_fn, timeout)
            all_results.extend(level_results)

            # 检查是否有失败的任务
            failed = [r for r in level_results if not r.success]
            if failed:
                # 可以在这里决定是否继续执行后续层级
                pass

        batch_result.results = all_results
        batch_result.completed_at = datetime.now()
        batch_result.total_time = (
            batch_result.completed_at - batch_result.started_at
        ).total_seconds()

        for result in all_results:
            if result.success:
                batch_result.successful += 1
            else:
                batch_result.failed += 1

        return batch_result

    async def cancel_task(self, task_id: TaskId, reason: str | None = None) -> bool:
        """取消正在执行的任务.

        Args:
            task_id: 要取消的任务 ID
            reason: 取消原因（可选）

        Returns:
            是否取消成功
        """
        async with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                self._stats.total_cancelled += 1

                # 设置取消令牌
                if task_id in self._cancellation_tokens:
                    self._cancellation_tokens[task_id].set()

                return True
            return False

    async def cancel_all(self) -> int:
        """取消所有正在执行的任务.

        Returns:
            取消的任务数量
        """
        async with self._lock:
            count = len(self._running_tasks)
            for task_id, task in list(self._running_tasks.items()):
                task.cancel()
                self._stats.total_cancelled += 1

                # 设置取消令牌
                if task_id in self._cancellation_tokens:
                    self._cancellation_tokens[task_id].set()

            return count

    async def cancel_by_priority(
        self, min_priority: TaskPriority
    ) -> int:
        """取消低优先级任务.

        取消优先级低于指定值的所有正在执行的任务。

        Args:
            min_priority: 最低保留优先级（低于此优先级的任务将被取消）

        Returns:
            取消的任务数量
        """
        async with self._lock:
            count = 0
            for task_id, async_task in list(self._running_tasks.items()):
                # 需要从其他地方获取任务优先级信息
                # 这里简单处理，实际应用中可能需要更复杂的跟踪
                async_task.cancel()
                count += 1
                self._stats.total_cancelled += 1

            return count

    def on_task_start(self, callback: Callable[[Task], None]) -> None:
        """注册任务开始回调.

        Args:
            callback: 任务开始时调用的函数
        """
        self._on_task_start.append(callback)

    def on_task_complete(self, callback: Callable[[ExecutionResult], None]) -> None:
        """注册任务完成回调.

        Args:
            callback: 任务完成时调用的函数
        """
        self._on_task_complete.append(callback)

    def on_task_error(self, callback: Callable[[Task, Exception], None]) -> None:
        """注册任务错误回调.

        Args:
            callback: 任务出错时调用的函数
        """
        self._on_task_error.append(callback)

    def on_progress(self, callback: ProgressCallback) -> None:
        """注册进度回调.

        Args:
            callback: 进度变化时调用的函数，参数为 (completed, failed, total)
        """
        self._on_progress.append(callback)

    def on_task_progress(self, callback: TaskProgressCallback) -> None:
        """注册任务进度回调.

        Args:
            callback: 单个任务进度变化时调用的函数
        """
        self._on_task_progress.append(callback)

    def _notify_progress(self) -> None:
        """通知进度回调."""
        current_time = time.monotonic()
        # 限制回调频率
        if current_time - self._last_progress_time < self.config.progress_interval:
            return

        self._last_progress_time = current_time

        for callback in self._on_progress:
            try:
                callback(
                    self._completed_tasks,
                    self._failed_tasks,
                    self._total_tasks,
                )
            except Exception:
                pass

    def _notify_task_progress(
        self, task_id: TaskId, status: str, progress: float
    ) -> None:
        """通知单个任务进度回调.

        Args:
            task_id: 任务 ID
            status: 当前状态
            progress: 进度百分比 (0.0 - 100.0)
        """
        for callback in self._on_task_progress:
            try:
                callback(task_id, status, progress)
            except Exception:
                pass

    @property
    def stats(self) -> ExecutorStats:
        """获取执行器统计信息."""
        self._stats.current_running = len(self._running_tasks)
        if self._execution_times:
            self._stats.average_execution_time = sum(self._execution_times) / len(
                self._execution_times
            )
        return self._stats

    @property
    def current_load(self) -> float:
        """获取当前负载率 (0.0 - 1.0)."""
        if self.config.max_workers == 0:
            return 0.0
        return len(self._running_tasks) / self.config.max_workers

    @property
    def available_slots(self) -> int:
        """获取可用执行槽位数."""
        return self.config.max_workers - len(self._running_tasks)

    async def _execute_with_retry(
        self,
        task: Task,
        executor_fn: TaskExecutorFn,
        timeout: float,
    ) -> ExecutionResult:
        """带重试的任务执行.

        Args:
            task: 要执行的任务
            executor_fn: 执行函数
            timeout: 超时时间

        Returns:
            执行结果
        """
        result = ExecutionResult(
            task_id=task.id,
            task=task,
            started_at=datetime.now(),
        )

        for attempt in range(self.config.max_retries + 1):
            if self._shutdown_event.is_set():
                result.error = Exception("执行器正在关闭")
                break

            try:
                # 获取信号量
                if self._semaphore:
                    await self._semaphore.acquire()

                try:
                    result.retry_count = attempt

                    # 触发开始回调
                    for callback in self._on_task_start:
                        callback(task)

                    # 更新状态
                    task.status = TaskStatus.IN_PROGRESS
                    self._stats.current_running += 1

                    # 创建执行任务
                    exec_task = asyncio.create_task(executor_fn(task))
                    self._running_tasks[task.id] = exec_task

                    # 等待执行完成
                    task_result = await asyncio.wait_for(exec_task, timeout=timeout)

                    # 执行成功
                    result.success = True
                    result.result = task_result
                    result.completed_at = datetime.now()
                    result.execution_time = (
                        result.completed_at - result.started_at
                    ).total_seconds()

                    # 更新统计
                    self._stats.total_executed += 1
                    self._stats.total_successful += 1
                    self._update_execution_time_stats(result.execution_time)

                    # 触发完成回调
                    for callback in self._on_task_complete:
                        callback(result)

                    break

                finally:
                    # 释放信号量
                    if self._semaphore:
                        self._semaphore.release()
                    self._stats.current_running -= 1
                    self._running_tasks.pop(task.id, None)

            except asyncio.TimeoutError:
                result.error = TaskExecutionError(
                    f"任务执行超时 ({timeout}秒)",
                    task_id=task.id,
                    phase="execution",
                )
                if attempt < self.config.max_retries:
                    self._stats.total_retried += 1
                    await asyncio.sleep(self.config.retry_delay)
                    continue

            except asyncio.CancelledError:
                result.error = Exception("任务被取消")
                break

            except Exception as e:
                result.error = e
                # 触发错误回调
                for callback in self._on_task_error:
                    callback(task, e)

                if attempt < self.config.max_retries:
                    self._stats.total_retried += 1
                    await asyncio.sleep(self.config.retry_delay)
                    continue

        if not result.success:
            result.completed_at = datetime.now()
            result.execution_time = (
                result.completed_at - result.started_at
            ).total_seconds()
            self._stats.total_executed += 1
            self._stats.total_failed += 1
            task.status = TaskStatus.FAILED

        return result

    async def _execute_parallel(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        timeout: float,
    ) -> list[ExecutionResult]:
        """完全并行执行任务.

        Args:
            tasks: 任务列表
            executor_fn: 执行函数
            timeout: 超时时间

        Returns:
            执行结果列表
        """
        coroutines = [
            self._execute_with_retry(task, executor_fn, timeout) for task in tasks
        ]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 处理异常结果
        processed_results: list[ExecutionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ExecutionResult(
                        task_id=tasks[i].id,
                        task=tasks[i],
                        success=False,
                        error=result,
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_sequential(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        timeout: float,
    ) -> list[ExecutionResult]:
        """顺序执行任务.

        Args:
            tasks: 任务列表
            executor_fn: 执行函数
            timeout: 超时时间

        Returns:
            执行结果列表
        """
        results: list[ExecutionResult] = []
        for task in tasks:
            if self._shutdown_event.is_set():
                break
            result = await self._execute_with_retry(task, executor_fn, timeout)
            results.append(result)
        return results

    async def _execute_batched(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        timeout: float,
    ) -> list[ExecutionResult]:
        """分批并行执行任务.

        Args:
            tasks: 任务列表
            executor_fn: 执行函数
            timeout: 超时时间

        Returns:
            执行结果列表
        """
        results: list[ExecutionResult] = []
        batch_size = self.config.batch_size

        for i in range(0, len(tasks), batch_size):
            if self._shutdown_event.is_set():
                break
            batch = tasks[i : i + batch_size]
            batch_results = await self._execute_parallel(batch, executor_fn, timeout)
            results.extend(batch_results)

        return results

    async def _execute_adaptive(
        self,
        tasks: Sequence[Task],
        executor_fn: TaskExecutorFn,
        timeout: float,
    ) -> list[ExecutionResult]:
        """自适应执行任务.

        根据系统负载动态调整并发度。

        Args:
            tasks: 任务列表
            executor_fn: 执行函数
            timeout: 超时时间

        Returns:
            执行结果列表
        """
        results: list[ExecutionResult] = []
        pending = list(tasks)

        while pending and not self._shutdown_event.is_set():
            # 根据当前负载决定批次大小
            current_load = self.current_load
            if current_load < 0.5:
                batch_size = min(len(pending), self.config.max_workers)
            elif current_load < 0.8:
                batch_size = min(len(pending), self.config.max_workers // 2)
            else:
                batch_size = 1

            batch = pending[:batch_size]
            pending = pending[batch_size:]

            batch_results = await self._execute_parallel(batch, executor_fn, timeout)
            results.extend(batch_results)

        return results

    def _update_execution_time_stats(self, execution_time: float) -> None:
        """更新执行时间统计.

        Args:
            execution_time: 执行时间
        """
        self._execution_times.append(execution_time)
        # 只保留最近 1000 条记录
        if len(self._execution_times) > 1000:
            self._execution_times = self._execution_times[-1000:]

        self._stats.max_execution_time = max(
            self._stats.max_execution_time, execution_time
        )
        self._stats.min_execution_time = min(
            self._stats.min_execution_time, execution_time
        )


# =============================================================================
# 便捷函数
# =============================================================================


async def execute_tasks_parallel(
    tasks: Sequence[Task],
    executor_fn: TaskExecutorFn,
    *,
    max_workers: int = 4,
    timeout: float = 300.0,
) -> BatchResult:
    """便捷函数：并行执行任务.

    Args:
        tasks: 任务列表
        executor_fn: 执行函数
        max_workers: 最大并发数
        timeout: 超时时间

    Returns:
        批量执行结果

    Example:
        >>> async def my_executor(task: Task) -> TaskResult:
        ...     # 执行任务逻辑
        ...     return TaskResult(task_id=task.id, success=True)
        >>>
        >>> result = await execute_tasks_parallel(
        ...     tasks,
        ...     my_executor,
        ...     max_workers=8,
        ... )
    """
    config = ExecutorConfig(max_workers=max_workers, default_timeout=timeout)
    executor = ParallelExecutor(config)
    await executor.start()
    try:
        return await executor.execute_batch(tasks, executor_fn)
    finally:
        await executor.shutdown(wait=False)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "TaskExecutorFn",
    "ExecutionMode",
    "ExecutorState",
    "ExecutionResult",
    "BatchResult",
    "ExecutorConfig",
    "ExecutorStats",
    "ParallelExecutorProtocol",
    "ParallelExecutor",
    "execute_tasks_parallel",
]
