"""模型注册表模块 - 管理和配置LLM模型."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelCapability(Enum):
    """模型能力枚举."""
    CHAT = "chat"
    COMPLETION = "completion"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REASONING = "reasoning"
    MATH = "math"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    LONG_CONTEXT = "long_context"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"


class ModelProvider(Enum):
    """模型提供商枚举."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"


class ModelTier(Enum):
    """模型层级."""
    FLAGSHIP = "flagship"
    STANDARD = "standard"
    FAST = "fast"
    MINI = "mini"


@dataclass
class ModelPricing:
    """模型定价."""
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0


@dataclass
class ModelLimits:
    """模型限制."""
    max_context: int = 128000
    max_output: int = 4096


@dataclass
class ModelConfig:
    """模型配置."""
    id: str
    name: str
    provider: ModelProvider
    tier: ModelTier = ModelTier.STANDARD
    capabilities: list[ModelCapability] = field(default_factory=list)
    limits: ModelLimits = field(default_factory=ModelLimits)
    pricing: ModelPricing = field(default_factory=ModelPricing)
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_capability(self, cap: ModelCapability) -> bool:
        return cap in self.capabilities

    def supports_context_length(self, length: int) -> bool:
        return length <= self.limits.max_context

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1000) * self.pricing.input_per_1k + \
               (output_tokens / 1000) * self.pricing.output_per_1k


# 预定义模型
CLAUDE_3_5_SONNET = ModelConfig(
    id="claude-3-5-sonnet-20241022",
    name="Claude 3.5 Sonnet",
    provider=ModelProvider.ANTHROPIC,
    tier=ModelTier.FLAGSHIP,
    capabilities=[ModelCapability.CHAT, ModelCapability.CODE_GENERATION,
                  ModelCapability.REASONING, ModelCapability.VISION,
                  ModelCapability.FUNCTION_CALLING, ModelCapability.LONG_CONTEXT],
    limits=ModelLimits(max_context=200000, max_output=8192),
    pricing=ModelPricing(input_per_1k=0.003, output_per_1k=0.015),
    aliases=["sonnet", "claude-sonnet"],
)

GPT_4O = ModelConfig(
    id="gpt-4o",
    name="GPT-4o",
    provider=ModelProvider.OPENAI,
    tier=ModelTier.FLAGSHIP,
    capabilities=[ModelCapability.CHAT, ModelCapability.CODE_GENERATION,
                  ModelCapability.REASONING, ModelCapability.VISION,
                  ModelCapability.FUNCTION_CALLING],
    limits=ModelLimits(max_context=128000, max_output=16384),
    pricing=ModelPricing(input_per_1k=0.005, output_per_1k=0.015),
    aliases=["gpt4o", "4o"],
)


class ModelRegistry:
    """模型注册表."""

    def __init__(self) -> None:
        self._models: dict[str, ModelConfig] = {}
        self._aliases: dict[str, str] = {}
        self._default: str | None = None
        self._register_defaults()

    def _register_defaults(self) -> None:
        for m in [CLAUDE_3_5_SONNET, GPT_4O]:
            self.register(m)
        self._default = CLAUDE_3_5_SONNET.id

    def register(self, config: ModelConfig) -> None:
        self._models[config.id] = config
        for alias in config.aliases:
            self._aliases[alias.lower()] = config.id

    def get(self, model_id: str) -> ModelConfig | None:
        if model_id in self._models:
            return self._models[model_id]
        resolved = self._aliases.get(model_id.lower())
        return self._models.get(resolved) if resolved else None

    def get_or_default(self, model_id: str | None = None) -> ModelConfig | None:
        if model_id:
            if config := self.get(model_id):
                return config
        return self._models.get(self._default) if self._default else None

    def list_all(self) -> list[ModelConfig]:
        return list(self._models.values())

    def list_by_provider(self, provider: ModelProvider) -> list[ModelConfig]:
        return [m for m in self._models.values() if m.provider == provider]

    def list_by_capability(self, cap: ModelCapability) -> list[ModelConfig]:
        return [m for m in self._models.values() if m.has_capability(cap)]

    def find_best(
        self,
        required: list[ModelCapability],
        min_context: int = 0,
        prefer_provider: ModelProvider | None = None,
    ) -> ModelConfig | None:
        candidates = [
            m for m in self._models.values()
            if all(m.has_capability(c) for c in required)
            and m.supports_context_length(min_context)
        ]
        if not candidates:
            return None
        if prefer_provider:
            preferred = [m for m in candidates if m.provider == prefer_provider]
            if preferred:
                return preferred[0]
        return candidates[0]


_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


__all__ = [
    "ModelCapability", "ModelProvider", "ModelTier",
    "ModelPricing", "ModelLimits", "ModelConfig",
    "CLAUDE_3_5_SONNET", "GPT_4O",
    "ModelRegistry", "get_registry",
]
