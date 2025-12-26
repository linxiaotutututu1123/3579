"""
Strategy Registry (Military Rule Level v4.2).

V4PRO Platform Component - Phase 8 Strategy Coordination
V4 SPEC: Section 28 Strategy Federation

Military Rule Coverage:
- M1: Single Signal Source - Strategy uniqueness guarantee
- M3: Audit Log - Complete registration traceability

This module manages strategy registration and lifecycle:
- Thread-safe strategy registration/unregistration
- Strategy metadata and state tracking
- Callback system for registration events
- Health monitoring integration
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.strategy.federation.models import (
    AuditEntry,
    AuditEventType,
    StrategyState,
    StrategyStatus,
)


if TYPE_CHECKING:
    from collections.abc import Callable


class RegistryEventType(Enum):
    """Registry event types."""

    REGISTERED = "REGISTERED"
    UNREGISTERED = "UNREGISTERED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    STATUS_CHANGED = "STATUS_CHANGED"
    HEALTH_UPDATED = "HEALTH_UPDATED"


@dataclass
class RegistryEvent:
    """Registry event for callback notification.

    Attributes:
        event_type: Type of event
        strategy_id: Affected strategy ID
        timestamp: Event timestamp
        old_state: Previous state (if applicable)
        new_state: New state (if applicable)
        details: Additional event details
    """

    event_type: RegistryEventType
    strategy_id: str
    timestamp: float = field(default_factory=time.time)
    old_state: StrategyState | None = None
    new_state: StrategyState | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type.value,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "old_state": self.old_state.to_dict() if self.old_state else None,
            "new_state": self.new_state.to_dict() if self.new_state else None,
            "details": self.details,
        }


@dataclass
class StrategyMetadata:
    """Strategy metadata for registry.

    Attributes:
        strategy_id: Unique strategy identifier
        name: Human-readable name
        version: Strategy version
        tags: Classification tags
        config: Strategy configuration
        registered_at: Registration timestamp
        registered_by: Who registered the strategy
    """

    strategy_id: str
    name: str
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    registered_by: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "tags": list(self.tags),
            "config": dict(self.config),
            "registered_at": self.registered_at,
            "registered_at_iso": datetime.fromtimestamp(
                self.registered_at, tz=timezone.utc
            ).isoformat(),
            "registered_by": self.registered_by,
        }


class StrategyRegistry:
    """Strategy Registry (M1/M3 Compliant).

    Thread-safe registry for managing strategy lifecycle:
    - Registration with uniqueness validation
    - Status tracking and health monitoring
    - Event callbacks for integration
    - Audit logging for compliance

    Example:
        >>> registry = StrategyRegistry()
        >>> # Register a strategy
        >>> success = registry.register(
        ...     strategy_id="kalman_arb",
        ...     name="Kalman Arbitrage",
        ...     weight=0.3,
        ... )
        >>> # Get strategy state
        >>> state = registry.get_state("kalman_arb")
        >>> # Enable/disable
        >>> registry.disable("kalman_arb")
        >>> registry.enable("kalman_arb")
    """

    def __init__(
        self,
        audit_logger: Callable[[AuditEntry], None] | None = None,
    ) -> None:
        """Initialize registry.

        Args:
            audit_logger: Optional audit log callback
        """
        self._lock = threading.RLock()

        # Strategy storage
        self._metadata: dict[str, StrategyMetadata] = {}
        self._states: dict[str, StrategyState] = {}
        self._weights: dict[str, float] = {}
        self._dynamic_weights: dict[str, float] = {}

        # Callbacks
        self._event_callbacks: list[Callable[[RegistryEvent], None]] = []
        self._audit_logger = audit_logger

        # Statistics
        self._register_count = 0
        self._unregister_count = 0

    @property
    def strategy_count(self) -> int:
        """Total registered strategies."""
        with self._lock:
            return len(self._metadata)

    @property
    def active_count(self) -> int:
        """Active strategy count."""
        with self._lock:
            return sum(
                1
                for state in self._states.values()
                if state.status == StrategyStatus.ACTIVE
            )

    def register(
        self,
        strategy_id: str,
        name: str | None = None,
        weight: float = 0.1,
        version: str = "1.0.0",
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
        registered_by: str = "system",
    ) -> bool:
        """Register a strategy.

        Args:
            strategy_id: Unique strategy identifier
            name: Human-readable name (defaults to strategy_id)
            weight: Initial weight (0-1)
            version: Strategy version
            tags: Classification tags
            config: Strategy configuration
            registered_by: Registration source

        Returns:
            True if registered successfully, False if already exists
        """
        with self._lock:
            if strategy_id in self._metadata:
                return False

            # Create metadata
            metadata = StrategyMetadata(
                strategy_id=strategy_id,
                name=name or strategy_id,
                version=version,
                tags=tags or [],
                config=config or {},
                registered_at=time.time(),
                registered_by=registered_by,
            )

            # Create initial state
            state = StrategyState(
                strategy_id=strategy_id,
                name=name or strategy_id,
                status=StrategyStatus.ACTIVE,
                health_score=1.0,
            )

            # Store
            self._metadata[strategy_id] = metadata
            self._states[strategy_id] = state
            self._weights[strategy_id] = max(0.0, min(1.0, weight))
            self._dynamic_weights[strategy_id] = self._weights[strategy_id]

            self._register_count += 1

        # Notify
        event = RegistryEvent(
            event_type=RegistryEventType.REGISTERED,
            strategy_id=strategy_id,
            new_state=state,
            details={"weight": weight, "version": version},
        )
        self._notify_event(event)
        self._log_audit(
            AuditEventType.STRATEGY_REGISTERED,
            strategy_id=strategy_id,
            action="register",
            result="success",
            details=metadata.to_dict(),
        )

        return True

    def unregister(self, strategy_id: str) -> bool:
        """Unregister a strategy.

        Args:
            strategy_id: Strategy ID to unregister

        Returns:
            True if unregistered successfully
        """
        with self._lock:
            if strategy_id not in self._metadata:
                return False

            old_state = self._states.get(strategy_id)

            del self._metadata[strategy_id]
            del self._states[strategy_id]
            self._weights.pop(strategy_id, None)
            self._dynamic_weights.pop(strategy_id, None)

            self._unregister_count += 1

        # Notify
        event = RegistryEvent(
            event_type=RegistryEventType.UNREGISTERED,
            strategy_id=strategy_id,
            old_state=old_state,
        )
        self._notify_event(event)
        self._log_audit(
            AuditEventType.STRATEGY_UNREGISTERED,
            strategy_id=strategy_id,
            action="unregister",
            result="success",
        )

        return True

    def is_registered(self, strategy_id: str) -> bool:
        """Check if strategy is registered.

        Args:
            strategy_id: Strategy ID to check

        Returns:
            True if registered
        """
        with self._lock:
            return strategy_id in self._metadata

    def is_active(self, strategy_id: str) -> bool:
        """Check if strategy is active.

        Args:
            strategy_id: Strategy ID to check

        Returns:
            True if active
        """
        with self._lock:
            state = self._states.get(strategy_id)
            return state is not None and state.status == StrategyStatus.ACTIVE

    def enable(self, strategy_id: str) -> bool:
        """Enable a strategy.

        Args:
            strategy_id: Strategy ID to enable

        Returns:
            True if enabled successfully
        """
        return self._update_status(strategy_id, StrategyStatus.ACTIVE)

    def disable(self, strategy_id: str) -> bool:
        """Disable a strategy.

        Args:
            strategy_id: Strategy ID to disable

        Returns:
            True if disabled successfully
        """
        return self._update_status(strategy_id, StrategyStatus.DISABLED)

    def pause(self, strategy_id: str) -> bool:
        """Pause a strategy.

        Args:
            strategy_id: Strategy ID to pause

        Returns:
            True if paused successfully
        """
        return self._update_status(strategy_id, StrategyStatus.PAUSED)

    def circuit_break(self, strategy_id: str) -> bool:
        """Trigger circuit breaker for a strategy (M6).

        Args:
            strategy_id: Strategy ID

        Returns:
            True if circuit breaker activated
        """
        return self._update_status(strategy_id, StrategyStatus.CIRCUIT_BREAK)

    def _update_status(
        self,
        strategy_id: str,
        new_status: StrategyStatus,
    ) -> bool:
        """Update strategy status.

        Args:
            strategy_id: Strategy ID
            new_status: New status

        Returns:
            True if updated
        """
        with self._lock:
            if strategy_id not in self._states:
                return False

            old_state = self._states[strategy_id]
            if old_state.status == new_status:
                return True

            # Create new state (immutable)
            new_state = StrategyState(
                strategy_id=old_state.strategy_id,
                name=old_state.name,
                status=new_status,
                health_score=old_state.health_score,
                signal_count=old_state.signal_count,
                hit_count=old_state.hit_count,
                error_count=old_state.error_count,
                last_signal_time=old_state.last_signal_time,
                last_error=old_state.last_error,
                metadata=old_state.metadata,
            )
            self._states[strategy_id] = new_state

        # Determine event type
        event_type = (
            RegistryEventType.ENABLED
            if new_status == StrategyStatus.ACTIVE
            else (
                RegistryEventType.DISABLED
                if new_status == StrategyStatus.DISABLED
                else RegistryEventType.STATUS_CHANGED
            )
        )

        event = RegistryEvent(
            event_type=event_type,
            strategy_id=strategy_id,
            old_state=old_state,
            new_state=new_state,
        )
        self._notify_event(event)

        # Audit log
        audit_type = (
            AuditEventType.STRATEGY_ENABLED
            if new_status == StrategyStatus.ACTIVE
            else (
                AuditEventType.STRATEGY_DISABLED
                if new_status == StrategyStatus.DISABLED
                else AuditEventType.CIRCUIT_BREAK_TRIGGERED
                if new_status == StrategyStatus.CIRCUIT_BREAK
                else AuditEventType.STRATEGY_DISABLED
            )
        )
        self._log_audit(
            audit_type,
            strategy_id=strategy_id,
            action=f"status_change_to_{new_status.value}",
            result="success",
        )

        return True

    def get_state(self, strategy_id: str) -> StrategyState | None:
        """Get strategy state.

        Args:
            strategy_id: Strategy ID

        Returns:
            Strategy state or None
        """
        with self._lock:
            return self._states.get(strategy_id)

    def get_metadata(self, strategy_id: str) -> StrategyMetadata | None:
        """Get strategy metadata.

        Args:
            strategy_id: Strategy ID

        Returns:
            Strategy metadata or None
        """
        with self._lock:
            return self._metadata.get(strategy_id)

    def get_weight(self, strategy_id: str) -> float:
        """Get strategy weight.

        Args:
            strategy_id: Strategy ID

        Returns:
            Weight value (0.0 if not found)
        """
        with self._lock:
            return self._weights.get(strategy_id, 0.0)

    def set_weight(self, strategy_id: str, weight: float) -> bool:
        """Set strategy weight.

        Args:
            strategy_id: Strategy ID
            weight: Weight value (0-1)

        Returns:
            True if updated
        """
        with self._lock:
            if strategy_id not in self._metadata:
                return False
            self._weights[strategy_id] = max(0.0, min(1.0, weight))
            return True

    def get_dynamic_weight(self, strategy_id: str) -> float:
        """Get dynamic weight.

        Args:
            strategy_id: Strategy ID

        Returns:
            Dynamic weight value
        """
        with self._lock:
            return self._dynamic_weights.get(strategy_id, 0.0)

    def set_dynamic_weight(self, strategy_id: str, weight: float) -> bool:
        """Set dynamic weight.

        Args:
            strategy_id: Strategy ID
            weight: Dynamic weight value

        Returns:
            True if updated
        """
        with self._lock:
            if strategy_id not in self._metadata:
                return False
            self._dynamic_weights[strategy_id] = max(0.0, weight)
            return True

    def update_health(
        self,
        strategy_id: str,
        health_score: float,
        signal_count: int | None = None,
        hit_count: int | None = None,
        error_count: int | None = None,
        last_error: str | None = None,
    ) -> bool:
        """Update strategy health metrics.

        Args:
            strategy_id: Strategy ID
            health_score: New health score (0-1)
            signal_count: Signal count increment
            hit_count: Hit count increment
            error_count: Error count increment
            last_error: Last error message

        Returns:
            True if updated
        """
        with self._lock:
            old_state = self._states.get(strategy_id)
            if old_state is None:
                return False

            new_state = StrategyState(
                strategy_id=old_state.strategy_id,
                name=old_state.name,
                status=old_state.status,
                health_score=max(0.0, min(1.0, health_score)),
                signal_count=(
                    old_state.signal_count + (signal_count or 0)
                    if signal_count
                    else old_state.signal_count
                ),
                hit_count=(
                    old_state.hit_count + (hit_count or 0)
                    if hit_count
                    else old_state.hit_count
                ),
                error_count=(
                    old_state.error_count + (error_count or 0)
                    if error_count
                    else old_state.error_count
                ),
                last_signal_time=time.time() if signal_count else old_state.last_signal_time,
                last_error=last_error if last_error is not None else old_state.last_error,
                metadata=old_state.metadata,
            )
            self._states[strategy_id] = new_state

        event = RegistryEvent(
            event_type=RegistryEventType.HEALTH_UPDATED,
            strategy_id=strategy_id,
            old_state=old_state,
            new_state=new_state,
        )
        self._notify_event(event)

        return True

    def record_signal(self, strategy_id: str, hit: bool = False) -> bool:
        """Record signal generation.

        Args:
            strategy_id: Strategy ID
            hit: Whether signal was successful

        Returns:
            True if recorded
        """
        with self._lock:
            old_state = self._states.get(strategy_id)
            if old_state is None:
                return False

            new_state = StrategyState(
                strategy_id=old_state.strategy_id,
                name=old_state.name,
                status=old_state.status,
                health_score=old_state.health_score,
                signal_count=old_state.signal_count + 1,
                hit_count=old_state.hit_count + (1 if hit else 0),
                error_count=old_state.error_count,
                last_signal_time=time.time(),
                last_error=old_state.last_error,
                metadata=old_state.metadata,
            )
            self._states[strategy_id] = new_state

        return True

    def record_error(self, strategy_id: str, error_message: str) -> bool:
        """Record strategy error.

        Args:
            strategy_id: Strategy ID
            error_message: Error message

        Returns:
            True if recorded
        """
        with self._lock:
            old_state = self._states.get(strategy_id)
            if old_state is None:
                return False

            new_state = StrategyState(
                strategy_id=old_state.strategy_id,
                name=old_state.name,
                status=old_state.status,
                health_score=max(0.0, old_state.health_score - 0.1),
                signal_count=old_state.signal_count,
                hit_count=old_state.hit_count,
                error_count=old_state.error_count + 1,
                last_signal_time=old_state.last_signal_time,
                last_error=error_message,
                metadata=old_state.metadata,
            )
            self._states[strategy_id] = new_state

        return True

    def get_all_states(self) -> dict[str, StrategyState]:
        """Get all strategy states.

        Returns:
            Dictionary of strategy states
        """
        with self._lock:
            return dict(self._states)

    def get_active_strategies(self) -> list[str]:
        """Get active strategy IDs.

        Returns:
            List of active strategy IDs
        """
        with self._lock:
            return [
                sid
                for sid, state in self._states.items()
                if state.status == StrategyStatus.ACTIVE
            ]

    def get_strategies_by_tag(self, tag: str) -> list[str]:
        """Get strategies with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of strategy IDs
        """
        with self._lock:
            return [
                sid
                for sid, meta in self._metadata.items()
                if tag in meta.tags
            ]

    def register_callback(
        self,
        callback: Callable[[RegistryEvent], None],
    ) -> None:
        """Register event callback.

        Args:
            callback: Callback function
        """
        with self._lock:
            self._event_callbacks.append(callback)

    def unregister_callback(
        self,
        callback: Callable[[RegistryEvent], None],
    ) -> None:
        """Unregister event callback.

        Args:
            callback: Callback function
        """
        with self._lock:
            if callback in self._event_callbacks:
                self._event_callbacks.remove(callback)

    def _notify_event(self, event: RegistryEvent) -> None:
        """Notify all callbacks of an event."""
        with self._lock:
            callbacks = list(self._event_callbacks)

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Ignore callback errors

    def _log_audit(
        self,
        event_type: AuditEventType,
        strategy_id: str = "",
        action: str = "",
        result: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log audit entry (M3)."""
        if self._audit_logger is None:
            return

        entry = AuditEntry(
            entry_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            timestamp=time.time(),
            strategy_id=strategy_id,
            action=action,
            result=result,
            details=details or {},
        )

        try:
            self._audit_logger(entry)
        except Exception:
            pass

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Statistics dictionary
        """
        with self._lock:
            active = sum(
                1
                for state in self._states.values()
                if state.status == StrategyStatus.ACTIVE
            )
            healthy = sum(1 for state in self._states.values() if state.is_healthy)

            return {
                "total_strategies": len(self._metadata),
                "active_strategies": active,
                "healthy_strategies": healthy,
                "register_count": self._register_count,
                "unregister_count": self._unregister_count,
                "callback_count": len(self._event_callbacks),
            }

    def reset(self) -> None:
        """Reset registry (for testing)."""
        with self._lock:
            self._metadata.clear()
            self._states.clear()
            self._weights.clear()
            self._dynamic_weights.clear()
            self._register_count = 0
            self._unregister_count = 0


__all__ = [
    "RegistryEventType",
    "RegistryEvent",
    "StrategyMetadata",
    "StrategyRegistry",
]
