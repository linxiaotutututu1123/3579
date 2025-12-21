"""Metrics Collector (Military-Grade v3.0).

Provides metrics collection and export functionality.

Features:
- Counter, Gauge, Histogram metrics
- Labels support
- Prometheus-compatible export
- Time series storage

Example:
    collector = MetricsCollector()
    collector.increment("orders_total")
    collector.set("active_positions", 5)
    collector.observe("order_latency_ms", 12.5)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricType(Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricValue:
    """Single metric value.

    Attributes:
        name: Metric name
        value: Current value
        metric_type: Type of metric
        labels: Metric labels
        timestamp: Value timestamp
    """

    name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
        }


@dataclass
class HistogramBucket:
    """Histogram bucket.

    Attributes:
        le: Upper bound (less than or equal)
        count: Number of observations in bucket
    """

    le: float
    count: int


class MetricsCollector:
    """Metrics collector with Prometheus-compatible interface."""

    # Default histogram buckets
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, prefix: str = "") -> None:
        """Initialize metrics collector.

        Args:
            prefix: Metric name prefix
        """
        self._prefix = prefix
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._histogram_buckets: dict[str, tuple[float, ...]] = {}
        self._labels: dict[str, dict[str, str]] = {}
        self._timestamps: dict[str, float] = {}

    def _full_name(self, name: str) -> str:
        """Get full metric name with prefix.

        Args:
            name: Base metric name

        Returns:
            Full metric name
        """
        return f"{self._prefix}{name}" if self._prefix else name

    def increment(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to add (must be positive)
            labels: Optional labels
        """
        if value < 0:
            raise ValueError("Counter can only be incremented")

        full_name = self._full_name(name)
        self._counters[full_name] = self._counters.get(full_name, 0.0) + value
        self._timestamps[full_name] = time.time()
        if labels:
            self._labels[full_name] = labels

    def set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value.

        Args:
            name: Metric name
            value: Value to set
            labels: Optional labels
        """
        full_name = self._full_name(name)
        self._gauges[full_name] = value
        self._timestamps[full_name] = time.time()
        if labels:
            self._labels[full_name] = labels

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        """Observe a histogram value.

        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels
            buckets: Optional custom buckets
        """
        full_name = self._full_name(name)

        if full_name not in self._histograms:
            self._histograms[full_name] = []
            self._histogram_buckets[full_name] = buckets or self.DEFAULT_BUCKETS

        self._histograms[full_name].append(value)
        self._timestamps[full_name] = time.time()
        if labels:
            self._labels[full_name] = labels

    def get_counter(self, name: str) -> float:
        """Get counter value.

        Args:
            name: Metric name

        Returns:
            Counter value
        """
        return self._counters.get(self._full_name(name), 0.0)

    def get_gauge(self, name: str) -> float:
        """Get gauge value.

        Args:
            name: Metric name

        Returns:
            Gauge value
        """
        return self._gauges.get(self._full_name(name), 0.0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get histogram statistics.

        Args:
            name: Metric name

        Returns:
            Dictionary with count, sum, avg, min, max
        """
        full_name = self._full_name(name)
        values = self._histograms.get(full_name, [])

        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_all_metrics(self) -> list[MetricValue]:
        """Get all metrics as MetricValue list.

        Returns:
            List of all metrics
        """
        metrics: list[MetricValue] = []

        # Counters
        for name, value in self._counters.items():
            metrics.append(
                MetricValue(
                    name=name,
                    value=value,
                    metric_type=MetricType.COUNTER,
                    labels=self._labels.get(name, {}),
                    timestamp=self._timestamps.get(name, time.time()),
                )
            )

        # Gauges
        for name, value in self._gauges.items():
            metrics.append(
                MetricValue(
                    name=name,
                    value=value,
                    metric_type=MetricType.GAUGE,
                    labels=self._labels.get(name, {}),
                    timestamp=self._timestamps.get(name, time.time()),
                )
            )

        # Histograms (as gauge of count)
        for name in self._histograms:
            stats = self.get_histogram_stats(name.replace(self._prefix, ""))
            metrics.append(
                MetricValue(
                    name=f"{name}_count",
                    value=float(stats["count"]),
                    metric_type=MetricType.GAUGE,
                    labels=self._labels.get(name, {}),
                    timestamp=self._timestamps.get(name, time.time()),
                )
            )

        return metrics

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._labels.clear()
        self._timestamps.clear()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines: list[str] = []

        # Counters
        for name, value in self._counters.items():
            labels = self._labels.get(name, {})
            label_str = self._format_labels(labels)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{label_str} {value}")

        # Gauges
        for name, value in self._gauges.items():
            labels = self._labels.get(name, {})
            label_str = self._format_labels(labels)
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name}{label_str} {value}")

        # Histograms
        for name, values in self._histograms.items():
            buckets = self._histogram_buckets.get(name, self.DEFAULT_BUCKETS)
            labels = self._labels.get(name, {})
            label_str = self._format_labels(labels)

            lines.append(f"# TYPE {name} histogram")

            # Bucket counts
            for bucket in buckets:
                count = sum(1 for v in values if v <= bucket)
                bucket_labels = {**labels, "le": str(bucket)}
                bucket_label_str = self._format_labels(bucket_labels)
                lines.append(f"{name}_bucket{bucket_label_str} {count}")

            # +Inf bucket
            inf_labels = {**labels, "le": "+Inf"}
            inf_label_str = self._format_labels(inf_labels)
            lines.append(f"{name}_bucket{inf_label_str} {len(values)}")

            # Sum and count
            lines.append(f"{name}_sum{label_str} {sum(values)}")
            lines.append(f"{name}_count{label_str} {len(values)}")

        return "\n".join(lines)

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus output.

        Args:
            labels: Label dictionary

        Returns:
            Formatted label string
        """
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(pairs) + "}"
