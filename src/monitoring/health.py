"""Health Checker (Military-Grade v3.0).

Provides system health monitoring functionality.

Features:
- Component health checks
- Dependency status monitoring
- Health history tracking
- Alerting support

Example:
    checker = HealthChecker()
    checker.register_check("broker", check_broker_connection)
    status = checker.check_all()
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthState(Enum):
    """Health state enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """Health check status.

    Attributes:
        component: Component name
        state: Health state
        message: Status message
        latency_ms: Check latency in milliseconds
        checked_at: Check timestamp
        metadata: Additional metadata
    """

    component: str
    state: HealthState
    message: str = ""
    latency_ms: float = 0.0
    checked_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component": self.component,
            "state": self.state.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "checked_at": self.checked_at,
            "metadata": self.metadata,
        }

    @property
    def is_healthy(self) -> bool:
        """Check if status is healthy."""
        return self.state == HealthState.HEALTHY


# Type alias for health check functions
HealthCheckFn = Callable[[], tuple[bool, str]]


class HealthChecker:
    """System health checker.

    Monitors health of system components through registered checks.
    """

    def __init__(self, check_interval_s: float = 10.0) -> None:
        """Initialize health checker.

        Args:
            check_interval_s: Minimum interval between checks
        """
        self._check_interval_s = check_interval_s
        self._checks: dict[str, HealthCheckFn] = {}
        self._last_status: dict[str, HealthStatus] = {}
        self._history: list[dict[str, HealthStatus]] = []
        self._max_history = 100

    def register_check(self, component: str, check_fn: HealthCheckFn) -> None:
        """Register a health check function.

        Args:
            component: Component name
            check_fn: Function that returns (is_healthy, message)
        """
        self._checks[component] = check_fn

    def unregister_check(self, component: str) -> None:
        """Unregister a health check.

        Args:
            component: Component name
        """
        self._checks.pop(component, None)
        self._last_status.pop(component, None)

    def check(self, component: str) -> HealthStatus:
        """Run health check for a component.

        Args:
            component: Component name

        Returns:
            Health status
        """
        if component not in self._checks:
            return HealthStatus(
                component=component,
                state=HealthState.UNKNOWN,
                message="Check not registered",
            )

        check_fn = self._checks[component]
        start = time.time()

        try:
            is_healthy, message = check_fn()
            latency_ms = (time.time() - start) * 1000

            status = HealthStatus(
                component=component,
                state=HealthState.HEALTHY if is_healthy else HealthState.UNHEALTHY,
                message=message,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            status = HealthStatus(
                component=component,
                state=HealthState.UNHEALTHY,
                message=f"Check failed: {e}",
                latency_ms=latency_ms,
            )

        self._last_status[component] = status
        return status

    def check_all(self) -> dict[str, HealthStatus]:
        """Run all registered health checks.

        Returns:
            Dictionary of component -> status
        """
        results: dict[str, HealthStatus] = {}
        for component in self._checks:
            results[component] = self.check(component)

        # Store in history
        self._history.append(dict(results))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return results

    def get_status(self, component: str) -> HealthStatus | None:
        """Get last status for a component.

        Args:
            component: Component name

        Returns:
            Last health status or None
        """
        return self._last_status.get(component)

    def get_all_status(self) -> dict[str, HealthStatus]:
        """Get all last statuses.

        Returns:
            Dictionary of component -> status
        """
        return dict(self._last_status)

    def is_system_healthy(self) -> bool:
        """Check if overall system is healthy.

        Returns:
            True if all components healthy
        """
        if not self._last_status:
            return False
        return all(s.is_healthy for s in self._last_status.values())

    def get_summary(self) -> dict[str, Any]:
        """Get health summary.

        Returns:
            Summary dictionary
        """
        total = len(self._last_status)
        healthy = sum(1 for s in self._last_status.values() if s.is_healthy)
        unhealthy = total - healthy

        return {
            "total_components": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "system_healthy": self.is_system_healthy(),
            "components": {k: v.to_dict() for k, v in self._last_status.items()},
        }

    @property
    def components(self) -> list[str]:
        """List of registered components."""
        return list(self._checks.keys())
