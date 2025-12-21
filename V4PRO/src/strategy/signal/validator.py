"""
信号验证模块 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制
V4 SPEC: M1军规 - 信号源ID验证

军规覆盖:
- M1: 单一信号源 - 信号源唯一性验证
- M3: 审计日志 - 验证结果追踪
- M7: 场景回放 - 验证可重放

功能特性:
- 信号源ID验证
- 信号签名验证
- 信号有效性检查
- 重复信号检测
- 审计日志支持

示例:
    >>> from src.strategy.signal import SignalValidator
    >>> validator = SignalValidator()
    >>> result = validator.validate(signal)
    >>> if result.is_valid:
    ...     process_signal(signal)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    from src.strategy.signal.source import SignalSource, TradingSignal


class ValidationErrorCode(Enum):
    """验证错误代码枚举."""

    NONE = "NONE"  # 无错误
    INVALID_SOURCE_ID = "INVALID_SOURCE_ID"  # 无效的信号源ID
    SOURCE_NOT_REGISTERED = "SOURCE_NOT_REGISTERED"  # 信号源未注册
    SOURCE_INACTIVE = "SOURCE_INACTIVE"  # 信号源未激活
    SIGNAL_EXPIRED = "SIGNAL_EXPIRED"  # 信号已过期
    INVALID_SIGNATURE = "INVALID_SIGNATURE"  # 签名无效
    DUPLICATE_SIGNAL = "DUPLICATE_SIGNAL"  # 重复信号
    INVALID_STRENGTH = "INVALID_STRENGTH"  # 无效的信号强度
    INVALID_CONFIDENCE = "INVALID_CONFIDENCE"  # 无效的置信度
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"  # 合约代码不匹配
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"  # 频率限制超出
    CONFLICTING_SIGNAL = "CONFLICTING_SIGNAL"  # 冲突信号


class ValidationSeverity(Enum):
    """验证严重程度枚举."""

    INFO = "INFO"  # 信息
    WARNING = "WARNING"  # 警告
    ERROR = "ERROR"  # 错误
    CRITICAL = "CRITICAL"  # 严重错误


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """验证结果 (不可变).

    属性:
        is_valid: 是否通过验证
        error_code: 错误代码
        severity: 严重程度
        message: 错误消息
        signal_id: 信号ID
        source_id: 信号源ID
        timestamp: 验证时间戳
        details: 详细信息
    """

    is_valid: bool
    error_code: ValidationErrorCode = ValidationErrorCode.NONE
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    signal_id: str = ""
    source_id: str = ""
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        signal_id: str,
        source_id: str,
        message: str = "Validation passed",
    ) -> ValidationResult:
        """创建成功结果."""
        return cls(
            is_valid=True,
            error_code=ValidationErrorCode.NONE,
            severity=ValidationSeverity.INFO,
            message=message,
            signal_id=signal_id,
            source_id=source_id,
        )

    @classmethod
    def failure(
        cls,
        signal_id: str,
        source_id: str,
        error_code: ValidationErrorCode,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """创建失败结果."""
        return cls(
            is_valid=False,
            error_code=error_code,
            severity=severity,
            message=message,
            signal_id=signal_id,
            source_id=source_id,
            details=details or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "is_valid": self.is_valid,
            "error_code": self.error_code.value,
            "severity": self.severity.value,
            "message": self.message,
            "signal_id": self.signal_id,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=UTC
            ).isoformat(),
            "details": self.details,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "SIGNAL_VALIDATION",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.to_dict(),
        }


@dataclass
class SignalValidator:
    """信号验证器 (M1军规核心组件).

    负责:
    - 验证信号源ID合法性
    - 验证信号签名
    - 检测重复信号
    - 检查信号有效性
    - 记录验证结果

    属性:
        registered_sources: 已注册的信号源字典
        seen_signals: 已处理的信号ID集合
        validation_history: 验证历史
    """

    # 默认配置
    DEFAULT_HISTORY_SIZE: ClassVar[int] = 10000  # 历史记录大小
    DEFAULT_DUPLICATE_WINDOW: ClassVar[float] = 60.0  # 重复检测窗口 (秒)
    DEFAULT_RATE_LIMIT: ClassVar[int] = 100  # 每秒最大信号数

    # 已注册的信号源
    registered_sources: dict[str, SignalSource] = field(default_factory=dict)

    # 内部状态
    _seen_signals: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _validation_history: deque[ValidationResult] = field(
        default_factory=lambda: deque(maxlen=10000), init=False, repr=False
    )
    _rate_counters: dict[str, deque[float]] = field(
        default_factory=dict, init=False, repr=False
    )
    _duplicate_window: float = field(default=60.0, init=False)
    _rate_limit: int = field(default=100, init=False)

    @property
    def validation_count(self) -> int:
        """获取验证总数."""
        return len(self._validation_history)

    @property
    def validation_pass_rate(self) -> float:
        """获取验证通过率."""
        if not self._validation_history:
            return 0.0
        passed = sum(1 for r in self._validation_history if r.is_valid)
        return passed / len(self._validation_history)

    def register_source(self, source: SignalSource) -> None:
        """注册信号源.

        参数:
            source: 信号源实例
        """
        self.registered_sources[source.full_source_id] = source
        self._rate_counters[source.full_source_id] = deque(maxlen=1000)

    def unregister_source(self, source_id: str) -> None:
        """注销信号源.

        参数:
            source_id: 信号源ID
        """
        if source_id in self.registered_sources:
            del self.registered_sources[source_id]
        if source_id in self._rate_counters:
            del self._rate_counters[source_id]

    def is_source_registered(self, source_id: str) -> bool:
        """检查信号源是否已注册."""
        return source_id in self.registered_sources

    def validate(
        self,
        signal: TradingSignal,
        expected_symbol: str | None = None,
        strict_mode: bool = True,
    ) -> ValidationResult:
        """验证交易信号 (M1军规).

        参数:
            signal: 待验证的信号
            expected_symbol: 期望的合约代码 (可选)
            strict_mode: 严格模式 (验证签名)

        返回:
            ValidationResult验证结果
        """
        signal_id = signal.signal_id
        source_id = signal.source_id

        # 1. 检查信号源ID格式
        if not self._validate_source_id_format(source_id):
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.INVALID_SOURCE_ID,
                message=f"Invalid source ID format: {source_id}",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        # 2. 检查信号源是否已注册
        if source_id not in self.registered_sources:
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.SOURCE_NOT_REGISTERED,
                message=f"Source not registered: {source_id}",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        source = self.registered_sources[source_id]

        # 3. 检查信号源是否活跃
        if not source.is_active():
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.SOURCE_INACTIVE,
                message=f"Source is not active: {source_id} (status: {source.status.value})",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        # 4. 检查信号是否过期
        if signal.is_expired():
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.SIGNAL_EXPIRED,
                message=f"Signal expired at {signal.expire_at}",
                severity=ValidationSeverity.WARNING,
                details={"expire_at": signal.expire_at, "current_time": time.time()},
            )
            self._record_validation(result)
            return result

        # 5. 检查重复信号
        if self._is_duplicate_signal(signal_id):
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.DUPLICATE_SIGNAL,
                message=f"Duplicate signal detected: {signal_id}",
                severity=ValidationSeverity.WARNING,
            )
            self._record_validation(result)
            return result

        # 6. 检查信号强度
        if not 0 <= signal.strength <= 1:
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.INVALID_STRENGTH,
                message=f"Invalid signal strength: {signal.strength}",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        # 7. 检查置信度
        if not 0 <= signal.confidence <= 1:
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.INVALID_CONFIDENCE,
                message=f"Invalid confidence: {signal.confidence}",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        # 8. 检查合约代码匹配
        if expected_symbol and signal.symbol != expected_symbol:
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.SYMBOL_MISMATCH,
                message=f"Symbol mismatch: expected {expected_symbol}, got {signal.symbol}",
                severity=ValidationSeverity.ERROR,
            )
            self._record_validation(result)
            return result

        # 9. 检查频率限制
        if self._is_rate_limited(source_id):
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.RATE_LIMIT_EXCEEDED,
                message=f"Rate limit exceeded for source: {source_id}",
                severity=ValidationSeverity.WARNING,
            )
            self._record_validation(result)
            return result

        # 10. 严格模式: 验证签名
        if strict_mode and not source.verify_signal(signal):
            result = ValidationResult.failure(
                signal_id=signal_id,
                source_id=source_id,
                error_code=ValidationErrorCode.INVALID_SIGNATURE,
                message="Signal signature verification failed",
                severity=ValidationSeverity.CRITICAL,
            )
            self._record_validation(result)
            return result

        # 所有检查通过
        self._mark_signal_seen(signal_id)
        self._record_rate(source_id)

        result = ValidationResult.success(
            signal_id=signal_id,
            source_id=source_id,
            message="Signal validation passed",
        )
        self._record_validation(result)
        return result

    def validate_source_ownership(
        self,
        signal: TradingSignal,
        expected_source_id: str,
    ) -> ValidationResult:
        """验证信号源归属 (M1军规核心).

        确保信号确实来自声称的信号源。

        参数:
            signal: 待验证的信号
            expected_source_id: 期望的信号源ID

        返回:
            ValidationResult验证结果
        """
        if signal.source_id != expected_source_id:
            return ValidationResult.failure(
                signal_id=signal.signal_id,
                source_id=signal.source_id,
                error_code=ValidationErrorCode.INVALID_SOURCE_ID,
                message=f"Source mismatch: expected {expected_source_id}, got {signal.source_id}",
                severity=ValidationSeverity.CRITICAL,
                details={
                    "expected_source_id": expected_source_id,
                    "actual_source_id": signal.source_id,
                },
            )

        return ValidationResult.success(
            signal_id=signal.signal_id,
            source_id=signal.source_id,
            message="Source ownership verified",
        )

    def _validate_source_id_format(self, source_id: str) -> bool:
        """验证信号源ID格式.

        格式: {strategy_id}:{instance_id}:{nonce}
        """
        if not source_id:
            return False

        parts = source_id.split(":")
        return len(parts) == 3 and all(parts)

    def _is_duplicate_signal(self, signal_id: str) -> bool:
        """检查是否为重复信号."""
        if signal_id in self._seen_signals:
            seen_time = self._seen_signals[signal_id]
            if time.time() - seen_time < self._duplicate_window:
                return True
        return False

    def _mark_signal_seen(self, signal_id: str) -> None:
        """标记信号已处理."""
        self._seen_signals[signal_id] = time.time()

        # 清理过期记录
        self._cleanup_seen_signals()

    def _cleanup_seen_signals(self) -> None:
        """清理过期的已处理信号记录."""
        now = time.time()
        cutoff = now - self._duplicate_window

        expired_keys = [
            k for k, v in self._seen_signals.items() if v < cutoff
        ]
        for key in expired_keys:
            del self._seen_signals[key]

    def _is_rate_limited(self, source_id: str) -> bool:
        """检查是否超出频率限制."""
        if source_id not in self._rate_counters:
            return False

        now = time.time()
        counter = self._rate_counters[source_id]

        # 移除1秒前的记录
        while counter and counter[0] < now - 1.0:
            counter.popleft()

        return len(counter) >= self._rate_limit

    def _record_rate(self, source_id: str) -> None:
        """记录频率."""
        if source_id in self._rate_counters:
            self._rate_counters[source_id].append(time.time())

    def _record_validation(self, result: ValidationResult) -> None:
        """记录验证结果."""
        self._validation_history.append(result)

    def get_validation_statistics(self) -> dict[str, Any]:
        """获取验证统计信息."""
        total = len(self._validation_history)
        passed = sum(1 for r in self._validation_history if r.is_valid)
        failed = total - passed

        error_counts: dict[str, int] = {}
        for result in self._validation_history:
            if not result.is_valid:
                code = result.error_code.value
                error_counts[code] = error_counts.get(code, 0) + 1

        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "registered_sources": len(self.registered_sources),
            "active_sources": sum(
                1 for s in self.registered_sources.values() if s.is_active()
            ),
            "error_breakdown": error_counts,
            "seen_signals_count": len(self._seen_signals),
        }

    def get_recent_failures(self, count: int = 10) -> list[ValidationResult]:
        """获取最近的验证失败记录."""
        failures = [r for r in self._validation_history if not r.is_valid]
        return list(failures)[-count:]

    def clear_history(self) -> None:
        """清空验证历史."""
        self._validation_history.clear()
        self._seen_signals.clear()

    def reset(self) -> None:
        """重置验证器状态."""
        self.clear_history()
        for counter in self._rate_counters.values():
            counter.clear()


# ============================================================
# 便捷函数
# ============================================================


def create_validator(
    duplicate_window: float = 60.0,
    rate_limit: int = 100,
) -> SignalValidator:
    """创建信号验证器.

    参数:
        duplicate_window: 重复检测窗口 (秒)
        rate_limit: 每秒最大信号数

    返回:
        SignalValidator实例
    """
    validator = SignalValidator()
    validator._duplicate_window = duplicate_window
    validator._rate_limit = rate_limit
    return validator
