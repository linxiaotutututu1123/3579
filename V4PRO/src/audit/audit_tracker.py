"""
AuditTracker - 审计追踪机制

V4PRO Platform Component - Phase 8
V2 SPEC: 7.2

军规级要求:
- M3: 审计日志完整 - 所有操作必须可追溯
- 链式追踪: trace_id 贯穿完整调用链
- 时序保证: 事件按严格时序记录
- 合规存储: 交易5年, 系统3年, 审计10年
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# =============================================================================
# 事件类型枚举
# =============================================================================


class AuditEventCategory(str, Enum):
    """审计事件类别.

    军规 M3: 必须区分事件类别以满足不同合规存储要求.
    """

    TRADING = "TRADING"      # 交易事件 - 5年存储
    RISK = "RISK"            # 风控事件 - 5年存储
    SYSTEM = "SYSTEM"        # 系统事件 - 3年存储
    AUDIT = "AUDIT"          # 审计事件 - 10年存储
    COMPLIANCE = "COMPLIANCE"  # 合规事件 - 10年存储


class AuditEventType(str, Enum):
    """审计事件类型."""

    # 交易类
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_CHANGED = "POSITION_CHANGED"
    PNL_REALIZED = "PNL_REALIZED"

    # 风控类
    RISK_CHECK_PASSED = "RISK_CHECK_PASSED"
    RISK_CHECK_FAILED = "RISK_CHECK_FAILED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    CIRCUIT_BREAKER_RESET = "CIRCUIT_BREAKER_RESET"
    MARGIN_WARNING = "MARGIN_WARNING"
    POSITION_LIMIT_WARNING = "POSITION_LIMIT_WARNING"

    # 系统类
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    CONFIG_CHANGED = "CONFIG_CHANGED"
    STRATEGY_LOADED = "STRATEGY_LOADED"
    STRATEGY_UNLOADED = "STRATEGY_UNLOADED"
    CONNECTION_ESTABLISHED = "CONNECTION_ESTABLISHED"
    CONNECTION_LOST = "CONNECTION_LOST"

    # 审计类
    AUDIT_TRAIL_CREATED = "AUDIT_TRAIL_CREATED"
    AUDIT_TRAIL_VERIFIED = "AUDIT_TRAIL_VERIFIED"
    AUDIT_CHECKPOINT = "AUDIT_CHECKPOINT"

    # 合规类
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    REGULATORY_REPORT = "REGULATORY_REPORT"


# 事件类别映射
EVENT_CATEGORY_MAP: dict[AuditEventType, AuditEventCategory] = {
    # 交易类
    AuditEventType.SIGNAL_GENERATED: AuditEventCategory.TRADING,
    AuditEventType.ORDER_SUBMITTED: AuditEventCategory.TRADING,
    AuditEventType.ORDER_FILLED: AuditEventCategory.TRADING,
    AuditEventType.ORDER_CANCELLED: AuditEventCategory.TRADING,
    AuditEventType.ORDER_REJECTED: AuditEventCategory.TRADING,
    AuditEventType.POSITION_CHANGED: AuditEventCategory.TRADING,
    AuditEventType.PNL_REALIZED: AuditEventCategory.TRADING,
    # 风控类
    AuditEventType.RISK_CHECK_PASSED: AuditEventCategory.RISK,
    AuditEventType.RISK_CHECK_FAILED: AuditEventCategory.RISK,
    AuditEventType.CIRCUIT_BREAKER_TRIGGERED: AuditEventCategory.RISK,
    AuditEventType.CIRCUIT_BREAKER_RESET: AuditEventCategory.RISK,
    AuditEventType.MARGIN_WARNING: AuditEventCategory.RISK,
    AuditEventType.POSITION_LIMIT_WARNING: AuditEventCategory.RISK,
    # 系统类
    AuditEventType.SYSTEM_STARTUP: AuditEventCategory.SYSTEM,
    AuditEventType.SYSTEM_SHUTDOWN: AuditEventCategory.SYSTEM,
    AuditEventType.CONFIG_CHANGED: AuditEventCategory.SYSTEM,
    AuditEventType.STRATEGY_LOADED: AuditEventCategory.SYSTEM,
    AuditEventType.STRATEGY_UNLOADED: AuditEventCategory.SYSTEM,
    AuditEventType.CONNECTION_ESTABLISHED: AuditEventCategory.SYSTEM,
    AuditEventType.CONNECTION_LOST: AuditEventCategory.SYSTEM,
    # 审计类
    AuditEventType.AUDIT_TRAIL_CREATED: AuditEventCategory.AUDIT,
    AuditEventType.AUDIT_TRAIL_VERIFIED: AuditEventCategory.AUDIT,
    AuditEventType.AUDIT_CHECKPOINT: AuditEventCategory.AUDIT,
    # 合规类
    AuditEventType.COMPLIANCE_CHECK: AuditEventCategory.COMPLIANCE,
    AuditEventType.REGULATORY_REPORT: AuditEventCategory.COMPLIANCE,
}


# 合规存储期限 (天)
RETENTION_DAYS: dict[AuditEventCategory, int] = {
    AuditEventCategory.TRADING: 5 * 365,     # 5年
    AuditEventCategory.RISK: 5 * 365,        # 5年 (与交易同等重要)
    AuditEventCategory.SYSTEM: 3 * 365,      # 3年
    AuditEventCategory.AUDIT: 10 * 365,      # 10年
    AuditEventCategory.COMPLIANCE: 10 * 365,  # 10年
}


# =============================================================================
# 审计事件数据类
# =============================================================================


@dataclass
class TracedAuditEvent:
    """可追踪的审计事件.

    V2 Scenario: AUDIT.TRACE.CHAIN

    军规 M3 要求:
    - 每个事件必须有唯一 trace_id
    - 支持父子事件关联 (parent_id)
    - 时间戳精确到微秒
    - checksum 防篡改

    Attributes:
        event_id: 事件唯一 ID (UUID)
        event_type: 事件类型
        category: 事件类别
        trace_id: 追踪 ID (贯穿整个调用链)
        parent_id: 父事件 ID (用于链式追踪)
        timestamp: 时间戳 (Unix epoch, 微秒精度)
        sequence: 序列号 (保证时序)
        run_id: 运行 ID
        exec_id: 执行 ID
        data: 事件数据
        checksum: SHA256 校验和
        metadata: 额外元数据
    """

    event_id: str
    event_type: str
    category: str
    trace_id: str
    timestamp: float
    sequence: int
    run_id: str
    exec_id: str
    data: dict[str, Any]
    checksum: str
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TracedAuditEvent:
        """从字典创建事件."""
        return cls(**data)

    def verify_checksum(self) -> bool:
        """验证校验和.

        Returns:
            True 如果校验和正确
        """
        expected = _compute_checksum(
            event_id=self.event_id,
            event_type=self.event_type,
            trace_id=self.trace_id,
            parent_id=self.parent_id,
            timestamp=self.timestamp,
            sequence=self.sequence,
            data=self.data,
        )
        return self.checksum == expected


def _compute_checksum(
    event_id: str,
    event_type: str,
    trace_id: str,
    parent_id: str | None,
    timestamp: float,
    sequence: int,
    data: dict[str, Any],
) -> str:
    """计算事件校验和.

    使用 SHA256 确保事件完整性和防篡改.

    Args:
        event_id: 事件 ID
        event_type: 事件类型
        trace_id: 追踪 ID
        parent_id: 父事件 ID
        timestamp: 时间戳
        sequence: 序列号
        data: 事件数据

    Returns:
        64 位十六进制校验和
    """
    content = {
        "event_id": event_id,
        "event_type": event_type,
        "trace_id": trace_id,
        "parent_id": parent_id,
        "timestamp": timestamp,
        "sequence": sequence,
        "data": data,
    }
    sorted_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(sorted_json.encode("utf-8")).hexdigest()


# =============================================================================
# 追踪上下文
# =============================================================================


@dataclass
class TraceContext:
    """追踪上下文.

    用于在调用链中传递追踪信息.

    Attributes:
        trace_id: 追踪 ID
        parent_id: 当前父事件 ID
        run_id: 运行 ID
        exec_id: 执行 ID
    """

    trace_id: str
    run_id: str
    exec_id: str
    parent_id: str | None = None

    def child(self, parent_event_id: str) -> TraceContext:
        """创建子上下文.

        Args:
            parent_event_id: 父事件 ID

        Returns:
            新的追踪上下文
        """
        return TraceContext(
            trace_id=self.trace_id,
            run_id=self.run_id,
            exec_id=self.exec_id,
            parent_id=parent_event_id,
        )

    @classmethod
    def new(cls, run_id: str, exec_id: str | None = None) -> TraceContext:
        """创建新的追踪上下文.

        Args:
            run_id: 运行 ID
            exec_id: 执行 ID (默认与 run_id 相同)

        Returns:
            新的追踪上下文
        """
        return cls(
            trace_id=str(uuid.uuid4()),
            run_id=run_id,
            exec_id=exec_id or run_id,
            parent_id=None,
        )


# =============================================================================
# 审计追踪器
# =============================================================================


class AuditTracker:
    """审计追踪器.

    V2 Scenarios:
    - AUDIT.TRACE.CHAIN: 链式追踪
    - AUDIT.TRACE.SEQUENCE: 时序保证
    - AUDIT.TRACE.PERSIST: 持久化存储

    军规 M3 要求:
    - 所有事件必须原子化写入
    - 支持链式追踪 (trace_id + parent_id)
    - 时序严格递增 (sequence)
    - 校验和防篡改
    - 合规存储期限

    使用示例:
        tracker = AuditTracker(
            base_path=Path("./audit_logs"),
            run_id="run-123",
        )

        # 创建追踪上下文
        ctx = tracker.new_trace()

        # 记录交易事件
        event = tracker.record(
            ctx=ctx,
            event_type=AuditEventType.ORDER_SUBMITTED,
            data={"order_id": "ord-456", "symbol": "IF2401"},
        )

        # 创建子事件
        child_ctx = ctx.child(event.event_id)
        tracker.record(
            ctx=child_ctx,
            event_type=AuditEventType.ORDER_FILLED,
            data={"order_id": "ord-456", "filled_qty": 1},
        )
    """

    def __init__(
        self,
        base_path: Path,
        run_id: str,
        exec_id: str | None = None,
        *,
        auto_checkpoint: bool = True,
        checkpoint_interval: int = 1000,
    ) -> None:
        """初始化审计追踪器.

        Args:
            base_path: 审计日志基础路径
            run_id: 运行 ID
            exec_id: 执行 ID (默认与 run_id 相同)
            auto_checkpoint: 是否自动创建检查点
            checkpoint_interval: 检查点间隔 (事件数)
        """
        self._base_path = base_path
        self._run_id = run_id
        self._exec_id = exec_id or run_id
        self._auto_checkpoint = auto_checkpoint
        self._checkpoint_interval = checkpoint_interval

        # 序列号生成器 (线程安全)
        self._sequence = 0
        self._sequence_lock = threading.Lock()

        # 事件缓存 (用于快速查询)
        self._events: dict[str, TracedAuditEvent] = {}
        self._traces: dict[str, list[str]] = {}  # trace_id -> [event_ids]

        # 按类别分离的写入器
        self._writers: dict[AuditEventCategory, Path] = {}

        # 事件监听器
        self._listeners: list[Callable[[TracedAuditEvent], None]] = []

        # 已关闭标志
        self._closed = False

        # 初始化目录结构
        self._init_directories()

    def _init_directories(self) -> None:
        """初始化目录结构."""
        # 按日期和类别组织
        date_str = datetime.now().strftime("%Y%m%d")

        for category in AuditEventCategory:
            category_path = self._base_path / category.value.lower() / date_str
            category_path.mkdir(parents=True, exist_ok=True)

            # 文件名包含 run_id 以支持多实例
            file_path = category_path / f"{self._run_id}.jsonl"
            self._writers[category] = file_path

    @property
    def run_id(self) -> str:
        """获取运行 ID."""
        return self._run_id

    @property
    def exec_id(self) -> str:
        """获取执行 ID."""
        return self._exec_id

    def new_trace(self) -> TraceContext:
        """创建新的追踪上下文.

        Returns:
            新的追踪上下文
        """
        return TraceContext.new(self._run_id, self._exec_id)

    def _next_sequence(self) -> int:
        """获取下一个序列号 (线程安全)."""
        with self._sequence_lock:
            self._sequence += 1
            return self._sequence

    def record(
        self,
        ctx: TraceContext,
        event_type: AuditEventType | str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> TracedAuditEvent:
        """记录审计事件.

        军规 M3: 所有操作必须有完整审计记录.

        Args:
            ctx: 追踪上下文
            event_type: 事件类型
            data: 事件数据
            metadata: 额外元数据

        Returns:
            创建的审计事件

        Raises:
            RuntimeError: 追踪器已关闭
        """
        if self._closed:
            raise RuntimeError("AuditTracker is closed")

        # 标准化事件类型
        if isinstance(event_type, AuditEventType):
            event_type_str = event_type.value
            category = EVENT_CATEGORY_MAP.get(event_type, AuditEventCategory.SYSTEM)
        else:
            event_type_str = event_type
            category = AuditEventCategory.SYSTEM

        # 生成事件 ID 和序列号
        event_id = str(uuid.uuid4())
        sequence = self._next_sequence()
        timestamp = time.time()

        # 计算校验和
        checksum = _compute_checksum(
            event_id=event_id,
            event_type=event_type_str,
            trace_id=ctx.trace_id,
            parent_id=ctx.parent_id,
            timestamp=timestamp,
            sequence=sequence,
            data=data,
        )

        # 创建事件
        event = TracedAuditEvent(
            event_id=event_id,
            event_type=event_type_str,
            category=category.value,
            trace_id=ctx.trace_id,
            parent_id=ctx.parent_id,
            timestamp=timestamp,
            sequence=sequence,
            run_id=ctx.run_id,
            exec_id=ctx.exec_id,
            data=data,
            checksum=checksum,
            metadata=metadata or {},
        )

        # 持久化写入
        self._persist(event, category)

        # 更新缓存
        self._events[event_id] = event
        if ctx.trace_id not in self._traces:
            self._traces[ctx.trace_id] = []
        self._traces[ctx.trace_id].append(event_id)

        # 通知监听器
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass  # 监听器异常不应影响主流程

        # 自动检查点
        if self._auto_checkpoint and sequence % self._checkpoint_interval == 0:
            self._create_checkpoint()

        return event

    def _persist(self, event: TracedAuditEvent, category: AuditEventCategory) -> None:
        """持久化写入事件.

        使用原子化写入确保数据完整性.
        """
        file_path = self._writers[category]
        line = json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n"

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def _create_checkpoint(self) -> None:
        """创建审计检查点.

        用于验证审计日志完整性.
        """
        checkpoint_data = {
            "checkpoint_time": time.time(),
            "sequence": self._sequence,
            "event_count": len(self._events),
            "trace_count": len(self._traces),
        }

        # 记录检查点事件
        ctx = self.new_trace()
        self.record(
            ctx=ctx,
            event_type=AuditEventType.AUDIT_CHECKPOINT,
            data=checkpoint_data,
        )

    def add_listener(self, listener: Callable[[TracedAuditEvent], None]) -> None:
        """添加事件监听器.

        Args:
            listener: 事件监听函数
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[TracedAuditEvent], None]) -> None:
        """移除事件监听器.

        Args:
            listener: 事件监听函数
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def get_event(self, event_id: str) -> TracedAuditEvent | None:
        """获取事件.

        Args:
            event_id: 事件 ID

        Returns:
            审计事件或 None
        """
        return self._events.get(event_id)

    def get_trace(self, trace_id: str) -> list[TracedAuditEvent]:
        """获取追踪链中的所有事件.

        Args:
            trace_id: 追踪 ID

        Returns:
            事件列表 (按序列号排序)
        """
        event_ids = self._traces.get(trace_id, [])
        events = [self._events[eid] for eid in event_ids if eid in self._events]
        return sorted(events, key=lambda e: e.sequence)

    def get_children(self, parent_id: str) -> list[TracedAuditEvent]:
        """获取子事件.

        Args:
            parent_id: 父事件 ID

        Returns:
            子事件列表
        """
        return [
            event for event in self._events.values()
            if event.parent_id == parent_id
        ]

    def verify_trace(self, trace_id: str) -> tuple[bool, list[str]]:
        """验证追踪链完整性.

        检查追踪链中所有事件的校验和.

        Args:
            trace_id: 追踪 ID

        Returns:
            (验证通过, 错误列表)
        """
        events = self.get_trace(trace_id)
        errors: list[str] = []

        for event in events:
            if not event.verify_checksum():
                errors.append(f"Event {event.event_id}: checksum mismatch")

        # 验证序列号连续性 (在同一 trace 内)
        sequences = [e.sequence for e in events]
        for i in range(1, len(sequences)):
            if sequences[i] <= sequences[i - 1]:
                errors.append(
                    f"Sequence order violation: {sequences[i]} <= {sequences[i-1]}"
                )

        return len(errors) == 0, errors

    def get_retention_expiry(self, category: AuditEventCategory) -> datetime:
        """获取合规存储到期时间.

        Args:
            category: 事件类别

        Returns:
            到期时间
        """
        days = RETENTION_DAYS.get(category, 365)
        return datetime.now() + timedelta(days=days)

    def close(self) -> None:
        """关闭追踪器."""
        if not self._closed:
            # 创建最终检查点
            self._create_checkpoint()
            self._closed = True

    def __enter__(self) -> AuditTracker:
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器出口."""
        self.close()


# =============================================================================
# 便捷工厂函数
# =============================================================================


def create_audit_tracker(
    base_path: str | Path,
    run_id: str,
    exec_id: str | None = None,
) -> AuditTracker:
    """创建审计追踪器.

    Args:
        base_path: 审计日志基础路径
        run_id: 运行 ID
        exec_id: 执行 ID

    Returns:
        AuditTracker 实例
    """
    return AuditTracker(
        base_path=Path(base_path),
        run_id=run_id,
        exec_id=exec_id,
    )


# =============================================================================
# 审计事件读取器
# =============================================================================


def read_audit_trail(
    base_path: Path,
    category: AuditEventCategory,
    date: datetime | None = None,
    run_id: str | None = None,
) -> list[TracedAuditEvent]:
    """读取审计追踪记录.

    Args:
        base_path: 审计日志基础路径
        category: 事件类别
        date: 日期 (默认今天)
        run_id: 运行 ID (可选, 不指定则读取所有)

    Returns:
        事件列表
    """
    if date is None:
        date = datetime.now()

    date_str = date.strftime("%Y%m%d")
    category_path = base_path / category.value.lower() / date_str

    if not category_path.exists():
        return []

    events: list[TracedAuditEvent] = []

    # 确定要读取的文件
    if run_id:
        files = [category_path / f"{run_id}.jsonl"]
    else:
        files = list(category_path.glob("*.jsonl"))

    for file_path in files:
        if not file_path.exists():
            continue

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    data = json.loads(stripped)
                    events.append(TracedAuditEvent.from_dict(data))

    return sorted(events, key=lambda e: e.sequence)


def verify_audit_integrity(
    base_path: Path,
    category: AuditEventCategory,
    date: datetime | None = None,
) -> tuple[bool, list[str]]:
    """验证审计日志完整性.

    军规 M3: 审计日志必须可验证完整性.

    Args:
        base_path: 审计日志基础路径
        category: 事件类别
        date: 日期

    Returns:
        (验证通过, 错误列表)
    """
    events = read_audit_trail(base_path, category, date)
    errors: list[str] = []

    for event in events:
        if not event.verify_checksum():
            errors.append(
                f"Event {event.event_id} at {event.timestamp}: checksum mismatch"
            )

    # 验证序列号全局唯一性和递增性
    seen_sequences: dict[str, int] = {}  # run_id -> last_sequence

    for event in events:
        run_id = event.run_id
        if run_id in seen_sequences:
            if event.sequence <= seen_sequences[run_id]:
                errors.append(
                    f"Event {event.event_id}: sequence {event.sequence} "
                    f"<= previous {seen_sequences[run_id]} for run {run_id}"
                )
        seen_sequences[run_id] = event.sequence

    return len(errors) == 0, errors
