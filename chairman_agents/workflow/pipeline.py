"""工作流管道模块.

本模块提供工作流管道功能，支持:
- 完整的工作流执行生命周期
- 检查点保存和恢复
- 任务调度和并行执行
- 错误处理和重试机制

架构设计:
    PipelineState: 管道状态数据类
    PipelineCheckpoint: 检查点数据类
    WorkflowPipeline: 工作流管道，协调整个工作流执行

Example:
    >>> pipeline = WorkflowPipeline(
    ...     pipeline_id="pipe_001",
    ...     workflow_id="wf_001",
    ... )
    >>> result = await pipeline.execute(task)
    >>> await pipeline.checkpoint("after_execution")
    >>> # 后续可从检查点恢复
    >>> await pipeline.resume("after_execution")
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable, Generic, TypeVar

from chairman_agents.core.exceptions import (
    PhaseTransitionError,
    WorkflowError,
)
from chairman_agents.core.types import (
    Task,
    TaskResult,
    TaskStatus,
    generate_id,
)
from chairman_agents.workflow.stage_manager import (
    StageManager,
    WorkflowStage,
    StageStatus,
    StageContext,
)


# =============================================================================
# 类型定义
# =============================================================================

T = TypeVar("T")


class PipelineStatus(Enum):
    """管道状态枚举."""

    IDLE = "idle"
    """空闲 - 管道未运行"""

    RUNNING = "running"
    """运行中 - 管道正在执行"""

    PAUSED = "paused"
    """已暂停 - 管道暂停执行"""

    COMPLETED = "completed"
    """已完成 - 管道成功完成"""

    FAILED = "failed"
    """失败 - 管道执行失败"""

    CANCELLED = "cancelled"
    """已取消 - 管道被取消"""


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class PipelineState:
    """管道状态数据类.

    记录管道的完整运行状态，支持序列化和反序列化。

    Attributes:
        pipeline_id: 管道唯一标识符
        workflow_id: 关联的工作流ID
        status: 管道状态
        current_stage: 当前工作流阶段
        started_at: 管道启动时间
        updated_at: 最后更新时间
        completed_at: 完成时间
        task_queue: 待执行任务队列
        completed_tasks: 已完成任务列表
        failed_tasks: 失败任务列表
        artifacts: 生成的工件映射
        metrics: 执行指标
        metadata: 附加元数据

    Example:
        >>> state = PipelineState(
        ...     pipeline_id="pipe_001",
        ...     workflow_id="wf_001",
        ...     status=PipelineStatus.RUNNING,
        ... )
        >>> state_dict = state.to_dict()
        >>> restored = PipelineState.from_dict(state_dict)
    """

    pipeline_id: str = field(default_factory=lambda: generate_id("pipe"))
    """管道唯一标识符"""

    workflow_id: str = ""
    """关联的工作流ID"""

    status: PipelineStatus = PipelineStatus.IDLE
    """管道状态"""

    current_stage: WorkflowStage | None = None
    """当前工作流阶段"""

    started_at: datetime | None = None
    """管道启动时间"""

    updated_at: datetime = field(default_factory=datetime.now)
    """最后更新时间"""

    completed_at: datetime | None = None
    """完成时间"""

    # 任务管理
    task_queue: list[str] = field(default_factory=list)
    """待执行任务ID队列"""

    completed_tasks: list[str] = field(default_factory=list)
    """已完成任务ID列表"""

    failed_tasks: list[str] = field(default_factory=list)
    """失败任务ID列表"""

    # 工件和结果
    artifacts: dict[str, Any] = field(default_factory=dict)
    """生成的工件映射 (task_id -> artifact)"""

    results: dict[str, TaskResult] = field(default_factory=dict)
    """任务结果映射 (task_id -> result)"""

    # 执行指标
    metrics: dict[str, float] = field(default_factory=dict)
    """执行指标（执行时间、成功率等）"""

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    # 错误信息
    last_error: str | None = None
    """最后一个错误信息"""

    error_count: int = 0
    """错误计数"""

    def __repr__(self) -> str:
        """返回状态的简洁表示."""
        stage_str = self.current_stage.value if self.current_stage else "None"
        return (
            f"PipelineState(id={self.pipeline_id!r}, status={self.status.value}, "
            f"stage={stage_str}, tasks={len(self.completed_tasks)}/{len(self.task_queue) + len(self.completed_tasks)})"
        )

    @property
    def progress(self) -> float:
        """计算执行进度 (0.0 - 1.0)."""
        total = len(self.task_queue) + len(self.completed_tasks) + len(self.failed_tasks)
        if total == 0:
            return 0.0
        return len(self.completed_tasks) / total

    @property
    def success_rate(self) -> float:
        """计算成功率 (0.0 - 1.0)."""
        completed = len(self.completed_tasks) + len(self.failed_tasks)
        if completed == 0:
            return 1.0
        return len(self.completed_tasks) / completed

    @property
    def is_running(self) -> bool:
        """判断管道是否正在运行."""
        return self.status == PipelineStatus.RUNNING

    @property
    def is_terminal(self) -> bool:
        """判断管道是否处于终态."""
        return self.status in (
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.CANCELLED,
        )

    @property
    def execution_time_seconds(self) -> float:
        """计算执行时间（秒）."""
        if self.started_at is None:
            return 0.0
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """将状态转换为可序列化的字典.

        Returns:
            状态字典
        """
        return {
            "pipeline_id": self.pipeline_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "task_queue": self.task_queue,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "last_error": self.last_error,
            "error_count": self.error_count,
            "progress": self.progress,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        """从字典恢复状态.

        Args:
            data: 状态字典

        Returns:
            PipelineState 实例
        """
        state = cls(
            pipeline_id=data.get("pipeline_id", generate_id("pipe")),
            workflow_id=data.get("workflow_id", ""),
            status=PipelineStatus(data.get("status", "idle")),
            current_stage=(
                WorkflowStage(data["current_stage"])
                if data.get("current_stage")
                else None
            ),
            task_queue=data.get("task_queue", []),
            completed_tasks=data.get("completed_tasks", []),
            failed_tasks=data.get("failed_tasks", []),
            artifacts=data.get("artifacts", {}),
            metrics=data.get("metrics", {}),
            metadata=data.get("metadata", {}),
            last_error=data.get("last_error"),
            error_count=data.get("error_count", 0),
        )

        # 解析时间戳
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("updated_at"):
            state.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])

        return state


@dataclass
class PipelineCheckpoint:
    """管道检查点数据类.

    保存管道在某一时刻的完整状态，用于恢复执行。

    Attributes:
        checkpoint_id: 检查点唯一标识符
        name: 检查点名称
        pipeline_state: 管道状态快照
        stage_contexts: 阶段上下文快照
        created_at: 创建时间
        description: 检查点描述
    """

    checkpoint_id: str = field(default_factory=lambda: generate_id("ckpt"))
    """检查点唯一标识符"""

    name: str = ""
    """检查点名称"""

    pipeline_state: PipelineState = field(default_factory=PipelineState)
    """管道状态快照"""

    stage_contexts: dict[str, dict[str, Any]] = field(default_factory=dict)
    """阶段上下文快照"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    description: str = ""
    """检查点描述"""

    def to_dict(self) -> dict[str, Any]:
        """将检查点转换为可序列化的字典."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "pipeline_state": self.pipeline_state.to_dict(),
            "stage_contexts": self.stage_contexts,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineCheckpoint:
        """从字典恢复检查点."""
        return cls(
            checkpoint_id=data.get("checkpoint_id", generate_id("ckpt")),
            name=data.get("name", ""),
            pipeline_state=PipelineState.from_dict(data.get("pipeline_state", {})),
            stage_contexts=data.get("stage_contexts", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
            description=data.get("description", ""),
        )


# =============================================================================
# 类型别名
# =============================================================================

# 任务执行器类型
TaskExecutor = Callable[[Task, StageContext], Awaitable[TaskResult]]

# 阶段处理器类型
StageHandler = Callable[[StageContext, list[Task]], Awaitable[list[TaskResult]]]


# =============================================================================
# 工作流管道
# =============================================================================


class WorkflowPipeline:
    """工作流管道 - 协调整个工作流执行.

    提供完整的工作流执行生命周期管理：
    - 任务调度和执行
    - 阶段转换和状态管理
    - 检查点保存和恢复
    - 错误处理和重试

    Attributes:
        pipeline_id: 管道唯一标识符
        workflow_id: 工作流唯一标识符
        state: 管道状态
        stage_manager: 阶段管理器

    Example:
        >>> # 创建管道
        >>> pipeline = WorkflowPipeline(
        ...     pipeline_id="pipe_001",
        ...     workflow_id="wf_001",
        ... )
        >>>
        >>> # 注册阶段处理器
        >>> pipeline.register_handler(WorkflowStage.EXECUTION, my_handler)
        >>>
        >>> # 执行任务
        >>> result = await pipeline.execute(tasks)
        >>>
        >>> # 保存检查点
        >>> await pipeline.checkpoint("mid_execution")
        >>>
        >>> # 从检查点恢复
        >>> await pipeline.resume("mid_execution")
    """

    def __init__(
        self,
        pipeline_id: str | None = None,
        workflow_id: str | None = None,
        *,
        checkpoint_dir: Path | None = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        parallel_limit: int = 5,
    ) -> None:
        """初始化工作流管道.

        Args:
            pipeline_id: 管道唯一标识符（自动生成如果为 None）
            workflow_id: 工作流唯一标识符（自动生成如果为 None）
            checkpoint_dir: 检查点保存目录
            max_retries: 最大重试次数
            retry_delay_seconds: 重试延迟（秒）
            parallel_limit: 并行任务限制
        """
        self.pipeline_id = pipeline_id or generate_id("pipe")
        self.workflow_id = workflow_id or generate_id("wf")

        # 配置
        self._checkpoint_dir = checkpoint_dir
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds
        self._parallel_limit = parallel_limit

        # 状态
        self._state = PipelineState(
            pipeline_id=self.pipeline_id,
            workflow_id=self.workflow_id,
        )

        # 阶段管理器
        self._stage_manager = StageManager(
            workflow_id=self.workflow_id,
            allow_rollback=True,
        )

        # 检查点存储
        self._checkpoints: dict[str, PipelineCheckpoint] = {}

        # 阶段处理器
        self._stage_handlers: dict[WorkflowStage, StageHandler] = {}

        # 任务执行器
        self._task_executor: TaskExecutor | None = None

        # 任务存储
        self._tasks: dict[str, Task] = {}

        # 并发控制
        self._semaphore = asyncio.Semaphore(parallel_limit)
        self._lock = asyncio.Lock()
        self._cancel_event = asyncio.Event()

    # =========================================================================
    # 属性
    # =========================================================================

    @property
    def state(self) -> PipelineState:
        """获取管道状态的只读副本."""
        return self._state

    @property
    def stage_manager(self) -> StageManager:
        """获取阶段管理器."""
        return self._stage_manager

    @property
    def is_running(self) -> bool:
        """判断管道是否正在运行."""
        return self._state.status == PipelineStatus.RUNNING

    @property
    def is_completed(self) -> bool:
        """判断管道是否已完成."""
        return self._state.status == PipelineStatus.COMPLETED

    @property
    def checkpoints(self) -> dict[str, PipelineCheckpoint]:
        """获取所有检查点."""
        return dict(self._checkpoints)

    # =========================================================================
    # 配置
    # =========================================================================

    def register_handler(
        self,
        stage: WorkflowStage,
        handler: StageHandler,
    ) -> None:
        """注册阶段处理器.

        Args:
            stage: 工作流阶段
            handler: 阶段处理器函数
        """
        self._stage_handlers[stage] = handler

    def set_task_executor(self, executor: TaskExecutor) -> None:
        """设置任务执行器.

        Args:
            executor: 任务执行器函数
        """
        self._task_executor = executor

    # =========================================================================
    # 执行控制
    # =========================================================================

    async def execute(
        self,
        tasks: list[Task] | Task,
        *,
        auto_checkpoint: bool = True,
    ) -> list[TaskResult]:
        """执行工作流任务.

        Args:
            tasks: 任务或任务列表
            auto_checkpoint: 是否自动保存检查点

        Returns:
            任务执行结果列表

        Raises:
            WorkflowError: 如果管道状态无效
        """
        async with self._lock:
            # 验证状态
            if self._state.is_running:
                raise WorkflowError(
                    "管道正在运行，无法启动新的执行",
                    workflow_id=self.workflow_id,
                )

            # 初始化
            if isinstance(tasks, Task):
                tasks = [tasks]

            # 重置取消事件
            self._cancel_event.clear()

            # 存储任务
            for task in tasks:
                self._tasks[task.id] = task
                self._state.task_queue.append(task.id)

            # 更新状态
            self._state.status = PipelineStatus.RUNNING
            self._state.started_at = datetime.now()
            self._state.updated_at = datetime.now()

        results: list[TaskResult] = []

        try:
            # 按阶段执行
            for stage in WorkflowStage.get_order():
                # 检查取消
                if self._cancel_event.is_set():
                    break

                # 进入阶段
                context = await self._stage_manager.enter_stage(stage)
                self._state.current_stage = stage

                # 执行阶段处理
                stage_results = await self._execute_stage(stage, context, tasks)
                results.extend(stage_results)

                # 自动检查点
                if auto_checkpoint:
                    await self.checkpoint(f"after_{stage.value}")

                # 完成阶段并获取下一阶段
                next_stage = await self._stage_manager.complete_stage(
                    outputs={"results": [r.task_id for r in stage_results]},
                    auto_advance=False,  # 手动控制阶段推进
                )

                # 检查是否需要进入下一阶段
                if next_stage:
                    continue

            # 完成
            async with self._lock:
                self._state.status = PipelineStatus.COMPLETED
                self._state.completed_at = datetime.now()
                self._state.updated_at = datetime.now()

        except Exception as e:
            async with self._lock:
                self._state.status = PipelineStatus.FAILED
                self._state.last_error = str(e)
                self._state.error_count += 1
                self._state.updated_at = datetime.now()
            raise

        return results

    async def _execute_stage(
        self,
        stage: WorkflowStage,
        context: StageContext,
        tasks: list[Task],
    ) -> list[TaskResult]:
        """执行单个阶段.

        Args:
            stage: 工作流阶段
            context: 阶段上下文
            tasks: 任务列表

        Returns:
            阶段执行结果列表
        """
        results: list[TaskResult] = []

        # 使用注册的处理器
        if stage in self._stage_handlers:
            handler = self._stage_handlers[stage]
            results = await handler(context, tasks)

        # 使用默认执行器（仅在 EXECUTION 阶段）
        elif stage == WorkflowStage.EXECUTION and self._task_executor:
            results = await self._execute_tasks_parallel(tasks, context)

        # 更新状态
        for result in results:
            if result.success:
                if result.task_id not in self._state.completed_tasks:
                    self._state.completed_tasks.append(result.task_id)
                # 从队列中移除
                if result.task_id in self._state.task_queue:
                    self._state.task_queue.remove(result.task_id)
            else:
                if result.task_id not in self._state.failed_tasks:
                    self._state.failed_tasks.append(result.task_id)

            # 保存结果
            self._state.results[result.task_id] = result

        return results

    async def _execute_tasks_parallel(
        self,
        tasks: list[Task],
        context: StageContext,
    ) -> list[TaskResult]:
        """并行执行任务.

        Args:
            tasks: 任务列表
            context: 阶段上下文

        Returns:
            任务结果列表
        """
        if not self._task_executor:
            return []

        async def execute_with_semaphore(task: Task) -> TaskResult:
            async with self._semaphore:
                # 检查取消
                if self._cancel_event.is_set():
                    return TaskResult(
                        task_id=task.id,
                        success=False,
                        error_message="任务被取消",
                    )

                # 重试逻辑
                for attempt in range(self._max_retries + 1):
                    try:
                        result = await self._task_executor(task, context)  # type: ignore
                        return result
                    except Exception as e:
                        if attempt == self._max_retries:
                            return TaskResult(
                                task_id=task.id,
                                success=False,
                                error_message=str(e),
                                error_type=type(e).__name__,
                            )
                        await asyncio.sleep(self._retry_delay * (attempt + 1))

                # 不应该到达这里
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error_message="未知错误",
                )

        # 并行执行
        coroutines = [execute_with_semaphore(task) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=False)

        return list(results)

    async def pause(self) -> None:
        """暂停管道执行."""
        async with self._lock:
            if self._state.status == PipelineStatus.RUNNING:
                self._state.status = PipelineStatus.PAUSED
                self._state.updated_at = datetime.now()
                self._cancel_event.set()

    async def cancel(self) -> None:
        """取消管道执行."""
        async with self._lock:
            if self._state.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED):
                self._state.status = PipelineStatus.CANCELLED
                self._state.updated_at = datetime.now()
                self._cancel_event.set()

    # =========================================================================
    # 检查点管理
    # =========================================================================

    async def checkpoint(
        self,
        name: str,
        *,
        description: str = "",
        persist: bool = True,
    ) -> PipelineCheckpoint:
        """保存检查点.

        Args:
            name: 检查点名称
            description: 检查点描述
            persist: 是否持久化到磁盘

        Returns:
            创建的检查点
        """
        async with self._lock:
            # 收集阶段上下文
            stage_contexts: dict[str, dict[str, Any]] = {}
            for stage in WorkflowStage:
                ctx = self._stage_manager.get_stage_context(stage)
                if ctx:
                    stage_contexts[stage.value] = {
                        "inputs": ctx.inputs,
                        "outputs": ctx.outputs,
                        "errors": ctx.errors,
                        "warnings": ctx.warnings,
                    }

            # 创建检查点
            checkpoint = PipelineCheckpoint(
                name=name,
                pipeline_state=PipelineState(
                    pipeline_id=self._state.pipeline_id,
                    workflow_id=self._state.workflow_id,
                    status=self._state.status,
                    current_stage=self._state.current_stage,
                    started_at=self._state.started_at,
                    updated_at=datetime.now(),
                    completed_at=self._state.completed_at,
                    task_queue=list(self._state.task_queue),
                    completed_tasks=list(self._state.completed_tasks),
                    failed_tasks=list(self._state.failed_tasks),
                    artifacts=dict(self._state.artifacts),
                    metrics=dict(self._state.metrics),
                    metadata=dict(self._state.metadata),
                    last_error=self._state.last_error,
                    error_count=self._state.error_count,
                ),
                stage_contexts=stage_contexts,
                description=description,
            )

            # 存储检查点
            self._checkpoints[name] = checkpoint

            # 持久化
            if persist and self._checkpoint_dir:
                await self._persist_checkpoint(checkpoint)

            return checkpoint

    async def resume(
        self,
        checkpoint_name: str,
        *,
        from_disk: bool = False,
    ) -> None:
        """从检查点恢复执行.

        Args:
            checkpoint_name: 检查点名称
            from_disk: 是否从磁盘加载

        Raises:
            WorkflowError: 如果检查点不存在
        """
        async with self._lock:
            # 获取检查点
            if from_disk and self._checkpoint_dir:
                checkpoint = await self._load_checkpoint(checkpoint_name)
            else:
                checkpoint = self._checkpoints.get(checkpoint_name)

            if checkpoint is None:
                raise WorkflowError(
                    f"检查点 '{checkpoint_name}' 不存在",
                    workflow_id=self.workflow_id,
                )

            # 恢复状态
            self._state = PipelineState.from_dict(
                checkpoint.pipeline_state.to_dict()
            )

            # 如果之前是暂停状态，恢复为运行
            if self._state.status == PipelineStatus.PAUSED:
                self._state.status = PipelineStatus.RUNNING

            # 重置取消事件
            self._cancel_event.clear()

            # 恢复阶段管理器状态
            if checkpoint.pipeline_state.current_stage:
                # 重新进入当前阶段
                await self._stage_manager.enter_stage(
                    checkpoint.pipeline_state.current_stage,
                    force=True,
                )

    async def _persist_checkpoint(self, checkpoint: PipelineCheckpoint) -> None:
        """持久化检查点到磁盘.

        Args:
            checkpoint: 检查点
        """
        if not self._checkpoint_dir:
            return

        # 确保目录存在
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 保存检查点文件
        filepath = self._checkpoint_dir / f"{checkpoint.name}.json"
        data = checkpoint.to_dict()

        # 异步写入
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            ),
        )

    async def _load_checkpoint(self, name: str) -> PipelineCheckpoint | None:
        """从磁盘加载检查点.

        Args:
            name: 检查点名称

        Returns:
            检查点，如果不存在则返回 None
        """
        if not self._checkpoint_dir:
            return None

        filepath = self._checkpoint_dir / f"{name}.json"
        if not filepath.exists():
            return None

        # 异步读取
        data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: json.loads(filepath.read_text(encoding="utf-8")),
        )

        return PipelineCheckpoint.from_dict(data)

    def list_checkpoints(self) -> list[str]:
        """列出所有检查点名称.

        Returns:
            检查点名称列表
        """
        return list(self._checkpoints.keys())

    async def delete_checkpoint(
        self,
        name: str,
        *,
        from_disk: bool = True,
    ) -> bool:
        """删除检查点.

        Args:
            name: 检查点名称
            from_disk: 是否同时删除磁盘文件

        Returns:
            是否成功删除
        """
        async with self._lock:
            # 删除内存中的检查点
            deleted = name in self._checkpoints
            if deleted:
                del self._checkpoints[name]

            # 删除磁盘文件
            if from_disk and self._checkpoint_dir:
                filepath = self._checkpoint_dir / f"{name}.json"
                if filepath.exists():
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        filepath.unlink,
                    )
                    deleted = True

            return deleted

    # =========================================================================
    # 任务管理
    # =========================================================================

    def get_task(self, task_id: str) -> Task | None:
        """获取任务.

        Args:
            task_id: 任务ID

        Returns:
            任务，如果不存在则返回 None
        """
        return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> TaskResult | None:
        """获取任务结果.

        Args:
            task_id: 任务ID

        Returns:
            任务结果，如果不存在则返回 None
        """
        return self._state.results.get(task_id)

    def get_pending_tasks(self) -> list[Task]:
        """获取待执行的任务列表.

        Returns:
            任务列表
        """
        return [
            self._tasks[tid]
            for tid in self._state.task_queue
            if tid in self._tasks
        ]

    def get_completed_tasks(self) -> list[Task]:
        """获取已完成的任务列表.

        Returns:
            任务列表
        """
        return [
            self._tasks[tid]
            for tid in self._state.completed_tasks
            if tid in self._tasks
        ]

    def get_failed_tasks(self) -> list[Task]:
        """获取失败的任务列表.

        Returns:
            任务列表
        """
        return [
            self._tasks[tid]
            for tid in self._state.failed_tasks
            if tid in self._tasks
        ]

    # =========================================================================
    # 状态查询
    # =========================================================================

    def get_metrics(self) -> dict[str, float]:
        """获取执行指标.

        Returns:
            指标字典
        """
        return {
            "progress": self._state.progress,
            "success_rate": self._state.success_rate,
            "execution_time_seconds": self._state.execution_time_seconds,
            "total_tasks": len(self._tasks),
            "completed_tasks": len(self._state.completed_tasks),
            "failed_tasks": len(self._state.failed_tasks),
            "pending_tasks": len(self._state.task_queue),
            "error_count": self._state.error_count,
            **self._state.metrics,
        }

    def to_dict(self) -> dict[str, Any]:
        """将管道状态转换为字典.

        Returns:
            状态字典
        """
        return {
            "pipeline_id": self.pipeline_id,
            "workflow_id": self.workflow_id,
            "state": self._state.to_dict(),
            "stage_manager": self._stage_manager.to_dict(),
            "checkpoints": list(self._checkpoints.keys()),
            "metrics": self.get_metrics(),
        }

    def __repr__(self) -> str:
        """返回管道的简洁表示."""
        return (
            f"WorkflowPipeline(id={self.pipeline_id!r}, "
            f"status={self._state.status.value}, "
            f"progress={self._state.progress:.1%})"
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "PipelineStatus",
    "PipelineState",
    "PipelineCheckpoint",
    "WorkflowPipeline",
    "TaskExecutor",
    "StageHandler",
]
