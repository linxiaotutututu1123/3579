"""角色分配模块。

本模块提供智能角色分配功能，用于为团队成员分配合适的任务和职责。

核心功能：
    - RoleAssignment: 角色分配结果数据结构
    - RoleAssigner: 角色分配器，根据任务和成员能力进行智能分配
    - assign_roles: 为团队成员分配角色和任务

设计原则：
    - 能力与任务的最优匹配
    - 负载均衡，避免单点过载
    - 支持角色优先级和约束条件
    - 动态调整和重新分配

Example:
    >>> from chairman_agents.team import RoleAssigner, RoleAssignment
    >>> assigner = RoleAssigner()
    >>> assignments = await assigner.assign_roles(
    ...     team=team,
    ...     tasks=tasks,
    ...     strategy=AssignmentStrategy.BALANCED
    ... )
    >>> for assignment in assignments:
    ...     print(f"{assignment.member_name} -> {assignment.task_title}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..core.types import (
    AgentCapability,
    AgentId,
    AgentRole,
    ExpertiseLevel,
    Task,
    TaskId,
    TaskPriority,
    generate_id,
)

if TYPE_CHECKING:
    from .team_builder import Team, TeamMember


# =============================================================================
# 日志配置
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举定义
# =============================================================================


class AssignmentStrategy(Enum):
    """分配策略枚举。

    定义不同的角色分配策略以适应不同场景。

    Attributes:
        GREEDY: 贪婪策略，优先分配给最匹配的成员
        BALANCED: 平衡策略，考虑负载均衡
        ROUND_ROBIN: 轮询策略，依次分配
        PRIORITY_FIRST: 优先级优先，按任务优先级分配
        EXPERTISE_MATCH: 专业匹配，优先匹配专业水平
    """

    GREEDY = "greedy"
    """贪婪策略 - 优先分配给最匹配的成员"""

    BALANCED = "balanced"
    """平衡策略 - 考虑负载均衡"""

    ROUND_ROBIN = "round_robin"
    """轮询策略 - 依次分配"""

    PRIORITY_FIRST = "priority_first"
    """优先级优先 - 按任务优先级分配"""

    EXPERTISE_MATCH = "expertise_match"
    """专业匹配 - 优先匹配专业水平"""


class AssignmentStatus(Enum):
    """分配状态枚举。

    Attributes:
        PENDING: 待确认
        CONFIRMED: 已确认
        IN_PROGRESS: 进行中
        COMPLETED: 已完成
        REASSIGNED: 已重新分配
        CANCELLED: 已取消
    """

    PENDING = "pending"
    """待确认"""

    CONFIRMED = "confirmed"
    """已确认"""

    IN_PROGRESS = "in_progress"
    """进行中"""

    COMPLETED = "completed"
    """已完成"""

    REASSIGNED = "reassigned"
    """已重新分配"""

    CANCELLED = "cancelled"
    """已取消"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class RoleAssignment:
    """角色分配结果。

    表示一个成员到任务/角色的分配结果。

    Attributes:
        id: 分配唯一标识符
        member_id: 成员智能体ID
        member_name: 成员名称
        member_role: 成员角色
        task_id: 分配的任务ID
        task_title: 任务标题
        assigned_role: 分配的角色职责
        responsibilities: 具体职责列表
        match_score: 匹配分数
        priority: 分配优先级
        status: 分配状态
        assigned_at: 分配时间
        confirmed_at: 确认时间
        estimated_hours: 预估工时
        notes: 备注

    Example:
        >>> assignment = RoleAssignment(
        ...     member_id="agent_123",
        ...     member_name="Senior Developer",
        ...     task_id="task_456",
        ...     task_title="实现用户认证",
        ...     assigned_role="主开发",
        ...     match_score=0.95
        ... )
    """

    id: str = field(default_factory=lambda: generate_id("assign"))
    """分配唯一标识符"""

    member_id: AgentId = ""
    """成员智能体ID"""

    member_name: str = ""
    """成员名称"""

    member_role: AgentRole | None = None
    """成员角色"""

    task_id: TaskId = ""
    """分配的任务ID"""

    task_title: str = ""
    """任务标题"""

    assigned_role: str = ""
    """分配的角色职责"""

    responsibilities: list[str] = field(default_factory=list)
    """具体职责列表"""

    assigned_capabilities: list[AgentCapability] = field(default_factory=list)
    """分配的能力职责"""

    match_score: float = 0.0
    """匹配分数 (0.0-1.0)"""

    priority: int = 3
    """分配优先级 (1-5，1最高)"""

    status: AssignmentStatus = AssignmentStatus.PENDING
    """分配状态"""

    assigned_at: datetime = field(default_factory=datetime.now)
    """分配时间"""

    confirmed_at: datetime | None = None
    """确认时间"""

    estimated_hours: float = 0.0
    """预估工时"""

    notes: str = ""
    """备注"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    # =========================================================================
    # 属性访问器
    # =========================================================================

    @property
    def is_confirmed(self) -> bool:
        """检查是否已确认。"""
        return self.status in (
            AssignmentStatus.CONFIRMED,
            AssignmentStatus.IN_PROGRESS,
            AssignmentStatus.COMPLETED,
        )

    @property
    def is_active(self) -> bool:
        """检查是否活跃。"""
        return self.status in (
            AssignmentStatus.CONFIRMED,
            AssignmentStatus.IN_PROGRESS,
        )

    @property
    def is_completed(self) -> bool:
        """检查是否已完成。"""
        return self.status == AssignmentStatus.COMPLETED

    # =========================================================================
    # 状态管理
    # =========================================================================

    def confirm(self) -> None:
        """确认分配。"""
        self.status = AssignmentStatus.CONFIRMED
        self.confirmed_at = datetime.now()
        logger.debug("确认分配: id=%s, member=%s", self.id, self.member_id)

    def start(self) -> None:
        """开始执行。"""
        if self.status == AssignmentStatus.PENDING:
            self.confirm()
        self.status = AssignmentStatus.IN_PROGRESS
        logger.debug("开始执行: id=%s", self.id)

    def complete(self) -> None:
        """完成分配。"""
        self.status = AssignmentStatus.COMPLETED
        logger.debug("完成分配: id=%s", self.id)

    def reassign(self, new_member_id: AgentId, new_member_name: str) -> None:
        """重新分配。

        Args:
            new_member_id: 新成员ID
            new_member_name: 新成员名称
        """
        old_member = self.member_id
        self.member_id = new_member_id
        self.member_name = new_member_name
        self.status = AssignmentStatus.REASSIGNED
        self.assigned_at = datetime.now()
        logger.info(
            "重新分配: id=%s, from=%s, to=%s",
            self.id, old_member, new_member_id
        )

    def cancel(self) -> None:
        """取消分配。"""
        self.status = AssignmentStatus.CANCELLED
        logger.debug("取消分配: id=%s", self.id)

    def __repr__(self) -> str:
        """返回分配的简洁表示。"""
        return (
            f"RoleAssignment(member={self.member_name!r}, "
            f"task={self.task_title!r}, score={self.match_score:.2f})"
        )


@dataclass
class AssignmentPlan:
    """分配计划。

    表示一组角色分配的完整计划。

    Attributes:
        id: 计划唯一标识符
        team_id: 团队ID
        assignments: 分配列表
        strategy: 使用的分配策略
        created_at: 创建时间
        total_score: 总匹配分数
        coverage: 能力覆盖率
        balance_score: 负载均衡分数
        unassigned_tasks: 未分配的任务ID列表
        warnings: 警告信息列表
    """

    id: str = field(default_factory=lambda: generate_id("plan"))
    """计划唯一标识符"""

    team_id: str = ""
    """团队ID"""

    assignments: list[RoleAssignment] = field(default_factory=list)
    """分配列表"""

    strategy: AssignmentStrategy = AssignmentStrategy.BALANCED
    """使用的分配策略"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    total_score: float = 0.0
    """总匹配分数"""

    coverage: float = 0.0
    """能力覆盖率 (0.0-1.0)"""

    balance_score: float = 0.0
    """负载均衡分数 (0.0-1.0)"""

    unassigned_tasks: list[TaskId] = field(default_factory=list)
    """未分配的任务ID列表"""

    warnings: list[str] = field(default_factory=list)
    """警告信息列表"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    # =========================================================================
    # 属性访问器
    # =========================================================================

    @property
    def assignment_count(self) -> int:
        """获取分配数量。"""
        return len(self.assignments)

    @property
    def is_complete(self) -> bool:
        """检查是否所有任务都已分配。"""
        return len(self.unassigned_tasks) == 0

    @property
    def average_score(self) -> float:
        """计算平均匹配分数。"""
        if not self.assignments:
            return 0.0
        return sum(a.match_score for a in self.assignments) / len(self.assignments)

    @property
    def confirmed_count(self) -> int:
        """获取已确认的分配数量。"""
        return sum(1 for a in self.assignments if a.is_confirmed)

    # =========================================================================
    # 查询方法
    # =========================================================================

    def get_assignments_for_member(self, member_id: AgentId) -> list[RoleAssignment]:
        """获取成员的所有分配。

        Args:
            member_id: 成员ID

        Returns:
            该成员的分配列表
        """
        return [a for a in self.assignments if a.member_id == member_id]

    def get_assignment_for_task(self, task_id: TaskId) -> RoleAssignment | None:
        """获取任务的分配。

        Args:
            task_id: 任务ID

        Returns:
            分配结果，不存在返回 None
        """
        for assignment in self.assignments:
            if assignment.task_id == task_id:
                return assignment
        return None

    def get_member_load(self, member_id: AgentId) -> float:
        """获取成员的负载。

        Args:
            member_id: 成员ID

        Returns:
            负载（预估工时总和）
        """
        member_assignments = self.get_assignments_for_member(member_id)
        return sum(a.estimated_hours for a in member_assignments)

    def confirm_all(self) -> None:
        """确认所有分配。"""
        for assignment in self.assignments:
            if assignment.status == AssignmentStatus.PENDING:
                assignment.confirm()


# =============================================================================
# 角色分配器
# =============================================================================


class RoleAssigner:
    """角色分配器。

    根据任务需求和成员能力进行智能角色分配，支持多种分配策略。

    核心功能：
        - 智能任务分配
        - 负载均衡
        - 能力匹配优化
        - 分配计划生成

    Attributes:
        default_strategy: 默认分配策略
        max_load_per_member: 每个成员的最大负载

    Example:
        >>> assigner = RoleAssigner()
        >>> plan = await assigner.assign_roles(
        ...     team=development_team,
        ...     tasks=[task1, task2, task3],
        ...     strategy=AssignmentStrategy.BALANCED
        ... )
        >>> print(f"分配计划: {plan.assignment_count} 项分配")
    """

    def __init__(
        self,
        default_strategy: AssignmentStrategy = AssignmentStrategy.BALANCED,
        max_load_per_member: float = 40.0,  # 每周工时
    ) -> None:
        """初始化角色分配器。

        Args:
            default_strategy: 默认分配策略
            max_load_per_member: 每个成员的最大负载（小时）
        """
        self._default_strategy = default_strategy
        self._max_load = max_load_per_member

        logger.info(
            "初始化角色分配器: strategy=%s, max_load=%.1f",
            default_strategy.value, max_load_per_member
        )

    # =========================================================================
    # 主要分配方法
    # =========================================================================

    async def assign_roles(
        self,
        team: Team,
        tasks: list[Task],
        *,
        strategy: AssignmentStrategy | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> AssignmentPlan:
        """为团队成员分配角色和任务。

        根据任务需求和成员能力，智能分配角色和任务。

        Args:
            team: 目标团队
            tasks: 待分配的任务列表
            strategy: 分配策略，默认使用分配器的默认策略
            constraints: 约束条件

        Returns:
            分配计划

        Example:
            >>> plan = await assigner.assign_roles(
            ...     team=my_team,
            ...     tasks=[review_task, dev_task],
            ...     strategy=AssignmentStrategy.BALANCED
            ... )
        """
        strategy = strategy or self._default_strategy
        constraints = constraints or {}

        logger.info(
            "开始角色分配: team=%s, tasks=%d, strategy=%s",
            team.id, len(tasks), strategy.value
        )

        # 创建分配计划
        plan = AssignmentPlan(
            team_id=team.id,
            strategy=strategy,
        )

        if not team.members:
            plan.warnings.append("团队没有成员")
            plan.unassigned_tasks = [t.id for t in tasks]
            return plan

        if not tasks:
            plan.warnings.append("没有待分配的任务")
            return plan

        # 按优先级排序任务
        sorted_tasks = self._sort_tasks(tasks, strategy)

        # 初始化成员负载
        member_loads: dict[AgentId, float] = {m.agent_id: 0.0 for m in team.members}

        # 执行分配
        for task in sorted_tasks:
            assignment = await self._assign_task(
                task=task,
                team=team,
                member_loads=member_loads,
                strategy=strategy,
                constraints=constraints,
            )

            if assignment:
                plan.assignments.append(assignment)
                member_loads[assignment.member_id] += assignment.estimated_hours
            else:
                plan.unassigned_tasks.append(task.id)
                plan.warnings.append(f"任务 '{task.title}' 无法分配")

        # 计算计划指标
        self._calculate_plan_metrics(plan, team, tasks)

        logger.info(
            "角色分配完成: assignments=%d, unassigned=%d, score=%.2f",
            plan.assignment_count,
            len(plan.unassigned_tasks),
            plan.average_score
        )

        return plan

    async def assign_single(
        self,
        task: Task,
        team: Team,
        *,
        preferred_member: AgentId | None = None,
        excluded_members: list[AgentId] | None = None,
    ) -> RoleAssignment | None:
        """分配单个任务。

        为单个任务选择最合适的团队成员。

        Args:
            task: 待分配的任务
            team: 目标团队
            preferred_member: 优先成员ID
            excluded_members: 排除的成员ID列表

        Returns:
            分配结果，无法分配时返回 None
        """
        excluded_members = excluded_members or []

        logger.debug("分配单个任务: task=%s", task.id)

        # 获取候选成员
        candidates = [
            m for m in team.members
            if m.agent_id not in excluded_members
        ]

        if not candidates:
            logger.warning("没有可用的候选成员")
            return None

        # 如果有优先成员且可用
        if preferred_member:
            for member in candidates:
                if member.agent_id == preferred_member:
                    return self._create_assignment(task, member, score=0.9)

        # 计算匹配分数并选择最佳成员
        scored_candidates = [
            (member, self._calculate_member_score(member, task))
            for member in candidates
        ]
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if scored_candidates:
            best_member, best_score = scored_candidates[0]
            if best_score >= 0.3:  # 最低匹配阈值
                return self._create_assignment(task, best_member, score=best_score)

        return None

    async def reassign(
        self,
        assignment: RoleAssignment,
        team: Team,
        reason: str = "",
    ) -> RoleAssignment | None:
        """重新分配任务。

        将已分配的任务重新分配给其他成员。

        Args:
            assignment: 原分配
            team: 团队
            reason: 重新分配原因

        Returns:
            新的分配结果，无法重新分配时返回 None
        """
        logger.info(
            "重新分配任务: assignment=%s, reason=%s",
            assignment.id, reason
        )

        # 找到原任务
        original_task = None
        for member in team.members:
            if member.agent_id == assignment.member_id:
                # 构造任务对象
                original_task = Task(
                    id=assignment.task_id,
                    title=assignment.task_title,
                    required_capabilities=assignment.assigned_capabilities,
                )
                break

        if not original_task:
            logger.warning("找不到原任务")
            return None

        # 排除原成员，重新分配
        new_assignment = await self.assign_single(
            task=original_task,
            team=team,
            excluded_members=[assignment.member_id],
        )

        if new_assignment:
            # 取消原分配
            assignment.cancel()
            assignment.notes = f"重新分配原因: {reason}"
            new_assignment.metadata["previous_assignment_id"] = assignment.id
            new_assignment.metadata["reassign_reason"] = reason

        return new_assignment

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _sort_tasks(
        self,
        tasks: list[Task],
        strategy: AssignmentStrategy,
    ) -> list[Task]:
        """按策略排序任务。

        Args:
            tasks: 任务列表
            strategy: 分配策略

        Returns:
            排序后的任务列表
        """
        if strategy == AssignmentStrategy.PRIORITY_FIRST:
            # 按优先级排序（优先级值越小越高）
            return sorted(tasks, key=lambda t: t.priority.value)
        elif strategy == AssignmentStrategy.EXPERTISE_MATCH:
            # 按复杂度排序（复杂任务优先，以便优先分配给高水平成员）
            return sorted(tasks, key=lambda t: t.complexity, reverse=True)
        else:
            # 默认按优先级排序
            return sorted(tasks, key=lambda t: t.priority.value)

    async def _assign_task(
        self,
        task: Task,
        team: Team,
        member_loads: dict[AgentId, float],
        strategy: AssignmentStrategy,
        constraints: dict[str, Any],
    ) -> RoleAssignment | None:
        """分配单个任务到团队成员。

        Args:
            task: 待分配任务
            team: 目标团队
            member_loads: 成员当前负载
            strategy: 分配策略
            constraints: 约束条件

        Returns:
            分配结果，无法分配时返回 None
        """
        # 获取可用成员（考虑负载）
        available_members = [
            m for m in team.members
            if member_loads.get(m.agent_id, 0) + task.estimated_hours <= self._max_load
        ]

        if not available_members:
            # 放宽负载限制
            available_members = list(team.members)

        if not available_members:
            return None

        # 计算匹配分数
        scored_members = [
            (member, self._calculate_member_score(member, task))
            for member in available_members
        ]

        # 根据策略调整分数
        if strategy == AssignmentStrategy.BALANCED:
            # 负载均衡：降低高负载成员的分数
            scored_members = [
                (m, score * (1 - member_loads.get(m.agent_id, 0) / self._max_load * 0.5))
                for m, score in scored_members
            ]
        elif strategy == AssignmentStrategy.ROUND_ROBIN:
            # 轮询：选择负载最低的成员
            scored_members = [
                (m, 1.0 - member_loads.get(m.agent_id, 0) / self._max_load)
                for m, _ in scored_members
            ]

        # 排序并选择
        scored_members.sort(key=lambda x: x[1], reverse=True)

        if scored_members:
            best_member, best_score = scored_members[0]
            return self._create_assignment(task, best_member, score=best_score)

        return None

    def _calculate_member_score(
        self,
        member: TeamMember,
        task: Task,
    ) -> float:
        """计算成员与任务的匹配分数。

        Args:
            member: 团队成员
            task: 目标任务

        Returns:
            匹配分数 (0.0-1.0)
        """
        score = 0.0

        # 能力匹配 (权重: 40%)
        if task.required_capabilities:
            matched = sum(
                1 for cap in task.required_capabilities
                if member.can_handle(cap)
            )
            cap_score = matched / len(task.required_capabilities)
            score += cap_score * 0.4
        else:
            score += 0.2  # 无特定能力要求时给基础分

        # 角色匹配 (权重: 30%)
        if task.required_role:
            if member.role == task.required_role:
                score += 0.3
            elif self._is_compatible_role(member.role, task.required_role):
                score += 0.15

        # 专业水平 (权重: 20%)
        if task.min_expertise_level:
            if member.expertise_level.value >= task.min_expertise_level.value:
                expertise_bonus = min(
                    (member.expertise_level.value - task.min_expertise_level.value + 1) * 0.05,
                    0.2
                )
                score += expertise_bonus

        # 可用性 (权重: 10%)
        score += member.effective_availability * 0.1

        return min(score, 1.0)

    def _is_compatible_role(self, member_role: AgentRole, task_role: AgentRole) -> bool:
        """检查角色是否兼容。

        Args:
            member_role: 成员角色
            task_role: 任务所需角色

        Returns:
            是否兼容
        """
        # 定义角色兼容性
        compatibility = {
            AgentRole.FULLSTACK_ENGINEER: [
                AgentRole.BACKEND_ENGINEER,
                AgentRole.FRONTEND_ENGINEER,
            ],
            AgentRole.TECH_LEAD: [
                AgentRole.BACKEND_ENGINEER,
                AgentRole.CODE_REVIEWER,
            ],
            AgentRole.QA_LEAD: [
                AgentRole.QA_ENGINEER,
            ],
            AgentRole.SYSTEM_ARCHITECT: [
                AgentRole.SOLUTION_ARCHITECT,
            ],
        }

        compatible_roles = compatibility.get(member_role, [])
        return task_role in compatible_roles

    def _create_assignment(
        self,
        task: Task,
        member: TeamMember,
        score: float,
    ) -> RoleAssignment:
        """创建分配结果。

        Args:
            task: 任务
            member: 成员
            score: 匹配分数

        Returns:
            分配结果
        """
        # 确定角色职责
        assigned_role = self._determine_assigned_role(member, task)

        # 确定具体职责
        responsibilities = self._determine_responsibilities(member, task)

        return RoleAssignment(
            member_id=member.agent_id,
            member_name=member.name,
            member_role=member.role,
            task_id=task.id,
            task_title=task.title,
            assigned_role=assigned_role,
            responsibilities=responsibilities,
            assigned_capabilities=list(task.required_capabilities),
            match_score=score,
            priority=task.priority.value,
            estimated_hours=task.estimated_hours,
        )

    def _determine_assigned_role(
        self,
        member: TeamMember,
        task: Task,
    ) -> str:
        """确定分配的角色职责。

        Args:
            member: 成员
            task: 任务

        Returns:
            角色职责描述
        """
        role_map = {
            AgentRole.PROJECT_MANAGER: "项目协调员",
            AgentRole.TECH_DIRECTOR: "技术决策者",
            AgentRole.SYSTEM_ARCHITECT: "架构师",
            AgentRole.SOLUTION_ARCHITECT: "方案设计师",
            AgentRole.TECH_LEAD: "技术负责人",
            AgentRole.BACKEND_ENGINEER: "后端开发工程师",
            AgentRole.FRONTEND_ENGINEER: "前端开发工程师",
            AgentRole.FULLSTACK_ENGINEER: "全栈开发工程师",
            AgentRole.QA_ENGINEER: "质量工程师",
            AgentRole.QA_LEAD: "测试负责人",
            AgentRole.CODE_REVIEWER: "代码审查员",
            AgentRole.PERFORMANCE_ENGINEER: "性能工程师",
            AgentRole.SECURITY_ARCHITECT: "安全架构师",
            AgentRole.DEVOPS_ENGINEER: "DevOps工程师",
            AgentRole.SRE_ENGINEER: "可靠性工程师",
            AgentRole.TECH_WRITER: "技术文档工程师",
        }

        base_role = role_map.get(member.role, "团队成员")

        # 根据任务类型调整
        if task.type == "review":
            return f"{base_role} (审查)"
        elif task.type == "development":
            return f"{base_role} (开发)"
        elif task.type == "testing":
            return f"{base_role} (测试)"

        return base_role

    def _determine_responsibilities(
        self,
        member: TeamMember,
        task: Task,
    ) -> list[str]:
        """确定具体职责。

        Args:
            member: 成员
            task: 任务

        Returns:
            职责列表
        """
        responsibilities: list[str] = []

        # 基于任务类型
        if task.type == "development":
            responsibilities.append("实现功能代码")
            responsibilities.append("编写单元测试")
        elif task.type == "review":
            responsibilities.append("审查代码质量")
            responsibilities.append("提供改进建议")
        elif task.type == "testing":
            responsibilities.append("设计测试用例")
            responsibilities.append("执行测试")
        elif task.type == "documentation":
            responsibilities.append("编写技术文档")

        # 基于能力
        for cap in task.required_capabilities:
            if cap == AgentCapability.CODE_REVIEW:
                responsibilities.append("代码审查")
            elif cap == AgentCapability.SECURITY_ANALYSIS:
                responsibilities.append("安全分析")
            elif cap == AgentCapability.PERFORMANCE_TESTING:
                responsibilities.append("性能测试")

        # 去重
        return list(dict.fromkeys(responsibilities))

    def _calculate_plan_metrics(
        self,
        plan: AssignmentPlan,
        team: Team,
        tasks: list[Task],
    ) -> None:
        """计算分配计划的指标。

        Args:
            plan: 分配计划
            team: 团队
            tasks: 任务列表
        """
        if not plan.assignments:
            return

        # 计算总分数
        plan.total_score = sum(a.match_score for a in plan.assignments)

        # 计算覆盖率
        assigned_task_count = len(plan.assignments)
        total_task_count = len(tasks)
        plan.coverage = assigned_task_count / total_task_count if total_task_count > 0 else 0.0

        # 计算负载均衡分数
        member_loads: dict[AgentId, float] = {}
        for assignment in plan.assignments:
            member_loads[assignment.member_id] = (
                member_loads.get(assignment.member_id, 0) + assignment.estimated_hours
            )

        if member_loads:
            loads = list(member_loads.values())
            avg_load = sum(loads) / len(loads)
            if avg_load > 0:
                variance = sum((l - avg_load) ** 2 for l in loads) / len(loads)
                std_dev = variance ** 0.5
                # 标准差越小，均衡分数越高
                plan.balance_score = max(0, 1 - std_dev / avg_load)
            else:
                plan.balance_score = 1.0

    # =========================================================================
    # 便捷方法
    # =========================================================================

    async def auto_assign(
        self,
        team: Team,
        tasks: list[Task],
    ) -> AssignmentPlan:
        """自动分配任务。

        使用默认策略自动完成任务分配。

        Args:
            team: 目标团队
            tasks: 待分配任务

        Returns:
            分配计划
        """
        return await self.assign_roles(
            team=team,
            tasks=tasks,
            strategy=self._default_strategy,
        )

    async def optimize_assignments(
        self,
        plan: AssignmentPlan,
        team: Team,
    ) -> AssignmentPlan:
        """优化分配计划。

        尝试优化现有分配计划以提高整体效率。

        Args:
            plan: 原分配计划
            team: 团队

        Returns:
            优化后的分配计划
        """
        logger.info("优化分配计划: plan=%s", plan.id)

        # 检查是否有低分配分
        low_score_threshold = 0.5
        low_score_assignments = [
            a for a in plan.assignments
            if a.match_score < low_score_threshold
        ]

        for assignment in low_score_assignments:
            # 尝试找到更好的分配
            task = Task(
                id=assignment.task_id,
                title=assignment.task_title,
                required_capabilities=assignment.assigned_capabilities,
            )

            better_assignment = await self.assign_single(
                task=task,
                team=team,
                excluded_members=[assignment.member_id],
            )

            if better_assignment and better_assignment.match_score > assignment.match_score:
                # 替换为更好的分配
                plan.assignments.remove(assignment)
                plan.assignments.append(better_assignment)
                logger.debug(
                    "优化分配: task=%s, old_score=%.2f, new_score=%.2f",
                    task.id, assignment.match_score, better_assignment.match_score
                )

        # 重新计算指标
        # 注意：这里需要获取原始任务列表，简化处理
        plan.total_score = sum(a.match_score for a in plan.assignments)

        return plan


# =============================================================================
# 便捷函数
# =============================================================================


async def assign_roles(
    team: Team,
    tasks: list[Task],
    strategy: AssignmentStrategy = AssignmentStrategy.BALANCED,
) -> AssignmentPlan:
    """便捷函数：为团队分配角色。

    Args:
        team: 目标团队
        tasks: 待分配任务
        strategy: 分配策略

    Returns:
        分配计划

    Example:
        >>> plan = await assign_roles(team, tasks)
        >>> for a in plan.assignments:
        ...     print(f"{a.member_name} -> {a.task_title}")
    """
    assigner = RoleAssigner(default_strategy=strategy)
    return await assigner.assign_roles(team, tasks, strategy=strategy)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 枚举
    "AssignmentStrategy",
    "AssignmentStatus",
    # 数据类
    "RoleAssignment",
    "AssignmentPlan",
    # 分配器
    "RoleAssigner",
    # 便捷函数
    "assign_roles",
]
