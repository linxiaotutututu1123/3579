"""团队模块 - 团队创建和管理.

本模块提供团队构建、角色分配和协作管理功能。

核心组件：
    - Team: 团队数据结构
    - TeamBuilder: 团队构建器
    - TeamMember: 团队成员
    - RoleAssigner: 角色分配器
    - RoleAssignment: 角色分配结果

主要功能：
    - 根据任务需求动态组建专家团队
    - 智能角色和任务分配
    - 负载均衡和能力匹配优化
    - 团队状态管理和协作支持

Example:
    >>> from chairman_agents.team import TeamBuilder, RoleAssigner
    >>>
    >>> # 构建团队
    >>> builder = TeamBuilder(agent_registry)
    >>> team = await builder.build_team(task, min_experts=2)
    >>>
    >>> # 分配角色
    >>> assigner = RoleAssigner()
    >>> plan = await assigner.assign_roles(team, tasks)
"""

from __future__ import annotations

from chairman_agents.team.team_builder import (
    # 协议
    AgentRegistryProtocol,
    # 枚举
    TeamFormationStrategy,
    TeamStatus,
    # 数据类
    Team,
    TeamConfiguration,
    TeamMember,
    # 构建器
    TeamBuilder,
)

from chairman_agents.team.role_assignment import (
    # 枚举
    AssignmentStatus,
    AssignmentStrategy,
    # 数据类
    AssignmentPlan,
    RoleAssignment,
    # 分配器
    RoleAssigner,
    # 便捷函数
    assign_roles,
)

__all__ = [
    # =========================================================================
    # 团队构建相关
    # =========================================================================
    # 协议
    "AgentRegistryProtocol",
    # 枚举
    "TeamFormationStrategy",
    "TeamStatus",
    # 数据类
    "Team",
    "TeamConfiguration",
    "TeamMember",
    # 构建器
    "TeamBuilder",
    # =========================================================================
    # 角色分配相关
    # =========================================================================
    # 枚举
    "AssignmentStatus",
    "AssignmentStrategy",
    # 数据类
    "AssignmentPlan",
    "RoleAssignment",
    # 分配器
    "RoleAssigner",
    # 便捷函数
    "assign_roles",
]
