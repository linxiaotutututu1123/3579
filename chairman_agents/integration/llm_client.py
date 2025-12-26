"""LLM客户端模块 - 支持多种LLM提供商的统一接口.

提供统一的LLM客户端接口和多个实现:
- LLMClient: Protocol定义的统一接口
- AnthropicClient: Anthropic Claude API客户端
- OpenAIClient: OpenAI API客户端
- MockClient: 测试用模拟客户端

支持响应缓存:
- 基于prompt hash的缓存键
- LRU淘汰策略
- 可选TTL过期
"""

from __future__ import annotations

import asyncio
import copy
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from chairman_agents.core.types import generate_id

if TYPE_CHECKING:
    from chairman_agents.integration.llm_cache import CacheConfig, LLMResponseCache


# =============================================================================
# 数据结构定义
# =============================================================================


class MessageRole(Enum):
    """消息角色枚举."""

    SYSTEM = "system"
    """系统消息"""

    USER = "user"
    """用户消息"""

    ASSISTANT = "assistant"
    """助手消息"""

    TOOL = "tool"
    """工具调用结果"""


@dataclass
class Message:
    """聊天消息结构.

    Attributes:
        role: 消息角色
        content: 消息内容
        name: 可选的发送者名称
        tool_call_id: 工具调用ID(用于工具结果)
        metadata: 额外元数据
    """

    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        result: dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            result["name"] = self.name
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class ToolCall:
    """工具调用请求.

    Attributes:
        id: 工具调用唯一ID
        name: 工具名称
        arguments: 工具参数(JSON字符串)
    """

    id: str = field(default_factory=lambda: generate_id("tool"))
    name: str = ""
    arguments: str = "{}"


@dataclass
class TokenUsage:
    """Token使用统计.

    Attributes:
        prompt_tokens: 提示词token数
        completion_tokens: 补全token数
        total_tokens: 总token数
        cached_tokens: 缓存命中的token数
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass
class CompletionResult:
    """补全结果.

    Attributes:
        id: 请求唯一ID
        content: 生成的内容
        finish_reason: 结束原因(stop, length, tool_calls等)
        model: 使用的模型
        usage: Token使用统计
        tool_calls: 工具调用请求列表
        created_at: 创建时间
        latency_ms: 延迟(毫秒)
    """

    id: str = field(default_factory=lambda: generate_id("completion"))
    content: str = ""
    finish_reason: str = "stop"
    model: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    tool_calls: list[ToolCall] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0


@dataclass
class ChatResult(CompletionResult):
    """聊天结果,继承自CompletionResult.

    Additional Attributes:
        messages: 对话历史(包含响应)
    """

    messages: list[Message] = field(default_factory=list)


@dataclass
class StreamChunk:
    """流式响应块.

    Attributes:
        delta: 增量内容
        is_final: 是否为最后一块
        accumulated: 累积内容
        finish_reason: 结束原因(仅最后一块)
    """

    delta: str = ""
    is_final: bool = False
    accumulated: str = ""
    finish_reason: str | None = None


@dataclass
class LLMConfig:
    """LLM客户端配置.

    Attributes:
        api_key: API密钥
        base_url: API基础URL
        model: 默认模型
        temperature: 温度参数
        max_tokens: 最大token数
        timeout: 超时时间(秒)
        max_retries: 最大重试次数
        retry_delay: 重试延迟(秒)
        cache_enabled: 是否启用响应缓存
        cache_max_size: 缓存最大条目数
        cache_ttl_seconds: 缓存过期时间(秒), None表示永不过期
    """

    api_key: str = ""
    base_url: str | None = None
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_enabled: bool = True
    cache_max_size: int = 1000
    cache_ttl_seconds: float | None = None


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class LLMClient(Protocol):
    """LLM客户端协议定义.

    定义所有LLM客户端必须实现的接口.
    """

    @property
    def provider(self) -> str:
        """返回提供商名称."""
        ...

    @property
    def default_model(self) -> str:
        """返回默认模型名称."""
        ...

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """执行文本补全.

        Args:
            prompt: 输入提示词
            model: 使用的模型(可选,使用默认模型)
            temperature: 温度参数
            max_tokens: 最大生成token数
            stop: 停止序列
            **kwargs: 其他参数

        Returns:
            CompletionResult: 补全结果
        """
        ...

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """执行聊天补全.

        Args:
            messages: 消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 可用工具定义
            **kwargs: 其他参数

        Returns:
            ChatResult: 聊天结果
        """
        ...

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式文本补全.

        Args:
            prompt: 输入提示词
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Yields:
            StreamChunk: 流式响应块
        """
        ...

    async def stream_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天补全.

        Args:
            messages: 消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Yields:
            StreamChunk: 流式响应块
        """
        ...


# =============================================================================
# 基础实现
# =============================================================================


class BaseLLMClient(ABC):
    """LLM客户端基类.

    提供通用功能实现:
    - 配置管理
    - 重试逻辑
    - 错误处理
    - 响应缓存
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化客户端.

        Args:
            config: 客户端配置
        """
        self._config = config
        self._request_count = 0
        self._total_tokens = 0
        self._cache: LLMResponseCache | None = None

        # 初始化缓存
        if config.cache_enabled:
            self._init_cache()

    def _init_cache(self) -> None:
        """初始化响应缓存."""
        from chairman_agents.integration.llm_cache import CacheConfig, LLMResponseCache

        cache_config = CacheConfig(
            enabled=self._config.cache_enabled,
            max_size=self._config.cache_max_size,
            ttl_seconds=self._config.cache_ttl_seconds,
        )
        self._cache = LLMResponseCache(cache_config)

    @property
    def cache(self) -> LLMResponseCache | None:
        """返回缓存实例."""
        return self._cache

    @property
    def cache_enabled(self) -> bool:
        """返回缓存是否启用."""
        return self._cache is not None and self._cache.enabled

    @cache_enabled.setter
    def cache_enabled(self, value: bool) -> None:
        """设置缓存启用状态."""
        if self._cache is None and value:
            self._init_cache()
        elif self._cache is not None:
            self._cache.enabled = value

    @property
    @abstractmethod
    def provider(self) -> str:
        """返回提供商名称."""
        ...

    @property
    def default_model(self) -> str:
        """返回默认模型名称."""
        return self._config.model

    @property
    def config(self) -> LLMConfig:
        """返回配置."""
        return self._config

    @property
    def request_count(self) -> int:
        """返回请求计数."""
        return self._request_count

    @property
    def total_tokens(self) -> int:
        """返回总token使用量."""
        return self._total_tokens

    def _get_model(self, model: str | None) -> str:
        """获取模型名称."""
        return model or self._config.model

    def _get_temperature(self, temperature: float | None) -> float:
        """获取温度参数."""
        return temperature if temperature is not None else self._config.temperature

    def _get_max_tokens(self, max_tokens: int | None) -> int:
        """获取最大token数."""
        return max_tokens or self._config.max_tokens

    async def _retry_with_backoff(
        self,
        coro_func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """带退避的重试逻辑.

        Args:
            coro_func: 协程函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            协程函数的返回值

        Raises:
            Exception: 超过最大重试次数后抛出最后一个异常
        """
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self._config.max_retries - 1:
                    delay = self._config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry failure")

    def _update_stats(self, usage: TokenUsage) -> None:
        """更新统计信息."""
        self._request_count += 1
        self._total_tokens += usage.total_tokens

    def _get_cached_completion(
        self,
        prompt: str,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> CompletionResult | None:
        """获取缓存的补全结果.

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            缓存的CompletionResult或None
        """
        if self._cache is None:
            return None

        cached = self._cache.get_completion(
            prompt,
            model=self._get_model(model),
            temperature=self._get_temperature(temperature),
            max_tokens=self._get_max_tokens(max_tokens),
        )

        if cached is not None:
            # 返回深拷贝避免缓存污染
            return copy.deepcopy(cached)
        return None

    def _cache_completion(
        self,
        prompt: str,
        result: CompletionResult,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        """缓存补全结果.

        Args:
            prompt: 提示词
            result: CompletionResult
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        if self._cache is None:
            return

        self._cache.set_completion(
            prompt,
            result,
            model=self._get_model(model),
            temperature=self._get_temperature(temperature),
            max_tokens=self._get_max_tokens(max_tokens),
        )

    def _get_cached_chat(
        self,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> ChatResult | None:
        """获取缓存的聊天结果.

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            缓存的ChatResult或None
        """
        if self._cache is None:
            return None

        # 将消息列表转换为可序列化的格式
        messages_dict = [msg.to_dict() for msg in messages]

        cached = self._cache.get_chat(
            messages_dict,
            model=self._get_model(model),
            temperature=self._get_temperature(temperature),
            max_tokens=self._get_max_tokens(max_tokens),
        )

        if cached is not None:
            # 返回深拷贝避免缓存污染
            return copy.deepcopy(cached)
        return None

    def _cache_chat(
        self,
        messages: list[Message],
        result: ChatResult,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        """缓存聊天结果.

        Args:
            messages: 消息列表
            result: ChatResult
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        if self._cache is None:
            return

        # 将消息列表转换为可序列化的格式
        messages_dict = [msg.to_dict() for msg in messages]

        self._cache.set_chat(
            messages_dict,
            result,
            model=self._get_model(model),
            temperature=self._get_temperature(temperature),
            max_tokens=self._get_max_tokens(max_tokens),
        )


# =============================================================================
# Anthropic客户端实现
# =============================================================================


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API客户端.

    支持Claude系列模型的API调用.
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化Anthropic客户端.

        Args:
            config: 客户端配置
        """
        super().__init__(config)
        if not config.base_url:
            self._config.base_url = "https://api.anthropic.com"
        if not config.model:
            self._config.model = "claude-3-5-sonnet-20241022"

        self._client: Any = None

    @property
    def provider(self) -> str:
        """返回提供商名称."""
        return "anthropic"

    async def _ensure_client(self) -> Any:
        """确保客户端已初始化."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                )
            except ImportError:
                raise ImportError(
                    "anthropic package is required. Install with: pip install anthropic"
                )
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """执行文本补全."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        result = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return CompletionResult(
            id=result.id,
            content=result.content,
            finish_reason=result.finish_reason,
            model=result.model,
            usage=result.usage,
            tool_calls=result.tool_calls,
            created_at=result.created_at,
            latency_ms=result.latency_ms,
        )

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """执行聊天补全."""
        # 不带工具时检查缓存(工具调用结果不可缓存)
        use_cache = tools is None and not kwargs.get("skip_cache", False)

        if use_cache:
            cached = self._get_cached_chat(messages, model, temperature, max_tokens)
            if cached is not None:
                return cached

        client = await self._ensure_client()
        start_time = time.perf_counter()

        # 构建消息列表
        api_messages = []
        system_content = ""

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            else:
                api_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._get_model(model),
            "messages": api_messages,
            "max_tokens": self._get_max_tokens(max_tokens),
            "temperature": self._get_temperature(temperature),
        }

        if system_content:
            request_params["system"] = system_content

        if tools:
            request_params["tools"] = tools

        # 发送请求
        response = await self._retry_with_backoff(
            client.messages.create,
            **request_params,
        )

        latency = (time.perf_counter() - start_time) * 1000

        # 解析响应
        content = ""
        tool_calls = []

        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=str(block.input),
                ))

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        self._update_stats(usage)

        # 添加助手响应到消息历史
        response_messages = messages.copy()
        response_messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=content,
        ))

        result = ChatResult(
            id=response.id,
            content=content,
            finish_reason=response.stop_reason or "stop",
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            latency_ms=latency,
            messages=response_messages,
        )

        # 缓存结果
        if use_cache:
            self._cache_chat(messages, result, model, temperature, max_tokens)

        return result

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式文本补全."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        async for chunk in self.stream_chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    async def stream_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天补全."""
        client = await self._ensure_client()

        # 构建消息列表
        api_messages = []
        system_content = ""

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_content = msg.content
            else:
                api_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._get_model(model),
            "messages": api_messages,
            "max_tokens": self._get_max_tokens(max_tokens),
            "temperature": self._get_temperature(temperature),
        }

        if system_content:
            request_params["system"] = system_content

        accumulated = ""

        async with client.messages.stream(**request_params) as stream:
            async for text in stream.text_stream:
                accumulated += text
                yield StreamChunk(
                    delta=text,
                    is_final=False,
                    accumulated=accumulated,
                )

        yield StreamChunk(
            delta="",
            is_final=True,
            accumulated=accumulated,
            finish_reason="stop",
        )


# =============================================================================
# OpenAI客户端实现
# =============================================================================


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端.

    支持GPT系列模型的API调用.
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化OpenAI客户端.

        Args:
            config: 客户端配置
        """
        super().__init__(config)
        if not config.base_url:
            self._config.base_url = "https://api.openai.com/v1"
        if not config.model:
            self._config.model = "gpt-4o"

        self._client: Any = None

    @property
    def provider(self) -> str:
        """返回提供商名称."""
        return "openai"

    async def _ensure_client(self) -> Any:
        """确保客户端已初始化."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AsyncOpenAI(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                )
            except ImportError:
                raise ImportError(
                    "openai package is required. Install with: pip install openai"
                )
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """执行文本补全."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        result = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return CompletionResult(
            id=result.id,
            content=result.content,
            finish_reason=result.finish_reason,
            model=result.model,
            usage=result.usage,
            tool_calls=result.tool_calls,
            created_at=result.created_at,
            latency_ms=result.latency_ms,
        )

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """执行聊天补全."""
        # 不带工具时检查缓存(工具调用结果不可缓存)
        use_cache = tools is None and not kwargs.get("skip_cache", False)

        if use_cache:
            cached = self._get_cached_chat(messages, model, temperature, max_tokens)
            if cached is not None:
                return cached

        client = await self._ensure_client()
        start_time = time.perf_counter()

        # 构建消息列表
        api_messages = [msg.to_dict() for msg in messages]

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._get_model(model),
            "messages": api_messages,
            "max_tokens": self._get_max_tokens(max_tokens),
            "temperature": self._get_temperature(temperature),
        }

        if tools:
            request_params["tools"] = tools

        # 发送请求
        response = await self._retry_with_backoff(
            client.chat.completions.create,
            **request_params,
        )

        latency = (time.perf_counter() - start_time) * 1000

        # 解析响应
        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ))

        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        self._update_stats(usage)

        # 添加助手响应到消息历史
        response_messages = messages.copy()
        response_messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=content,
        ))

        result = ChatResult(
            id=response.id,
            content=content,
            finish_reason=choice.finish_reason or "stop",
            model=response.model,
            usage=usage,
            tool_calls=tool_calls,
            latency_ms=latency,
            messages=response_messages,
        )

        # 缓存结果
        if use_cache:
            self._cache_chat(messages, result, model, temperature, max_tokens)

        return result

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式文本补全."""
        messages = [Message(role=MessageRole.USER, content=prompt)]
        async for chunk in self.stream_chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    async def stream_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天补全."""
        client = await self._ensure_client()

        # 构建消息列表
        api_messages = [msg.to_dict() for msg in messages]

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._get_model(model),
            "messages": api_messages,
            "max_tokens": self._get_max_tokens(max_tokens),
            "temperature": self._get_temperature(temperature),
            "stream": True,
        }

        accumulated = ""
        finish_reason = None

        stream = await client.chat.completions.create(**request_params)

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                accumulated += content
                finish_reason = chunk.choices[0].finish_reason

                yield StreamChunk(
                    delta=content,
                    is_final=finish_reason is not None,
                    accumulated=accumulated,
                    finish_reason=finish_reason,
                )


# =============================================================================
# Mock客户端(测试用)
# =============================================================================


class MockLLMClient(BaseLLMClient):
    """模拟LLM客户端,用于测试.

    可配置固定响应或响应生成函数.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        responses: list[str] | None = None,
        response_generator: Any = None,
    ) -> None:
        """初始化Mock客户端.

        Args:
            config: 客户端配置
            responses: 预设响应列表(循环使用)
            response_generator: 响应生成函数
        """
        super().__init__(config or LLMConfig(model="mock-model"))
        self._responses = responses or ["This is a mock response."]
        self._response_generator = response_generator
        self._response_index = 0
        self._call_history: list[dict[str, Any]] = []

    @property
    def provider(self) -> str:
        """返回提供商名称."""
        return "mock"

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """返回调用历史."""
        return self._call_history

    def _get_response(self, prompt: str) -> str:
        """获取响应."""
        if self._response_generator:
            return self._response_generator(prompt)

        response = self._responses[self._response_index % len(self._responses)]
        self._response_index += 1
        return response

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult:
        """执行文本补全."""
        self._call_history.append({
            "method": "complete",
            "prompt": prompt,
            "model": model,
            "kwargs": kwargs,
        })

        content = self._get_response(prompt)
        usage = TokenUsage(
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(prompt.split()) + len(content.split()),
        )

        self._update_stats(usage)

        return CompletionResult(
            content=content,
            model=self._get_model(model),
            usage=usage,
        )

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """执行聊天补全."""
        self._call_history.append({
            "method": "chat",
            "messages": messages,
            "model": model,
            "kwargs": kwargs,
        })

        # 使用最后一条用户消息作为输入
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_msg = msg.content
                break

        content = self._get_response(last_user_msg)
        usage = TokenUsage(
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=len(content.split()),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(content.split()),
        )

        self._update_stats(usage)

        response_messages = messages.copy()
        response_messages.append(Message(
            role=MessageRole.ASSISTANT,
            content=content,
        ))

        return ChatResult(
            content=content,
            model=self._get_model(model),
            usage=usage,
            messages=response_messages,
        )

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式文本补全."""
        content = self._get_response(prompt)
        words = content.split()
        accumulated = ""

        for i, word in enumerate(words):
            delta = word + " "
            accumulated += delta
            yield StreamChunk(
                delta=delta,
                is_final=(i == len(words) - 1),
                accumulated=accumulated,
                finish_reason="stop" if i == len(words) - 1 else None,
            )
            await asyncio.sleep(0.01)  # 模拟延迟

    async def stream_chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天补全."""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_msg = msg.content
                break

        async for chunk in self.stream(
            last_user_msg,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk


# =============================================================================
# 工厂函数
# =============================================================================


def create_llm_client(
    provider: str,
    config: LLMConfig | None = None,
    **kwargs: Any,
) -> BaseLLMClient:
    """创建LLM客户端实例.

    Args:
        provider: 提供商名称(anthropic, openai, mock)
        config: 客户端配置
        **kwargs: 额外配置参数

    Returns:
        BaseLLMClient: LLM客户端实例

    Raises:
        ValueError: 不支持的提供商
    """
    if config is None:
        config = LLMConfig(**kwargs)

    provider_lower = provider.lower()

    if provider_lower == "anthropic":
        return AnthropicClient(config)
    elif provider_lower == "openai":
        return OpenAIClient(config)
    elif provider_lower == "mock":
        return MockLLMClient(config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 数据结构
    "MessageRole",
    "Message",
    "ToolCall",
    "TokenUsage",
    "CompletionResult",
    "ChatResult",
    "StreamChunk",
    "LLMConfig",
    # 协议
    "LLMClient",
    # 实现
    "BaseLLMClient",
    "AnthropicClient",
    "OpenAIClient",
    "MockLLMClient",
    # 工厂
    "create_llm_client",
]
