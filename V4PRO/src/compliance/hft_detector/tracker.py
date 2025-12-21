"""
订单频率追踪器模块 (军规级 v4.0).

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: D7-P1 程序化交易备案, M17 程序化合规

军规覆盖:
- M3: 审计日志完整 - 所有操作必须记录审计日志
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 滑动窗口统计 (支持多种时间窗口)
- 多账户并发追踪 (线程安全)
- 内存高效的环形缓冲区
- 过期数据自动清理
- 高性能设计 (支持每秒1000+事件)

监管规则 (2025年《期货市场程序化交易管理规定》):
- 5秒内报撤单预警阈值: 50笔
- 单秒高频交易判定: >=300笔
- 单日高频交易判定: >=20000笔

示例:
    >>> from src.compliance.hft_detector.tracker import (
    ...     OrderFrequencyTracker,
    ...     FrequencyMetrics,
    ...     OrderEvent,
    ... )
    >>> tracker = OrderFrequencyTracker()
    >>> tracker.track_order(order)
    >>> metrics = tracker.get_frequency("account_001", window_sec=5)
    >>> print(f"订单频率: {metrics.orders_per_sec}/秒")
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


# ============================================================
# 常量定义
# ============================================================

# 默认配置
DEFAULT_MAX_EVENTS_PER_ACCOUNT = 100000  # 每账户最大事件数
DEFAULT_WINDOW_SECONDS = 5  # 默认统计窗口 (秒)
DEFAULT_CLEANUP_INTERVAL = 60  # 清理间隔 (秒)
DEFAULT_EVENT_TTL = 300  # 事件存活时间 (秒)

# 预警阈值 (2025年监管规则)
WARNING_THRESHOLD_5SEC = 50  # 5秒内报撤单预警阈值
HFT_THRESHOLD_PER_SEC = 300  # 单秒高频交易判定阈值
HFT_THRESHOLD_PER_DAY = 20000  # 单日高频交易判定阈值


class EventType(Enum):
    """订单事件类型枚举."""

    ORDER_SUBMIT = "ORDER_SUBMIT"  # 订单提交
    ORDER_CANCEL = "ORDER_CANCEL"  # 订单撤销
    ORDER_AMEND = "ORDER_AMEND"  # 订单修改
    ORDER_FILL = "ORDER_FILL"  # 订单成交
    ORDER_REJECT = "ORDER_REJECT"  # 订单拒绝


@dataclass(frozen=True, slots=True)
class OrderEvent:
    """订单事件 (不可变).

    使用 frozen=True 和 slots=True 优化内存使用和访问速度。

    属性:
        timestamp: 事件时间戳 (Unix时间)
        event_type: 事件类型
        order_id: 订单ID
        account_id: 账户ID
        strategy_id: 策略ID (可选)
        symbol: 合约代码 (可选)
        direction: 方向 (可选)
        volume: 数量 (可选)
        price: 价格 (可选)
    """

    timestamp: float
    event_type: EventType
    order_id: str
    account_id: str
    strategy_id: str = ""
    symbol: str = ""
    direction: str = ""
    volume: int = 0
    price: float = 0.0

    @property
    def is_order(self) -> bool:
        """是否为下单事件."""
        return self.event_type == EventType.ORDER_SUBMIT

    @property
    def is_cancel(self) -> bool:
        """是否为撤单事件."""
        return self.event_type == EventType.ORDER_CANCEL

    @property
    def is_amend(self) -> bool:
        """是否为改单事件."""
        return self.event_type == EventType.ORDER_AMEND

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "event_type": self.event_type.value,
            "order_id": self.order_id,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "volume": self.volume,
            "price": self.price,
        }


@dataclass(frozen=True, slots=True)
class FrequencyMetrics:
    """频率指标 (不可变).

    属性:
        orders_per_sec: 每秒订单数
        cancels_per_sec: 每秒撤单数
        amends_per_sec: 每秒改单数
        cancel_ratio: 撤单比例 (撤单数/总订单数)
        window_sec: 统计窗口 (秒)
        total_orders: 窗口内总订单数
        total_cancels: 窗口内总撤单数
        total_amends: 窗口内总改单数
        timestamp: 指标计算时间戳
        is_warning: 是否达到预警阈值
        is_hft: 是否达到高频交易阈值
    """

    orders_per_sec: float
    cancels_per_sec: float
    amends_per_sec: float
    cancel_ratio: float
    window_sec: int
    total_orders: int
    total_cancels: int
    total_amends: int
    timestamp: float
    is_warning: bool = False
    is_hft: bool = False

    @property
    def total_events(self) -> int:
        """总事件数."""
        return self.total_orders + self.total_cancels + self.total_amends

    @property
    def events_per_sec(self) -> float:
        """每秒事件数."""
        return self.orders_per_sec + self.cancels_per_sec + self.amends_per_sec

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "orders_per_sec": round(self.orders_per_sec, 2),
            "cancels_per_sec": round(self.cancels_per_sec, 2),
            "amends_per_sec": round(self.amends_per_sec, 2),
            "events_per_sec": round(self.events_per_sec, 2),
            "cancel_ratio": round(self.cancel_ratio, 4),
            "window_sec": self.window_sec,
            "total_orders": self.total_orders,
            "total_cancels": self.total_cancels,
            "total_amends": self.total_amends,
            "total_events": self.total_events,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "is_warning": self.is_warning,
            "is_hft": self.is_hft,
        }


@dataclass
class TrackerConfig:
    """追踪器配置.

    属性:
        max_events_per_account: 每账户最大事件数
        default_window_sec: 默认统计窗口 (秒)
        event_ttl: 事件存活时间 (秒)
        cleanup_interval: 自动清理间隔 (秒)
        warning_threshold_5sec: 5秒预警阈值
        hft_threshold_per_sec: 高频交易阈值 (笔/秒)
        enable_auto_cleanup: 是否启用自动清理
    """

    max_events_per_account: int = DEFAULT_MAX_EVENTS_PER_ACCOUNT
    default_window_sec: int = DEFAULT_WINDOW_SECONDS
    event_ttl: int = DEFAULT_EVENT_TTL
    cleanup_interval: int = DEFAULT_CLEANUP_INTERVAL
    warning_threshold_5sec: int = WARNING_THRESHOLD_5SEC
    hft_threshold_per_sec: int = HFT_THRESHOLD_PER_SEC
    enable_auto_cleanup: bool = True


class RingBuffer:
    """环形缓冲区 - 内存高效的事件存储.

    使用 collections.deque 实现固定大小的环形缓冲区。
    当缓冲区满时，最旧的事件会被自动移除。

    特性:
    - O(1) 的添加和移除操作
    - 固定内存占用
    - 自动过期清理
    """

    __slots__ = ("_buffer", "_maxlen")

    def __init__(self, maxlen: int = DEFAULT_MAX_EVENTS_PER_ACCOUNT) -> None:
        """初始化环形缓冲区.

        参数:
            maxlen: 最大容量
        """
        self._buffer: deque[OrderEvent] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def append(self, event: OrderEvent) -> None:
        """添加事件.

        参数:
            event: 订单事件
        """
        self._buffer.append(event)

    def get_events_in_window(
        self,
        window_start: float,
        window_end: float | None = None,
    ) -> list[OrderEvent]:
        """获取时间窗口内的事件.

        参数:
            window_start: 窗口开始时间
            window_end: 窗口结束时间 (None表示当前时间)

        返回:
            时间窗口内的事件列表
        """
        if window_end is None:
            window_end = time.time()

        # 从最新事件开始查找，因为我们通常查询最近的事件
        result: list[OrderEvent] = []
        for event in reversed(self._buffer):
            if event.timestamp < window_start:
                # 由于事件按时间顺序存储，可以提前退出
                break
            if event.timestamp <= window_end:
                result.append(event)

        return result

    def clear_before(self, timestamp: float) -> int:
        """清除指定时间之前的事件.

        参数:
            timestamp: 截止时间戳

        返回:
            清除的事件数量
        """
        original_len = len(self._buffer)

        # 找到第一个不过期的事件
        while self._buffer and self._buffer[0].timestamp < timestamp:
            self._buffer.popleft()

        return original_len - len(self._buffer)

    def get_latest(self, limit: int = 100) -> list[OrderEvent]:
        """获取最新的事件.

        参数:
            limit: 返回数量限制

        返回:
            最新事件列表
        """
        if limit >= len(self._buffer):
            return list(self._buffer)

        result: list[OrderEvent] = []
        for i, event in enumerate(reversed(self._buffer)):
            if i >= limit:
                break
            result.append(event)

        return result

    def __len__(self) -> int:
        """返回缓冲区大小."""
        return len(self._buffer)

    def __iter__(self) -> Iterator[OrderEvent]:
        """迭代所有事件."""
        return iter(self._buffer)


class AccountTracker:
    """单账户追踪器 - 追踪单个账户的订单活动.

    功能:
    - 存储账户的订单事件
    - 计算频率指标
    - 过期数据清理
    """

    __slots__ = (
        "_account_id",
        "_buffer",
        "_lock",
        "_total_orders",
        "_total_cancels",
        "_total_amends",
        "_last_update",
    )

    def __init__(
        self,
        account_id: str,
        maxlen: int = DEFAULT_MAX_EVENTS_PER_ACCOUNT,
    ) -> None:
        """初始化账户追踪器.

        参数:
            account_id: 账户ID
            maxlen: 最大事件数
        """
        self._account_id = account_id
        self._buffer = RingBuffer(maxlen=maxlen)
        self._lock = threading.Lock()

        # 累计统计 (不受窗口影响)
        self._total_orders: int = 0
        self._total_cancels: int = 0
        self._total_amends: int = 0
        self._last_update: float = 0.0

    @property
    def account_id(self) -> str:
        """账户ID."""
        return self._account_id

    @property
    def total_orders(self) -> int:
        """总订单数 (累计)."""
        return self._total_orders

    @property
    def total_cancels(self) -> int:
        """总撤单数 (累计)."""
        return self._total_cancels

    @property
    def total_amends(self) -> int:
        """总改单数 (累计)."""
        return self._total_amends

    @property
    def last_update(self) -> float:
        """最后更新时间."""
        return self._last_update

    @property
    def event_count(self) -> int:
        """当前缓冲区事件数."""
        return len(self._buffer)

    def track_event(self, event: OrderEvent) -> None:
        """追踪事件.

        参数:
            event: 订单事件
        """
        with self._lock:
            self._buffer.append(event)
            self._last_update = event.timestamp

            # 更新累计统计
            if event.is_order:
                self._total_orders += 1
            elif event.is_cancel:
                self._total_cancels += 1
            elif event.is_amend:
                self._total_amends += 1

    def get_frequency(
        self,
        window_sec: int,
        timestamp: float | None = None,
        warning_threshold: int = WARNING_THRESHOLD_5SEC,
        hft_threshold: int = HFT_THRESHOLD_PER_SEC,
    ) -> FrequencyMetrics:
        """计算频率指标.

        参数:
            window_sec: 统计窗口 (秒)
            timestamp: 计算时间 (None使用当前时间)
            warning_threshold: 预警阈值
            hft_threshold: 高频交易阈值

        返回:
            频率指标
        """
        if timestamp is None:
            timestamp = time.time()

        window_start = timestamp - window_sec

        with self._lock:
            events = self._buffer.get_events_in_window(window_start, timestamp)

        # 统计各类事件数量
        order_count = 0
        cancel_count = 0
        amend_count = 0

        for event in events:
            if event.is_order:
                order_count += 1
            elif event.is_cancel:
                cancel_count += 1
            elif event.is_amend:
                amend_count += 1

        # 计算频率
        orders_per_sec = order_count / window_sec if window_sec > 0 else 0.0
        cancels_per_sec = cancel_count / window_sec if window_sec > 0 else 0.0
        amends_per_sec = amend_count / window_sec if window_sec > 0 else 0.0

        # 计算撤单比例
        total_events = order_count + cancel_count + amend_count
        cancel_ratio = cancel_count / total_events if total_events > 0 else 0.0

        # 判断是否达到阈值
        is_warning = False
        is_hft = False

        # 5秒窗口预警判断
        if window_sec == 5:
            is_warning = (order_count + cancel_count) >= warning_threshold

        # 高频交易判断 (每秒)
        events_per_sec = orders_per_sec + cancels_per_sec + amends_per_sec
        is_hft = events_per_sec >= hft_threshold

        return FrequencyMetrics(
            orders_per_sec=orders_per_sec,
            cancels_per_sec=cancels_per_sec,
            amends_per_sec=amends_per_sec,
            cancel_ratio=cancel_ratio,
            window_sec=window_sec,
            total_orders=order_count,
            total_cancels=cancel_count,
            total_amends=amend_count,
            timestamp=timestamp,
            is_warning=is_warning,
            is_hft=is_hft,
        )

    def get_history(self, limit: int = 100) -> list[OrderEvent]:
        """获取历史事件.

        参数:
            limit: 返回数量限制

        返回:
            事件列表 (最新在前)
        """
        with self._lock:
            return self._buffer.get_latest(limit)

    def clear_expired(self, ttl: int = DEFAULT_EVENT_TTL) -> int:
        """清除过期事件.

        参数:
            ttl: 存活时间 (秒)

        返回:
            清除的事件数量
        """
        cutoff = time.time() - ttl
        with self._lock:
            return self._buffer.clear_before(cutoff)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "account_id": self._account_id,
            "event_count": self.event_count,
            "total_orders": self._total_orders,
            "total_cancels": self._total_cancels,
            "total_amends": self._total_amends,
            "last_update": self._last_update,
            "last_update_iso": (
                datetime.fromtimestamp(self._last_update).isoformat()
                if self._last_update > 0
                else ""
            ),
        }


class OrderFrequencyTracker:
    """订单频率追踪器 - 实时追踪账户订单活动 (军规 M17).

    功能:
    - 滑动窗口统计 (支持多种时间窗口)
    - 多账户并发追踪 (线程安全)
    - 内存高效的环形缓冲区
    - 过期数据自动清理
    - 高性能设计 (支持每秒1000+事件)

    线程安全:
    - 使用读写锁保护共享状态
    - 每个账户有独立的锁
    - 支持高并发读写

    示例:
        >>> tracker = OrderFrequencyTracker()
        >>> # 追踪订单
        >>> event = OrderEvent(
        ...     timestamp=time.time(),
        ...     event_type=EventType.ORDER_SUBMIT,
        ...     order_id="order_001",
        ...     account_id="acc_001",
        ... )
        >>> tracker.track_event(event)
        >>> # 获取频率
        >>> metrics = tracker.get_frequency("acc_001", window_sec=5)
        >>> print(f"订单频率: {metrics.orders_per_sec}/秒")
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: TrackerConfig | None = None,
        audit_callback: Callable[[OrderEvent], None] | None = None,
    ) -> None:
        """初始化订单频率追踪器.

        参数:
            config: 追踪器配置 (None使用默认配置)
            audit_callback: 审计回调函数
        """
        self._config = config or TrackerConfig()
        self._audit_callback = audit_callback

        # 账户追踪器映射
        self._trackers: dict[str, AccountTracker] = {}
        self._lock = threading.RLock()  # 使用可重入锁

        # 统计
        self._total_events: int = 0
        self._total_orders: int = 0
        self._total_cancels: int = 0
        self._total_amends: int = 0
        self._start_time: float = time.time()

        # 自动清理
        self._cleanup_timer: threading.Timer | None = None
        self._last_cleanup: float = 0.0

        if self._config.enable_auto_cleanup:
            self._schedule_cleanup()

    @property
    def config(self) -> TrackerConfig:
        """获取配置."""
        return self._config

    @property
    def account_count(self) -> int:
        """账户数量."""
        with self._lock:
            return len(self._trackers)

    @property
    def total_events(self) -> int:
        """总事件数."""
        return self._total_events

    def _get_or_create_tracker(self, account_id: str) -> AccountTracker:
        """获取或创建账户追踪器.

        参数:
            account_id: 账户ID

        返回:
            账户追踪器
        """
        with self._lock:
            if account_id not in self._trackers:
                self._trackers[account_id] = AccountTracker(
                    account_id=account_id,
                    maxlen=self._config.max_events_per_account,
                )
            return self._trackers[account_id]

    def track_event(self, event: OrderEvent) -> None:
        """追踪订单事件.

        参数:
            event: 订单事件
        """
        tracker = self._get_or_create_tracker(event.account_id)
        tracker.track_event(event)

        # 更新全局统计
        self._total_events += 1
        if event.is_order:
            self._total_orders += 1
        elif event.is_cancel:
            self._total_cancels += 1
        elif event.is_amend:
            self._total_amends += 1

        # 审计回调
        if self._audit_callback:
            try:
                self._audit_callback(event)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")

    def track_order(
        self,
        order_id: str,
        account_id: str,
        strategy_id: str = "",
        symbol: str = "",
        direction: str = "",
        volume: int = 0,
        price: float = 0.0,
        timestamp: float | None = None,
    ) -> None:
        """追踪下单事件 (便捷方法).

        参数:
            order_id: 订单ID
            account_id: 账户ID
            strategy_id: 策略ID
            symbol: 合约代码
            direction: 方向
            volume: 数量
            price: 价格
            timestamp: 时间戳 (None使用当前时间)
        """
        if timestamp is None:
            timestamp = time.time()

        event = OrderEvent(
            timestamp=timestamp,
            event_type=EventType.ORDER_SUBMIT,
            order_id=order_id,
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            direction=direction,
            volume=volume,
            price=price,
        )
        self.track_event(event)

    def track_cancel(
        self,
        order_id: str,
        account_id: str,
        strategy_id: str = "",
        symbol: str = "",
        timestamp: float | None = None,
    ) -> None:
        """追踪撤单事件 (便捷方法).

        参数:
            order_id: 订单ID
            account_id: 账户ID
            strategy_id: 策略ID
            symbol: 合约代码
            timestamp: 时间戳 (None使用当前时间)
        """
        if timestamp is None:
            timestamp = time.time()

        event = OrderEvent(
            timestamp=timestamp,
            event_type=EventType.ORDER_CANCEL,
            order_id=order_id,
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
        )
        self.track_event(event)

    def track_amend(
        self,
        order_id: str,
        account_id: str,
        strategy_id: str = "",
        symbol: str = "",
        volume: int = 0,
        price: float = 0.0,
        timestamp: float | None = None,
    ) -> None:
        """追踪改单事件 (便捷方法).

        参数:
            order_id: 订单ID
            account_id: 账户ID
            strategy_id: 策略ID
            symbol: 合约代码
            volume: 数量
            price: 价格
            timestamp: 时间戳 (None使用当前时间)
        """
        if timestamp is None:
            timestamp = time.time()

        event = OrderEvent(
            timestamp=timestamp,
            event_type=EventType.ORDER_AMEND,
            order_id=order_id,
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=symbol,
            volume=volume,
            price=price,
        )
        self.track_event(event)

    def get_frequency(
        self,
        account_id: str,
        window_sec: int | None = None,
        timestamp: float | None = None,
    ) -> FrequencyMetrics:
        """获取账户频率指标.

        参数:
            account_id: 账户ID
            window_sec: 统计窗口 (秒), None使用默认值
            timestamp: 计算时间 (None使用当前时间)

        返回:
            频率指标
        """
        if window_sec is None:
            window_sec = self._config.default_window_sec

        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            if account_id not in self._trackers:
                # 返回空指标
                return FrequencyMetrics(
                    orders_per_sec=0.0,
                    cancels_per_sec=0.0,
                    amends_per_sec=0.0,
                    cancel_ratio=0.0,
                    window_sec=window_sec,
                    total_orders=0,
                    total_cancels=0,
                    total_amends=0,
                    timestamp=timestamp,
                    is_warning=False,
                    is_hft=False,
                )

            tracker = self._trackers[account_id]

        return tracker.get_frequency(
            window_sec=window_sec,
            timestamp=timestamp,
            warning_threshold=self._config.warning_threshold_5sec,
            hft_threshold=self._config.hft_threshold_per_sec,
        )

    def get_history(
        self,
        account_id: str,
        limit: int = 100,
    ) -> list[OrderEvent]:
        """获取账户历史事件.

        参数:
            account_id: 账户ID
            limit: 返回数量限制

        返回:
            事件列表 (最新在前)
        """
        with self._lock:
            if account_id not in self._trackers:
                return []
            tracker = self._trackers[account_id]

        return tracker.get_history(limit)

    def get_all_accounts(self) -> list[str]:
        """获取所有账户ID.

        返回:
            账户ID列表
        """
        with self._lock:
            return list(self._trackers.keys())

    def get_account_statistics(self, account_id: str) -> dict[str, Any]:
        """获取账户统计信息.

        参数:
            account_id: 账户ID

        返回:
            统计字典
        """
        with self._lock:
            if account_id not in self._trackers:
                return {}
            return self._trackers[account_id].get_statistics()

    def clear_expired(self, ttl: int | None = None) -> int:
        """清除所有账户的过期事件.

        参数:
            ttl: 存活时间 (秒), None使用配置值

        返回:
            清除的事件总数
        """
        if ttl is None:
            ttl = self._config.event_ttl

        total_cleared = 0

        with self._lock:
            for tracker in self._trackers.values():
                total_cleared += tracker.clear_expired(ttl)

            self._last_cleanup = time.time()

        if total_cleared > 0:
            logger.info(f"清理过期事件: {total_cleared}条")

        return total_cleared

    def clear_account(self, account_id: str) -> bool:
        """清除指定账户的追踪数据.

        参数:
            account_id: 账户ID

        返回:
            是否成功 (账户存在)
        """
        with self._lock:
            if account_id in self._trackers:
                del self._trackers[account_id]
                return True
            return False

    def reset(self) -> None:
        """重置追踪器 (清除所有数据)."""
        with self._lock:
            self._trackers.clear()
            self._total_events = 0
            self._total_orders = 0
            self._total_cancels = 0
            self._total_amends = 0
            self._start_time = time.time()

        logger.info("追踪器已重置")

    def get_statistics(self) -> dict[str, Any]:
        """获取全局统计信息.

        返回:
            统计字典
        """
        with self._lock:
            account_count = len(self._trackers)
            total_buffer_size = sum(
                t.event_count for t in self._trackers.values()
            )

        uptime = time.time() - self._start_time
        events_per_sec = self._total_events / uptime if uptime > 0 else 0.0

        return {
            "account_count": account_count,
            "total_events": self._total_events,
            "total_orders": self._total_orders,
            "total_cancels": self._total_cancels,
            "total_amends": self._total_amends,
            "total_buffer_size": total_buffer_size,
            "events_per_sec": round(events_per_sec, 2),
            "uptime_sec": round(uptime, 2),
            "start_time": self._start_time,
            "last_cleanup": self._last_cleanup,
            "config": {
                "max_events_per_account": self._config.max_events_per_account,
                "default_window_sec": self._config.default_window_sec,
                "event_ttl": self._config.event_ttl,
                "cleanup_interval": self._config.cleanup_interval,
                "warning_threshold_5sec": self._config.warning_threshold_5sec,
                "hft_threshold_per_sec": self._config.hft_threshold_per_sec,
            },
            "version": self.VERSION,
        }

    def _schedule_cleanup(self) -> None:
        """调度自动清理."""
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()

        self._cleanup_timer = threading.Timer(
            self._config.cleanup_interval,
            self._auto_cleanup,
        )
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def _auto_cleanup(self) -> None:
        """自动清理回调."""
        try:
            self.clear_expired()
        except Exception as e:
            logger.error(f"自动清理失败: {e}")
        finally:
            if self._config.enable_auto_cleanup:
                self._schedule_cleanup()

    def stop(self) -> None:
        """停止追踪器 (释放资源)."""
        if self._cleanup_timer is not None:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None

        logger.info("追踪器已停止")

    def __enter__(self) -> OrderFrequencyTracker:
        """进入上下文管理器."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文管理器."""
        self.stop()


# ============================================================
# 便捷函数
# ============================================================


def create_tracker(
    config: TrackerConfig | None = None,
    audit_callback: Callable[[OrderEvent], None] | None = None,
) -> OrderFrequencyTracker:
    """创建订单频率追踪器.

    参数:
        config: 追踪器配置
        audit_callback: 审计回调函数

    返回:
        追踪器实例
    """
    return OrderFrequencyTracker(config, audit_callback)


def get_default_config() -> TrackerConfig:
    """获取默认配置.

    返回:
        默认配置
    """
    return TrackerConfig()


__all__ = [
    # 枚举
    "EventType",
    # 数据类
    "OrderEvent",
    "FrequencyMetrics",
    "TrackerConfig",
    # 核心类
    "RingBuffer",
    "AccountTracker",
    "OrderFrequencyTracker",
    # 便捷函数
    "create_tracker",
    "get_default_config",
    # 常量
    "DEFAULT_MAX_EVENTS_PER_ACCOUNT",
    "DEFAULT_WINDOW_SECONDS",
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_EVENT_TTL",
    "WARNING_THRESHOLD_5SEC",
    "HFT_THRESHOLD_PER_SEC",
    "HFT_THRESHOLD_PER_DAY",
]
