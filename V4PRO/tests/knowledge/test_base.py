"""
知识库基类测试.

测试 base.py 中的核心类型和基类。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.base import (
    KnowledgeAuditRecord,
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeType,
    QueryContext,
    StorageTier,
    STORAGE_TIER_THRESHOLDS,
    validate_knowledge_entry,
)


class TestKnowledgeType:
    """知识类型枚举测试."""

    def test_all_types_defined(self) -> None:
        """验证所有类型已定义."""
        expected_types = [
            KnowledgeType.REFLEXION,
            KnowledgeType.PATTERN,
            KnowledgeType.DECISION,
            KnowledgeType.FAULT,
            KnowledgeType.STRATEGY,
            KnowledgeType.RISK,
        ]
        assert len(KnowledgeType) == 6
        for t in expected_types:
            assert isinstance(t, KnowledgeType)


class TestKnowledgePriority:
    """知识优先级枚举测试."""

    def test_priority_values(self) -> None:
        """验证优先级值."""
        assert KnowledgePriority.CRITICAL.value == 4
        assert KnowledgePriority.HIGH.value == 3
        assert KnowledgePriority.MEDIUM.value == 2
        assert KnowledgePriority.LOW.value == 1

    def test_priority_weights(self) -> None:
        """验证优先级权重."""
        assert KnowledgePriority.CRITICAL.weight == 1.0
        assert KnowledgePriority.HIGH.weight == 0.8
        assert KnowledgePriority.MEDIUM.weight == 0.5
        assert KnowledgePriority.LOW.weight == 0.2


class TestStorageTier:
    """存储层级枚举测试."""

    def test_tier_values(self) -> None:
        """验证层级值."""
        assert StorageTier.HOT.value == "hot"
        assert StorageTier.WARM.value == "warm"
        assert StorageTier.COLD.value == "cold"

    def test_tier_thresholds(self) -> None:
        """验证层级阈值."""
        assert STORAGE_TIER_THRESHOLDS[StorageTier.HOT] == 7 * 24 * 3600
        assert STORAGE_TIER_THRESHOLDS[StorageTier.WARM] == 90 * 24 * 3600
        assert STORAGE_TIER_THRESHOLDS[StorageTier.COLD] == float("inf")


class TestKnowledgeEntry:
    """知识条目测试."""

    def test_create_entry(self) -> None:
        """测试创建条目."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"key": "value"},
            priority=KnowledgePriority.HIGH,
            tags=["test"],
        )

        assert entry.id
        assert entry.knowledge_type == KnowledgeType.REFLEXION
        assert entry.priority == KnowledgePriority.HIGH
        assert entry.content == {"key": "value"}
        assert entry.tags == ["test"]
        assert entry.created_at > 0
        assert entry.content_hash

    def test_content_hash_deterministic(self) -> None:
        """测试内容哈希确定性."""
        content = {"a": 1, "b": 2}
        entry1 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content=content,
        )
        entry2 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content=content,
        )
        assert entry1.content_hash == entry2.content_hash

    def test_content_hash_different_for_different_content(self) -> None:
        """测试不同内容产生不同哈希."""
        entry1 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content={"a": 1},
        )
        entry2 = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content={"a": 2},
        )
        assert entry1.content_hash != entry2.content_hash

    def test_age_seconds(self) -> None:
        """测试年龄计算."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.DECISION,
            content={"data": "test"},
        )
        # 刚创建的条目年龄应该接近0
        assert entry.age_seconds < 1

    def test_storage_tier_hot(self) -> None:
        """测试新条目应该在热存储."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": "test"},
        )
        assert entry.storage_tier == StorageTier.HOT

    def test_touch_updates_access(self) -> None:
        """测试touch更新访问信息."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": "test"},
        )
        original_access_count = entry.access_count
        original_accessed_at = entry.accessed_at

        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == original_access_count + 1
        assert entry.accessed_at >= original_accessed_at

    def test_update_content(self) -> None:
        """测试更新内容."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content={"version": 1},
        )
        original_hash = entry.content_hash
        original_version = entry.version

        entry.update_content({"version": 2})

        assert entry.content == {"version": 2}
        assert entry.version == original_version + 1
        assert entry.content_hash != original_hash

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.DECISION,
            content={"key": "value"},
            priority=KnowledgePriority.CRITICAL,
            tags=["test"],
            run_id="run-123",
        )

        data = entry.to_dict()

        assert data["id"] == entry.id
        assert data["knowledge_type"] == "DECISION"
        assert data["priority"] == "CRITICAL"
        assert data["content"] == {"key": "value"}
        assert data["tags"] == ["test"]
        assert data["run_id"] == "run-123"
        assert "storage_tier" in data

    def test_from_dict(self) -> None:
        """测试从字典创建."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": [1, 2, 3]},
            priority=KnowledgePriority.HIGH,
        )
        data = entry.to_dict()

        restored = KnowledgeEntry.from_dict(data)

        assert restored.id == entry.id
        assert restored.knowledge_type == entry.knowledge_type
        assert restored.priority == entry.priority
        assert restored.content == entry.content


class TestKnowledgeAuditRecord:
    """审计记录测试."""

    def test_create_record(self) -> None:
        """测试创建审计记录."""
        record = KnowledgeAuditRecord.create(
            operation="put",
            entry_id="entry-123",
            knowledge_type="REFLEXION",
            run_id="run-456",
            details={"tier": "hot"},
        )

        assert record.id
        assert record.ts > 0
        assert record.operation == "put"
        assert record.entry_id == "entry-123"
        assert record.knowledge_type == "REFLEXION"
        assert record.run_id == "run-456"
        assert record.success

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        record = KnowledgeAuditRecord.create(
            operation="get",
            entry_id="entry-789",
            knowledge_type="PATTERN",
        )
        data = record.to_dict()

        assert data["operation"] == "get"
        assert data["entry_id"] == "entry-789"
        assert data["knowledge_type"] == "PATTERN"
        assert data["success"]


class TestQueryContext:
    """查询上下文测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        ctx = QueryContext()

        assert ctx.knowledge_types == []
        assert ctx.tags == []
        assert ctx.min_priority is None
        assert ctx.limit == 100
        assert ctx.offset == 0
        assert ctx.order_by == "created_at"
        assert not ctx.ascending


class TestValidateKnowledgeEntry:
    """验证函数测试."""

    def test_valid_entry(self) -> None:
        """测试有效条目验证通过."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": "test"},
        )
        errors = validate_knowledge_entry(entry)
        assert errors == []

    def test_missing_id(self) -> None:
        """测试缺少ID."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": "test"},
        )
        entry.id = ""
        errors = validate_knowledge_entry(entry)
        assert any("id is missing" in e for e in errors)

    def test_empty_content(self) -> None:
        """测试空内容."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={},
        )
        entry.content = {}
        errors = validate_knowledge_entry(entry)
        assert any("content is empty" in e for e in errors)

    def test_invalid_timestamp(self) -> None:
        """测试无效时间戳."""
        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"data": "test"},
        )
        entry.created_at = 0
        errors = validate_knowledge_entry(entry)
        assert any("created_at is invalid" in e for e in errors)
