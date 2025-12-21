"""
Guardian Actions 测试.

V2 Scenarios:
- GUARD.ACTION.SET_MODE: set_mode 动作
- GUARD.ACTION.CANCEL_ALL: cancel_all 动作
- GUARD.ACTION.FLATTEN_ALL: flatten_all 动作
"""

from src.guardian.actions import ActionStatus, ActionType, GuardianActions
from src.guardian.state_machine import GuardianMode


class TestGuardianActions:
    """GuardianActions 测试类."""

    def test_guard_action_set_mode(self) -> None:
        """GUARD.ACTION.SET_MODE: 设置模式."""
        actions = GuardianActions()
        result = actions.set_mode(GuardianMode.REDUCE_ONLY, "test_trigger")

        assert result.action_type == ActionType.SET_MODE
        assert result.status == ActionStatus.COMPLETED
        assert result.success is True
        assert result.details["mode"] == "REDUCE_ONLY"
        assert result.details["trigger"] == "test_trigger"

    def test_guard_action_cancel_all_success(self) -> None:
        """GUARD.ACTION.CANCEL_ALL: 成功撤单."""
        cancelled_orders: list[str] = []

        def cancel_order(order_id: str) -> bool:
            cancelled_orders.append(order_id)
            return True

        def get_active_orders() -> list[dict[str, str]]:
            return [{"order_id": "ord1"}, {"order_id": "ord2"}]

        actions = GuardianActions(
            cancel_order_fn=cancel_order,
            get_active_orders_fn=get_active_orders,
        )
        result = actions.cancel_all()

        assert result.action_type == ActionType.CANCEL_ALL
        assert result.status == ActionStatus.COMPLETED
        assert result.success is True
        assert set(cancelled_orders) == {"ord1", "ord2"}

    def test_guard_action_cancel_all_partial_failure(self) -> None:
        """GUARD.ACTION.CANCEL_ALL: 部分失败."""

        def cancel_order(order_id: str) -> bool:
            return order_id != "ord2"  # ord2 失败

        def get_active_orders() -> list[dict[str, str]]:
            return [{"order_id": "ord1"}, {"order_id": "ord2"}]

        actions = GuardianActions(
            cancel_order_fn=cancel_order,
            get_active_orders_fn=get_active_orders,
        )
        result = actions.cancel_all()

        assert result.success is False
        assert "ord2" in result.details["failed"]

    def test_guard_action_cancel_all_no_functions(self) -> None:
        """GUARD.ACTION.CANCEL_ALL: 未配置函数."""
        actions = GuardianActions()
        result = actions.cancel_all()

        assert result.status == ActionStatus.FAILED
        assert result.success is False

    def test_guard_action_flatten_all_success(self) -> None:
        """GUARD.ACTION.FLATTEN_ALL: 成功平仓."""
        flattened: list[tuple[str, int]] = []

        def flatten(symbol: str, qty: int) -> bool:
            flattened.append((symbol, qty))
            return True

        actions = GuardianActions(flatten_fn=flatten)
        result = actions.flatten_all({"AO2501": 10, "SA2501": -5})

        assert result.action_type == ActionType.FLATTEN_ALL
        assert result.status == ActionStatus.COMPLETED
        assert result.success is True
        assert len(flattened) == 2

    def test_guard_action_flatten_all_skip_zero(self) -> None:
        """GUARD.ACTION.FLATTEN_ALL: 跳过零仓位."""
        flattened: list[tuple[str, int]] = []

        def flatten(symbol: str, qty: int) -> bool:
            flattened.append((symbol, qty))
            return True

        actions = GuardianActions(flatten_fn=flatten)
        result = actions.flatten_all({"AO2501": 10, "SA2501": 0})

        assert result.success is True
        assert len(flattened) == 1

    def test_guard_action_flatten_all_no_function(self) -> None:
        """GUARD.ACTION.FLATTEN_ALL: 未配置函数."""
        actions = GuardianActions()
        result = actions.flatten_all({"AO2501": 10})

        assert result.status == ActionStatus.FAILED
        assert result.success is False

    def test_send_alert_success(self) -> None:
        """测试发送告警成功."""
        alerts: list[tuple[str, str]] = []

        def send_alert(message: str, level: str) -> None:
            alerts.append((message, level))

        actions = GuardianActions(send_alert_fn=send_alert)
        result = actions.send_alert("Test alert", "WARN")

        assert result.success is True
        assert len(alerts) == 1
        assert alerts[0] == ("Test alert", "WARN")

    def test_send_alert_no_handler(self) -> None:
        """测试无告警处理器."""
        actions = GuardianActions()
        result = actions.send_alert("Test alert", "WARN")

        assert result.success is True  # 跳过但成功
        assert "skipped" in result.message.lower()

    def test_on_action_callback(self) -> None:
        """测试动作回调."""
        from src.guardian.actions import ActionResult

        callbacks: list[ActionResult] = []

        def on_action(result: ActionResult) -> None:
            callbacks.append(result)

        actions = GuardianActions(on_action=on_action)
        actions.set_mode(GuardianMode.RUNNING, "test")

        assert len(callbacks) == 1
        assert callbacks[0].action_type == ActionType.SET_MODE
