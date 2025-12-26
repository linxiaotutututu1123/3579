"""
V4PRO 降级兜底机制模块.

Phase 8 核心组件 - M4军规实现
"""

from src.execution.fallback.fallback_manager import (
    FallbackConfig,
    FallbackLevel,
    FallbackManager,
    FallbackResult,
    FallbackStrategy,
)
from src.execution.fallback.fallback_executor import (
    FallbackExecutor,
    ExecutionMode,
)

__all__ = [
    "FallbackConfig",
    "FallbackLevel",
    "FallbackManager",
    "FallbackResult",
    "FallbackStrategy",
    "FallbackExecutor",
    "ExecutionMode",
]
