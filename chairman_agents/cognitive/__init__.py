"""认知模块 - 推理、记忆、反思.

本模块提供智能体的认知能力，包括:
- 推理引擎: 思维链 (CoT) 和思维树 (ToT) 推理
- 记忆系统: 短期/长期记忆管理（待实现）
- 反思机制: 自我评估和改进（待实现）

Example:
    >>> from chairman_agents.cognitive import ReasoningEngine, ThoughtNode
    >>> engine = ReasoningEngine(llm_client)
    >>> result = await engine.chain_of_thought("设计一个 API")
"""

from __future__ import annotations

from chairman_agents.cognitive.reasoning import (
    LLMClientProtocol,
    ReasoningEngine,
    ReasoningResult,
    ReasoningStrategy,
    ThoughtNode,
)

__all__ = [
    # 推理引擎
    "ReasoningEngine",
    "ThoughtNode",
    "ReasoningResult",
    "ReasoningStrategy",
    "LLMClientProtocol",
]
