"""团队构建器模块。

本模块提供团队构建功能，用于根据任务需求动态组建专家团队。

核心功能：
    - Team: 团队数据结构，包含团队成员和配置信息
    - TeamBuilder: 团队构建器，根据任务需求选择合适的专家
    - select_experts: 智能选择最适合任务的专家组合

设计原则：
    - 基于任务需求自动匹配专家能力
    - 支持团队规模动态调整
    - 考虑专家可用性和负载均衡
    - 优化团队协作效率

Example:
    >>> from chairman_agents.team import TeamBuilder, Team
    >>> builder = TeamBuilder(agent_registry)
    >>> team = await builder.build_team(
    ...     task=task,
    ...     min_experts=2,
    ...     max_experts=5
    ... )
    >>> print(f"团队成员: {[m.name for m in team.members]}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..core.types import (
    AgentCapability,
    AgentId,
    AgentProfile,
    AgentRole,
    ExpertiseLevel,
    Task,
    TaskPriority,
    generate_id,
)

if TYPE_CHECKING:
    from ..agents.base import BaseExpertAgent


# =============================================================================
# 日志配置
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class AgentRegistryProtocol(Protocol):
    """智能体注册表协议。

    定义智能体发现和管理的接口。
    """

    def find_agents_by_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> list[AgentId]:
        """根据能力查找智能体。

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            符合条件的智能体ID列表
        """
        ...

    def find_agents_by_role(self, role: AgentRole) -> list[AgentId]:
        """根据角色查找智能体。

        Args:
            role: 目标角色

        Returns:
            具有该角色的智能体ID列表
        """
        ...

    def get_agent_profile(self, agent_id: AgentId) -> AgentProfile | None:
        """获取智能体配置。

        Args:
            agent_id: 智能体ID

        Returns:
            智能体配置，不存在返回 None
        """
        ...

    def get_agent(self, agent_id: AgentId) -> BaseExpertAgent | None:
        """获取智能体实例。

        Args:
            agent_id: 智能体ID

        Returns:
            智能体实例，不存在返回 None
        """
        ...


# =============================================================================
# 枚举定义
# =============================================================================


class TeamFormationStrategy(Enum):
    """团队组建策略枚举。

    定义不同的团队组建策略以适应不同场景。

    Attributes:
        MINIMAL: 最小团队，只选择核心必需的专家
        BALANCED: 平衡团队，兼顾能力覆盖和团队规模
        COMPREHENSIVE: 全面团队，尽可能覆盖所有相关能力
        SPECIALIZED: 专业团队，优先选择特定领域的顶尖专家
    """

    MINIMAL = "minimal"
    """最小团队 - 只选择核心必需的专家"""

    BALANCED = "balanced"
    """平衡团队 - 兼顾能力覆盖和团队规模"""

    COMPREHENSIVE = "comprehensive"
    """全面团队 - 尽可能覆盖所有相关能力"""

    SPECIALIZED = "specialized"
    """专业团队 - 优先选择特定领域的顶尖专家"""


class TeamStatus(Enum):
    """团队状态枚举。

    Attributes:
        FORMING: 组建中
        READY: 就绪
        ACTIVE: 活跃
        PAUSED: 暂停
        DISBANDED: 已解散
    """

    FORMING = "forming"
    """组建中 - 团队正在组建"""

    READY = "ready"
    """就绪 - 团队已组建完成，准备开始工作"""

    ACTIVE = "active"
    """活跃 - 团队正在执行任务"""

    PAUSED = "paused"
    """暂停 - 团队暂时停止工作"""

    DISBANDED = "disbanded"
    """已解散 - 团队已完成使命或被解散"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class TeamMember:
    """团队成员。

    表示团队中的一个成员，包含智能体信息和团队角色。

    Attributes:
        agent_id: 智能体ID
        profile: 智能体配置
        team_role: 在团队中的角色
        is_lead: 是否为团队负责人
        assigned_capabilities: 分配的能力职责
        availability: 可用性 (0.0-1.0)
        current_load: 当前负载 (0.0-1.0)
        joined_at: 加入时间
    """

    agent_id: AgentId
    """智能体ID"""

    profile: AgentProfile
    """智能体配置"""

    team_role: str = ""
    """在团队中的角色描述"""

    is_lead: bool = False
    """是否为团队负责人"""

    assigned_capabilities: list[AgentCapability] = field(default_factory=list)
    """分配的能力职责"""

    availability: float = 1.0
    """可用性 (0.0-1.0)"""

    current_load: float = 0.0
    """当前负载 (0.0-1.0)"""

    joined_at: datetime = field(default_factory=datetime.now)
    """加入时间"""

    @property
    def name(self) -> str:
        """获取成员名称。"""
        return self.profile.name

    @property
    def role(self) -> AgentRole:
        """获取成员角色。"""
        return self.profile.role

    @property
    def expertise_level(self) -> ExpertiseLevel:
        """获取专业水平。"""
        return self.profile.expertise_level

    @property
    def effective_availability(self) -> float:
        """计算有效可用性。"""
        return self.availability * (1.0 - self.current_load)

    def can_handle(self, capability: AgentCapability, min_level: int = 1) -> bool:
        """检查是否能处理指定能力。

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            是否能处理
        """
        return self.profile.has_capability(capability, min_level)


@dataclass
class TeamConfiguration:
    """团队配置。

    定义团队的配置参数和约束条件。

    Attributes:
        min_size: 最小团队规模
        max_size: 最大团队规模
        required_roles: 必需的角色列表
        required_capabilities: 必需的能力列表
        preferred_expertise_level: 优选专业水平
        formation_strategy: 组建策略
        allow_multi_role: 是否允许一人多角色
        balance_load: 是否进行负载均衡
    """

    min_size: int = 1
    """最小团队规模"""

    max_size: int = 10
    """最大团队规模"""

    required_roles: list[AgentRole] = field(default_factory=list)
    """必需的角色列表"""

    required_capabilities: list[AgentCapability] = field(default_factory=list)
    """必需的能力列表"""

    preferred_expertise_level: ExpertiseLevel = ExpertiseLevel.SENIOR
    """优选专业水平"""

    formation_strategy: TeamFormationStrategy = TeamFormationStrategy.BALANCED
    """组建策略"""

    allow_multi_role: bool = True
    """是否允许一人多角色"""

    balance_load: bool = True
    """是否进行负载均衡"""


@dataclass
class Team:
    """团队数据结构。

    表示一个专家团队，包含成员列表、配置和状态信息。

    Attributes:
        id: 团队唯一标识符
        name: 团队名称
        description: 团队描述
        members: 团队成员列表
        lead_id: 团队负责人ID
        status: 团队状态
        configuration: 团队配置
        task_id: 关联的任务ID
        created_at: 创建时间
        metadata: 附加元数据

    Example:
        >>> team = Team(
        ...     name="代码审查团队",
        ...     members=[member1, member2],
        ...     lead_id=member1.agent_id
        ... )
        >>> print(f"团队规模: {team.size}")
        >>> print(f"覆盖能力: {team.covered_capabilities}")
    """

    id: str = field(default_factory=lambda: generate_id("team"))
    """团队唯一标识符"""

    name: str = ""
    """团队名称"""

    description: str = ""
    """团队描述"""

    members: list[TeamMember] = field(default_factory=list)
    """团队成员列表"""

    lead_id: AgentId | None = None
    """团队负责人ID"""

    status: TeamStatus = TeamStatus.FORMING
    """团队状态"""

    configuration: TeamConfiguration = field(default_factory=TeamConfiguration)
    """团队配置"""

    task_id: str | None = None
    """关联的任务ID"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    # =========================================================================
    # 属性访问器
    # =========================================================================

    @property
    def size(self) -> int:
        """获取团队规模。"""
        return len(self.members)

    @property
    def lead(self) -> TeamMember | None:
        """获取团队负责人。"""
        if self.lead_id is None:
            return None
        return self.get_member(self.lead_id)

    @property
    def is_ready(self) -> bool:
        """检查团队是否就绪。"""
        return self.status in (TeamStatus.READY, TeamStatus.ACTIVE)

    @property
    def member_ids(self) -> list[AgentId]:
        """获取所有成员ID。"""
        return [m.agent_id for m in self.members]

    @property
    def covered_roles(self) -> set[AgentRole]:
        """获取团队覆盖的所有角色。"""
        return {m.role for m in self.members}

    @property
    def covered_capabilities(self) -> set[AgentCapability]:
        """获取团队覆盖的所有能力。"""
        capabilities: set[AgentCapability] = set()
        for member in self.members:
            capabilities.update(member.profile.capabilities)
        return capabilities

    @property
    def average_expertise_level(self) -> float:
        """计算平均专业水平。"""
        if not self.members:
            return 0.0
        return sum(m.expertise_level.value for m in self.members) / len(self.members)

    @property
    def total_capacity(self) -> float:
        """计算团队总容量。"""
        return sum(m.effective_availability for m in self.members)

    # =========================================================================
    # 成员管理
    # =========================================================================

    def get_member(self, agent_id: AgentId) -> TeamMember | None:
        """获取指定成员。

        Args:
            agent_id: 智能体ID

        Returns:
            团队成员，不存在返回 None
        """
        for member in self.members:
            if member.agent_id == agent_id:
                return member
        return None

    def add_member(self, member: TeamMember) -> None:
        """添加团队成员。

        Args:
            member: 要添加的成员
        """
        if member.agent_id not in self.member_ids:
            self.members.append(member)
            logger.info(
                "添加团队成员: team=%s, member=%s, role=%s",
                self.id, member.agent_id, member.role.value
            )

    def remove_member(self, agent_id: AgentId) -> bool:
        """移除团队成员。

        Args:
            agent_id: 要移除的成员ID

        Returns:
            是否成功移除
        """
        for i, member in enumerate(self.members):
            if member.agent_id == agent_id:
                del self.members[i]
                logger.info("移除团队成员: team=%s, member=%s", self.id, agent_id)
                return True
        return False

    def set_lead(self, agent_id: AgentId) -> bool:
        """设置团队负责人。

        Args:
            agent_id: 负责人ID

        Returns:
            是否设置成功
        """
        member = self.get_member(agent_id)
        if member is None:
            return False

        # 重置之前的负责人
        if self.lead_id:
            old_lead = self.get_member(self.lead_id)
            if old_lead:
                old_lead.is_lead = False

        # 设置新负责人
        member.is_lead = True
        self.lead_id = agent_id
        logger.info("设置团队负责人: team=%s, lead=%s", self.id, agent_id)
        return True

    # =========================================================================
    # 能力查询
    # =========================================================================

    def has_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> bool:
        """检查团队是否具有指定能力。

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            是否具有该能力
        """
        for member in self.members:
            if member.can_handle(capability, min_level):
                return True
        return False

    def get_members_by_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> list[TeamMember]:
        """获取具有指定能力的成员。

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            具有该能力的成员列表
        """
        return [m for m in self.members if m.can_handle(capability, min_level)]

    def get_members_by_role(self, role: AgentRole) -> list[TeamMember]:
        """获取指定角色的成员。

        Args:
            role: 目标角色

        Returns:
            具有该角色的成员列表
        """
        return [m for m in self.members if m.role == role]

    def get_available_members(self, min_availability: float = 0.5) -> list[TeamMember]:
        """获取可用成员。

        Args:
            min_availability: 最低可用性要求

        Returns:
            可用成员列表
        """
        return [m for m in self.members if m.effective_availability >= min_availability]

    # =========================================================================
    # 状态管理
    # =========================================================================

    def mark_ready(self) -> None:
        """标记团队就绪。"""
        self.status = TeamStatus.READY
        logger.info("团队就绪: team=%s, size=%d", self.id, self.size)

    def mark_active(self) -> None:
        """标记团队活跃。"""
        self.status = TeamStatus.ACTIVE
        logger.info("团队开始工作: team=%s", self.id)

    def pause(self) -> None:
        """暂停团队。"""
        self.status = TeamStatus.PAUSED
        logger.info("团队暂停: team=%s", self.id)

    def disband(self) -> None:
        """解散团队。"""
        self.status = TeamStatus.DISBANDED
        logger.info("团队解散: team=%s", self.id)

    # =========================================================================
    # 验证方法
    # =========================================================================

    def validate(self) -> tuple[bool, list[str]]:
        """验证团队配置。

        Returns:
            (是否有效, 错误列表)
        """
        errors: list[str] = []

        # 检查团队规模
        if self.size < self.configuration.min_size:
            errors.append(
                f"团队规模 ({self.size}) 小于最小要求 ({self.configuration.min_size})"
            )
        if self.size > self.configuration.max_size:
            errors.append(
                f"团队规模 ({self.size}) 超过最大限制 ({self.configuration.max_size})"
            )

        # 检查必需角色
        for role in self.configuration.required_roles:
            if role not in self.covered_roles:
                errors.append(f"缺少必需角色: {role.value}")

        # 检查必需能力
        for cap in self.configuration.required_capabilities:
            if not self.has_capability(cap):
                errors.append(f"缺少必需能力: {cap.value}")

        # 检查负责人
        if self.lead_id and self.get_member(self.lead_id) is None:
            errors.append("团队负责人不在成员列表中")

        return len(errors) == 0, errors

    def __repr__(self) -> str:
        """返回团队的简洁表示。"""
        return (
            f"Team(id={self.id!r}, name={self.name!r}, "
            f"size={self.size}, status={self.status.value!r})"
        )


# =============================================================================
# 团队构建器
# =============================================================================


class TeamBuilder:
    """团队构建器。

    根据任务需求动态组建专家团队，支持多种构建策略和优化选项。

    核心功能：
        - 根据任务需求自动选择专家
        - 支持多种团队组建策略
        - 负载均衡和可用性检查
        - 能力覆盖优化

    Attributes:
        registry: 智能体注册表
        default_strategy: 默认组建策略

    Example:
        >>> builder = TeamBuilder(agent_registry)
        >>> team = await builder.build_team(
        ...     task=complex_task,
        ...     strategy=TeamFormationStrategy.COMPREHENSIVE,
        ...     min_experts=3
        ... )
    """

    def __init__(
        self,
        registry: AgentRegistryProtocol | None = None,
        default_strategy: TeamFormationStrategy = TeamFormationStrategy.BALANCED,
    ) -> None:
        """初始化团队构建器。

        Args:
            registry: 智能体注册表
            default_strategy: 默认组建策略
        """
        self._registry = registry
        self._default_strategy = default_strategy
        self._agent_pool: dict[AgentId, AgentProfile] = {}

        logger.info(
            "初始化团队构建器: strategy=%s",
            default_strategy.value
        )

    # =========================================================================
    # 智能体池管理
    # =========================================================================

    def register_agent(self, profile: AgentProfile) -> None:
        """注册智能体到池中。

        Args:
            profile: 智能体配置
        """
        self._agent_pool[profile.id] = profile
        logger.debug("注册智能体: id=%s, role=%s", profile.id, profile.role.value)

    def unregister_agent(self, agent_id: AgentId) -> bool:
        """从池中注销智能体。

        Args:
            agent_id: 智能体ID

        Returns:
            是否成功注销
        """
        if agent_id in self._agent_pool:
            del self._agent_pool[agent_id]
            logger.debug("注销智能体: id=%s", agent_id)
            return True
        return False

    def get_available_agents(self) -> list[AgentProfile]:
        """获取所有可用智能体。

        Returns:
            可用智能体配置列表
        """
        agents = list(self._agent_pool.values())

        # 如果有注册表，也从注册表获取
        if self._registry:
            # 获取所有角色的智能体
            for role in AgentRole:
                for agent_id in self._registry.find_agents_by_role(role):
                    profile = self._registry.get_agent_profile(agent_id)
                    if profile and profile.id not in self._agent_pool:
                        agents.append(profile)

        return agents

    # =========================================================================
    # 团队构建
    # =========================================================================

    async def build_team(
        self,
        task: Task,
        *,
        name: str = "",
        strategy: TeamFormationStrategy | None = None,
        min_experts: int = 1,
        max_experts: int = 10,
        required_roles: list[AgentRole] | None = None,
        excluded_agents: list[AgentId] | None = None,
    ) -> Team:
        """根据任务需求构建团队。

        根据任务的能力需求、角色要求和复杂度，智能选择合适的专家组成团队。

        Args:
            task: 目标任务
            name: 团队名称
            strategy: 组建策略，默认使用构建器的默认策略
            min_experts: 最小专家数量
            max_experts: 最大专家数量
            required_roles: 必需的角色列表
            excluded_agents: 排除的智能体ID列表

        Returns:
            构建完成的团队

        Example:
            >>> team = await builder.build_team(
            ...     task=review_task,
            ...     name="代码审查团队",
            ...     min_experts=2,
            ...     required_roles=[AgentRole.CODE_REVIEWER, AgentRole.SECURITY_ARCHITECT]
            ... )
        """
        strategy = strategy or self._default_strategy
        excluded_agents = excluded_agents or []
        required_roles = required_roles or []

        logger.info(
            "开始构建团队: task=%s, strategy=%s, min=%d, max=%d",
            task.id, strategy.value, min_experts, max_experts
        )

        # 创建团队配置
        config = TeamConfiguration(
            min_size=min_experts,
            max_size=max_experts,
            required_roles=required_roles + ([task.required_role] if task.required_role else []),
            required_capabilities=list(task.required_capabilities),
            preferred_expertise_level=task.min_expertise_level,
            formation_strategy=strategy,
        )

        # 创建团队
        team = Team(
            name=name or f"Team-{task.id}",
            description=f"为任务 '{task.title}' 组建的团队",
            configuration=config,
            task_id=task.id,
        )

        # 选择专家
        experts = await self.select_experts(
            task=task,
            strategy=strategy,
            min_count=min_experts,
            max_count=max_experts,
            required_roles=config.required_roles,
            excluded_agents=excluded_agents,
        )

        # 添加成员到团队
        for i, profile in enumerate(experts):
            member = TeamMember(
                agent_id=profile.id,
                profile=profile,
                team_role=self._determine_team_role(profile, task),
                is_lead=(i == 0),  # 第一个成员默认为负责人
            )
            team.add_member(member)

        # 设置负责人
        if team.members:
            team.set_lead(team.members[0].agent_id)

        # 验证团队
        is_valid, errors = team.validate()
        if not is_valid:
            logger.warning("团队验证失败: %s", errors)

        # 标记就绪
        if is_valid:
            team.mark_ready()

        logger.info(
            "团队构建完成: team=%s, size=%d, roles=%s",
            team.id, team.size, [m.role.value for m in team.members]
        )

        return team

    async def select_experts(
        self,
        task: Task,
        *,
        strategy: TeamFormationStrategy | None = None,
        min_count: int = 1,
        max_count: int = 10,
        required_roles: list[AgentRole] | None = None,
        excluded_agents: list[AgentId] | None = None,
    ) -> list[AgentProfile]:
        """根据任务需求选择专家。

        智能选择最适合任务的专家组合，考虑能力匹配度、专业水平和可用性。

        Args:
            task: 目标任务
            strategy: 选择策略
            min_count: 最小数量
            max_count: 最大数量
            required_roles: 必需的角色
            excluded_agents: 排除的智能体

        Returns:
            选中的专家配置列表

        Example:
            >>> experts = await builder.select_experts(
            ...     task=code_review_task,
            ...     min_count=2,
            ...     required_roles=[AgentRole.CODE_REVIEWER]
            ... )
        """
        strategy = strategy or self._default_strategy
        excluded_agents = excluded_agents or []
        required_roles = required_roles or []

        logger.debug(
            "选择专家: task=%s, strategy=%s, required_roles=%s",
            task.id, strategy.value, [r.value for r in required_roles]
        )

        # 获取候选专家
        candidates = self._get_candidates(task, excluded_agents)

        if not candidates:
            logger.warning("没有可用的候选专家")
            return []

        # 计算匹配分数
        scored_candidates = self._score_candidates(candidates, task, strategy)

        # 选择专家
        selected = self._select_by_strategy(
            scored_candidates=scored_candidates,
            task=task,
            strategy=strategy,
            min_count=min_count,
            max_count=max_count,
            required_roles=required_roles,
        )

        logger.debug(
            "选中专家: count=%d, ids=%s",
            len(selected), [p.id for p in selected]
        )

        return selected

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _get_candidates(
        self,
        task: Task,
        excluded_agents: list[AgentId],
    ) -> list[AgentProfile]:
        """获取候选专家列表。

        Args:
            task: 目标任务
            excluded_agents: 排除的智能体

        Returns:
            候选专家配置列表
        """
        candidates: list[AgentProfile] = []

        # 从注册表获取
        if self._registry:
            # 按能力查找
            for cap in task.required_capabilities:
                for agent_id in self._registry.find_agents_by_capability(cap):
                    if agent_id not in excluded_agents:
                        profile = self._registry.get_agent_profile(agent_id)
                        if profile and profile not in candidates:
                            candidates.append(profile)

            # 按角色查找
            if task.required_role:
                for agent_id in self._registry.find_agents_by_role(task.required_role):
                    if agent_id not in excluded_agents:
                        profile = self._registry.get_agent_profile(agent_id)
                        if profile and profile not in candidates:
                            candidates.append(profile)

        # 从内部池获取
        for profile in self._agent_pool.values():
            if profile.id not in excluded_agents and profile not in candidates:
                candidates.append(profile)

        return candidates

    def _score_candidates(
        self,
        candidates: list[AgentProfile],
        task: Task,
        strategy: TeamFormationStrategy,
    ) -> list[tuple[AgentProfile, float]]:
        """计算候选专家的匹配分数。

        Args:
            candidates: 候选专家列表
            task: 目标任务
            strategy: 选择策略

        Returns:
            (专家配置, 分数) 列表，按分数降序排列
        """
        scored: list[tuple[AgentProfile, float]] = []

        for profile in candidates:
            score = self._calculate_match_score(profile, task, strategy)
            scored.append((profile, score))

        # 按分数降序排列
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _calculate_match_score(
        self,
        profile: AgentProfile,
        task: Task,
        strategy: TeamFormationStrategy,
    ) -> float:
        """计算单个专家的匹配分数。

        Args:
            profile: 专家配置
            task: 目标任务
            strategy: 选择策略

        Returns:
            匹配分数 (0.0-1.0)
        """
        score = 0.0

        # 能力匹配 (权重: 40%)
        if task.required_capabilities:
            matched_caps = sum(
                1 for cap in task.required_capabilities
                if profile.has_capability(cap)
            )
            cap_score = matched_caps / len(task.required_capabilities)
            score += cap_score * 0.4

        # 角色匹配 (权重: 25%)
        if task.required_role:
            if profile.role == task.required_role:
                score += 0.25
            elif self._is_related_role(profile.role, task.required_role):
                score += 0.15

        # 专业水平 (权重: 20%)
        expertise_ratio = profile.expertise_level.value / ExpertiseLevel.FELLOW.value
        score += expertise_ratio * 0.2

        # 策略特定加权
        if strategy == TeamFormationStrategy.SPECIALIZED:
            # 专业团队策略加重专业水平
            score += expertise_ratio * 0.1
        elif strategy == TeamFormationStrategy.COMPREHENSIVE:
            # 全面团队策略加重能力覆盖
            all_caps = len(profile.capabilities)
            score += min(all_caps / 10, 0.15)

        # 优先级匹配 (权重: 5%)
        if task.priority == TaskPriority.CRITICAL:
            # 关键任务优先选择高级专家
            if profile.expertise_level.value >= ExpertiseLevel.SENIOR.value:
                score += 0.05

        return min(score, 1.0)

    def _is_related_role(self, role1: AgentRole, role2: AgentRole) -> bool:
        """检查两个角色是否相关。

        Args:
            role1: 角色1
            role2: 角色2

        Returns:
            是否相关
        """
        # 定义相关角色组
        related_groups = [
            {AgentRole.BACKEND_ENGINEER, AgentRole.FULLSTACK_ENGINEER, AgentRole.TECH_LEAD},
            {AgentRole.FRONTEND_ENGINEER, AgentRole.FULLSTACK_ENGINEER},
            {AgentRole.QA_ENGINEER, AgentRole.QA_LEAD, AgentRole.CODE_REVIEWER},
            {AgentRole.SYSTEM_ARCHITECT, AgentRole.SOLUTION_ARCHITECT, AgentRole.TECH_DIRECTOR},
            {AgentRole.DEVOPS_ENGINEER, AgentRole.SRE_ENGINEER},
        ]

        for group in related_groups:
            if role1 in group and role2 in group:
                return True

        return False

    def _select_by_strategy(
        self,
        scored_candidates: list[tuple[AgentProfile, float]],
        task: Task,
        strategy: TeamFormationStrategy,
        min_count: int,
        max_count: int,
        required_roles: list[AgentRole],
    ) -> list[AgentProfile]:
        """根据策略选择专家。

        Args:
            scored_candidates: 评分后的候选列表
            task: 目标任务
            strategy: 选择策略
            min_count: 最小数量
            max_count: 最大数量
            required_roles: 必需的角色

        Returns:
            选中的专家列表
        """
        selected: list[AgentProfile] = []
        selected_roles: set[AgentRole] = set()

        # 首先确保必需角色
        for role in required_roles:
            for profile, score in scored_candidates:
                if profile.role == role and profile not in selected:
                    selected.append(profile)
                    selected_roles.add(role)
                    break

        # 然后根据策略填充
        for profile, score in scored_candidates:
            if len(selected) >= max_count:
                break

            if profile in selected:
                continue

            if strategy == TeamFormationStrategy.MINIMAL:
                # 最小策略：只选择必需的
                if len(selected) >= min_count:
                    break
            elif strategy == TeamFormationStrategy.SPECIALIZED:
                # 专业策略：优先高分专家
                if score < 0.5:
                    continue
            elif strategy == TeamFormationStrategy.COMPREHENSIVE:
                # 全面策略：尽量覆盖不同角色
                if profile.role in selected_roles and len(selected) >= min_count:
                    continue

            selected.append(profile)
            selected_roles.add(profile.role)

        # 确保达到最小数量
        while len(selected) < min_count and len(selected) < len(scored_candidates):
            for profile, _ in scored_candidates:
                if profile not in selected:
                    selected.append(profile)
                    break

        return selected

    def _determine_team_role(self, profile: AgentProfile, task: Task) -> str:
        """确定成员在团队中的角色。

        Args:
            profile: 成员配置
            task: 目标任务

        Returns:
            团队角色描述
        """
        role_descriptions = {
            AgentRole.PROJECT_MANAGER: "项目协调",
            AgentRole.TECH_DIRECTOR: "技术决策",
            AgentRole.SYSTEM_ARCHITECT: "架构设计",
            AgentRole.SOLUTION_ARCHITECT: "方案设计",
            AgentRole.TECH_LEAD: "技术指导",
            AgentRole.BACKEND_ENGINEER: "后端开发",
            AgentRole.FRONTEND_ENGINEER: "前端开发",
            AgentRole.FULLSTACK_ENGINEER: "全栈开发",
            AgentRole.QA_ENGINEER: "质量保障",
            AgentRole.QA_LEAD: "测试管理",
            AgentRole.CODE_REVIEWER: "代码审查",
            AgentRole.PERFORMANCE_ENGINEER: "性能优化",
            AgentRole.SECURITY_ARCHITECT: "安全审计",
            AgentRole.DEVOPS_ENGINEER: "运维部署",
            AgentRole.SRE_ENGINEER: "可靠性保障",
            AgentRole.TECH_WRITER: "技术文档",
        }

        return role_descriptions.get(profile.role, "团队成员")

    # =========================================================================
    # 便捷方法
    # =========================================================================

    async def build_review_team(
        self,
        task: Task,
        reviewers_count: int = 2,
    ) -> Team:
        """构建代码审查团队。

        Args:
            task: 审查任务
            reviewers_count: 审查员数量

        Returns:
            审查团队
        """
        return await self.build_team(
            task=task,
            name="代码审查团队",
            strategy=TeamFormationStrategy.SPECIALIZED,
            min_experts=reviewers_count,
            max_experts=reviewers_count + 1,
            required_roles=[AgentRole.CODE_REVIEWER],
        )

    async def build_development_team(
        self,
        task: Task,
        include_qa: bool = True,
    ) -> Team:
        """构建开发团队。

        Args:
            task: 开发任务
            include_qa: 是否包含QA

        Returns:
            开发团队
        """
        required_roles = [AgentRole.BACKEND_ENGINEER]
        if include_qa:
            required_roles.append(AgentRole.QA_ENGINEER)

        return await self.build_team(
            task=task,
            name="开发团队",
            strategy=TeamFormationStrategy.BALANCED,
            min_experts=2,
            max_experts=5,
            required_roles=required_roles,
        )

    async def build_security_team(
        self,
        task: Task,
    ) -> Team:
        """构建安全审计团队。

        Args:
            task: 安全审计任务

        Returns:
            安全团队
        """
        return await self.build_team(
            task=task,
            name="安全审计团队",
            strategy=TeamFormationStrategy.SPECIALIZED,
            min_experts=1,
            max_experts=3,
            required_roles=[AgentRole.SECURITY_ARCHITECT],
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 协议
    "AgentRegistryProtocol",
    # 枚举
    "TeamFormationStrategy",
    "TeamStatus",
    # 数据类
    "TeamMember",
    "TeamConfiguration",
    "Team",
    # 构建器
    "TeamBuilder",
]
