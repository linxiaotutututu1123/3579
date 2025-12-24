"""LLM响应缓存模块 - 基于LRU的内存缓存.

提供LLM响应缓存功能:
- 基于prompt hash的缓存键
- LRU淘汰策略
- 可选TTL过期
- 线程安全
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# =============================================================================
# 缓存配置
# =============================================================================


@dataclass
class CacheConfig:
    """缓存配置.

    Attributes:
        enabled: 是否启用缓存
        max_size: 最大缓存条目数
        ttl_seconds: 缓存过期时间(秒), None表示永不过期
        include_model: 缓存键是否包含模型名称
        include_temperature: 缓存键是否包含温度参数
    """

    enabled: bool = True
    max_size: int = 1000
    ttl_seconds: float | None = None
    include_model: bool = True
    include_temperature: bool = True


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目.

    Attributes:
        value: 缓存的值
        created_at: 创建时间戳
        hits: 命中次数
    """

    value: T
    created_at: float = field(default_factory=time.time)
    hits: int = 0

    def is_expired(self, ttl_seconds: float | None) -> bool:
        """检查是否过期."""
        if ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > ttl_seconds


@dataclass
class CacheStats:
    """缓存统计信息.

    Attributes:
        hits: 缓存命中次数
        misses: 缓存未命中次数
        evictions: 淘汰次数
        expired: 过期淘汰次数
        current_size: 当前缓存大小
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expired": self.expired,
            "current_size": self.current_size,
            "hit_rate": f"{self.hit_rate:.2%}",
        }


# =============================================================================
# 缓存键生成
# =============================================================================


def generate_cache_key(
    prompt: str,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    messages: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """生成缓存键.

    基于输入参数生成唯一的缓存键(SHA256 hash).

    Args:
        prompt: 提示词
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大token数
        messages: 消息列表(用于chat接口)
        extra: 额外参数

    Returns:
        str: 缓存键(64字符的十六进制字符串)
    """
    key_data: dict[str, Any] = {}

    if prompt:
        key_data["prompt"] = prompt

    if messages:
        # 将消息列表序列化为稳定的字符串
        key_data["messages"] = messages

    if model is not None:
        key_data["model"] = model

    if temperature is not None:
        # 使用固定精度避免浮点数精度问题
        key_data["temperature"] = round(temperature, 4)

    if max_tokens is not None:
        key_data["max_tokens"] = max_tokens

    if extra:
        key_data["extra"] = extra

    # 序列化并计算哈希
    key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


# =============================================================================
# LRU缓存实现
# =============================================================================


class LRUCache(Generic[T]):
    """线程安全的LRU缓存.

    使用OrderedDict实现LRU淘汰策略.
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """初始化LRU缓存.

        Args:
            config: 缓存配置
        """
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

    @property
    def config(self) -> CacheConfig:
        """返回缓存配置."""
        return self._config

    @property
    def stats(self) -> CacheStats:
        """返回缓存统计."""
        with self._lock:
            self._stats.current_size = len(self._cache)
            return self._stats

    def get(self, key: str) -> T | None:
        """获取缓存值.

        如果缓存命中且未过期,返回缓存值并更新访问顺序.
        如果缓存未命中或已过期,返回None.

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        if not self._config.enabled:
            return None

        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired(self._config.ttl_seconds):
                del self._cache[key]
                self._stats.expired += 1
                self._stats.misses += 1
                return None

            # 更新访问顺序(移到末尾表示最近使用)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1

            return entry.value

    def set(self, key: str, value: T) -> None:
        """设置缓存值.

        如果达到最大容量,淘汰最久未使用的条目.

        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self._config.enabled:
            return

        with self._lock:
            # 如果key已存在,先删除
            if key in self._cache:
                del self._cache[key]

            # 检查容量,需要时淘汰最久未使用的条目
            while len(self._cache) >= self._config.max_size:
                self._cache.popitem(last=False)
                self._stats.evictions += 1

            # 添加新条目
            self._cache[key] = CacheEntry(value=value)

    def delete(self, key: str) -> bool:
        """删除缓存条目.

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """清空缓存.

        Returns:
            清除的条目数
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """清理过期条目.

        Returns:
            清理的条目数
        """
        if self._config.ttl_seconds is None:
            return 0

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired(self._config.ttl_seconds)
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.expired += 1

            return len(expired_keys)

    def contains(self, key: str) -> bool:
        """检查键是否存在且未过期.

        Args:
            key: 缓存键

        Returns:
            是否存在且未过期
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired(self._config.ttl_seconds):
                del self._cache[key]
                self._stats.expired += 1
                return False

            return True

    def __len__(self) -> int:
        """返回缓存大小."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """检查键是否存在."""
        return self.contains(key)


# =============================================================================
# LLM缓存包装器
# =============================================================================


class LLMResponseCache:
    """LLM响应缓存.

    封装LRU缓存,提供针对LLM响应的便捷接口.
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """初始化LLM响应缓存.

        Args:
            config: 缓存配置
        """
        self._config = config or CacheConfig()
        self._cache: LRUCache[Any] = LRUCache(self._config)

    @property
    def config(self) -> CacheConfig:
        """返回缓存配置."""
        return self._config

    @property
    def stats(self) -> CacheStats:
        """返回缓存统计."""
        return self._cache.stats

    @property
    def enabled(self) -> bool:
        """返回缓存是否启用."""
        return self._config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置缓存启用状态."""
        self._config.enabled = value

    def get_completion(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any | None:
        """获取补全结果缓存.

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            缓存的CompletionResult或None
        """
        key = generate_cache_key(
            prompt,
            model=model if self._config.include_model else None,
            temperature=temperature if self._config.include_temperature else None,
            max_tokens=max_tokens,
        )
        return self._cache.get(key)

    def set_completion(
        self,
        prompt: str,
        result: Any,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """缓存补全结果.

        Args:
            prompt: 提示词
            result: CompletionResult
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        key = generate_cache_key(
            prompt,
            model=model if self._config.include_model else None,
            temperature=temperature if self._config.include_temperature else None,
            max_tokens=max_tokens,
        )
        self._cache.set(key, result)

    def get_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any | None:
        """获取聊天结果缓存.

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            缓存的ChatResult或None
        """
        key = generate_cache_key(
            "",
            messages=messages,
            model=model if self._config.include_model else None,
            temperature=temperature if self._config.include_temperature else None,
            max_tokens=max_tokens,
        )
        return self._cache.get(key)

    def set_chat(
        self,
        messages: list[dict[str, Any]],
        result: Any,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """缓存聊天结果.

        Args:
            messages: 消息列表
            result: ChatResult
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        """
        key = generate_cache_key(
            "",
            messages=messages,
            model=model if self._config.include_model else None,
            temperature=temperature if self._config.include_temperature else None,
            max_tokens=max_tokens,
        )
        self._cache.set(key, result)

    def clear(self) -> int:
        """清空缓存.

        Returns:
            清除的条目数
        """
        return self._cache.clear()

    def cleanup(self) -> int:
        """清理过期条目.

        Returns:
            清理的条目数
        """
        return self._cache.cleanup_expired()


# =============================================================================
# 全局缓存实例
# =============================================================================

_global_cache: LLMResponseCache | None = None
_global_cache_lock = threading.Lock()


def get_global_cache(config: CacheConfig | None = None) -> LLMResponseCache:
    """获取全局缓存实例.

    Args:
        config: 缓存配置(仅在首次调用时生效)

    Returns:
        LLMResponseCache: 全局缓存实例
    """
    global _global_cache

    with _global_cache_lock:
        if _global_cache is None:
            _global_cache = LLMResponseCache(config)
        return _global_cache


def reset_global_cache(config: CacheConfig | None = None) -> LLMResponseCache:
    """重置全局缓存实例.

    Args:
        config: 新的缓存配置

    Returns:
        LLMResponseCache: 新的全局缓存实例
    """
    global _global_cache

    with _global_cache_lock:
        _global_cache = LLMResponseCache(config)
        return _global_cache


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 配置
    "CacheConfig",
    "CacheEntry",
    "CacheStats",
    # 缓存键
    "generate_cache_key",
    # 缓存实现
    "LRUCache",
    "LLMResponseCache",
    # 全局缓存
    "get_global_cache",
    "reset_global_cache",
]
