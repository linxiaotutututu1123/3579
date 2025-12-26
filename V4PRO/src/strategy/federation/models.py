"""
Federation data models (Military Rule Level v4.2).

V4PRO Platform Component - Phase 8 Strategy Coordination
V4 SPEC: Section 28 Strategy Federation, Section 29 Signal Fusion

Military Rule Coverage:
- M1: Single Signal Source - Unique signal source guarantee
- M3: Audit Log - Complete operation traceability
- M6: Circuit Breaker - Federation-level protection

This module defines all data models for the Strategy Federation Hub:
- StrategyState: Strategy health and operational status
- ResourceRequest: Resource allocation requests
- ResourceAllocation: Resource allocation results
- FederationStatus: Federation-wide status summary
- ConflictRecord: Signal conflict information
- AuditEntry: Audit log entries
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class StrategyStatus(Enum):
    """Strategy operational status."""

    ACTIVE = "ACTIVE"  # Normal operation
    PAUSED = "PAUSED"  # Temporarily paused
    DEGRADED = "DEGRADED"  # Reduced capacity
    CIRCUIT_BREAK = "CIRCUIT_BREAK"  # Circuit breaker triggered
    DISABLED = "DISABLED"  # Administratively disabled
    ERROR = "ERROR"  # Error state


class ResourceType(Enum):
    """Resource types that can be allocated."""

    POSITION_QUOTA = "POSITION_QUOTA"  # Position quota
    MARGIN_QUOTA = "MARGIN_QUOTA"  # Margin quota
    ORDER_RATE = "ORDER_RATE"  # Order rate limit
    SIGNAL_PRIORITY = "SIGNAL_PRIORITY"  # Signal priority level
    COMPUTE_SLOTS = "COMPUTE_SLOTS"  # Compute resource slots


class ConflictType(Enum):
    """Signal conflict types."""

    DIRECTION = "DIRECTION"  # Opposing directions (LONG vs SHORT)
    DUPLICATE = "DUPLICATE"  # Same signal from same source
    RATE_LIMIT = "RATE_LIMIT"  # Signal rate exceeded
    PRIORITY = "PRIORITY"  # Priority conflict
    RESOURCE = "RESOURCE"  # Resource contention


class ResolutionAction(Enum):
    """Conflict resolution actions."""

    ACCEPT_FIRST = "ACCEPT_FIRST"  # Accept first signal
    ACCEPT_HIGHEST = "ACCEPT_HIGHEST"  # Accept highest priority/confidence
    MERGE = "MERGE"  # Merge signals
    REJECT_ALL = "REJECT_ALL"  # Reject all conflicting signals
    DEFER = "DEFER"  # Defer decision
    FLAT = "FLAT"  # Force flat position


class AuditEventType(Enum):
    """Audit event types for M3 compliance."""

    STRATEGY_REGISTERED = "STRATEGY_REGISTERED"
    STRATEGY_UNREGISTERED = "STRATEGY_UNREGISTERED"
    STRATEGY_ENABLED = "STRATEGY_ENABLED"
    STRATEGY_DISABLED = "STRATEGY_DISABLED"
    SIGNAL_SUBMITTED = "SIGNAL_SUBMITTED"
    SIGNAL_VALIDATED = "SIGNAL_VALIDATED"
    SIGNAL_REJECTED = "SIGNAL_REJECTED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    CONFLICT_RESOLVED = "CONFLICT_RESOLVED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    CIRCUIT_BREAK_TRIGGERED = "CIRCUIT_BREAK_TRIGGERED"
    CIRCUIT_BREAK_RECOVERED = "CIRCUIT_BREAK_RECOVERED"
    FEDERATION_STATUS_CHANGED = "FEDERATION_STATUS_CHANGED"


@dataclass(frozen=True, slots=True)
class StrategyState:
    """Strategy operational state (immutable).

    Attributes:
        strategy_id: Unique strategy identifier
        name: Human-readable strategy name
        status: Current operational status
        health_score: Health score (0.0-1.0)
        signal_count: Total signals generated
        hit_count: Successful signal count
        error_count: Error count
        last_signal_time: Last signal timestamp
        last_error: Last error message
        metadata: Additional metadata
    """

    strategy_id: str
    name: str
    status: StrategyStatus = StrategyStatus.ACTIVE
    health_score: float = 1.0
    signal_count: int = 0
    hit_count: int = 0
    error_count: int = 0
    last_signal_time: float = 0.0
    last_error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        if self.signal_count == 0:
            return 0.0
        return self.hit_count / self.signal_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.signal_count == 0:
            return 0.0
        return self.error_count / self.signal_count

    @property
    def is_healthy(self) -> bool:
        """Check if strategy is healthy."""
        return (
            self.status == StrategyStatus.ACTIVE
            and self.health_score >= 0.7
            and self.error_rate < 0.1
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "status": self.status.value,
            "health_score": round(self.health_score, 4),
            "signal_count": self.signal_count,
            "hit_count": self.hit_count,
            "error_count": self.error_count,
            "hit_rate": round(self.hit_rate, 4),
            "error_rate": round(self.error_rate, 4),
            "last_signal_time": self.last_signal_time,
            "last_error": self.last_error,
            "is_healthy": self.is_healthy,
        }


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    """Resource allocation request (immutable).

    Attributes:
        strategy_id: Requesting strategy ID
        resource_type: Type of resource requested
        amount: Requested amount
        priority: Request priority (higher = more urgent)
        reason: Reason for request
        timestamp: Request timestamp
    """

    strategy_id: str
    resource_type: ResourceType
    amount: float
    priority: int = 5
    reason: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "resource_type": self.resource_type.value,
            "amount": self.amount,
            "priority": self.priority,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True, slots=True)
class ResourceAllocation:
    """Resource allocation result (immutable).

    Attributes:
        request: Original request
        allocated_amount: Actually allocated amount
        success: Whether allocation succeeded
        message: Status message
        expiry_time: When allocation expires
        allocation_id: Unique allocation ID
    """

    request: ResourceRequest
    allocated_amount: float
    success: bool
    message: str = ""
    expiry_time: float = 0.0
    allocation_id: str = ""

    @property
    def is_partial(self) -> bool:
        """Check if allocation is partial."""
        return self.success and self.allocated_amount < self.request.amount

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allocation_id": self.allocation_id,
            "strategy_id": self.request.strategy_id,
            "resource_type": self.request.resource_type.value,
            "requested_amount": self.request.amount,
            "allocated_amount": self.allocated_amount,
            "success": self.success,
            "is_partial": self.is_partial,
            "message": self.message,
            "expiry_time": self.expiry_time,
        }


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    """Signal conflict record (immutable).

    Attributes:
        conflict_id: Unique conflict identifier
        conflict_type: Type of conflict
        signal_ids: IDs of conflicting signals
        strategy_ids: IDs of conflicting strategies
        symbol: Trading symbol
        resolution: Resolution action taken
        winner_signal_id: ID of winning signal (if any)
        timestamp: Conflict detection timestamp
        details: Additional conflict details
    """

    conflict_id: str
    conflict_type: ConflictType
    signal_ids: tuple[str, ...]
    strategy_ids: tuple[str, ...]
    symbol: str
    resolution: ResolutionAction
    winner_signal_id: str = ""
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "signal_ids": list(self.signal_ids),
            "strategy_ids": list(self.strategy_ids),
            "symbol": self.symbol,
            "resolution": self.resolution.value,
            "winner_signal_id": self.winner_signal_id,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Audit log entry (immutable) - M3 Compliance.

    Attributes:
        entry_id: Unique entry identifier
        event_type: Type of audit event
        timestamp: Event timestamp
        strategy_id: Related strategy ID (if any)
        signal_id: Related signal ID (if any)
        action: Action taken
        result: Action result
        details: Additional details
        operator: Operator who initiated action
    """

    entry_id: str
    event_type: AuditEventType
    timestamp: float
    strategy_id: str = ""
    signal_id: str = ""
    action: str = ""
    result: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    operator: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "operator": self.operator,
        }


@dataclass
class FederationStatus:
    """Federation-wide status summary.

    Attributes:
        total_strategies: Total registered strategies
        active_strategies: Currently active strategies
        healthy_strategies: Healthy strategy count
        total_signals: Total signals processed
        total_conflicts: Total conflicts detected
        circuit_breaker_active: Whether federation circuit breaker is active
        position_ratio: Current position ratio (for M6)
        last_update: Last status update timestamp
        strategy_states: Individual strategy states
    """

    total_strategies: int = 0
    active_strategies: int = 0
    healthy_strategies: int = 0
    total_signals: int = 0
    total_conflicts: int = 0
    circuit_breaker_active: bool = False
    position_ratio: float = 1.0
    last_update: float = field(default_factory=time.time)
    strategy_states: dict[str, StrategyState] = field(default_factory=dict)

    @property
    def health_ratio(self) -> float:
        """Calculate overall health ratio."""
        if self.total_strategies == 0:
            return 1.0
        return self.healthy_strategies / self.total_strategies

    @property
    def conflict_ratio(self) -> float:
        """Calculate conflict ratio."""
        if self.total_signals == 0:
            return 0.0
        return self.total_conflicts / self.total_signals

    @property
    def is_healthy(self) -> bool:
        """Check if federation is healthy."""
        return (
            self.health_ratio >= 0.7
            and self.conflict_ratio < 0.3
            and not self.circuit_breaker_active
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_strategies": self.total_strategies,
            "active_strategies": self.active_strategies,
            "healthy_strategies": self.healthy_strategies,
            "total_signals": self.total_signals,
            "total_conflicts": self.total_conflicts,
            "health_ratio": round(self.health_ratio, 4),
            "conflict_ratio": round(self.conflict_ratio, 4),
            "circuit_breaker_active": self.circuit_breaker_active,
            "position_ratio": round(self.position_ratio, 4),
            "is_healthy": self.is_healthy,
            "last_update": self.last_update,
            "last_update_iso": datetime.fromtimestamp(
                self.last_update, tz=timezone.utc
            ).isoformat(),
        }


__all__ = [
    # Enums
    "StrategyStatus",
    "ResourceType",
    "ConflictType",
    "ResolutionAction",
    "AuditEventType",
    # Data classes
    "StrategyState",
    "ResourceRequest",
    "ResourceAllocation",
    "ConflictRecord",
    "AuditEntry",
    "FederationStatus",
]
