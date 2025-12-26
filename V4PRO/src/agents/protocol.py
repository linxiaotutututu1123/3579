"""智能体通信协议 (Agent Communication Protocol).

V4PRO Platform Component - 智能体间通信标准
军规覆盖: M3(审计追踪), M7(回放一致性)

定义智能体之间的通信协议、消息格式和任务上下文。

示例:
    >>> msg = AgentMessage(
    ...     sender=AgentRole.ARCHITECT,
    ...     receiver=AgentRole.DEVELOPER,
    ...     content="请实现用户服务接口",
    ...     context=TaskContext(task_id="T001"),
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
import uuid


class AgentRole(Enum):
    """智能体角色枚举.

    定义世界级编码团队的所有角色。
    """

    # 领导层 (Leadership)
    TECH_LEAD = "tech_lead"  # 技术负责人
    PROJECT_MANAGER = "project_manager"  # 项目经理

    # 架构层 (Architecture)
    SYSTEM_ARCHITECT = "system_architect"  # 系统架构师
    SECURITY_ARCHITECT = "security_architect"  # 安全架构师

    # 开发层 (Development)
    BACKEND_ENGINEER = "backend_engineer"  # 后端工程师
    FRONTEND_ENGINEER = "frontend_engineer"  # 前端工程师
    DATA_ENGINEER = "data_engineer"  # 数据工程师

    # 质量层 (Quality)
    QA_ENGINEER = "qa_engineer"  # 测试工程师
    DEVOPS_ENGINEER = "devops_engineer"  # DevOps工程师

    # 支持层 (Support)
    TECH_WRITER = "tech_writer"  # 技术文档工程师
    CODE_REVIEWER = "code_reviewer"  # 代码审查员

    # 特殊角色
    ORCHESTRATOR = "orchestrator"  # 编排器 (系统角色)
    CONFIDENCE_CHECKER = "confidence_checker"  # 置信度检查器


class AgentCapability(Enum):
    """智能体能力枚举."""

    # 分析能力
    REQUIREMENT_ANALYSIS = auto()  # 需求分析
    ARCHITECTURE_DESIGN = auto()  # 架构设计
    SECURITY_ANALYSIS = auto()  # 安全分析
    PERFORMANCE_ANALYSIS = auto()  # 性能分析

    # 开发能力
    CODE_IMPLEMENTATION = auto()  # 代码实现
    API_DESIGN = auto()  # API设计
    DATABASE_DESIGN = auto()  # 数据库设计
    UI_DEVELOPMENT = auto()  # UI开发

    # 质量能力
    TEST_DESIGN = auto()  # 测试设计
    CODE_REVIEW = auto()  # 代码审查
    DOCUMENTATION = auto()  # 文档编写

    # 运维能力
    CI_CD = auto()  # CI/CD配置
    DEPLOYMENT = auto()  # 部署管理
    MONITORING = auto()  # 监控配置


class TaskStatus(Enum):
    """任务状态枚举."""

    PENDING = "pending"  # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    REVIEW = "review"  # 审查中
    BLOCKED = "blocked"  # 阻塞
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class MessageType(Enum):
    """消息类型枚举."""

    TASK_ASSIGNMENT = "task_assignment"  # 任务分配
    TASK_UPDATE = "task_update"  # 任务更新
    TASK_COMPLETION = "task_completion"  # 任务完成
    QUERY = "query"  # 查询
    RESPONSE = "response"  # 响应
    REVIEW_REQUEST = "review_request"  # 审查请求
    REVIEW_RESULT = "review_result"  # 审查结果
    CONFIDENCE_CHECK = "confidence_check"  # 置信度检查
    ESCALATION = "escalation"  # 升级


@dataclass
class TaskContext:
    """任务上下文.

    包含任务执行所需的所有上下文信息。

    属性:
        task_id: 任务唯一标识
        parent_task_id: 父任务ID (可选)
        project_id: 项目ID
        priority: 优先级 (1-5, 5最高)
        deadline: 截止时间 (可选)
        requirements: 需求描述
        constraints: 约束条件
        metadata: 附加元数据
    """

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_task_id: str = ""
    project_id: str = "default"
    priority: int = 3
    deadline: str = ""
    requirements: str = ""
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # 置信度检查相关
    confidence_required: float = 0.90  # 要求的置信度阈值
    confidence_checks_passed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "project_id": self.project_id,
            "priority": self.priority,
            "deadline": self.deadline,
            "requirements": self.requirements,
            "constraints": self.constraints,
            "metadata": self.metadata,
            "confidence_required": self.confidence_required,
            "confidence_checks_passed": self.confidence_checks_passed,
        }


@dataclass
class TaskResult:
    """任务执行结果.

    属性:
        task_id: 任务ID
        status: 任务状态
        output: 输出内容
        artifacts: 产出物列表 (文件路径等)
        confidence_score: 置信度分数
        execution_time_ms: 执行时间 (毫秒)
        error_message: 错误信息 (如果失败)
        review_comments: 审查意见
    """

    task_id: str
    status: TaskStatus
    output: str = ""
    artifacts: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    execution_time_ms: int = 0
    error_message: str = ""
    review_comments: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )

    @property
    def is_success(self) -> bool:
        """是否成功."""
        return self.status == TaskStatus.COMPLETED

    @property
    def needs_review(self) -> bool:
        """是否需要审查."""
        return self.status == TaskStatus.REVIEW

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式 (M3)."""
        return {
            "event_type": "TASK_RESULT",
            "task_id": self.task_id,
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "artifacts_count": len(self.artifacts),
            "timestamp": self.timestamp,
        }


@dataclass
class AgentMessage:
    """智能体消息.

    智能体之间通信的标准消息格式。

    属性:
        message_id: 消息唯一标识
        sender: 发送者角色
        receiver: 接收者角色
        message_type: 消息类型
        content: 消息内容
        context: 任务上下文
        priority: 优先级
        timestamp: 时间戳
        metadata: 附加元数据
    """

    sender: AgentRole
    receiver: AgentRole
    message_type: MessageType
    content: str
    context: TaskContext = field(default_factory=TaskContext)
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    priority: int = 3
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # 追踪信息
    correlation_id: str = ""  # 关联ID (用于追踪消息链)
    reply_to: str = ""  # 回复的消息ID

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "message_id": self.message_id,
            "sender": self.sender.value,
            "receiver": self.receiver.value,
            "message_type": self.message_type.value,
            "content": self.content,
            "context": self.context.to_dict(),
            "priority": self.priority,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }

    def create_reply(
        self,
        content: str,
        message_type: MessageType = MessageType.RESPONSE,
    ) -> AgentMessage:
        """创建回复消息."""
        return AgentMessage(
            sender=self.receiver,
            receiver=self.sender,
            message_type=message_type,
            content=content,
            context=self.context,
            correlation_id=self.correlation_id or self.message_id,
            reply_to=self.message_id,
        )


@dataclass
class AgentState:
    """智能体状态.

    记录智能体的当前状态。
    """

    role: AgentRole
    status: str = "idle"  # idle, working, blocked, offline
    current_task_id: str = ""
    pending_tasks: list[str] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_confidence: float = 0.0
    last_activity: str = field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )

    @property
    def is_available(self) -> bool:
        """是否可用."""
        return self.status in ("idle", "working")

    @property
    def workload(self) -> int:
        """当前工作负载."""
        return len(self.pending_tasks) + (1 if self.current_task_id else 0)


# 角色能力映射
ROLE_CAPABILITIES: dict[AgentRole, set[AgentCapability]] = {
    AgentRole.TECH_LEAD: {
        AgentCapability.REQUIREMENT_ANALYSIS,
        AgentCapability.ARCHITECTURE_DESIGN,
        AgentCapability.CODE_REVIEW,
    },
    AgentRole.PROJECT_MANAGER: {
        AgentCapability.REQUIREMENT_ANALYSIS,
    },
    AgentRole.SYSTEM_ARCHITECT: {
        AgentCapability.ARCHITECTURE_DESIGN,
        AgentCapability.API_DESIGN,
        AgentCapability.DATABASE_DESIGN,
    },
    AgentRole.SECURITY_ARCHITECT: {
        AgentCapability.SECURITY_ANALYSIS,
        AgentCapability.CODE_REVIEW,
    },
    AgentRole.BACKEND_ENGINEER: {
        AgentCapability.CODE_IMPLEMENTATION,
        AgentCapability.API_DESIGN,
        AgentCapability.DATABASE_DESIGN,
    },
    AgentRole.FRONTEND_ENGINEER: {
        AgentCapability.CODE_IMPLEMENTATION,
        AgentCapability.UI_DEVELOPMENT,
    },
    AgentRole.DATA_ENGINEER: {
        AgentCapability.DATABASE_DESIGN,
        AgentCapability.CODE_IMPLEMENTATION,
    },
    AgentRole.QA_ENGINEER: {
        AgentCapability.TEST_DESIGN,
        AgentCapability.CODE_REVIEW,
    },
    AgentRole.DEVOPS_ENGINEER: {
        AgentCapability.CI_CD,
        AgentCapability.DEPLOYMENT,
        AgentCapability.MONITORING,
    },
    AgentRole.TECH_WRITER: {
        AgentCapability.DOCUMENTATION,
    },
    AgentRole.CODE_REVIEWER: {
        AgentCapability.CODE_REVIEW,
        AgentCapability.SECURITY_ANALYSIS,
    },
}


def get_agents_for_capability(capability: AgentCapability) -> list[AgentRole]:
    """获取具有指定能力的智能体角色列表."""
    return [
        role
        for role, caps in ROLE_CAPABILITIES.items()
        if capability in caps
    ]
