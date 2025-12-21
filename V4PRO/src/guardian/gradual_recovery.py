"""
GradualRecovery - 渐进式恢复执行器.

V4PRO Platform Component - Phase 10
V4 SPEC: D2 熔断-恢复闭环
V2 Scenarios: GUARD.CIRCUIT_BREAKER.RECOVERY

军规级要求:
- M6: 熔断保护机制完整，恢复过程渐进式
- 恢复策略: position_ratio_steps = [0.25, 0.5, 0.75, 1.0]
- 步进间隔: step_interval_seconds = 60

恢复流程:
1. 熔断触发后进入 COOLING 冷却期 (30秒)
2. 冷却完成后进入 RECOVERY 恢复期
3. 渐进式恢复仓位比例: 25% -> 50% -> 75% -> 100%
4. 每步间隔 60 秒
5. 恢复完成后回到 NORMAL 状态
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from src.guardian.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    RecoveryConfig,
    RecoveryProgress,
)


if TYPE_CHECKING:
    from collections.abc import Callable


class RecoveryStage(Enum):
    """恢复阶段枚举."""

    IDLE = "idle"  # 空闲
    COOLING = "cooling"  # 冷却中
    RECOVERING = "recovering"  # 恢复中
    COMPLETED = "completed"  # 完成


class PositionScaler(Protocol):
    """仓位缩放协议.

    用于调整策略的仓位输出。
    """

    def scale_position(
        self,
        target: dict[str, int],
        ratio: float,
    ) -> dict[str, int]:
        """按比例缩放目标仓位.

        Args:
            target: 原始目标仓位
            ratio: 缩放比例 (0.0 - 1.0)

        Returns:
            缩放后的目标仓位
        """
        ...


class AlertSender(Protocol):
    """告警发送协议."""

    def send_alert(
        self,
        level: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        """发送告警.

        Args:
            level: 告警级别 (INFO/WARN/ERROR/FATAL)
            message: 告警消息
            details: 详细信息
        """
        ...


@dataclass
class RecoveryEvent:
    """恢复事件.

    记录恢复过程中的事件。
    """

    timestamp: float
    event_type: str
    stage: RecoveryStage
    position_ratio: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "stage": self.stage.value,
            "position_ratio": self.position_ratio,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class RecoveryStatus:
    """恢复状态.

    跟踪恢复进度。
    """

    stage: RecoveryStage = RecoveryStage.IDLE
    current_step: int = 0
    total_steps: int = 4
    current_ratio: float = 1.0
    target_ratio: float = 1.0
    stage_start_time: float = 0.0
    recovery_start_time: float = 0.0
    events: list[RecoveryEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "stage": self.stage.value,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_ratio": self.current_ratio,
            "target_ratio": self.target_ratio,
            "stage_start_time": self.stage_start_time,
            "recovery_start_time": self.recovery_start_time,
            "event_count": len(self.events),
        }


class DefaultPositionScaler:
    """默认仓位缩放器."""

    def scale_position(
        self,
        target: dict[str, int],
        ratio: float,
    ) -> dict[str, int]:
        """按比例缩放目标仓位.

        Args:
            target: 原始目标仓位
            ratio: 缩放比例 (0.0 - 1.0)

        Returns:
            缩放后的目标仓位
        """
        if ratio >= 1.0:
            return dict(target)

        scaled: dict[str, int] = {}
        for symbol, qty in target.items():
            # 按比例缩放，取整
            scaled_qty = int(qty * ratio)
            if scaled_qty != 0:
                scaled[symbol] = scaled_qty
            elif qty != 0:
                # 保留最小单位
                scaled[symbol] = 1 if qty > 0 else -1

        return scaled


class DefaultAlertSender:
    """默认告警发送器.

    仅打印告警，实际使用时应替换为真实实现。
    """

    def __init__(self) -> None:
        """初始化告警发送器."""
        self._alerts: list[dict[str, Any]] = []

    @property
    def alerts(self) -> list[dict[str, Any]]:
        """获取所有告警."""
        return self._alerts.copy()

    def send_alert(
        self,
        level: str,
        message: str,
        details: dict[str, Any],
    ) -> None:
        """发送告警.

        Args:
            level: 告警级别
            message: 告警消息
            details: 详细信息
        """
        alert = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "details": details,
        }
        self._alerts.append(alert)

    def clear(self) -> None:
        """清空告警."""
        self._alerts.clear()


class GradualRecoveryExecutor:
    """渐进式恢复执行器.

    V4 SPEC D2: 渐进式恢复

    负责执行渐进式恢复过程，包括:
    - 监控熔断器状态
    - 管理恢复阶段
    - 缩放仓位输出
    - 发送恢复事件告警
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        position_scaler: PositionScaler | None = None,
        alert_sender: AlertSender | None = None,
        recovery_config: RecoveryConfig | None = None,
        on_stage_change: Callable[[RecoveryStage, RecoveryStage], None] | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        """初始化恢复执行器.

        Args:
            circuit_breaker: 熔断器实例
            position_scaler: 仓位缩放器
            alert_sender: 告警发送器
            recovery_config: 恢复配置
            on_stage_change: 阶段变更回调
            time_func: 时间函数（用于测试）
        """
        self._breaker = circuit_breaker
        self._scaler = position_scaler or DefaultPositionScaler()
        self._alerter = alert_sender or DefaultAlertSender()
        self._config = recovery_config or RecoveryConfig()
        self._on_stage_change = on_stage_change
        self._time_func = time_func or time.time

        self._status = RecoveryStatus(
            total_steps=len(self._config.position_ratio_steps),
        )

    @property
    def status(self) -> RecoveryStatus:
        """恢复状态."""
        return self._status

    @property
    def stage(self) -> RecoveryStage:
        """当前阶段."""
        return self._status.stage

    @property
    def current_ratio(self) -> float:
        """当前仓位比例."""
        return self._status.current_ratio

    @property
    def is_recovering(self) -> bool:
        """是否正在恢复中."""
        return self._status.stage in (RecoveryStage.COOLING, RecoveryStage.RECOVERING)

    def get_scaled_position(
        self,
        target: dict[str, int],
    ) -> dict[str, int]:
        """获取缩放后的目标仓位.

        Args:
            target: 原始目标仓位

        Returns:
            缩放后的目标仓位
        """
        # 根据熔断器状态确定比例
        breaker_state = self._breaker.state
        ratio = self._breaker.current_position_ratio

        if breaker_state == CircuitBreakerState.NORMAL:
            return dict(target)
        elif breaker_state in (
            CircuitBreakerState.TRIGGERED,
            CircuitBreakerState.COOLING,
            CircuitBreakerState.MANUAL_OVERRIDE,
        ):
            # 禁止新开仓，只允许减仓
            return {}
        elif breaker_state == CircuitBreakerState.RECOVERY:
            # 渐进式恢复
            return self._scaler.scale_position(target, ratio)

        return {}

    def tick(self) -> RecoveryStage:
        """时钟推进.

        同步熔断器状态，更新恢复阶段。

        Returns:
            当前恢复阶段
        """
        # 先推进熔断器
        self._breaker.tick()

        # 同步状态
        self._sync_with_breaker()

        return self._status.stage

    def _sync_with_breaker(self) -> None:
        """同步熔断器状态."""
        breaker_state = self._breaker.state
        old_stage = self._status.stage
        new_stage = old_stage

        if breaker_state == CircuitBreakerState.NORMAL:
            if old_stage in (RecoveryStage.RECOVERING, RecoveryStage.COOLING):
                new_stage = RecoveryStage.COMPLETED
                self._record_event(
                    "recovery_complete",
                    new_stage,
                    1.0,
                    "恢复完成，回到正常状态",
                )
            elif old_stage == RecoveryStage.COMPLETED:
                new_stage = RecoveryStage.IDLE
            else:
                new_stage = RecoveryStage.IDLE

        elif breaker_state == CircuitBreakerState.TRIGGERED:
            if old_stage != RecoveryStage.COOLING:
                new_stage = RecoveryStage.COOLING
                self._status.stage_start_time = self._time_func()
                self._status.current_ratio = 0.0
                self._record_event(
                    "breaker_triggered",
                    new_stage,
                    0.0,
                    "熔断触发，进入冷却期",
                )
                self._alerter.send_alert(
                    "WARN",
                    "熔断触发",
                    {"stage": new_stage.value, "ratio": 0.0},
                )

        elif breaker_state == CircuitBreakerState.COOLING:
            if old_stage != RecoveryStage.COOLING:
                new_stage = RecoveryStage.COOLING
                self._status.stage_start_time = self._time_func()
                self._status.current_ratio = 0.0
                self._record_event(
                    "cooling_start",
                    new_stage,
                    0.0,
                    "进入冷却期",
                )

        elif breaker_state == CircuitBreakerState.RECOVERY:
            if old_stage != RecoveryStage.RECOVERING:
                new_stage = RecoveryStage.RECOVERING
                self._status.recovery_start_time = self._time_func()
                self._status.stage_start_time = self._time_func()
                self._status.current_step = 0
                self._record_event(
                    "recovery_start",
                    new_stage,
                    self._breaker.current_position_ratio,
                    "开始渐进式恢复",
                )
                self._alerter.send_alert(
                    "INFO",
                    "开始渐进式恢复",
                    {
                        "stage": new_stage.value,
                        "ratio": self._breaker.current_position_ratio,
                    },
                )
            else:
                # 检查是否有恢复进度
                progress = self._breaker.recovery_progress
                if progress.current_step != self._status.current_step:
                    self._status.current_step = progress.current_step
                    self._status.current_ratio = progress.current_position_ratio
                    self._record_event(
                        "recovery_step",
                        new_stage,
                        progress.current_position_ratio,
                        f"恢复进度: {progress.current_step + 1}/{progress.total_steps}",
                        {
                            "step": progress.current_step,
                            "total": progress.total_steps,
                        },
                    )
                    self._alerter.send_alert(
                        "INFO",
                        f"恢复进度: {progress.current_position_ratio:.0%}",
                        {
                            "step": progress.current_step,
                            "ratio": progress.current_position_ratio,
                        },
                    )

        elif breaker_state == CircuitBreakerState.MANUAL_OVERRIDE:
            if old_stage not in (RecoveryStage.IDLE, RecoveryStage.COMPLETED):
                self._record_event(
                    "manual_override",
                    old_stage,
                    0.0,
                    "人工接管，暂停恢复",
                )
                self._alerter.send_alert(
                    "WARN",
                    "人工接管",
                    {"previous_stage": old_stage.value},
                )

        # 更新阶段
        if new_stage != old_stage:
            self._status.stage = new_stage
            self._status.stage_start_time = self._time_func()
            if self._on_stage_change:
                self._on_stage_change(old_stage, new_stage)

        # 同步当前比例
        self._status.current_ratio = self._breaker.current_position_ratio
        self._status.target_ratio = 1.0 if new_stage == RecoveryStage.IDLE else (
            self._config.position_ratio_steps[-1]
            if new_stage == RecoveryStage.RECOVERING
            else 0.0
        )

    def _record_event(
        self,
        event_type: str,
        stage: RecoveryStage,
        ratio: float,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录事件.

        Args:
            event_type: 事件类型
            stage: 阶段
            ratio: 仓位比例
            message: 消息
            details: 详细信息
        """
        event = RecoveryEvent(
            timestamp=self._time_func(),
            event_type=event_type,
            stage=stage,
            position_ratio=ratio,
            message=message,
            details=details or {},
        )
        self._status.events.append(event)

    def reset(self) -> None:
        """重置恢复状态."""
        self._status = RecoveryStatus(
            total_steps=len(self._config.position_ratio_steps),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            状态字典
        """
        return {
            "stage": self._status.stage.value,
            "current_step": self._status.current_step,
            "total_steps": self._status.total_steps,
            "current_ratio": self._status.current_ratio,
            "target_ratio": self._status.target_ratio,
            "is_recovering": self.is_recovering,
            "breaker_state": self._breaker.state.name,
            "event_count": len(self._status.events),
            "recent_events": [
                e.to_dict() for e in self._status.events[-5:]
            ],
        }


class RecoveryCoordinator:
    """恢复协调器.

    协调多个恢复执行器，支持全局恢复管理。
    """

    def __init__(
        self,
        alert_sender: AlertSender | None = None,
    ) -> None:
        """初始化协调器.

        Args:
            alert_sender: 告警发送器
        """
        self._executors: dict[str, GradualRecoveryExecutor] = {}
        self._alerter = alert_sender or DefaultAlertSender()

    def register_executor(
        self,
        name: str,
        executor: GradualRecoveryExecutor,
    ) -> None:
        """注册执行器.

        Args:
            name: 执行器名称
            executor: 执行器实例
        """
        self._executors[name] = executor

    def unregister_executor(self, name: str) -> bool:
        """取消注册执行器.

        Args:
            name: 执行器名称

        Returns:
            是否成功
        """
        if name in self._executors:
            del self._executors[name]
            return True
        return False

    def get_executor(self, name: str) -> GradualRecoveryExecutor | None:
        """获取执行器.

        Args:
            name: 执行器名称

        Returns:
            执行器实例
        """
        return self._executors.get(name)

    def tick_all(self) -> dict[str, RecoveryStage]:
        """推进所有执行器.

        Returns:
            所有执行器的当前阶段
        """
        return {name: executor.tick() for name, executor in self._executors.items()}

    def get_all_stages(self) -> dict[str, RecoveryStage]:
        """获取所有执行器阶段.

        Returns:
            所有执行器的阶段
        """
        return {name: executor.stage for name, executor in self._executors.items()}

    def is_any_recovering(self) -> bool:
        """是否有任何执行器在恢复中.

        Returns:
            是否有恢复中的执行器
        """
        return any(executor.is_recovering for executor in self._executors.values())

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            状态字典
        """
        return {
            "executors": {
                name: executor.to_dict() for name, executor in self._executors.items()
            },
            "is_any_recovering": self.is_any_recovering(),
        }
