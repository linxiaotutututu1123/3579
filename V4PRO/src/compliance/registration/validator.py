"""
程序化交易合规验证模块 - Validator (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.VALIDATION: 合规阈值验证
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测

军规覆盖:
- M3: 审计日志完整 - 违规事件必须记录审计日志
- M7: 场景回放 - 支持合规检查场景回放
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 报撤单比例监控 (<=50%)
- 撤单频率监控 (<=500次/秒)
- 订单间隔监控 (>=100ms)
- 审计延迟监控 (<=1s)
- 高频交易检测
- 实时合规验证

合规阈值 (D7-P1):
- 报撤单比例: <=50%
- 撤单频率: <=500次/秒
- 订单间隔: >=100ms
- 审计延迟: <=1s

示例:
    >>> from src.compliance.registration.validator import (
    ...     ComplianceValidator,
    ...     OrderFrequencyMonitor,
    ... )
    >>> validator = ComplianceValidator()
    >>> monitor = OrderFrequencyMonitor()
    >>> result = validator.validate_order(order_info)
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class ViolationLevel(Enum):
    """违规级别枚举."""

    INFO = "INFO"  # 信息 - 仅记录
    WARNING = "WARNING"  # 预警 - 接近阈值
    VIOLATION = "VIOLATION"  # 违规 - 超过阈值
    CRITICAL = "CRITICAL"  # 严重 - 严重违规


class ViolationType(Enum):
    """违规类型枚举."""

    CANCEL_RATIO_EXCEEDED = "CANCEL_RATIO_EXCEEDED"  # 报撤单比例超限
    CANCEL_FREQ_EXCEEDED = "CANCEL_FREQ_EXCEEDED"  # 撤单频率超限
    ORDER_INTERVAL_TOO_SHORT = "ORDER_INTERVAL_TOO_SHORT"  # 订单间隔过短
    AUDIT_DELAY_EXCEEDED = "AUDIT_DELAY_EXCEEDED"  # 审计延迟超限
    HFT_DETECTED = "HFT_DETECTED"  # 高频交易检测
    UNREGISTERED_ACCOUNT = "UNREGISTERED_ACCOUNT"  # 未备案账户
    INACTIVE_STRATEGY = "INACTIVE_STRATEGY"  # 策略未激活


@dataclass(frozen=True)
class ComplianceValidatorConfig:
    """合规验证配置 (不可变).

    属性:
        max_cancel_ratio: 最大报撤单比例 (默认0.5, 即50%)
        max_cancel_freq_per_sec: 最大撤单频率 (次/秒, 默认500)
        min_order_interval_ms: 最小订单间隔 (毫秒, 默认100)
        max_audit_delay_sec: 最大审计延迟 (秒, 默认1.0)
        hft_threshold_per_sec: 高频交易判定阈值 (笔/秒, 默认300)
        warning_ratio: 预警比例 (默认0.8)
        enable_hft_detection: 是否启用高频交易检测 (默认True)
        enable_strict_mode: 是否启用严格模式 (默认False)
    """

    max_cancel_ratio: float = 0.50
    max_cancel_freq_per_sec: int = 500
    min_order_interval_ms: int = 100
    max_audit_delay_sec: float = 1.0
    hft_threshold_per_sec: int = 300
    warning_ratio: float = 0.8
    enable_hft_detection: bool = True
    enable_strict_mode: bool = False


@dataclass(frozen=True)
class ViolationDetail:
    """违规详情 (不可变).

    属性:
        violation_type: 违规类型
        violation_level: 违规级别
        message: 违规描述
        threshold: 阈值
        actual_value: 实际值
        account_id: 账户ID
        strategy_id: 策略ID
        timestamp: 时间戳
        military_rule: 关联军规
    """

    violation_type: ViolationType
    violation_level: ViolationLevel
    message: str
    threshold: float
    actual_value: float
    account_id: str = ""
    strategy_id: str = ""
    timestamp: str = ""
    military_rule: str = "M17"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "violation_type": self.violation_type.value,
            "violation_level": self.violation_level.value,
            "message": self.message,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "timestamp": self.timestamp,
            "military_rule": self.military_rule,
        }


@dataclass
class ValidationResult:
    """验证结果.

    属性:
        is_valid: 是否合规
        violations: 违规列表
        warnings: 预警列表
        metrics: 合规指标
        validated_at: 验证时间
    """

    is_valid: bool
    violations: list[ViolationDetail] = field(default_factory=list)
    warnings: list[ViolationDetail] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    validated_at: str = ""

    def has_violations(self) -> bool:
        """是否有违规."""
        return len(self.violations) > 0

    def has_warnings(self) -> bool:
        """是否有预警."""
        return len(self.warnings) > 0

    def get_critical_violations(self) -> list[ViolationDetail]:
        """获取严重违规列表."""
        return [v for v in self.violations if v.violation_level == ViolationLevel.CRITICAL]


@dataclass
class ComplianceMetrics:
    """合规指标.

    属性:
        cancel_ratio: 报撤单比例
        cancel_freq_per_sec: 撤单频率 (次/秒)
        avg_order_interval_ms: 平均订单间隔 (毫秒)
        max_audit_delay_sec: 最大审计延迟 (秒)
        orders_per_sec: 订单频率 (笔/秒)
        is_hft: 是否高频交易
        total_orders: 总订单数
        total_cancels: 总撤单数
        measurement_period_sec: 测量周期 (秒)
    """

    cancel_ratio: float = 0.0
    cancel_freq_per_sec: float = 0.0
    avg_order_interval_ms: float = 0.0
    max_audit_delay_sec: float = 0.0
    orders_per_sec: float = 0.0
    is_hft: bool = False
    total_orders: int = 0
    total_cancels: int = 0
    measurement_period_sec: float = 1.0


@dataclass
class OrderEvent:
    """订单事件.

    属性:
        event_type: 事件类型 ("submit", "cancel", "amend")
        account_id: 账户ID
        strategy_id: 策略ID
        order_id: 订单ID
        symbol: 合约代码
        timestamp: 时间戳
        audit_recorded_at: 审计记录时间
    """

    event_type: str
    account_id: str
    strategy_id: str
    order_id: str
    symbol: str
    timestamp: datetime
    audit_recorded_at: datetime | None = None


class OrderFrequencyMonitor:
    """订单频率监控器 (军规 M17).

    功能:
    - 实时监控订单频率
    - 计算报撤单比例
    - 检测高频交易
    - 计算订单间隔

    示例:
        >>> monitor = OrderFrequencyMonitor()
        >>> monitor.record_order("submit", "acc_001", "strat_001", "order_001")
        >>> metrics = monitor.get_metrics()
        >>> print(f"报撤单比例: {metrics.cancel_ratio:.2%}")
    """

    def __init__(
        self,
        window_seconds: int = 5,
        max_events: int = 100000,
    ) -> None:
        """初始化订单频率监控器.

        参数:
            window_seconds: 滑动窗口大小 (秒)
            max_events: 最大事件数
        """
        self._window_seconds = window_seconds
        self._max_events = max_events

        # 事件队列
        self._events: deque[OrderEvent] = deque(maxlen=max_events)
        self._order_timestamps: deque[float] = deque(maxlen=max_events)

        # 统计
        self._total_orders: int = 0
        self._total_cancels: int = 0
        self._total_amends: int = 0
        self._last_order_time: float | None = None

    @property
    def total_orders(self) -> int:
        """获取总订单数."""
        return self._total_orders

    @property
    def total_cancels(self) -> int:
        """获取总撤单数."""
        return self._total_cancels

    def record_order(
        self,
        event_type: str,
        account_id: str,
        strategy_id: str,
        order_id: str,
        symbol: str = "",
        timestamp: datetime | None = None,
        audit_recorded_at: datetime | None = None,
    ) -> None:
        """记录订单事件.

        参数:
            event_type: 事件类型 ("submit", "cancel", "amend")
            account_id: 账户ID
            strategy_id: 策略ID
            order_id: 订单ID
            symbol: 合约代码
            timestamp: 时间戳
            audit_recorded_at: 审计记录时间
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        event = OrderEvent(
            event_type=event_type,
            account_id=account_id,
            strategy_id=strategy_id,
            order_id=order_id,
            symbol=symbol,
            timestamp=timestamp,
            audit_recorded_at=audit_recorded_at,
        )

        self._events.append(event)
        ts = timestamp.timestamp()
        self._order_timestamps.append(ts)

        # 更新统计
        if event_type == "submit":
            self._total_orders += 1
        elif event_type == "cancel":
            self._total_cancels += 1
            self._total_orders += 1  # 撤单也计入总操作
        elif event_type == "amend":
            self._total_amends += 1
            self._total_orders += 1  # 改单也计入总操作

        self._last_order_time = ts

    def get_metrics(self, timestamp: datetime | None = None) -> ComplianceMetrics:
        """获取合规指标.

        参数:
            timestamp: 计算时间

        返回:
            合规指标
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        now = timestamp.timestamp()
        window_start = now - self._window_seconds

        # 筛选窗口内事件
        window_events = [e for e in self._events if e.timestamp.timestamp() >= window_start]

        if not window_events:
            return ComplianceMetrics(
                measurement_period_sec=self._window_seconds,
            )

        # 计算各项指标
        submit_count = sum(1 for e in window_events if e.event_type == "submit")
        cancel_count = sum(1 for e in window_events if e.event_type == "cancel")
        total_count = len(window_events)

        # 报撤单比例 = 撤单数 / (报单数 + 撤单数)
        cancel_ratio = cancel_count / total_count if total_count > 0 else 0.0

        # 撤单频率 (次/秒)
        cancel_freq = cancel_count / self._window_seconds

        # 订单间隔
        if len(window_events) >= 2:
            intervals = []
            sorted_events = sorted(window_events, key=lambda e: e.timestamp)
            for i in range(1, len(sorted_events)):
                interval = (
                    sorted_events[i].timestamp - sorted_events[i - 1].timestamp
                ).total_seconds() * 1000  # 转换为毫秒
                intervals.append(interval)
            avg_interval = sum(intervals) / len(intervals) if intervals else 0.0
        else:
            avg_interval = 0.0

        # 订单频率 (笔/秒)
        orders_per_sec = total_count / self._window_seconds

        # 审计延迟
        audit_delays = []
        for e in window_events:
            if e.audit_recorded_at:
                delay = (e.audit_recorded_at - e.timestamp).total_seconds()
                audit_delays.append(delay)
        max_audit_delay = max(audit_delays) if audit_delays else 0.0

        # 高频交易判定
        is_hft = orders_per_sec >= 300  # 每秒>=300笔

        return ComplianceMetrics(
            cancel_ratio=cancel_ratio,
            cancel_freq_per_sec=cancel_freq,
            avg_order_interval_ms=avg_interval,
            max_audit_delay_sec=max_audit_delay,
            orders_per_sec=orders_per_sec,
            is_hft=is_hft,
            total_orders=self._total_orders,
            total_cancels=self._total_cancels,
            measurement_period_sec=self._window_seconds,
        )

    def get_cancel_freq_per_sec(self, timestamp: datetime | None = None) -> float:
        """获取撤单频率 (次/秒).

        参数:
            timestamp: 计算时间

        返回:
            撤单频率
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        now = timestamp.timestamp()
        window_start = now - 1.0  # 1秒窗口

        cancel_count = sum(
            1 for e in self._events
            if e.event_type == "cancel" and e.timestamp.timestamp() >= window_start
        )
        return float(cancel_count)

    def get_order_interval_ms(self, timestamp: datetime | None = None) -> float:
        """获取最近订单间隔 (毫秒).

        参数:
            timestamp: 计算时间

        返回:
            订单间隔 (毫秒)
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        if self._last_order_time is None:
            return float("inf")

        interval = (timestamp.timestamp() - self._last_order_time) * 1000
        return interval

    def is_hft(self, timestamp: datetime | None = None) -> bool:
        """判断是否高频交易.

        参数:
            timestamp: 计算时间

        返回:
            是否高频交易
        """
        metrics = self.get_metrics(timestamp)
        return metrics.is_hft

    def reset(self) -> None:
        """重置监控器."""
        self._events.clear()
        self._order_timestamps.clear()
        self._total_orders = 0
        self._total_cancels = 0
        self._total_amends = 0
        self._last_order_time = None


class ComplianceValidator:
    """合规验证器 (军规 M3, M7, M17).

    功能:
    - 报撤单比例验证 (<=50%)
    - 撤单频率验证 (<=500次/秒)
    - 订单间隔验证 (>=100ms)
    - 审计延迟验证 (<=1s)
    - 高频交易检测
    - 综合合规验证

    示例:
        >>> validator = ComplianceValidator()
        >>> result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        >>> if not result.is_valid:
        ...     for v in result.violations:
        ...         print(f"违规: {v.message}")
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: ComplianceValidatorConfig | None = None,
        audit_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """初始化合规验证器.

        参数:
            config: 验证配置 (None使用默认配置)
            audit_callback: 审计回调函数 (可选)
        """
        self._config = config or ComplianceValidatorConfig()
        self._audit_callback = audit_callback
        self._monitor = OrderFrequencyMonitor()

        # 统计
        self._validation_count: int = 0
        self._violation_count: int = 0
        self._warning_count: int = 0

    @property
    def config(self) -> ComplianceValidatorConfig:
        """获取配置."""
        return self._config

    @property
    def monitor(self) -> OrderFrequencyMonitor:
        """获取频率监控器."""
        return self._monitor

    def record_order(
        self,
        event_type: str,
        account_id: str,
        strategy_id: str,
        order_id: str,
        symbol: str = "",
        timestamp: datetime | None = None,
        audit_recorded_at: datetime | None = None,
    ) -> ValidationResult:
        """记录订单并验证合规性.

        参数:
            event_type: 事件类型 ("submit", "cancel", "amend")
            account_id: 账户ID
            strategy_id: 策略ID
            order_id: 订单ID
            symbol: 合约代码
            timestamp: 时间戳
            audit_recorded_at: 审计记录时间

        返回:
            验证结果
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 记录到监控器
        self._monitor.record_order(
            event_type=event_type,
            account_id=account_id,
            strategy_id=strategy_id,
            order_id=order_id,
            symbol=symbol,
            timestamp=timestamp,
            audit_recorded_at=audit_recorded_at,
        )

        # 获取指标并验证
        metrics = self._monitor.get_metrics(timestamp)
        return self.validate_metrics(metrics, account_id, strategy_id, timestamp)

    def validate_metrics(
        self,
        metrics: ComplianceMetrics,
        account_id: str = "",
        strategy_id: str = "",
        timestamp: datetime | None = None,
    ) -> ValidationResult:
        """验证合规指标.

        参数:
            metrics: 合规指标
            account_id: 账户ID
            strategy_id: 策略ID
            timestamp: 验证时间

        返回:
            验证结果
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        self._validation_count += 1
        violations: list[ViolationDetail] = []
        warnings: list[ViolationDetail] = []

        # 1. 检查报撤单比例 (<=50%)
        cancel_ratio_result = self._check_cancel_ratio(
            metrics.cancel_ratio, account_id, strategy_id, timestamp
        )
        if cancel_ratio_result:
            if cancel_ratio_result.violation_level == ViolationLevel.WARNING:
                warnings.append(cancel_ratio_result)
            else:
                violations.append(cancel_ratio_result)

        # 2. 检查撤单频率 (<=500次/秒)
        cancel_freq_result = self._check_cancel_freq(
            metrics.cancel_freq_per_sec, account_id, strategy_id, timestamp
        )
        if cancel_freq_result:
            if cancel_freq_result.violation_level == ViolationLevel.WARNING:
                warnings.append(cancel_freq_result)
            else:
                violations.append(cancel_freq_result)

        # 3. 检查订单间隔 (>=100ms)
        if metrics.avg_order_interval_ms > 0:
            interval_result = self._check_order_interval(
                metrics.avg_order_interval_ms, account_id, strategy_id, timestamp
            )
            if interval_result:
                if interval_result.violation_level == ViolationLevel.WARNING:
                    warnings.append(interval_result)
                else:
                    violations.append(interval_result)

        # 4. 检查审计延迟 (<=1s)
        if metrics.max_audit_delay_sec > 0:
            audit_delay_result = self._check_audit_delay(
                metrics.max_audit_delay_sec, account_id, strategy_id, timestamp
            )
            if audit_delay_result:
                if audit_delay_result.violation_level == ViolationLevel.WARNING:
                    warnings.append(audit_delay_result)
                else:
                    violations.append(audit_delay_result)

        # 5. 检查高频交易
        if self._config.enable_hft_detection and metrics.is_hft:
            hft_result = ViolationDetail(
                violation_type=ViolationType.HFT_DETECTED,
                violation_level=ViolationLevel.WARNING,
                message=f"检测到高频交易行为: {metrics.orders_per_sec:.1f}笔/秒, 需备案",
                threshold=float(self._config.hft_threshold_per_sec),
                actual_value=metrics.orders_per_sec,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
            warnings.append(hft_result)

        # 更新统计
        self._violation_count += len(violations)
        self._warning_count += len(warnings)

        # 构建结果
        is_valid = len(violations) == 0 or not self._config.enable_strict_mode
        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            metrics={
                "cancel_ratio": metrics.cancel_ratio,
                "cancel_freq_per_sec": metrics.cancel_freq_per_sec,
                "avg_order_interval_ms": metrics.avg_order_interval_ms,
                "max_audit_delay_sec": metrics.max_audit_delay_sec,
                "orders_per_sec": metrics.orders_per_sec,
                "is_hft": 1.0 if metrics.is_hft else 0.0,
            },
            validated_at=timestamp.isoformat(),
        )

        # 发送审计事件
        if violations:
            self._emit_audit_event(
                event_type="COMPLIANCE_VIOLATION",
                account_id=account_id,
                strategy_id=strategy_id,
                violations=violations,
                timestamp=timestamp,
            )

        return result

    def validate_order_interval(
        self,
        account_id: str = "",
        strategy_id: str = "",
        timestamp: datetime | None = None,
    ) -> ValidationResult:
        """验证订单间隔.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            timestamp: 验证时间

        返回:
            验证结果
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        interval = self._monitor.get_order_interval_ms(timestamp)
        violations: list[ViolationDetail] = []
        warnings: list[ViolationDetail] = []

        result = self._check_order_interval(interval, account_id, strategy_id, timestamp)
        if result:
            if result.violation_level == ViolationLevel.WARNING:
                warnings.append(result)
            else:
                violations.append(result)

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            metrics={"order_interval_ms": interval},
            validated_at=timestamp.isoformat(),
        )

    def get_current_metrics(self, timestamp: datetime | None = None) -> ComplianceMetrics:
        """获取当前合规指标.

        参数:
            timestamp: 计算时间

        返回:
            合规指标
        """
        return self._monitor.get_metrics(timestamp)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "validation_count": self._validation_count,
            "violation_count": self._violation_count,
            "warning_count": self._warning_count,
            "violation_rate": (
                self._violation_count / self._validation_count
                if self._validation_count > 0
                else 0.0
            ),
            "total_orders": self._monitor.total_orders,
            "total_cancels": self._monitor.total_cancels,
            "validator_version": self.VERSION,
        }

    def reset(self) -> None:
        """重置验证器."""
        self._monitor.reset()
        self._validation_count = 0
        self._violation_count = 0
        self._warning_count = 0

    def _check_cancel_ratio(
        self,
        cancel_ratio: float,
        account_id: str,
        strategy_id: str,
        timestamp: datetime,
    ) -> ViolationDetail | None:
        """检查报撤单比例."""
        max_ratio = self._config.max_cancel_ratio
        warning_threshold = max_ratio * self._config.warning_ratio

        if cancel_ratio >= max_ratio:
            return ViolationDetail(
                violation_type=ViolationType.CANCEL_RATIO_EXCEEDED,
                violation_level=ViolationLevel.VIOLATION,
                message=f"报撤单比例超限: {cancel_ratio:.1%} > {max_ratio:.0%}",
                threshold=max_ratio,
                actual_value=cancel_ratio,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        if cancel_ratio >= warning_threshold:
            return ViolationDetail(
                violation_type=ViolationType.CANCEL_RATIO_EXCEEDED,
                violation_level=ViolationLevel.WARNING,
                message=f"报撤单比例接近限制: {cancel_ratio:.1%}, 限制: {max_ratio:.0%}",
                threshold=max_ratio,
                actual_value=cancel_ratio,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        return None

    def _check_cancel_freq(
        self,
        cancel_freq: float,
        account_id: str,
        strategy_id: str,
        timestamp: datetime,
    ) -> ViolationDetail | None:
        """检查撤单频率."""
        max_freq = self._config.max_cancel_freq_per_sec
        warning_threshold = max_freq * self._config.warning_ratio

        if cancel_freq >= max_freq:
            return ViolationDetail(
                violation_type=ViolationType.CANCEL_FREQ_EXCEEDED,
                violation_level=ViolationLevel.CRITICAL,
                message=f"撤单频率超限: {cancel_freq:.0f}次/秒 > {max_freq}次/秒",
                threshold=float(max_freq),
                actual_value=cancel_freq,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        if cancel_freq >= warning_threshold:
            return ViolationDetail(
                violation_type=ViolationType.CANCEL_FREQ_EXCEEDED,
                violation_level=ViolationLevel.WARNING,
                message=f"撤单频率接近限制: {cancel_freq:.0f}次/秒, 限制: {max_freq}次/秒",
                threshold=float(max_freq),
                actual_value=cancel_freq,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        return None

    def _check_order_interval(
        self,
        interval_ms: float,
        account_id: str,
        strategy_id: str,
        timestamp: datetime,
    ) -> ViolationDetail | None:
        """检查订单间隔."""
        min_interval = self._config.min_order_interval_ms
        warning_threshold = min_interval / self._config.warning_ratio

        if interval_ms < min_interval:
            return ViolationDetail(
                violation_type=ViolationType.ORDER_INTERVAL_TOO_SHORT,
                violation_level=ViolationLevel.VIOLATION,
                message=f"订单间隔过短: {interval_ms:.0f}ms < {min_interval}ms",
                threshold=float(min_interval),
                actual_value=interval_ms,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        if interval_ms < warning_threshold:
            return ViolationDetail(
                violation_type=ViolationType.ORDER_INTERVAL_TOO_SHORT,
                violation_level=ViolationLevel.WARNING,
                message=f"订单间隔接近下限: {interval_ms:.0f}ms, 下限: {min_interval}ms",
                threshold=float(min_interval),
                actual_value=interval_ms,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M17",
            )
        return None

    def _check_audit_delay(
        self,
        delay_sec: float,
        account_id: str,
        strategy_id: str,
        timestamp: datetime,
    ) -> ViolationDetail | None:
        """检查审计延迟."""
        max_delay = self._config.max_audit_delay_sec
        warning_threshold = max_delay * self._config.warning_ratio

        if delay_sec > max_delay:
            return ViolationDetail(
                violation_type=ViolationType.AUDIT_DELAY_EXCEEDED,
                violation_level=ViolationLevel.VIOLATION,
                message=f"审计延迟超限: {delay_sec:.2f}s > {max_delay}s",
                threshold=max_delay,
                actual_value=delay_sec,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M3",
            )
        if delay_sec > warning_threshold:
            return ViolationDetail(
                violation_type=ViolationType.AUDIT_DELAY_EXCEEDED,
                violation_level=ViolationLevel.WARNING,
                message=f"审计延迟接近限制: {delay_sec:.2f}s, 限制: {max_delay}s",
                threshold=max_delay,
                actual_value=delay_sec,
                account_id=account_id,
                strategy_id=strategy_id,
                timestamp=timestamp.isoformat(),
                military_rule="M3",
            )
        return None

    def _emit_audit_event(
        self,
        event_type: str,
        account_id: str,
        strategy_id: str,
        violations: list[ViolationDetail],
        timestamp: datetime,
    ) -> None:
        """发送审计事件."""
        if self._audit_callback:
            event = {
                "event_type": event_type,
                "account_id": account_id,
                "strategy_id": strategy_id,
                "violations": [v.to_dict() for v in violations],
                "timestamp": timestamp.isoformat(),
                "module": "compliance.registration.validator",
                "military_rules": ["M3", "M7", "M17"],
            }
            try:
                self._audit_callback(event)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")


# ============================================================
# 便捷函数
# ============================================================


def create_compliance_validator(
    config: ComplianceValidatorConfig | None = None,
    audit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ComplianceValidator:
    """创建合规验证器.

    参数:
        config: 验证配置 (None使用默认配置)
        audit_callback: 审计回调函数 (可选)

    返回:
        合规验证器实例
    """
    return ComplianceValidator(config, audit_callback)


def create_order_frequency_monitor(
    window_seconds: int = 5,
    max_events: int = 100000,
) -> OrderFrequencyMonitor:
    """创建订单频率监控器.

    参数:
        window_seconds: 滑动窗口大小 (秒)
        max_events: 最大事件数

    返回:
        订单频率监控器实例
    """
    return OrderFrequencyMonitor(window_seconds, max_events)
