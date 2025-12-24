"""可观测性模块 - 监控、追踪、日志.

提供应用程序可观测性功能:
- tracer: 分布式追踪
- metrics: 指标收集
- logger: 结构化日志

使用示例:
    >>> from chairman_agents.observability import Tracer, MetricsCollector, StructuredLogger
    >>>
    >>> tracer = Tracer("my-service")
    >>> collector = MetricsCollector("my-service")
    >>> logger = StructuredLogger("my-service")
"""

from __future__ import annotations

# Tracer exports
from chairman_agents.observability.tracer import (
    SpanId,
    TraceId,
    SpanStatus,
    SpanKind,
    SpanEvent,
    Span,
    Tracer,
    get_tracer,
    set_tracer,
    reset_tracer,
)

# Metrics exports
from chairman_agents.observability.metrics import (
    MetricName,
    Labels,
    MetricType,
    MetricPoint,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    MetricsCollector,
    get_collector,
    set_collector,
    reset_collector,
)

# Logger exports
from chairman_agents.observability.logger import (
    LogContext,
    LogLevel,
    LogFormat,
    LogRecord,
    LogHandler,
    StreamHandler,
    FileHandler,
    MemoryHandler,
    StructuredLogger,
    get_logger,
    set_logger,
    reset_logger,
    configure_logging,
)

__all__ = [
    # Tracer
    "SpanId",
    "TraceId",
    "SpanStatus",
    "SpanKind",
    "SpanEvent",
    "Span",
    "Tracer",
    "get_tracer",
    "set_tracer",
    "reset_tracer",
    # Metrics
    "MetricName",
    "Labels",
    "MetricType",
    "MetricPoint",
    "CounterMetric",
    "GaugeMetric",
    "HistogramMetric",
    "MetricsCollector",
    "get_collector",
    "set_collector",
    "reset_collector",
    # Logger
    "LogContext",
    "LogLevel",
    "LogFormat",
    "LogRecord",
    "LogHandler",
    "StreamHandler",
    "FileHandler",
    "MemoryHandler",
    "StructuredLogger",
    "get_logger",
    "set_logger",
    "reset_logger",
    "configure_logging",
]
