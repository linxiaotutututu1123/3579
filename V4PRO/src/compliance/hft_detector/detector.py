"""
高频交易检测器模块 - HFT Detector (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测
- CHINA.COMPLIANCE.THROTTLING: 合规节流机制
- CHINA.COMPLIANCE.AUDIT_LOG: 审计日志记录

军规覆盖:
- M3: 审计日志完整 - 检测结果必须记录审计日志
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 多维度高频交易检测 (订单频率、撤单比例、往返时间)
- 分级限速机制 (警告、严重、阻断)
- 账户级别HFT标识管理
- 实时指标计算与监控
- 审计日志集成

高频交易阈值 (设计规格):
- 订单频率: warning=200, critical=300, block=500 (笔/秒)
- 撤单比例: warning=40%, critical=50%
- 往返时间: <10ms 视为HFT行为指标

示例:
    >>> from src.compliance.hft_detector import (
    ...     HFTDetector,
    ...     OrderFlow,
    ...     ThrottleLevel,
    ... )
    >>> detector = HFTDetector()
    >>> order_flow = OrderFlow(
    ...     account_id="acc_001",
    ...     order_id="order_001",
    ...     event_type="submit",
    ...     timestamp=time.time(),
    ... )
    >>> result = detector.detect_hft_pattern(order_flow)
    >>> if result.is_hft:
    ...     print(f"检测到HFT: {result.detection_reason}")
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

# 导入现有的 ThrottleLevel 枚举
from src.compliance.hft_detector.throttle import ThrottleLevel

logger = logging.getLogger(__name__)


# ============================================================
# 高频交易阈值配置 (设计规格)
# ============================================================

HFT_THRESHOLDS = {
    "order_frequency": {
        "warning": 200,     # 200笔/秒 - 预警级别
        "critical": 300,    # 300笔/秒 - 严重级别
        "block": 500,       # 500笔/秒 - 阻断级别
    },
    "cancel_ratio": {
        "warning": 0.4,     # 40% - 预警级别
        "critical": 0.5,    # 50% - 严重级别 (监管红线)
    },
    "round_trip_time": {
        "hft_indicator": 10,  # <10ms 视为HFT行为指标
    },
}

# 默认检测窗口 (秒)
DEFAULT_WINDOW_SECONDS = 1

# 最大记录数
MAX_RECORDS = 100000


# ============================================================
# 枚举定义
# ============================================================

# 注意: ThrottleLevel 从 throttle 模块导入，包含以下级别:
# - NONE: 无限速，正常交易
# - WARNING: 预警级别，记录日志但允许交易
# - SLOW: 减速级别，间隔100ms
# - CRITICAL: 严重级别，间隔500ms
# - BLOCK: 阻断级别，拒绝新订单


class HFTIndicatorType(Enum):
    """HFT指标类型枚举."""

    ORDER_FREQUENCY = "ORDER_FREQUENCY"      # 订单频率
    CANCEL_RATIO = "CANCEL_RATIO"            # 撤单比例
    ROUND_TRIP_TIME = "ROUND_TRIP_TIME"      # 往返时间
    COMBINED = "COMBINED"                     # 综合判定


class AuditEventType(Enum):
    """审计事件类型枚举."""

    HFT_DETECTED = "HFT_DETECTED"            # 高频交易检测
    HFT_WARNING = "HFT_WARNING"              # 高频预警
    THROTTLE_APPLIED = "THROTTLE_APPLIED"    # 限速应用
    THROTTLE_RELEASED = "THROTTLE_RELEASED"  # 限速解除


# ============================================================
# 数据结构定义
# ============================================================


@dataclass
class OrderFlow:
    """订单流数据结构.

    记录单个订单事件的完整信息，用于HFT检测分析。

    属性:
        account_id: 账户ID
        order_id: 订单ID
        event_type: 事件类型 ("submit", "cancel", "amend", "fill")
        timestamp: 事件时间戳 (Unix时间)
        strategy_id: 策略ID (可选)
        symbol: 合约代码 (可选)
        direction: 方向 ("buy", "sell") (可选)
        price: 价格 (可选)
        volume: 数量 (可选)
        round_trip_ms: 往返时间 (毫秒, 可选)
        source_latency_ms: 源延迟 (毫秒, 可选)
    """

    account_id: str
    order_id: str
    event_type: str
    timestamp: float
    strategy_id: str = ""
    symbol: str = ""
    direction: str = ""
    price: float = 0.0
    volume: int = 0
    round_trip_ms: float = 0.0
    source_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "account_id": self.account_id,
            "order_id": self.order_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "price": self.price,
            "volume": self.volume,
            "round_trip_ms": self.round_trip_ms,
            "source_latency_ms": self.source_latency_ms,
        }


@dataclass
class HFTIndicator:
    """HFT指标详情.

    记录单个HFT检测指标的详细信息。

    属性:
        indicator_type: 指标类型
        current_value: 当前值
        threshold_warning: 预警阈值
        threshold_critical: 严重阈值
        threshold_block: 阻断阈值 (仅订单频率有此阈值)
        level: 触发的限速级别
        message: 描述消息
    """

    indicator_type: HFTIndicatorType
    current_value: float
    threshold_warning: float
    threshold_critical: float
    threshold_block: float = 0.0
    level: ThrottleLevel = ThrottleLevel.NONE
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "indicator_type": self.indicator_type.value,
            "current_value": self.current_value,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "threshold_block": self.threshold_block,
            "level": self.level.value,
            "message": self.message,
        }


@dataclass
class HFTDetectionResult:
    """高频交易检测结果.

    包含HFT检测的完整结果信息。

    属性:
        is_hft: 是否被判定为高频交易
        throttle_level: 建议的限速级别
        order_frequency: 订单频率 (笔/秒)
        cancel_ratio: 撤单比例 (0-1)
        avg_round_trip_ms: 平均往返时间 (毫秒)
        indicators: 各项指标详情列表
        detection_reason: 检测原因描述
        recommendation: 建议措施
        account_id: 账户ID
        detection_time: 检测时间 (ISO格式)
        window_seconds: 检测窗口 (秒)
        total_orders: 窗口内总订单数
        total_cancels: 窗口内总撤单数
        military_rule: 关联军规
    """

    is_hft: bool
    throttle_level: ThrottleLevel = ThrottleLevel.NONE
    order_frequency: float = 0.0
    cancel_ratio: float = 0.0
    avg_round_trip_ms: float = 0.0
    indicators: list[HFTIndicator] = field(default_factory=list)
    detection_reason: str = ""
    recommendation: str = ""
    account_id: str = ""
    detection_time: str = ""
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    total_orders: int = 0
    total_cancels: int = 0
    military_rule: str = "M17"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "is_hft": self.is_hft,
            "throttle_level": self.throttle_level.value,
            "order_frequency": self.order_frequency,
            "cancel_ratio": self.cancel_ratio,
            "avg_round_trip_ms": self.avg_round_trip_ms,
            "indicators": [i.to_dict() for i in self.indicators],
            "detection_reason": self.detection_reason,
            "recommendation": self.recommendation,
            "account_id": self.account_id,
            "detection_time": self.detection_time,
            "window_seconds": self.window_seconds,
            "total_orders": self.total_orders,
            "total_cancels": self.total_cancels,
            "military_rule": self.military_rule,
        }

    def has_warning(self) -> bool:
        """是否有预警级别指标."""
        return any(
            i.level == ThrottleLevel.WARNING for i in self.indicators
        )

    def has_critical(self) -> bool:
        """是否有严重级别指标."""
        return any(
            i.level == ThrottleLevel.CRITICAL for i in self.indicators
        )

    def has_block(self) -> bool:
        """是否有阻断级别指标."""
        return any(
            i.level == ThrottleLevel.BLOCK for i in self.indicators
        )


@dataclass(frozen=True)
class HFTDetectorConfig:
    """HFT检测器配置 (不可变).

    属性:
        order_freq_warning: 订单频率预警阈值 (笔/秒)
        order_freq_critical: 订单频率严重阈值 (笔/秒)
        order_freq_block: 订单频率阻断阈值 (笔/秒)
        cancel_ratio_warning: 撤单比例预警阈值
        cancel_ratio_critical: 撤单比例严重阈值
        round_trip_hft_indicator: 往返时间HFT指标阈值 (毫秒)
        window_seconds: 检测窗口 (秒)
        max_records: 最大记录数
        enable_audit_logging: 是否启用审计日志
        enable_auto_throttle: 是否启用自动限速
    """

    order_freq_warning: int = HFT_THRESHOLDS["order_frequency"]["warning"]
    order_freq_critical: int = HFT_THRESHOLDS["order_frequency"]["critical"]
    order_freq_block: int = HFT_THRESHOLDS["order_frequency"]["block"]
    cancel_ratio_warning: float = HFT_THRESHOLDS["cancel_ratio"]["warning"]
    cancel_ratio_critical: float = HFT_THRESHOLDS["cancel_ratio"]["critical"]
    round_trip_hft_indicator: int = HFT_THRESHOLDS["round_trip_time"]["hft_indicator"]
    window_seconds: int = DEFAULT_WINDOW_SECONDS
    max_records: int = MAX_RECORDS
    enable_audit_logging: bool = True
    enable_auto_throttle: bool = True


@dataclass
class ThrottleState:
    """限速状态.

    记录账户当前的限速状态。

    属性:
        level: 当前限速级别
        applied_at: 应用时间
        reason: 限速原因
        expires_at: 过期时间 (可选)
        delay_ms: 延迟时间 (毫秒)
    """

    level: ThrottleLevel
    applied_at: float
    reason: str
    expires_at: float | None = None
    delay_ms: int = 0

    def is_expired(self, current_time: float | None = None) -> bool:
        """检查限速是否已过期."""
        if self.expires_at is None:
            return False
        if current_time is None:
            current_time = time.time()
        return current_time >= self.expires_at


@dataclass
class AuditLogEntry:
    """审计日志条目 (M3军规).

    必记字段:
    - timestamp: 时间戳
    - event_type: 事件类型
    - operator: 操作者
    - target: 操作目标
    - action: 操作动作
    - result: 操作结果
    - context: 上下文信息

    属性:
        timestamp: ISO格式时间戳
        event_type: 事件类型
        operator: 操作者 (账户ID)
        target: 操作目标
        action: 操作动作描述
        result: 操作结果
        context: 上下文信息
        integrity_hash: 完整性校验哈希
        sequence_id: 序列号
        military_rule: 关联军规
    """

    timestamp: str
    event_type: AuditEventType
    operator: str
    target: str
    action: str
    result: str
    context: dict[str, Any] = field(default_factory=dict)
    integrity_hash: str = ""
    sequence_id: int = 0
    military_rule: str = "M17"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "operator": self.operator,
            "target": self.target,
            "action": self.action,
            "result": self.result,
            "context": self.context,
            "integrity_hash": self.integrity_hash,
            "sequence_id": self.sequence_id,
            "military_rule": self.military_rule,
        }

    def compute_integrity_hash(self) -> str:
        """计算完整性校验哈希."""
        data = json.dumps(
            {
                "timestamp": self.timestamp,
                "event_type": self.event_type.value,
                "operator": self.operator,
                "target": self.target,
                "action": self.action,
                "result": self.result,
                "context": self.context,
                "sequence_id": self.sequence_id,
            },
            sort_keys=True,
        )
        return hashlib.sha256(data.encode()).hexdigest()


# ============================================================
# 主类实现
# ============================================================


class HFTDetector:
    """高频交易检测器 (军规 M17).

    功能:
    - 多维度HFT检测 (订单频率、撤单比例、往返时间)
    - 分级限速机制 (警告、严重、阻断)
    - 账户级别HFT标识管理
    - 实时指标计算与监控
    - 审计日志集成

    检测维度:
    1. 订单频率检测:
       - warning: 200笔/秒
       - critical: 300笔/秒
       - block: 500笔/秒

    2. 撤单比例检测:
       - warning: 40%
       - critical: 50%

    3. 往返时间检测:
       - <10ms视为HFT行为指标

    示例:
        >>> detector = HFTDetector()
        >>> order_flow = OrderFlow(
        ...     account_id="acc_001",
        ...     order_id="order_001",
        ...     event_type="submit",
        ...     timestamp=time.time(),
        ... )
        >>> result = detector.detect_hft_pattern(order_flow)
        >>> if result.is_hft:
        ...     detector.apply_throttle(result.account_id, result.throttle_level)
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: HFTDetectorConfig | None = None,
        audit_callback: Callable[[AuditLogEntry], None] | None = None,
    ) -> None:
        """初始化高频交易检测器.

        参数:
            config: 检测器配置 (None使用默认配置)
            audit_callback: 审计回调函数 (可选)
        """
        self._config = config or HFTDetectorConfig()
        self._audit_callback = audit_callback

        # 按账户存储订单流记录
        self._order_flows: dict[str, deque[OrderFlow]] = {}
        self._lock = threading.Lock()

        # HFT标记账户集合
        self._hft_accounts: set[str] = set()

        # 账户限速状态
        self._throttle_states: dict[str, ThrottleState] = {}

        # 审计序列号
        self._audit_sequence: int = 0

        # 统计
        self._detection_count: int = 0
        self._hft_detection_count: int = 0
        self._throttle_applied_count: int = 0

    @property
    def config(self) -> HFTDetectorConfig:
        """获取配置."""
        return self._config

    @property
    def hft_accounts(self) -> set[str]:
        """获取HFT标记账户集合 (副本)."""
        with self._lock:
            return self._hft_accounts.copy()

    def record_order_flow(self, order_flow: OrderFlow) -> None:
        """记录订单流事件.

        参数:
            order_flow: 订单流数据
        """
        account_id = order_flow.account_id

        with self._lock:
            if account_id not in self._order_flows:
                self._order_flows[account_id] = deque(
                    maxlen=self._config.max_records
                )
            self._order_flows[account_id].append(order_flow)

    def detect_hft_pattern(self, order_flow: OrderFlow) -> HFTDetectionResult:
        """检测高频交易模式.

        这是主检测方法，会自动记录订单流并进行多维度检测。

        参数:
            order_flow: 订单流数据

        返回:
            HFT检测结果
        """
        # 记录订单流
        self.record_order_flow(order_flow)

        account_id = order_flow.account_id
        timestamp = order_flow.timestamp

        self._detection_count += 1

        # 获取检测窗口内的订单流
        window_flows = self._get_window_flows(account_id, timestamp)

        if not window_flows:
            return HFTDetectionResult(
                is_hft=False,
                account_id=account_id,
                detection_time=datetime.now().isoformat(),  # noqa: DTZ005
                window_seconds=self._config.window_seconds,
            )

        # 计算各项指标
        indicators: list[HFTIndicator] = []

        # 1. 订单频率检测
        order_frequency = len(window_flows) / self._config.window_seconds
        freq_indicator = self._check_order_frequency(order_frequency)
        indicators.append(freq_indicator)

        # 2. 撤单比例检测
        cancel_count = sum(1 for f in window_flows if f.event_type == "cancel")
        cancel_ratio = cancel_count / len(window_flows) if window_flows else 0.0
        ratio_indicator = self._check_cancel_ratio(cancel_ratio)
        indicators.append(ratio_indicator)

        # 3. 往返时间检测
        rtt_values = [f.round_trip_ms for f in window_flows if f.round_trip_ms > 0]
        avg_rtt = sum(rtt_values) / len(rtt_values) if rtt_values else 0.0
        rtt_indicator = self._check_round_trip_time(avg_rtt)
        indicators.append(rtt_indicator)

        # 确定最高限速级别
        max_level = ThrottleLevel.NONE
        for indicator in indicators:
            if indicator.level.value > max_level.value:
                max_level = indicator.level

        # 判定是否为HFT
        is_hft = max_level in (ThrottleLevel.CRITICAL, ThrottleLevel.BLOCK)

        # 生成检测原因和建议
        detection_reason = self._generate_detection_reason(indicators, is_hft)
        recommendation = self._generate_recommendation(max_level, indicators)

        # 更新HFT账户标记
        if is_hft:
            self._hft_accounts.add(account_id)
            self._hft_detection_count += 1

        result = HFTDetectionResult(
            is_hft=is_hft,
            throttle_level=max_level,
            order_frequency=order_frequency,
            cancel_ratio=cancel_ratio,
            avg_round_trip_ms=avg_rtt,
            indicators=indicators,
            detection_reason=detection_reason,
            recommendation=recommendation,
            account_id=account_id,
            detection_time=datetime.now().isoformat(),  # noqa: DTZ005
            window_seconds=self._config.window_seconds,
            total_orders=len(window_flows),
            total_cancels=cancel_count,
        )

        # 发送审计日志
        if self._config.enable_audit_logging and is_hft:
            self._emit_audit(
                event_type=AuditEventType.HFT_DETECTED,
                account_id=account_id,
                action="高频交易检测",
                result="DETECTED",
                context=result.to_dict(),
            )
        elif self._config.enable_audit_logging and max_level == ThrottleLevel.WARNING:
            self._emit_audit(
                event_type=AuditEventType.HFT_WARNING,
                account_id=account_id,
                action="高频预警",
                result="WARNING",
                context=result.to_dict(),
            )

        # 自动应用限速
        if self._config.enable_auto_throttle and max_level != ThrottleLevel.NONE:
            self.apply_throttle(account_id, max_level)

        return result

    def get_order_frequency(
        self,
        account_id: str,
        window_sec: int = 1,
        timestamp: float | None = None,
    ) -> int:
        """获取账户订单频率.

        参数:
            account_id: 账户ID
            window_sec: 统计窗口 (秒)
            timestamp: 计算时间 (None使用当前时间)

        返回:
            订单频率 (笔/秒)
        """
        if timestamp is None:
            timestamp = time.time()

        window_flows = self._get_window_flows(account_id, timestamp, window_sec)
        return len(window_flows)

    def get_cancel_ratio(
        self,
        account_id: str,
        window_sec: int = 60,
        timestamp: float | None = None,
    ) -> float:
        """获取账户撤单比例.

        参数:
            account_id: 账户ID
            window_sec: 统计窗口 (秒)
            timestamp: 计算时间 (None使用当前时间)

        返回:
            撤单比例 (0-1)
        """
        if timestamp is None:
            timestamp = time.time()

        window_flows = self._get_window_flows(account_id, timestamp, window_sec)

        if not window_flows:
            return 0.0

        cancel_count = sum(1 for f in window_flows if f.event_type == "cancel")
        return cancel_count / len(window_flows)

    def is_hft_account(self, account_id: str) -> bool:
        """判断是否为HFT账户.

        参数:
            account_id: 账户ID

        返回:
            是否为HFT账户
        """
        with self._lock:
            return account_id in self._hft_accounts

    def apply_throttle(
        self,
        account_id: str,
        level: ThrottleLevel,
        duration_sec: float | None = None,
    ) -> None:
        """应用限速.

        根据限速级别应用相应的延迟或阻断措施。

        参数:
            account_id: 账户ID
            level: 限速级别
            duration_sec: 限速持续时间 (秒, None表示永久)
        """
        current_time = time.time()

        # 计算延迟时间
        delay_ms = self._calculate_delay(level)

        # 计算过期时间
        expires_at = None
        if duration_sec is not None:
            expires_at = current_time + duration_sec

        # 创建限速状态
        state = ThrottleState(
            level=level,
            applied_at=current_time,
            reason=f"HFT检测触发 {level.value} 级别限速",
            expires_at=expires_at,
            delay_ms=delay_ms,
        )

        with self._lock:
            self._throttle_states[account_id] = state

        self._throttle_applied_count += 1

        # 发送审计日志
        if self._config.enable_audit_logging:
            self._emit_audit(
                event_type=AuditEventType.THROTTLE_APPLIED,
                account_id=account_id,
                action=f"应用{level.value}级别限速",
                result="APPLIED",
                context={
                    "level": level.value,
                    "delay_ms": delay_ms,
                    "duration_sec": duration_sec,
                    "expires_at": expires_at,
                },
            )

        logger.info(
            f"账户 {account_id} 应用 {level.value} 级别限速, "
            f"延迟 {delay_ms}ms"
        )

    def release_throttle(self, account_id: str) -> None:
        """解除限速.

        参数:
            account_id: 账户ID
        """
        with self._lock:
            if account_id in self._throttle_states:
                del self._throttle_states[account_id]

        # 发送审计日志
        if self._config.enable_audit_logging:
            self._emit_audit(
                event_type=AuditEventType.THROTTLE_RELEASED,
                account_id=account_id,
                action="解除限速",
                result="RELEASED",
                context={},
            )

        logger.info(f"账户 {account_id} 限速已解除")

    def get_throttle_state(self, account_id: str) -> ThrottleState | None:
        """获取账户限速状态.

        参数:
            account_id: 账户ID

        返回:
            限速状态 (None表示无限速)
        """
        with self._lock:
            state = self._throttle_states.get(account_id)

        if state is None:
            return None

        # 检查是否过期
        if state.is_expired():
            self.release_throttle(account_id)
            return None

        return state

    def should_block(self, account_id: str) -> tuple[bool, str]:
        """判断是否应该阻断订单.

        参数:
            account_id: 账户ID

        返回:
            (是否阻断, 原因消息)
        """
        state = self.get_throttle_state(account_id)

        if state is None:
            return False, ""

        if state.level == ThrottleLevel.BLOCK:
            return True, f"账户 {account_id} 处于阻断状态: {state.reason}"

        return False, ""

    def get_delay_ms(self, account_id: str) -> int:
        """获取账户应延迟的毫秒数.

        参数:
            account_id: 账户ID

        返回:
            延迟毫秒数 (0表示无需延迟)
        """
        state = self.get_throttle_state(account_id)

        if state is None:
            return 0

        return state.delay_ms

    def clear_hft_flag(self, account_id: str) -> None:
        """清除HFT标记.

        参数:
            account_id: 账户ID
        """
        with self._lock:
            self._hft_accounts.discard(account_id)

        logger.info(f"账户 {account_id} HFT标记已清除")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        with self._lock:
            hft_account_count = len(self._hft_accounts)
            throttled_account_count = len(self._throttle_states)
            total_accounts = len(self._order_flows)

        return {
            "detection_count": self._detection_count,
            "hft_detection_count": self._hft_detection_count,
            "hft_detection_rate": (
                self._hft_detection_count / self._detection_count
                if self._detection_count > 0
                else 0.0
            ),
            "throttle_applied_count": self._throttle_applied_count,
            "hft_account_count": hft_account_count,
            "throttled_account_count": throttled_account_count,
            "total_accounts": total_accounts,
            "config": {
                "order_freq_warning": self._config.order_freq_warning,
                "order_freq_critical": self._config.order_freq_critical,
                "order_freq_block": self._config.order_freq_block,
                "cancel_ratio_warning": self._config.cancel_ratio_warning,
                "cancel_ratio_critical": self._config.cancel_ratio_critical,
                "round_trip_hft_indicator": self._config.round_trip_hft_indicator,
                "window_seconds": self._config.window_seconds,
            },
            "version": self.VERSION,
            "military_rule": "M17",
        }

    def reset(self) -> None:
        """重置检测器."""
        with self._lock:
            self._order_flows.clear()
            self._hft_accounts.clear()
            self._throttle_states.clear()

        self._detection_count = 0
        self._hft_detection_count = 0
        self._throttle_applied_count = 0

        logger.info("HFT检测器已重置")

    # ============================================================
    # 内部方法
    # ============================================================

    def _get_window_flows(
        self,
        account_id: str,
        timestamp: float,
        window_sec: int | None = None,
    ) -> list[OrderFlow]:
        """获取检测窗口内的订单流."""
        if window_sec is None:
            window_sec = self._config.window_seconds

        window_start = timestamp - window_sec

        with self._lock:
            if account_id not in self._order_flows:
                return []

            flows = self._order_flows[account_id]
            return [f for f in flows if f.timestamp >= window_start]

    def _check_order_frequency(self, frequency: float) -> HFTIndicator:
        """检查订单频率指标."""
        level = ThrottleLevel.NONE
        message = ""

        if frequency >= self._config.order_freq_block:
            level = ThrottleLevel.BLOCK
            message = (
                f"订单频率严重超限: {frequency:.1f}笔/秒 >= "
                f"{self._config.order_freq_block}笔/秒, 需阻断"
            )
        elif frequency >= self._config.order_freq_critical:
            level = ThrottleLevel.CRITICAL
            message = (
                f"订单频率超限: {frequency:.1f}笔/秒 >= "
                f"{self._config.order_freq_critical}笔/秒, 判定为HFT"
            )
        elif frequency >= self._config.order_freq_warning:
            level = ThrottleLevel.WARNING
            message = (
                f"订单频率接近阈值: {frequency:.1f}笔/秒, "
                f"预警阈值: {self._config.order_freq_warning}笔/秒"
            )
        else:
            message = f"订单频率正常: {frequency:.1f}笔/秒"

        return HFTIndicator(
            indicator_type=HFTIndicatorType.ORDER_FREQUENCY,
            current_value=frequency,
            threshold_warning=float(self._config.order_freq_warning),
            threshold_critical=float(self._config.order_freq_critical),
            threshold_block=float(self._config.order_freq_block),
            level=level,
            message=message,
        )

    def _check_cancel_ratio(self, ratio: float) -> HFTIndicator:
        """检查撤单比例指标."""
        level = ThrottleLevel.NONE
        message = ""

        if ratio >= self._config.cancel_ratio_critical:
            level = ThrottleLevel.CRITICAL
            message = (
                f"撤单比例超限: {ratio:.1%} >= "
                f"{self._config.cancel_ratio_critical:.0%}, 违反监管红线"
            )
        elif ratio >= self._config.cancel_ratio_warning:
            level = ThrottleLevel.WARNING
            message = (
                f"撤单比例接近阈值: {ratio:.1%}, "
                f"预警阈值: {self._config.cancel_ratio_warning:.0%}"
            )
        else:
            message = f"撤单比例正常: {ratio:.1%}"

        return HFTIndicator(
            indicator_type=HFTIndicatorType.CANCEL_RATIO,
            current_value=ratio,
            threshold_warning=self._config.cancel_ratio_warning,
            threshold_critical=self._config.cancel_ratio_critical,
            level=level,
            message=message,
        )

    def _check_round_trip_time(self, avg_rtt: float) -> HFTIndicator:
        """检查往返时间指标."""
        level = ThrottleLevel.NONE
        message = ""

        if avg_rtt > 0 and avg_rtt < self._config.round_trip_hft_indicator:
            level = ThrottleLevel.WARNING
            message = (
                f"往返时间极短: {avg_rtt:.2f}ms < "
                f"{self._config.round_trip_hft_indicator}ms, 疑似HFT行为"
            )
        elif avg_rtt > 0:
            message = f"往返时间正常: {avg_rtt:.2f}ms"
        else:
            message = "无往返时间数据"

        return HFTIndicator(
            indicator_type=HFTIndicatorType.ROUND_TRIP_TIME,
            current_value=avg_rtt,
            threshold_warning=float(self._config.round_trip_hft_indicator),
            threshold_critical=float(self._config.round_trip_hft_indicator),
            level=level,
            message=message,
        )

    def _generate_detection_reason(
        self,
        indicators: list[HFTIndicator],
        is_hft: bool,
    ) -> str:
        """生成检测原因描述."""
        if not is_hft:
            return "交易行为正常，未检测到高频交易特征"

        reasons = []
        for indicator in indicators:
            if indicator.level in (ThrottleLevel.CRITICAL, ThrottleLevel.BLOCK):
                reasons.append(indicator.message)

        return "; ".join(reasons) if reasons else "综合判定为高频交易"

    def _generate_recommendation(
        self,
        level: ThrottleLevel,
        indicators: list[HFTIndicator],
    ) -> str:
        """生成建议措施."""
        if level == ThrottleLevel.NONE:
            return "继续正常交易"

        if level == ThrottleLevel.WARNING:
            return (
                "建议: 1) 适当降低交易频率; "
                "2) 减少不必要的撤单; "
                "3) 关注后续交易行为"
            )

        if level == ThrottleLevel.CRITICAL:
            return (
                "建议: 1) 立即降低交易频率至200笔/秒以下; "
                "2) 检查交易策略是否需要备案; "
                "3) 联系合规部门确认"
            )

        if level == ThrottleLevel.BLOCK:
            return (
                "警告: 订单已被阻断! "
                "1) 立即停止自动交易; "
                "2) 联系合规部门处理; "
                "3) 完成高频交易备案后方可恢复"
            )

        return ""

    def _calculate_delay(self, level: ThrottleLevel) -> int:
        """计算限速延迟时间 (毫秒)."""
        delay_map = {
            ThrottleLevel.NONE: 0,
            ThrottleLevel.WARNING: 50,      # 50ms
            ThrottleLevel.CRITICAL: 200,    # 200ms
            ThrottleLevel.BLOCK: 5000,      # 5000ms (实际应阻断)
        }
        return delay_map.get(level, 0)

    def _emit_audit(
        self,
        event_type: AuditEventType,
        account_id: str,
        action: str,
        result: str,
        context: dict[str, Any],
    ) -> None:
        """发送审计事件."""
        if self._audit_callback is None:
            return

        with self._lock:
            self._audit_sequence += 1
            sequence_id = self._audit_sequence

        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            event_type=event_type,
            operator=account_id,
            target="HFT_DETECTOR",
            action=action,
            result=result,
            context=context,
            sequence_id=sequence_id,
            military_rule="M17",
        )

        # 计算完整性哈希
        entry = AuditLogEntry(
            timestamp=entry.timestamp,
            event_type=entry.event_type,
            operator=entry.operator,
            target=entry.target,
            action=entry.action,
            result=entry.result,
            context=entry.context,
            integrity_hash=entry.compute_integrity_hash(),
            sequence_id=entry.sequence_id,
            military_rule=entry.military_rule,
        )

        try:
            self._audit_callback(entry)
        except Exception as e:
            logger.error(f"审计回调失败: {e}")


# ============================================================
# 便捷函数
# ============================================================


def create_hft_detector(
    config: HFTDetectorConfig | None = None,
    audit_callback: Callable[[AuditLogEntry], None] | None = None,
) -> HFTDetector:
    """创建高频交易检测器.

    参数:
        config: 检测器配置 (None使用默认配置)
        audit_callback: 审计回调函数 (可选)

    返回:
        HFT检测器实例
    """
    return HFTDetector(config, audit_callback)


def get_default_hft_config() -> HFTDetectorConfig:
    """获取默认HFT检测器配置.

    返回:
        默认配置
    """
    return HFTDetectorConfig()


def get_hft_thresholds() -> dict[str, dict[str, int | float]]:
    """获取HFT阈值配置.

    返回:
        阈值配置字典
    """
    return HFT_THRESHOLDS.copy()
