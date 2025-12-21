"""
CircuitBreakerController - 熔断恢复闭环控制器.

V4PRO Platform Component - Phase 10
V4 SPEC: D2 熔断-恢复闭环
V2 Scenarios: GUARD.CIRCUIT_BREAKER.CONTROLLER

军规级要求:
- M3: 审计日志完整，全程追踪
- M6: 熔断保护机制完整，闭环控制

控制流程:
1. 风险监控 -> 检测触发条件
2. 熔断触发 -> NORMAL -> TRIGGERED
3. 冷却期 -> TRIGGERED -> COOLING (30s)
4. 恢复期 -> COOLING -> RECOVERY
5. 渐进恢复 -> [0.25, 0.5, 0.75, 1.0] (每步60s)
6. 恢复完成 -> RECOVERY -> NORMAL

本模块整合:
- CircuitBreaker: 状态机
- CircuitBreakerRiskTrigger: 触发检测
- GradualRecoveryExecutor: 恢复执行
- AlertSender: 告警通知
- AuditLogger: 审计日志
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.guardian.circuit_breaker import (
    AuditLogger,
    CircuitBreaker,
    CircuitBreakerMetrics,
    CircuitBreakerState,
    DefaultAuditLogger,
    RecoveryConfig,
    TriggerThresholds,
)
from src.guardian.circuit_breaker_triggers import (
    CircuitBreakerRiskTrigger,
    RiskMetricsCollector,
)
from src.guardian.gradual_recovery import (
    AlertSender,
    DefaultAlertSender,
    GradualRecoveryExecutor,
    RecoveryStage,
)


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ControllerStatus:
    """控制器状态.

    Attributes:
        breaker_state: 熔断器状态
        recovery_stage: 恢复阶段
        position_ratio: 仓位比例
        is_trading_allowed: 是否允许交易
        is_new_position_allowed: 是否允许新开仓
        last_check_time: 最后检查时间
        last_trigger_reasons: 最后触发原因
        metrics: 当前风险指标
    """

    breaker_state: CircuitBreakerState = CircuitBreakerState.NORMAL
    recovery_stage: RecoveryStage = RecoveryStage.IDLE
    position_ratio: float = 1.0
    is_trading_allowed: bool = True
    is_new_position_allowed: bool = True
    last_check_time: float = 0.0
    last_trigger_reasons: list[str] = field(default_factory=list)
    metrics: CircuitBreakerMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "breaker_state": self.breaker_state.name,
            "recovery_stage": self.recovery_stage.value,
            "position_ratio": self.position_ratio,
            "is_trading_allowed": self.is_trading_allowed,
            "is_new_position_allowed": self.is_new_position_allowed,
            "last_check_time": self.last_check_time,
            "last_trigger_reasons": self.last_trigger_reasons,
            "metrics": self.metrics.to_dict() if self.metrics else None,
        }


class CircuitBreakerController:
    """熔断恢复闭环控制器.

    V4 SPEC D2: 完整的熔断-恢复闭环

    整合:
    - 风险触发检测
    - 熔断状态机
    - 渐进式恢复
    - 告警通知
    - 审计日志

    使用示例:
        >>> controller = CircuitBreakerController()
        >>> # 更新风险数据
        >>> state = {
        ...     "day_start_equity": 100000,
        ...     "current_equity": 95000,  # 5% 亏损
        ...     "margin_used": 80000,
        ...     "margin_available": 20000,
        ...     "consecutive_losses": 3,
        ... }
        >>> # 执行检查
        >>> status = controller.check(state)
        >>> # 获取目标仓位
        >>> scaled = controller.get_scaled_position({"rb2501": 10})
    """

    def __init__(
        self,
        thresholds: TriggerThresholds | None = None,
        recovery_config: RecoveryConfig | None = None,
        audit_logger: AuditLogger | None = None,
        alert_sender: AlertSender | None = None,
        on_state_change: Callable[
            [CircuitBreakerState, CircuitBreakerState, str], None
        ]
        | None = None,
        on_recovery_stage_change: Callable[
            [RecoveryStage, RecoveryStage], None
        ]
        | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        """初始化控制器.

        Args:
            thresholds: 触发阈值配置
            recovery_config: 恢复策略配置
            audit_logger: 审计日志记录器
            alert_sender: 告警发送器
            on_state_change: 状态变更回调
            on_recovery_stage_change: 恢复阶段变更回调
            time_func: 时间函数（用于测试）
        """
        self._thresholds = thresholds or TriggerThresholds()
        self._recovery_config = recovery_config or RecoveryConfig()
        self._audit_logger = audit_logger or DefaultAuditLogger()
        self._alert_sender = alert_sender or DefaultAlertSender()
        self._on_state_change = on_state_change
        self._on_recovery_stage_change = on_recovery_stage_change
        self._time_func = time_func or time.time

        # 创建熔断器
        self._breaker = CircuitBreaker(
            thresholds=self._thresholds,
            recovery_config=self._recovery_config,
            audit_logger=self._audit_logger,
            on_state_change=self._handle_state_change,
            time_func=self._time_func,
        )

        # 创建风险触发器
        self._risk_trigger = CircuitBreakerRiskTrigger(self._thresholds)

        # 创建恢复执行器
        self._recovery_executor = GradualRecoveryExecutor(
            circuit_breaker=self._breaker,
            alert_sender=self._alert_sender,
            recovery_config=self._recovery_config,
            on_stage_change=self._handle_recovery_stage_change,
            time_func=self._time_func,
        )

        # 指标收集器
        self._metrics_collector = RiskMetricsCollector()

        # 状态
        self._status = ControllerStatus()
        self._enabled = True

    @property
    def breaker(self) -> CircuitBreaker:
        """熔断器实例."""
        return self._breaker

    @property
    def status(self) -> ControllerStatus:
        """控制器状态."""
        return self._status

    @property
    def is_enabled(self) -> bool:
        """是否启用."""
        return self._enabled

    @property
    def state(self) -> CircuitBreakerState:
        """熔断器状态."""
        return self._breaker.state

    @property
    def recovery_stage(self) -> RecoveryStage:
        """恢复阶段."""
        return self._recovery_executor.stage

    @property
    def position_ratio(self) -> float:
        """当前仓位比例."""
        return self._breaker.current_position_ratio

    @property
    def is_trading_allowed(self) -> bool:
        """是否允许交易."""
        return self._breaker.is_trading_allowed

    @property
    def is_new_position_allowed(self) -> bool:
        """是否允许新开仓."""
        return self._breaker.is_new_position_allowed

    def enable(self) -> None:
        """启用控制器."""
        self._enabled = True
        self._log_audit("controller_enabled", "控制器启用")

    def disable(self) -> None:
        """禁用控制器."""
        self._enabled = False
        self._log_audit("controller_disabled", "控制器禁用")

    def check(self, state: dict[str, Any]) -> ControllerStatus:
        """执行风险检查.

        Args:
            state: 状态字典，包含风险数据:
                - day_start_equity: 日初净值
                - current_equity: 当前权益
                - position_cost: 持仓成本
                - position_value: 持仓市值
                - positions: 持仓列表 (可选)
                - margin_used: 已用保证金
                - margin_available: 可用保证金
                - consecutive_losses: 连续亏损次数

        Returns:
            控制器状态
        """
        now = self._time_func()
        self._status.last_check_time = now

        if not self._enabled:
            return self._status

        # 更新指标收集器
        self._metrics_collector.update_from_state(state)
        metrics = self._metrics_collector.calculate_metrics()
        self._status.metrics = metrics

        # 检查触发条件
        if self._breaker.state == CircuitBreakerState.NORMAL:
            trigger_result = self._risk_trigger.check(state)
            if trigger_result.triggered:
                # 触发熔断
                triggered = self._breaker.trigger(metrics)
                if triggered:
                    self._status.last_trigger_reasons = trigger_result.details.get(
                        "trigger_reasons", []
                    )
                    self._alert_sender.send_alert(
                        "ERROR",
                        "熔断触发",
                        {
                            "reasons": self._status.last_trigger_reasons,
                            "metrics": metrics.to_dict(),
                        },
                    )

        # 推进恢复执行器
        self._recovery_executor.tick()

        # 更新状态
        self._update_status()

        return self._status

    def tick(self) -> ControllerStatus:
        """时钟推进.

        仅推进状态机，不检查触发条件。

        Returns:
            控制器状态
        """
        if not self._enabled:
            return self._status

        # 推进恢复执行器 (内部会推进熔断器)
        self._recovery_executor.tick()

        # 更新状态
        self._update_status()

        return self._status

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
        if not self._enabled:
            return dict(target)

        return self._recovery_executor.get_scaled_position(target)

    def filter_target_portfolio(
        self,
        target: dict[str, int],
        current: dict[str, int],
    ) -> dict[str, int]:
        """根据当前状态过滤目标仓位.

        Args:
            target: 策略输出的目标仓位
            current: 当前持仓

        Returns:
            过滤后的目标仓位
        """
        if not self._enabled:
            return dict(target)

        state = self._breaker.state

        # NORMAL: 允许完整目标
        if state == CircuitBreakerState.NORMAL:
            return dict(target)

        # TRIGGERED/COOLING/MANUAL: 仅允许减仓
        if state in (
            CircuitBreakerState.TRIGGERED,
            CircuitBreakerState.COOLING,
            CircuitBreakerState.MANUAL_OVERRIDE,
        ):
            return self._filter_reduce_only(target, current)

        # RECOVERY: 渐进式恢复
        if state == CircuitBreakerState.RECOVERY:
            scaled = self.get_scaled_position(target)
            return self._filter_reduce_or_scaled(scaled, current)

        return dict(current)

    def manual_override(self, reason: str = "manual intervention") -> bool:
        """人工接管.

        Args:
            reason: 接管原因

        Returns:
            是否成功
        """
        result = self._breaker.manual_override(reason)
        if result:
            self._alert_sender.send_alert(
                "WARN",
                "人工接管",
                {"reason": reason},
            )
        return result

    def manual_release(self, to_normal: bool = True) -> bool:
        """人工解除.

        Args:
            to_normal: True 则恢复到 NORMAL，False 则进入 COOLING

        Returns:
            是否成功
        """
        result = self._breaker.manual_release(to_normal)
        if result:
            target = "NORMAL" if to_normal else "COOLING"
            self._alert_sender.send_alert(
                "INFO",
                f"人工解除，进入 {target}",
                {"to_normal": to_normal},
            )
        return result

    def reset(self) -> None:
        """重置控制器."""
        self._breaker.force_state(CircuitBreakerState.NORMAL, "controller_reset")
        self._recovery_executor.reset()
        self._metrics_collector = RiskMetricsCollector()
        self._status = ControllerStatus()
        self._log_audit("controller_reset", "控制器重置")

    def record_trade_result(self, pnl: float) -> None:
        """记录交易结果.

        用于更新连续亏损计数。

        Args:
            pnl: 盈亏金额
        """
        self._metrics_collector.record_trade_result(pnl)

    def reset_daily(self, equity: float) -> None:
        """重置日内数据.

        每日开盘时调用。

        Args:
            equity: 日初净值
        """
        self._metrics_collector.reset_daily(equity)
        self._log_audit(
            "daily_reset",
            "日内数据重置",
            {"day_start_equity": equity},
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            控制器状态字典
        """
        return {
            "enabled": self._enabled,
            "status": self._status.to_dict(),
            "breaker": self._breaker.to_dict(),
            "recovery": self._recovery_executor.to_dict(),
            "thresholds": {
                "daily_loss_pct": self._thresholds.daily_loss_pct,
                "position_loss_pct": self._thresholds.position_loss_pct,
                "margin_usage_pct": self._thresholds.margin_usage_pct,
                "consecutive_losses": self._thresholds.consecutive_losses,
            },
            "recovery_config": {
                "position_ratio_steps": list(
                    self._recovery_config.position_ratio_steps
                ),
                "step_interval_seconds": self._recovery_config.step_interval_seconds,
                "cooling_duration_seconds": (
                    self._recovery_config.cooling_duration_seconds
                ),
            },
        }

    def _update_status(self) -> None:
        """更新状态."""
        self._status.breaker_state = self._breaker.state
        self._status.recovery_stage = self._recovery_executor.stage
        self._status.position_ratio = self._breaker.current_position_ratio
        self._status.is_trading_allowed = self._breaker.is_trading_allowed
        self._status.is_new_position_allowed = self._breaker.is_new_position_allowed

    def _handle_state_change(
        self,
        from_state: CircuitBreakerState,
        to_state: CircuitBreakerState,
        reason: str,
    ) -> None:
        """处理状态变更."""
        if self._on_state_change:
            self._on_state_change(from_state, to_state, reason)

    def _handle_recovery_stage_change(
        self,
        from_stage: RecoveryStage,
        to_stage: RecoveryStage,
    ) -> None:
        """处理恢复阶段变更."""
        if self._on_recovery_stage_change:
            self._on_recovery_stage_change(from_stage, to_stage)

    def _filter_reduce_only(
        self,
        target: dict[str, int],
        current: dict[str, int],
    ) -> dict[str, int]:
        """仅允许减仓过滤.

        Args:
            target: 目标仓位
            current: 当前仓位

        Returns:
            过滤后仓位
        """
        filtered: dict[str, int] = {}
        all_symbols = set(target.keys()) | set(current.keys())

        for symbol in all_symbols:
            target_qty = target.get(symbol, 0)
            current_qty = current.get(symbol, 0)

            if current_qty == 0:
                # 无持仓，不允许开仓
                filtered[symbol] = 0
            elif current_qty > 0:
                # 多头：只允许减仓 (target <= current)
                filtered[symbol] = max(0, min(target_qty, current_qty))
            else:
                # 空头：只允许减仓 (target >= current)
                filtered[symbol] = min(0, max(target_qty, current_qty))

        return filtered

    def _filter_reduce_or_scaled(
        self,
        scaled: dict[str, int],
        current: dict[str, int],
    ) -> dict[str, int]:
        """减仓或缩放过滤.

        Args:
            scaled: 缩放后目标
            current: 当前仓位

        Returns:
            过滤后仓位
        """
        filtered: dict[str, int] = {}
        all_symbols = set(scaled.keys()) | set(current.keys())

        for symbol in all_symbols:
            scaled_qty = scaled.get(symbol, 0)
            current_qty = current.get(symbol, 0)

            if current_qty == 0:
                # 无持仓，允许按缩放比例开仓
                filtered[symbol] = scaled_qty
            elif current_qty > 0:
                # 多头：允许缩放后目标，但不超过当前持仓太多
                filtered[symbol] = min(scaled_qty, current_qty * 2)
            else:
                # 空头：允许缩放后目标，但不超过当前持仓太多
                filtered[symbol] = max(scaled_qty, current_qty * 2)

        return filtered

    def _log_audit(
        self,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录审计日志.

        Args:
            event_type: 事件类型
            message: 消息
            details: 详细信息
        """
        self._audit_logger.log(
            event_type=f"controller_{event_type}",
            from_state=self._breaker.state.name,
            to_state=self._breaker.state.name,
            trigger_reason=message,
            details=details or {},
        )


def create_default_controller(
    on_state_change: Callable[
        [CircuitBreakerState, CircuitBreakerState, str], None
    ]
    | None = None,
    on_recovery_stage_change: Callable[
        [RecoveryStage, RecoveryStage], None
    ]
    | None = None,
) -> CircuitBreakerController:
    """创建默认控制器.

    使用 D2 设计文档中的默认配置:
    - daily_loss_pct: 0.03 (3%)
    - position_loss_pct: 0.05 (5%)
    - margin_usage_pct: 0.85 (85%)
    - consecutive_losses: 5
    - position_ratio_steps: [0.25, 0.5, 0.75, 1.0]
    - step_interval_seconds: 60
    - cooling_duration_seconds: 30

    Args:
        on_state_change: 状态变更回调
        on_recovery_stage_change: 恢复阶段变更回调

    Returns:
        控制器实例
    """
    return CircuitBreakerController(
        thresholds=TriggerThresholds(
            daily_loss_pct=0.03,
            position_loss_pct=0.05,
            margin_usage_pct=0.85,
            consecutive_losses=5,
        ),
        recovery_config=RecoveryConfig(
            position_ratio_steps=(0.25, 0.5, 0.75, 1.0),
            step_interval_seconds=60.0,
            cooling_duration_seconds=30.0,
            full_cooling_duration_seconds=300.0,
        ),
        on_state_change=on_state_change,
        on_recovery_stage_change=on_recovery_stage_change,
    )
