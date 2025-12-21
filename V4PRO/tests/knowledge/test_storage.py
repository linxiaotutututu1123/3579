"""
分层存储测试.

测试 storage.py 中的存储实现。
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeType,
)
from src.knowledge.storage import (
    ColdStorage,
    HotStorage,
    TieredStorage,
    TieredStorageConfig,
    WarmStorage,
)


class TestHotStorage:
    """热存储测试."""

    def test_put_and_get(self, hot_storage: HotStorage, sample_entry: KnowledgeEntry) -> None:
        """测试存储和获取."""
        entry_id = hot_storage.put(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = hot_storage.get(entry_id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.content == sample_entry.content

    def test_get_nonexistent(self, hot_storage: HotStorage) -> None:
        """测试获取不存在的条目."""
        result = hot_storage.get("nonexistent-id")
        assert result is None

    def test_delete(self, hot_storage: HotStorage, sample_entry: KnowledgeEntry) -> None:
        """测试删除."""
        hot_storage.put(sample_entry)
        deleted = hot_storage.delete(sample_entry.id)
        assert deleted

        result = hot_storage.get(sample_entry.id)
        assert result is None

    def test_delete_nonexistent(self, hot_storage: HotStorage) -> None:
        """测试删除不存在的条目."""
        deleted = hot_storage.delete("nonexistent-id")
        assert not deleted

    def test_query_by_type(self, hot_storage: HotStorage) -> None:
        """测试按类型查询."""
        entry1 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": 1},
        )
        entry2 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content={"data": 2},
        )

        hot_storage.put(entry1)
        hot_storage.put(entry2)

        results = hot_storage.query(knowledge_type=KnowledgeType.REFLEXION)
        assert len(results) == 1
        assert results[0].knowledge_type == KnowledgeType.REFLEXION

    def test_query_by_tags(self, hot_storage: HotStorage) -> None:
        """测试按标签查询."""
        entry1 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": 1},
            tags=["tag1", "tag2"],
        )
        entry2 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": 2},
            tags=["tag1"],
        )

        hot_storage.put(entry1)
        hot_storage.put(entry2)

        results = hot_storage.query(tags=["tag1", "tag2"])
        assert len(results) == 1
        assert "tag2" in results[0].tags

    def test_query_by_priority(self, hot_storage: HotStorage) -> None:
        """测试按优先级查询."""
        entry1 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": 1},
            priority=KnowledgePriority.HIGH,
        )
        entry2 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": 2},
            priority=KnowledgePriority.LOW,
        )

        hot_storage.put(entry1)
        hot_storage.put(entry2)

        results = hot_storage.query(min_priority=KnowledgePriority.MEDIUM)
        assert len(results) == 1
        assert results[0].priority == KnowledgePriority.HIGH

    def test_lru_eviction(self) -> None:
        """测试LRU淘汰."""
        storage = HotStorage(name="test", max_items=3, ttl_seconds=3600)

        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            storage.put(entry)

        assert storage.count() == 3

    def test_count(self, hot_storage: HotStorage) -> None:
        """测试计数."""
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            hot_storage.put(entry)

        assert hot_storage.count() == 5

    def test_clear(self, hot_storage: HotStorage) -> None:
        """测试清空."""
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            hot_storage.put(entry)

        count = hot_storage.clear()
        assert count == 5
        assert hot_storage.count() == 0

    def test_get_stats(self, hot_storage: HotStorage, sample_entry: KnowledgeEntry) -> None:
        """测试统计信息."""
        hot_storage.put(sample_entry)
        hot_storage.get(sample_entry.id)
        hot_storage.get("nonexistent")

        stats = hot_storage.get_stats()
        assert stats["total_entries"] == 1
        assert stats["total_reads"] == 2
        assert stats["total_writes"] == 1
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1


class TestWarmStorage:
    """温存储测试."""

    def test_put_and_get(self, warm_storage: WarmStorage, sample_entry: KnowledgeEntry) -> None:
        """测试存储和获取."""
        entry_id = warm_storage.put(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = warm_storage.get(entry_id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id

    def test_persistence(self, temp_dir: str, sample_entry: KnowledgeEntry) -> None:
        """测试持久化."""
        db_path = os.path.join(temp_dir, "persist_test.db")

        # 第一个实例写入
        storage1 = WarmStorage(name="test", db_path=db_path)
        storage1.put(sample_entry)

        # 第二个实例读取
        storage2 = WarmStorage(name="test", db_path=db_path)
        retrieved = storage2.get(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id

    def test_delete(self, warm_storage: WarmStorage, sample_entry: KnowledgeEntry) -> None:
        """测试删除."""
        warm_storage.put(sample_entry)
        deleted = warm_storage.delete(sample_entry.id)
        assert deleted

        result = warm_storage.get(sample_entry.id)
        assert result is None

    def test_query_with_filters(self, warm_storage: WarmStorage) -> None:
        """测试带过滤的查询."""
        for i in range(10):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION if i % 2 == 0 else KnowledgeType.PATTERN,
                content={"index": i},
                priority=KnowledgePriority.HIGH if i < 5 else KnowledgePriority.LOW,
            )
            warm_storage.put(entry)

        # 按类型查询
        results = warm_storage.query(knowledge_type=KnowledgeType.REFLEXION)
        assert len(results) == 5

        # 按优先级查询
        results = warm_storage.query(min_priority=KnowledgePriority.HIGH)
        assert len(results) == 5

    def test_count(self, warm_storage: WarmStorage) -> None:
        """测试计数."""
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            warm_storage.put(entry)

        assert warm_storage.count() == 5

    def test_clear(self, warm_storage: WarmStorage) -> None:
        """测试清空."""
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            warm_storage.put(entry)

        count = warm_storage.clear()
        assert count == 5
        assert warm_storage.count() == 0


class TestColdStorage:
    """冷存储测试."""

    def test_put_and_get(self, cold_storage: ColdStorage, sample_entry: KnowledgeEntry) -> None:
        """测试存储和获取."""
        entry_id = cold_storage.put(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = cold_storage.get(entry_id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id

    def test_compressed_storage(self, temp_dir: str, sample_entry: KnowledgeEntry) -> None:
        """测试压缩存储."""
        storage = ColdStorage(
            name="test",
            storage_dir=os.path.join(temp_dir, "compressed"),
            compress=True,
        )

        storage.put(sample_entry)
        retrieved = storage.get(sample_entry.id)
        assert retrieved is not None
        assert retrieved.content == sample_entry.content

    def test_delete(self, cold_storage: ColdStorage, sample_entry: KnowledgeEntry) -> None:
        """测试删除."""
        cold_storage.put(sample_entry)
        deleted = cold_storage.delete(sample_entry.id)
        assert deleted

        result = cold_storage.get(sample_entry.id)
        assert result is None

    def test_query(self, cold_storage: ColdStorage) -> None:
        """测试查询."""
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
                tags=["test"],
            )
            cold_storage.put(entry)

        results = cold_storage.query(knowledge_type=KnowledgeType.REFLEXION)
        assert len(results) == 5

    def test_count(self, cold_storage: ColdStorage) -> None:
        """测试计数."""
        for i in range(3):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            cold_storage.put(entry)

        assert cold_storage.count() == 3


class TestTieredStorage:
    """分层存储测试."""

    def test_put_and_get(self, tiered_storage: TieredStorage, sample_entry: KnowledgeEntry) -> None:
        """测试存储和获取."""
        entry_id = tiered_storage.put(sample_entry)
        assert entry_id == sample_entry.id

        retrieved = tiered_storage.get(entry_id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id

    def test_cross_tier_get(self, tiered_storage: TieredStorage, sample_entry: KnowledgeEntry) -> None:
        """测试跨层获取."""
        # 直接放入温存储
        tiered_storage.warm.put(sample_entry)

        # 通过分层存储获取
        retrieved = tiered_storage.get(sample_entry.id)
        assert retrieved is not None

        # 验证已提升到热存储
        hot_retrieved = tiered_storage.hot.get(sample_entry.id)
        assert hot_retrieved is not None

    def test_delete_from_all_tiers(self, tiered_storage: TieredStorage, sample_entry: KnowledgeEntry) -> None:
        """测试从所有层删除."""
        # 放入热存储和温存储
        tiered_storage.hot.put(sample_entry)
        tiered_storage.warm.put(sample_entry)

        deleted = tiered_storage.delete(sample_entry.id)
        assert deleted

        # 验证两层都已删除
        assert tiered_storage.hot.get(sample_entry.id) is None
        assert tiered_storage.warm.get(sample_entry.id) is None

    def test_query_across_tiers(self, tiered_storage: TieredStorage) -> None:
        """测试跨层查询."""
        # 创建不同层的条目
        hot_entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"tier": "hot"},
            tags=["test"],
        )
        warm_entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"tier": "warm"},
            tags=["test"],
        )

        tiered_storage.hot.put(hot_entry)
        tiered_storage.warm.put(warm_entry)

        results = tiered_storage.query(
            knowledge_type=KnowledgeType.REFLEXION,
            tags=["test"],
        )
        assert len(results) == 2

    def test_count_across_tiers(self, tiered_storage: TieredStorage) -> None:
        """测试跨层计数."""
        for i in range(3):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            if i == 0:
                tiered_storage.hot.put(entry)
            elif i == 1:
                tiered_storage.warm.put(entry)
            else:
                tiered_storage.cold.put(entry)

        assert tiered_storage.count() == 3

    def test_get_stats(self, tiered_storage: TieredStorage, sample_entry: KnowledgeEntry) -> None:
        """测试统计信息."""
        tiered_storage.put(sample_entry)
        tiered_storage.get(sample_entry.id)

        stats = tiered_storage.get_stats()
        assert "overall" in stats
        assert "hot" in stats
        assert "warm" in stats
        assert "cold" in stats

    def test_clear(self, tiered_storage: TieredStorage) -> None:
        """测试清空."""
        for i in range(3):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.REFLEXION,
                content={"index": i},
            )
            tiered_storage.put(entry)

        count = tiered_storage.clear()
        assert count >= 3
        assert tiered_storage.count() == 0
