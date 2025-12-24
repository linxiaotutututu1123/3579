"""
Memory System Module for Chairman Agents.

Provides episodic, semantic, and procedural memory capabilities
with Chinese language support for relevance calculation.
"""

from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


@dataclass
class MemoryItem:
    """Represents a single memory item."""

    id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    importance: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            importance=data["importance"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""

    query: str
    memory_types: list[str] | None = None
    limit: int = 10
    min_relevance: float = 0.3
    time_decay: bool = True
    time_decay_factor: float = 0.1  # Higher = faster decay


class MemorySystem:
    """
    Memory system with support for Chinese text processing.

    Features:
    - Episodic, semantic, and procedural memory types
    - Chinese tokenization via jieba (optional)
    - Time-based relevance decay
    - Persistence to disk
    - Memory consolidation
    """

    # Valid memory types
    MEMORY_TYPES = {"episodic", "semantic", "procedural"}

    # Chinese character range for detection
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')

    def __init__(
        self,
        storage_path: Path | None = None,
        use_embeddings: bool = False,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        """
        Initialize the memory system.

        Args:
            storage_path: Path for persistent storage
            use_embeddings: Whether to use vector embeddings
            embedding_model: Name of the sentence-transformers model to use
        """
        self.memories: dict[str, MemoryItem] = {}
        self.storage_path = storage_path
        self.use_embeddings = use_embeddings
        self._embedding_model_name = embedding_model

        # Chinese tokenization support (optional)
        self._jieba_available = self._check_jieba()
        self._jieba = None

        # Embedding model support (optional)
        self._embedding_model = None
        self._embeddings_available = False
        if use_embeddings:
            self._init_embedding_model()

        # Load existing memories if storage path exists
        if storage_path and storage_path.exists():
            self.load_from_disk()

    def _check_jieba(self) -> bool:
        """Check if jieba is available for Chinese tokenization."""
        try:
            import jieba
            self._jieba = jieba
            return True
        except ImportError:
            return False

    def _init_embedding_model(self) -> None:
        """
        Initialize the sentence-transformers embedding model.

        Checks if sentence-transformers is available and loads the model.
        If not available, gracefully degrades to text matching.
        """
        try:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self._embedding_model_name)
            self._embeddings_available = True
        except ImportError:
            # sentence-transformers not installed, degrade gracefully
            self._embedding_model = None
            self._embeddings_available = False
        except Exception:
            # Model loading failed, degrade gracefully
            self._embedding_model = None
            self._embeddings_available = False

    def _generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector, or None if unavailable
        """
        if not self._embeddings_available or self._embedding_model is None:
            return None

        if not text or not text.strip():
            return None

        try:
            # Generate embedding using sentence-transformers
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            # Convert numpy array to list for JSON serialization
            return embedding.tolist()
        except Exception:
            # Embedding generation failed, return None
            return None

    def _cosine_similarity(
        self,
        a: list[float],
        b: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First embedding vector
            b: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if not a or not b or len(a) != len(b):
            return 0.0

        # Calculate dot product
        dot_product = sum(x * y for x, y in zip(a, b))

        # Calculate magnitudes
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        # Avoid division by zero
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    def _contains_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        return bool(self.CHINESE_PATTERN.search(text))

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text with support for Chinese and English.

        Chinese: Uses jieba if available, otherwise character-level
        English: Uses whitespace tokenization

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Normalize text
        text = text.lower().strip()

        # Check if text contains Chinese
        has_chinese = self._contains_chinese(text)

        if has_chinese:
            if self._jieba_available and self._jieba:
                # Use jieba for Chinese tokenization
                tokens = list(self._jieba.cut(text))
            else:
                # Fallback: character-level for Chinese, word-level for others
                tokens = self._character_tokenize(text)
        else:
            # English/other: whitespace tokenization
            tokens = re.findall(r'\b\w+\b', text)

        # Filter out empty tokens and single characters for non-Chinese
        if has_chinese:
            tokens = [t.strip() for t in tokens if t.strip()]
        else:
            tokens = [t for t in tokens if len(t) > 1 or t.isalpha()]

        return tokens

    def _character_tokenize(self, text: str) -> list[str]:
        """
        Character-level tokenization for Chinese text.

        Splits Chinese into individual characters while keeping
        English words together.
        """
        tokens: list[str] = []
        current_english: list[str] = []

        for char in text:
            if self.CHINESE_PATTERN.match(char):
                # Flush any accumulated English
                if current_english:
                    word = ''.join(current_english).strip()
                    if word:
                        tokens.append(word)
                    current_english = []
                # Add Chinese character as token
                tokens.append(char)
            elif char.isalnum():
                current_english.append(char)
            else:
                # Whitespace or punctuation
                if current_english:
                    word = ''.join(current_english).strip()
                    if word:
                        tokens.append(word)
                    current_english = []

        # Flush remaining English
        if current_english:
            word = ''.join(current_english).strip()
            if word:
                tokens.append(word)

        return tokens

    def _calculate_relevance(
        self,
        query: str,
        memory: MemoryItem,
        time_decay: bool = True,
        time_decay_factor: float = 0.1,
        query_embedding: list[float] | None = None,
    ) -> float:
        """
        Calculate relevance score between query and memory.

        Uses vector similarity if embeddings are available, otherwise falls back
        to TF-IDF-like scoring with:
        1. Token overlap (Jaccard similarity)
        2. Term frequency weighting
        3. Importance weighting
        4. Time decay (optional)

        Args:
            query: Search query
            memory: Memory item to compare
            time_decay: Whether to apply time decay
            time_decay_factor: Decay rate (higher = faster decay)
            query_embedding: Pre-computed query embedding (optional, for efficiency)

        Returns:
            Relevance score between 0 and 1
        """
        base_score = 0.0

        # Try vector similarity first if embeddings are available
        use_vector_similarity = (
            self._embeddings_available
            and memory.embedding is not None
        )

        if use_vector_similarity:
            # Generate query embedding if not provided
            if query_embedding is None:
                query_embedding = self._generate_embedding(query)

            if query_embedding is not None:
                # Calculate cosine similarity between query and memory embeddings
                cosine_sim = self._cosine_similarity(query_embedding, memory.embedding)
                # Normalize cosine similarity from [-1, 1] to [0, 1]
                base_score = (cosine_sim + 1.0) / 2.0
            else:
                # Embedding generation failed, fall back to token-based
                use_vector_similarity = False

        # Fall back to token-based similarity if vector similarity not available
        if not use_vector_similarity:
            # Tokenize query and memory content
            query_tokens = self._tokenize(query)
            memory_tokens = self._tokenize(memory.content)

            if not query_tokens or not memory_tokens:
                return 0.0

            # Calculate token overlap (Jaccard-like)
            query_set = set(query_tokens)
            memory_set = set(memory_tokens)

            intersection = query_set & memory_set
            union = query_set | memory_set

            if not union:
                return 0.0

            # Base relevance: Jaccard similarity
            jaccard = len(intersection) / len(union)

            # Term frequency bonus: reward more occurrences in memory
            tf_bonus = 0.0
            if intersection:
                memory_token_freq: dict[str, int] = {}
                for token in memory_tokens:
                    memory_token_freq[token] = memory_token_freq.get(token, 0) + 1

                total_freq = sum(memory_token_freq.get(t, 0) for t in intersection)
                tf_bonus = min(0.2, total_freq / (len(memory_tokens) * 2))

            # Coverage bonus: what fraction of query terms are found
            coverage = len(intersection) / len(query_set) if query_set else 0
            coverage_bonus = coverage * 0.2

            # Combine scores
            base_score = jaccard + tf_bonus + coverage_bonus

        # Apply importance weighting
        importance_weight = 0.7 + (memory.importance * 0.3)
        weighted_score = base_score * importance_weight

        # Apply time decay
        if time_decay:
            days_since_access = (datetime.now() - memory.last_accessed).days
            decay = math.exp(-time_decay_factor * days_since_access / 30)  # Monthly decay
            weighted_score *= decay

        # Access count boost (frequently accessed memories are more relevant)
        access_boost = 1.0 + min(0.1, memory.access_count * 0.01)
        weighted_score *= access_boost

        # Normalize to [0, 1]
        return min(1.0, max(0.0, weighted_score))

    def store(
        self,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """
        Store a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory (episodic, semantic, procedural)
            importance: Importance score (0-1)
            metadata: Additional metadata

        Returns:
            Created MemoryItem

        Raises:
            ValueError: If memory_type is invalid
        """
        if memory_type not in self.MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory type: {memory_type}. "
                f"Must be one of: {self.MEMORY_TYPES}"
            )

        importance = max(0.0, min(1.0, importance))

        now = datetime.now()
        memory_id = str(uuid.uuid4())

        # Generate embedding if enabled
        embedding = None
        if self.use_embeddings and self._embeddings_available:
            embedding = self._generate_embedding(content)

        memory = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=now,
            last_accessed=now,
            access_count=0,
            embedding=embedding,
            metadata=metadata or {},
        )

        self.memories[memory_id] = memory
        return memory

    def retrieve(
        self,
        query: MemoryQuery,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Retrieve relevant memories based on query.

        Args:
            query: MemoryQuery with search parameters

        Returns:
            List of (MemoryItem, relevance_score) tuples, sorted by relevance
        """
        results: list[tuple[MemoryItem, float]] = []

        # Pre-compute query embedding for efficiency (avoid regenerating for each memory)
        query_embedding = None
        if self._embeddings_available:
            query_embedding = self._generate_embedding(query.query)

        for memory in self.memories.values():
            # Filter by memory type if specified
            if query.memory_types and memory.memory_type not in query.memory_types:
                continue

            # Calculate relevance (pass pre-computed query embedding)
            relevance = self._calculate_relevance(
                query.query,
                memory,
                time_decay=query.time_decay,
                time_decay_factor=query.time_decay_factor,
                query_embedding=query_embedding,
            )

            # Filter by minimum relevance
            if relevance >= query.min_relevance:
                results.append((memory, relevance))

        # Sort by relevance (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        # Apply limit
        results = results[:query.limit]

        # Update access timestamps and counts
        now = datetime.now()
        for memory, _ in results:
            memory.last_accessed = now
            memory.access_count += 1

        return results

    def retrieve_by_type(
        self,
        memory_type: str,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """
        Retrieve memories by type.

        Args:
            memory_type: Type to filter by
            limit: Maximum number to return

        Returns:
            List of MemoryItems sorted by importance
        """
        memories = [
            m for m in self.memories.values()
            if m.memory_type == memory_type
        ]

        # Sort by importance
        memories.sort(key=lambda m: m.importance, reverse=True)

        return memories[:limit]

    def forget(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted, False if not found
        """
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False

    def consolidate(
        self,
        similarity_threshold: float = 0.8,
        min_importance: float = 0.2,
        max_age_days: int = 90,
    ) -> int:
        """
        Consolidate memories by merging similar ones and removing old/unimportant ones.

        Args:
            similarity_threshold: Threshold for merging similar memories
            min_importance: Minimum importance to keep
            max_age_days: Maximum age in days before considering removal

        Returns:
            Number of memories removed/merged
        """
        removed_count = 0
        now = datetime.now()

        # Phase 1: Remove old, unimportant, rarely accessed memories
        to_remove = []
        for memory_id, memory in self.memories.items():
            age_days = (now - memory.created_at).days

            # Remove if: old + low importance + rarely accessed
            if (
                age_days > max_age_days
                and memory.importance < min_importance
                and memory.access_count < 3
            ):
                to_remove.append(memory_id)

        for memory_id in to_remove:
            del self.memories[memory_id]
            removed_count += 1

        # Phase 2: Merge similar memories
        # Group by memory type first
        by_type: dict[str, list[MemoryItem]] = {}
        for memory in self.memories.values():
            if memory.memory_type not in by_type:
                by_type[memory.memory_type] = []
            by_type[memory.memory_type].append(memory)

        merged_ids = set()

        for memory_type, memories in by_type.items():
            for i, mem1 in enumerate(memories):
                if mem1.id in merged_ids:
                    continue

                for mem2 in memories[i + 1:]:
                    if mem2.id in merged_ids:
                        continue

                    # Calculate similarity
                    similarity = self._calculate_relevance(
                        mem1.content, mem2, time_decay=False
                    )

                    if similarity >= similarity_threshold:
                        # Merge: keep the more important one, combine metadata
                        if mem1.importance >= mem2.importance:
                            keeper, merger = mem1, mem2
                        else:
                            keeper, merger = mem2, mem1

                        # Update keeper with merged info
                        keeper.access_count += merger.access_count
                        keeper.importance = max(keeper.importance, merger.importance)
                        keeper.metadata.update(merger.metadata)

                        # Mark for removal
                        merged_ids.add(merger.id)

        # Remove merged memories
        for memory_id in merged_ids:
            if memory_id in self.memories:
                del self.memories[memory_id]
                removed_count += 1

        return removed_count

    def save_to_disk(self) -> None:
        """
        Persist memories to disk.

        Raises:
            ValueError: If storage_path is not set
        """
        if not self.storage_path:
            raise ValueError("Storage path not configured")

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize memories
        data = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "memories": [m.to_dict() for m in self.memories.values()],
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_disk(self) -> None:
        """
        Load memories from disk.

        Raises:
            ValueError: If storage_path is not set
            FileNotFoundError: If storage file doesn't exist
        """
        if not self.storage_path:
            raise ValueError("Storage path not configured")

        if not self.storage_path.exists():
            raise FileNotFoundError(f"Memory file not found: {self.storage_path}")

        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Clear existing memories
        self.memories.clear()

        # Load memories
        for memory_data in data.get("memories", []):
            memory = MemoryItem.from_dict(memory_data)
            self.memories[memory.id] = memory

    def get_statistics(self) -> dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Dictionary with statistics
        """
        now = datetime.now()

        # Count by type
        by_type: dict[str, int] = {}
        total_importance = 0.0
        total_access = 0
        oldest: datetime | None = None
        newest: datetime | None = None

        for memory in self.memories.values():
            by_type[memory.memory_type] = by_type.get(memory.memory_type, 0) + 1
            total_importance += memory.importance
            total_access += memory.access_count

            if oldest is None or memory.created_at < oldest:
                oldest = memory.created_at
            if newest is None or memory.created_at > newest:
                newest = memory.created_at

        count = len(self.memories)

        # Count memories with embeddings
        memories_with_embeddings = sum(
            1 for m in self.memories.values() if m.embedding is not None
        )

        return {
            "total_memories": count,
            "by_type": by_type,
            "average_importance": total_importance / count if count > 0 else 0,
            "total_access_count": total_access,
            "average_access_count": total_access / count if count > 0 else 0,
            "oldest_memory": oldest.isoformat() if oldest else None,
            "newest_memory": newest.isoformat() if newest else None,
            "jieba_available": self._jieba_available,
            "embeddings_available": self._embeddings_available,
            "embedding_model": self._embedding_model_name if self._embeddings_available else None,
            "memories_with_embeddings": memories_with_embeddings,
            "storage_path": str(self.storage_path) if self.storage_path else None,
        }

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """
        Update the importance of a memory.

        Args:
            memory_id: ID of memory to update
            importance: New importance value (0-1)

        Returns:
            True if updated, False if not found
        """
        if memory_id not in self.memories:
            return False

        self.memories[memory_id].importance = max(0.0, min(1.0, importance))
        return True

    def search_by_metadata(
        self,
        key: str,
        value: Any,
        limit: int = 10,
    ) -> list[MemoryItem]:
        """
        Search memories by metadata key-value pair.

        Args:
            key: Metadata key to search
            value: Value to match
            limit: Maximum results

        Returns:
            List of matching MemoryItems
        """
        results = [
            m for m in self.memories.values()
            if m.metadata.get(key) == value
        ]

        # Sort by importance
        results.sort(key=lambda m: m.importance, reverse=True)

        return results[:limit]

    def clear(self) -> int:
        """
        Clear all memories.

        Returns:
            Number of memories cleared
        """
        count = len(self.memories)
        self.memories.clear()
        return count

    def __len__(self) -> int:
        """Return number of memories."""
        return len(self.memories)

    def __contains__(self, memory_id: str) -> bool:
        """Check if memory exists."""
        return memory_id in self.memories
