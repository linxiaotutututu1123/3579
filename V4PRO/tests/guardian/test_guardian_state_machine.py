"""
Guardian State Machine 测试.

V2 Scenarios:
- GUARD.FSM.TRANSITIONS: 状态机转移覆盖
"""

import pytest

from src.guardian.state_machine import (
    VALID_TRANSITIONS,
    GuardianFSM,
    GuardianMode,
    TransitionError,
)


class TestGuardianFSM:
    """GuardianFSM 测试类."""

    def test_initial_mode(self) -> None:
        """测试初始模式."""
        fsm = GuardianFSM()
        assert fsm.mode == GuardianMode.INIT

    def test_custom_initial_mode(self) -> None:
        """测试自定义初始模式."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        assert fsm.mode == GuardianMode.RUNNING

    def test_guard_fsm_transitions_init_to_running(self) -> None:
        """GUARD.FSM.TRANSITIONS: INIT -> RUNNING."""
        fsm = GuardianFSM()
        new_mode = fsm.transition("init_success")
        assert new_mode == GuardianMode.RUNNING
        assert fsm.mode == GuardianMode.RUNNING

    def test_guard_fsm_transitions_init_to_halted(self) -> None:
        """GUARD.FSM.TRANSITIONS: INIT -> HALTED."""
        fsm = GuardianFSM()
        new_mode = fsm.transition("init_failed")
        assert new_mode == GuardianMode.HALTED

    def test_guard_fsm_transitions_running_to_reduce_only_quote_stale(self) -> None:
        """GUARD.FSM.TRANSITIONS: RUNNING -> REDUCE_ONLY (quote_stale)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        new_mode = fsm.transition("quote_stale")
        assert new_mode == GuardianMode.REDUCE_ONLY

    def test_guard_fsm_transitions_running_to_reduce_only_order_stuck(self) -> None:
        """GUARD.FSM.TRANSITIONS: RUNNING -> REDUCE_ONLY (order_stuck)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        new_mode = fsm.transition("order_stuck")
        assert new_mode == GuardianMode.REDUCE_ONLY

    def test_guard_fsm_transitions_running_to_reduce_only_leg_imbalance(self) -> None:
        """GUARD.FSM.TRANSITIONS: RUNNING -> REDUCE_ONLY (leg_imbalance)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        new_mode = fsm.transition("leg_imbalance")
        assert new_mode == GuardianMode.REDUCE_ONLY

    def test_guard_fsm_transitions_running_to_halted_position_drift(self) -> None:
        """GUARD.FSM.TRANSITIONS: RUNNING -> HALTED (position_drift)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        new_mode = fsm.transition("position_drift")
        assert new_mode == GuardianMode.HALTED

    def test_guard_fsm_transitions_reduce_only_to_running(self) -> None:
        """GUARD.FSM.TRANSITIONS: REDUCE_ONLY -> RUNNING (recovered)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        new_mode = fsm.transition("recovered")
        assert new_mode == GuardianMode.RUNNING

    def test_guard_fsm_transitions_reduce_only_to_halted(self) -> None:
        """GUARD.FSM.TRANSITIONS: REDUCE_ONLY -> HALTED (degraded)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        new_mode = fsm.transition("degraded")
        assert new_mode == GuardianMode.HALTED

    def test_guard_fsm_transitions_halted_to_manual(self) -> None:
        """GUARD.FSM.TRANSITIONS: HALTED -> MANUAL."""
        fsm = GuardianFSM(initial_mode=GuardianMode.HALTED)
        new_mode = fsm.transition("manual_takeover")
        assert new_mode == GuardianMode.MANUAL

    def test_guard_fsm_transitions_manual_to_running(self) -> None:
        """GUARD.FSM.TRANSITIONS: MANUAL -> RUNNING."""
        fsm = GuardianFSM(initial_mode=GuardianMode.MANUAL)
        new_mode = fsm.transition("manual_release")
        assert new_mode == GuardianMode.RUNNING

    def test_invalid_transition_raises_error(self) -> None:
        """测试非法转移抛出异常."""
        fsm = GuardianFSM()  # INIT mode
        with pytest.raises(TransitionError):
            fsm.transition("recovered")  # Invalid from INIT

    def test_can_transition_true(self) -> None:
        """测试 can_transition 返回 True."""
        fsm = GuardianFSM()
        assert fsm.can_transition("init_success") is True

    def test_can_transition_false(self) -> None:
        """测试 can_transition 返回 False."""
        fsm = GuardianFSM()
        assert fsm.can_transition("recovered") is False

    def test_get_next_mode(self) -> None:
        """测试 get_next_mode."""
        fsm = GuardianFSM()
        next_mode = fsm.get_next_mode("init_success")
        assert next_mode == GuardianMode.RUNNING

    def test_get_next_mode_invalid(self) -> None:
        """测试 get_next_mode 非法事件."""
        fsm = GuardianFSM()
        next_mode = fsm.get_next_mode("invalid_event")
        assert next_mode is None

    def test_transition_count(self) -> None:
        """测试转移计数."""
        fsm = GuardianFSM()
        assert fsm.transition_count == 0
        fsm.transition("init_success")
        assert fsm.transition_count == 1

    def test_on_transition_callback(self) -> None:
        """测试转移回调."""
        transitions: list[tuple[GuardianMode, GuardianMode, str]] = []

        def callback(
            from_mode: GuardianMode, to_mode: GuardianMode, event: str
        ) -> None:
            transitions.append((from_mode, to_mode, event))

        fsm = GuardianFSM(on_transition=callback)
        fsm.transition("init_success")

        assert len(transitions) == 1
        assert transitions[0] == (
            GuardianMode.INIT,
            GuardianMode.RUNNING,
            "init_success",
        )

    def test_force_mode(self) -> None:
        """测试强制模式设置."""
        fsm = GuardianFSM()
        fsm.force_mode(GuardianMode.RUNNING, "test")
        assert fsm.mode == GuardianMode.RUNNING

    def test_is_trading_allowed(self) -> None:
        """测试 is_trading_allowed."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        assert fsm.is_trading_allowed() is True

        fsm.force_mode(GuardianMode.REDUCE_ONLY)
        assert fsm.is_trading_allowed() is True

        fsm.force_mode(GuardianMode.HALTED)
        assert fsm.is_trading_allowed() is False

    def test_is_open_allowed(self) -> None:
        """测试 is_open_allowed (GUARD.MODE.REDUCE_ONLY_EFFECT)."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        assert fsm.is_open_allowed() is True

        fsm.force_mode(GuardianMode.REDUCE_ONLY)
        assert fsm.is_open_allowed() is False

    def test_to_dict(self) -> None:
        """测试 to_dict."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        data = fsm.to_dict()
        assert data["mode"] == "RUNNING"
        assert data["mode_value"] == 1
        assert data["trading_allowed"] is True
        assert data["open_allowed"] is True

    def test_all_valid_transitions_covered(self) -> None:
        """GUARD.FSM.TRANSITIONS: 验证所有有效转移."""
        # 确保所有定义的转移都可以执行
        for (from_mode, event), to_mode in VALID_TRANSITIONS.items():
            fsm = GuardianFSM(initial_mode=from_mode)
            result = fsm.transition(event)
            assert result == to_mode, f"Failed: {from_mode} + {event} -> {to_mode}"
