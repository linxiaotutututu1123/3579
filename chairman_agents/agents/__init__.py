"""智能体模块.

本模块提供智能体基类和专家智能体实现。

结构:
    base: 智能体基类和配置
    experts: 专家智能体实现

Example:
    >>> from chairman_agents.agents import BaseExpertAgent, AgentConfig
    >>> from chairman_agents.agents.experts import FrontendEngineerAgent
"""

from __future__ import annotations

from chairman_agents.agents.base import (
    # 基类
    AgentConfig,
    BaseExpertAgent,
    # 协作类型
    CollaborationStatus,
    FeedbackItem,
    HelpRequest,
    ReviewRequest,
    # 协议
    AgentRegistryProtocol,
    LLMClientProtocol,
    MessageBrokerProtocol,
    ToolExecutorProtocol,
)

__all__ = [
    # 基类
    "BaseExpertAgent",
    "AgentConfig",
    # 协作类型
    "CollaborationStatus",
    "ReviewRequest",
    "HelpRequest",
    "FeedbackItem",
    # 协议
    "LLMClientProtocol",
    "ToolExecutorProtocol",
    "MessageBrokerProtocol",
    "AgentRegistryProtocol",
]
