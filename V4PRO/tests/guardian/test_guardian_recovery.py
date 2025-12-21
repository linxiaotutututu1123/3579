"""
Guardian Recovery 测试.

V2 Scenarios:
- GUARD.RECOVERY.COLD_START: 冷启动恢复
"""

from src.guardian.recovery import ColdStartRecovery, RecoveryStatus, RecoveryStep


class TestColdStartRecovery:
    """ColdStartRecovery 测试类."""

    def test_guard_recovery_cold_start_success(self) -> None:
        """GUARD.RECOVERY.COLD_START: 完整冷启动流程."""
        steps_executed: list[str] = []

        def cancel_all() -> bool:
            steps_executed.append("cancel_all")
            return True

        def query_positions() -> dict[str, int]:
            steps_executed.append("query_positions")
            return {"AO2501": 10}

        def reconcile(local: dict[str, int], broker: dict[str, int]) -> bool:
            steps_executed.append("reconcile")
            return True

        def set_mode(mode: object) -> None:
            steps_executed.append("set_mode")

        def health_check() -> bool:
            steps_executed.append("health_check")
            return True

        recovery = ColdStartRecovery(
            cooldown_s=0.0,
            cancel_all_fn=cancel_all,
            query_positions_fn=query_positions,
            reconcile_fn=reconcile,
            set_mode_fn=set_mode,
            health_check_fn=health_check,
        )

        state = recovery.start()

        assert state.status == RecoveryStatus.COMPLETED
        assert recovery.is_complete is True
        assert RecoveryStep.COMPLETE in state.completed_steps
        assert "cancel_all" in steps_executed
        assert "query_positions" in steps_executed
        assert "reconcile" in steps_executed
        assert "health_check" in steps_executed

    def test_guard_recovery_cold_start_cancel_fail(self) -> None:
        """GUARD.RECOVERY.COLD_START: 撤单失败."""

        def cancel_all() -> bool:
            return False

        recovery = ColdStartRecovery(cancel_all_fn=cancel_all)
        state = recovery.start()

        assert state.status == RecoveryStatus.FAILED
        assert recovery.is_failed is True
        assert len(state.errors) > 0

    def test_guard_recovery_cold_start_reconcile_fail(self) -> None:
        """GUARD.RECOVERY.COLD_START: 对账失败."""

        def cancel_all() -> bool:
            return True

        def query_positions() -> dict[str, int]:
            return {"AO2501": 10}

        def reconcile(local: dict[str, int], broker: dict[str, int]) -> bool:
            return False  # 对账失败

        recovery = ColdStartRecovery(
            cancel_all_fn=cancel_all,
            query_positions_fn=query_positions,
            reconcile_fn=reconcile,
        )
        state = recovery.start()

        assert state.status == RecoveryStatus.FAILED

    def test_guard_recovery_cold_start_health_check_fail(self) -> None:
        """GUARD.RECOVERY.COLD_START: 健康检查失败."""

        def health_check() -> bool:
            return False

        recovery = ColdStartRecovery(health_check_fn=health_check)
        state = recovery.start()

        assert state.status == RecoveryStatus.FAILED

    def test_recovery_without_functions(self) -> None:
        """测试无函数配置的恢复（全部跳过）."""
        recovery = ColdStartRecovery()
        state = recovery.start()

        # 所有步骤都被跳过，应该成功
        assert state.status == RecoveryStatus.COMPLETED

    def test_recovery_on_step_callback(self) -> None:
        """测试步骤回调."""
        from typing import Any

        callbacks: list[tuple[RecoveryStep, bool, dict[str, Any]]] = []

        def on_step(step: RecoveryStep, success: bool, details: dict[str, Any]) -> None:
            callbacks.append((step, success, details))

        recovery = ColdStartRecovery(on_step=on_step)
        recovery.start()

        assert len(callbacks) >= 1
        # 至少有 CANCEL_ALL 步骤
        assert callbacks[0][0] == RecoveryStep.CANCEL_ALL

    def test_recovery_state_to_dict(self) -> None:
        """测试状态转换为字典."""
        recovery = ColdStartRecovery()
        state = recovery.start()
        data = state.to_dict()

        assert "status" in data
        assert "completed_steps" in data
        assert data["status"] == "completed"

    def test_recovery_reset(self) -> None:
        """测试重置."""
        recovery = ColdStartRecovery()
        recovery.start()
        assert recovery.is_complete is True

        recovery.reset()
        assert recovery.is_complete is False
        assert recovery.state.status == RecoveryStatus.NOT_STARTED

    def test_recovery_state_properties(self) -> None:
        """测试恢复状态属性."""
        recovery = ColdStartRecovery()
        assert recovery.is_complete is False
        assert recovery.is_failed is False

        recovery.start()
        assert recovery.is_complete is True
        assert recovery.is_failed is False
