"""指标收集器模块 - 应用程序度量收集和导出.

提供应用程序度量收集功能:
- Counter: 计数器(只增不减)
- Gauge: 瞬时值(可增可减)
- Histogram: 直方图(分布统计)

使用示例:
    >>> collector = MetricsCollector("my-service")
    >>> collector.counter("requests_total", 1, {"method": "GET"})
    >>> collector.gauge("active_connections", 42)
    >>> collector.histogram("request_duration_ms", 150.5)
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, TypeAlias

# =============================================================================
# 类型别名
# =============================================================================

MetricName: TypeAlias = str
"""指标名称."""

Labels: TypeAlias = dict[str, str]
"""标签字典."""


# =============================================================================
# 枚举定义
# =============================================================================


class MetricType(Enum):
    """指标类型枚举.

    支持的指标类型:
    - COUNTER: 计数器, 只增不减
    - GAUGE: 瞬时值, 可增可减
    - HISTOGRAM: 直方图, 记录值分布
    """

    COUNTER = "counter"
    """计数器: 只增不减的累计值"""

    GAUGE = "gauge"
    """瞬时值: 可增可减的当前值"""

    HISTOGRAM = "histogram"
    """直方图: 值的分布统计"""


# =============================================================================
# 指标数据类
# =============================================================================


@dataclass
class MetricPoint:
    """指标数据点.

    表示单个指标测量:
    - name: 指标名称
    - value: 指标值
    - type: 指标类型
    - labels: 标签
    - timestamp: 时间戳
    """

    name: MetricName
    """指标名称"""

    value: float
    """指标值"""

    type: MetricType
    """指标类型"""

    labels: Labels = field(default_factory=dict)
    """标签字典"""

    timestamp: datetime = field(default_factory=datetime.now)
    """时间戳"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典表示.

        Returns:
            包含指标信息的字典
        """
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CounterMetric:
    """计数器指标.

    只能增加的累计计数器:
    - 适用于请求总数、错误总数等
    - 支持按标签分组
    """

    name: MetricName
    """指标名称"""

    description: str = ""
    """指标描述"""

    _values: dict[str, float] = field(default_factory=dict, repr=False)
    """按标签键存储的值"""

    _lock: Lock = field(default_factory=Lock, repr=False)
    """线程锁"""

    def _labels_key(self, labels: Labels | None) -> str:
        """生成标签键.

        Args:
            labels: 标签字典

        Returns:
            标签的字符串表示
        """
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def inc(self, value: float = 1.0, labels: Labels | None = None) -> None:
        """增加计数.

        Args:
            value: 增加的值(必须为正数)
            labels: 标签

        Raises:
            ValueError: 如果value为负数
        """
        if value < 0:
            raise ValueError("计数器增量必须为非负数")

        key = self._labels_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def get(self, labels: Labels | None = None) -> float:
        """获取当前值.

        Args:
            labels: 标签

        Returns:
            当前计数值
        """
        key = self._labels_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def get_all(self) -> dict[str, float]:
        """获取所有值.

        Returns:
            所有标签组合的值
        """
        with self._lock:
            return dict(self._values)

    def reset(self) -> None:
        """重置所有值."""
        with self._lock:
            self._values.clear()


@dataclass
class GaugeMetric:
    """瞬时值指标.

    可增可减的当前值:
    - 适用于活跃连接数、队列长度等
    - 支持按标签分组
    """

    name: MetricName
    """指标名称"""

    description: str = ""
    """指标描述"""

    _values: dict[str, float] = field(default_factory=dict, repr=False)
    """按标签键存储的值"""

    _lock: Lock = field(default_factory=Lock, repr=False)
    """线程锁"""

    def _labels_key(self, labels: Labels | None) -> str:
        """生成标签键.

        Args:
            labels: 标签字典

        Returns:
            标签的字符串表示
        """
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def set(self, value: float, labels: Labels | None = None) -> None:
        """设置值.

        Args:
            value: 新值
            labels: 标签
        """
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, labels: Labels | None = None) -> None:
        """增加值.

        Args:
            value: 增加的值
            labels: 标签
        """
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def dec(self, value: float = 1.0, labels: Labels | None = None) -> None:
        """减少值.

        Args:
            value: 减少的值
            labels: 标签
        """
        key = self._labels_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - value

    def get(self, labels: Labels | None = None) -> float:
        """获取当前值.

        Args:
            labels: 标签

        Returns:
            当前值
        """
        key = self._labels_key(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def get_all(self) -> dict[str, float]:
        """获取所有值.

        Returns:
            所有标签组合的值
        """
        with self._lock:
            return dict(self._values)

    def reset(self) -> None:
        """重置所有值."""
        with self._lock:
            self._values.clear()


@dataclass
class HistogramMetric:
    """直方图指标.

    记录值的分布统计:
    - 适用于请求延迟、响应大小等
    - 支持按标签分组
    - 提供统计摘要(min, max, mean, p50, p95, p99)
    """

    name: MetricName
    """指标名称"""

    description: str = ""
    """指标描述"""

    buckets: tuple[float, ...] = (
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    )
    """桶边界"""

    _observations: dict[str, list[float]] = field(default_factory=dict, repr=False)
    """观测值列表"""

    _sum: dict[str, float] = field(default_factory=dict, repr=False)
    """总和"""

    _count: dict[str, int] = field(default_factory=dict, repr=False)
    """计数"""

    _lock: Lock = field(default_factory=Lock, repr=False)
    """线程锁"""

    max_observations: int = 10000
    """最大观测值数量(防止内存泄漏)"""

    def _labels_key(self, labels: Labels | None) -> str:
        """生成标签键.

        Args:
            labels: 标签字典

        Returns:
            标签的字符串表示
        """
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def observe(self, value: float, labels: Labels | None = None) -> None:
        """记录观测值.

        Args:
            value: 观测值
            labels: 标签
        """
        key = self._labels_key(labels)
        with self._lock:
            if key not in self._observations:
                self._observations[key] = []
                self._sum[key] = 0.0
                self._count[key] = 0

            self._observations[key].append(value)
            self._sum[key] += value
            self._count[key] += 1

            # 限制观测值数量
            if len(self._observations[key]) > self.max_observations:
                self._observations[key] = self._observations[key][-self.max_observations:]

    def get_summary(self, labels: Labels | None = None) -> dict[str, float]:
        """获取统计摘要.

        Args:
            labels: 标签

        Returns:
            包含统计信息的字典
        """
        key = self._labels_key(labels)
        with self._lock:
            observations = self._observations.get(key, [])
            if not observations:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }

            sorted_obs = sorted(observations)
            count = len(sorted_obs)

            return {
                "count": count,
                "sum": self._sum.get(key, 0.0),
                "min": min(sorted_obs),
                "max": max(sorted_obs),
                "mean": statistics.mean(sorted_obs),
                "p50": self._percentile(sorted_obs, 50),
                "p95": self._percentile(sorted_obs, 95),
                "p99": self._percentile(sorted_obs, 99),
            }

    def _percentile(self, sorted_data: list[float], percentile: float) -> float:
        """计算百分位数.

        Args:
            sorted_data: 已排序的数据
            percentile: 百分位(0-100)

        Returns:
            百分位值
        """
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1]
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def get_bucket_counts(self, labels: Labels | None = None) -> dict[float, int]:
        """获取桶计数.

        Args:
            labels: 标签

        Returns:
            每个桶的计数
        """
        key = self._labels_key(labels)
        with self._lock:
            observations = self._observations.get(key, [])
            bucket_counts: dict[float, int] = {b: 0 for b in self.buckets}
            bucket_counts[float("inf")] = 0

            for value in observations:
                for bucket in self.buckets:
                    if value <= bucket:
                        bucket_counts[bucket] += 1
                        break
                else:
                    bucket_counts[float("inf")] += 1

            return bucket_counts

    def reset(self) -> None:
        """重置所有值."""
        with self._lock:
            self._observations.clear()
            self._sum.clear()
            self._count.clear()


# =============================================================================
# MetricsCollector类
# =============================================================================


class MetricsCollector:
    """指标收集器类.

    统一管理应用程序的度量收集:
    - 创建和管理各类型指标
    - 提供简便的记录方法
    - 支持指标导出

    Attributes:
        service_name: 服务名称
        default_labels: 默认标签

    使用示例:
        >>> collector = MetricsCollector("api-service")
        >>> collector.counter("http_requests_total", 1, {"method": "GET", "path": "/users"})
        >>> collector.gauge("active_users", 150)
        >>> collector.histogram("request_latency_seconds", 0.042)
        >>> print(collector.export())
    """

    def __init__(
        self,
        service_name: str,
        default_labels: Labels | None = None,
    ) -> None:
        """初始化指标收集器.

        Args:
            service_name: 服务名称
            default_labels: 默认标签(会添加到所有指标)
        """
        self.service_name = service_name
        self.default_labels = default_labels or {}
        self._counters: dict[MetricName, CounterMetric] = {}
        self._gauges: dict[MetricName, GaugeMetric] = {}
        self._histograms: dict[MetricName, HistogramMetric] = {}
        self._points: list[MetricPoint] = []
        self._lock = Lock()
        self._max_points = 10000

    def _merge_labels(self, labels: Labels | None) -> Labels:
        """合并标签.

        Args:
            labels: 用户提供的标签

        Returns:
            合并后的标签
        """
        merged = {"service": self.service_name}
        merged.update(self.default_labels)
        if labels:
            merged.update(labels)
        return merged

    def counter(
        self,
        name: MetricName,
        value: float = 1.0,
        labels: Labels | None = None,
        description: str = "",
    ) -> None:
        """记录计数器指标.

        Args:
            name: 指标名称
            value: 增加的值(必须为正数)
            labels: 标签
            description: 指标描述(仅在首次创建时使用)
        """
        merged_labels = self._merge_labels(labels)

        with self._lock:
            if name not in self._counters:
                self._counters[name] = CounterMetric(name=name, description=description)
            self._counters[name].inc(value, merged_labels)

        self._record_point(name, value, MetricType.COUNTER, merged_labels)

    def gauge(
        self,
        name: MetricName,
        value: float,
        labels: Labels | None = None,
        description: str = "",
    ) -> None:
        """记录瞬时值指标.

        Args:
            name: 指标名称
            value: 当前值
            labels: 标签
            description: 指标描述(仅在首次创建时使用)
        """
        merged_labels = self._merge_labels(labels)

        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = GaugeMetric(name=name, description=description)
            self._gauges[name].set(value, merged_labels)

        self._record_point(name, value, MetricType.GAUGE, merged_labels)

    def histogram(
        self,
        name: MetricName,
        value: float,
        labels: Labels | None = None,
        description: str = "",
    ) -> None:
        """记录直方图指标.

        Args:
            name: 指标名称
            value: 观测值
            labels: 标签
            description: 指标描述(仅在首次创建时使用)
        """
        merged_labels = self._merge_labels(labels)

        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = HistogramMetric(name=name, description=description)
            self._histograms[name].observe(value, merged_labels)

        self._record_point(name, value, MetricType.HISTOGRAM, merged_labels)

    def _record_point(
        self,
        name: MetricName,
        value: float,
        metric_type: MetricType,
        labels: Labels,
    ) -> None:
        """记录指标数据点.

        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型
            labels: 标签
        """
        point = MetricPoint(
            name=name,
            value=value,
            type=metric_type,
            labels=labels,
        )
        with self._lock:
            self._points.append(point)
            if len(self._points) > self._max_points:
                self._points = self._points[-self._max_points:]

    def get_counter(self, name: MetricName) -> CounterMetric | None:
        """获取计数器指标.

        Args:
            name: 指标名称

        Returns:
            计数器指标或None
        """
        return self._counters.get(name)

    def get_gauge(self, name: MetricName) -> GaugeMetric | None:
        """获取瞬时值指标.

        Args:
            name: 指标名称

        Returns:
            瞬时值指标或None
        """
        return self._gauges.get(name)

    def get_histogram(self, name: MetricName) -> HistogramMetric | None:
        """获取直方图指标.

        Args:
            name: 指标名称

        Returns:
            直方图指标或None
        """
        return self._histograms.get(name)

    def time(self, name: MetricName, labels: Labels | None = None) -> _Timer:
        """创建计时器上下文管理器.

        用于测量代码块的执行时间:
        >>> with collector.time("operation_duration_seconds"):
        ...     # 执行操作
        ...     pass

        Args:
            name: 指标名称
            labels: 标签

        Returns:
            计时器上下文管理器
        """
        return _Timer(self, name, labels)

    def export(self) -> dict[str, Any]:
        """导出所有指标.

        Returns:
            包含所有指标的字典
        """
        with self._lock:
            result: dict[str, Any] = {
                "service_name": self.service_name,
                "timestamp": datetime.now().isoformat(),
                "counters": {},
                "gauges": {},
                "histograms": {},
            }

            for name, counter in self._counters.items():
                result["counters"][name] = {
                    "description": counter.description,
                    "values": counter.get_all(),
                }

            for name, gauge in self._gauges.items():
                result["gauges"][name] = {
                    "description": gauge.description,
                    "values": gauge.get_all(),
                }

            for name, histogram in self._histograms.items():
                result["histograms"][name] = {
                    "description": histogram.description,
                    "summary": histogram.get_summary(),
                }

            return result

    def get_points(self, limit: int | None = None) -> list[MetricPoint]:
        """获取记录的数据点.

        Args:
            limit: 返回的最大数量

        Returns:
            数据点列表
        """
        with self._lock:
            if limit:
                return list(self._points[-limit:])
            return list(self._points)

    def reset(self) -> None:
        """重置所有指标."""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
            for gauge in self._gauges.values():
                gauge.reset()
            for histogram in self._histograms.values():
                histogram.reset()
            self._points.clear()


# =============================================================================
# 辅助类
# =============================================================================


class _Timer:
    """计时器上下文管理器.

    用于测量代码块的执行时间并记录到直方图.
    """

    def __init__(
        self,
        collector: MetricsCollector,
        name: MetricName,
        labels: Labels | None = None,
    ) -> None:
        """初始化计时器.

        Args:
            collector: 指标收集器
            name: 指标名称
            labels: 标签
        """
        self._collector = collector
        self._name = name
        self._labels = labels
        self._start_time: float = 0.0

    def __enter__(self) -> _Timer:
        """开始计时."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """结束计时并记录."""
        duration = time.perf_counter() - self._start_time
        self._collector.histogram(self._name, duration, self._labels)


# =============================================================================
# 全局指标收集器
# =============================================================================

_global_collector: MetricsCollector | None = None


def get_collector(service_name: str = "default") -> MetricsCollector:
    """获取或创建全局指标收集器.

    Args:
        service_name: 服务名称(仅在创建时使用)

    Returns:
        全局指标收集器实例
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector(service_name)
    return _global_collector


def set_collector(collector: MetricsCollector) -> None:
    """设置全局指标收集器.

    Args:
        collector: 指标收集器实例
    """
    global _global_collector
    _global_collector = collector


def reset_collector() -> None:
    """重置全局指标收集器."""
    global _global_collector
    _global_collector = None


# =============================================================================
# 模块导出
# =============================================================================

__all__ = [
    # 类型别名
    "MetricName",
    "Labels",
    # 枚举
    "MetricType",
    # 数据类
    "MetricPoint",
    "CounterMetric",
    "GaugeMetric",
    "HistogramMetric",
    # 主类
    "MetricsCollector",
    # 全局函数
    "get_collector",
    "set_collector",
    "reset_collector",
]
