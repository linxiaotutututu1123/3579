"""依赖解析器模块.

本模块提供任务依赖关系的解析和管理功能，支持：
- 依赖图构建与验证
- 循环依赖检测
- 拓扑排序
- 可执行任务识别

核心类:
    DependencyGraph: 依赖图数据结构
    DependencyResolver: 依赖解析器实现
    DependencyResolverProtocol: 依赖解析器协议接口

Example:
    >>> resolver = DependencyResolver()
    >>> resolver.add_task(task1)
    >>> resolver.add_task(task2, dependencies=["task1"])
    >>> ready_tasks = await resolver.get_ready_tasks()
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from chairman_agents.core.exceptions import DependencyError
from chairman_agents.core.types import Task, TaskId, TaskStatus

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


# =============================================================================
# 枚举定义
# =============================================================================


class DependencyState(Enum):
    """依赖状态枚举.

    States:
        UNRESOLVED: 依赖尚未解析
        RESOLVED: 依赖已解析完成
        BLOCKED: 依赖被阻塞
        CIRCULAR: 存在循环依赖
    """

    UNRESOLVED = "unresolved"
    """依赖尚未解析"""

    RESOLVED = "resolved"
    """依赖已解析完成"""

    BLOCKED = "blocked"
    """依赖被阻塞"""

    CIRCULAR = "circular"
    """存在循环依赖"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class DependencyNode:
    """依赖图中的节点.

    表示依赖图中的一个任务节点，包含其依赖关系和状态。

    Attributes:
        task_id: 任务唯一标识
        task: 关联的任务对象
        dependencies: 前置依赖任务 ID 集合
        dependents: 后置依赖任务 ID 集合（依赖此任务的任务）
        state: 当前依赖状态
        depth: 在依赖图中的深度层级
    """

    task_id: TaskId
    """任务唯一标识"""

    task: Task
    """关联的任务对象"""

    dependencies: set[TaskId] = field(default_factory=set)
    """前置依赖任务 ID 集合"""

    dependents: set[TaskId] = field(default_factory=set)
    """后置依赖任务 ID 集合"""

    state: DependencyState = DependencyState.UNRESOLVED
    """当前依赖状态"""

    depth: int = 0
    """在依赖图中的深度层级"""

    def is_ready(self) -> bool:
        """检查任务是否可以执行.

        Returns:
            如果没有未完成的依赖则返回 True
        """
        return len(self.dependencies) == 0 and self.state == DependencyState.UNRESOLVED


@dataclass
class DependencyGraph:
    """任务依赖图.

    管理任务之间的依赖关系，提供依赖分析功能。

    Attributes:
        nodes: 任务 ID 到节点的映射
        _completed_tasks: 已完成任务 ID 集合
        _failed_tasks: 失败任务 ID 集合
    """

    nodes: dict[TaskId, DependencyNode] = field(default_factory=dict)
    """任务 ID 到节点的映射"""

    _completed_tasks: set[TaskId] = field(default_factory=set)
    """已完成任务 ID 集合"""

    _failed_tasks: set[TaskId] = field(default_factory=set)
    """失败任务 ID 集合"""

    def add_node(self, task: Task) -> DependencyNode:
        """添加任务节点到图中.

        Args:
            task: 要添加的任务

        Returns:
            创建的依赖节点
        """
        if task.id in self.nodes:
            return self.nodes[task.id]

        node = DependencyNode(
            task_id=task.id,
            task=task,
            dependencies=set(task.dependencies),
        )
        self.nodes[task.id] = node

        # 更新反向依赖关系
        for dep_id in task.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.add(task.id)

        return node

    def remove_node(self, task_id: TaskId) -> None:
        """从图中移除任务节点.

        Args:
            task_id: 要移除的任务 ID
        """
        if task_id not in self.nodes:
            return

        node = self.nodes[task_id]

        # 清理反向依赖
        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.discard(task_id)

        # 清理正向依赖
        for dependent_id in node.dependents:
            if dependent_id in self.nodes:
                self.nodes[dependent_id].dependencies.discard(task_id)

        del self.nodes[task_id]

    def mark_completed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务为已完成.

        标记后会更新所有依赖此任务的节点。

        Args:
            task_id: 完成的任务 ID

        Returns:
            因此变为可执行状态的任务 ID 列表
        """
        if task_id not in self.nodes:
            return []

        node = self.nodes[task_id]
        node.state = DependencyState.RESOLVED
        self._completed_tasks.add(task_id)

        newly_ready: list[TaskId] = []

        # 更新所有依赖此任务的节点
        for dependent_id in node.dependents:
            if dependent_id in self.nodes:
                dep_node = self.nodes[dependent_id]
                dep_node.dependencies.discard(task_id)
                if dep_node.is_ready():
                    newly_ready.append(dependent_id)

        return newly_ready

    def mark_failed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务为失败.

        会级联阻塞所有依赖此任务的任务。

        Args:
            task_id: 失败的任务 ID

        Returns:
            被阻塞的任务 ID 列表
        """
        if task_id not in self.nodes:
            return []

        self._failed_tasks.add(task_id)
        blocked_tasks: list[TaskId] = []

        # 递归阻塞所有下游任务
        def block_dependents(tid: TaskId) -> None:
            if tid not in self.nodes:
                return
            node = self.nodes[tid]
            if node.state == DependencyState.BLOCKED:
                return
            node.state = DependencyState.BLOCKED
            blocked_tasks.append(tid)
            for dependent_id in node.dependents:
                block_dependents(dependent_id)

        block_dependents(task_id)
        return blocked_tasks

    def get_ready_tasks(self) -> list[Task]:
        """获取所有可执行的任务.

        Returns:
            可以立即执行的任务列表
        """
        ready = []
        for node in self.nodes.values():
            if node.is_ready() and node.task.status == TaskStatus.PENDING:
                ready.append(node.task)
        return ready

    @property
    def is_empty(self) -> bool:
        """检查图是否为空."""
        return len(self.nodes) == 0

    @property
    def total_tasks(self) -> int:
        """获取总任务数."""
        return len(self.nodes)

    @property
    def completed_count(self) -> int:
        """获取已完成任务数."""
        return len(self._completed_tasks)

    @property
    def pending_count(self) -> int:
        """获取待处理任务数."""
        return len(self.nodes) - len(self._completed_tasks) - len(self._failed_tasks)


@dataclass
class ResolutionResult:
    """依赖解析结果.

    Attributes:
        success: 解析是否成功
        execution_order: 任务的拓扑执行顺序
        circular_dependencies: 检测到的循环依赖链
        missing_dependencies: 缺失的依赖任务 ID
        execution_levels: 按执行层级分组的任务（可并行执行）
    """

    success: bool = True
    """解析是否成功"""

    execution_order: list[TaskId] = field(default_factory=list)
    """任务的拓扑执行顺序"""

    circular_dependencies: list[list[TaskId]] = field(default_factory=list)
    """检测到的循环依赖链"""

    missing_dependencies: set[TaskId] = field(default_factory=set)
    """缺失的依赖任务 ID"""

    execution_levels: list[list[TaskId]] = field(default_factory=list)
    """按执行层级分组的任务"""


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class DependencyResolverProtocol(Protocol):
    """依赖解析器协议.

    定义依赖解析器的标准接口。

    Example:
        >>> class MyResolver(DependencyResolverProtocol):
        ...     async def resolve(self, tasks: list[Task]) -> ResolutionResult:
        ...         # 实现解析逻辑
        ...         return ResolutionResult()
    """

    async def resolve(self, tasks: Sequence[Task]) -> ResolutionResult:
        """解析任务依赖关系.

        Args:
            tasks: 要解析的任务列表

        Returns:
            解析结果
        """
        ...

    async def get_ready_tasks(self) -> list[Task]:
        """获取可执行的任务列表.

        Returns:
            当前可以执行的任务列表
        """
        ...

    async def mark_completed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务完成.

        Args:
            task_id: 完成的任务 ID

        Returns:
            因此变为可执行的任务 ID 列表
        """
        ...

    async def mark_failed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务失败.

        Args:
            task_id: 失败的任务 ID

        Returns:
            被阻塞的任务 ID 列表
        """
        ...


# =============================================================================
# 依赖解析器实现
# =============================================================================


class DependencyResolver:
    """任务依赖解析器.

    提供完整的依赖关系解析功能：
    - 构建和管理依赖图
    - 检测循环依赖
    - 拓扑排序
    - 动态更新依赖状态

    Attributes:
        graph: 内部依赖图
        _lock: 异步锁，保证线程安全

    Example:
        >>> resolver = DependencyResolver()
        >>> tasks = [task1, task2, task3]
        >>> result = await resolver.resolve(tasks)
        >>> if result.success:
        ...     for level in result.execution_levels:
        ...         # 同一层级的任务可以并行执行
        ...         await execute_parallel(level)
    """

    def __init__(self) -> None:
        """初始化依赖解析器."""
        self.graph = DependencyGraph()
        self._lock = asyncio.Lock()

    async def resolve(self, tasks: Sequence[Task]) -> ResolutionResult:
        """解析任务依赖关系.

        分析所有任务的依赖关系，检测问题，并计算执行顺序。

        Args:
            tasks: 要解析的任务列表

        Returns:
            包含解析结果的 ResolutionResult 对象

        Raises:
            DependencyError: 当存在无法解决的依赖问题时
        """
        async with self._lock:
            result = ResolutionResult()

            # 1. 构建依赖图
            task_ids = set()
            for task in tasks:
                self.graph.add_node(task)
                task_ids.add(task.id)

            # 2. 检测缺失依赖
            for task in tasks:
                for dep_id in task.dependencies:
                    if dep_id not in task_ids:
                        result.missing_dependencies.add(dep_id)

            if result.missing_dependencies:
                result.success = False
                return result

            # 3. 检测循环依赖
            cycles = self._detect_cycles()
            if cycles:
                result.circular_dependencies = cycles
                result.success = False
                return result

            # 4. 拓扑排序
            result.execution_order = self._topological_sort()

            # 5. 计算执行层级
            result.execution_levels = self._compute_execution_levels()

            return result

    async def add_task(
        self,
        task: Task,
        dependencies: Iterable[TaskId] | None = None,
    ) -> None:
        """添加单个任务到解析器.

        Args:
            task: 要添加的任务
            dependencies: 额外的依赖任务 ID（可选）
        """
        async with self._lock:
            if dependencies:
                task.dependencies.extend(dep for dep in dependencies if dep not in task.dependencies)
            self.graph.add_node(task)

    async def remove_task(self, task_id: TaskId) -> None:
        """从解析器中移除任务.

        Args:
            task_id: 要移除的任务 ID
        """
        async with self._lock:
            self.graph.remove_node(task_id)

    async def get_ready_tasks(self) -> list[Task]:
        """获取当前可执行的任务.

        Returns:
            没有未完成依赖的任务列表
        """
        async with self._lock:
            return self.graph.get_ready_tasks()

    async def mark_completed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务为已完成.

        更新依赖图并返回新的可执行任务。

        Args:
            task_id: 完成的任务 ID

        Returns:
            因依赖解除而变为可执行的任务 ID 列表
        """
        async with self._lock:
            return self.graph.mark_completed(task_id)

    async def mark_failed(self, task_id: TaskId) -> list[TaskId]:
        """标记任务为失败.

        级联阻塞所有下游依赖任务。

        Args:
            task_id: 失败的任务 ID

        Returns:
            被阻塞的任务 ID 列表
        """
        async with self._lock:
            return self.graph.mark_failed(task_id)

    async def get_dependency_chain(self, task_id: TaskId) -> list[TaskId]:
        """获取任务的完整依赖链.

        Args:
            task_id: 目标任务 ID

        Returns:
            从根任务到目标任务的依赖链
        """
        async with self._lock:
            chain: list[TaskId] = []
            visited: set[TaskId] = set()

            def trace_back(tid: TaskId) -> None:
                if tid in visited or tid not in self.graph.nodes:
                    return
                visited.add(tid)
                node = self.graph.nodes[tid]
                for dep_id in node.dependencies:
                    trace_back(dep_id)
                chain.append(tid)

            trace_back(task_id)
            return chain

    async def get_blocked_tasks(self) -> list[Task]:
        """获取所有被阻塞的任务.

        Returns:
            状态为 BLOCKED 的任务列表
        """
        async with self._lock:
            blocked = []
            for node in self.graph.nodes.values():
                if node.state == DependencyState.BLOCKED:
                    blocked.append(node.task)
            return blocked

    async def validate(self) -> tuple[bool, list[str]]:
        """验证当前依赖图的有效性.

        Returns:
            (是否有效, 问题描述列表)
        """
        async with self._lock:
            issues: list[str] = []

            # 检查循环依赖
            cycles = self._detect_cycles()
            for cycle in cycles:
                issues.append(f"循环依赖: {' -> '.join(cycle)}")

            # 检查缺失依赖
            all_ids = set(self.graph.nodes.keys())
            for node in self.graph.nodes.values():
                for dep_id in node.dependencies:
                    if dep_id not in all_ids:
                        issues.append(f"任务 {node.task_id} 依赖不存在的任务 {dep_id}")

            return len(issues) == 0, issues

    async def clear(self) -> None:
        """清空解析器状态."""
        async with self._lock:
            self.graph = DependencyGraph()

    @property
    def stats(self) -> dict[str, int]:
        """获取当前统计信息.

        Returns:
            包含各种统计数据的字典
        """
        return {
            "total_tasks": self.graph.total_tasks,
            "completed_tasks": self.graph.completed_count,
            "pending_tasks": self.graph.pending_count,
            "ready_tasks": len(self.graph.get_ready_tasks()),
        }

    def _detect_cycles(self) -> list[list[TaskId]]:
        """检测依赖图中的循环依赖.

        使用 DFS 算法检测所有循环。

        Returns:
            检测到的循环依赖链列表
        """
        cycles: list[list[TaskId]] = []
        visited: set[TaskId] = set()
        rec_stack: set[TaskId] = set()
        path: list[TaskId] = []

        def dfs(task_id: TaskId) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            if task_id in self.graph.nodes:
                node = self.graph.nodes[task_id]
                for dep_id in node.dependencies:
                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # 找到循环
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)
                        return True

            path.pop()
            rec_stack.remove(task_id)
            return False

        for task_id in self.graph.nodes:
            if task_id not in visited:
                dfs(task_id)

        return cycles

    def _topological_sort(self) -> list[TaskId]:
        """对任务进行拓扑排序.

        Returns:
            按依赖顺序排列的任务 ID 列表
        """
        in_degree: dict[TaskId, int] = defaultdict(int)
        for node in self.graph.nodes.values():
            if node.task_id not in in_degree:
                in_degree[node.task_id] = 0
            for dep_id in node.dependencies:
                in_degree[node.task_id] += 1

        # 从入度为 0 的节点开始
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result: list[TaskId] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            if current in self.graph.nodes:
                for dependent_id in self.graph.nodes[current].dependents:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)

        return result

    def _compute_execution_levels(self) -> list[list[TaskId]]:
        """计算任务的执行层级.

        同一层级的任务可以并行执行。

        Returns:
            按层级分组的任务 ID 列表
        """
        levels: list[list[TaskId]] = []
        remaining = set(self.graph.nodes.keys())
        completed: set[TaskId] = set()

        while remaining:
            # 找出当前可执行的任务（所有依赖都在 completed 中）
            current_level: list[TaskId] = []
            for task_id in remaining:
                node = self.graph.nodes[task_id]
                if all(dep_id in completed for dep_id in node.task.dependencies):
                    current_level.append(task_id)

            if not current_level:
                # 无法继续，可能存在循环依赖
                break

            levels.append(current_level)
            for task_id in current_level:
                remaining.remove(task_id)
                completed.add(task_id)

        return levels


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "DependencyState",
    "DependencyNode",
    "DependencyGraph",
    "ResolutionResult",
    "DependencyResolverProtocol",
    "DependencyResolver",
]
