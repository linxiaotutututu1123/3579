"""
FallbackManager - 降级兜底管理器.

V4PRO Platform Component - Phase 8
V4 SPEC: 降级兜底机制
V2 Scenarios: EXEC.FALLBACK.MANAGER

军规级要求:
- M4: 降级兜底机制完整
- M3: 审计日志完整
- M6: 与熔断保护联动

降级策略分层:
1. GRACEFUL (优雅降级): 切换到备用算法
2. REDUCED (减量模式): 降低交易规模
3. MANUAL (人工接管): 暂停自动交易，等待人工
4. EMERGENCY (紧急模式): 仅允许平仓操作

触发条件:
- 主执行路径连续失败 N 次
- 熔断器触发后的恢复期
- 市场极端波动
- 系统资源不足
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.guardian.circuit_breaker_controller import CircuitBreakerController


class FallbackLevel(Enum):
    """降级级别.

    定义系统降级的不同级别，从轻微到严重。
    """

    NORMAL = "normal"  # 正常模式
    GRACEFUL = "graceful"  # 优雅降级：切换备用算法
    REDUCED = "reduced"  # 减量模式：降低交易规模
    MANUAL = "manual"  # 人工接管：暂停自动交易
    EMERGENCY = "emergency"  # 紧急模式：仅允许平仓


class FallbackStrategy(Enum):
    """降级策略类型."""

    ALGORITHM_SWITCH = "algorithm_switch"  # 切换算法
    VOLUME_REDUCTION = "volume_reduction"  # 减少交易量
    TIMEOUT_EXTENSION = "timeout_extension"  # 延长超时
    RETRY_ENHANCEMENT = "retry_enhancement"  # 增强重试
    MANUAL_QUEUE = "manual_queue"  # 进入人工队列
    CLOSE_ONLY = "close_only"  # 仅允许平仓


@dataclass
class FallbackConfig:
    """降级配置.

    Attributes:
        max_failures: 触发降级的最大失败次数
        failure_window_seconds: 失败统计时间窗口
        graceful_volume_ratio: 优雅降级时的交易量比例
        reduced_volume_ratio: 减量模式时的交易量比例
        auto_recovery_enabled: 是否启用自动恢复
        recovery_check_interval: 恢复检查间隔(秒)
        recovery_success_threshold: 恢复所需成功次数
    """

    max_failures: int = 3
    failure_window_seconds: float = 300.0  # 5分钟
    graceful_volume_ratio: float = 0.75  # 75%
    reduced_volume_ratio: float = 0.50  # 50%
    auto_recovery_enabled: bool = True
    recovery_check_interval: float = 60.0  # 1分钟
    recovery_success_threshold: int = 5

    def validate(self) -> list[str]:
        """验证配置有效性."""
        errors = []
        if self.max_failures < 1:
            errors.append("max_failures must be >= 1")
        if self.failure_window_seconds <= 0:
            errors.append("failure_window_seconds must be > 0")
        if not 0 < self.graceful_volume_ratio <= 1:
            errors.append("graceful_volume_ratio must be in (0, 1]")
        if not 0 < self.reduced_volume_ratio <= 1:
            errors.append("reduced_volume_ratio must be in (0, 1]")
        if self.reduced_volume_ratio > self.graceful_volume_ratio:
            errors.append("reduced_volume_ratio should <= graceful_volume_ratio")
        return errors


@dataclass
class FallbackResult:
    """降级操作结果.

    Attributes:
        success: 是否成功
        level: 当前降级级别
        strategy: 采用的降级策略
        message: 结果消息
        adjusted_params: 调整后的参数
        timestamp: 时间戳
    """

    success: bool
    level: FallbackLevel
    strategy: FallbackStrategy | None = None
    message: str = ""
    adjusted_params: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "success": self.success,
            "level": self.level.value,
            "strategy": self.strategy.value if self.strategy else None,
            "message": self.message,
            "adjusted_params": self.adjusted_params,
            "timestamp": self.timestamp,
        }


@dataclass
class FailureRecord:
    """失败记录."""

    timestamp: float
    reason: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackState:
    """降级状态.

    Attributes:
        current_level: 当前降级级别
        failure_count: 当前失败计数
        success_count: 恢复成功计数
        last_failure_time: 最后失败时间
        last_level_change_time: 最后级别变更时间
        failure_history: 失败历史记录
    """

    current_level: FallbackLevel = FallbackLevel.NORMAL
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_level_change_time: float = 0.0
    failure_history: list[FailureRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "current_level": self.current_level.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_level_change_time": self.last_level_change_time,
            "failure_history_count": len(self.failure_history),
        }


class FallbackManager:
    """降级兜底管理器.

    V4 SPEC M4: 降级兜底机制

    功能:
    1. 监控执行失败并触发降级
    2. 根据失败严重程度选择降级策略
    3. 与熔断器联动实现保护
    4. 支持自动恢复到正常模式

    使用示例:
        manager = FallbackManager(config)
        manager.register_circuit_breaker(circuit_breaker_controller)

        # 报告执行失败
        result = manager.report_failure("timeout", {"order_id": "123"})

        # 获取当前允许的操作
        if manager.is_operation_allowed("new_order"):
            # 执行操作
            pass

        # 报告成功以尝试恢复
        manager.report_success()
    """

    # 降级级别转换矩阵
    LEVEL_TRANSITIONS: dict[FallbackLevel, list[FallbackLevel]] = {
        FallbackLevel.NORMAL: [FallbackLevel.GRACEFUL],
        FallbackLevel.GRACEFUL: [FallbackLevel.REDUCED, FallbackLevel.NORMAL],
        FallbackLevel.REDUCED: [FallbackLevel.MANUAL, FallbackLevel.GRACEFUL],
        FallbackLevel.MANUAL: [FallbackLevel.EMERGENCY, FallbackLevel.REDUCED],
        FallbackLevel.EMERGENCY: [FallbackLevel.MANUAL],
    }

    # 各级别允许的操作
    ALLOWED_OPERATIONS: dict[FallbackLevel, set[str]] = {
        FallbackLevel.NORMAL: {"new_order", "modify_order", "cancel_order", "close_position"},
        FallbackLevel.GRACEFUL: {"new_order", "modify_order", "cancel_order", "close_position"},
        FallbackLevel.REDUCED: {"new_order", "cancel_order", "close_position"},
        FallbackLevel.MANUAL: {"cancel_order", "close_position"},
        FallbackLevel.EMERGENCY: {"close_position"},
    }

    # 各级别默认策略
    DEFAULT_STRATEGIES: dict[FallbackLevel, FallbackStrategy] = {
        FallbackLevel.GRACEFUL: FallbackStrategy.ALGORITHM_SWITCH,
        FallbackLevel.REDUCED: FallbackStrategy.VOLUME_REDUCTION,
        FallbackLevel.MANUAL: FallbackStrategy.MANUAL_QUEUE,
        FallbackLevel.EMERGENCY: FallbackStrategy.CLOSE_ONLY,
    }

    def __init__(
        self,
        config: FallbackConfig | None = None,
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """初始化降级管理器.

        Args:
            config: 降级配置
            audit_callback: 审计日志回调
        """
        self._config = config or FallbackConfig()
        self._state = FallbackState()
        self._audit_callback = audit_callback
        self._circuit_breaker: CircuitBreakerController | None = None

        # 验证配置
        errors = self._config.validate()
        if errors:
            raise ValueError(f"Invalid FallbackConfig: {errors}")

    @property
    def current_level(self) -> FallbackLevel:
        """获取当前降级级别."""
        return self._state.current_level

    @property
    def state(self) -> FallbackState:
        """获取当前状态."""
        return self._state

    def register_circuit_breaker(self, controller: CircuitBreakerController) -> None:
        """注册熔断控制器.

        Args:
            controller: 熔断控制器实例
        """
        self._circuit_breaker = controller
        self._audit("fallback.circuit_breaker.registered", {})

    def report_failure(
        self,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> FallbackResult:
        """报告执行失败.

        Args:
            reason: 失败原因
            context: 失败上下文

        Returns:
            降级操作结果
        """
        now = time.time()
        context = context or {}

        # 清理过期的失败记录
        self._cleanup_old_failures(now)

        # 记录失败
        record = FailureRecord(timestamp=now, reason=reason, context=context)
        self._state.failure_history.append(record)
        self._state.failure_count += 1
        self._state.last_failure_time = now
        self._state.success_count = 0  # 重置成功计数

        self._audit("fallback.failure.reported", {
            "reason": reason,
            "failure_count": self._state.failure_count,
            "current_level": self._state.current_level.value,
        })

        # 检查是否需要升级降级级别
        if self._should_escalate():
            return self._escalate_level(reason)

        return FallbackResult(
            success=True,
            level=self._state.current_level,
            message=f"Failure recorded, count: {self._state.failure_count}",
        )

    def report_success(self) -> FallbackResult:
        """报告执行成功.

        用于恢复检测，连续成功可触发降级恢复。

        Returns:
            降级操作结果
        """
        self._state.success_count += 1

        self._audit("fallback.success.reported", {
            "success_count": self._state.success_count,
            "current_level": self._state.current_level.value,
        })

        # 检查是否可以恢复
        if self._config.auto_recovery_enabled and self._should_recover():
            return self._recover_level()

        return FallbackResult(
            success=True,
            level=self._state.current_level,
            message=f"Success recorded, count: {self._state.success_count}",
        )

    def is_operation_allowed(self, operation: str) -> bool:
        """检查操作是否被允许.

        Args:
            operation: 操作类型 (new_order, modify_order, cancel_order, close_position)

        Returns:
            是否允许
        """
        allowed = self.ALLOWED_OPERATIONS.get(self._state.current_level, set())
        return operation in allowed

    def get_volume_ratio(self) -> float:
        """获取当前允许的交易量比例.

        Returns:
            交易量比例 (0.0-1.0)
        """
        if self._state.current_level == FallbackLevel.NORMAL:
            return 1.0
        elif self._state.current_level == FallbackLevel.GRACEFUL:
            return self._config.graceful_volume_ratio
        elif self._state.current_level == FallbackLevel.REDUCED:
            return self._config.reduced_volume_ratio
        else:
            return 0.0  # MANUAL 和 EMERGENCY 不允许新开仓

    def get_adjusted_params(
        self,
        original_params: dict[str, Any],
    ) -> dict[str, Any]:
        """获取调整后的执行参数.

        根据当前降级级别调整交易参数。

        Args:
            original_params: 原始参数

        Returns:
            调整后的参数
        """
        adjusted = original_params.copy()
        level = self._state.current_level

        if level == FallbackLevel.NORMAL:
            return adjusted

        # 调整交易量
        if "volume" in adjusted:
            adjusted["volume"] = int(adjusted["volume"] * self.get_volume_ratio())
            adjusted["volume"] = max(1, adjusted["volume"])  # 至少1手

        # GRACEFUL: 切换到更保守的算法
        if level == FallbackLevel.GRACEFUL:
            adjusted["execution_algorithm"] = "TWAP"  # 切换到TWAP
            adjusted["urgency"] = "low"

        # REDUCED: 进一步降低激进度
        elif level == FallbackLevel.REDUCED:
            adjusted["execution_algorithm"] = "ICEBERG"
            adjusted["urgency"] = "minimal"
            adjusted["max_participation_rate"] = 0.05  # 最大参与率5%

        # MANUAL/EMERGENCY: 标记需要人工确认
        elif level in (FallbackLevel.MANUAL, FallbackLevel.EMERGENCY):
            adjusted["requires_manual_confirmation"] = True
            adjusted["auto_execute"] = False

        return adjusted

    def force_level(
        self,
        level: FallbackLevel,
        reason: str = "manual_override",
    ) -> FallbackResult:
        """强制设置降级级别.

        用于人工干预或紧急情况。

        Args:
            level: 目标降级级别
            reason: 原因

        Returns:
            操作结果
        """
        old_level = self._state.current_level
        self._state.current_level = level
        self._state.last_level_change_time = time.time()

        self._audit("fallback.level.forced", {
            "old_level": old_level.value,
            "new_level": level.value,
            "reason": reason,
        })

        return FallbackResult(
            success=True,
            level=level,
            strategy=self.DEFAULT_STRATEGIES.get(level),
            message=f"Level forced from {old_level.value} to {level.value}",
        )

    def reset(self) -> FallbackResult:
        """重置到正常模式.

        清除所有失败记录，恢复到NORMAL级别。

        Returns:
            操作结果
        """
        old_level = self._state.current_level
        self._state = FallbackState()

        self._audit("fallback.reset", {
            "old_level": old_level.value,
        })

        return FallbackResult(
            success=True,
            level=FallbackLevel.NORMAL,
            message="Fallback manager reset to NORMAL",
        )

    def _cleanup_old_failures(self, now: float) -> None:
        """清理过期的失败记录."""
        cutoff = now - self._config.failure_window_seconds
        self._state.failure_history = [
            r for r in self._state.failure_history if r.timestamp >= cutoff
        ]
        self._state.failure_count = len(self._state.failure_history)

    def _should_escalate(self) -> bool:
        """判断是否应该升级降级级别."""
        # 检查熔断器状态
        if self._circuit_breaker:
            status = self._circuit_breaker.get_status()
            if not status.is_trading_allowed:
                return True

        # 检查失败次数
        return self._state.failure_count >= self._config.max_failures

    def _should_recover(self) -> bool:
        """判断是否应该恢复降级级别."""
        if self._state.current_level == FallbackLevel.NORMAL:
            return False

        # 检查成功次数
        if self._state.success_count < self._config.recovery_success_threshold:
            return False

        # 检查最后级别变更时间
        now = time.time()
        min_time_at_level = self._config.recovery_check_interval * 2
        if now - self._state.last_level_change_time < min_time_at_level:
            return False

        return True

    def _escalate_level(self, reason: str) -> FallbackResult:
        """升级降级级别."""
        old_level = self._state.current_level
        transitions = self.LEVEL_TRANSITIONS.get(old_level, [])

        # 选择下一个更严格的级别
        new_level = old_level
        for level in transitions:
            if self._is_more_severe(level, old_level):
                new_level = level
                break

        if new_level == old_level:
            # 已经是最高级别
            return FallbackResult(
                success=True,
                level=old_level,
                message=f"Already at maximum fallback level: {old_level.value}",
            )

        self._state.current_level = new_level
        self._state.last_level_change_time = time.time()
        self._state.failure_count = 0  # 重置计数

        strategy = self.DEFAULT_STRATEGIES.get(new_level)

        self._audit("fallback.level.escalated", {
            "old_level": old_level.value,
            "new_level": new_level.value,
            "reason": reason,
            "strategy": strategy.value if strategy else None,
        })

        return FallbackResult(
            success=True,
            level=new_level,
            strategy=strategy,
            message=f"Escalated from {old_level.value} to {new_level.value}",
            adjusted_params={"volume_ratio": self.get_volume_ratio()},
        )

    def _recover_level(self) -> FallbackResult:
        """恢复降级级别."""
        old_level = self._state.current_level
        transitions = self.LEVEL_TRANSITIONS.get(old_level, [])

        # 选择下一个较轻的级别
        new_level = old_level
        for level in transitions:
            if self._is_less_severe(level, old_level):
                new_level = level
                break

        if new_level == old_level:
            return FallbackResult(
                success=True,
                level=old_level,
                message=f"Cannot recover from level: {old_level.value}",
            )

        self._state.current_level = new_level
        self._state.last_level_change_time = time.time()
        self._state.success_count = 0  # 重置计数

        self._audit("fallback.level.recovered", {
            "old_level": old_level.value,
            "new_level": new_level.value,
        })

        return FallbackResult(
            success=True,
            level=new_level,
            message=f"Recovered from {old_level.value} to {new_level.value}",
            adjusted_params={"volume_ratio": self.get_volume_ratio()},
        )

    def _is_more_severe(self, level: FallbackLevel, reference: FallbackLevel) -> bool:
        """判断级别是否更严重."""
        severity = {
            FallbackLevel.NORMAL: 0,
            FallbackLevel.GRACEFUL: 1,
            FallbackLevel.REDUCED: 2,
            FallbackLevel.MANUAL: 3,
            FallbackLevel.EMERGENCY: 4,
        }
        return severity.get(level, 0) > severity.get(reference, 0)

    def _is_less_severe(self, level: FallbackLevel, reference: FallbackLevel) -> bool:
        """判断级别是否更轻微."""
        severity = {
            FallbackLevel.NORMAL: 0,
            FallbackLevel.GRACEFUL: 1,
            FallbackLevel.REDUCED: 2,
            FallbackLevel.MANUAL: 3,
            FallbackLevel.EMERGENCY: 4,
        }
        return severity.get(level, 0) < severity.get(reference, 0)

    def _audit(self, event: str, data: dict[str, Any]) -> None:
        """记录审计日志."""
        if self._audit_callback:
            self._audit_callback(event, {
                **data,
                "timestamp": time.time(),
                "module": "FallbackManager",
            })
