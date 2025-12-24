# Integration 模块 API

LLM客户端集成和响应缓存。

## llm_client 模块

### 数据类

#### MessageRole

消息角色枚举。

| 值 | 说明 |
|---|---|
| `SYSTEM` | 系统消息 |
| `USER` | 用户消息 |
| `ASSISTANT` | 助手消息 |
| `TOOL` | 工具调用结果 |

#### Message

聊天消息。

```python
@dataclass
class Message:
    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]
```

#### LLMConfig

客户端配置。

```python
@dataclass
class LLMConfig:
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
```

#### TokenUsage

Token使用统计。

```python
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
```

#### CompletionResult

补全结果。

```python
@dataclass
class CompletionResult:
    id: str
    content: str
    finish_reason: str = "stop"
    model: str = ""
    usage: TokenUsage
    tool_calls: list[ToolCall] = field(default_factory=list)
    latency_ms: float = 0.0
```

#### ChatResult

聊天结果（继承CompletionResult）。

```python
@dataclass
class ChatResult(CompletionResult):
    messages: list[Message] = field(default_factory=list)
```

#### StreamChunk

流式响应块。

```python
@dataclass
class StreamChunk:
    delta: str = ""
    is_final: bool = False
    accumulated: str = ""
    finish_reason: str | None = None
```

---

### LLMClient 协议

```python
@runtime_checkable
class LLMClient(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def default_model(self) -> str: ...

    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> CompletionResult: ...

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult: ...

    async def stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]: ...

    async def stream_chat(
        self,
        messages: list[Message],
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]: ...
```

---

### AnthropicClient

Anthropic Claude API客户端。

```python
class AnthropicClient(BaseLLMClient):
    def __init__(self, config: LLMConfig) -> None
```

**默认值：**
- `base_url`: `https://api.anthropic.com`
- `model`: `claude-3-5-sonnet-20241022`

**示例：**
```python
from chairman_agents.integration.llm_client import AnthropicClient, LLMConfig, Message, MessageRole

config = LLMConfig(api_key="sk-ant-xxx")
client = AnthropicClient(config)

result = await client.chat([
    Message(role=MessageRole.SYSTEM, content="你是一个助手"),
    Message(role=MessageRole.USER, content="你好"),
])
print(result.content)
```

---

### OpenAIClient

OpenAI API客户端。

```python
class OpenAIClient(BaseLLMClient):
    def __init__(self, config: LLMConfig) -> None
```

**默认值：**
- `base_url`: `https://api.openai.com/v1`
- `model`: `gpt-4o`

---

### MockLLMClient

测试用模拟客户端。

```python
class MockLLMClient(BaseLLMClient):
    def __init__(
        self,
        config: LLMConfig | None = None,
        responses: list[str] | None = None,
        response_generator: Any = None,
    ) -> None

    @property
    def call_history(self) -> list[dict[str, Any]]
```

**示例：**
```python
mock = MockLLMClient(responses=["响应1", "响应2"])
result = await mock.complete("测试")
assert result.content == "响应1"
```

---

### create_llm_client

工厂函数。

```python
def create_llm_client(
    provider: str,
    config: LLMConfig | None = None,
    **kwargs: Any,
) -> BaseLLMClient
```

**参数：**
- `provider` - 提供商名称：`anthropic`, `openai`, `mock`
- `config` - 客户端配置
- `**kwargs` - 额外配置参数

**示例：**
```python
client = create_llm_client(
    "anthropic",
    api_key="sk-ant-xxx",
    model="claude-3-5-sonnet-20241022",
)
```

---

## llm_cache 模块

### CacheConfig

缓存配置。

```python
@dataclass
class CacheConfig:
    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: float | None = None
    include_model: bool = True
    include_temperature: bool = True
```

### CacheStats

缓存统计。

```python
@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float
```

### LRUCache

线程安全的LRU缓存。

```python
class LRUCache(Generic[T]):
    def __init__(self, config: CacheConfig | None = None) -> None
    def get(self, key: str) -> T | None
    def set(self, key: str, value: T) -> None
    def delete(self, key: str) -> bool
    def clear(self) -> int
    def cleanup_expired(self) -> int
    def contains(self, key: str) -> bool
```

### LLMResponseCache

LLM响应缓存封装。

```python
class LLMResponseCache:
    def __init__(self, config: CacheConfig | None = None) -> None

    def get_completion(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any | None

    def set_completion(
        self,
        prompt: str,
        result: Any,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None

    def get_chat(
        self,
        messages: list[dict[str, Any]],
        **kwargs,
    ) -> Any | None

    def set_chat(
        self,
        messages: list[dict[str, Any]],
        result: Any,
        **kwargs,
    ) -> None

    def clear(self) -> int
    def cleanup(self) -> int
```

### 全局缓存

```python
def get_global_cache(config: CacheConfig | None = None) -> LLMResponseCache
def reset_global_cache(config: CacheConfig | None = None) -> LLMResponseCache
```

### generate_cache_key

生成缓存键。

```python
def generate_cache_key(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    messages: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> str
```

**返回：** SHA256哈希字符串(64字符)

**示例：**
```python
key = generate_cache_key(
    "Hello",
    model="gpt-4",
    temperature=0.7,
)
```
