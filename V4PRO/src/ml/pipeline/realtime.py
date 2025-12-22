"""实时数据管道 (军规级 v4.0).

V4PRO Platform Component - Phase 6.1.1 ML数据管道实时处理
V4 SPEC: SS30 数据管道设计
V4 Scenarios:
- ML.PIPELINE.REALTIME: 实时流式数据处理
- ML.PIPELINE.CIRCUIT_BREAKER: 熔断保护机制
- ML.PIPELINE.AUDIT_TRAIL: 审计追踪

军规覆盖:
- M3: 完整审计日志 - 每次操作记录审计轨迹
- M6: 熔断保护机制 - 连续失败触发熔断保护
- M33: 知识沉淀机制 - 处理模式沉淀为可复用知识

功能特性:
- 流式处理，低延迟 (<10ms P99)
- 环形缓冲区
- 熔断保护 (M6)
- 审计追踪 (M3)

示例:
    >>> from src.ml.pipeline.realtime import RealtimePipeline
    >>> from src.ml.pipeline.base import PipelineConfig, PipelineMode, DataSource
    >>> config = PipelineConfig(
    ...     mode=PipelineMode.REALTIME,
    ...     sources=[DataSource.MARKET],
    ...     buffer_size=10000,
    ... )
    >>> pipeline = RealtimePipeline(config)
    >>> pipeline.start()
    >>> result = pipeline.ingest({"price": 100.5, "volume": 1000})
    >>> for item in pipeline.process_stream():
    ...     print(item)
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from src.ml.pipeline.base import (
    DataPipeline,
    PipelineConfig,
    PipelineMetrics,
    PipelineMode,
    ProcessingStage,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


# ============================================================
# 枚举定义
# ============================================================


class CircuitState(Enum):
    """熔断器状态枚举 (M6).

    定义熔断器的三种状态。

    属性:
        CLOSED: 正常状态，允许请求通过
        OPEN: 熔断状态，拒绝所有请求
        HALF_OPEN: 半开状态，允许少量请求探测恢复
    """

    CLOSED = "CLOSED"  # 正常状态
    OPEN = "OPEN"  # 熔断状态
    HALF_OPEN = "HALF_OPEN"  # 半开状态


class AuditEventType(Enum):
    """审计事件类型枚举 (M3).

    定义审计日志的事件类型。

    属性:
        INGEST: 数据摄取事件
        PROCESS: 数据处理事件
        CIRCUIT_OPEN: 熔断器打开事件
        CIRCUIT_CLOSE: 熔断器关闭事件
        BUFFER_OVERFLOW: 缓冲区溢出事件
        LATENCY_VIOLATION: 延迟违规事件
        ERROR: 错误事件
    """

    INGEST = "INGEST"
    PROCESS = "PROCESS"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    CIRCUIT_CLOSE = "CIRCUIT_CLOSE"
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"
    LATENCY_VIOLATION = "LATENCY_VIOLATION"
    ERROR = "ERROR"


# ============================================================
# 数据类定义
# ============================================================


@dataclass
class BufferedItem:
    """缓冲区数据项.

    Attributes:
        data: 原始数据
        timestamp: 入队时间戳
        correlation_id: 关联ID
        sequence_id: 序列号
        metadata: 元数据
    """

    data: Any
    timestamp: float
    correlation_id: str
    sequence_id: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerState:
    """熔断器状态数据类 (M6).

    Attributes:
        state: 当前熔断状态
        failure_count: 连续失败次数
        last_failure_time: 最后失败时间
        last_success_time: 最后成功时间
        open_time: 熔断打开时间
        half_open_attempts: 半开状态尝试次数
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    open_time: float = 0.0
    half_open_attempts: int = 0

    def reset(self) -> None:
        """重置熔断器状态."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
        self.open_time = 0.0
        self.half_open_attempts = 0


@dataclass
class LatencyTracker:
    """延迟追踪器.

    Attributes:
        samples: 延迟样本列表
        max_samples: 最大样本数
        p99_threshold_ms: P99延迟阈值
    """

    samples: list[float] = field(default_factory=list)
    max_samples: int = 1000
    p99_threshold_ms: float = 10.0

    def add_sample(self, latency_ms: float) -> None:
        """添加延迟样本.

        Args:
            latency_ms: 延迟毫秒数
        """
        self.samples.append(latency_ms)
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples :]

    @property
    def p99(self) -> float:
        """计算P99延迟."""
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def avg(self) -> float:
        """计算平均延迟."""
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    @property
    def max(self) -> float:
        """获取最大延迟."""
        if not self.samples:
            return 0.0
        return max(self.samples)

    @property
    def min(self) -> float:
        """获取最小延迟."""
        if not self.samples:
            return 0.0
        return min(self.samples)

    def is_violation(self) -> bool:
        """检查是否存在延迟违规."""
        return self.p99 > self.p99_threshold_ms

    def reset(self) -> None:
        """重置追踪器."""
        self.samples.clear()


# ============================================================
# 实时数据管道实现
# ============================================================


class RealtimePipeline(DataPipeline):
    """实时数据管道 (军规 M3/M6/M33).

    V4 Scenario: ML.PIPELINE.REALTIME

    特性:
    - 流式处理，低延迟 (<10ms P99)
    - 环形缓冲区
    - 熔断保护 (M6)
    - 审计追踪 (M3)

    军规覆盖:
    - M3: 每次操作记录审计轨迹
    - M6: 连续失败触发熔断保护
    - M33: 处理模式沉淀为可复用知识

    示例:
        >>> pipeline = RealtimePipeline(config)
        >>> pipeline.start()
        >>> result = pipeline.ingest(data)
        >>> for item in pipeline.process_stream():
        ...     process(item)
    """

    # 类常量
    DEFAULT_BUFFER_SIZE: ClassVar[int] = 10000
    MAX_LATENCY_MS: ClassVar[float] = 10.0
    CIRCUIT_BREAKER_THRESHOLD: ClassVar[int] = 100  # 连续失败次数
    CIRCUIT_RECOVERY_TIME_S: ClassVar[float] = 30.0  # 熔断恢复时间
    HALF_OPEN_MAX_ATTEMPTS: ClassVar[int] = 3  # 半开状态最大尝试次数

    def __init__(
        self,
        config: PipelineConfig,
        *,
        on_circuit_open: Callable[[], None] | None = None,
        on_circuit_close: Callable[[], None] | None = None,
    ) -> None:
        """初始化实时管道.

        Args:
            config: 管道配置
            on_circuit_open: 熔断打开回调
            on_circuit_close: 熔断关闭回调
        """
        super().__init__(config)

        # 验证模式
        if config.mode != PipelineMode.REALTIME:
            msg = f"RealtimePipeline仅支持REALTIME模式, 当前模式: {config.mode.value}"
            raise ValueError(msg)

        # 环形缓冲区
        buffer_size = config.buffer_size or self.DEFAULT_BUFFER_SIZE
        self._buffer: deque[BufferedItem] = deque(maxlen=buffer_size)
        self._buffer_lock = threading.Lock()

        # 序列号生成
        self._sequence_counter = 0
        self._sequence_lock = threading.Lock()

        # 熔断器状态 (M6)
        self._circuit_state = CircuitBreakerState()
        self._circuit_lock = threading.Lock()
        self._on_circuit_open = on_circuit_open
        self._on_circuit_close = on_circuit_close

        # 延迟追踪
        self._latency_tracker = LatencyTracker(p99_threshold_ms=self.MAX_LATENCY_MS)

        # 审计日志 (M3)
        self._audit_log: list[dict[str, Any]] = []
        self._audit_lock = threading.Lock()

        # 处理统计
        self._processed_count = 0
        self._dropped_count = 0
        self._error_count = 0

    # ============================================================
    # 核心接口实现
    # ============================================================

    def ingest(self, data: Any) -> Any:
        """摄取数据到缓冲区.

        V4 Scenario: ML.PIPELINE.INGEST

        Args:
            data: 输入数据

        Returns:
            处理结果（BufferedItem或None表示被丢弃）

        Raises:
            RuntimeError: 熔断器打开时抛出
        """
        start_time = time.time()

        # 检查熔断状态 (M6)
        if not self._check_circuit_breaker():
            self._record_audit(
                AuditEventType.ERROR,
                {
                    "reason": "circuit_open",
                    "state": self._circuit_state.state.value,
                    "failure_count": self._circuit_state.failure_count,
                },
            )
            msg = "熔断器已打开，拒绝数据摄取"
            raise RuntimeError(msg)

        # 生成序列号
        with self._sequence_lock:
            self._sequence_counter += 1
            seq_id = self._sequence_counter

        # 创建缓冲项
        correlation_id = f"rt-{seq_id}-{int(start_time * 1000)}"
        item = BufferedItem(
            data=data,
            timestamp=start_time,
            correlation_id=correlation_id,
            sequence_id=seq_id,
            metadata={
                "source": "realtime",
                "ingest_time": datetime.now().isoformat(),
            },
        )

        # 添加到缓冲区
        with self._buffer_lock:
            if self._buffer.maxlen is not None and len(self._buffer) >= self._buffer.maxlen:
                # 缓冲区已满，丢弃最旧的数据
                self._dropped_count += 1
                self._record_audit(
                    AuditEventType.BUFFER_OVERFLOW,
                    {
                        "buffer_size": len(self._buffer),
                        "max_size": self._buffer.maxlen,
                        "dropped_seq_id": seq_id,
                    },
                )

            self._buffer.append(item)

        # 计算延迟
        latency_ms = (time.time() - start_time) * 1000
        self._latency_tracker.add_sample(latency_ms)

        # 更新指标
        self._metrics.records_processed += 1
        self._metrics.latency_ms = self._latency_tracker.avg

        # 检查延迟违规
        if latency_ms > self.MAX_LATENCY_MS:
            self._record_audit(
                AuditEventType.LATENCY_VIOLATION,
                {
                    "latency_ms": latency_ms,
                    "threshold_ms": self.MAX_LATENCY_MS,
                    "seq_id": seq_id,
                },
            )

        # 记录审计 (M3)
        self._record_audit(
            AuditEventType.INGEST,
            {
                "seq_id": seq_id,
                "correlation_id": correlation_id,
                "latency_ms": round(latency_ms, 3),
                "buffer_size": len(self._buffer),
            },
        )

        # 记录成功，重置熔断计数
        self._record_success()

        return item

    def validate(self, data: Any) -> bool:
        """验证数据有效性.

        Args:
            data: 待验证数据

        Returns:
            验证是否通过
        """
        if data is None:
            return False

        if isinstance(data, BufferedItem):
            return data.data is not None

        return True

    def transform(self, data: Any) -> Any:
        """转换数据.

        Args:
            data: 待转换数据

        Returns:
            转换后的数据
        """
        if isinstance(data, BufferedItem):
            # 添加转换时间戳
            data.metadata["transform_time"] = datetime.now().isoformat()
            return data

        return data

    def process(self, data: Any) -> Any:
        """处理单条数据.

        完整的处理流程：摄取 -> 验证 -> 转换 -> 输出。

        Args:
            data: 输入数据

        Returns:
            处理结果
        """
        start_time = time.time()

        try:
            # 摄取阶段
            self.update_stage(ProcessingStage.INGEST)
            item = self.ingest(data)

            # 验证阶段
            self.update_stage(ProcessingStage.VALIDATE)
            if not self.validate(item):
                self._record_failure("validation_failed")
                return None

            # 转换阶段
            self.update_stage(ProcessingStage.TRANSFORM)
            result = self.transform(item)

            # 输出阶段
            self.update_stage(ProcessingStage.OUTPUT)

            # 记录处理时间
            latency_ms = (time.time() - start_time) * 1000
            self._record_audit(
                AuditEventType.PROCESS,
                {
                    "seq_id": item.sequence_id,
                    "correlation_id": item.correlation_id,
                    "total_latency_ms": round(latency_ms, 3),
                },
            )

            self._processed_count += 1
            return result

        except Exception as e:
            self._record_failure(str(e))
            self._record_audit(
                AuditEventType.ERROR,
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

    def process_stream(self) -> Generator[Any, None, None]:
        """流式处理生成器.

        V4 Scenario: ML.PIPELINE.REALTIME

        从缓冲区持续获取数据并处理。

        Yields:
            处理后的数据项
        """
        while self._is_running or len(self._buffer) > 0:
            item = self._pop_from_buffer()

            if item is None:
                # 缓冲区为空，短暂等待
                time.sleep(0.001)  # 1ms
                continue

            start_time = time.time()

            try:
                # 检查熔断状态
                if not self._check_circuit_breaker():
                    self._record_audit(
                        AuditEventType.ERROR,
                        {
                            "reason": "circuit_open_during_stream",
                            "seq_id": item.sequence_id,
                        },
                    )
                    # 熔断时丢弃数据
                    self._dropped_count += 1
                    continue

                # 验证
                if not self.validate(item):
                    self._record_failure("stream_validation_failed")
                    continue

                # 转换
                result = self.transform(item)

                # 计算延迟
                latency_ms = (time.time() - start_time) * 1000
                self._latency_tracker.add_sample(latency_ms)

                # 记录审计
                self._record_audit(
                    AuditEventType.PROCESS,
                    {
                        "seq_id": item.sequence_id,
                        "stream_latency_ms": round(latency_ms, 3),
                        "queue_latency_ms": round(
                            (start_time - item.timestamp) * 1000, 3
                        ),
                    },
                )

                self._record_success()
                self._processed_count += 1

                yield result

            except Exception as e:
                self._record_failure(str(e))
                self._record_audit(
                    AuditEventType.ERROR,
                    {
                        "seq_id": item.sequence_id,
                        "error": str(e),
                    },
                )

    def get_metrics(self) -> PipelineMetrics:
        """获取管道运行指标.

        Returns:
            管道指标对象
        """
        # 更新指标
        self._metrics.records_processed = self._processed_count
        self._metrics.records_failed = self._error_count
        self._metrics.latency_ms = self._latency_tracker.avg

        # 计算吞吐量
        if self._metrics.start_time:
            try:
                start = datetime.fromisoformat(self._metrics.start_time)
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed > 0:
                    self._metrics.throughput_per_sec = self._processed_count / elapsed
            except (ValueError, TypeError):
                pass

        return self._metrics

    # ============================================================
    # 熔断器实现 (M6)
    # ============================================================

    def _check_circuit_breaker(self) -> bool:
        """检查熔断状态 (M6).

        根据熔断器状态决定是否允许请求通过。

        Returns:
            是否允许请求通过
        """
        with self._circuit_lock:
            current_time = time.time()

            if self._circuit_state.state == CircuitState.CLOSED:
                # 正常状态，允许通过
                return True

            elif self._circuit_state.state == CircuitState.OPEN:
                # 检查是否可以进入半开状态
                elapsed = current_time - self._circuit_state.open_time
                if elapsed >= self.CIRCUIT_RECOVERY_TIME_S:
                    self._circuit_state.state = CircuitState.HALF_OPEN
                    self._circuit_state.half_open_attempts = 0
                    self._record_audit(
                        AuditEventType.CIRCUIT_CLOSE,
                        {
                            "reason": "entering_half_open",
                            "elapsed_seconds": elapsed,
                        },
                    )
                    return True
                return False

            elif self._circuit_state.state == CircuitState.HALF_OPEN:
                # 半开状态，允许有限请求通过
                if self._circuit_state.half_open_attempts < self.HALF_OPEN_MAX_ATTEMPTS:
                    self._circuit_state.half_open_attempts += 1
                    return True
                return False

            return False

    def _record_success(self) -> None:
        """记录成功处理."""
        with self._circuit_lock:
            self._circuit_state.last_success_time = time.time()
            self._circuit_state.failure_count = 0

            if self._circuit_state.state == CircuitState.HALF_OPEN:
                # 半开状态下成功，完全关闭熔断器
                self._circuit_state.state = CircuitState.CLOSED
                self._circuit_state.reset()
                self._record_audit(
                    AuditEventType.CIRCUIT_CLOSE,
                    {"reason": "half_open_success"},
                )
                if self._on_circuit_close:
                    self._on_circuit_close()

    def _record_failure(self, reason: str) -> None:
        """记录处理失败.

        Args:
            reason: 失败原因
        """
        with self._circuit_lock:
            self._circuit_state.failure_count += 1
            self._circuit_state.last_failure_time = time.time()
            self._error_count += 1

            # 检查是否需要打开熔断器
            if self._circuit_state.failure_count >= self.CIRCUIT_BREAKER_THRESHOLD:
                self._open_circuit(reason)
            elif self._circuit_state.state == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新打开熔断器
                self._open_circuit(f"half_open_failure: {reason}")

    def _open_circuit(self, reason: str) -> None:
        """打开熔断器.

        Args:
            reason: 打开原因
        """
        self._circuit_state.state = CircuitState.OPEN
        self._circuit_state.open_time = time.time()

        self._record_audit(
            AuditEventType.CIRCUIT_OPEN,
            {
                "reason": reason,
                "failure_count": self._circuit_state.failure_count,
                "recovery_time_s": self.CIRCUIT_RECOVERY_TIME_S,
            },
        )

        # 知识沉淀 (M33)
        self.record_knowledge(
            category="circuit_breaker",
            content=f"熔断器触发: {reason}",
            context={
                "failure_count": self._circuit_state.failure_count,
                "threshold": self.CIRCUIT_BREAKER_THRESHOLD,
            },
        )

        if self._on_circuit_open:
            self._on_circuit_open()

    def reset_circuit_breaker(self) -> None:
        """手动重置熔断器."""
        with self._circuit_lock:
            self._circuit_state.reset()
            self._record_audit(
                AuditEventType.CIRCUIT_CLOSE,
                {"reason": "manual_reset"},
            )

    # ============================================================
    # 审计日志实现 (M3)
    # ============================================================

    def _record_audit(
        self,
        event_type: AuditEventType,
        data: dict[str, Any],
    ) -> None:
        """记录审计日志 (M3).

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if not self._config.enable_audit:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "pipeline": "realtime",
            "stage": self._current_stage.value,
            **data,
        }

        with self._audit_lock:
            self._audit_log.append(entry)

            # 限制审计日志大小
            max_entries = 10000
            if len(self._audit_log) > max_entries:
                self._audit_log = self._audit_log[-max_entries:]

        # 同步到指标中的审计日志
        self._metrics.add_audit_entry(entry)

    def get_audit_log(self) -> list[dict[str, Any]]:
        """获取审计日志 (M3).

        Returns:
            审计日志列表副本
        """
        with self._audit_lock:
            return self._audit_log.copy()

    def clear_audit_log(self) -> None:
        """清空审计日志."""
        with self._audit_lock:
            self._audit_log.clear()

    # ============================================================
    # 缓冲区操作
    # ============================================================

    def _pop_from_buffer(self) -> BufferedItem | None:
        """从缓冲区弹出数据.

        Returns:
            缓冲区数据项或None
        """
        with self._buffer_lock:
            if self._buffer:
                return self._buffer.popleft()
            return None

    def get_buffer_size(self) -> int:
        """获取当前缓冲区大小.

        Returns:
            缓冲区中的数据项数量
        """
        with self._buffer_lock:
            return len(self._buffer)

    def get_buffer_capacity(self) -> int:
        """获取缓冲区容量.

        Returns:
            缓冲区最大容量
        """
        return self._buffer.maxlen or self.DEFAULT_BUFFER_SIZE

    def clear_buffer(self) -> int:
        """清空缓冲区.

        Returns:
            被清空的数据项数量
        """
        with self._buffer_lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    # ============================================================
    # 状态与统计
    # ============================================================

    def get_status(self) -> dict[str, Any]:
        """获取管道状态.

        Returns:
            状态字典
        """
        return {
            "running": self._is_running,
            "mode": self._config.mode.value,
            "buffer": {
                "size": self.get_buffer_size(),
                "capacity": self.get_buffer_capacity(),
                "usage_percent": round(
                    self.get_buffer_size() / self.get_buffer_capacity() * 100, 2
                ),
            },
            "circuit_breaker": {
                "state": self._circuit_state.state.value,
                "failure_count": self._circuit_state.failure_count,
                "threshold": self.CIRCUIT_BREAKER_THRESHOLD,
            },
            "latency": {
                "p99_ms": round(self._latency_tracker.p99, 3),
                "avg_ms": round(self._latency_tracker.avg, 3),
                "max_ms": round(self._latency_tracker.max, 3),
                "threshold_ms": self.MAX_LATENCY_MS,
                "is_violation": self._latency_tracker.is_violation(),
            },
            "counters": {
                "processed": self._processed_count,
                "dropped": self._dropped_count,
                "errors": self._error_count,
                "sequence": self._sequence_counter,
            },
            "audit_log_count": len(self._audit_log),
        }

    def get_latency_stats(self) -> dict[str, float]:
        """获取延迟统计.

        Returns:
            延迟统计字典
        """
        return {
            "p99_ms": round(self._latency_tracker.p99, 3),
            "avg_ms": round(self._latency_tracker.avg, 3),
            "max_ms": round(self._latency_tracker.max, 3),
            "min_ms": round(self._latency_tracker.min, 3),
            "sample_count": len(self._latency_tracker.samples),
            "threshold_ms": self.MAX_LATENCY_MS,
            "is_compliant": not self._latency_tracker.is_violation(),
        }

    @property
    def is_circuit_open(self) -> bool:
        """熔断器是否打开."""
        return self._circuit_state.state == CircuitState.OPEN

    @property
    def circuit_state(self) -> CircuitState:
        """获取熔断器状态."""
        return self._circuit_state.state

    @property
    def processed_count(self) -> int:
        """获取已处理数量."""
        return self._processed_count

    @property
    def dropped_count(self) -> int:
        """获取丢弃数量."""
        return self._dropped_count

    @property
    def error_count(self) -> int:
        """获取错误数量."""
        return self._error_count

    # ============================================================
    # 生命周期管理
    # ============================================================

    def start(self) -> None:
        """启动管道."""
        super().start()
        self._record_audit(
            AuditEventType.PROCESS,
            {
                "action": "pipeline_start",
                "buffer_capacity": self.get_buffer_capacity(),
                "circuit_threshold": self.CIRCUIT_BREAKER_THRESHOLD,
                "max_latency_ms": self.MAX_LATENCY_MS,
            },
        )

    def stop(self) -> None:
        """停止管道."""
        self._record_audit(
            AuditEventType.PROCESS,
            {
                "action": "pipeline_stop",
                "processed_count": self._processed_count,
                "dropped_count": self._dropped_count,
                "error_count": self._error_count,
                "final_buffer_size": self.get_buffer_size(),
            },
        )
        super().stop()

    def reset(self) -> None:
        """重置管道状态."""
        super().reset()
        self.clear_buffer()
        self.reset_circuit_breaker()
        self._latency_tracker.reset()
        self.clear_audit_log()
        self._processed_count = 0
        self._dropped_count = 0
        self._error_count = 0
        with self._sequence_lock:
            self._sequence_counter = 0


# ============================================================
# 便捷函数
# ============================================================


def create_realtime_pipeline(
    buffer_size: int = RealtimePipeline.DEFAULT_BUFFER_SIZE,
    enable_audit: bool = True,
    enable_knowledge: bool = True,
    on_circuit_open: Callable[[], None] | None = None,
    on_circuit_close: Callable[[], None] | None = None,
) -> RealtimePipeline:
    """创建实时管道.

    Args:
        buffer_size: 缓冲区大小
        enable_audit: 是否启用审计日志 (M3)
        enable_knowledge: 是否启用知识沉淀 (M33)
        on_circuit_open: 熔断打开回调
        on_circuit_close: 熔断关闭回调

    Returns:
        RealtimePipeline实例

    示例:
        >>> pipeline = create_realtime_pipeline(
        ...     buffer_size=5000,
        ...     on_circuit_open=lambda: print("Circuit opened!"),
        ... )
    """
    from src.ml.pipeline.base import DataSource

    config = PipelineConfig(
        mode=PipelineMode.REALTIME,
        sources=[DataSource.MARKET],
        buffer_size=buffer_size,
        enable_audit=enable_audit,
        enable_knowledge=enable_knowledge,
    )

    return RealtimePipeline(
        config,
        on_circuit_open=on_circuit_open,
        on_circuit_close=on_circuit_close,
    )
