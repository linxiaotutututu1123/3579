"""
CircuitBreaker - 熔断-恢复状态机

V4PRO Platform Component - Phase 10
V4 SPEC: D2 熔断-恢复闭环
V2 Scenarios: GUARD.CIRCUIT_BREAKER.*

军规级要求:
- M3: 每次状态转换必须记录审计日志
- M6: 熔断保护机制完整，状态机设计完善
- 状态转移必须严格按照转移表
- 恢复过程必须渐进式执行

状态定义:
- NORMAL: 正常运行，允许完整交易
- TRIGGERED: 熔断触发，立即停止新开仓
- COOLING: 冷却期，等待30秒后进入恢复
- RECOVERY: 恢复期，渐进式恢复仓位比例
- MANUAL_OVERRIDE: 人工接管，等待人工操作

触发条件:
- daily_loss_pct > 0.03 (日损失>3%)
- position_loss_pct > 0.05 (持仓损失>5%)
- margin_usage_pct > 0.85 (保证金使用率>85%)
- consecutive_losses >= 5 (连续亏损>=5次)

恢复策略:
- position_ratio_steps: [0.25, 0.5, 0.75, 1.0]
- step_interval_seconds: 60
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Protocol


if TYPE_CHECKING:
    from collections.abc import Callable


class AuditLogger(Protocol):
    """审计日志协议.

    M3军规: 所有状态转换必须写入审计日志.
    """

    def log(
        self,
        event_type: str,
        from_state: str,
        to_state: str,
        trigger_reason: str,
        details: dict[str, Any],
    ) -> None:
        """记录审计日志.

        Args:
            event_type: 事件类型
            from_state: 原状态
            to_state: 目标状态
            trigger_reason: 触发原因
            details: 详细信息
        """
        ...


class CircuitBreakerState(IntEnum):
    """熔断器状态枚举.

    V4 SPEC D2: 5状态定义
    """

    NORMAL = 0  # 正常运行
    TRIGGERED = 1  # 熔断触发
    COOLING = 2  # 冷却期
    RECOVERY = 3  # 恢复期
    MANUAL_OVERRIDE = 4  # 人工接管


@dataclass(frozen=True)
class TriggerThresholds:
    """触发条件阈值.

    V4 SPEC D2: 触发条件配置
    """

    daily_loss_pct: float = 0.03  # 日损失百分比阈值
    position_loss_pct: float = 0.05  # 持仓损失百分比阈值
    margin_usage_pct: float = 0.85  # 保证金使用率阈值
    consecutive_losses: int = 5  # 连续亏损次数阈值


@dataclass(frozen=True)
class RecoveryConfig:
    """恢复策略配置.

    V4 SPEC D2: 恢复策略
    """

    position_ratio_steps: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0)
    step_interval_seconds: float = 60.0
    cooling_duration_seconds: float = 30.0
    full_cooling_duration_seconds: float = 300.0  # 5分钟


@dataclass
class CircuitBreakerMetrics:
    """熔断器当前指标.

    用于检测是否满足触发条件.
    """

    daily_loss_pct: float = 0.0
    position_loss_pct: float = 0.0
    margin_usage_pct: float = 0.0
    consecutive_losses: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "daily_loss_pct": self.daily_loss_pct,
            "position_loss_pct": self.position_loss_pct,
            "margin_usage_pct": self.margin_usage_pct,
            "consecutive_losses": self.consecutive_losses,
        }


@dataclass
class TriggerCheckResult:
    """触发条件检测结果."""

    should_trigger: bool
    trigger_reasons: list[str]
    metrics: CircuitBreakerMetrics
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "should_trigger": self.should_trigger,
            "trigger_reasons": self.trigger_reasons,
            "metrics": self.metrics.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class AuditRecord:
    """审计记录.

    M3军规: 状态转换审计.
    """

    record_id: str
    timestamp: float
    event_type: str
    from_state: str
    to_state: str
    trigger_reason: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "trigger_reason": self.trigger_reason,
            "details": self.details,
        }


class DefaultAuditLogger:
    """默认审计日志实现.

    M3军规: 内存存储审计日志.
    """

    def __init__(self) -> None:
        """初始化审计日志."""
        self._records: list[AuditRecord] = []

    @property
    def records(self) -> list[AuditRecord]:
        """获取所有审计记录."""
        return self._records.copy()

    def log(
        self,
        event_type: str,
        from_state: str,
        to_state: str,
        trigger_reason: str,
        details: dict[str, Any],
    ) -> None:
        """记录审计日志.

        Args:
            event_type: 事件类型
            from_state: 原状态
            to_state: 目标状态
            trigger_reason: 触发原因
            details: 详细信息
        """
        record = AuditRecord(
            record_id=str(uuid.uuid4()),
            timestamp=time.time(),
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            trigger_reason=trigger_reason,
            details=details,
        )
        self._records.append(record)

    def get_records_by_type(self, event_type: str) -> list[AuditRecord]:
        """按事件类型获取记录.

        Args:
            event_type: 事件类型

        Returns:
            匹配的审计记录列表
        """
        return [r for r in self._records if r.event_type == event_type]

    def clear(self) -> None:
        """清空审计记录."""
        self._records.clear()


@dataclass
class RecoveryProgress:
    """恢复进度.

    跟踪渐进式恢复过程.
    """

    current_step: int = 0
    current_position_ratio: float = 0.0
    step_start_time: float = 0.0
    total_steps: int = 4

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "current_step": self.current_step,
            "current_position_ratio": self.current_position_ratio,
            "step_start_time": self.step_start_time,
            "total_steps": self.total_steps,
        }


class TransitionError(Exception):
    """状态转换错误."""


# 状态转移事件定义
class CircuitBreakerEvent:
    """熔断器事件常量."""

    TRIGGER = "trigger"  # 触发熔断
    COOLING_START = "cooling_start"  # 开始冷却
    COOLING_COMPLETE = "cooling_complete"  # 冷却完成
    RECOVERY_STEP = "recovery_step"  # 恢复进度
    RECOVERY_COMPLETE = "recovery_complete"  # 恢复完成
    MANUAL_OVERRIDE = "manual_override"  # 人工接管
    MANUAL_RELEASE = "manual_release"  # 人工解除
    MANUAL_TO_COOLING = "manual_to_cooling"  # 人工转冷却


# 合法状态转移表
VALID_CIRCUIT_BREAKER_TRANSITIONS: dict[
    tuple[CircuitBreakerState, str], CircuitBreakerState
] = {
    # NORMAL -> TRIGGERED (触发条件满足)
    (CircuitBreakerState.NORMAL, CircuitBreakerEvent.TRIGGER): (
        CircuitBreakerState.TRIGGERED
    ),
    # TRIGGERED -> COOLING (30秒后自动)
    (CircuitBreakerState.TRIGGERED, CircuitBreakerEvent.COOLING_START): (
        CircuitBreakerState.COOLING
    ),
    # COOLING -> RECOVERY (5分钟冷却完成)
    (CircuitBreakerState.COOLING, CircuitBreakerEvent.COOLING_COMPLETE): (
        CircuitBreakerState.RECOVERY
    ),
    # RECOVERY -> NORMAL (渐进式恢复完成)
    (CircuitBreakerState.RECOVERY, CircuitBreakerEvent.RECOVERY_COMPLETE): (
        CircuitBreakerState.NORMAL
    ),
    # ANY -> MANUAL_OVERRIDE (人工介入)
    (CircuitBreakerState.NORMAL, CircuitBreakerEvent.MANUAL_OVERRIDE): (
        CircuitBreakerState.MANUAL_OVERRIDE
    ),
    (CircuitBreakerState.TRIGGERED, CircuitBreakerEvent.MANUAL_OVERRIDE): (
        CircuitBreakerState.MANUAL_OVERRIDE
    ),
    (CircuitBreakerState.COOLING, CircuitBreakerEvent.MANUAL_OVERRIDE): (
        CircuitBreakerState.MANUAL_OVERRIDE
    ),
    (CircuitBreakerState.RECOVERY, CircuitBreakerEvent.MANUAL_OVERRIDE): (
        CircuitBreakerState.MANUAL_OVERRIDE
    ),
    # MANUAL_OVERRIDE -> NORMAL (人工解除到正常)
    (CircuitBreakerState.MANUAL_OVERRIDE, CircuitBreakerEvent.MANUAL_RELEASE): (
        CircuitBreakerState.NORMAL
    ),
    # MANUAL_OVERRIDE -> COOLING (人工解除到冷却)
    (CircuitBreakerState.MANUAL_OVERRIDE, CircuitBreakerEvent.MANUAL_TO_COOLING): (
        CircuitBreakerState.COOLING
    ),
}


class CircuitBreaker:
    """熔断器状态机.

    V4 SPEC D2: 熔断-恢复闭环
    V2 Scenario: GUARD.CIRCUIT_BREAKER.STATE_MACHINE

    实现5状态熔断器:
    - NORMAL: 正常运行
    - TRIGGERED: 熔断触发
    - COOLING: 冷却期
    - RECOVERY: 渐进式恢复
    - MANUAL_OVERRIDE: 人工接管

    军规合规:
    - M3: 审计日志完整，状态转换全记录
    - M6: 熔断保护机制完整，状态机设计完善
    """

    def __init__(
        self,
        thresholds: TriggerThresholds | None = None,
        recovery_config: RecoveryConfig | None = None,
        audit_logger: AuditLogger | None = None,
        on_state_change: Callable[
            [CircuitBreakerState, CircuitBreakerState, str], None
        ]
        | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        """初始化熔断器.

        Args:
            thresholds: 触发条件阈值配置
            recovery_config: 恢复策略配置
            audit_logger: 审计日志记录器 (M3军规)
            on_state_change: 状态变更回调 (from, to, reason)
            time_func: 时间函数（用于测试注入）
        """
        self._state = CircuitBreakerState.NORMAL
        self._thresholds = thresholds or TriggerThresholds()
        self._recovery_config = recovery_config or RecoveryConfig()
        self._audit_logger = audit_logger or DefaultAuditLogger()
        self._on_state_change = on_state_change
        self._time_func = time_func or time.time

        # 状态跟踪
        self._state_enter_time: float = self._time_func()
        self._triggered_time: float | None = None
        self._cooling_start_time: float | None = None
        self._recovery_progress = RecoveryProgress()
        self._transition_count: int = 0
        self._last_trigger_reasons: list[str] = []

        # 初始化日志
        self._log_audit(
            event_type="circuit_breaker_init",
            from_state="NONE",
            to_state=self._state.name,
            trigger_reason="initialization",
            details={"thresholds": self._thresholds_to_dict()},
        )

    @property
    def state(self) -> CircuitBreakerState:
        """当前状态."""
        return self._state

    @property
    def thresholds(self) -> TriggerThresholds:
        """触发阈值配置."""
        return self._thresholds

    @property
    def recovery_config(self) -> RecoveryConfig:
        """恢复策略配置."""
        return self._recovery_config

    @property
    def transition_count(self) -> int:
        """状态转换次数."""
        return self._transition_count

    @property
    def recovery_progress(self) -> RecoveryProgress:
        """恢复进度."""
        return self._recovery_progress

    @property
    def current_position_ratio(self) -> float:
        """当前允许的仓位比例.

        根据状态返回不同的仓位限制:
        - NORMAL: 1.0 (100%)
        - TRIGGERED/COOLING: 0.0 (不允许新开仓)
        - RECOVERY: 根据恢复进度渐进
        - MANUAL_OVERRIDE: 0.0 (等待人工)
        """
        if self._state == CircuitBreakerState.NORMAL:
            return 1.0
        if self._state == CircuitBreakerState.RECOVERY:
            return self._recovery_progress.current_position_ratio
        return 0.0

    @property
    def is_trading_allowed(self) -> bool:
        """是否允许交易（含减仓）.

        NORMAL和RECOVERY状态允许交易.
        """
        return self._state in (
            CircuitBreakerState.NORMAL,
            CircuitBreakerState.RECOVERY,
        )

    @property
    def is_new_position_allowed(self) -> bool:
        """是否允许新开仓.

        仅NORMAL状态完全允许，RECOVERY状态受比例限制.
        """
        return self._state in (
            CircuitBreakerState.NORMAL,
            CircuitBreakerState.RECOVERY,
        )

    def check_trigger_conditions(
        self, metrics: CircuitBreakerMetrics
    ) -> TriggerCheckResult:
        """检测触发条件.

        V4 SPEC D2: 触发条件检测

        Args:
            metrics: 当前指标数据

        Returns:
            触发检测结果
        """
        reasons: list[str] = []

        if metrics.daily_loss_pct > self._thresholds.daily_loss_pct:
            reasons.append(
                f"daily_loss_pct({metrics.daily_loss_pct:.2%}) > "
                f"threshold({self._thresholds.daily_loss_pct:.2%})"
            )

        if metrics.position_loss_pct > self._thresholds.position_loss_pct:
            reasons.append(
                f"position_loss_pct({metrics.position_loss_pct:.2%}) > "
                f"threshold({self._thresholds.position_loss_pct:.2%})"
            )

        if metrics.margin_usage_pct > self._thresholds.margin_usage_pct:
            reasons.append(
                f"margin_usage_pct({metrics.margin_usage_pct:.2%}) > "
                f"threshold({self._thresholds.margin_usage_pct:.2%})"
            )

        if metrics.consecutive_losses >= self._thresholds.consecutive_losses:
            reasons.append(
                f"consecutive_losses({metrics.consecutive_losses}) >= "
                f"threshold({self._thresholds.consecutive_losses})"
            )

        return TriggerCheckResult(
            should_trigger=len(reasons) > 0,
            trigger_reasons=reasons,
            metrics=metrics,
            timestamp=self._time_func(),
        )

    def trigger(self, metrics: CircuitBreakerMetrics) -> bool:
        """触发熔断.

        V4 SPEC D2: NORMAL -> TRIGGERED

        Args:
            metrics: 触发时的指标数据

        Returns:
            是否成功触发
        """
        if self._state != CircuitBreakerState.NORMAL:
            return False

        check_result = self.check_trigger_conditions(metrics)
        if not check_result.should_trigger:
            return False

        self._last_trigger_reasons = check_result.trigger_reasons
        self._transition(
            CircuitBreakerEvent.TRIGGER,
            trigger_reason="; ".join(check_result.trigger_reasons),
            details=check_result.to_dict(),
        )
        self._triggered_time = self._time_func()
        return True

    def can_transition(self, event: str) -> bool:
        """检查是否可以转换.

        Args:
            event: 事件名称

        Returns:
            是否可以转换
        """
        return (self._state, event) in VALID_CIRCUIT_BREAKER_TRANSITIONS

    def get_next_state(self, event: str) -> CircuitBreakerState | None:
        """获取下一个状态.

        Args:
            event: 事件名称

        Returns:
            下一个状态，或None如果不可转换
        """
        return VALID_CIRCUIT_BREAKER_TRANSITIONS.get((self._state, event))

    def tick(self) -> CircuitBreakerState:
        """时钟推进.

        根据时间自动推进状态:
        - TRIGGERED + 30s -> COOLING
        - COOLING + 5min -> RECOVERY
        - RECOVERY + step_interval -> 恢复进度推进

        Returns:
            当前状态
        """
        now = self._time_func()

        if self._state == CircuitBreakerState.TRIGGERED:
            if self._triggered_time is not None:
                elapsed = now - self._triggered_time
                if elapsed >= self._recovery_config.cooling_duration_seconds:
                    self._start_cooling()

        elif self._state == CircuitBreakerState.COOLING:
            if self._cooling_start_time is not None:
                elapsed = now - self._cooling_start_time
                if elapsed >= self._recovery_config.full_cooling_duration_seconds:
                    self._start_recovery()

        elif self._state == CircuitBreakerState.RECOVERY:
            self._advance_recovery()

        return self._state

    def manual_override(self, reason: str = "manual intervention") -> bool:
        """人工接管.

        V4 SPEC D2: ANY -> MANUAL_OVERRIDE

        Args:
            reason: 接管原因

        Returns:
            是否成功接管
        """
        if self._state == CircuitBreakerState.MANUAL_OVERRIDE:
            return False

        self._transition(
            CircuitBreakerEvent.MANUAL_OVERRIDE,
            trigger_reason=reason,
            details={"previous_state": self._state.name},
        )
        return True

    def manual_release(self, to_normal: bool = True) -> bool:
        """人工解除.

        V4 SPEC D2: MANUAL_OVERRIDE -> NORMAL/COOLING

        Args:
            to_normal: True则恢复到NORMAL，False则进入COOLING

        Returns:
            是否成功解除
        """
        if self._state != CircuitBreakerState.MANUAL_OVERRIDE:
            return False

        if to_normal:
            self._transition(
                CircuitBreakerEvent.MANUAL_RELEASE,
                trigger_reason="manual release to normal",
                details={"target_state": "NORMAL"},
            )
            self._reset_recovery_progress()
        else:
            self._transition(
                CircuitBreakerEvent.MANUAL_TO_COOLING,
                trigger_reason="manual release to cooling",
                details={"target_state": "COOLING"},
            )
            self._cooling_start_time = self._time_func()

        return True

    def force_state(
        self, state: CircuitBreakerState, reason: str = "forced"
    ) -> None:
        """强制设置状态（仅用于恢复/测试）.

        Args:
            state: 目标状态
            reason: 原因
        """
        from_state = self._state
        self._state = state
        self._state_enter_time = self._time_func()
        self._transition_count += 1

        self._log_audit(
            event_type="circuit_breaker_force",
            from_state=from_state.name,
            to_state=state.name,
            trigger_reason=f"force:{reason}",
            details={"forced": True},
        )

        if self._on_state_change:
            self._on_state_change(from_state, state, f"force:{reason}")

    def get_state_duration(self) -> float:
        """获取当前状态持续时间（秒）.

        Returns:
            持续时间
        """
        return self._time_func() - self._state_enter_time

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            状态信息字典
        """
        return {
            "state": self._state.name,
            "state_value": self._state.value,
            "transition_count": self._transition_count,
            "state_duration": self.get_state_duration(),
            "current_position_ratio": self.current_position_ratio,
            "is_trading_allowed": self.is_trading_allowed,
            "is_new_position_allowed": self.is_new_position_allowed,
            "recovery_progress": self._recovery_progress.to_dict(),
            "last_trigger_reasons": self._last_trigger_reasons,
            "thresholds": self._thresholds_to_dict(),
        }

    def _transition(
        self, event: str, trigger_reason: str, details: dict[str, Any]
    ) -> CircuitBreakerState:
        """执行状态转换.

        Args:
            event: 事件名称
            trigger_reason: 触发原因
            details: 详细信息

        Returns:
            新状态

        Raises:
            TransitionError: 非法转换
        """
        key = (self._state, event)
        if key not in VALID_CIRCUIT_BREAKER_TRANSITIONS:
            raise TransitionError(
                f"Invalid transition: {self._state.name} + {event}"
            )

        from_state = self._state
        to_state = VALID_CIRCUIT_BREAKER_TRANSITIONS[key]
        self._state = to_state
        self._state_enter_time = self._time_func()
        self._transition_count += 1

        # M3军规: 记录审计日志
        self._log_audit(
            event_type="circuit_breaker_transition",
            from_state=from_state.name,
            to_state=to_state.name,
            trigger_reason=trigger_reason,
            details=details,
        )

        if self._on_state_change:
            self._on_state_change(from_state, to_state, trigger_reason)

        return to_state

    def _start_cooling(self) -> None:
        """开始冷却期."""
        self._transition(
            CircuitBreakerEvent.COOLING_START,
            trigger_reason="auto cooling after trigger timeout",
            details={
                "triggered_duration": (
                    self._time_func() - (self._triggered_time or 0)
                )
            },
        )
        self._cooling_start_time = self._time_func()

    def _start_recovery(self) -> None:
        """开始恢复期."""
        self._transition(
            CircuitBreakerEvent.COOLING_COMPLETE,
            trigger_reason="cooling period completed",
            details={
                "cooling_duration": (
                    self._time_func() - (self._cooling_start_time or 0)
                )
            },
        )
        self._reset_recovery_progress()
        self._recovery_progress.current_step = 0
        self._recovery_progress.current_position_ratio = (
            self._recovery_config.position_ratio_steps[0]
        )
        self._recovery_progress.step_start_time = self._time_func()
        self._recovery_progress.total_steps = len(
            self._recovery_config.position_ratio_steps
        )

    def _advance_recovery(self) -> None:
        """推进恢复进度."""
        if self._state != CircuitBreakerState.RECOVERY:
            return

        now = self._time_func()
        elapsed = now - self._recovery_progress.step_start_time

        if elapsed < self._recovery_config.step_interval_seconds:
            return

        next_step = self._recovery_progress.current_step + 1
        total_steps = len(self._recovery_config.position_ratio_steps)

        if next_step >= total_steps:
            # 恢复完成
            self._transition(
                CircuitBreakerEvent.RECOVERY_COMPLETE,
                trigger_reason="recovery completed",
                details={
                    "total_recovery_time": now - self._state_enter_time,
                    "final_step": next_step,
                },
            )
            self._reset_recovery_progress()
        else:
            # 推进到下一步
            self._recovery_progress.current_step = next_step
            self._recovery_progress.current_position_ratio = (
                self._recovery_config.position_ratio_steps[next_step]
            )
            self._recovery_progress.step_start_time = now

            # 记录恢复进度
            self._log_audit(
                event_type="circuit_breaker_recovery_step",
                from_state=self._state.name,
                to_state=self._state.name,
                trigger_reason=f"recovery step {next_step}",
                details={
                    "step": next_step,
                    "position_ratio": self._recovery_progress.current_position_ratio,
                },
            )

    def _reset_recovery_progress(self) -> None:
        """重置恢复进度."""
        self._recovery_progress = RecoveryProgress()
        self._triggered_time = None
        self._cooling_start_time = None
        self._last_trigger_reasons = []

    def _log_audit(
        self,
        event_type: str,
        from_state: str,
        to_state: str,
        trigger_reason: str,
        details: dict[str, Any],
    ) -> None:
        """记录审计日志.

        M3军规: 所有状态转换必须记录.

        Args:
            event_type: 事件类型
            from_state: 原状态
            to_state: 目标状态
            trigger_reason: 触发原因
            details: 详细信息
        """
        self._audit_logger.log(
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            trigger_reason=trigger_reason,
            details=details,
        )

    def _thresholds_to_dict(self) -> dict[str, Any]:
        """阈值转换为字典."""
        return {
            "daily_loss_pct": self._thresholds.daily_loss_pct,
            "position_loss_pct": self._thresholds.position_loss_pct,
            "margin_usage_pct": self._thresholds.margin_usage_pct,
            "consecutive_losses": self._thresholds.consecutive_losses,
        }


class CircuitBreakerManager:
    """熔断器管理器.

    管理多个熔断器实例，支持全局和策略级熔断.
    """

    def __init__(
        self,
        default_thresholds: TriggerThresholds | None = None,
        default_recovery_config: RecoveryConfig | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        """初始化管理器.

        Args:
            default_thresholds: 默认触发阈值
            default_recovery_config: 默认恢复配置
            audit_logger: 审计日志记录器
        """
        self._default_thresholds = default_thresholds or TriggerThresholds()
        self._default_recovery_config = default_recovery_config or RecoveryConfig()
        self._audit_logger = audit_logger or DefaultAuditLogger()
        self._breakers: dict[str, CircuitBreaker] = {}

        # 创建全局熔断器
        self._global_breaker = CircuitBreaker(
            thresholds=self._default_thresholds,
            recovery_config=self._default_recovery_config,
            audit_logger=self._audit_logger,
        )
        self._breakers["global"] = self._global_breaker

    @property
    def global_breaker(self) -> CircuitBreaker:
        """全局熔断器."""
        return self._global_breaker

    def get_breaker(self, name: str) -> CircuitBreaker | None:
        """获取熔断器.

        Args:
            name: 熔断器名称

        Returns:
            熔断器实例，或None
        """
        return self._breakers.get(name)

    def create_breaker(
        self,
        name: str,
        thresholds: TriggerThresholds | None = None,
        recovery_config: RecoveryConfig | None = None,
    ) -> CircuitBreaker:
        """创建熔断器.

        Args:
            name: 熔断器名称
            thresholds: 触发阈值
            recovery_config: 恢复配置

        Returns:
            新创建的熔断器
        """
        breaker = CircuitBreaker(
            thresholds=thresholds or self._default_thresholds,
            recovery_config=recovery_config or self._default_recovery_config,
            audit_logger=self._audit_logger,
        )
        self._breakers[name] = breaker
        return breaker

    def remove_breaker(self, name: str) -> bool:
        """移除熔断器.

        Args:
            name: 熔断器名称

        Returns:
            是否成功移除
        """
        if name == "global":
            return False  # 不允许移除全局熔断器
        if name in self._breakers:
            del self._breakers[name]
            return True
        return False

    def tick_all(self) -> dict[str, CircuitBreakerState]:
        """推进所有熔断器.

        Returns:
            所有熔断器的当前状态
        """
        return {name: breaker.tick() for name, breaker in self._breakers.items()}

    def get_all_states(self) -> dict[str, CircuitBreakerState]:
        """获取所有熔断器状态.

        Returns:
            所有熔断器的当前状态
        """
        return {name: breaker.state for name, breaker in self._breakers.items()}

    def is_any_triggered(self) -> bool:
        """是否有任何熔断器触发.

        Returns:
            是否有熔断器处于非正常状态
        """
        return any(
            breaker.state != CircuitBreakerState.NORMAL
            for breaker in self._breakers.values()
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            管理器状态字典
        """
        return {
            "breakers": {
                name: breaker.to_dict() for name, breaker in self._breakers.items()
            },
            "is_any_triggered": self.is_any_triggered(),
        }
