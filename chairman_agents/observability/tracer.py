"""追踪器模块 - 分布式追踪和Span管理.

提供分布式追踪功能:
- Span数据类: 表示单个追踪跨度
- Tracer类: 管理追踪上下文和Span生命周期
- trace上下文管理器: 简化追踪代码的编写

使用示例:
    >>> tracer = Tracer("my-service")
    >>> with tracer.trace("operation") as span:
    ...     span.set_attribute("key", "value")
    ...     # 执行操作
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import local
from typing import Any, Generator, TypeAlias

# =============================================================================
# 类型别名
# =============================================================================

SpanId: TypeAlias = str
"""Span的唯一标识符."""

TraceId: TypeAlias = str
"""追踪链的唯一标识符."""


# =============================================================================
# 枚举定义
# =============================================================================


class SpanStatus(Enum):
    """Span状态枚举.

    表示Span的执行状态:
    - UNSET: 未设置状态
    - OK: 执行成功
    - ERROR: 执行出错
    """

    UNSET = "unset"
    """未设置状态"""

    OK = "ok"
    """执行成功"""

    ERROR = "error"
    """执行出错"""


class SpanKind(Enum):
    """Span类型枚举.

    表示Span的类型:
    - INTERNAL: 内部操作
    - SERVER: 服务端处理请求
    - CLIENT: 客户端发起请求
    - PRODUCER: 消息生产者
    - CONSUMER: 消息消费者
    """

    INTERNAL = "internal"
    """内部操作"""

    SERVER = "server"
    """服务端处理请求"""

    CLIENT = "client"
    """客户端发起请求"""

    PRODUCER = "producer"
    """消息生产者"""

    CONSUMER = "consumer"
    """消息消费者"""


# =============================================================================
# 辅助函数
# =============================================================================


def _generate_id() -> str:
    """生成唯一标识符.

    Returns:
        16字符的十六进制字符串
    """
    return uuid.uuid4().hex[:16]


def _generate_trace_id() -> str:
    """生成追踪ID.

    Returns:
        32字符的十六进制字符串
    """
    return uuid.uuid4().hex


# =============================================================================
# Span数据类
# =============================================================================


@dataclass
class SpanEvent:
    """Span事件.

    记录Span执行过程中的重要事件:
    - name: 事件名称
    - timestamp: 事件发生时间
    - attributes: 事件属性
    """

    name: str
    """事件名称"""

    timestamp: datetime = field(default_factory=datetime.now)
    """事件发生时间"""

    attributes: dict[str, Any] = field(default_factory=dict)
    """事件属性"""


@dataclass
class Span:
    """追踪跨度数据类.

    表示分布式追踪中的一个操作单元:
    - 标识: trace_id, span_id, parent_span_id
    - 基本信息: name, kind, status
    - 时间: start_time, end_time, duration_ms
    - 属性: attributes (键值对)
    - 事件: events (时间点标记)
    - 异常: exception_info (错误信息)

    Attributes:
        trace_id: 追踪链ID
        span_id: 当前Span ID
        parent_span_id: 父Span ID (如果有)
        name: Span名称
        kind: Span类型
        status: Span状态
        start_time: 开始时间
        end_time: 结束时间
        duration_ms: 持续时间(毫秒)
        attributes: 属性字典
        events: 事件列表
        exception_info: 异常信息
    """

    # 标识信息
    trace_id: TraceId = field(default_factory=_generate_trace_id)
    """追踪链ID"""

    span_id: SpanId = field(default_factory=_generate_id)
    """当前Span ID"""

    parent_span_id: SpanId | None = None
    """父Span ID"""

    # 基本信息
    name: str = ""
    """Span名称"""

    kind: SpanKind = SpanKind.INTERNAL
    """Span类型"""

    status: SpanStatus = SpanStatus.UNSET
    """Span状态"""

    status_message: str = ""
    """状态消息(用于错误描述)"""

    # 时间信息
    start_time: datetime = field(default_factory=datetime.now)
    """开始时间"""

    end_time: datetime | None = None
    """结束时间"""

    duration_ms: float | None = None
    """持续时间(毫秒)"""

    # 属性和事件
    attributes: dict[str, Any] = field(default_factory=dict)
    """属性字典"""

    events: list[SpanEvent] = field(default_factory=list)
    """事件列表"""

    # 异常信息
    exception_info: dict[str, Any] | None = None
    """异常信息"""

    # 内部状态
    _start_time_ns: int = field(default=0, repr=False)
    """开始时间(纳秒, 用于精确计时)"""

    _is_ended: bool = field(default=False, repr=False)
    """是否已结束"""

    def set_attribute(self, key: str, value: Any) -> Span:
        """设置属性.

        Args:
            key: 属性键
            value: 属性值

        Returns:
            返回self以支持链式调用
        """
        self.attributes[key] = value
        return self

    def set_attributes(self, attributes: dict[str, Any]) -> Span:
        """批量设置属性.

        Args:
            attributes: 属性字典

        Returns:
            返回self以支持链式调用
        """
        self.attributes.update(attributes)
        return self

    def add_event(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> Span:
        """添加事件.

        Args:
            name: 事件名称
            attributes: 事件属性
            timestamp: 事件时间(默认为当前时间)

        Returns:
            返回self以支持链式调用
        """
        event = SpanEvent(
            name=name,
            timestamp=timestamp or datetime.now(),
            attributes=attributes or {},
        )
        self.events.append(event)
        return self

    def set_status(self, status: SpanStatus, message: str = "") -> Span:
        """设置状态.

        Args:
            status: 状态枚举值
            message: 状态消息(用于错误描述)

        Returns:
            返回self以支持链式调用
        """
        self.status = status
        self.status_message = message
        return self

    def record_exception(
        self,
        exception: BaseException,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """记录异常.

        Args:
            exception: 异常对象
            attributes: 附加属性

        Returns:
            返回self以支持链式调用
        """
        self.exception_info = {
            "type": type(exception).__name__,
            "message": str(exception),
            "attributes": attributes or {},
        }
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
                **(attributes or {}),
            },
        )
        self.set_status(SpanStatus.ERROR, str(exception))
        return self

    def end(self, end_time: datetime | None = None) -> None:
        """结束Span.

        Args:
            end_time: 结束时间(默认为当前时间)
        """
        if self._is_ended:
            return

        self._is_ended = True
        self.end_time = end_time or datetime.now()

        # 计算持续时间
        if self._start_time_ns > 0:
            end_ns = time.perf_counter_ns()
            self.duration_ms = (end_ns - self._start_time_ns) / 1_000_000
        else:
            # 回退到datetime计算
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000

    @property
    def is_recording(self) -> bool:
        """检查Span是否仍在记录.

        Returns:
            如果Span未结束则返回True
        """
        return not self._is_ended

    def to_dict(self) -> dict[str, Any]:
        """转换为字典表示.

        Returns:
            包含Span所有信息的字典
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
            "exception_info": self.exception_info,
        }


# =============================================================================
# Tracer类
# =============================================================================


class Tracer:
    """追踪器类.

    管理追踪上下文和Span生命周期:
    - 创建和管理Span
    - 维护Span的父子关系
    - 提供上下文管理器简化使用

    Attributes:
        service_name: 服务名称
        spans: 所有已完成的Span列表
        max_spans: 最大保留Span数量

    使用示例:
        >>> tracer = Tracer("order-service")
        >>> with tracer.trace("process_order") as span:
        ...     span.set_attribute("order_id", "12345")
        ...     # 处理订单
        ...     with tracer.trace("validate_order"):
        ...         # 验证订单
        ...         pass
    """

    def __init__(
        self,
        service_name: str,
        max_spans: int = 1000,
    ) -> None:
        """初始化追踪器.

        Args:
            service_name: 服务名称
            max_spans: 最大保留Span数量(防止内存泄漏)
        """
        self.service_name = service_name
        self.max_spans = max_spans
        self._spans: list[Span] = []
        self._context = local()

    @property
    def spans(self) -> list[Span]:
        """获取所有已完成的Span.

        Returns:
            Span列表的副本
        """
        return list(self._spans)

    @property
    def _current_span(self) -> Span | None:
        """获取当前活动的Span.

        Returns:
            当前Span或None
        """
        span_stack = getattr(self._context, "span_stack", None)
        if span_stack:
            return span_stack[-1]
        return None

    @property
    def _current_trace_id(self) -> TraceId | None:
        """获取当前追踪ID.

        Returns:
            当前追踪ID或None
        """
        current = self._current_span
        return current.trace_id if current else None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
        parent: Span | None = None,
    ) -> Span:
        """开始一个新的Span.

        Args:
            name: Span名称
            kind: Span类型
            attributes: 初始属性
            parent: 父Span(如果不指定则使用当前上下文中的Span)

        Returns:
            新创建的Span
        """
        # 确定父Span
        parent_span = parent or self._current_span

        # 创建Span
        span = Span(
            name=name,
            kind=kind,
            trace_id=parent_span.trace_id if parent_span else _generate_trace_id(),
            parent_span_id=parent_span.span_id if parent_span else None,
            start_time=datetime.now(),
            _start_time_ns=time.perf_counter_ns(),
        )

        # 添加服务名称属性
        span.set_attribute("service.name", self.service_name)

        # 设置初始属性
        if attributes:
            span.set_attributes(attributes)

        # 推入上下文栈
        if not hasattr(self._context, "span_stack"):
            self._context.span_stack = []
        self._context.span_stack.append(span)

        return span

    def end_span(self, span: Span | None = None) -> None:
        """结束Span.

        Args:
            span: 要结束的Span(如果不指定则结束当前Span)
        """
        target_span = span or self._current_span
        if not target_span:
            return

        # 结束Span
        target_span.end()

        # 从上下文栈中移除
        span_stack = getattr(self._context, "span_stack", [])
        if span_stack and span_stack[-1] is target_span:
            span_stack.pop()

        # 存储已完成的Span
        self._store_span(target_span)

    def _store_span(self, span: Span) -> None:
        """存储已完成的Span.

        Args:
            span: 要存储的Span
        """
        self._spans.append(span)

        # 限制存储数量
        if len(self._spans) > self.max_spans:
            self._spans = self._spans[-self.max_spans :]

    @contextmanager
    def trace(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """追踪上下文管理器.

        简化Span的创建和管理:
        - 自动开始和结束Span
        - 自动处理异常并记录
        - 自动设置成功/失败状态

        Args:
            name: Span名称
            kind: Span类型
            attributes: 初始属性

        Yields:
            创建的Span对象

        使用示例:
            >>> with tracer.trace("my_operation") as span:
            ...     span.set_attribute("key", "value")
            ...     # 执行操作
        """
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            self.end_span(span)

    def clear_spans(self) -> None:
        """清空所有已存储的Span."""
        self._spans.clear()

    def get_active_spans(self) -> list[Span]:
        """获取当前活动的Span栈.

        Returns:
            活动Span列表(从根到叶)
        """
        return list(getattr(self._context, "span_stack", []))

    def inject_context(self) -> dict[str, str]:
        """注入追踪上下文.

        用于跨进程/服务传递追踪信息.

        Returns:
            包含追踪上下文的字典
        """
        current = self._current_span
        if not current:
            return {}

        return {
            "trace_id": current.trace_id,
            "span_id": current.span_id,
            "service_name": self.service_name,
        }

    def extract_context(
        self,
        headers: dict[str, str],
    ) -> tuple[TraceId | None, SpanId | None]:
        """提取追踪上下文.

        从传入的请求头中提取追踪信息.

        Args:
            headers: 包含追踪上下文的字典

        Returns:
            (trace_id, span_id)元组
        """
        return headers.get("trace_id"), headers.get("span_id")

    def create_child_span(
        self,
        name: str,
        trace_id: TraceId,
        parent_span_id: SpanId,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> Span:
        """创建子Span.

        用于从外部上下文创建子Span(跨服务调用).

        Args:
            name: Span名称
            trace_id: 追踪ID
            parent_span_id: 父Span ID
            kind: Span类型

        Returns:
            新创建的Span
        """
        span = Span(
            name=name,
            kind=kind,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            start_time=datetime.now(),
            _start_time_ns=time.perf_counter_ns(),
        )
        span.set_attribute("service.name", self.service_name)

        # 推入上下文栈
        if not hasattr(self._context, "span_stack"):
            self._context.span_stack = []
        self._context.span_stack.append(span)

        return span


# =============================================================================
# 全局追踪器
# =============================================================================

_global_tracer: Tracer | None = None


def get_tracer(service_name: str = "default") -> Tracer:
    """获取或创建全局追踪器.

    Args:
        service_name: 服务名称(仅在创建时使用)

    Returns:
        全局追踪器实例
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer(service_name)
    return _global_tracer


def set_tracer(tracer: Tracer) -> None:
    """设置全局追踪器.

    Args:
        tracer: 追踪器实例
    """
    global _global_tracer
    _global_tracer = tracer


def reset_tracer() -> None:
    """重置全局追踪器."""
    global _global_tracer
    _global_tracer = None


# =============================================================================
# 模块导出
# =============================================================================

__all__ = [
    # 类型别名
    "SpanId",
    "TraceId",
    # 枚举
    "SpanStatus",
    "SpanKind",
    # 数据类
    "SpanEvent",
    "Span",
    # 主类
    "Tracer",
    # 全局函数
    "get_tracer",
    "set_tracer",
    "reset_tracer",
]
