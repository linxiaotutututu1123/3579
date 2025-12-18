"""监控模块 (军规级 v3.0).

本模块提供系统监控和健康检查功能，
参照 V3PRO_UPGRADE_PLAN 扩展模块规划 (第24章)。

组件:
- HealthChecker: 系统健康监控
- MetricsCollector: 指标收集和导出

示例:
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
