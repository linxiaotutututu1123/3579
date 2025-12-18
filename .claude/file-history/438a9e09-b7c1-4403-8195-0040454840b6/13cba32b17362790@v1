"""Replay Verifier for Deterministic Event Verification (Military-Grade v3.0).

Implements replay verification as specified in V2 SPEC 7.3.
Verifies that same inputs produce identical decision and guardian event sequences.

Required Scenarios:
- REPLAY.DETERMINISTIC.DECISION: Same input produces identical DecisionEvent sequence
- REPLAY.DETERMINISTIC.GUARDIAN: Same input produces identical GuardianEvent sequence

Verification Process:
1. Load events from two JSONL files (original and replay)
2. Filter by event type (decision or guardian)
3. Compute SHA256 hash of event sequence (excluding timestamps)
4. Compare hashes and report differences

Example:
    from src.replay.verifier import ReplayVerifier

    verifier = ReplayVerifier()

    # Verify decision events
    result = verifier.verify_decision_sequence(
        events_a=original_events,
        events_b=replay_events,
    )

    if result.is_match:
        print("Decision sequences match!")
    else:
        print(f"Mismatch at index {result.first_mismatch_index}")
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VerifyResult:
    """Result of sequence verification.

    Attributes:
        is_match: Whether sequences match
        hash_a: Hash of sequence A
        hash_b: Hash of sequence B
        length_a: Length of sequence A
        length_b: Length of sequence B
        first_mismatch_index: Index of first mismatch (-1 if match)
        first_mismatch_a: First mismatched event from A
        first_mismatch_b: First mismatched event from B
        details: Additional details
    """

    is_match: bool
    hash_a: str
    hash_b: str
    length_a: int
    length_b: int
    first_mismatch_index: int = -1
    first_mismatch_a: dict[str, Any] | None = None
    first_mismatch_b: dict[str, Any] | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "is_match": self.is_match,
            "hash_a": self.hash_a,
            "hash_b": self.hash_b,
            "length_a": self.length_a,
            "length_b": self.length_b,
            "first_mismatch_index": self.first_mismatch_index,
            "first_mismatch_a": self.first_mismatch_a,
            "first_mismatch_b": self.first_mismatch_b,
            "details": self.details,
        }


class ReplayVerifier:
    """Verifier for deterministic replay of events.

    Ensures that same inputs produce identical event sequences for both
    decision events (strategy output) and guardian events (mode changes).

    Required Scenarios Coverage:
    - REPLAY.DETERMINISTIC.DECISION: verify_decision_sequence()
    - REPLAY.DETERMINISTIC.GUARDIAN: verify_guardian_sequence()
    """

    # Fields to exclude from comparison (timestamps may vary slightly)
    EXCLUDE_FIELDS = {"ts", "timestamp", "received_at"}

    # Maximum timestamp difference allowed (ms)
    MAX_TS_DIFF_MS = 1.0

    def __init__(self) -> None:
        """Initialize replay verifier."""
        pass

    def verify_decision_sequence(
        self,
        events_a: list[dict[str, Any]],
        events_b: list[dict[str, Any]],
    ) -> VerifyResult:
        """Verify decision event sequences match.

        Scenario: REPLAY.DETERMINISTIC.DECISION

        Args:
            events_a: Decision events from run A
            events_b: Decision events from run B

        Returns:
            VerifyResult indicating match status
        """
        # Filter to decision events only
        decisions_a = self._filter_by_type(events_a, "decision")
        decisions_b = self._filter_by_type(events_b, "decision")

        return self._verify_sequences(decisions_a, decisions_b)

    def verify_guardian_sequence(
        self,
        events_a: list[dict[str, Any]],
        events_b: list[dict[str, Any]],
    ) -> VerifyResult:
        """Verify guardian event sequences match.

        Scenario: REPLAY.DETERMINISTIC.GUARDIAN

        Args:
            events_a: Guardian events from run A
            events_b: Guardian events from run B

        Returns:
            VerifyResult indicating match status
        """
        # Filter to guardian events only
        guardian_a = self._filter_by_type(events_a, "guardian")
        guardian_b = self._filter_by_type(events_b, "guardian")

        return self._verify_sequences(guardian_a, guardian_b)

    def _filter_by_type(
        self,
        events: list[dict[str, Any]],
        event_type: str,
    ) -> list[dict[str, Any]]:
        """Filter events by type prefix.

        Args:
            events: List of events
            event_type: Event type prefix to filter

        Returns:
            Filtered events
        """
        filtered = []
        for event in events:
            et = event.get("event_type", "")
            # Match prefix (e.g., "decision" matches "decision", "decision_start")
            # or exact type for guardian events
            if et.startswith(event_type) or et == event_type:
                filtered.append(event)
            # Also match guardian_* patterns
            elif event_type == "guardian" and "guardian" in et:
                filtered.append(event)
        return filtered

    def _verify_sequences(
        self,
        events_a: list[dict[str, Any]],
        events_b: list[dict[str, Any]],
    ) -> VerifyResult:
        """Verify two event sequences match.

        Args:
            events_a: Events from run A
            events_b: Events from run B

        Returns:
            VerifyResult
        """
        # Compute hashes
        hash_a = self.compute_hash(events_a)
        hash_b = self.compute_hash(events_b)

        # Quick check: hashes match
        if hash_a == hash_b:
            return VerifyResult(
                is_match=True,
                hash_a=hash_a,
                hash_b=hash_b,
                length_a=len(events_a),
                length_b=len(events_b),
            )

        # Find first mismatch
        first_mismatch_idx = -1
        first_mismatch_a = None
        first_mismatch_b = None

        max_len = max(len(events_a), len(events_b))
        for i in range(max_len):
            event_a = events_a[i] if i < len(events_a) else None
            event_b = events_b[i] if i < len(events_b) else None

            if not self._events_match(event_a, event_b):
                first_mismatch_idx = i
                first_mismatch_a = event_a
                first_mismatch_b = event_b
                break

        return VerifyResult(
            is_match=False,
            hash_a=hash_a,
            hash_b=hash_b,
            length_a=len(events_a),
            length_b=len(events_b),
            first_mismatch_index=first_mismatch_idx,
            first_mismatch_a=first_mismatch_a,
            first_mismatch_b=first_mismatch_b,
            details={
                "length_mismatch": len(events_a) != len(events_b),
            },
        )

    def _events_match(
        self,
        event_a: dict[str, Any] | None,
        event_b: dict[str, Any] | None,
    ) -> bool:
        """Check if two events match (excluding timestamp).

        Args:
            event_a: Event A
            event_b: Event B

        Returns:
            True if events match
        """
        if event_a is None and event_b is None:
            return True
        if event_a is None or event_b is None:
            return False

        # Compare normalized events
        norm_a = self._normalize_event(event_a)
        norm_b = self._normalize_event(event_b)

        return norm_a == norm_b

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Normalize event for comparison (remove timestamps).

        Args:
            event: Event to normalize

        Returns:
            Normalized event
        """
        normalized = {}
        for key, value in event.items():
            if key not in self.EXCLUDE_FIELDS:
                # Recursively normalize nested dicts
                if isinstance(value, dict):
                    normalized[key] = self._normalize_event(value)
                else:
                    normalized[key] = value
        return normalized

    def compute_hash(self, events: list[dict[str, Any]]) -> str:
        """Compute SHA256 hash of event sequence.

        Args:
            events: List of events

        Returns:
            SHA256 hash string
        """
        # Normalize all events
        normalized = [self._normalize_event(e) for e in events]

        # Serialize deterministically
        serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=True)

        # Compute hash
        return hashlib.sha256(serialized.encode()).hexdigest()

    def load_events_from_jsonl(self, path: Path) -> list[dict[str, Any]]:
        """Load events from JSONL file.

        Args:
            path: Path to JSONL file

        Returns:
            List of events
        """
        events: list[dict[str, Any]] = []

        if not path.exists():
            return events

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

        return events

    def verify_files(
        self,
        path_a: Path,
        path_b: Path,
        event_type: str = "decision",
    ) -> VerifyResult:
        """Verify event sequences from two JSONL files.

        Args:
            path_a: Path to first JSONL file
            path_b: Path to second JSONL file
            event_type: Event type to verify ("decision" or "guardian")

        Returns:
            VerifyResult
        """
        events_a = self.load_events_from_jsonl(path_a)
        events_b = self.load_events_from_jsonl(path_b)

        if event_type == "decision":
            return self.verify_decision_sequence(events_a, events_b)
        elif event_type == "guardian":
            return self.verify_guardian_sequence(events_a, events_b)
        else:
            # Verify all events
            return self._verify_sequences(events_a, events_b)


def verify_replay_determinism(
    original_path: Path,
    replay_path: Path,
) -> tuple[VerifyResult, VerifyResult]:
    """Convenience function to verify both decision and guardian determinism.

    Args:
        original_path: Path to original run JSONL
        replay_path: Path to replay run JSONL

    Returns:
        Tuple of (decision_result, guardian_result)
    """
    verifier = ReplayVerifier()

    original_events = verifier.load_events_from_jsonl(original_path)
    replay_events = verifier.load_events_from_jsonl(replay_path)

    decision_result = verifier.verify_decision_sequence(
        original_events, replay_events
    )
    guardian_result = verifier.verify_guardian_sequence(
        original_events, replay_events
    )

    return decision_result, guardian_result
