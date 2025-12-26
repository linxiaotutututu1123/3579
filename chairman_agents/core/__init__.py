"""Chairman Agents 核心模块.

本模块提供 Chairman Agents 系统的核心类型定义、异常类和配置管理功能。

核心组件:
    - 类型定义: AgentId, TaskId, AgentRole, Task 等
    - 异常类: ChairmanAgentError 及其子类
    - 配置管理: Config, get_config, set_config
"""

from .types import (
    # 基础ID类型
    AgentId,
    TaskId,
    ArtifactId,
    generate_id,
    # 枚举类型
    AgentRole,
    ExpertiseLevel,
    AgentCapability,
    TaskStatus,
    TaskPriority,
    MessageType,
    ArtifactType,
    ToolType,
    # 数据类
    AgentProfile,
    Task,
    TaskContext,
    Artifact,
    QualityRequirements,
    TaskResult,
    ReasoningStep,
    ReviewComment,
    AgentMessage,
    AgentState,
)

from .exceptions import (
    # 基础异常
    ChairmanAgentError,
    # LLM相关异常
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMResponseError,
    # Agent相关异常
    AgentError,
    AgentNotFoundError,
    TaskExecutionError,
    CapabilityMismatchError,
    # Workflow相关异常
    WorkflowError,
    QualityGateError,
    PhaseTransitionError,
    DependencyError,
    # Tool相关异常
    ToolError,
    ToolExecutionError,
    ToolTimeoutError,
    # 配置相关异常
    ConfigurationError,
)

from .protocols import (
    LLMClientProtocol,
    ToolExecutorProtocol,
    MessageBrokerProtocol,
    AgentRegistryProtocol,
)

from .config import (
    # Exceptions (ConfigurationError already imported from exceptions)
    ConfigValidationError as ConfigValidationErr,
    ConfigLoadError,
    # Configuration classes
    LLMConfig,
    TeamConfig,
    OrchestratorConfig,
    QualityConfig,
    PathConfig,
    LoggingConfig,
    Config,
    # Global management functions
    get_config,
    set_config,
    reset_config,
    init_config,
)

__all__ = [
    # 基础ID类型
    "AgentId",
    "TaskId",
    "ArtifactId",
    "generate_id",
    # 枚举类型
    "AgentRole",
    "ExpertiseLevel",
    "AgentCapability",
    "TaskStatus",
    "TaskPriority",
    "MessageType",
    "ArtifactType",
    "ToolType",
    # 数据类
    "AgentProfile",
    "Task",
    "TaskContext",
    "Artifact",
    "QualityRequirements",
    "TaskResult",
    "ReasoningStep",
    "ReviewComment",
    "AgentMessage",
    "AgentState",
    # 基础异常
    "ChairmanAgentError",
    # LLM相关异常
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMResponseError",
    # Agent相关异常
    "AgentError",
    "AgentNotFoundError",
    "TaskExecutionError",
    "CapabilityMismatchError",
    # Workflow相关异常
    "WorkflowError",
    "QualityGateError",
    "PhaseTransitionError",
    "DependencyError",
    # Tool相关异常
    "ToolError",
    "ToolExecutionError",
    "ToolTimeoutError",
    # 协议
    "LLMClientProtocol",
    "ToolExecutorProtocol",
    "MessageBrokerProtocol",
    "AgentRegistryProtocol",
    # 配置管理
    "ConfigurationError",
    "ConfigValidationErr",
    "ConfigLoadError",
    "LLMConfig",
    "TeamConfig",
    "OrchestratorConfig",
    "QualityConfig",
    "PathConfig",
    "LoggingConfig",
    "Config",
    "get_config",
    "set_config",
    "reset_config",
    "init_config",
]
