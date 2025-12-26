"""Tests for LLM response cache module.

Tests cover:
- CacheConfig dataclass
- CacheEntry dataclass
- CacheStats statistics
- generate_cache_key() hash generation
- LRUCache thread-safe LRU cache
- LLMResponseCache completion and chat caching
- TTL expiration mechanism
- Cache hit/miss statistics
- Concurrent access (threading)
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import patch

import pytest

from chairman_agents.integration.llm_cache import (
    CacheConfig,
    CacheEntry,
    CacheStats,
    LLMResponseCache,
    LRUCache,
    generate_cache_key,
    get_global_cache,
    reset_global_cache,
)


# =============================================================================
# CacheConfig Tests
# =============================================================================


@pytest.mark.unit
class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_values(self) -> None:
        """Test CacheConfig default values."""
        config = CacheConfig()

        assert config.enabled is True
        assert config.max_size == 1000
        assert config.ttl_seconds is None
        assert config.include_model is True
        assert config.include_temperature is True

    def test_custom_values(self) -> None:
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            enabled=False,
            max_size=500,
            ttl_seconds=120.0,
            include_model=False,
            include_temperature=False,
        )

        assert config.enabled is False
        assert config.max_size == 500
        assert config.ttl_seconds == 120.0
        assert config.include_model is False
        assert config.include_temperature is False

    def test_ttl_seconds_float(self) -> None:
        """Test TTL with float values."""
        config = CacheConfig(ttl_seconds=0.5)
        assert config.ttl_seconds == 0.5


# =============================================================================
# CacheEntry Tests
# =============================================================================


@pytest.mark.unit
class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_creation(self) -> None:
        """Test CacheEntry creation."""
        entry = CacheEntry(value="test_value")

        assert entry.value == "test_value"
        assert entry.hits == 0
        assert isinstance(entry.created_at, float)

    def test_created_at_default(self) -> None:
        """Test created_at uses current time."""
        before = time.time()
        entry = CacheEntry(value="test")
        after = time.time()

        assert before <= entry.created_at <= after

    def test_is_expired_no_ttl(self) -> None:
        """Test is_expired returns False when TTL is None."""
        entry = CacheEntry(value="test")

        assert entry.is_expired(None) is False

    def test_is_expired_not_expired(self) -> None:
        """Test is_expired returns False when within TTL."""
        entry = CacheEntry(value="test")

        # 60 seconds TTL, just created
        assert entry.is_expired(60.0) is False

    def test_is_expired_expired(self) -> None:
        """Test is_expired returns True when past TTL."""
        entry = CacheEntry(value="test")
        # Manually set created_at to 2 seconds ago
        entry.created_at = time.time() - 2.0

        # 1 second TTL
        assert entry.is_expired(1.0) is True

    def test_hits_increment(self) -> None:
        """Test hits counter can be incremented."""
        entry = CacheEntry(value="test")
        entry.hits += 1
        entry.hits += 1

        assert entry.hits == 2

    def test_generic_type(self) -> None:
        """Test CacheEntry works with different types."""
        entry_str = CacheEntry[str](value="string")
        entry_dict = CacheEntry[dict](value={"key": "value"})
        entry_list = CacheEntry[list](value=[1, 2, 3])

        assert entry_str.value == "string"
        assert entry_dict.value == {"key": "value"}
        assert entry_list.value == [1, 2, 3]


# =============================================================================
# CacheStats Tests
# =============================================================================


@pytest.mark.unit
class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_default_values(self) -> None:
        """Test CacheStats default values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expired == 0
        assert stats.current_size == 0

    def test_hit_rate_zero_total(self) -> None:
        """Test hit_rate returns 0 when no requests."""
        stats = CacheStats()

        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit_rate calculation."""
        stats = CacheStats(hits=75, misses=25)

        assert stats.hit_rate == 0.75

    def test_hit_rate_all_hits(self) -> None:
        """Test hit_rate with 100% hits."""
        stats = CacheStats(hits=100, misses=0)

        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self) -> None:
        """Test hit_rate with 0% hits."""
        stats = CacheStats(hits=0, misses=100)

        assert stats.hit_rate == 0.0

    def test_to_dict(self) -> None:
        """Test to_dict conversion."""
        stats = CacheStats(
            hits=50,
            misses=50,
            evictions=10,
            expired=5,
            current_size=100,
        )
        result = stats.to_dict()

        assert result["hits"] == 50
        assert result["misses"] == 50
        assert result["evictions"] == 10
        assert result["expired"] == 5
        assert result["current_size"] == 100
        assert result["hit_rate"] == "50.00%"

    def test_to_dict_hit_rate_format(self) -> None:
        """Test hit_rate formatting in to_dict."""
        stats = CacheStats(hits=1, misses=2)
        result = stats.to_dict()

        # 1/3 = 33.33%
        assert result["hit_rate"] == "33.33%"


# =============================================================================
# generate_cache_key Tests
# =============================================================================


@pytest.mark.unit
class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""

    def test_basic_prompt(self) -> None:
        """Test key generation with basic prompt."""
        key = generate_cache_key("Hello, world!")

        # Key should be 64 character hex string (SHA256)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_prompt_same_key(self) -> None:
        """Test same prompt generates same key."""
        key1 = generate_cache_key("Test prompt")
        key2 = generate_cache_key("Test prompt")

        assert key1 == key2

    def test_different_prompt_different_key(self) -> None:
        """Test different prompts generate different keys."""
        key1 = generate_cache_key("Prompt A")
        key2 = generate_cache_key("Prompt B")

        assert key1 != key2

    def test_with_model(self) -> None:
        """Test key includes model when provided."""
        key_no_model = generate_cache_key("Test", model=None)
        key_with_model = generate_cache_key("Test", model="gpt-4")

        assert key_no_model != key_with_model

    def test_same_model_same_key(self) -> None:
        """Test same model generates same key."""
        key1 = generate_cache_key("Test", model="gpt-4")
        key2 = generate_cache_key("Test", model="gpt-4")

        assert key1 == key2

    def test_with_temperature(self) -> None:
        """Test key includes temperature when provided."""
        key_no_temp = generate_cache_key("Test", temperature=None)
        key_with_temp = generate_cache_key("Test", temperature=0.7)

        assert key_no_temp != key_with_temp

    def test_temperature_precision(self) -> None:
        """Test temperature is rounded to 4 decimal places."""
        key1 = generate_cache_key("Test", temperature=0.12345)
        key2 = generate_cache_key("Test", temperature=0.12346)

        # Both should round to 0.1235
        assert key1 == key2

    def test_with_max_tokens(self) -> None:
        """Test key includes max_tokens when provided."""
        key1 = generate_cache_key("Test", max_tokens=100)
        key2 = generate_cache_key("Test", max_tokens=200)

        assert key1 != key2

    def test_with_messages(self) -> None:
        """Test key includes messages when provided."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        key_no_msg = generate_cache_key("Test", messages=None)
        key_with_msg = generate_cache_key("Test", messages=messages)

        assert key_no_msg != key_with_msg

    def test_messages_order_matters(self) -> None:
        """Test message order affects key."""
        messages1 = [
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
        ]
        messages2 = [
            {"role": "user", "content": "Second"},
            {"role": "user", "content": "First"},
        ]
        key1 = generate_cache_key("", messages=messages1)
        key2 = generate_cache_key("", messages=messages2)

        assert key1 != key2

    def test_with_extra(self) -> None:
        """Test key includes extra parameters."""
        extra = {"custom_param": "value"}
        key_no_extra = generate_cache_key("Test", extra=None)
        key_with_extra = generate_cache_key("Test", extra=extra)

        assert key_no_extra != key_with_extra

    def test_all_parameters(self) -> None:
        """Test key with all parameters."""
        key = generate_cache_key(
            "Test prompt",
            model="gpt-4",
            temperature=0.5,
            max_tokens=100,
            messages=[{"role": "user", "content": "test"}],
            extra={"param": "value"},
        )

        assert len(key) == 64

    def test_unicode_prompt(self) -> None:
        """Test key generation with unicode characters."""
        key = generate_cache_key("你好世界")

        assert len(key) == 64

    def test_empty_prompt_with_messages(self) -> None:
        """Test empty prompt with messages (chat API style)."""
        messages = [{"role": "user", "content": "Hello"}]
        key = generate_cache_key("", messages=messages)

        assert len(key) == 64


# =============================================================================
# LRUCache Tests
# =============================================================================


@pytest.mark.unit
class TestLRUCache:
    """Tests for LRUCache class."""

    def test_creation_default_config(self) -> None:
        """Test LRUCache creation with default config."""
        cache = LRUCache()

        assert cache.config.enabled is True
        assert cache.config.max_size == 1000
        assert len(cache) == 0

    def test_creation_custom_config(self, cache_config: CacheConfig) -> None:
        """Test LRUCache creation with custom config."""
        cache = LRUCache(cache_config)

        assert cache.config == cache_config

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache: LRUCache[str] = LRUCache()

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_get_nonexistent(self) -> None:
        """Test get returns None for nonexistent key."""
        cache: LRUCache[str] = LRUCache()

        result = cache.get("nonexistent")

        assert result is None

    def test_get_updates_miss_stats(self) -> None:
        """Test get increments miss counter on cache miss."""
        cache: LRUCache[str] = LRUCache()

        cache.get("nonexistent")
        cache.get("another")

        assert cache.stats.misses == 2

    def test_get_updates_hit_stats(self) -> None:
        """Test get increments hit counter on cache hit."""
        cache: LRUCache[str] = LRUCache()
        cache.set("key", "value")

        cache.get("key")
        cache.get("key")

        assert cache.stats.hits == 2

    def test_set_overwrites_existing(self) -> None:
        """Test set overwrites existing value."""
        cache: LRUCache[str] = LRUCache()

        cache.set("key", "value1")
        cache.set("key", "value2")

        assert cache.get("key") == "value2"
        assert len(cache) == 1

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when max_size is reached."""
        config = CacheConfig(max_size=3)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        # This should evict key1 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.stats.evictions == 1

    def test_lru_access_updates_order(self) -> None:
        """Test accessing item updates its position."""
        config = CacheConfig(max_size=3)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1, making it most recently used
        cache.get("key1")

        # Add new key, should evict key2 (now least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_delete(self) -> None:
        """Test delete removes entry."""
        cache: LRUCache[str] = LRUCache()
        cache.set("key", "value")

        result = cache.delete("key")

        assert result is True
        assert cache.get("key") is None
        assert len(cache) == 0

    def test_delete_nonexistent(self) -> None:
        """Test delete returns False for nonexistent key."""
        cache: LRUCache[str] = LRUCache()

        result = cache.delete("nonexistent")

        assert result is False

    def test_clear(self) -> None:
        """Test clear removes all entries."""
        cache: LRUCache[str] = LRUCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        count = cache.clear()

        assert count == 3
        assert len(cache) == 0

    def test_clear_empty_cache(self) -> None:
        """Test clear on empty cache."""
        cache: LRUCache[str] = LRUCache()

        count = cache.clear()

        assert count == 0

    def test_contains(self) -> None:
        """Test contains method."""
        cache: LRUCache[str] = LRUCache()
        cache.set("key", "value")

        assert cache.contains("key") is True
        assert cache.contains("nonexistent") is False

    def test_in_operator(self) -> None:
        """Test 'in' operator."""
        cache: LRUCache[str] = LRUCache()
        cache.set("key", "value")

        assert "key" in cache
        assert "nonexistent" not in cache

    def test_len(self) -> None:
        """Test len() returns cache size."""
        cache: LRUCache[str] = LRUCache()

        assert len(cache) == 0

        cache.set("key1", "value1")
        assert len(cache) == 1

        cache.set("key2", "value2")
        assert len(cache) == 2

    def test_stats_current_size(self) -> None:
        """Test stats.current_size is updated."""
        cache: LRUCache[str] = LRUCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.stats.current_size == 2

    def test_disabled_cache_get(self) -> None:
        """Test get returns None when cache is disabled."""
        config = CacheConfig(enabled=False)
        cache: LRUCache[str] = LRUCache(config)
        cache.set("key", "value")

        result = cache.get("key")

        assert result is None

    def test_disabled_cache_set(self) -> None:
        """Test set does nothing when cache is disabled."""
        config = CacheConfig(enabled=False)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")

        assert len(cache) == 0

    def test_ttl_expiration(self) -> None:
        """Test TTL expiration on get."""
        config = CacheConfig(ttl_seconds=0.1)  # 100ms
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(0.15)

        assert cache.get("key") is None
        assert cache.stats.expired == 1

    def test_ttl_not_expired(self) -> None:
        """Test item is accessible within TTL."""
        config = CacheConfig(ttl_seconds=1.0)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")

        # Should still be valid
        assert cache.get("key") == "value"

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired removes expired entries."""
        config = CacheConfig(ttl_seconds=0.1)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Wait for expiration
        time.sleep(0.15)

        count = cache.cleanup_expired()

        assert count == 3
        assert len(cache) == 0
        assert cache.stats.expired == 3

    def test_cleanup_expired_no_ttl(self) -> None:
        """Test cleanup_expired returns 0 when TTL is None."""
        config = CacheConfig(ttl_seconds=None)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")

        count = cache.cleanup_expired()

        assert count == 0

    def test_contains_removes_expired(self) -> None:
        """Test contains removes expired entries."""
        config = CacheConfig(ttl_seconds=0.1)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")

        # Wait for expiration
        time.sleep(0.15)

        assert cache.contains("key") is False
        assert cache.stats.expired == 1


# =============================================================================
# LRUCache Concurrent Tests
# =============================================================================


@pytest.mark.unit
class TestLRUCacheConcurrent:
    """Concurrent access tests for LRUCache."""

    def test_concurrent_set(self) -> None:
        """Test concurrent set operations."""
        cache: LRUCache[int] = LRUCache()
        num_threads = 10
        items_per_thread = 100

        def worker(thread_id: int) -> None:
            for i in range(items_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                cache.set(key, thread_id * 1000 + i)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(cache) == num_threads * items_per_thread

    def test_concurrent_get_set(self) -> None:
        """Test concurrent get and set operations."""
        cache: LRUCache[str] = LRUCache()
        cache.set("shared_key", "initial")
        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(100):
                    cache.get("shared_key")
            except Exception as e:
                errors.append(e)

        def writer() -> None:
            try:
                for i in range(100):
                    cache.set("shared_key", f"value_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader) for _ in range(5)
        ] + [
            threading.Thread(target=writer) for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_eviction(self) -> None:
        """Test thread safety during eviction."""
        config = CacheConfig(max_size=50)
        cache: LRUCache[int] = LRUCache(config)

        def worker(thread_id: int) -> None:
            for i in range(100):
                key = f"t{thread_id}_k{i}"
                cache.set(key, i)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for f in futures:
                f.result()

        # Cache size should not exceed max_size
        assert len(cache) <= config.max_size
        assert cache.stats.evictions > 0


# =============================================================================
# LLMResponseCache Tests
# =============================================================================


@pytest.mark.unit
class TestLLMResponseCache:
    """Tests for LLMResponseCache class."""

    def test_creation_default_config(self) -> None:
        """Test LLMResponseCache creation with default config."""
        cache = LLMResponseCache()

        assert cache.config.enabled is True
        assert cache.enabled is True

    def test_creation_with_config(self, cache_config: CacheConfig) -> None:
        """Test LLMResponseCache creation with custom config."""
        cache = LLMResponseCache(cache_config)

        assert cache.config == cache_config

    def test_enabled_property(self) -> None:
        """Test enabled property getter and setter."""
        cache = LLMResponseCache()

        assert cache.enabled is True

        cache.enabled = False
        assert cache.enabled is False

        cache.enabled = True
        assert cache.enabled is True

    def test_set_get_completion(self, llm_cache: LLMResponseCache) -> None:
        """Test set and get completion using fixture."""
        result = {"text": "Test response", "tokens": 10}

        llm_cache.set_completion("Test prompt", result, model="gpt-4")
        cached = llm_cache.get_completion("Test prompt", model="gpt-4")

        assert cached == result

    def test_completion_miss(self, llm_cache: LLMResponseCache) -> None:
        """Test completion cache miss."""
        result = llm_cache.get_completion("Nonexistent prompt")

        assert result is None

    def test_completion_different_models(
        self,
        llm_cache: LLMResponseCache,
    ) -> None:
        """Test completions with different models are cached separately."""
        result1 = {"text": "GPT-4 response"}
        result2 = {"text": "Claude response"}

        llm_cache.set_completion("Same prompt", result1, model="gpt-4")
        llm_cache.set_completion("Same prompt", result2, model="claude-3")

        assert llm_cache.get_completion("Same prompt", model="gpt-4") == result1
        assert llm_cache.get_completion("Same prompt", model="claude-3") == result2

    def test_completion_with_temperature(
        self,
        llm_cache: LLMResponseCache,
    ) -> None:
        """Test completions with different temperatures."""
        result1 = {"text": "Deterministic"}
        result2 = {"text": "Creative"}

        llm_cache.set_completion("Prompt", result1, temperature=0.0)
        llm_cache.set_completion("Prompt", result2, temperature=1.0)

        assert llm_cache.get_completion("Prompt", temperature=0.0) == result1
        assert llm_cache.get_completion("Prompt", temperature=1.0) == result2

    def test_completion_with_max_tokens(
        self,
        llm_cache: LLMResponseCache,
    ) -> None:
        """Test completions with different max_tokens."""
        result1 = {"text": "Short"}
        result2 = {"text": "Long response"}

        llm_cache.set_completion("Prompt", result1, max_tokens=50)
        llm_cache.set_completion("Prompt", result2, max_tokens=500)

        assert llm_cache.get_completion("Prompt", max_tokens=50) == result1
        assert llm_cache.get_completion("Prompt", max_tokens=500) == result2

    def test_set_get_chat(self, llm_cache: LLMResponseCache) -> None:
        """Test set and get chat."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = {"content": "How can I help?", "tokens": 15}

        llm_cache.set_chat(messages, result)
        cached = llm_cache.get_chat(messages)

        assert cached == result

    def test_chat_miss(self, llm_cache: LLMResponseCache) -> None:
        """Test chat cache miss."""
        messages = [{"role": "user", "content": "Unknown"}]

        result = llm_cache.get_chat(messages)

        assert result is None

    def test_chat_different_messages(
        self,
        llm_cache: LLMResponseCache,
    ) -> None:
        """Test different message histories are cached separately."""
        messages1 = [{"role": "user", "content": "Question 1"}]
        messages2 = [{"role": "user", "content": "Question 2"}]

        llm_cache.set_chat(messages1, {"response": "Answer 1"})
        llm_cache.set_chat(messages2, {"response": "Answer 2"})

        assert llm_cache.get_chat(messages1) == {"response": "Answer 1"}
        assert llm_cache.get_chat(messages2) == {"response": "Answer 2"}

    def test_chat_with_model(self, llm_cache: LLMResponseCache) -> None:
        """Test chat caching with model parameter."""
        messages = [{"role": "user", "content": "Test"}]
        result1 = {"text": "GPT-4 reply"}
        result2 = {"text": "Claude reply"}

        llm_cache.set_chat(messages, result1, model="gpt-4")
        llm_cache.set_chat(messages, result2, model="claude-3")

        assert llm_cache.get_chat(messages, model="gpt-4") == result1
        assert llm_cache.get_chat(messages, model="claude-3") == result2

    def test_clear(self, llm_cache: LLMResponseCache) -> None:
        """Test clear removes all entries."""
        llm_cache.set_completion("prompt1", {"result": 1})
        llm_cache.set_completion("prompt2", {"result": 2})
        llm_cache.set_chat([{"role": "user", "content": "test"}], {"r": 3})

        count = llm_cache.clear()

        assert count == 3
        assert llm_cache.get_completion("prompt1") is None

    def test_cleanup(self) -> None:
        """Test cleanup removes expired entries."""
        config = CacheConfig(ttl_seconds=0.1)
        cache = LLMResponseCache(config)

        cache.set_completion("prompt1", {"result": 1})
        cache.set_completion("prompt2", {"result": 2})

        # Wait for expiration
        time.sleep(0.15)

        count = cache.cleanup()

        assert count == 2

    def test_stats(self, llm_cache: LLMResponseCache) -> None:
        """Test stats are tracked correctly."""
        llm_cache.set_completion("prompt", {"result": "test"})

        # 1 hit
        llm_cache.get_completion("prompt")
        # 2 misses
        llm_cache.get_completion("nonexistent1")
        llm_cache.get_completion("nonexistent2")

        stats = llm_cache.stats

        assert stats.hits == 1
        assert stats.misses == 2

    def test_config_include_model_false(self) -> None:
        """Test include_model=False ignores model in cache key."""
        config = CacheConfig(include_model=False)
        cache = LLMResponseCache(config)

        cache.set_completion("prompt", {"result": "shared"}, model="gpt-4")
        # Different model should still hit the same cache entry
        result = cache.get_completion("prompt", model="claude-3")

        assert result == {"result": "shared"}

    def test_config_include_temperature_false(self) -> None:
        """Test include_temperature=False ignores temperature in cache key."""
        config = CacheConfig(include_temperature=False)
        cache = LLMResponseCache(config)

        cache.set_completion("prompt", {"result": "shared"}, temperature=0.5)
        # Different temperature should still hit the same cache entry
        result = cache.get_completion("prompt", temperature=0.9)

        assert result == {"result": "shared"}


# =============================================================================
# LLMResponseCache TTL Tests
# =============================================================================


@pytest.mark.unit
class TestLLMResponseCacheTTL:
    """TTL expiration tests for LLMResponseCache."""

    def test_completion_expires(self) -> None:
        """Test completion cache entry expires after TTL."""
        config = CacheConfig(ttl_seconds=0.1)
        cache = LLMResponseCache(config)

        cache.set_completion("prompt", {"result": "test"})
        assert cache.get_completion("prompt") is not None

        time.sleep(0.15)

        assert cache.get_completion("prompt") is None

    def test_chat_expires(self) -> None:
        """Test chat cache entry expires after TTL."""
        config = CacheConfig(ttl_seconds=0.1)
        cache = LLMResponseCache(config)

        messages = [{"role": "user", "content": "test"}]
        cache.set_chat(messages, {"result": "test"})
        assert cache.get_chat(messages) is not None

        time.sleep(0.15)

        assert cache.get_chat(messages) is None

    def test_no_ttl_never_expires(self) -> None:
        """Test entries never expire when TTL is None."""
        config = CacheConfig(ttl_seconds=None)
        cache = LLMResponseCache(config)

        cache.set_completion("prompt", {"result": "test"})

        # Even after some time, should still be valid
        time.sleep(0.1)

        assert cache.get_completion("prompt") == {"result": "test"}


# =============================================================================
# Global Cache Tests
# =============================================================================


@pytest.mark.unit
class TestGlobalCache:
    """Tests for global cache functions."""

    def test_get_global_cache(self) -> None:
        """Test get_global_cache returns same instance."""
        # Reset first to ensure clean state
        reset_global_cache()

        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

    def test_reset_global_cache(self) -> None:
        """Test reset_global_cache creates new instance."""
        cache1 = get_global_cache()
        cache2 = reset_global_cache()

        assert cache1 is not cache2

    def test_reset_global_cache_with_config(self) -> None:
        """Test reset_global_cache with custom config."""
        config = CacheConfig(max_size=50, ttl_seconds=30.0)

        cache = reset_global_cache(config)

        assert cache.config.max_size == 50
        assert cache.config.ttl_seconds == 30.0

    def test_global_cache_initial_config(self) -> None:
        """Test get_global_cache accepts initial config."""
        # Reset to clear existing instance
        reset_global_cache()

        config = CacheConfig(max_size=200)
        cache = get_global_cache(config)

        assert cache.config.max_size == 1000

    def test_global_cache_config_only_first_call(self) -> None:
        """Test config only applies on first get_global_cache call."""
        reset_global_cache()

        config1 = CacheConfig(max_size=100)
        config2 = CacheConfig(max_size=200)

        cache1 = get_global_cache(config1)
        cache2 = get_global_cache(config2)

        # Second config should be ignored
        assert cache1.config.max_size == 1000
        assert cache2.config.max_size == 1000


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests."""

    def test_empty_prompt(self) -> None:
        """Test empty prompt handling."""
        cache = LLMResponseCache()

        cache.set_completion("", {"result": "empty"})
        result = cache.get_completion("")

        assert result == {"result": "empty"}

    def test_very_long_prompt(self) -> None:
        """Test very long prompt handling."""
        cache = LLMResponseCache()
        long_prompt = "x" * 100000

        cache.set_completion(long_prompt, {"result": "long"})
        result = cache.get_completion(long_prompt)

        assert result == {"result": "long"}

    def test_special_characters_in_prompt(self) -> None:
        """Test special characters in prompt."""
        cache = LLMResponseCache()
        special_prompt = "Hello\n\t\r\"'\\<>&"

        cache.set_completion(special_prompt, {"result": "special"})
        result = cache.get_completion(special_prompt)

        assert result == {"result": "special"}

    def test_none_values_in_result(self) -> None:
        """Test caching results with None values."""
        cache = LLMResponseCache()
        result_with_none = {"value": None, "items": [None, 1, None]}

        cache.set_completion("prompt", result_with_none)
        cached = cache.get_completion("prompt")

        assert cached == result_with_none

    def test_complex_nested_result(self) -> None:
        """Test caching complex nested structures."""
        cache = LLMResponseCache()
        complex_result = {
            "text": "Response",
            "metadata": {
                "tokens": {"input": 10, "output": 20},
                "model": "gpt-4",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "Hi"}},
                ],
            },
            "usage": {"total": 30},
        }

        cache.set_completion("prompt", complex_result)
        cached = cache.get_completion("prompt")

        assert cached == complex_result

    def test_max_size_one(self) -> None:
        """Test cache with max_size=1."""
        config = CacheConfig(max_size=1)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert len(cache) == 1

    def test_zero_ttl(self) -> None:
        """Test cache with ttl_seconds=0 (immediate expiration)."""
        config = CacheConfig(ttl_seconds=0.0)
        cache: LRUCache[str] = LRUCache(config)

        cache.set("key", "value")

        # Should expire immediately
        time.sleep(0.001)
        assert cache.get("key") is None
