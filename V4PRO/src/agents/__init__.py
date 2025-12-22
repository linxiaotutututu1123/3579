"""世界级智能体协调团队系统 (World-Class Agent Team System).

V4PRO Platform Component - 通用智能体编排框架
军规覆盖: M3(审计), M19(归因), M31(置信度), M32(自检)

核心模块:
- protocol: 智能体通信协议
- orchestrator: 中央编排器
- workflow: 工作流引擎
- team: 团队定义

示例:
    >>> from src.agents import TeamOrchestrator, Workflow
    >>> team = TeamOrchestrator.create_default_team()
    >>> result = await team.execute("实现用户认证系统")
"""

from src.agents.protocol import (
    AgentRole,
    AgentCapability,
    AgentMessage,
    TaskContext,
    TaskResult,
    TaskStatus,
)
from src.agents.orchestrator import TeamOrchestrator
from src.agents.workflow import (
    Workflow,
    WorkflowPhase,
    WorkflowEngine,
)
from src.agents.team import (
    AgentTeam,
    create_world_class_team,
)

__all__ = [
    # Protocol
    "AgentRole",
    "AgentCapability",
    "AgentMessage",
    "TaskContext",
    "TaskResult",
    "TaskStatus",
    # Orchestrator
    "TeamOrchestrator",
    # Workflow
    "Workflow",
    "WorkflowPhase",
    "WorkflowEngine",
    # Team
    "AgentTeam",
    "create_world_class_team",
]
