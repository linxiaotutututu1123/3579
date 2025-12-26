"""协作模块 - 辩论、共识、结对编程.

This module provides collaboration mechanisms for agents including:
- Pair Programming: Driver/navigator pattern for collaborative coding
- Debate: Structured technical discussions (planned)
- Consensus: Group decision making (planned)
"""

from __future__ import annotations

from .pair_programming import (
    BaseAgent,
    PairMessage,
    PairMessageType,
    PairProgrammingSystem,
    PairResult,
    PairRole,
    PairSession,
)

__all__ = [
    # Pair Programming
    "BaseAgent",
    "PairMessage",
    "PairMessageType",
    "PairProgrammingSystem",
    "PairResult",
    "PairRole",
    "PairSession",
]
