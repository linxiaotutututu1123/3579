"""Monitoring Module (Military-Grade v3.0).

This module provides system monitoring and health check functionality
as specified in V3PRO_UPGRADE_PLAN extension modules (Chapter 24).

Components:
- HealthChecker: System health monitoring
- MetricsCollector: Metrics collection and export

Example:
    from src.monitoring import HealthChecker, MetricsCollector

    health = HealthChecker()
    status = health.check_all()

    metrics = MetricsCollector()
    metrics.record("order_count", 100)
"""

from __future__ import annotations

from src.monitoring.health import HealthChecker, HealthStatus
from src.monitoring.metrics import MetricsCollector, MetricValue


__all__ = [
    "HealthChecker",
    "HealthStatus",
    "MetricValue",
    "MetricsCollector",
]
