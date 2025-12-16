"""
Guardian Actions - 动作执行

V3PRO+ Platform Component - Phase 1
V2 SPEC: 6.3
V2 Scenarios:
- GUARD.ACTION.SET_MODE: set_mode 动作
- GUARD.ACTION.CANCEL_ALL: cancel_all 动作
- GUARD.ACTION.FLATTEN_ALL: flatten_all 动作

军规级要求:
- 动作必须是幂等的
- 动作必须写入审计日志
- 动作必须有超时保护
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol


if TYPE_CHECKING:
    from src.guardian.state_machine import GuardianMode


class ActionType(str, Enum):
    """动作类型."""

    SET_MODE = "set_mode"
    CANCEL_ALL = "cancel_all"
    FLATTEN_ALL = "flatten_all"
    SEND_ALERT = "send_alert"


class ActionStatus(str, Enum):
    """动作执行状态."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ActionResult:
    """动作执行结果.

    Attributes:
        action_type: 动作类型
        status: 执行状态
        success: 是否成功
        message: 结果消息
        details: 详细信息
    """

    action_type: ActionType
    status: ActionStatus
    success: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class BrokerProtocol(Protocol):
    """Broker 协议，用于类型提示."""

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单."""
        ...

    def get_active_orders(self) -> list[dict[str, Any]]:
        """获取活动订单."""
        ...


class GuardianActions:
    """Guardian 动作执行器.

    V2 Scenarios:
    - GUARD.ACTION.SET_MODE
    - GUARD.ACTION.CANCEL_ALL
    - GUARD.ACTION.FLATTEN_ALL

    执行 Guardian 的各种动作。
    """

    def __init__(
        self,
        cancel_order_fn: Any | None = None,
        get_active_orders_fn: Any | None = None,
        flatten_fn: Any | None = None,
        send_alert_fn: Any | None = None,
        on_action: Any | None = None,
    ) -> None:
        """初始化动作执行器.

        Args:
            cancel_order_fn: 撤单函数 (order_id) -> bool
            get_active_orders_fn: 获取活动订单函数 () -> list[dict]
            flatten_fn: 平仓函数 (symbol, qty) -> bool
            send_alert_fn: 发送告警函数 (message, level) -> None
            on_action: 动作回调 (ActionResult) -> None
        """
        self._cancel_order_fn = cancel_order_fn
        self._get_active_orders_fn = get_active_orders_fn
        self._flatten_fn = flatten_fn
        self._send_alert_fn = send_alert_fn
        self._on_action = on_action

    def set_mode(self, mode: GuardianMode, trigger: str) -> ActionResult:
        """设置 Guardian 模式.

        V2 Scenario: GUARD.ACTION.SET_MODE

        Args:
            mode: 目标模式
            trigger: 触发原因

        Returns:
            动作结果
        """
        result = ActionResult(
            action_type=ActionType.SET_MODE,
            status=ActionStatus.COMPLETED,
            success=True,
            message=f"Mode set to {mode.name}",
            details={
                "mode": mode.name,
                "mode_value": mode.value,
                "trigger": trigger,
            },
        )

        if self._on_action:
            self._on_action(result)

        return result

    def cancel_all(self) -> ActionResult:
        """撤销所有活动订单.

        V2 Scenario: GUARD.ACTION.CANCEL_ALL

        Returns:
            动作结果
        """
        if not self._get_active_orders_fn or not self._cancel_order_fn:
            return ActionResult(
                action_type=ActionType.CANCEL_ALL,
                status=ActionStatus.FAILED,
                success=False,
                message="Cancel functions not configured",
            )

        try:
            active_orders = self._get_active_orders_fn()
            cancelled: list[str] = []
            failed: list[str] = []

            for order in active_orders:
                order_id = order.get("order_id", order.get("local_id", ""))
                if order_id:
                    success = self._cancel_order_fn(order_id)
                    if success:
                        cancelled.append(order_id)
                    else:
                        failed.append(order_id)

            result = ActionResult(
                action_type=ActionType.CANCEL_ALL,
                status=ActionStatus.COMPLETED,
                success=len(failed) == 0,
                message=f"Cancelled {len(cancelled)}, failed {len(failed)}",
                details={
                    "cancelled": cancelled,
                    "failed": failed,
                    "total": len(active_orders),
                },
            )

        except Exception as e:
            result = ActionResult(
                action_type=ActionType.CANCEL_ALL,
                status=ActionStatus.FAILED,
                success=False,
                message=str(e),
            )

        if self._on_action:
            self._on_action(result)

        return result

    def flatten_all(self, positions: dict[str, int] | None = None) -> ActionResult:
        """平掉所有持仓.

        V2 Scenario: GUARD.ACTION.FLATTEN_ALL

        Args:
            positions: 持仓字典 {symbol: qty}，None 表示无持仓

        Returns:
            动作结果
        """
        if not self._flatten_fn:
            return ActionResult(
                action_type=ActionType.FLATTEN_ALL,
                status=ActionStatus.FAILED,
                success=False,
                message="Flatten function not configured",
            )

        positions = positions or {}

        try:
            flattened: list[str] = []
            failed: list[str] = []

            for symbol, qty in positions.items():
                if qty != 0:
                    success = self._flatten_fn(symbol, qty)
                    if success:
                        flattened.append(symbol)
                    else:
                        failed.append(symbol)

            result = ActionResult(
                action_type=ActionType.FLATTEN_ALL,
                status=ActionStatus.COMPLETED,
                success=len(failed) == 0,
                message=f"Flattened {len(flattened)}, failed {len(failed)}",
                details={
                    "flattened": flattened,
                    "failed": failed,
                    "total": len(positions),
                },
            )

        except Exception as e:
            result = ActionResult(
                action_type=ActionType.FLATTEN_ALL,
                status=ActionStatus.FAILED,
                success=False,
                message=str(e),
            )

        if self._on_action:
            self._on_action(result)

        return result

    def send_alert(self, message: str, level: str = "WARN") -> ActionResult:
        """发送告警.

        Args:
            message: 告警消息
            level: 告警级别 (INFO/WARN/ERROR/FATAL)

        Returns:
            动作结果
        """
        if not self._send_alert_fn:
            return ActionResult(
                action_type=ActionType.SEND_ALERT,
                status=ActionStatus.COMPLETED,
                success=True,
                message="Alert skipped (no handler)",
                details={"message": message, "level": level},
            )

        try:
            self._send_alert_fn(message, level)
            result = ActionResult(
                action_type=ActionType.SEND_ALERT,
                status=ActionStatus.COMPLETED,
                success=True,
                message=f"Alert sent: {level}",
                details={"message": message, "level": level},
            )
        except Exception as e:
            result = ActionResult(
                action_type=ActionType.SEND_ALERT,
                status=ActionStatus.FAILED,
                success=False,
                message=str(e),
                details={"message": message, "level": level},
            )

        if self._on_action:
            self._on_action(result)

        return result
