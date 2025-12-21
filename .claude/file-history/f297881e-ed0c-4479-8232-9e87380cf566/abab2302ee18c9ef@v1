"""Tests for Sim Gate (Military-Grade v3.0)."""

from __future__ import annotations

from pathlib import Path

from src.trading.sim_gate import (
    ScenarioFailure,
    SimExitCode,
    SimGate,
    SimMetrics,
    SimReport,
    SimStatus,
    _compute_context_sha,
    _generate_exec_id,
    _generate_run_id,
)


class TestMilitaryGradeHelpers:
    """Tests for military-grade helper functions."""

    def test_generate_run_id_is_uuid(self) -> None:
        """run_id should be valid UUID format."""
        run_id = _generate_run_id()
        assert len(run_id) == 36
        assert run_id.count("-") == 4

    def test_generate_exec_id_format(self) -> None:
        """exec_id should be commit_timestamp format."""
        exec_id = _generate_exec_id()
        assert "_" in exec_id

    def test_compute_context_sha_missing_file(self) -> None:
        """SHA of missing file is empty string."""
        sha = _compute_context_sha(Path("nonexistent/file.md"))
        assert sha == ""


class TestScenarioFailure:
    """Tests for ScenarioFailure dataclass."""

    def test_basic_fields(self) -> None:
        """Basic fields are set correctly."""
        failure = ScenarioFailure(
            scenario="test_scenario",
            rule_id="TEST.RULE.001",
            component="test_component",
            tick=42,
            expected={"value": 1},
            actual={"value": 2},
            error="Values don't match",
        )
        assert failure.scenario == "test_scenario"
        assert failure.rule_id == "TEST.RULE.001"
        assert failure.component == "test_component"
        assert failure.tick == 42

    def test_default_evidence(self) -> None:
        """Evidence defaults to empty dict."""
        failure = ScenarioFailure(
            scenario="test",
            rule_id="TEST",
            component="test",
            tick=0,
            expected={},
            actual={},
            error="error",
        )
        assert failure.evidence == {}

    def test_default_event_id(self) -> None:
        """event_id defaults to empty string."""
        failure = ScenarioFailure(
            scenario="test",
            rule_id="TEST",
            component="test",
            tick=0,
            expected={},
            actual={},
            error="error",
        )
        assert failure.event_id == ""

    def test_to_dict_uses_tick_as_event_id(self) -> None:
        """to_dict uses tick as event_id when event_id is empty."""
        failure = ScenarioFailure(
            scenario="test",
            rule_id="TEST",
            component="test",
            tick=123,
            expected={},
            actual={},
            error="error",
        )
        d = failure.to_dict()
        assert d["event_id"] == "123"
        assert d["tick"] == 123

    def test_to_dict_uses_explicit_event_id(self) -> None:
        """to_dict uses explicit event_id when provided."""
        failure = ScenarioFailure(
            scenario="test",
            rule_id="TEST",
            component="test",
            tick=0,
            expected={},
            actual={},
            error="error",
            event_id="evt_abc123",
        )
        d = failure.to_dict()
        assert d["event_id"] == "evt_abc123"

    def test_to_dict_has_required_fields(self) -> None:
        """to_dict includes all military-grade required fields."""
        failure = ScenarioFailure(
            scenario="test_scenario",
            rule_id="TEST.RULE",
            component="comp",
            tick=1,
            expected={"a": 1},
            actual={"a": 2},
            error="mismatch",
            evidence={"state": "bad"},
        )
        d = failure.to_dict()
        assert "scenario" in d
        assert "rule_id" in d
        assert "component" in d
        assert "event_id" in d
        assert "tick" in d
        assert "expected" in d
        assert "actual" in d
        assert "error" in d
        assert "evidence" in d


class TestSimMetrics:
    """Tests for SimMetrics."""

    def test_defaults(self) -> None:
        """Default values are zeros."""
        metrics = SimMetrics()
        assert metrics.total_ticks == 0
        assert metrics.avg_tick_duration_ms == 0.0
        assert metrics.pnl_total == 0.0

    def test_to_dict(self) -> None:
        """to_dict includes all fields."""
        metrics = SimMetrics(total_ticks=100, pnl_total=1000.0)
        d = metrics.to_dict()
        assert d["total_ticks"] == 100
        assert d["pnl_total"] == 1000.0


class TestSimReport:
    """Tests for SimReport military-grade schema."""

    def test_default_schema_version(self) -> None:
        """Default schema_version is 3."""
        report = SimReport(type="replay")
        assert report.schema_version == 3

    def test_check_mode_true(self) -> None:
        """check_mode can be set to True."""
        report = SimReport(type="sim", check_mode=True)
        assert report.check_mode is True

    def test_auto_generates_run_id(self) -> None:
        """run_id is auto-generated if not provided."""
        report = SimReport(type="replay")
        assert report.run_id
        assert len(report.run_id) == 36

    def test_auto_generates_exec_id(self) -> None:
        """exec_id is auto-generated if not provided."""
        report = SimReport(type="sim")
        assert report.exec_id
        assert "_" in report.exec_id

    def test_auto_generates_timestamp(self) -> None:
        """timestamp is auto-generated if not provided."""
        report = SimReport(type="replay")
        assert report.timestamp
        assert "T" in report.timestamp

    def test_overall_pass_when_no_failures(self) -> None:
        """overall is PASS when scenarios_failed is 0."""
        report = SimReport(type="replay", scenarios_passed=5, scenarios_failed=0)
        assert report.overall == SimStatus.PASS

    def test_overall_fail_when_has_failures(self) -> None:
        """overall is FAIL when scenarios_failed > 0."""
        report = SimReport(type="replay", scenarios_failed=1)
        assert report.overall == SimStatus.FAIL

    def test_passed_property(self) -> None:
        """passed is True when no failures."""
        report = SimReport(type="replay")
        assert report.passed is True

    def test_exit_code_success_for_pass(self) -> None:
        """exit_code is SUCCESS when passed."""
        report = SimReport(type="replay")
        assert report.exit_code == SimExitCode.SUCCESS

    def test_exit_code_replay_fail(self) -> None:
        """exit_code is REPLAY_FAIL for failed replay."""
        report = SimReport(type="replay", scenarios_failed=1)
        assert report.exit_code == SimExitCode.REPLAY_FAIL

    def test_exit_code_sim_fail(self) -> None:
        """exit_code is SIM_FAIL for failed sim."""
        report = SimReport(type="sim", scenarios_failed=1)
        assert report.exit_code == SimExitCode.SIM_FAIL

    def test_add_pass_increments_counters(self) -> None:
        """add_pass increments total and passed counts."""
        report = SimReport(type="replay")
        report.add_pass("scenario1")
        assert report.scenarios_total == 1
        assert report.scenarios_passed == 1

    def test_add_failure_increments_counters(self) -> None:
        """add_failure increments total and failed counts."""
        report = SimReport(type="replay")
        report.add_failure(
            scenario="test",
            tick=0,
            expected={},
            actual={},
            error="error",
        )
        assert report.scenarios_total == 1
        assert report.scenarios_failed == 1
        assert len(report.failures) == 1

    def test_add_failure_auto_rule_id(self) -> None:
        """add_failure auto-generates rule_id if not provided."""
        report = SimReport(type="replay")
        report.add_failure(
            scenario="my test",
            tick=0,
            expected={},
            actual={},
            error="error",
        )
        assert report.failures[0].rule_id.startswith("UNKNOWN.")

    def test_to_dict_has_required_fields(self) -> None:
        """to_dict includes all military-grade required fields."""
        report = SimReport(type="replay", check_mode=True)
        d = report.to_dict()

        # Military-grade required fields
        assert d["schema_version"] == 3
        assert d["type"] == "replay"
        assert "overall" in d
        assert "exit_code" in d
        assert d["check_mode"] is True
        assert "timestamp" in d
        assert "run_id" in d
        assert "exec_id" in d
        assert "artifacts" in d
        assert "scenarios" in d
        assert "failures" in d

    def test_to_dict_scenarios_has_counts(self) -> None:
        """scenarios includes total/passed/failed/skipped."""
        report = SimReport(type="replay")
        d = report.to_dict()
        scenarios = d["scenarios"]
        assert "total" in scenarios
        assert "passed" in scenarios
        assert "failed" in scenarios
        assert "skipped" in scenarios

    def test_to_dict_artifacts_has_paths(self) -> None:
        """artifacts includes required paths."""
        report = SimReport(type="replay")
        d = report.to_dict()
        assert "report_path" in d["artifacts"]
        assert "events_jsonl_path" in d["artifacts"]


class TestSimGate:
    """Tests for SimGate controller."""

    def test_init_with_check_mode(self) -> None:
        """SimGate initializes with check_mode."""
        gate = SimGate(sim_type="replay", check_mode=True)
        assert gate.report.check_mode is True

    def test_record_pass(self) -> None:
        """record_pass increments pass counter."""
        gate = SimGate(sim_type="replay", check_mode=True)
        gate.record_pass("scenario1", rule_id="TEST.001", component="test")
        assert gate.report.scenarios_passed == 1

    def test_record_failure(self) -> None:
        """record_failure adds failure to report."""
        gate = SimGate(sim_type="replay", check_mode=True)
        gate.record_failure(
            scenario="test_scenario",
            tick=10,
            expected={"value": 1},
            actual={"value": 2},
            error="Mismatch",
            rule_id="TEST.002",
            component="test",
            evidence={"state": "bad"},
        )
        assert gate.report.scenarios_failed == 1
        assert len(gate.report.failures) == 1
        f = gate.report.failures[0]
        assert f.rule_id == "TEST.002"
        assert f.tick == 10

    def test_set_check_mode(self) -> None:
        """set_check_mode updates report."""
        gate = SimGate(sim_type="sim")
        assert gate.report.check_mode is False
        gate.set_check_mode(True)
        assert gate.report.check_mode is True

    def test_save_report(self, tmp_path: Path) -> None:
        """save_report writes JSON file."""
        gate = SimGate(sim_type="replay", check_mode=True)
        gate.record_pass("test")
        output = tmp_path / "report.json"
        gate.save_report(str(output))
        assert output.exists()
        import json

        content = json.loads(output.read_text())
        assert content["schema_version"] == 3
        assert content["type"] == "replay"

    def test_set_metrics(self) -> None:
        """set_metrics updates report metrics."""
        gate = SimGate(sim_type="sim")
        gate.set_metrics(
            total_ticks=1000,
            avg_tick_duration_ms=1.5,
            max_drawdown_pct=5.0,
            orders_placed=100,
            orders_rejected=10,
            orders_filled=90,
            pnl_total=5000.0,
        )
        metrics = gate.report.metrics
        assert metrics.total_ticks == 1000
        assert metrics.avg_tick_duration_ms == 1.5
        assert metrics.max_drawdown_pct == 5.0
        assert metrics.orders_placed == 100
        assert metrics.orders_rejected == 10
        assert metrics.orders_filled == 90
        assert metrics.pnl_total == 5000.0

    def test_generate_report(self) -> None:
        """generate_report returns the report."""
        gate = SimGate(sim_type="replay")
        gate.record_pass("test")
        report = gate.generate_report()
        assert report.scenarios_passed == 1


class TestGetSimExitCode:
    """Tests for get_sim_exit_code function."""

    def test_passed_returns_success(self) -> None:
        """Passed report returns SUCCESS."""
        from src.trading.sim_gate import get_sim_exit_code

        report = SimReport(type="replay", scenarios_passed=5)
        assert get_sim_exit_code(report) == SimExitCode.SUCCESS

    def test_replay_fail_returns_replay_fail(self) -> None:
        """Failed replay returns REPLAY_FAIL."""
        from src.trading.sim_gate import get_sim_exit_code

        report = SimReport(type="replay", scenarios_failed=1)
        assert get_sim_exit_code(report) == SimExitCode.REPLAY_FAIL

    def test_sim_fail_returns_sim_fail(self) -> None:
        """Failed sim returns SIM_FAIL."""
        from src.trading.sim_gate import get_sim_exit_code

        report = SimReport(type="sim", scenarios_failed=1)
        assert get_sim_exit_code(report) == SimExitCode.SIM_FAIL


class TestGetPathsForType:
    """Tests for get_paths_for_type function."""

    def test_replay_paths(self) -> None:
        """Replay paths are correct."""
        from src.trading.sim_gate import get_paths_for_type

        paths = get_paths_for_type("replay")
        assert "report" in paths
        assert "events_jsonl" in paths
        assert "replay" in str(paths["report"])

    def test_sim_paths(self) -> None:
        """Sim paths are correct."""
        from src.trading.sim_gate import get_paths_for_type

        paths = get_paths_for_type("sim")
        assert "report" in paths
        assert "sim" in str(paths["report"])


class TestSimReportSummary:
    """Tests for SimReport summary method."""

    def test_summary_pass(self) -> None:
        """Summary for passed report."""
        report = SimReport(type="replay", scenarios_total=5, scenarios_passed=5)
        summary = report.summary()
        assert "PASS" in summary
        assert "5/5" in summary

    def test_summary_fail(self) -> None:
        """Summary for failed report."""
        report = SimReport(type="sim", scenarios_total=5, scenarios_passed=3, scenarios_failed=2)
        summary = report.summary()
        assert "FAIL" in summary
        assert "3/5" in summary


class TestSimReportJson:
    """Tests for SimReport JSON methods."""

    def test_to_json(self) -> None:
        """to_json returns valid JSON."""
        import json

        report = SimReport(type="replay")
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["schema_version"] == 3
        assert data["type"] == "replay"

    def test_to_dict_artifacts_match_type(self) -> None:
        """Artifacts paths match report type."""
        report = SimReport(type="replay")
        d = report.to_dict()
        assert "replay" in d["artifacts"]["report_path"]

        report_sim = SimReport(type="sim")
        d_sim = report_sim.to_dict()
        assert "sim" in d_sim["artifacts"]["report_path"]
