"""
Guardian Monitor 测试.

V2 Scenarios:
- GUARD.MODE.REDUCE_ONLY_EFFECT: reduce_only 禁开仓
- STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 禁开仓
- STRAT.DEGRADE.HALTED_OUTPUT_ZERO: HALTED 输出零
"""

import time

from src.guardian.monitor import GuardianMonitor
from src.guardian.state_machine import GuardianFSM, GuardianMode
from src.guardian.triggers import QuoteStaleTrigger, TriggerManager


class TestGuardianMonitor:
    """GuardianMonitor 测试类."""

    def test_initial_mode(self) -> None:
        """测试初始模式."""
        monitor = GuardianMonitor()
        assert monitor.mode == GuardianMode.INIT

    def test_guard_mode_reduce_only_effect(self) -> None:
        """GUARD.MODE.REDUCE_ONLY_EFFECT: REDUCE_ONLY 禁止开仓."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        monitor = GuardianMonitor(fsm=fsm)

        assert monitor.can_open_position() is False

    def test_strat_degrade_reduce_only_no_open(self) -> None:
        """STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 禁开仓."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        monitor = GuardianMonitor(fsm=fsm)

        target = {"AO2501": 10}  # 想开多10手
        current = {"AO2501": 0}  # 当前无仓位

        filtered = monitor.filter_target_portfolio(target, current)
        assert filtered["AO2501"] == 0  # 不允许开仓

    def test_strat_degrade_reduce_only_allow_close(self) -> None:
        """STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 允许平仓."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        monitor = GuardianMonitor(fsm=fsm)

        target = {"AO2501": 5}  # 目标持仓5手
        current = {"AO2501": 10}  # 当前持仓10手

        filtered = monitor.filter_target_portfolio(target, current)
        assert filtered["AO2501"] == 5  # 允许减仓

    def test_strat_degrade_reduce_only_no_reverse(self) -> None:
        """STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 不允许翻仓."""
        fsm = GuardianFSM(initial_mode=GuardianMode.REDUCE_ONLY)
        monitor = GuardianMonitor(fsm=fsm)

        target = {"AO2501": -10}  # 想翻空
        current = {"AO2501": 10}  # 当前持多

        filtered = monitor.filter_target_portfolio(target, current)
        assert filtered["AO2501"] == 0  # 只能平到0，不能翻空

    def test_strat_degrade_halted_output_zero(self) -> None:
        """STRAT.DEGRADE.HALTED_OUTPUT_ZERO: HALTED 输出零."""
        fsm = GuardianFSM(initial_mode=GuardianMode.HALTED)
        monitor = GuardianMonitor(fsm=fsm)

        target = {"AO2501": 10, "SA2501": -5}
        current = {"AO2501": 5, "SA2501": -3}

        filtered = monitor.filter_target_portfolio(target, current)
        # HALTED 模式应保持当前仓位不变
        assert filtered == current

    def test_running_mode_allow_all(self) -> None:
        """RUNNING 模式允许所有交易."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        monitor = GuardianMonitor(fsm=fsm)

        target = {"AO2501": 10, "SA2501": -5}
        current = {"AO2501": 0}

        filtered = monitor.filter_target_portfolio(target, current)
        assert filtered == target

    def test_can_open_position_running(self) -> None:
        """RUNNING 模式允许开仓."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        monitor = GuardianMonitor(fsm=fsm)
        assert monitor.can_open_position() is True

    def test_can_open_position_init(self) -> None:
        """INIT 模式不允许开仓."""
        monitor = GuardianMonitor()
        assert monitor.can_open_position() is False

    def test_check_triggers_mode_change(self) -> None:
        """测试检查触发模式变更."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        trigger_manager = TriggerManager(triggers=[QuoteStaleTrigger(hard_stale_ms=5000.0)])
        monitor = GuardianMonitor(fsm=fsm, trigger_manager=trigger_manager)

        now = time.time()
        state = {
            "quote_timestamps": {"AO2501": now - 10.0},  # 10秒前，stale
            "now_ts": now,
        }

        result = monitor.check(state)

        assert result.triggered is True
        assert len(result.triggers) == 1
        assert monitor.mode == GuardianMode.REDUCE_ONLY

    def test_check_no_triggers(self) -> None:
        """测试无触发."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        trigger_manager = TriggerManager(triggers=[QuoteStaleTrigger(hard_stale_ms=5000.0)])
        monitor = GuardianMonitor(fsm=fsm, trigger_manager=trigger_manager)

        now = time.time()
        state = {
            "quote_timestamps": {"AO2501": now - 1.0},  # 1秒前，正常
            "now_ts": now,
        }

        result = monitor.check(state)

        assert result.triggered is False
        assert monitor.mode == GuardianMode.RUNNING

    def test_initialize_success(self) -> None:
        """测试初始化成功."""
        monitor = GuardianMonitor()
        success = monitor.initialize()

        assert success is True
        assert monitor.mode == GuardianMode.RUNNING

    def test_initialize_already_running(self) -> None:
        """测试已经 RUNNING 时初始化."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        monitor = GuardianMonitor(fsm=fsm)
        success = monitor.initialize()

        assert success is False  # 不在 INIT 模式

    def test_manual_set_mode(self) -> None:
        """测试手动设置模式."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        monitor = GuardianMonitor(fsm=fsm)

        success = monitor.manual_set_mode(GuardianMode.HALTED, "test")
        assert success is True
        assert monitor.mode == GuardianMode.HALTED

    def test_on_mode_change_callback(self) -> None:
        """测试模式变更回调."""
        changes: list[tuple[GuardianMode, GuardianMode, str]] = []

        def on_change(from_mode: GuardianMode, to_mode: GuardianMode, trigger: str) -> None:
            changes.append((from_mode, to_mode, trigger))

        monitor = GuardianMonitor(on_mode_change=on_change)
        monitor.initialize()

        assert len(changes) == 1
        assert changes[0] == (GuardianMode.INIT, GuardianMode.RUNNING, "init_success")

    def test_add_trigger(self) -> None:
        """测试添加触发器."""
        monitor = GuardianMonitor()
        trigger = QuoteStaleTrigger()
        monitor.add_trigger(trigger)
        # 验证触发器已添加
        assert trigger in monitor.trigger_manager._triggers

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        fsm = GuardianFSM(initial_mode=GuardianMode.RUNNING)
        monitor = GuardianMonitor(fsm=fsm)

        data = monitor.to_dict()

        assert data["mode"] == "RUNNING"
        assert data["can_open_position"] is True
        assert "transition_count" in data
