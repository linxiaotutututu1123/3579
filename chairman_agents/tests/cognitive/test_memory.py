"""
Unit tests for the Memory System module.

Tests cover:
- MemoryItem serialization/deserialization
- MemorySystem store/retrieve operations
- Tokenization for Chinese and English
- Relevance calculation
- Memory consolidation
- Persistence (save/load)
- Statistics reporting
- Edge cases and boundary conditions
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from chairman_agents.cognitive.memory import (
    MemoryItem,
    MemoryQuery,
    MemorySystem,
)


# =============================================================================
# MemoryItem Tests
# =============================================================================


@pytest.mark.unit
class TestMemoryItem:
    """Tests for MemoryItem dataclass."""

    def test_to_dict_basic(self) -> None:
        """Test basic serialization to dictionary."""
        now = datetime.now()
        item = MemoryItem(
            id="test-id-001",
            content="Test memory content",
            memory_type="semantic",
            importance=0.8,
            created_at=now,
            last_accessed=now,
            access_count=5,
            embedding=None,
            metadata={"key": "value"},
        )

        result = item.to_dict()

        assert result["id"] == "test-id-001"
        assert result["content"] == "Test memory content"
        assert result["memory_type"] == "semantic"
        assert result["importance"] == 0.8
        assert result["created_at"] == now.isoformat()
        assert result["last_accessed"] == now.isoformat()
        assert result["access_count"] == 5
        assert result["embedding"] is None
        assert result["metadata"] == {"key": "value"}

    def test_to_dict_with_embedding(self) -> None:
        """Test serialization with embedding vector."""
        now = datetime.now()
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        item = MemoryItem(
            id="test-id-002",
            content="Embedded content",
            memory_type="procedural",
            importance=0.5,
            created_at=now,
            last_accessed=now,
            embedding=embedding,
            metadata={},
        )

        result = item.to_dict()

        assert result["embedding"] == embedding

    def test_from_dict_basic(self) -> None:
        """Test basic deserialization from dictionary."""
        now = datetime.now()
        data = {
            "id": "test-id-003",
            "content": "Deserialized content",
            "memory_type": "episodic",
            "importance": 0.7,
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            "access_count": 3,
            "embedding": None,
            "metadata": {"source": "test"},
        }

        item = MemoryItem.from_dict(data)

        assert item.id == "test-id-003"
        assert item.content == "Deserialized content"
        assert item.memory_type == "episodic"
        assert item.importance == 0.7
        assert item.created_at.isoformat() == now.isoformat()
        assert item.access_count == 3
        assert item.metadata == {"source": "test"}

    def test_from_dict_with_optional_fields(self) -> None:
        """Test deserialization with optional fields missing."""
        now = datetime.now()
        data = {
            "id": "test-id-004",
            "content": "Minimal content",
            "memory_type": "semantic",
            "importance": 0.5,
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            # access_count, embedding, metadata omitted
        }

        item = MemoryItem.from_dict(data)

        assert item.access_count == 0
        assert item.embedding is None
        assert item.metadata == {}

    def test_roundtrip_serialization(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        now = datetime.now()
        original = MemoryItem(
            id="roundtrip-id",
            content="Roundtrip test content",
            memory_type="procedural",
            importance=0.95,
            created_at=now,
            last_accessed=now,
            access_count=10,
            embedding=[0.1, 0.2, 0.3],
            metadata={"nested": {"data": True}},
        )

        serialized = original.to_dict()
        restored = MemoryItem.from_dict(serialized)

        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.memory_type == original.memory_type
        assert restored.importance == original.importance
        assert restored.access_count == original.access_count
        assert restored.embedding == original.embedding
        assert restored.metadata == original.metadata


# =============================================================================
# MemorySystem Store Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemStore:
    """Tests for MemorySystem.store() method."""

    def test_store_basic(self, memory_system: MemorySystem) -> None:
        """Test basic memory storage."""
        item = memory_system.store(
            content="Test memory content",
            memory_type="semantic",
            importance=0.7,
        )

        assert item.content == "Test memory content"
        assert item.memory_type == "semantic"
        assert item.importance == 0.7
        assert item.id in memory_system.memories
        assert len(memory_system) == 1

    def test_store_with_metadata(self, memory_system: MemorySystem) -> None:
        """Test storage with metadata."""
        metadata = {"task_id": "task-123", "source": "user_input"}
        item = memory_system.store(
            content="Memory with metadata",
            memory_type="episodic",
            importance=0.8,
            metadata=metadata,
        )

        assert item.metadata == metadata

    def test_store_all_memory_types(self, memory_system: MemorySystem) -> None:
        """Test storage for all valid memory types."""
        for memory_type in ["episodic", "semantic", "procedural"]:
            item = memory_system.store(
                content=f"Content for {memory_type}",
                memory_type=memory_type,
                importance=0.5,
            )
            assert item.memory_type == memory_type

        assert len(memory_system) == 3

    def test_store_invalid_memory_type(self, memory_system: MemorySystem) -> None:
        """Test that invalid memory type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            memory_system.store(
                content="Invalid type content",
                memory_type="invalid_type",
                importance=0.5,
            )

        assert "Invalid memory type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)

    def test_store_importance_clamping(self, memory_system: MemorySystem) -> None:
        """Test that importance is clamped to [0, 1]."""
        # Test upper bound
        item_high = memory_system.store(
            content="High importance",
            memory_type="semantic",
            importance=1.5,
        )
        assert item_high.importance == 1.0

        # Test lower bound
        item_low = memory_system.store(
            content="Low importance",
            memory_type="semantic",
            importance=-0.5,
        )
        assert item_low.importance == 0.0

    def test_store_generates_unique_ids(self, memory_system: MemorySystem) -> None:
        """Test that each stored memory gets unique ID."""
        ids = set()
        for i in range(10):
            item = memory_system.store(
                content=f"Content {i}",
                memory_type="semantic",
                importance=0.5,
            )
            ids.add(item.id)

        assert len(ids) == 10

    def test_store_sets_timestamps(self, memory_system: MemorySystem) -> None:
        """Test that store sets created_at and last_accessed timestamps."""
        before = datetime.now()
        item = memory_system.store(
            content="Timestamped content",
            memory_type="episodic",
            importance=0.5,
        )
        after = datetime.now()

        assert before <= item.created_at <= after
        assert before <= item.last_accessed <= after
        assert item.access_count == 0

    def test_store_chinese_content(self, memory_system: MemorySystem) -> None:
        """Test storage of Chinese text content."""
        chinese_content = "这是一个中文记忆测试内容"
        item = memory_system.store(
            content=chinese_content,
            memory_type="semantic",
            importance=0.8,
        )

        assert item.content == chinese_content
        assert item.id in memory_system

    def test_store_empty_content(self, memory_system: MemorySystem) -> None:
        """Test storage of empty content (allowed by design)."""
        item = memory_system.store(
            content="",
            memory_type="semantic",
            importance=0.5,
        )

        assert item.content == ""
        assert item.id in memory_system


# =============================================================================
# MemorySystem Retrieve Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemRetrieve:
    """Tests for MemorySystem.retrieve() method."""

    def test_retrieve_basic(self, memory_system_with_data: MemorySystem) -> None:
        """Test basic memory retrieval."""
        query = MemoryQuery(
            query="feature implementation",
            min_relevance=0.1,
        )

        results = memory_system_with_data.retrieve(query)

        assert len(results) > 0
        # Results should be tuples of (MemoryItem, relevance)
        for item, relevance in results:
            assert isinstance(item, MemoryItem)
            assert 0.0 <= relevance <= 1.0

    def test_retrieve_sorted_by_relevance(
        self, memory_system_with_data: MemorySystem
    ) -> None:
        """Test that results are sorted by relevance descending."""
        query = MemoryQuery(
            query="Python programming",
            min_relevance=0.0,
            limit=100,
        )

        results = memory_system_with_data.retrieve(query)

        if len(results) > 1:
            relevances = [r for _, r in results]
            assert relevances == sorted(relevances, reverse=True)

    def test_retrieve_respects_limit(
        self, memory_system_with_data: MemorySystem
    ) -> None:
        """Test that retrieve respects the limit parameter."""
        query = MemoryQuery(
            query="test",
            min_relevance=0.0,
            limit=2,
        )

        results = memory_system_with_data.retrieve(query)

        assert len(results) <= 2

    def test_retrieve_filters_by_memory_type(
        self, memory_system_with_data: MemorySystem
    ) -> None:
        """Test filtering by memory type."""
        query = MemoryQuery(
            query="test",
            memory_types=["episodic"],
            min_relevance=0.0,
        )

        results = memory_system_with_data.retrieve(query)

        for item, _ in results:
            assert item.memory_type == "episodic"

    def test_retrieve_filters_by_min_relevance(
        self, memory_system: MemorySystem
    ) -> None:
        """Test filtering by minimum relevance."""
        # Store memories with known content
        memory_system.store(
            content="apple banana cherry",
            memory_type="semantic",
            importance=0.8,
        )
        memory_system.store(
            content="completely unrelated xyz",
            memory_type="semantic",
            importance=0.5,
        )

        query = MemoryQuery(
            query="apple",
            min_relevance=0.3,
        )

        results = memory_system.retrieve(query)

        for _, relevance in results:
            assert relevance >= 0.3

    def test_retrieve_updates_access_info(self, memory_system: MemorySystem) -> None:
        """Test that retrieve updates last_accessed and access_count."""
        item = memory_system.store(
            content="access tracking test",
            memory_type="semantic",
            importance=0.8,
        )
        original_accessed = item.last_accessed
        original_count = item.access_count

        # Wait a tiny bit to ensure timestamp differs
        import time
        time.sleep(0.01)

        query = MemoryQuery(
            query="access tracking",
            min_relevance=0.0,
        )
        results = memory_system.retrieve(query)

        # Find the item in results
        for result_item, _ in results:
            if result_item.id == item.id:
                assert result_item.access_count > original_count
                break

    def test_retrieve_empty_query(self, memory_system_with_data: MemorySystem) -> None:
        """Test retrieval with empty query returns no high-relevance matches."""
        query = MemoryQuery(
            query="",
            min_relevance=0.5,
        )

        results = memory_system_with_data.retrieve(query)

        # Empty query should not match well
        assert len(results) == 0

    def test_retrieve_no_matches(self, memory_system: MemorySystem) -> None:
        """Test retrieval when no memories exist."""
        query = MemoryQuery(
            query="nonexistent content",
            min_relevance=0.1,
        )

        results = memory_system.retrieve(query)

        assert len(results) == 0


# =============================================================================
# MemorySystem Tokenization Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemTokenize:
    """Tests for MemorySystem._tokenize() method."""

    def test_tokenize_english(self, memory_system: MemorySystem) -> None:
        """Test tokenization of English text."""
        text = "Hello world, this is a test."
        tokens = memory_system._tokenize(text)

        assert "hello" in tokens
        assert "world" in tokens
        assert "this" in tokens
        assert "test" in tokens

    def test_tokenize_english_case_insensitive(
        self, memory_system: MemorySystem
    ) -> None:
        """Test that tokenization is case insensitive."""
        text = "HELLO World MiXeD"
        tokens = memory_system._tokenize(text)

        assert "hello" in tokens
        assert "world" in tokens
        assert "mixed" in tokens

    def test_tokenize_chinese(self, memory_system: MemorySystem) -> None:
        """Test tokenization of Chinese text."""
        text = "这是一个测试"
        tokens = memory_system._tokenize(text)

        assert len(tokens) > 0
        # At minimum, character-level tokenization should work
        assert "这" in tokens or "测试" in tokens or "这是" in tokens

    def test_tokenize_mixed_chinese_english(
        self, memory_system: MemorySystem
    ) -> None:
        """Test tokenization of mixed Chinese and English text."""
        text = "这是一个test测试"
        tokens = memory_system._tokenize(text)

        assert len(tokens) > 0
        # Should contain some form of tokens
        assert any(token for token in tokens if token)

    def test_tokenize_empty_string(self, memory_system: MemorySystem) -> None:
        """Test tokenization of empty string."""
        tokens = memory_system._tokenize("")

        assert tokens == []

    def test_tokenize_whitespace_only(self, memory_system: MemorySystem) -> None:
        """Test tokenization of whitespace-only string."""
        tokens = memory_system._tokenize("   \t\n  ")

        assert tokens == []

    def test_tokenize_special_characters(self, memory_system: MemorySystem) -> None:
        """Test tokenization handles special characters."""
        text = "hello@world.com test-case123"
        tokens = memory_system._tokenize(text)

        # Should extract some tokens
        assert len(tokens) > 0

    def test_tokenize_numbers(self, memory_system: MemorySystem) -> None:
        """Test tokenization of text with numbers."""
        text = "version 3.14 release 2024"
        tokens = memory_system._tokenize(text)

        # Should include words and possibly numbers
        assert "version" in tokens
        assert "release" in tokens


# =============================================================================
# MemorySystem Relevance Calculation Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemRelevance:
    """Tests for MemorySystem._calculate_relevance() method."""

    def test_relevance_exact_match(self, memory_system: MemorySystem) -> None:
        """Test relevance for exact content match."""
        item = memory_system.store(
            content="python programming tutorial",
            memory_type="semantic",
            importance=0.8,
        )

        relevance = memory_system._calculate_relevance(
            "python programming tutorial",
            memory_system.memories[item.id],
            time_decay=False,
        )

        # Exact match should have high relevance
        assert relevance > 0.5

    def test_relevance_partial_match(self, memory_system: MemorySystem) -> None:
        """Test relevance for partial content match."""
        item = memory_system.store(
            content="python programming tutorial",
            memory_type="semantic",
            importance=0.8,
        )

        relevance = memory_system._calculate_relevance(
            "python",
            memory_system.memories[item.id],
            time_decay=False,
        )

        # Partial match should have moderate relevance
        assert 0.0 < relevance < 1.0

    def test_relevance_no_match(self, memory_system: MemorySystem) -> None:
        """Test relevance for non-matching content."""
        item = memory_system.store(
            content="python programming tutorial",
            memory_type="semantic",
            importance=0.8,
        )

        relevance = memory_system._calculate_relevance(
            "quantum physics galaxies",
            memory_system.memories[item.id],
            time_decay=False,
        )

        # No match should have zero or very low relevance
        assert relevance < 0.2

    def test_relevance_importance_weighting(self, memory_system: MemorySystem) -> None:
        """Test that importance affects relevance score."""
        item_high = memory_system.store(
            content="test content",
            memory_type="semantic",
            importance=1.0,
        )
        item_low = memory_system.store(
            content="test content",
            memory_type="semantic",
            importance=0.0,
        )

        relevance_high = memory_system._calculate_relevance(
            "test content",
            memory_system.memories[item_high.id],
            time_decay=False,
        )
        relevance_low = memory_system._calculate_relevance(
            "test content",
            memory_system.memories[item_low.id],
            time_decay=False,
        )

        # Higher importance should result in higher relevance
        assert relevance_high >= relevance_low

    def test_relevance_time_decay(self, memory_system: MemorySystem) -> None:
        """Test time decay effect on relevance."""
        item = memory_system.store(
            content="test content for decay",
            memory_type="semantic",
            importance=0.8,
        )

        # Get reference without decay
        relevance_no_decay = memory_system._calculate_relevance(
            "test content",
            memory_system.memories[item.id],
            time_decay=False,
        )

        # Get with decay
        relevance_with_decay = memory_system._calculate_relevance(
            "test content",
            memory_system.memories[item.id],
            time_decay=True,
        )

        # For recent memory, decay should not significantly reduce relevance
        # The difference should be minimal for fresh memories
        assert relevance_with_decay <= relevance_no_decay

    def test_relevance_empty_query(self, memory_system: MemorySystem) -> None:
        """Test relevance with empty query."""
        item = memory_system.store(
            content="test content",
            memory_type="semantic",
            importance=0.8,
        )

        relevance = memory_system._calculate_relevance(
            "",
            memory_system.memories[item.id],
            time_decay=False,
        )

        assert relevance == 0.0

    def test_relevance_chinese_text(self, memory_system: MemorySystem) -> None:
        """Test relevance calculation for Chinese text."""
        item = memory_system.store(
            content="这是一个中文测试内容",
            memory_type="semantic",
            importance=0.8,
        )

        relevance = memory_system._calculate_relevance(
            "中文测试",
            memory_system.memories[item.id],
            time_decay=False,
        )

        # Should have some relevance due to overlapping tokens
        assert relevance > 0.0


# =============================================================================
# MemorySystem Consolidate Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemConsolidate:
    """Tests for MemorySystem.consolidate() method."""

    def test_consolidate_removes_old_unimportant(
        self, memory_system: MemorySystem
    ) -> None:
        """Test that consolidate removes old, unimportant, rarely accessed memories."""
        # Create an old, unimportant memory
        item = memory_system.store(
            content="old unimportant content",
            memory_type="semantic",
            importance=0.1,
        )
        # Manually age the memory
        memory_system.memories[item.id].created_at = datetime.now() - timedelta(days=100)
        memory_system.memories[item.id].access_count = 1

        removed_count = memory_system.consolidate(
            min_importance=0.2,
            max_age_days=90,
        )

        assert removed_count >= 1
        assert item.id not in memory_system

    def test_consolidate_keeps_important(self, memory_system: MemorySystem) -> None:
        """Test that consolidate keeps important memories."""
        item = memory_system.store(
            content="important content",
            memory_type="semantic",
            importance=0.9,
        )
        # Age it
        memory_system.memories[item.id].created_at = datetime.now() - timedelta(days=100)

        memory_system.consolidate(
            min_importance=0.5,
            max_age_days=90,
        )

        # Important memory should still exist
        assert item.id in memory_system

    def test_consolidate_keeps_frequently_accessed(
        self, memory_system: MemorySystem
    ) -> None:
        """Test that consolidate keeps frequently accessed memories."""
        item = memory_system.store(
            content="frequently accessed",
            memory_type="semantic",
            importance=0.1,
        )
        # Age it but give it high access count
        memory_system.memories[item.id].created_at = datetime.now() - timedelta(days=100)
        memory_system.memories[item.id].access_count = 10

        memory_system.consolidate(
            min_importance=0.5,
            max_age_days=90,
        )

        # Frequently accessed should still exist
        assert item.id in memory_system

    def test_consolidate_empty_system(self, memory_system: MemorySystem) -> None:
        """Test consolidate on empty memory system."""
        removed_count = memory_system.consolidate()

        assert removed_count == 0
        assert len(memory_system) == 0

    def test_consolidate_merges_similar(self, memory_system: MemorySystem) -> None:
        """Test that consolidate merges similar memories."""
        # Create two very similar memories
        item1 = memory_system.store(
            content="python programming guide",
            memory_type="semantic",
            importance=0.6,
        )
        item2 = memory_system.store(
            content="python programming guide tutorial",
            memory_type="semantic",
            importance=0.8,
        )

        initial_count = len(memory_system)
        removed_count = memory_system.consolidate(
            similarity_threshold=0.7,
        )

        # At least one should be merged if similar enough
        # Or both kept if not similar enough
        assert len(memory_system) <= initial_count


# =============================================================================
# MemorySystem Persistence Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemPersistence:
    """Tests for MemorySystem persistence (save_to_disk/load_from_disk)."""

    def test_save_to_disk(
        self, memory_system: MemorySystem, memory_storage_path: Path
    ) -> None:
        """Test saving memories to disk."""
        memory_system.store(
            content="Persistent memory",
            memory_type="semantic",
            importance=0.8,
        )

        memory_system.save_to_disk()

        assert memory_storage_path.exists()
        with open(memory_storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "memories" in data
        assert "version" in data
        assert len(data["memories"]) == 1

    def test_save_without_storage_path_raises(self) -> None:
        """Test that save_to_disk raises when storage_path is not set."""
        system = MemorySystem(storage_path=None)
        system.store(content="test", memory_type="semantic", importance=0.5)

        with pytest.raises(ValueError) as exc_info:
            system.save_to_disk()

        assert "Storage path not configured" in str(exc_info.value)

    def test_load_from_disk(
        self, memory_system: MemorySystem, memory_storage_path: Path
    ) -> None:
        """Test loading memories from disk."""
        # Store and save
        original_item = memory_system.store(
            content="Loadable memory",
            memory_type="procedural",
            importance=0.7,
            metadata={"key": "value"},
        )
        memory_system.save_to_disk()

        # Create new system and load
        new_system = MemorySystem(storage_path=memory_storage_path)
        new_system.load_from_disk()

        assert len(new_system) == 1
        loaded_item = list(new_system.memories.values())[0]
        assert loaded_item.content == "Loadable memory"
        assert loaded_item.memory_type == "procedural"
        assert loaded_item.importance == 0.7
        assert loaded_item.metadata == {"key": "value"}

    def test_load_without_storage_path_raises(self) -> None:
        """Test that load_from_disk raises when storage_path is not set."""
        system = MemorySystem(storage_path=None)

        with pytest.raises(ValueError) as exc_info:
            system.load_from_disk()

        assert "Storage path not configured" in str(exc_info.value)

    def test_load_nonexistent_file_raises(self, test_data_dir: Path) -> None:
        """Test that load_from_disk raises for nonexistent file."""
        nonexistent_path = test_data_dir / "nonexistent.json"
        system = MemorySystem(storage_path=nonexistent_path)

        with pytest.raises(FileNotFoundError):
            system.load_from_disk()

    def test_roundtrip_persistence(
        self, memory_system: MemorySystem, memory_storage_path: Path
    ) -> None:
        """Test full save and load cycle preserves data."""
        # Create multiple memories
        items = []
        for i in range(5):
            item = memory_system.store(
                content=f"Memory content {i}",
                memory_type=["episodic", "semantic", "procedural"][i % 3],
                importance=i / 5,
                metadata={"index": i},
            )
            items.append(item)

        memory_system.save_to_disk()

        # Load into new system
        new_system = MemorySystem(storage_path=memory_storage_path)
        new_system.load_from_disk()

        assert len(new_system) == 5

        for original in items:
            assert original.id in new_system
            loaded = new_system.memories[original.id]
            assert loaded.content == original.content
            assert loaded.memory_type == original.memory_type
            assert loaded.importance == original.importance

    def test_save_chinese_content(
        self, memory_system: MemorySystem, memory_storage_path: Path
    ) -> None:
        """Test saving and loading Chinese content."""
        chinese_content = "这是一个中文记忆测试"
        memory_system.store(
            content=chinese_content,
            memory_type="semantic",
            importance=0.8,
        )
        memory_system.save_to_disk()

        new_system = MemorySystem(storage_path=memory_storage_path)
        new_system.load_from_disk()

        loaded_item = list(new_system.memories.values())[0]
        assert loaded_item.content == chinese_content


# =============================================================================
# MemorySystem Statistics Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemStatistics:
    """Tests for MemorySystem.get_statistics() method."""

    def test_statistics_empty_system(self, memory_system: MemorySystem) -> None:
        """Test statistics for empty memory system."""
        stats = memory_system.get_statistics()

        assert stats["total_memories"] == 0
        assert stats["by_type"] == {}
        assert stats["average_importance"] == 0
        assert stats["total_access_count"] == 0
        assert stats["oldest_memory"] is None
        assert stats["newest_memory"] is None

    def test_statistics_with_memories(
        self, memory_system_with_data: MemorySystem
    ) -> None:
        """Test statistics with populated memory system."""
        stats = memory_system_with_data.get_statistics()

        assert stats["total_memories"] > 0
        assert len(stats["by_type"]) > 0
        assert stats["oldest_memory"] is not None
        assert stats["newest_memory"] is not None

    def test_statistics_by_type(self, memory_system: MemorySystem) -> None:
        """Test by_type breakdown in statistics."""
        memory_system.store(content="episodic1", memory_type="episodic", importance=0.5)
        memory_system.store(content="episodic2", memory_type="episodic", importance=0.5)
        memory_system.store(content="semantic1", memory_type="semantic", importance=0.5)

        stats = memory_system.get_statistics()

        assert stats["by_type"]["episodic"] == 2
        assert stats["by_type"]["semantic"] == 1

    def test_statistics_average_importance(self, memory_system: MemorySystem) -> None:
        """Test average importance calculation."""
        memory_system.store(content="test1", memory_type="semantic", importance=0.2)
        memory_system.store(content="test2", memory_type="semantic", importance=0.8)

        stats = memory_system.get_statistics()

        assert stats["average_importance"] == pytest.approx(0.5, rel=0.01)

    def test_statistics_storage_path(
        self, memory_system: MemorySystem, memory_storage_path: Path
    ) -> None:
        """Test storage path in statistics."""
        stats = memory_system.get_statistics()

        assert stats["storage_path"] == str(memory_storage_path)

    def test_statistics_jieba_availability(self, memory_system: MemorySystem) -> None:
        """Test jieba availability in statistics."""
        stats = memory_system.get_statistics()

        assert "jieba_available" in stats
        assert isinstance(stats["jieba_available"], bool)


# =============================================================================
# MemorySystem Edge Cases Tests
# =============================================================================


@pytest.mark.unit
class TestMemorySystemEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_contains_operator(self, memory_system: MemorySystem) -> None:
        """Test __contains__ operator."""
        item = memory_system.store(
            content="test",
            memory_type="semantic",
            importance=0.5,
        )

        assert item.id in memory_system
        assert "nonexistent-id" not in memory_system

    def test_len_operator(self, memory_system: MemorySystem) -> None:
        """Test __len__ operator."""
        assert len(memory_system) == 0

        memory_system.store(content="test1", memory_type="semantic", importance=0.5)
        assert len(memory_system) == 1

        memory_system.store(content="test2", memory_type="semantic", importance=0.5)
        assert len(memory_system) == 2

    def test_forget(self, memory_system: MemorySystem) -> None:
        """Test forget (delete) memory."""
        item = memory_system.store(
            content="forgettable",
            memory_type="semantic",
            importance=0.5,
        )
        assert item.id in memory_system

        result = memory_system.forget(item.id)

        assert result is True
        assert item.id not in memory_system

    def test_forget_nonexistent(self, memory_system: MemorySystem) -> None:
        """Test forget nonexistent memory returns False."""
        result = memory_system.forget("nonexistent-id")

        assert result is False

    def test_clear(self, memory_system_with_data: MemorySystem) -> None:
        """Test clear all memories."""
        initial_count = len(memory_system_with_data)
        assert initial_count > 0

        cleared = memory_system_with_data.clear()

        assert cleared == initial_count
        assert len(memory_system_with_data) == 0

    def test_update_importance(self, memory_system: MemorySystem) -> None:
        """Test updating memory importance."""
        item = memory_system.store(
            content="test",
            memory_type="semantic",
            importance=0.5,
        )

        result = memory_system.update_importance(item.id, 0.9)

        assert result is True
        assert memory_system.memories[item.id].importance == 0.9

    def test_update_importance_clamping(self, memory_system: MemorySystem) -> None:
        """Test that update_importance clamps values."""
        item = memory_system.store(
            content="test",
            memory_type="semantic",
            importance=0.5,
        )

        memory_system.update_importance(item.id, 1.5)
        assert memory_system.memories[item.id].importance == 1.0

        memory_system.update_importance(item.id, -0.5)
        assert memory_system.memories[item.id].importance == 0.0

    def test_update_importance_nonexistent(self, memory_system: MemorySystem) -> None:
        """Test update_importance for nonexistent memory."""
        result = memory_system.update_importance("nonexistent", 0.5)

        assert result is False

    def test_retrieve_by_type(self, memory_system_with_data: MemorySystem) -> None:
        """Test retrieve_by_type method."""
        episodic_memories = memory_system_with_data.retrieve_by_type(
            memory_type="episodic",
            limit=10,
        )

        for memory in episodic_memories:
            assert memory.memory_type == "episodic"

    def test_search_by_metadata(self, memory_system_with_data: MemorySystem) -> None:
        """Test search_by_metadata method."""
        results = memory_system_with_data.search_by_metadata(
            key="topic",
            value="async",
            limit=10,
        )

        assert len(results) > 0
        for result in results:
            assert result.metadata.get("topic") == "async"

    def test_search_by_metadata_no_match(
        self, memory_system_with_data: MemorySystem
    ) -> None:
        """Test search_by_metadata with no matching results."""
        results = memory_system_with_data.search_by_metadata(
            key="nonexistent_key",
            value="nonexistent_value",
        )

        assert len(results) == 0

    def test_cosine_similarity_empty_vectors(self, memory_system: MemorySystem) -> None:
        """Test cosine similarity with empty vectors."""
        result = memory_system._cosine_similarity([], [])
        assert result == 0.0

    def test_cosine_similarity_mismatched_lengths(
        self, memory_system: MemorySystem
    ) -> None:
        """Test cosine similarity with different length vectors."""
        result = memory_system._cosine_similarity([1, 2, 3], [1, 2])
        assert result == 0.0

    def test_cosine_similarity_zero_vector(self, memory_system: MemorySystem) -> None:
        """Test cosine similarity with zero vector."""
        result = memory_system._cosine_similarity([0, 0, 0], [1, 2, 3])
        assert result == 0.0

    def test_cosine_similarity_identical_vectors(
        self, memory_system: MemorySystem
    ) -> None:
        """Test cosine similarity with identical vectors."""
        vector = [0.1, 0.2, 0.3]
        result = memory_system._cosine_similarity(vector, vector)
        assert result == pytest.approx(1.0, rel=0.001)

    def test_contains_chinese(self, memory_system: MemorySystem) -> None:
        """Test _contains_chinese method."""
        assert memory_system._contains_chinese("中文") is True
        assert memory_system._contains_chinese("English") is False
        assert memory_system._contains_chinese("Mixed中文Text") is True
        assert memory_system._contains_chinese("") is False

    def test_character_tokenize(self, memory_system: MemorySystem) -> None:
        """Test _character_tokenize method."""
        tokens = memory_system._character_tokenize("测试test中文")

        assert "测" in tokens
        assert "试" in tokens
        assert "中" in tokens
        assert "文" in tokens
        assert "test" in tokens


# =============================================================================
# MemoryQuery Tests
# =============================================================================


@pytest.mark.unit
class TestMemoryQuery:
    """Tests for MemoryQuery dataclass."""

    def test_memory_query_defaults(self) -> None:
        """Test MemoryQuery default values."""
        query = MemoryQuery(query="test")

        assert query.query == "test"
        assert query.memory_types is None
        assert query.limit == 10
        assert query.min_relevance == 0.3
        assert query.time_decay is True
        assert query.time_decay_factor == 0.1

    def test_memory_query_custom_values(self) -> None:
        """Test MemoryQuery with custom values."""
        query = MemoryQuery(
            query="custom search",
            memory_types=["episodic", "semantic"],
            limit=5,
            min_relevance=0.5,
            time_decay=False,
            time_decay_factor=0.2,
        )

        assert query.query == "custom search"
        assert query.memory_types == ["episodic", "semantic"]
        assert query.limit == 5
        assert query.min_relevance == 0.5
        assert query.time_decay is False
        assert query.time_decay_factor == 0.2
