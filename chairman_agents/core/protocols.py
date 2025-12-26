"""统一协议定义模块.

本模块集中定义所有协议接口，避免重复定义，确保接口一致性。

协议列表:
    - LLMClientProtocol: LLM 客户端协议
    - ToolExecutorProtocol: 工具执行器协议
    - MessageBrokerProtocol: 消息代理协议
    - AgentRegistryProtocol: 智能体注册表协议

Example:
    >>> from chairman_agents.core.protocols import LLMClientProtocol
    >>> class MyLLMClient(LLMClientProtocol):
    ...     async def generate(self, prompt: str, **kwargs) -> str:
    ...         return "response"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from chairman_agents.core.types import (
        AgentCapability,
        AgentId,
        AgentMessage,
        AgentProfile,
        AgentRole,
        MessageType,
        ToolType,
    )


# =============================================================================
# LLM 客户端协议
# =============================================================================


@runtime_checkable
class LLMClientProtocol(Protocol):
    """LLM 客户端协议.

    定义与大语言模型交互所需的接口。
    所有 LLM 客户端实现都应遵循此协议。

    Methods:
        generate: 生成文本响应
        complete: generate 的别名（兼容性）

    Example:
        >>> class OpenAIClient(LLMClientProtocol):
        ...     async def generate(
        ...         self,
        ...         prompt: str,
        ...         *,
        ...         temperature: float = 0.7,
        ...         max_tokens: int = 2048,
        ...     ) -> str:
        ...         # 调用 OpenAI API
        ...         return response
    """

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本响应.

        Args:
            prompt: 输入提示
            temperature: 采样温度 (0.0-2.0)
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本响应
        """
        ...

    async def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """生成补全响应（generate 的别名）.

        Args:
            prompt: 输入提示
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本响应
        """
        ...


# =============================================================================
# 工具执行器协议
# =============================================================================


@runtime_checkable
class ToolExecutorProtocol(Protocol):
    """工具执行器协议.

    定义工具执行所需的接口。

    Example:
        >>> class MyToolExecutor(ToolExecutorProtocol):
        ...     async def execute(
        ...         self,
        ...         tool_type: ToolType,
        ...         params: dict[str, Any],
        ...     ) -> dict[str, Any]:
        ...         # 执行工具
        ...         return {"result": "success"}
    """

    async def execute(
        self,
        tool_type: ToolType,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行工具.

        Args:
            tool_type: 工具类型
            params: 工具参数

        Returns:
            工具执行结果
        """
        ...


# =============================================================================
# 消息代理协议
# =============================================================================


@runtime_checkable
class MessageBrokerProtocol(Protocol):
    """消息代理协议.

    定义智能体间消息传递的接口。

    Example:
        >>> class MyMessageBroker(MessageBrokerProtocol):
        ...     async def send_message(self, message: AgentMessage) -> None:
        ...         # 发送消息
        ...         pass
    """

    async def send_message(self, message: AgentMessage) -> None:
        """发送消息.

        Args:
            message: 要发送的消息
        """
        ...

    async def receive_messages(
        self,
        agent_id: AgentId,
        message_types: list[MessageType] | None = None,
        limit: int = 10,
    ) -> list[AgentMessage]:
        """接收消息.

        Args:
            agent_id: 接收者智能体 ID
            message_types: 消息类型过滤
            limit: 最大返回数量

        Returns:
            消息列表
        """
        ...

    async def broadcast(
        self,
        message: AgentMessage,
        target_roles: list[AgentRole] | None = None,
    ) -> None:
        """广播消息.

        Args:
            message: 要广播的消息
            target_roles: 目标角色过滤
        """
        ...


# =============================================================================
# 智能体注册表协议
# =============================================================================


@runtime_checkable
class AgentRegistryProtocol(Protocol):
    """智能体注册表协议.

    定义智能体发现和管理的接口。

    Example:
        >>> class MyAgentRegistry(AgentRegistryProtocol):
        ...     def find_agents_by_capability(
        ...         self,
        ...         capability: AgentCapability,
        ...         min_level: int = 1,
        ...     ) -> list[AgentId]:
        ...         return ["agent_1", "agent_2"]
    """

    def find_agents_by_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> list[AgentId]:
        """根据能力查找智能体.

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            符合条件的智能体 ID 列表
        """
        ...

    def find_agents_by_role(self, role: AgentRole) -> list[AgentId]:
        """根据角色查找智能体.

        Args:
            role: 目标角色

        Returns:
            具有该角色的智能体 ID 列表
        """
        ...

    def get_agent_profile(self, agent_id: AgentId) -> AgentProfile | None:
        """获取智能体配置.

        Args:
            agent_id: 智能体 ID

        Returns:
            智能体配置，不存在返回 None
        """
        ...


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "LLMClientProtocol",
    "ToolExecutorProtocol",
    "MessageBrokerProtocol",
    "AgentRegistryProtocol",
]
