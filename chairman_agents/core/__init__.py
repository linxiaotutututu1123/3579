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
)

from .exceptions import (
    # 基础异常
    ChairmanAgentError,
    # LLM相关异常
    LLMError,
    LLMRateLimitError,
    LLMConnectionError,
    LLMResponseError,
    # Agent相关异常
    AgentError,
    AgentNotFoundError,
    AgentBusyError,
    AgentCapabilityError,
    # Task相关异常
    TaskError,
    TaskNotFoundError,
    TaskExecutionError,
    TaskTimeoutError,
    TaskDependencyError,
    # 配置相关异常
    ConfigError,
    ConfigValidationError,
    # 通信相关异常
    CommunicationError,
    MessageDeliveryError,
)

from .config import (
    Config,
    get_config,
    set_config,
)

__all__ = [
    # 基础ID类型
    "AgentId",
    "TaskId",
    "ArtifactId",
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
    # 基础异常
    "ChairmanAgentError",
    # LLM相关异常
    "LLMError",
    "LLMRateLimitError",
    "LLMConnectionError",
    "LLMResponseError",
    # Agent相关异常
    "AgentError",
    "AgentNotFoundError",
    "AgentBusyError",
    "AgentCapabilityError",
    # Task相关异常
    "TaskError",
    "TaskNotFoundError",
    "TaskExecutionError",
    "TaskTimeoutError",
    "TaskDependencyError",
    # 配置相关异常
    "ConfigError",
    "ConfigValidationError",
    # 通信相关异常
    "CommunicationError",
    "MessageDeliveryError",
    # 配置管理
    "Config",
    "get_config",
    "set_config",
]
