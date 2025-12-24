"""API模块 - Pydantic数据模型.

本模块定义了REST API的请求和响应模型,
使用Pydantic v2进行数据验证和序列化。

模型类别:
    - Task: 任务相关的请求/响应模型
    - Team: 团队相关的请求/响应模型
    - Workflow: 工作流相关的请求/响应模型
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 通用枚举类型
# =============================================================================


class TaskStatusEnum(str, Enum):
    """任务状态枚举."""

    DRAFT = "draft"
    """草稿 - 任务正在定义中"""

    PENDING = "pending"
    """待处理 - 任务已准备好分配"""

    QUEUED = "queued"
    """排队中 - 任务在执行队列中"""

    ASSIGNED = "assigned"
    """已分配 - 任务已分配给代理"""

    IN_PROGRESS = "in_progress"
    """进行中 - 任务正在执行"""

    IN_REVIEW = "in_review"
    """审核中 - 任务输出正在审核"""

    COMPLETED = "completed"
    """已完成 - 任务成功完成"""

    FAILED = "failed"
    """失败 - 任务无法完成"""

    CANCELLED = "cancelled"
    """已取消 - 任务被取消"""


class TaskPriorityEnum(str, Enum):
    """任务优先级枚举."""

    CRITICAL = "critical"
    """紧急 - 阻塞性问题,需要立即处理"""

    HIGH = "high"
    """高 - 核心功能,重要特性"""

    MEDIUM = "medium"
    """中 - 标准功能,常规工作"""

    LOW = "low"
    """低 - 优化改进"""

    BACKLOG = "backlog"
    """待办 - 未来考虑"""


class AgentRoleEnum(str, Enum):
    """代理角色枚举."""

    PROJECT_MANAGER = "project_manager"
    """项目经理"""

    TECH_DIRECTOR = "tech_director"
    """技术总监"""

    SYSTEM_ARCHITECT = "system_architect"
    """系统架构师"""

    BACKEND_ENGINEER = "backend_engineer"
    """后端工程师"""

    FRONTEND_ENGINEER = "frontend_engineer"
    """前端工程师"""

    QA_ENGINEER = "qa_engineer"
    """测试工程师"""

    DEVOPS_ENGINEER = "devops_engineer"
    """DevOps工程师"""

    SECURITY_ARCHITECT = "security_architect"
    """安全架构师"""


class WorkflowStatusEnum(str, Enum):
    """工作流状态枚举."""

    CREATED = "created"
    """已创建 - 工作流已初始化"""

    RUNNING = "running"
    """运行中 - 工作流正在执行"""

    PAUSED = "paused"
    """已暂停 - 工作流暂停执行"""

    COMPLETED = "completed"
    """已完成 - 工作流成功完成"""

    FAILED = "failed"
    """失败 - 工作流执行失败"""

    CANCELLED = "cancelled"
    """已取消 - 工作流被取消"""


# =============================================================================
# 基础模型
# =============================================================================


class BaseSchema(BaseModel):
    """基础模型,配置通用选项."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


# =============================================================================
# Task 模型
# =============================================================================


class TaskRequest(BaseSchema):
    """任务创建请求模型.

    用于创建新任务的请求体。

    Attributes:
        title: 任务标题,简短描述任务内容
        description: 任务详细描述,包含实现要求
        priority: 任务优先级
        required_capabilities: 所需代理能力列表
        required_role: 所需代理角色(可选)
        estimated_hours: 预估完成时间(小时)
        deadline: 截止时间(可选)
        context: 附加上下文信息
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="任务标题",
        examples=["实现用户登录API"],
    )

    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="任务详细描述",
        examples=["使用JWT实现用户认证,包括登录、注册、刷新token功能"],
    )

    priority: TaskPriorityEnum = Field(
        default=TaskPriorityEnum.MEDIUM,
        description="任务优先级",
    )

    required_capabilities: list[str] = Field(
        default_factory=list,
        description="所需代理能力列表",
        examples=[["code_generation", "api_design"]],
    )

    required_role: AgentRoleEnum | None = Field(
        default=None,
        description="所需代理角色",
    )

    estimated_hours: float = Field(
        default=4.0,
        ge=0.1,
        le=1000.0,
        description="预估完成时间(小时)",
    )

    deadline: datetime | None = Field(
        default=None,
        description="截止时间",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="附加上下文信息",
    )


class TaskResponse(BaseSchema):
    """任务响应模型.

    返回任务详细信息。

    Attributes:
        id: 任务唯一标识符
        title: 任务标题
        description: 任务详细描述
        status: 当前任务状态
        priority: 任务优先级
        assigned_to: 分配的代理ID
        created_at: 创建时间
        updated_at: 更新时间
        completed_at: 完成时间(如已完成)
        result: 任务执行结果(如已完成)
    """

    id: str = Field(
        ...,
        description="任务唯一标识符",
        examples=["task_abc123"],
    )

    title: str = Field(
        ...,
        description="任务标题",
    )

    description: str = Field(
        ...,
        description="任务详细描述",
    )

    status: TaskStatusEnum = Field(
        ...,
        description="当前任务状态",
    )

    priority: TaskPriorityEnum = Field(
        ...,
        description="任务优先级",
    )

    assigned_to: str | None = Field(
        default=None,
        description="分配的代理ID",
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
    )

    updated_at: datetime | None = Field(
        default=None,
        description="更新时间",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="完成时间",
    )

    result: dict[str, Any] | None = Field(
        default=None,
        description="任务执行结果",
    )


class TaskListResponse(BaseSchema):
    """任务列表响应模型.

    Attributes:
        tasks: 任务列表
        total: 总任务数
        page: 当前页码
        page_size: 每页数量
    """

    tasks: list[TaskResponse] = Field(
        default_factory=list,
        description="任务列表",
    )

    total: int = Field(
        ...,
        ge=0,
        description="总任务数",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="当前页码",
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每页数量",
    )


# =============================================================================
# Team 模型
# =============================================================================


class AgentInfo(BaseSchema):
    """代理信息模型.

    Attributes:
        id: 代理唯一标识符
        name: 代理名称
        role: 代理角色
        status: 代理状态
        capabilities: 代理能力列表
    """

    id: str = Field(
        ...,
        description="代理唯一标识符",
        examples=["agent_xyz789"],
    )

    name: str = Field(
        ...,
        description="代理名称",
        examples=["Backend Engineer #1"],
    )

    role: AgentRoleEnum = Field(
        ...,
        description="代理角色",
    )

    status: str = Field(
        default="idle",
        description="代理状态",
        examples=["idle", "working", "reviewing"],
    )

    capabilities: list[str] = Field(
        default_factory=list,
        description="代理能力列表",
    )


class TeamRequest(BaseSchema):
    """团队创建/配置请求模型.

    用于创建或配置团队的请求体。

    Attributes:
        name: 团队名称
        description: 团队描述
        roles: 团队所需角色及数量
        project_type: 项目类型
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="团队名称",
        examples=["API开发团队"],
    )

    description: str = Field(
        default="",
        max_length=1000,
        description="团队描述",
    )

    roles: dict[AgentRoleEnum, int] = Field(
        default_factory=dict,
        description="团队所需角色及数量",
        examples=[{"backend_engineer": 2, "qa_engineer": 1}],
    )

    project_type: str = Field(
        default="general",
        description="项目类型",
        examples=["web_api", "microservices", "data_pipeline"],
    )


class TeamResponse(BaseSchema):
    """团队响应模型.

    返回团队详细信息。

    Attributes:
        id: 团队唯一标识符
        name: 团队名称
        description: 团队描述
        agents: 团队成员列表
        created_at: 创建时间
        active_tasks: 活跃任务数
    """

    id: str = Field(
        ...,
        description="团队唯一标识符",
        examples=["team_def456"],
    )

    name: str = Field(
        ...,
        description="团队名称",
    )

    description: str = Field(
        default="",
        description="团队描述",
    )

    agents: list[AgentInfo] = Field(
        default_factory=list,
        description="团队成员列表",
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
    )

    active_tasks: int = Field(
        default=0,
        ge=0,
        description="活跃任务数",
    )


class TeamListResponse(BaseSchema):
    """团队列表响应模型.

    Attributes:
        teams: 团队列表
        total: 总团队数
    """

    teams: list[TeamResponse] = Field(
        default_factory=list,
        description="团队列表",
    )

    total: int = Field(
        ...,
        ge=0,
        description="总团队数",
    )


# =============================================================================
# Workflow 模型
# =============================================================================


class WorkflowStageInfo(BaseSchema):
    """工作流阶段信息模型.

    Attributes:
        name: 阶段名称
        status: 阶段状态
        started_at: 开始时间
        completed_at: 完成时间
        tasks: 阶段任务ID列表
    """

    name: str = Field(
        ...,
        description="阶段名称",
        examples=["requirement_analysis", "design", "implementation"],
    )

    status: str = Field(
        default="pending",
        description="阶段状态",
        examples=["pending", "in_progress", "completed"],
    )

    started_at: datetime | None = Field(
        default=None,
        description="开始时间",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="完成时间",
    )

    tasks: list[str] = Field(
        default_factory=list,
        description="阶段任务ID列表",
    )


class WorkflowRequest(BaseSchema):
    """工作流创建请求模型.

    用于创建新工作流的请求体。

    Attributes:
        name: 工作流名称
        description: 工作流描述
        project_goal: 项目目标
        team_id: 执行团队ID
        stages: 自定义阶段配置(可选)
        config: 工作流配置选项
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="工作流名称",
        examples=["用户管理系统开发"],
    )

    description: str = Field(
        default="",
        max_length=5000,
        description="工作流描述",
    )

    project_goal: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="项目目标",
        examples=["开发一个完整的用户管理系统,支持注册、登录、权限管理"],
    )

    team_id: str | None = Field(
        default=None,
        description="执行团队ID,为空则自动创建团队",
    )

    stages: list[str] | None = Field(
        default=None,
        description="自定义阶段列表,为空则使用默认6阶段",
        examples=[["requirement", "design", "implement", "test", "review", "deploy"]],
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="工作流配置选项",
    )


class WorkflowResponse(BaseSchema):
    """工作流响应模型.

    返回工作流详细信息。

    Attributes:
        id: 工作流唯一标识符
        name: 工作流名称
        description: 工作流描述
        status: 工作流状态
        team_id: 执行团队ID
        stages: 阶段信息列表
        current_stage: 当前阶段名称
        progress: 完成进度(0-100)
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
    """

    id: str = Field(
        ...,
        description="工作流唯一标识符",
        examples=["workflow_ghi012"],
    )

    name: str = Field(
        ...,
        description="工作流名称",
    )

    description: str = Field(
        default="",
        description="工作流描述",
    )

    status: WorkflowStatusEnum = Field(
        ...,
        description="工作流状态",
    )

    team_id: str | None = Field(
        default=None,
        description="执行团队ID",
    )

    stages: list[WorkflowStageInfo] = Field(
        default_factory=list,
        description="阶段信息列表",
    )

    current_stage: str | None = Field(
        default=None,
        description="当前阶段名称",
    )

    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="完成进度(0-100)",
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
    )

    started_at: datetime | None = Field(
        default=None,
        description="开始时间",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="完成时间",
    )


class WorkflowListResponse(BaseSchema):
    """工作流列表响应模型.

    Attributes:
        workflows: 工作流列表
        total: 总工作流数
    """

    workflows: list[WorkflowResponse] = Field(
        default_factory=list,
        description="工作流列表",
    )

    total: int = Field(
        ...,
        ge=0,
        description="总工作流数",
    )


# =============================================================================
# 通用响应模型
# =============================================================================


class ErrorResponse(BaseSchema):
    """错误响应模型.

    Attributes:
        error: 错误类型
        message: 错误描述
        detail: 详细信息
    """

    error: str = Field(
        ...,
        description="错误类型",
        examples=["ValidationError", "NotFoundError"],
    )

    message: str = Field(
        ...,
        description="错误描述",
    )

    detail: dict[str, Any] | None = Field(
        default=None,
        description="详细信息",
    )


class HealthResponse(BaseSchema):
    """健康检查响应模型.

    Attributes:
        status: 服务状态
        version: 服务版本
        timestamp: 检查时间
    """

    status: str = Field(
        default="healthy",
        description="服务状态",
    )

    version: str = Field(
        ...,
        description="服务版本",
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="检查时间",
    )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 枚举
    "TaskStatusEnum",
    "TaskPriorityEnum",
    "AgentRoleEnum",
    "WorkflowStatusEnum",
    # 基础
    "BaseSchema",
    # Task
    "TaskRequest",
    "TaskResponse",
    "TaskListResponse",
    # Team
    "AgentInfo",
    "TeamRequest",
    "TeamResponse",
    "TeamListResponse",
    # Workflow
    "WorkflowStageInfo",
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowListResponse",
    # 通用
    "ErrorResponse",
    "HealthResponse",
]
