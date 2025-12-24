"""编排模块 - 任务调度、并行执行、依赖解析.

本模块提供任务编排功能，包括：
- 依赖解析器：分析和管理任务依赖关系
- 任务调度器：基于优先级和依赖的任务调度
- 并行执行器：高效的并行任务执行

核心组件:
    DependencyResolver: 依赖解析器
    TaskScheduler: 任务调度器
    ParallelExecutor: 并行执行器

Example:
    >>> from chairman_agents.orchestration import (
    ...     DependencyResolver,
    ...     TaskScheduler,
    ...     ParallelExecutor,
    ... )
    >>>
    >>> # 创建调度器和执行器
    >>> scheduler = TaskScheduler()
    >>> executor = ParallelExecutor()
    >>>
    >>> # 提交任务
    >>> await scheduler.submit_batch(tasks)
    >>>
    >>> # 执行任务
    >>> while not scheduler.is_empty:
    ...     task = await scheduler.next()
    ...     if task:
    ...         await executor.execute(task, my_executor_fn)
"""

from __future__ import annotations

from chairman_agents.orchestration.dependency_resolver import (
    DependencyGraph,
    DependencyNode,
    DependencyResolver,
    DependencyResolverProtocol,
    DependencyState,
    ResolutionResult,
)
from chairman_agents.orchestration.parallel_executor import (
    BatchResult,
    ExecutionMode,
    ExecutionResult,
    ExecutorConfig,
    ExecutorState,
    ExecutorStats,
    ParallelExecutor,
    ParallelExecutorProtocol,
    TaskExecutorFn,
    execute_tasks_parallel,
)
from chairman_agents.orchestration.task_scheduler import (
    ScheduledTask,
    SchedulerState,
    SchedulerStats,
    SchedulingStrategy,
    TaskScheduler,
    TaskSchedulerProtocol,
)

__all__ = [
    # 依赖解析器
    "DependencyState",
    "DependencyNode",
    "DependencyGraph",
    "ResolutionResult",
    "DependencyResolverProtocol",
    "DependencyResolver",
    # 任务调度器
    "SchedulingStrategy",
    "SchedulerState",
    "ScheduledTask",
    "SchedulerStats",
    "TaskSchedulerProtocol",
    "TaskScheduler",
    # 并行执行器
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
