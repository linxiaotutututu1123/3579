"""工作流阶段管理器模块.

本模块提供工作流阶段管理功能，支持:
- 6阶段标准工作流: 初始化 -> 规划 -> 执行 -> 审查 -> 完善 -> 完成
- 阶段状态跟踪和转换验证
- 阶段回滚和恢复机制

架构设计:
    WorkflowStage: 工作流阶段枚举（6个标准阶段）
    StageTransition: 阶段转换记录
    StageManager: 阶段管理器，控制工作流阶段生命周期

Example:
    >>> manager = StageManager(workflow_id="wf_001")
    >>> await manager.enter_stage(WorkflowStage.PLANNING)
    >>> await manager.complete_stage()
    >>> print(manager.current_stage)  # WorkflowStage.EXECUTION
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from chairman_agents.core.exceptions import (
    PhaseTransitionError,
    WorkflowError,
)
from chairman_agents.core.types import generate_id


# =============================================================================
# 类型定义
# =============================================================================


class WorkflowStage(Enum):
    """工作流阶段枚举 - 6个标准阶段.

    工作流生命周期分为6个阶段，每个阶段有特定的职责和产出：

    1. INITIALIZATION: 初始化阶段
       - 加载配置和资源
       - 验证前置条件
       - 建立执行环境

    2. PLANNING: 规划阶段
       - 任务分解和调度
       - 资源分配
       - 制定执行计划

    3. EXECUTION: 执行阶段
       - 执行任务
       - 生成工件
       - 实时监控

    4. REVIEW: 审查阶段
       - 质量检查
       - 代码审查
       - 安全审计

    5. REFINEMENT: 完善阶段
       - 根据审查反馈修改
       - 优化和改进
       - 重新验证

    6. COMPLETION: 完成阶段
       - 最终验证
       - 资源清理
       - 报告生成
    """

    INITIALIZATION = "initialization"
    """初始化阶段 - 加载配置、验证前置条件、建立执行环境"""

    PLANNING = "planning"
    """规划阶段 - 任务分解、资源分配、制定执行计划"""

    EXECUTION = "execution"
    """执行阶段 - 执行任务、生成工件、实时监控"""

    REVIEW = "review"
    """审查阶段 - 质量检查、代码审查、安全审计"""

    REFINEMENT = "refinement"
    """完善阶段 - 根据审查反馈修改、优化和改进"""

    COMPLETION = "completion"
    """完成阶段 - 最终验证、资源清理、报告生成"""

    @classmethod
    def get_order(cls) -> list[WorkflowStage]:
        """获取阶段的标准顺序.

        Returns:
            按顺序排列的阶段列表
        """
        return [
            cls.INITIALIZATION,
            cls.PLANNING,
            cls.EXECUTION,
            cls.REVIEW,
            cls.REFINEMENT,
            cls.COMPLETION,
        ]

    @classmethod
    def get_index(cls, stage: WorkflowStage) -> int:
        """获取阶段的索引位置.

        Args:
            stage: 工作流阶段

        Returns:
            阶段在标准顺序中的索引（0-5）

        Raises:
            ValueError: 如果阶段无效
        """
        order = cls.get_order()
        return order.index(stage)

    @classmethod
    def get_next(cls, stage: WorkflowStage) -> WorkflowStage | None:
        """获取下一个阶段.

        Args:
            stage: 当前阶段

        Returns:
            下一个阶段，如果已是最后阶段则返回 None
        """
        order = cls.get_order()
        idx = order.index(stage)
        if idx < len(order) - 1:
            return order[idx + 1]
        return None

    @classmethod
    def get_previous(cls, stage: WorkflowStage) -> WorkflowStage | None:
        """获取上一个阶段.

        Args:
            stage: 当前阶段

        Returns:
            上一个阶段，如果已是第一阶段则返回 None
        """
        order = cls.get_order()
        idx = order.index(stage)
        if idx > 0:
            return order[idx - 1]
        return None


class StageStatus(Enum):
    """阶段状态枚举."""

    PENDING = "pending"
    """待处理 - 阶段尚未开始"""

    ACTIVE = "active"
    """活动中 - 阶段正在执行"""

    COMPLETED = "completed"
    """已完成 - 阶段成功完成"""

    FAILED = "failed"
    """失败 - 阶段执行失败"""

    SKIPPED = "skipped"
    """已跳过 - 阶段被跳过"""

    ROLLED_BACK = "rolled_back"
    """已回滚 - 阶段已回滚"""


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class StageTransition:
    """阶段转换记录.

    记录工作流阶段之间的转换历史，用于审计和回滚。

    Attributes:
        id: 转换记录唯一标识符
        from_stage: 源阶段（None 表示初始进入）
        to_stage: 目标阶段
        status: 转换后的状态
        timestamp: 转换时间戳
        duration_seconds: 阶段执行时长（秒）
        metadata: 附加元数据
    """

    id: str = field(default_factory=lambda: generate_id("trans"))
    """转换记录唯一标识符"""

    from_stage: WorkflowStage | None = None
    """源阶段"""

    to_stage: WorkflowStage = WorkflowStage.INITIALIZATION
    """目标阶段"""

    status: StageStatus = StageStatus.ACTIVE
    """转换后的状态"""

    timestamp: datetime = field(default_factory=datetime.now)
    """转换时间戳"""

    duration_seconds: float | None = None
    """阶段执行时长（秒）"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    def __repr__(self) -> str:
        """返回转换记录的简洁表示."""
        from_str = self.from_stage.value if self.from_stage else "None"
        return (
            f"StageTransition({from_str} -> {self.to_stage.value}, "
            f"status={self.status.value})"
        )


@dataclass
class StageContext:
    """阶段执行上下文.

    提供阶段执行所需的上下文信息和中间结果。

    Attributes:
        stage: 当前阶段
        started_at: 阶段开始时间
        inputs: 阶段输入数据
        outputs: 阶段输出数据
        errors: 阶段执行错误列表
        warnings: 阶段执行警告列表
    """

    stage: WorkflowStage = WorkflowStage.INITIALIZATION
    """当前阶段"""

    started_at: datetime = field(default_factory=datetime.now)
    """阶段开始时间"""

    inputs: dict[str, Any] = field(default_factory=dict)
    """阶段输入数据"""

    outputs: dict[str, Any] = field(default_factory=dict)
    """阶段输出数据"""

    errors: list[str] = field(default_factory=list)
    """阶段执行错误列表"""

    warnings: list[str] = field(default_factory=list)
    """阶段执行警告列表"""

    @property
    def has_errors(self) -> bool:
        """判断是否有错误."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """判断是否有警告."""
        return len(self.warnings) > 0


# =============================================================================
# 阶段管理器
# =============================================================================


# 钩子函数类型
StageHook = Callable[[StageContext], Awaitable[None]]


class StageManager:
    """工作流阶段管理器.

    管理工作流的阶段生命周期，包括：
    - 阶段进入和退出控制
    - 阶段状态跟踪
    - 转换验证和历史记录
    - 阶段回滚和恢复

    Attributes:
        workflow_id: 工作流唯一标识符
        current_stage: 当前阶段（可能为 None）
        stage_status: 各阶段状态映射
        transitions: 转换历史记录
        stage_contexts: 各阶段上下文

    Example:
        >>> manager = StageManager(workflow_id="wf_001")
        >>> # 进入初始化阶段
        >>> await manager.enter_stage(WorkflowStage.INITIALIZATION)
        >>> # 完成当前阶段并自动进入下一阶段
        >>> await manager.complete_stage()
        >>> print(manager.current_stage)  # WorkflowStage.PLANNING
        >>> # 回滚到上一阶段
        >>> await manager.rollback()
        >>> print(manager.current_stage)  # WorkflowStage.INITIALIZATION
    """

    def __init__(
        self,
        workflow_id: str,
        *,
        allow_skip: bool = False,
        allow_rollback: bool = True,
        max_rollback_depth: int = 3,
    ) -> None:
        """初始化阶段管理器.

        Args:
            workflow_id: 工作流唯一标识符
            allow_skip: 是否允许跳过阶段
            allow_rollback: 是否允许回滚
            max_rollback_depth: 最大回滚深度
        """
        self.workflow_id = workflow_id
        self.allow_skip = allow_skip
        self.allow_rollback = allow_rollback
        self.max_rollback_depth = max_rollback_depth

        # 状态跟踪
        self._current_stage: WorkflowStage | None = None
        self._stage_status: dict[WorkflowStage, StageStatus] = {
            stage: StageStatus.PENDING for stage in WorkflowStage
        }

        # 历史记录
        self._transitions: list[StageTransition] = []
        self._stage_contexts: dict[WorkflowStage, StageContext] = {}

        # 钩子函数
        self._on_enter_hooks: dict[WorkflowStage, list[StageHook]] = {
            stage: [] for stage in WorkflowStage
        }
        self._on_exit_hooks: dict[WorkflowStage, list[StageHook]] = {
            stage: [] for stage in WorkflowStage
        }

        # 锁，防止并发状态修改
        self._lock = asyncio.Lock()

    # =========================================================================
    # 属性
    # =========================================================================

    @property
    def current_stage(self) -> WorkflowStage | None:
        """获取当前阶段."""
        return self._current_stage

    @property
    def stage_status(self) -> dict[WorkflowStage, StageStatus]:
        """获取所有阶段状态的只读副本."""
        return dict(self._stage_status)

    @property
    def transitions(self) -> list[StageTransition]:
        """获取转换历史的只读副本."""
        return list(self._transitions)

    @property
    def is_completed(self) -> bool:
        """判断工作流是否已完成."""
        return (
            self._current_stage == WorkflowStage.COMPLETION
            and self._stage_status[WorkflowStage.COMPLETION] == StageStatus.COMPLETED
        )

    @property
    def current_context(self) -> StageContext | None:
        """获取当前阶段的上下文."""
        if self._current_stage is None:
            return None
        return self._stage_contexts.get(self._current_stage)

    @property
    def progress(self) -> float:
        """获取工作流进度（0.0 - 1.0）."""
        if self._current_stage is None:
            return 0.0

        completed_count = sum(
            1
            for status in self._stage_status.values()
            if status == StageStatus.COMPLETED
        )

        # 如果当前阶段正在执行，算作半个
        if self._stage_status.get(self._current_stage) == StageStatus.ACTIVE:
            completed_count += 0.5

        return completed_count / len(WorkflowStage)

    # =========================================================================
    # 阶段控制
    # =========================================================================

    async def enter_stage(
        self,
        stage: WorkflowStage,
        *,
        inputs: dict[str, Any] | None = None,
        force: bool = False,
    ) -> StageContext:
        """进入指定阶段.

        Args:
            stage: 要进入的阶段
            inputs: 阶段输入数据
            force: 是否强制进入（跳过验证）

        Returns:
            阶段上下文

        Raises:
            PhaseTransitionError: 如果转换无效
        """
        async with self._lock:
            # 验证转换
            if not force:
                self._validate_transition(self._current_stage, stage)

            # 如果有当前阶段，先执行退出钩子
            if self._current_stage is not None:
                current_context = self._stage_contexts.get(self._current_stage)
                if current_context:
                    await self._run_exit_hooks(current_context)

            # 记录转换
            transition = StageTransition(
                from_stage=self._current_stage,
                to_stage=stage,
                status=StageStatus.ACTIVE,
                metadata={"inputs": inputs or {}},
            )
            self._transitions.append(transition)

            # 更新状态
            self._current_stage = stage
            self._stage_status[stage] = StageStatus.ACTIVE

            # 创建阶段上下文
            context = StageContext(
                stage=stage,
                inputs=inputs or {},
            )
            self._stage_contexts[stage] = context

            # 执行进入钩子
            await self._run_enter_hooks(context)

            return context

    async def complete_stage(
        self,
        *,
        outputs: dict[str, Any] | None = None,
        auto_advance: bool = True,
    ) -> WorkflowStage | None:
        """完成当前阶段.

        Args:
            outputs: 阶段输出数据
            auto_advance: 是否自动进入下一阶段

        Returns:
            下一阶段（如果自动进入），否则返回 None

        Raises:
            WorkflowError: 如果没有活动阶段
        """
        async with self._lock:
            if self._current_stage is None:
                raise WorkflowError(
                    "没有活动的阶段可以完成",
                    workflow_id=self.workflow_id,
                )

            current = self._current_stage
            context = self._stage_contexts.get(current)

            if context:
                # 更新输出
                if outputs:
                    context.outputs.update(outputs)

                # 计算阶段时长
                duration = (datetime.now() - context.started_at).total_seconds()

                # 执行退出钩子
                await self._run_exit_hooks(context)

            else:
                duration = 0.0

            # 更新最后一个转换记录
            if self._transitions:
                self._transitions[-1].status = StageStatus.COMPLETED
                self._transitions[-1].duration_seconds = duration

            # 更新阶段状态
            self._stage_status[current] = StageStatus.COMPLETED

            # 自动进入下一阶段
            if auto_advance:
                next_stage = WorkflowStage.get_next(current)
                if next_stage:
                    self._current_stage = None  # 临时清除以避免锁冲突
                    # 释放锁后再调用 enter_stage
                    return next_stage

            self._current_stage = None
            return None

    async def fail_stage(
        self,
        error: str,
        *,
        retry: bool = False,
    ) -> None:
        """标记当前阶段失败.

        Args:
            error: 错误描述
            retry: 是否允许重试

        Raises:
            WorkflowError: 如果没有活动阶段
        """
        async with self._lock:
            if self._current_stage is None:
                raise WorkflowError(
                    "没有活动的阶段可以标记失败",
                    workflow_id=self.workflow_id,
                )

            current = self._current_stage
            context = self._stage_contexts.get(current)

            if context:
                context.errors.append(error)
                duration = (datetime.now() - context.started_at).total_seconds()
            else:
                duration = 0.0

            # 更新转换记录
            if self._transitions:
                self._transitions[-1].status = StageStatus.FAILED
                self._transitions[-1].duration_seconds = duration
                self._transitions[-1].metadata["error"] = error
                self._transitions[-1].metadata["retry"] = retry

            # 更新阶段状态
            self._stage_status[current] = StageStatus.FAILED

            if not retry:
                self._current_stage = None

    async def rollback(
        self,
        *,
        target_stage: WorkflowStage | None = None,
        preserve_outputs: bool = False,
    ) -> WorkflowStage:
        """回滚到指定阶段或上一阶段.

        Args:
            target_stage: 目标阶段（None 表示上一阶段）
            preserve_outputs: 是否保留输出数据

        Returns:
            回滚后的当前阶段

        Raises:
            PhaseTransitionError: 如果回滚无效
            WorkflowError: 如果回滚被禁用
        """
        async with self._lock:
            if not self.allow_rollback:
                raise WorkflowError(
                    "工作流回滚已被禁用",
                    workflow_id=self.workflow_id,
                )

            if self._current_stage is None:
                raise WorkflowError(
                    "没有活动的阶段可以回滚",
                    workflow_id=self.workflow_id,
                )

            # 确定目标阶段
            if target_stage is None:
                target_stage = WorkflowStage.get_previous(self._current_stage)
                if target_stage is None:
                    raise PhaseTransitionError(
                        "已在第一阶段，无法回滚",
                        workflow_id=self.workflow_id,
                        from_phase=self._current_stage.value,
                        to_phase=None,
                    )

            # 验证回滚深度
            current_idx = WorkflowStage.get_index(self._current_stage)
            target_idx = WorkflowStage.get_index(target_stage)
            rollback_depth = current_idx - target_idx

            if rollback_depth <= 0:
                raise PhaseTransitionError(
                    "无法回滚到当前或更晚的阶段",
                    workflow_id=self.workflow_id,
                    from_phase=self._current_stage.value,
                    to_phase=target_stage.value,
                )

            if rollback_depth > self.max_rollback_depth:
                raise PhaseTransitionError(
                    f"回滚深度 {rollback_depth} 超过最大限制 {self.max_rollback_depth}",
                    workflow_id=self.workflow_id,
                    from_phase=self._current_stage.value,
                    to_phase=target_stage.value,
                )

            # 标记中间阶段为已回滚
            order = WorkflowStage.get_order()
            for i in range(target_idx + 1, current_idx + 1):
                stage = order[i]
                self._stage_status[stage] = StageStatus.ROLLED_BACK

                # 清理上下文（除非保留输出）
                if not preserve_outputs and stage in self._stage_contexts:
                    self._stage_contexts[stage].outputs.clear()

            # 记录回滚转换
            transition = StageTransition(
                from_stage=self._current_stage,
                to_stage=target_stage,
                status=StageStatus.ACTIVE,
                metadata={"type": "rollback", "depth": rollback_depth},
            )
            self._transitions.append(transition)

            # 更新当前阶段
            self._current_stage = target_stage
            self._stage_status[target_stage] = StageStatus.ACTIVE

            # 恢复或创建上下文
            if target_stage not in self._stage_contexts:
                self._stage_contexts[target_stage] = StageContext(stage=target_stage)

            return target_stage

    async def skip_stage(
        self,
        *,
        reason: str = "",
    ) -> WorkflowStage | None:
        """跳过当前阶段.

        Args:
            reason: 跳过原因

        Returns:
            下一阶段，如果已是最后阶段则返回 None

        Raises:
            WorkflowError: 如果跳过被禁用
        """
        async with self._lock:
            if not self.allow_skip:
                raise WorkflowError(
                    "工作流阶段跳过已被禁用",
                    workflow_id=self.workflow_id,
                )

            if self._current_stage is None:
                raise WorkflowError(
                    "没有活动的阶段可以跳过",
                    workflow_id=self.workflow_id,
                )

            current = self._current_stage

            # 更新阶段状态
            self._stage_status[current] = StageStatus.SKIPPED

            # 记录转换
            if self._transitions:
                self._transitions[-1].status = StageStatus.SKIPPED
                self._transitions[-1].metadata["skip_reason"] = reason

            # 获取下一阶段
            next_stage = WorkflowStage.get_next(current)
            self._current_stage = None

            return next_stage

    # =========================================================================
    # 验证
    # =========================================================================

    def _validate_transition(
        self,
        from_stage: WorkflowStage | None,
        to_stage: WorkflowStage,
    ) -> None:
        """验证阶段转换是否有效.

        Args:
            from_stage: 源阶段（None 表示初始进入）
            to_stage: 目标阶段

        Raises:
            PhaseTransitionError: 如果转换无效
        """
        # 初始进入必须是 INITIALIZATION
        if from_stage is None:
            if to_stage != WorkflowStage.INITIALIZATION:
                raise PhaseTransitionError(
                    f"工作流必须从 INITIALIZATION 阶段开始，不能直接进入 {to_stage.value}",
                    workflow_id=self.workflow_id,
                    from_phase=None,
                    to_phase=to_stage.value,
                )
            return

        # 检查阶段状态
        current_status = self._stage_status.get(from_stage)
        if current_status not in (StageStatus.ACTIVE, StageStatus.COMPLETED):
            raise PhaseTransitionError(
                f"当前阶段 {from_stage.value} 状态为 {current_status.value}，不允许转换",
                workflow_id=self.workflow_id,
                from_phase=from_stage.value,
                to_phase=to_stage.value,
            )

        # 获取阶段索引
        from_idx = WorkflowStage.get_index(from_stage)
        to_idx = WorkflowStage.get_index(to_stage)

        # 正常前进：只能进入下一阶段
        if to_idx == from_idx + 1:
            return

        # 允许跳过时可以跳过多个阶段
        if self.allow_skip and to_idx > from_idx:
            return

        # 允许回滚时可以返回之前的阶段
        if self.allow_rollback and to_idx < from_idx:
            depth = from_idx - to_idx
            if depth <= self.max_rollback_depth:
                return

        raise PhaseTransitionError(
            f"无效的阶段转换: {from_stage.value} -> {to_stage.value}",
            workflow_id=self.workflow_id,
            from_phase=from_stage.value,
            to_phase=to_stage.value,
        )

    def can_transition_to(self, stage: WorkflowStage) -> bool:
        """检查是否可以转换到指定阶段.

        Args:
            stage: 目标阶段

        Returns:
            是否可以转换
        """
        try:
            self._validate_transition(self._current_stage, stage)
            return True
        except PhaseTransitionError:
            return False

    # =========================================================================
    # 钩子管理
    # =========================================================================

    def on_enter(self, stage: WorkflowStage, hook: StageHook) -> None:
        """注册阶段进入钩子.

        Args:
            stage: 阶段
            hook: 钩子函数
        """
        self._on_enter_hooks[stage].append(hook)

    def on_exit(self, stage: WorkflowStage, hook: StageHook) -> None:
        """注册阶段退出钩子.

        Args:
            stage: 阶段
            hook: 钩子函数
        """
        self._on_exit_hooks[stage].append(hook)

    async def _run_enter_hooks(self, context: StageContext) -> None:
        """执行阶段进入钩子.

        Args:
            context: 阶段上下文
        """
        for hook in self._on_enter_hooks[context.stage]:
            try:
                await hook(context)
            except Exception as e:
                context.warnings.append(f"进入钩子执行失败: {e}")

    async def _run_exit_hooks(self, context: StageContext) -> None:
        """执行阶段退出钩子.

        Args:
            context: 阶段上下文
        """
        for hook in self._on_exit_hooks[context.stage]:
            try:
                await hook(context)
            except Exception as e:
                context.warnings.append(f"退出钩子执行失败: {e}")

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def get_stage_context(self, stage: WorkflowStage) -> StageContext | None:
        """获取指定阶段的上下文.

        Args:
            stage: 阶段

        Returns:
            阶段上下文，如果不存在则返回 None
        """
        return self._stage_contexts.get(stage)

    def get_transition_history(
        self,
        stage: WorkflowStage | None = None,
    ) -> list[StageTransition]:
        """获取转换历史.

        Args:
            stage: 可选的阶段过滤

        Returns:
            转换历史列表
        """
        if stage is None:
            return list(self._transitions)

        return [
            t for t in self._transitions if t.from_stage == stage or t.to_stage == stage
        ]

    def to_dict(self) -> dict[str, Any]:
        """将阶段管理器状态转换为字典.

        Returns:
            状态字典
        """
        return {
            "workflow_id": self.workflow_id,
            "current_stage": self._current_stage.value if self._current_stage else None,
            "stage_status": {
                stage.value: status.value
                for stage, status in self._stage_status.items()
            },
            "progress": self.progress,
            "is_completed": self.is_completed,
            "transition_count": len(self._transitions),
        }

    def __repr__(self) -> str:
        """返回阶段管理器的简洁表示."""
        stage_str = self._current_stage.value if self._current_stage else "None"
        return (
            f"StageManager(workflow_id={self.workflow_id!r}, "
            f"current_stage={stage_str}, progress={self.progress:.1%})"
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "WorkflowStage",
    "StageStatus",
    "StageTransition",
    "StageContext",
    "StageManager",
    "StageHook",
]
