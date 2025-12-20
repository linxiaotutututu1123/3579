"""
GuardianLog 测试.

V2 Scenarios:
- STRAT.DEGRADE.MODE_TRANSITION_AUDIT: 模式切换审计
"""

from src.audit.guardian_log import GuardianEvent, GuardianEventType


class TestGuardianEvent:
    """GuardianEvent 测试类."""

    def test_strat_degrade_mode_transition_audit(self) -> None:
        """STRAT.DEGRADE.MODE_TRANSITION_AUDIT: 模式切换审计."""
        event = GuardianEvent.mode_change(
            ts=1234567890.123,
            run_id="run-001",
            exec_id="exec-001",
            mode_from="RUNNING",
            mode_to="REDUCE_ONLY",
            trigger="quote_stale",
            details={"stale_symbols": ["AO2501"]},
        )

        data = event.to_dict()

        assert data["event_type"] == "GUARDIAN"
        assert data["guardian_event_type"] == "MODE_CHANGE"
        assert data["mode_from"] == "RUNNING"
        assert data["mode_to"] == "REDUCE_ONLY"
        assert data["trigger"] == "quote_stale"
        assert data["run_id"] == "run-001"
        assert data["exec_id"] == "exec-001"

    def test_guardian_event_type_enum(self) -> None:
        """测试事件类型枚举."""
        assert GuardianEventType.MODE_CHANGE.value == "MODE_CHANGE"
        assert GuardianEventType.TRIGGER_DETECTED.value == "TRIGGER_DETECTED"
        assert GuardianEventType.ACTION_EXECUTED.value == "ACTION_EXECUTED"
        assert GuardianEventType.RECOVERY_STARTED.value == "RECOVERY_STARTED"
        assert GuardianEventType.RECOVERY_COMPLETED.value == "RECOVERY_COMPLETED"
        assert GuardianEventType.HEALTH_CHECK.value == "HEALTH_CHECK"

    def test_mode_change_event(self) -> None:
        """测试模式变更事件."""
        event = GuardianEvent.mode_change(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            mode_from="INIT",
            mode_to="RUNNING",
            trigger="init_success",
        )

        assert event.guardian_event_type == "MODE_CHANGE"
        assert event.mode_from == "INIT"
        assert event.mode_to == "RUNNING"
        assert event.trigger == "init_success"
        assert event.details == {}

    def test_trigger_detected_event(self) -> None:
        """测试触发器检测事件."""
        event = GuardianEvent.trigger_detected(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            trigger="quote_stale",
            details={"stale_symbols": ["AO2501", "SA2501"]},
        )

        assert event.guardian_event_type == "TRIGGER_DETECTED"
        assert event.trigger == "quote_stale"
        assert event.details["stale_symbols"] == ["AO2501", "SA2501"]

    def test_action_executed_event(self) -> None:
        """测试动作执行事件."""
        event = GuardianEvent.action_executed(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            action="cancel_all",
            details={"cancelled_count": 5},
        )

        assert event.guardian_event_type == "ACTION_EXECUTED"
        assert event.action == "cancel_all"
        assert event.details["cancelled_count"] == 5

    def test_guardian_event_direct_construction(self) -> None:
        """测试直接构造事件."""
        event = GuardianEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            guardian_event_type="HEALTH_CHECK",
            details={"status": "healthy"},
        )

        assert event.guardian_event_type == "HEALTH_CHECK"
        assert event.mode_from is None
        assert event.mode_to is None
        assert event.trigger is None
        assert event.action is None

    def test_guardian_event_to_dict(self) -> None:
        """测试转换为字典."""
        event = GuardianEvent(
            ts=1234567890.0,
            run_id="run-001",
            exec_id="exec-001",
            guardian_event_type="MODE_CHANGE",
            mode_from="RUNNING",
            mode_to="HALTED",
            trigger="position_drift",
        )

        data = event.to_dict()

        assert data["event_type"] == "GUARDIAN"
        assert data["ts"] == 1234567890.0
        assert data["run_id"] == "run-001"
        assert data["exec_id"] == "exec-001"
        assert data["guardian_event_type"] == "MODE_CHANGE"
        assert data["mode_from"] == "RUNNING"
        assert data["mode_to"] == "HALTED"
        assert data["trigger"] == "position_drift"

    def test_mode_change_with_details(self) -> None:
        """测试带详情的模式变更."""
        event = GuardianEvent.mode_change(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            mode_from="REDUCE_ONLY",
            mode_to="HALTED",
            trigger="degraded",
            details={
                "reason": "Multiple triggers active",
                "active_triggers": ["quote_stale", "order_stuck"],
            },
        )

        assert event.details["reason"] == "Multiple triggers active"
        assert len(event.details["active_triggers"]) == 2

    def test_event_type_property(self) -> None:
        """测试事件类型属性."""
        event = GuardianEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            guardian_event_type="TEST",
        )

        assert event.event_type == "GUARDIAN"
