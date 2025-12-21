"""
信号源注册表模块 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制
V4 SPEC: M1军规 - 信号源注册与管理

军规覆盖:
- M1: 单一信号源 - 信号源唯一性管理
- M3: 审计日志 - 注册/注销追踪
- M7: 场景回放 - 状态可恢复

功能特性:
- 信号源注册/注销
- 信号源生命周期管理
- 信号源状态监控
- 审计日志支持
- 线程安全操作

示例:
    >>> from src.strategy.signal import SignalSourceRegistry, SignalSource
    >>> registry = SignalSourceRegistry.get_instance()
    >>> source = SignalSource(strategy_id="kalman_arb", instance_id="inst_001")
    >>> registry.register(source)
    >>> active_sources = registry.get_active_sources()
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from src.strategy.signal.source import SignalSource, SourceStatus


if TYPE_CHECKING:
    from collections.abc import Callable


class RegistryEventType(Enum):
    """注册表事件类型枚举."""

    SOURCE_REGISTERED = "SOURCE_REGISTERED"  # 信号源注册
    SOURCE_UNREGISTERED = "SOURCE_UNREGISTERED"  # 信号源注销
    SOURCE_ACTIVATED = "SOURCE_ACTIVATED"  # 信号源激活
    SOURCE_SUSPENDED = "SOURCE_SUSPENDED"  # 信号源暂停
    SOURCE_DISABLED = "SOURCE_DISABLED"  # 信号源禁用
    SOURCE_EXPIRED = "SOURCE_EXPIRED"  # 信号源过期


@dataclass(frozen=True, slots=True)
class RegistryEvent:
    """注册表事件 (不可变).

    属性:
        event_type: 事件类型
        source_id: 信号源ID
        strategy_id: 策略ID
        timestamp: 时间戳
        details: 详细信息
    """

    event_type: RegistryEventType
    source_id: str
    strategy_id: str
    timestamp: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "event_type": self.event_type.value,
            "source_id": self.source_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=UTC
            ).isoformat(),
            "details": self.details,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_category": "SIGNAL_REGISTRY",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.to_dict(),
        }


@dataclass
class SourceMetadata:
    """信号源元数据.

    属性:
        source: 信号源实例
        registered_at: 注册时间
        last_active_at: 最后活跃时间
        signal_count: 信号计数
        error_count: 错误计数
        tags: 标签列表
    """

    source: SignalSource
    registered_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)
    signal_count: int = 0
    error_count: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def source_id(self) -> str:
        """获取信号源ID."""
        return self.source.full_source_id

    @property
    def strategy_id(self) -> str:
        """获取策略ID."""
        return self.source.strategy_id

    def record_signal(self) -> None:
        """记录信号."""
        self.signal_count += 1
        self.last_active_at = time.time()

    def record_error(self) -> None:
        """记录错误."""
        self.error_count += 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "source_id": self.source_id,
            "strategy_id": self.strategy_id,
            "instance_id": self.source.instance_id,
            "status": self.source.status.value,
            "registered_at": self.registered_at,
            "last_active_at": self.last_active_at,
            "signal_count": self.signal_count,
            "error_count": self.error_count,
            "tags": self.tags,
        }


class SignalSourceRegistry:
    """信号源注册表 (M1军规核心组件 - 单例模式).

    负责:
    - 信号源注册与注销
    - 信号源生命周期管理
    - 信号源状态监控
    - 审计事件记录
    - 线程安全操作

    属性:
        _instance: 单例实例
        _sources: 已注册信号源
        _events: 事件历史
    """

    # 单例实例
    _instance: ClassVar[SignalSourceRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # 默认配置
    DEFAULT_EVENT_HISTORY_SIZE: ClassVar[int] = 10000  # 事件历史大小
    DEFAULT_SOURCE_TTL: ClassVar[float] = 86400.0  # 信号源默认TTL (24小时)

    def __new__(cls) -> SignalSourceRegistry:
        """确保单例."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """初始化注册表."""
        if getattr(self, "_initialized", False):
            return

        self._sources: dict[str, SourceMetadata] = {}
        self._strategy_sources: dict[str, set[str]] = {}  # strategy_id -> source_ids
        self._events: deque[RegistryEvent] = deque(maxlen=self.DEFAULT_EVENT_HISTORY_SIZE)
        self._callbacks: list[Callable[[RegistryEvent], None]] = []
        self._source_lock = threading.RLock()
        self._initialized = True

    @classmethod
    def get_instance(cls) -> SignalSourceRegistry:
        """获取单例实例."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例 (仅用于测试)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._sources.clear()
                cls._instance._strategy_sources.clear()
                cls._instance._events.clear()
                cls._instance._callbacks.clear()
            cls._instance = None

    @property
    def source_count(self) -> int:
        """获取注册的信号源数量."""
        with self._source_lock:
            return len(self._sources)

    @property
    def active_source_count(self) -> int:
        """获取活跃的信号源数量."""
        with self._source_lock:
            return sum(
                1 for meta in self._sources.values()
                if meta.source.status == SourceStatus.ACTIVE
            )

    @property
    def strategy_count(self) -> int:
        """获取策略数量."""
        with self._source_lock:
            return len(self._strategy_sources)

    def register(
        self,
        source: SignalSource,
        tags: list[str] | None = None,
    ) -> bool:
        """注册信号源.

        参数:
            source: 信号源实例
            tags: 标签列表

        返回:
            是否注册成功
        """
        source_id = source.full_source_id
        strategy_id = source.strategy_id

        with self._source_lock:
            # 检查是否已注册
            if source_id in self._sources:
                return False

            # 创建元数据
            metadata = SourceMetadata(
                source=source,
                tags=tags or [],
            )

            # 注册信号源
            self._sources[source_id] = metadata

            # 更新策略索引
            if strategy_id not in self._strategy_sources:
                self._strategy_sources[strategy_id] = set()
            self._strategy_sources[strategy_id].add(source_id)

        # 记录事件
        self._emit_event(
            event_type=RegistryEventType.SOURCE_REGISTERED,
            source_id=source_id,
            strategy_id=strategy_id,
            details={"tags": tags or []},
        )

        return True

    def unregister(self, source_id: str) -> bool:
        """注销信号源.

        参数:
            source_id: 信号源ID

        返回:
            是否注销成功
        """
        with self._source_lock:
            if source_id not in self._sources:
                return False

            metadata = self._sources[source_id]
            strategy_id = metadata.strategy_id

            # 移除信号源
            del self._sources[source_id]

            # 更新策略索引
            if strategy_id in self._strategy_sources:
                self._strategy_sources[strategy_id].discard(source_id)
                if not self._strategy_sources[strategy_id]:
                    del self._strategy_sources[strategy_id]

        # 记录事件
        self._emit_event(
            event_type=RegistryEventType.SOURCE_UNREGISTERED,
            source_id=source_id,
            strategy_id=strategy_id,
        )

        return True

    def get_source(self, source_id: str) -> SignalSource | None:
        """获取信号源.

        参数:
            source_id: 信号源ID

        返回:
            信号源实例或None
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            return metadata.source if metadata else None

    def get_metadata(self, source_id: str) -> SourceMetadata | None:
        """获取信号源元数据.

        参数:
            source_id: 信号源ID

        返回:
            元数据或None
        """
        with self._source_lock:
            return self._sources.get(source_id)

    def is_registered(self, source_id: str) -> bool:
        """检查信号源是否已注册."""
        with self._source_lock:
            return source_id in self._sources

    def is_active(self, source_id: str) -> bool:
        """检查信号源是否活跃."""
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False
            return metadata.source.status == SourceStatus.ACTIVE

    def activate(self, source_id: str) -> bool:
        """激活信号源.

        参数:
            source_id: 信号源ID

        返回:
            是否激活成功
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False

            metadata.source.activate()
            strategy_id = metadata.strategy_id

        self._emit_event(
            event_type=RegistryEventType.SOURCE_ACTIVATED,
            source_id=source_id,
            strategy_id=strategy_id,
        )

        return True

    def suspend(self, source_id: str) -> bool:
        """暂停信号源.

        参数:
            source_id: 信号源ID

        返回:
            是否暂停成功
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False

            metadata.source.suspend()
            strategy_id = metadata.strategy_id

        self._emit_event(
            event_type=RegistryEventType.SOURCE_SUSPENDED,
            source_id=source_id,
            strategy_id=strategy_id,
        )

        return True

    def disable(self, source_id: str) -> bool:
        """禁用信号源.

        参数:
            source_id: 信号源ID

        返回:
            是否禁用成功
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False

            metadata.source.disable()
            strategy_id = metadata.strategy_id

        self._emit_event(
            event_type=RegistryEventType.SOURCE_DISABLED,
            source_id=source_id,
            strategy_id=strategy_id,
        )

        return True

    def get_all_sources(self) -> list[SignalSource]:
        """获取所有信号源."""
        with self._source_lock:
            return [meta.source for meta in self._sources.values()]

    def get_active_sources(self) -> list[SignalSource]:
        """获取所有活跃的信号源."""
        with self._source_lock:
            return [
                meta.source for meta in self._sources.values()
                if meta.source.status == SourceStatus.ACTIVE
            ]

    def get_sources_by_strategy(self, strategy_id: str) -> list[SignalSource]:
        """获取指定策略的所有信号源.

        参数:
            strategy_id: 策略ID

        返回:
            信号源列表
        """
        with self._source_lock:
            source_ids = self._strategy_sources.get(strategy_id, set())
            return [
                self._sources[sid].source
                for sid in source_ids
                if sid in self._sources
            ]

    def get_sources_by_tag(self, tag: str) -> list[SignalSource]:
        """获取指定标签的所有信号源.

        参数:
            tag: 标签

        返回:
            信号源列表
        """
        with self._source_lock:
            return [
                meta.source for meta in self._sources.values()
                if tag in meta.tags
            ]

    def record_signal(self, source_id: str) -> None:
        """记录信号发射.

        参数:
            source_id: 信号源ID
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if metadata:
                metadata.record_signal()

    def record_error(self, source_id: str) -> None:
        """记录错误.

        参数:
            source_id: 信号源ID
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if metadata:
                metadata.record_error()

    def add_tag(self, source_id: str, tag: str) -> bool:
        """添加标签.

        参数:
            source_id: 信号源ID
            tag: 标签

        返回:
            是否添加成功
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False
            if tag not in metadata.tags:
                metadata.tags.append(tag)
            return True

    def remove_tag(self, source_id: str, tag: str) -> bool:
        """移除标签.

        参数:
            source_id: 信号源ID
            tag: 标签

        返回:
            是否移除成功
        """
        with self._source_lock:
            metadata = self._sources.get(source_id)
            if not metadata:
                return False
            if tag in metadata.tags:
                metadata.tags.remove(tag)
            return True

    def register_callback(
        self,
        callback: Callable[[RegistryEvent], None],
    ) -> None:
        """注册事件回调.

        参数:
            callback: 回调函数
        """
        self._callbacks.append(callback)

    def unregister_callback(
        self,
        callback: Callable[[RegistryEvent], None],
    ) -> None:
        """注销事件回调.

        参数:
            callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _emit_event(
        self,
        event_type: RegistryEventType,
        source_id: str,
        strategy_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """发送事件.

        参数:
            event_type: 事件类型
            source_id: 信号源ID
            strategy_id: 策略ID
            details: 详细信息
        """
        event = RegistryEvent(
            event_type=event_type,
            source_id=source_id,
            strategy_id=strategy_id,
            timestamp=time.time(),
            details=details or {},
        )

        self._events.append(event)

        # 通知回调
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass  # 忽略回调异常

    def get_recent_events(self, count: int = 100) -> list[RegistryEvent]:
        """获取最近的事件.

        参数:
            count: 事件数量

        返回:
            事件列表
        """
        return list(self._events)[-count:]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        with self._source_lock:
            status_counts: dict[str, int] = {}
            for meta in self._sources.values():
                status = meta.source.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            total_signals = sum(meta.signal_count for meta in self._sources.values())
            total_errors = sum(meta.error_count for meta in self._sources.values())

            return {
                "total_sources": len(self._sources),
                "total_strategies": len(self._strategy_sources),
                "status_breakdown": status_counts,
                "total_signals": total_signals,
                "total_errors": total_errors,
                "event_count": len(self._events),
            }

    def get_health_report(self) -> dict[str, Any]:
        """获取健康报告."""
        with self._source_lock:
            unhealthy_sources = []
            now = time.time()

            for source_id, meta in self._sources.items():
                # 检查是否长时间未活跃
                inactive_duration = now - meta.last_active_at
                if inactive_duration > 3600:  # 1小时未活跃
                    unhealthy_sources.append({
                        "source_id": source_id,
                        "reason": "inactive",
                        "duration": inactive_duration,
                    })

                # 检查错误率
                if meta.signal_count > 0:
                    error_rate = meta.error_count / meta.signal_count
                    if error_rate > 0.1:  # 错误率超过10%
                        unhealthy_sources.append({
                            "source_id": source_id,
                            "reason": "high_error_rate",
                            "error_rate": error_rate,
                        })

            return {
                "healthy": len(unhealthy_sources) == 0,
                "total_sources": len(self._sources),
                "unhealthy_count": len(unhealthy_sources),
                "unhealthy_sources": unhealthy_sources,
                "check_time": datetime.now(tz=UTC).isoformat(),
            }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "REGISTRY_STATUS",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.get_statistics(),
        }

    def clear(self) -> None:
        """清空注册表 (仅用于测试)."""
        with self._source_lock:
            self._sources.clear()
            self._strategy_sources.clear()
            self._events.clear()


# ============================================================
# 便捷函数
# ============================================================


def get_registry() -> SignalSourceRegistry:
    """获取全局注册表实例."""
    return SignalSourceRegistry.get_instance()


def register_source(
    source: SignalSource,
    tags: list[str] | None = None,
) -> bool:
    """注册信号源到全局注册表.

    参数:
        source: 信号源实例
        tags: 标签列表

    返回:
        是否注册成功
    """
    return get_registry().register(source, tags)


def unregister_source(source_id: str) -> bool:
    """从全局注册表注销信号源.

    参数:
        source_id: 信号源ID

    返回:
        是否注销成功
    """
    return get_registry().unregister(source_id)


def get_source(source_id: str) -> SignalSource | None:
    """从全局注册表获取信号源.

    参数:
        source_id: 信号源ID

    返回:
        信号源实例或None
    """
    return get_registry().get_source(source_id)
