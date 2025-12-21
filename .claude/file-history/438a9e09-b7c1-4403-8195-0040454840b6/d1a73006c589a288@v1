"""Replay Module (Military-Grade v3.0).

This module provides replay functionality for deterministic verification
as specified in V2 SPEC 7.3.

Components:
- ReplayVerifier: Verifies event sequence determinism
- verify_replay_determinism: Convenience function for verification

Required Scenarios:
- REPLAY.DETERMINISTIC.DECISION: Same input produces identical DecisionEvent
- REPLAY.DETERMINISTIC.GUARDIAN: Same input produces identical GuardianEvent

Example:
    from src.replay import ReplayVerifier

    verifier = ReplayVerifier()

    # Verify decision sequences
    result = verifier.verify_decision_sequence(
        events_a=original_events,
        events_b=replay_events,
    )

    print(f"Match: {result.is_match}")
"""

from __future__ import annotations

from src.replay.verifier import (
    ReplayVerifier,
    VerifyResult,
    verify_replay_determinism,
)

__all__ = [
    "ReplayVerifier",
    "VerifyResult",
    "verify_replay_determinism",
]
