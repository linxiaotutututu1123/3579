"""
CircuitBreaker Triggers - 熔断触发器 (与TriggerManager兼容).

V4PRO Platform Component - Phase 10
V4 SPEC: D2 熔断-恢复闭环
V2 Scenarios: GUARD.CIRCUIT_BREAKER.TRIGGERS

军规级要求:
- M6: 熔断保护机制完整，触发条件明确
- 与现有 TriggerManager 无缝集成
- 支持 BaseTrigger 接口

触发条件:
- daily_loss_pct > 0.03 (日损失>3%)
- position_loss_pct > 0.05 (持仓损失>5%)
- margin_usage_pct > 0.85 (保证金使用率>85%)
- consecutive_losses >= 5 (连续亏损>=5次)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.guardian.circuit_breaker import (
    CircuitBreakerMetrics,
    TriggerCheckResult,
    TriggerThresholds,
)
from src.guardian.triggers import BaseTrigger, TriggerResult


@dataclass
class RiskMetricsCollector:
    """风险指标收集器.

    负责从交易状态中计算风险指标。
    """

    # 日初净值 (用于计算日损失)
    day_start_equity: float = 0.0

    # 当前权益
    current_equity: float = 0.0

    # 持仓成本
    position_cost: float = 0.0

    # 持仓市值
    position_value: float = 0.0

    # 保证金使用
    margin_used: float = 0.0

    # 可用保证金
    margin_available: float = 0.0

    # 连续亏损次数
    consecutive_losses: int = 0

    # 交易记录 (用于计算连续亏损)
    recent_trades: list[dict[str, Any]] = field(default_factory=list)

    def calculate_metrics(self) -> CircuitBreakerMetrics:
        """计算熔断指标.

        Returns:
            熔断指标
        """
        # 计算日损失百分比
        daily_loss_pct = 0.0
        if self.day_start_equity > 0:
            daily_loss_pct = max(
                0.0,
                (self.day_start_equity - self.current_equity) / self.day_start_equity,
            )

        # 计算持仓损失百分比
        position_loss_pct = 0.0
        if self.position_cost > 0:
            position_loss_pct = max(
                0.0, (self.position_cost - self.position_value) / self.position_cost
            )

        # 计算保证金使用率
        margin_usage_pct = 0.0
        total_margin = self.margin_used + self.margin_available
        if total_margin > 0:
            margin_usage_pct = self.margin_used / total_margin

        return CircuitBreakerMetrics(
            daily_loss_pct=daily_loss_pct,
            position_loss_pct=position_loss_pct,
            margin_usage_pct=margin_usage_pct,
            consecutive_losses=self.consecutive_losses,
        )

    def update_from_state(self, state: dict[str, Any]) -> None:
        """从状态字典更新指标.

        Args:
            state: 状态字典，可包含:
                - day_start_equity: 日初净值
                - current_equity: 当前权益
                - position_cost: 持仓成本
                - position_value: 持仓市值
                - margin_used: 已用保证金
                - margin_available: 可用保证金
                - consecutive_losses: 连续亏损次数
                - recent_trades: 最近交易记录
        """
        self.day_start_equity = state.get("day_start_equity", self.day_start_equity)
        self.current_equity = state.get("current_equity", self.current_equity)
        self.position_cost = state.get("position_cost", self.position_cost)
        self.position_value = state.get("position_value", self.position_value)
        self.margin_used = state.get("margin_used", self.margin_used)
        self.margin_available = state.get("margin_available", self.margin_available)
        self.consecutive_losses = state.get(
            "consecutive_losses", self.consecutive_losses
        )
        self.recent_trades = state.get("recent_trades", self.recent_trades)

    def record_trade_result(self, pnl: float) -> None:
        """记录交易结果.

        Args:
            pnl: 盈亏金额
        """
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_daily(self, equity: float) -> None:
        """重置日内数据.

        Args:
            equity: 新的日初净值
        """
        self.day_start_equity = equity
        self.current_equity = equity


class DailyLossTrigger(BaseTrigger):
    """日亏损触发器.

    V4 SPEC D2: daily_loss_pct > 0.03

    检测日亏损是否超过阈值。
    """

    def __init__(self, threshold: float = 0.03) -> None:
        """初始化日亏损触发器.

        Args:
            threshold: 日亏损阈值 (默认 0.03 即 3%)
        """
        self._threshold = threshold
        self._last_loss_pct: float = 0.0

    @property
    def name(self) -> str:
        """触发器名称."""
        return "daily_loss"

    @property
    def threshold(self) -> float:
        """阈值."""
        return self._threshold

    @property
    def last_loss_pct(self) -> float:
        """最后检测的亏损百分比."""
        return self._last_loss_pct

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查日亏损.

        Args:
            state: 状态字典，需包含:
                - day_start_equity: float 日初净值
                - current_equity: float 当前权益

        Returns:
            检测结果
        """
        day_start_equity = state.get("day_start_equity", 0.0)
        current_equity = state.get("current_equity", 0.0)

        # 计算日亏损百分比
        if day_start_equity > 0:
            self._last_loss_pct = max(
                0.0, (day_start_equity - current_equity) / day_start_equity
            )
        else:
            self._last_loss_pct = 0.0

        triggered = self._last_loss_pct > self._threshold

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="circuit_breaker_trigger",
            details={
                "trigger_type": "daily_loss",
                "loss_pct": self._last_loss_pct,
                "loss_pct_str": f"{self._last_loss_pct:.2%}",
                "threshold": self._threshold,
                "threshold_str": f"{self._threshold:.2%}",
                "day_start_equity": day_start_equity,
                "current_equity": current_equity,
            },
        )

    def reset(self) -> None:
        """重置触发器状态."""
        self._last_loss_pct = 0.0


class PositionLossTrigger(BaseTrigger):
    """持仓亏损触发器.

    V4 SPEC D2: position_loss_pct > 0.05

    检测单一持仓亏损是否超过阈值。
    """

    def __init__(self, threshold: float = 0.05) -> None:
        """初始化持仓亏损触发器.

        Args:
            threshold: 持仓亏损阈值 (默认 0.05 即 5%)
        """
        self._threshold = threshold
        self._max_loss_pct: float = 0.0
        self._triggered_positions: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        """触发器名称."""
        return "position_loss"

    @property
    def threshold(self) -> float:
        """阈值."""
        return self._threshold

    @property
    def max_loss_pct(self) -> float:
        """最大亏损百分比."""
        return self._max_loss_pct

    @property
    def triggered_positions(self) -> list[dict[str, Any]]:
        """触发的持仓列表."""
        return self._triggered_positions.copy()

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查持仓亏损.

        Args:
            state: 状态字典，需包含:
                - positions: list[dict] 持仓列表
                  每个持仓包含 {symbol, cost, value, qty}

        Returns:
            检测结果
        """
        positions = state.get("positions", [])
        self._triggered_positions.clear()
        self._max_loss_pct = 0.0

        for pos in positions:
            cost = pos.get("cost", 0.0)
            value = pos.get("value", 0.0)
            qty = pos.get("qty", 0)

            if cost <= 0 or qty == 0:
                continue

            # 计算持仓亏损百分比
            loss_pct = max(0.0, (cost - value) / cost)
            self._max_loss_pct = max(self._max_loss_pct, loss_pct)

            if loss_pct > self._threshold:
                self._triggered_positions.append(
                    {
                        "symbol": pos.get("symbol", "unknown"),
                        "cost": cost,
                        "value": value,
                        "qty": qty,
                        "loss_pct": loss_pct,
                        "loss_pct_str": f"{loss_pct:.2%}",
                    }
                )

        triggered = len(self._triggered_positions) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="circuit_breaker_trigger",
            details={
                "trigger_type": "position_loss",
                "max_loss_pct": self._max_loss_pct,
                "max_loss_pct_str": f"{self._max_loss_pct:.2%}",
                "threshold": self._threshold,
                "threshold_str": f"{self._threshold:.2%}",
                "triggered_count": len(self._triggered_positions),
                "triggered_positions": self._triggered_positions,
            },
        )

    def reset(self) -> None:
        """重置触发器状态."""
        self._max_loss_pct = 0.0
        self._triggered_positions.clear()


class MarginUsageTrigger(BaseTrigger):
    """保证金使用率触发器.

    V4 SPEC D2: margin_usage_pct > 0.85

    检测保证金使用率是否超过阈值。
    """

    def __init__(self, threshold: float = 0.85) -> None:
        """初始化保证金使用率触发器.

        Args:
            threshold: 保证金使用率阈值 (默认 0.85 即 85%)
        """
        self._threshold = threshold
        self._last_usage_pct: float = 0.0

    @property
    def name(self) -> str:
        """触发器名称."""
        return "margin_usage"

    @property
    def threshold(self) -> float:
        """阈值."""
        return self._threshold

    @property
    def last_usage_pct(self) -> float:
        """最后检测的使用率."""
        return self._last_usage_pct

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查保证金使用率.

        Args:
            state: 状态字典，需包含:
                - margin_used: float 已用保证金
                - margin_available: float 可用保证金
                或:
                - equity: float 账户权益
                - margin_used: float 已用保证金

        Returns:
            检测结果
        """
        margin_used = state.get("margin_used", 0.0)

        # 计算总保证金
        if "margin_available" in state:
            total_margin = margin_used + state["margin_available"]
        elif "equity" in state:
            total_margin = state["equity"]
        else:
            total_margin = 0.0

        # 计算使用率
        if total_margin > 0:
            self._last_usage_pct = margin_used / total_margin
        else:
            self._last_usage_pct = 1.0 if margin_used > 0 else 0.0

        triggered = self._last_usage_pct > self._threshold

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="circuit_breaker_trigger",
            details={
                "trigger_type": "margin_usage",
                "usage_pct": self._last_usage_pct,
                "usage_pct_str": f"{self._last_usage_pct:.2%}",
                "threshold": self._threshold,
                "threshold_str": f"{self._threshold:.2%}",
                "margin_used": margin_used,
                "total_margin": total_margin,
            },
        )

    def reset(self) -> None:
        """重置触发器状态."""
        self._last_usage_pct = 0.0


class ConsecutiveLossTrigger(BaseTrigger):
    """连续亏损触发器.

    V4 SPEC D2: consecutive_losses >= 5

    检测连续亏损次数是否超过阈值。
    """

    def __init__(self, threshold: int = 5) -> None:
        """初始化连续亏损触发器.

        Args:
            threshold: 连续亏损次数阈值 (默认 5)
        """
        self._threshold = threshold
        self._current_count: int = 0

    @property
    def name(self) -> str:
        """触发器名称."""
        return "consecutive_loss"

    @property
    def threshold(self) -> int:
        """阈值."""
        return self._threshold

    @property
    def current_count(self) -> int:
        """当前连续亏损次数."""
        return self._current_count

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查连续亏损.

        Args:
            state: 状态字典，需包含:
                - consecutive_losses: int 连续亏损次数

        Returns:
            检测结果
        """
        self._current_count = state.get("consecutive_losses", 0)
        triggered = self._current_count >= self._threshold

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="circuit_breaker_trigger",
            details={
                "trigger_type": "consecutive_loss",
                "count": self._current_count,
                "threshold": self._threshold,
            },
        )

    def reset(self) -> None:
        """重置触发器状态."""
        self._current_count = 0


class CircuitBreakerRiskTrigger(BaseTrigger):
    """熔断风险综合触发器.

    V4 SPEC D2: 综合所有熔断触发条件

    整合所有风险触发条件，任一条件满足即触发。
    """

    def __init__(
        self,
        thresholds: TriggerThresholds | None = None,
    ) -> None:
        """初始化熔断风险触发器.

        Args:
            thresholds: 触发阈值配置
        """
        self._thresholds = thresholds or TriggerThresholds()
        self._sub_triggers = [
            DailyLossTrigger(self._thresholds.daily_loss_pct),
            PositionLossTrigger(self._thresholds.position_loss_pct),
            MarginUsageTrigger(self._thresholds.margin_usage_pct),
            ConsecutiveLossTrigger(self._thresholds.consecutive_losses),
        ]
        self._last_check_result: TriggerCheckResult | None = None

    @property
    def name(self) -> str:
        """触发器名称."""
        return "circuit_breaker_risk"

    @property
    def thresholds(self) -> TriggerThresholds:
        """阈值配置."""
        return self._thresholds

    @property
    def last_check_result(self) -> TriggerCheckResult | None:
        """最后检测结果."""
        return self._last_check_result

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查所有风险条件.

        Args:
            state: 状态字典，包含所有子触发器需要的数据

        Returns:
            检测结果
        """
        triggered_results: list[TriggerResult] = []
        trigger_reasons: list[str] = []

        for sub_trigger in self._sub_triggers:
            result = sub_trigger.check(state)
            if result.triggered:
                triggered_results.append(result)
                trigger_type = result.details.get("trigger_type", sub_trigger.name)
                if trigger_type == "daily_loss":
                    trigger_reasons.append(
                        f"日亏损{result.details.get('loss_pct_str', 'N/A')} > "
                        f"阈值{result.details.get('threshold_str', 'N/A')}"
                    )
                elif trigger_type == "position_loss":
                    trigger_reasons.append(
                        f"持仓亏损{result.details.get('max_loss_pct_str', 'N/A')} > "
                        f"阈值{result.details.get('threshold_str', 'N/A')}"
                    )
                elif trigger_type == "margin_usage":
                    trigger_reasons.append(
                        f"保证金使用率{result.details.get('usage_pct_str', 'N/A')} > "
                        f"阈值{result.details.get('threshold_str', 'N/A')}"
                    )
                elif trigger_type == "consecutive_loss":
                    trigger_reasons.append(
                        f"连续亏损{result.details.get('count', 0)}次 >= "
                        f"阈值{result.details.get('threshold', 0)}次"
                    )

        # 收集指标
        metrics = self._collect_metrics(state)
        self._last_check_result = TriggerCheckResult(
            should_trigger=len(triggered_results) > 0,
            trigger_reasons=trigger_reasons,
            metrics=metrics,
        )

        return TriggerResult(
            triggered=len(triggered_results) > 0,
            trigger_name=self.name,
            event_name="circuit_breaker_trigger",
            details={
                "trigger_reasons": trigger_reasons,
                "triggered_count": len(triggered_results),
                "metrics": metrics.to_dict(),
                "sub_trigger_details": [r.details for r in triggered_results],
            },
        )

    def _collect_metrics(self, state: dict[str, Any]) -> CircuitBreakerMetrics:
        """收集风险指标.

        Args:
            state: 状态字典

        Returns:
            熔断指标
        """
        collector = RiskMetricsCollector()
        collector.update_from_state(state)
        return collector.calculate_metrics()

    def reset(self) -> None:
        """重置触发器状态."""
        for trigger in self._sub_triggers:
            trigger.reset()
        self._last_check_result = None


def create_circuit_breaker_triggers(
    thresholds: TriggerThresholds | None = None,
) -> list[BaseTrigger]:
    """创建熔断触发器列表.

    Args:
        thresholds: 触发阈值配置

    Returns:
        触发器列表
    """
    thresholds = thresholds or TriggerThresholds()
    return [
        DailyLossTrigger(thresholds.daily_loss_pct),
        PositionLossTrigger(thresholds.position_loss_pct),
        MarginUsageTrigger(thresholds.margin_usage_pct),
        ConsecutiveLossTrigger(thresholds.consecutive_losses),
    ]


def register_circuit_breaker_triggers(
    manager: Any,
    thresholds: TriggerThresholds | None = None,
) -> list[str]:
    """注册熔断触发器到管理器.

    Args:
        manager: TriggerManager 实例
        thresholds: 触发阈值配置

    Returns:
        已注册的触发器名称列表
    """
    triggers = create_circuit_breaker_triggers(thresholds)
    names = []
    for trigger in triggers:
        manager.add_trigger(trigger)
        names.append(trigger.name)
    return names
