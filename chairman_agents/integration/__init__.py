"""集成模块 - LLM客户端和模型注册."""

from __future__ import annotations

from chairman_agents.integration.llm_cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
    generate_cache_key,
    LRUCache,
    LLMResponseCache,
    get_global_cache,
    reset_global_cache,
)
from chairman_agents.integration.llm_client import (
    MessageRole,
    Message,
    ToolCall,
    TokenUsage,
    CompletionResult,
    ChatResult,
    StreamChunk,
    LLMConfig,
    LLMClient,
    BaseLLMClient,
    AnthropicClient,
    OpenAIClient,
    MockLLMClient,
    create_llm_client,
)
from chairman_agents.integration.model_registry import (
    ModelCapability,
    ModelProvider,
    ModelTier,
    ModelPricing,
    ModelLimits,
    ModelConfig,
    CLAUDE_3_5_SONNET,
    GPT_4O,
    ModelRegistry,
    get_registry,
)

__all__ = [
    # llm_cache
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    "generate_cache_key",
    "LRUCache",
    "LLMResponseCache",
    "get_global_cache",
    "reset_global_cache",
    # llm_client
    "MessageRole",
    "Message",
    "ToolCall",
    "TokenUsage",
    "CompletionResult",
    "ChatResult",
    "StreamChunk",
    "LLMConfig",
    "LLMClient",
    "BaseLLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "MockLLMClient",
    "create_llm_client",
    # model_registry
    "ModelCapability",
    "ModelProvider",
    "ModelTier",
    "ModelPricing",
    "ModelLimits",
    "ModelConfig",
    "CLAUDE_3_5_SONNET",
    "GPT_4O",
    "ModelRegistry",
    "get_registry",
]
