"""
Shared pytest fixtures for Chairman Agents test suite.

Provides common fixtures for:
- LLM client mocking
- Memory system setup
- Agent creation
- Async event loop management
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Event Loop Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def memory_storage_path(test_data_dir: Path) -> Path:
    """Create path for memory storage."""
    return test_data_dir / "memory.json"


# =============================================================================
# Mock LLM Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Standard mock LLM response."""
    return {
        "id": "test-response-id",
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from the LLM.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create mock LLM client."""
    client = MagicMock()
    client.complete = AsyncMock(return_value=MagicMock(
        text="Mock completion response",
        tokens_used=30,
        model="test-model",
    ))
    client.chat = AsyncMock(return_value=MagicMock(
        content="Mock chat response",
        tokens_used=30,
        model="test-model",
    ))
    return client


# =============================================================================
# Memory Fixtures
# =============================================================================

@pytest.fixture
def memory_system(memory_storage_path: Path):
    """Create memory system for testing."""
    from chairman_agents.cognitive.memory import MemorySystem

    return MemorySystem(
        storage_path=memory_storage_path,
        use_embeddings=False,  # Disable for faster tests
    )


@pytest.fixture
def memory_system_with_data(memory_system):
    """Memory system pre-populated with test data."""
    from chairman_agents.cognitive.memory import MemoryItem

    # Add episodic memories
    memory_system.store(
        content="User requested feature X implementation",
        memory_type="episodic",
        importance=0.8,
        metadata={"task_id": "task-001"},
    )
    memory_system.store(
        content="Bug fix completed for issue #123",
        memory_type="episodic",
        importance=0.6,
        metadata={"issue": "123"},
    )

    # Add semantic memories
    memory_system.store(
        content="Python best practices for async programming",
        memory_type="semantic",
        importance=0.9,
        metadata={"topic": "async"},
    )

    # Add procedural memories
    memory_system.store(
        content="Steps to deploy: build, test, deploy",
        memory_type="procedural",
        importance=0.7,
        metadata={"workflow": "deploy"},
    )

    return memory_system


# =============================================================================
# Cache Fixtures
# =============================================================================

@pytest.fixture
def cache_config():
    """Create cache configuration for testing."""
    from chairman_agents.integration.llm_cache import CacheConfig

    return CacheConfig(
        enabled=True,
        max_size=100,
        ttl_seconds=60.0,
    )


@pytest.fixture
def llm_cache(cache_config):
    """Create LLM response cache for testing."""
    from chairman_agents.integration.llm_cache import LLMResponseCache

    return LLMResponseCache(cache_config)


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def mock_task() -> MagicMock:
    """Create mock task for agent testing."""
    task = MagicMock()
    task.id = "test-task-001"
    task.title = "Test Task"
    task.description = "A test task for unit testing"
    task.context = {
        "method": "POST",
        "path": "/api/users/{user_id}",
        "auth_required": True,
    }
    task.priority = 1
    task.status = "pending"
    return task


@pytest.fixture
def mock_agent_context() -> dict[str, Any]:
    """Create mock agent context."""
    return {
        "session_id": "test-session-001",
        "user_id": "test-user",
        "project_path": "/test/project",
        "capabilities": ["code_generation", "analysis", "debugging"],
    }


# =============================================================================
# Async Fixtures
# =============================================================================

@pytest.fixture
async def async_mock_client() -> AsyncGenerator[AsyncMock, None]:
    """Async mock client for integration tests."""
    client = AsyncMock()
    client.get = AsyncMock(return_value={"status": "ok"})
    client.post = AsyncMock(return_value={"id": "created"})
    client.put = AsyncMock(return_value={"updated": True})
    client.delete = AsyncMock(return_value={"deleted": True})
    yield client


# =============================================================================
# Utility Functions
# =============================================================================

def create_test_memory_item(
    content: str = "Test content",
    memory_type: str = "semantic",
    importance: float = 0.5,
) -> dict[str, Any]:
    """Create test memory item data."""
    from datetime import datetime
    import uuid

    return {
        "id": str(uuid.uuid4()),
        "content": content,
        "memory_type": memory_type,
        "importance": importance,
        "created_at": datetime.now().isoformat(),
        "last_accessed": datetime.now().isoformat(),
        "access_count": 0,
        "embedding": None,
        "metadata": {},
    }


# =============================================================================
# Markers Configuration
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_llm: Requires LLM API")
    config.addinivalue_line("markers", "orchestration: Orchestration module tests")
    config.addinivalue_line("markers", "workflow: Workflow pipeline tests")
    config.addinivalue_line("markers", "llm: LLM client tests")
