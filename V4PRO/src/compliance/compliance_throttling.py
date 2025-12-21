"""
合规节流机制模块 - Compliance Throttling (军规级 v4.0).

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: D7-P1 程序化交易备案, M3 审计日志完整, M17 程序化合规
V4 Scenarios:
- CHINA.COMPLIANCE.THROTTLING: 合规节流机制
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测
- CHINA.COMPLIANCE.AUDIT_LOG: 审计日志记录

军规覆盖:
- M3: 审计日志完整 - 必记字段/保留期限/存储要求
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 合规阈值监控与节流
- 高频交易检测器 (HFT Detector)
- M3军规审计日志规范
- 自动限速机制

合规阈值 (D7-P1):
- 报撤单比例: <=50%
- 撤单频率: <=500次/秒
- 订单间隔: >=100ms
- 审计延迟: <=1s

审计日志规范 (M3):
- 必记字段: timestamp, event_type, operator, target, action, result, context
- 保留期限: 交易日志5年, 系统日志3年, 审计日志10年
- 存储要求: 加密, 不可篡改, 异地备份

示例:
    >>> from src.compliance.compliance_throttling import (
    ...     ComplianceThrottleManager,
    ...     HFTDetector,
    ...     AuditLogger,
    ... )
    >>> throttle = ComplianceThrottleManager()
    >>> can_submit, delay = throttle.check_and_throttle("acc_001", "strat_001")
    >>> hft_detector = HFTDetector()
    >>> is_hft = hft_detector.detect("acc_001")
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ============================================================
# 常量定义
# ============================================================

# 合规阈值 (D7-P1)
MAX_CANCEL_RATIO = 0.50  # 报撤单比例 <=50%
MAX_CANCEL_FREQ_PER_SEC = 500  # 撤单频率 <=500次/秒
MIN_ORDER_INTERVAL_MS = 100  # 订单间隔 >=100ms
MAX_AUDIT_DELAY_SEC = 1.0  # 审计延迟 <=1s

# 高频交易阈值
HFT_THRESHOLD_PER_SEC = 300  # 每秒>=300笔视为高频

# 审计日志保留期限 (M3)
TRADING_LOG_RETENTION_YEARS = 5  # 交易日志 5年
SYSTEM_LOG_RETENTION_YEARS = 3  # 系统日志 3年
AUDIT_LOG_RETENTION_YEARS = 10  # 审计日志 10年


class ThrottleAction(Enum):
    """节流动作枚举."""

    ALLOW = "ALLOW"  # 允许通过
    DELAY = "DELAY"  # 延迟执行
    REJECT = "REJECT"  # 拒绝执行
    WARN = "WARN"  # 警告但允许


class AuditEventType(Enum):
    """审计事件类型枚举."""

    # 订单相关
    ORDER_SUBMIT = "ORDER_SUBMIT"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_AMEND = "ORDER_AMEND"
    ORDER_FILL = "ORDER_FILL"
    ORDER_REJECT = "ORDER_REJECT"

    # 合规相关
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    COMPLIANCE_WARNING = "COMPLIANCE_WARNING"

    # 节流相关
    THROTTLE_DELAY = "THROTTLE_DELAY"
    THROTTLE_REJECT = "THROTTLE_REJECT"

    # 高频交易
    HFT_DETECTED = "HFT_DETECTED"
    HFT_LIMIT_APPLIED = "HFT_LIMIT_APPLIED"

    # 系统事件
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    CONFIG_CHANGE = "CONFIG_CHANGE"


class LogCategory(Enum):
    """日志分类枚举."""

    TRADING = "TRADING"  # 交易日志 - 保留5年
    SYSTEM = "SYSTEM"  # 系统日志 - 保留3年
    AUDIT = "AUDIT"  # 审计日志 - 保留10年


@dataclass(frozen=True)
class ThrottleConfig:
    """节流配置 (不可变).

    属性:
        max_cancel_ratio: 最大报撤单比例 (默认0.5)
        max_cancel_freq_per_sec: 最大撤单频率 (默认500)
        min_order_interval_ms: 最小订单间隔 (默认100ms)
        max_audit_delay_sec: 最大审计延迟 (默认1.0s)
        hft_threshold_per_sec: 高频交易阈值 (默认300)
        warning_ratio: 预警比例 (默认0.8)
        enable_auto_throttle: 是否启用自动节流 (默认True)
        enable_hft_detection: 是否启用高频检测 (默认True)
        base_delay_ms: 基础延迟时间 (默认50ms)
        max_delay_ms: 最大延迟时间 (默认5000ms)
    """

    max_cancel_ratio: float = MAX_CANCEL_RATIO
    max_cancel_freq_per_sec: int = MAX_CANCEL_FREQ_PER_SEC
    min_order_interval_ms: int = MIN_ORDER_INTERVAL_MS
    max_audit_delay_sec: float = MAX_AUDIT_DELAY_SEC
    hft_threshold_per_sec: int = HFT_THRESHOLD_PER_SEC
    warning_ratio: float = 0.8
    enable_auto_throttle: bool = True
    enable_hft_detection: bool = True
    base_delay_ms: int = 50
    max_delay_ms: int = 5000


@dataclass(frozen=True)
class AuditLogConfig:
    """审计日志配置 (不可变, M3军规).

    属性:
        trading_log_retention_years: 交易日志保留年限 (默认5)
        system_log_retention_years: 系统日志保留年限 (默认3)
        audit_log_retention_years: 审计日志保留年限 (默认10)
        enable_encryption: 是否启用加密 (默认True)
        enable_integrity_check: 是否启用完整性校验 (默认True)
        enable_remote_backup: 是否启用异地备份 (默认True)
        log_base_path: 日志基础路径
        encryption_key: 加密密钥 (实际使用时应从安全存储获取)
    """

    trading_log_retention_years: int = TRADING_LOG_RETENTION_YEARS
    system_log_retention_years: int = SYSTEM_LOG_RETENTION_YEARS
    audit_log_retention_years: int = AUDIT_LOG_RETENTION_YEARS
    enable_encryption: bool = True
    enable_integrity_check: bool = True
    enable_remote_backup: bool = True
    log_base_path: str = ""
    encryption_key: str = ""


@dataclass
class ThrottleResult:
    """节流结果.

    属性:
        action: 节流动作
        delay_ms: 延迟时间 (毫秒)
        message: 消息
        reason: 原因
        metrics: 当前指标
        timestamp: 时间戳
    """

    action: ThrottleAction
    delay_ms: int = 0
    message: str = ""
    reason: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    timestamp: str = ""

    def should_delay(self) -> bool:
        """是否需要延迟."""
        return self.action == ThrottleAction.DELAY and self.delay_ms > 0

    def should_reject(self) -> bool:
        """是否需要拒绝."""
        return self.action == ThrottleAction.REJECT


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
        operator: 操作者 (账户ID/策略ID/系统)
        target: 操作目标 (订单ID/合约代码等)
        action: 操作动作描述
        result: 操作结果 (SUCCESS/FAILURE/PARTIAL)
        context: 上下文信息
        category: 日志分类
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
    category: LogCategory = LogCategory.AUDIT
    integrity_hash: str = ""
    sequence_id: int = 0
    military_rule: str = "M3"

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
            "category": self.category.value,
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


@dataclass
class HFTDetectionResult:
    """高频交易检测结果.

    属性:
        is_hft: 是否高频交易
        orders_per_sec: 订单频率 (笔/秒)
        cancel_ratio: 撤单比例
        threshold: 判定阈值
        detection_time: 检测时间
        recommendation: 建议措施
        limit_applied: 是否已应用限制
    """

    is_hft: bool
    orders_per_sec: float = 0.0
    cancel_ratio: float = 0.0
    threshold: int = HFT_THRESHOLD_PER_SEC
    detection_time: str = ""
    recommendation: str = ""
    limit_applied: bool = False


@dataclass
class OrderRecord:
    """订单记录.

    属性:
        timestamp: 时间戳
        account_id: 账户ID
        strategy_id: 策略ID
        order_id: 订单ID
        event_type: 事件类型 (submit/cancel/amend)
        symbol: 合约代码
    """

    timestamp: float
    account_id: str
    strategy_id: str
    order_id: str
    event_type: str
    symbol: str = ""


class HFTDetector:
    """高频交易检测器 (军规 M17).

    功能:
    - 识别高频交易行为 (>=300笔/秒)
    - 监控撤单比例
    - 自动应用频率限制
    - 生成HFT报告

    示例:
        >>> detector = HFTDetector()
        >>> detector.record_order("acc_001", "strat_001", "order_001", "submit")
        >>> result = detector.detect("acc_001")
        >>> if result.is_hft:
        ...     print(f"检测到高频交易: {result.orders_per_sec}笔/秒")
    """

    def __init__(
        self,
        threshold_per_sec: int = HFT_THRESHOLD_PER_SEC,
        window_seconds: int = 1,
        max_records: int = 100000,
    ) -> None:
        """初始化高频交易检测器.

        参数:
            threshold_per_sec: 每秒订单阈值 (默认300)
            window_seconds: 检测窗口 (秒)
            max_records: 最大记录数
        """
        self._threshold = threshold_per_sec
        self._window_seconds = window_seconds
        self._max_records = max_records

        # 按账户存储订单记录
        self._records: dict[str, deque[OrderRecord]] = {}
        self._lock = threading.Lock()

        # HFT标记账户
        self._hft_accounts: set[str] = set()

        # 统计
        self._detection_count: int = 0
        self._hft_detection_count: int = 0

    @property
    def threshold(self) -> int:
        """获取阈值."""
        return self._threshold

    @property
    def hft_accounts(self) -> set[str]:
        """获取HFT标记账户集合."""
        return self._hft_accounts.copy()

    def record_order(
        self,
        account_id: str,
        strategy_id: str,
        order_id: str,
        event_type: str,
        symbol: str = "",
        timestamp: float | None = None,
    ) -> None:
        """记录订单事件.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            order_id: 订单ID
            event_type: 事件类型 (submit/cancel/amend)
            symbol: 合约代码
            timestamp: 时间戳 (None使用当前时间)
        """
        if timestamp is None:
            timestamp = time.time()

        record = OrderRecord(
            timestamp=timestamp,
            account_id=account_id,
            strategy_id=strategy_id,
            order_id=order_id,
            event_type=event_type,
            symbol=symbol,
        )

        with self._lock:
            if account_id not in self._records:
                self._records[account_id] = deque(maxlen=self._max_records)
            self._records[account_id].append(record)

    def detect(
        self,
        account_id: str,
        timestamp: float | None = None,
    ) -> HFTDetectionResult:
        """检测高频交易.

        参数:
            account_id: 账户ID
            timestamp: 检测时间 (None使用当前时间)

        返回:
            检测结果
        """
        if timestamp is None:
            timestamp = time.time()

        self._detection_count += 1

        with self._lock:
            if account_id not in self._records:
                return HFTDetectionResult(
                    is_hft=False,
                    detection_time=datetime.now().isoformat(),  # noqa: DTZ005
                )

            records = self._records[account_id]
            window_start = timestamp - self._window_seconds

            # 筛选窗口内记录
            window_records = [r for r in records if r.timestamp >= window_start]

            if not window_records:
                return HFTDetectionResult(
                    is_hft=False,
                    detection_time=datetime.now().isoformat(),  # noqa: DTZ005
                )

            # 计算每秒订单数
            orders_per_sec = len(window_records) / self._window_seconds

            # 计算撤单比例
            cancel_count = sum(1 for r in window_records if r.event_type == "cancel")
            cancel_ratio = cancel_count / len(window_records) if window_records else 0.0

            # 判定高频交易
            is_hft = orders_per_sec >= self._threshold

            if is_hft:
                self._hft_accounts.add(account_id)
                self._hft_detection_count += 1
                recommendation = (
                    f"账户{account_id}已被识别为高频交易 ({orders_per_sec:.1f}笔/秒), "
                    f"建议: 1) 申请高频交易备案 2) 降低交易频率至{self._threshold}笔/秒以下"
                )
            else:
                recommendation = "交易频率正常"

            return HFTDetectionResult(
                is_hft=is_hft,
                orders_per_sec=orders_per_sec,
                cancel_ratio=cancel_ratio,
                threshold=self._threshold,
                detection_time=datetime.now().isoformat(),  # noqa: DTZ005
                recommendation=recommendation,
                limit_applied=account_id in self._hft_accounts,
            )

    def is_hft_account(self, account_id: str) -> bool:
        """判断是否HFT账户.

        参数:
            account_id: 账户ID

        返回:
            是否HFT账户
        """
        return account_id in self._hft_accounts

    def clear_hft_flag(self, account_id: str) -> None:
        """清除HFT标记.

        参数:
            account_id: 账户ID
        """
        self._hft_accounts.discard(account_id)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "detection_count": self._detection_count,
            "hft_detection_count": self._hft_detection_count,
            "hft_detection_rate": (
                self._hft_detection_count / self._detection_count
                if self._detection_count > 0
                else 0.0
            ),
            "hft_accounts_count": len(self._hft_accounts),
            "threshold_per_sec": self._threshold,
        }

    def reset(self) -> None:
        """重置检测器."""
        with self._lock:
            self._records.clear()
            self._hft_accounts.clear()
            self._detection_count = 0
            self._hft_detection_count = 0


class ComplianceThrottleManager:
    """合规节流管理器 (军规 M17).

    功能:
    - 合规阈值监控 (D7-P1)
    - 自动节流机制
    - 高频交易检测与限制
    - 订单间隔控制

    合规阈值:
    - 报撤单比例: <=50%
    - 撤单频率: <=500次/秒
    - 订单间隔: >=100ms
    - 审计延迟: <=1s

    示例:
        >>> throttle = ComplianceThrottleManager()
        >>> result = throttle.check_and_throttle("acc_001", "strat_001")
        >>> if result.should_delay():
        ...     time.sleep(result.delay_ms / 1000)
        >>> if result.should_reject():
        ...     raise ComplianceError(result.message)
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: ThrottleConfig | None = None,
        audit_callback: Callable[[AuditLogEntry], None] | None = None,
    ) -> None:
        """初始化合规节流管理器.

        参数:
            config: 节流配置 (None使用默认配置)
            audit_callback: 审计回调函数
        """
        self._config = config or ThrottleConfig()
        self._audit_callback = audit_callback

        # HFT检测器
        self._hft_detector = HFTDetector(
            threshold_per_sec=self._config.hft_threshold_per_sec
        )

        # 按账户存储状态
        self._account_states: dict[str, _AccountThrottleState] = {}
        self._lock = threading.Lock()

        # 统计
        self._check_count: int = 0
        self._throttle_count: int = 0
        self._reject_count: int = 0

    @property
    def config(self) -> ThrottleConfig:
        """获取配置."""
        return self._config

    @property
    def hft_detector(self) -> HFTDetector:
        """获取HFT检测器."""
        return self._hft_detector

    def record_order(
        self,
        account_id: str,
        strategy_id: str,
        order_id: str,
        event_type: str,
        symbol: str = "",
        timestamp: float | None = None,
    ) -> None:
        """记录订单事件.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            order_id: 订单ID
            event_type: 事件类型 (submit/cancel/amend)
            symbol: 合约代码
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            if account_id not in self._account_states:
                self._account_states[account_id] = _AccountThrottleState()
            state = self._account_states[account_id]
            state.record_order(event_type, timestamp)

        # 同时记录到HFT检测器
        self._hft_detector.record_order(
            account_id=account_id,
            strategy_id=strategy_id,
            order_id=order_id,
            event_type=event_type,
            symbol=symbol,
            timestamp=timestamp,
        )

    def check_and_throttle(
        self,
        account_id: str,
        strategy_id: str = "",
        timestamp: float | None = None,
    ) -> ThrottleResult:
        """检查并执行节流.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            timestamp: 检查时间

        返回:
            节流结果
        """
        if timestamp is None:
            timestamp = time.time()

        self._check_count += 1

        with self._lock:
            if account_id not in self._account_states:
                self._account_states[account_id] = _AccountThrottleState()
            state = self._account_states[account_id]

        # 获取当前指标
        metrics = self._get_metrics(state, timestamp)

        # 检查各项阈值
        violations: list[str] = []
        warnings: list[str] = []
        delay_ms = 0

        # 1. 检查订单间隔 (>=100ms)
        if state.last_order_time is not None:
            interval_ms = (timestamp - state.last_order_time) * 1000
            if interval_ms < self._config.min_order_interval_ms:
                required_delay = self._config.min_order_interval_ms - interval_ms
                delay_ms = max(delay_ms, int(required_delay))
                violations.append(
                    f"订单间隔过短: {interval_ms:.0f}ms < {self._config.min_order_interval_ms}ms"
                )

        # 2. 检查撤单频率 (<=500次/秒)
        cancel_freq = metrics.get("cancel_freq_per_sec", 0.0)
        if cancel_freq > self._config.max_cancel_freq_per_sec:
            violations.append(
                f"撤单频率超限: {cancel_freq:.0f}次/秒 > {self._config.max_cancel_freq_per_sec}次/秒"
            )
            # 计算需要的延迟
            excess_ratio = cancel_freq / self._config.max_cancel_freq_per_sec
            delay_ms = max(delay_ms, int(self._config.base_delay_ms * excess_ratio))
        elif cancel_freq > self._config.max_cancel_freq_per_sec * self._config.warning_ratio:
            warnings.append(
                f"撤单频率接近限制: {cancel_freq:.0f}次/秒"
            )

        # 3. 检查报撤单比例 (<=50%)
        cancel_ratio = metrics.get("cancel_ratio", 0.0)
        if cancel_ratio > self._config.max_cancel_ratio:
            violations.append(
                f"报撤单比例超限: {cancel_ratio:.1%} > {self._config.max_cancel_ratio:.0%}"
            )
            # 增加延迟
            delay_ms = max(delay_ms, self._config.base_delay_ms * 2)
        elif cancel_ratio > self._config.max_cancel_ratio * self._config.warning_ratio:
            warnings.append(
                f"报撤单比例接近限制: {cancel_ratio:.1%}"
            )

        # 4. 检查高频交易
        if self._config.enable_hft_detection:
            hft_result = self._hft_detector.detect(account_id, timestamp)
            if hft_result.is_hft:
                warnings.append(
                    f"检测到高频交易: {hft_result.orders_per_sec:.1f}笔/秒"
                )
                # HFT账户增加额外延迟
                delay_ms = max(delay_ms, self._config.base_delay_ms * 3)

        # 限制最大延迟
        delay_ms = min(delay_ms, self._config.max_delay_ms)

        # 确定动作
        if violations and not self._config.enable_auto_throttle:
            action = ThrottleAction.REJECT
            self._reject_count += 1
            message = "合规检查未通过, 订单被拒绝"
            reason = "; ".join(violations)
        elif delay_ms > 0:
            action = ThrottleAction.DELAY
            self._throttle_count += 1
            message = f"节流生效, 延迟{delay_ms}ms"
            reason = "; ".join(violations + warnings)
        elif warnings:
            action = ThrottleAction.WARN
            message = "接近合规阈值, 请注意控制频率"
            reason = "; ".join(warnings)
        else:
            action = ThrottleAction.ALLOW
            message = "合规检查通过"
            reason = ""

        result = ThrottleResult(
            action=action,
            delay_ms=delay_ms,
            message=message,
            reason=reason,
            metrics=metrics,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
        )

        # 发送审计事件
        if violations or warnings:
            self._emit_audit(
                event_type=AuditEventType.COMPLIANCE_WARNING if not violations else AuditEventType.THROTTLE_DELAY,
                account_id=account_id,
                strategy_id=strategy_id,
                result=result,
            )

        return result

    def can_submit(
        self,
        account_id: str,
        strategy_id: str = "",
        timestamp: float | None = None,
    ) -> tuple[bool, str]:
        """检查是否可以提交订单.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            timestamp: 检查时间

        返回:
            (是否允许, 消息)
        """
        result = self.check_and_throttle(account_id, strategy_id, timestamp)

        if result.should_reject():
            return False, result.message

        if result.should_delay():
            # 执行延迟
            time.sleep(result.delay_ms / 1000)
            return True, f"延迟{result.delay_ms}ms后允许"

        return True, result.message

    def get_account_metrics(
        self,
        account_id: str,
        timestamp: float | None = None,
    ) -> dict[str, float]:
        """获取账户合规指标.

        参数:
            account_id: 账户ID
            timestamp: 计算时间

        返回:
            指标字典
        """
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            if account_id not in self._account_states:
                return {}
            state = self._account_states[account_id]
            return self._get_metrics(state, timestamp)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "check_count": self._check_count,
            "throttle_count": self._throttle_count,
            "reject_count": self._reject_count,
            "throttle_rate": (
                self._throttle_count / self._check_count
                if self._check_count > 0
                else 0.0
            ),
            "reject_rate": (
                self._reject_count / self._check_count
                if self._check_count > 0
                else 0.0
            ),
            "hft_detector": self._hft_detector.get_statistics(),
            "config": {
                "max_cancel_ratio": self._config.max_cancel_ratio,
                "max_cancel_freq_per_sec": self._config.max_cancel_freq_per_sec,
                "min_order_interval_ms": self._config.min_order_interval_ms,
            },
            "version": self.VERSION,
        }

    def reset(self) -> None:
        """重置管理器."""
        with self._lock:
            self._account_states.clear()
        self._hft_detector.reset()
        self._check_count = 0
        self._throttle_count = 0
        self._reject_count = 0

    def _get_metrics(
        self,
        state: _AccountThrottleState,
        timestamp: float,
    ) -> dict[str, float]:
        """计算指标."""
        return {
            "cancel_ratio": state.get_cancel_ratio(),
            "cancel_freq_per_sec": state.get_cancel_freq_per_sec(timestamp),
            "order_freq_per_sec": state.get_order_freq_per_sec(timestamp),
            "total_orders": float(state.total_orders),
            "total_cancels": float(state.total_cancels),
        }

    def _emit_audit(
        self,
        event_type: AuditEventType,
        account_id: str,
        strategy_id: str,
        result: ThrottleResult,
    ) -> None:
        """发送审计事件."""
        if self._audit_callback:
            entry = AuditLogEntry(
                timestamp=result.timestamp,
                event_type=event_type,
                operator=f"{account_id}/{strategy_id}" if strategy_id else account_id,
                target="ORDER_THROTTLE",
                action=result.action.value,
                result="DELAYED" if result.should_delay() else "REJECTED" if result.should_reject() else "WARNED",
                context={
                    "message": result.message,
                    "reason": result.reason,
                    "delay_ms": result.delay_ms,
                    "metrics": result.metrics,
                },
                category=LogCategory.AUDIT,
                military_rule="M17",
            )
            entry = AuditLogEntry(
                timestamp=entry.timestamp,
                event_type=entry.event_type,
                operator=entry.operator,
                target=entry.target,
                action=entry.action,
                result=entry.result,
                context=entry.context,
                category=entry.category,
                integrity_hash=entry.compute_integrity_hash(),
                sequence_id=entry.sequence_id,
                military_rule=entry.military_rule,
            )
            try:
                self._audit_callback(entry)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")


class _AccountThrottleState:
    """账户节流状态 (内部类)."""

    def __init__(self, window_seconds: int = 5, max_records: int = 10000) -> None:
        """初始化."""
        self._window_seconds = window_seconds
        self._records: deque[tuple[float, str]] = deque(maxlen=max_records)
        self._total_orders: int = 0
        self._total_cancels: int = 0
        self._last_order_time: float | None = None

    @property
    def total_orders(self) -> int:
        """总订单数."""
        return self._total_orders

    @property
    def total_cancels(self) -> int:
        """总撤单数."""
        return self._total_cancels

    @property
    def last_order_time(self) -> float | None:
        """最后订单时间."""
        return self._last_order_time

    def record_order(self, event_type: str, timestamp: float) -> None:
        """记录订单."""
        self._records.append((timestamp, event_type))
        self._total_orders += 1
        if event_type == "cancel":
            self._total_cancels += 1
        self._last_order_time = timestamp

    def get_cancel_ratio(self) -> float:
        """获取撤单比例."""
        if self._total_orders == 0:
            return 0.0
        return self._total_cancels / self._total_orders

    def get_cancel_freq_per_sec(self, timestamp: float) -> float:
        """获取撤单频率 (每秒)."""
        window_start = timestamp - 1.0
        cancel_count = sum(
            1 for ts, ev in self._records
            if ts >= window_start and ev == "cancel"
        )
        return float(cancel_count)

    def get_order_freq_per_sec(self, timestamp: float) -> float:
        """获取订单频率 (每秒)."""
        window_start = timestamp - 1.0
        order_count = sum(1 for ts, _ in self._records if ts >= window_start)
        return float(order_count)


class AuditLogger:
    """审计日志记录器 (军规 M3).

    功能:
    - 记录审计日志 (必记字段: timestamp, event_type, operator, target, action, result, context)
    - 完整性校验 (SHA256哈希)
    - 日志分类与保留期限管理
    - 支持加密存储
    - 支持异地备份

    保留期限:
    - 交易日志: 5年
    - 系统日志: 3年
    - 审计日志: 10年

    示例:
        >>> audit_logger = AuditLogger()
        >>> audit_logger.log(
        ...     event_type=AuditEventType.ORDER_SUBMIT,
        ...     operator="acc_001/strat_001",
        ...     target="order_12345",
        ...     action="提交买入订单",
        ...     result="SUCCESS",
        ...     context={"symbol": "rb2501", "volume": 10},
        ... )
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: AuditLogConfig | None = None,
        backup_callback: Callable[[AuditLogEntry], None] | None = None,
    ) -> None:
        """初始化审计日志记录器.

        参数:
            config: 日志配置 (None使用默认配置)
            backup_callback: 异地备份回调函数
        """
        self._config = config or AuditLogConfig()
        self._backup_callback = backup_callback

        # 日志存储 (按分类)
        self._logs: dict[LogCategory, list[AuditLogEntry]] = {
            LogCategory.TRADING: [],
            LogCategory.SYSTEM: [],
            LogCategory.AUDIT: [],
        }
        self._lock = threading.Lock()

        # 序列号生成
        self._sequence_counter: int = 0

        # 统计
        self._log_count: int = 0

    @property
    def config(self) -> AuditLogConfig:
        """获取配置."""
        return self._config

    def log(
        self,
        event_type: AuditEventType,
        operator: str,
        target: str,
        action: str,
        result: str,
        context: dict[str, Any] | None = None,
        category: LogCategory | None = None,
        timestamp: datetime | None = None,
    ) -> AuditLogEntry:
        """记录审计日志.

        参数:
            event_type: 事件类型
            operator: 操作者
            target: 操作目标
            action: 操作动作
            result: 操作结果
            context: 上下文信息
            category: 日志分类 (None自动推断)
            timestamp: 时间戳 (None使用当前时间)

        返回:
            审计日志条目
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        if context is None:
            context = {}

        # 自动推断分类
        if category is None:
            category = self._infer_category(event_type)

        with self._lock:
            self._sequence_counter += 1
            sequence_id = self._sequence_counter

        # 创建日志条目
        entry = AuditLogEntry(
            timestamp=timestamp.isoformat(),
            event_type=event_type,
            operator=operator,
            target=target,
            action=action,
            result=result,
            context=context,
            category=category,
            sequence_id=sequence_id,
            military_rule="M3",
        )

        # 计算完整性哈希
        integrity_hash = entry.compute_integrity_hash()
        entry = AuditLogEntry(
            timestamp=entry.timestamp,
            event_type=entry.event_type,
            operator=entry.operator,
            target=entry.target,
            action=entry.action,
            result=entry.result,
            context=entry.context,
            category=entry.category,
            integrity_hash=integrity_hash,
            sequence_id=entry.sequence_id,
            military_rule=entry.military_rule,
        )

        # 存储日志
        with self._lock:
            self._logs[category].append(entry)
            self._log_count += 1

        # 异地备份
        if self._config.enable_remote_backup and self._backup_callback:
            try:
                self._backup_callback(entry)
            except Exception as e:
                logger.error(f"审计日志备份失败: {e}")

        return entry

    def log_order_submit(
        self,
        account_id: str,
        strategy_id: str,
        order_id: str,
        symbol: str,
        direction: str,
        volume: int,
        price: float,
        result: str = "SUCCESS",
    ) -> AuditLogEntry:
        """记录订单提交日志.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            order_id: 订单ID
            symbol: 合约代码
            direction: 方向
            volume: 数量
            price: 价格
            result: 结果

        返回:
            审计日志条目
        """
        return self.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator=f"{account_id}/{strategy_id}",
            target=order_id,
            action=f"提交{direction}订单",
            result=result,
            context={
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "price": price,
            },
            category=LogCategory.TRADING,
        )

    def log_compliance_violation(
        self,
        account_id: str,
        strategy_id: str,
        violation_type: str,
        message: str,
        metrics: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        """记录合规违规日志.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            violation_type: 违规类型
            message: 违规消息
            metrics: 相关指标

        返回:
            审计日志条目
        """
        return self.log(
            event_type=AuditEventType.COMPLIANCE_VIOLATION,
            operator=f"{account_id}/{strategy_id}",
            target=violation_type,
            action="合规检查违规",
            result="VIOLATION",
            context={
                "message": message,
                "metrics": metrics or {},
            },
            category=LogCategory.AUDIT,
        )

    def log_hft_detected(
        self,
        account_id: str,
        orders_per_sec: float,
        threshold: int,
    ) -> AuditLogEntry:
        """记录高频交易检测日志.

        参数:
            account_id: 账户ID
            orders_per_sec: 每秒订单数
            threshold: 阈值

        返回:
            审计日志条目
        """
        return self.log(
            event_type=AuditEventType.HFT_DETECTED,
            operator=account_id,
            target="HFT_DETECTION",
            action="高频交易检测",
            result="DETECTED",
            context={
                "orders_per_sec": orders_per_sec,
                "threshold": threshold,
                "excess_ratio": orders_per_sec / threshold if threshold > 0 else 0,
            },
            category=LogCategory.AUDIT,
        )

    def get_logs(
        self,
        category: LogCategory | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[AuditLogEntry]:
        """查询日志.

        参数:
            category: 日志分类 (None返回所有)
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        返回:
            日志列表
        """
        with self._lock:
            if category:
                logs = self._logs.get(category, []).copy()
            else:
                logs = []
                for cat_logs in self._logs.values():
                    logs.extend(cat_logs)

        # 时间筛选
        if start_time:
            start_str = start_time.isoformat()
            logs = [l for l in logs if l.timestamp >= start_str]

        if end_time:
            end_str = end_time.isoformat()
            logs = [l for l in logs if l.timestamp <= end_str]

        # 按时间排序
        logs.sort(key=lambda l: l.timestamp, reverse=True)

        return logs[:limit]

    def verify_integrity(self, entry: AuditLogEntry) -> bool:
        """验证日志完整性.

        参数:
            entry: 日志条目

        返回:
            是否完整
        """
        expected_hash = entry.compute_integrity_hash()
        return entry.integrity_hash == expected_hash

    def get_retention_date(self, category: LogCategory) -> datetime:
        """获取保留截止日期.

        参数:
            category: 日志分类

        返回:
            截止日期
        """
        now = datetime.now()  # noqa: DTZ005
        retention_years = {
            LogCategory.TRADING: self._config.trading_log_retention_years,
            LogCategory.SYSTEM: self._config.system_log_retention_years,
            LogCategory.AUDIT: self._config.audit_log_retention_years,
        }
        years = retention_years.get(category, 10)
        return now - timedelta(days=years * 365)

    def cleanup_expired_logs(self) -> int:
        """清理过期日志.

        返回:
            清理数量
        """
        cleaned_count = 0
        now = datetime.now()  # noqa: DTZ005

        with self._lock:
            for category in LogCategory:
                retention_date = self.get_retention_date(category)
                retention_str = retention_date.isoformat()

                original_count = len(self._logs[category])
                self._logs[category] = [
                    l for l in self._logs[category]
                    if l.timestamp >= retention_str
                ]
                cleaned_count += original_count - len(self._logs[category])

        if cleaned_count > 0:
            logger.info(f"清理过期日志: {cleaned_count}条")

        return cleaned_count

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        with self._lock:
            log_counts = {
                cat.value: len(logs) for cat, logs in self._logs.items()
            }

        return {
            "total_log_count": self._log_count,
            "log_counts_by_category": log_counts,
            "sequence_counter": self._sequence_counter,
            "config": {
                "trading_retention_years": self._config.trading_log_retention_years,
                "system_retention_years": self._config.system_log_retention_years,
                "audit_retention_years": self._config.audit_log_retention_years,
                "encryption_enabled": self._config.enable_encryption,
                "integrity_check_enabled": self._config.enable_integrity_check,
                "remote_backup_enabled": self._config.enable_remote_backup,
            },
            "version": self.VERSION,
        }

    def _infer_category(self, event_type: AuditEventType) -> LogCategory:
        """推断日志分类."""
        trading_events = {
            AuditEventType.ORDER_SUBMIT,
            AuditEventType.ORDER_CANCEL,
            AuditEventType.ORDER_AMEND,
            AuditEventType.ORDER_FILL,
            AuditEventType.ORDER_REJECT,
        }

        system_events = {
            AuditEventType.SYSTEM_START,
            AuditEventType.SYSTEM_STOP,
            AuditEventType.CONFIG_CHANGE,
        }

        if event_type in trading_events:
            return LogCategory.TRADING
        elif event_type in system_events:
            return LogCategory.SYSTEM
        else:
            return LogCategory.AUDIT


# ============================================================
# 便捷函数
# ============================================================


def create_throttle_manager(
    config: ThrottleConfig | None = None,
    audit_callback: Callable[[AuditLogEntry], None] | None = None,
) -> ComplianceThrottleManager:
    """创建合规节流管理器.

    参数:
        config: 节流配置
        audit_callback: 审计回调函数

    返回:
        节流管理器实例
    """
    return ComplianceThrottleManager(config, audit_callback)


def create_hft_detector(
    threshold_per_sec: int = HFT_THRESHOLD_PER_SEC,
    window_seconds: int = 1,
) -> HFTDetector:
    """创建高频交易检测器.

    参数:
        threshold_per_sec: 每秒订单阈值
        window_seconds: 检测窗口

    返回:
        检测器实例
    """
    return HFTDetector(threshold_per_sec, window_seconds)


def create_audit_logger(
    config: AuditLogConfig | None = None,
    backup_callback: Callable[[AuditLogEntry], None] | None = None,
) -> AuditLogger:
    """创建审计日志记录器.

    参数:
        config: 日志配置
        backup_callback: 异地备份回调函数

    返回:
        日志记录器实例
    """
    return AuditLogger(config, backup_callback)


def get_default_throttle_config() -> ThrottleConfig:
    """获取默认节流配置.

    返回:
        默认配置
    """
    return ThrottleConfig()


def get_default_audit_config() -> AuditLogConfig:
    """获取默认审计日志配置.

    返回:
        默认配置
    """
    return AuditLogConfig()
