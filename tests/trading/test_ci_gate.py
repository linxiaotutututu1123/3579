"""Tests for CI gate checks (军规级 v4.0).

覆盖场景:
- INFRA.CI.GATE_PASS: CI门禁全部通过
- INFRA.CI.LINT_PASS: Ruff检查通过
- INFRA.CI.TYPE_PASS: Mypy检查通过
- INFRA.CI.TEST_PASS: Pytest通过
- INFRA.CI.COVERAGE_MIN: 覆盖率≥80%
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.trading.ci_gate import (
    CIGate,
    CIJsonReport,
    CIJsonReportV3,
    CIStep,
    CIStepFailure,
    CIStepStatus,
    ExitCode,
    GateCheck,
    GateCheckStatus,
    GateReport,
    PolicyReport,
    PolicyViolation,
    assert_not_check_mode,
    check_command_whitelist,
    disable_check_mode,
    enable_check_mode,
    get_exit_code,
    get_hints_for_step,
    is_check_mode,
    log_gate_report,
    parse_mypy_output,
    parse_pytest_output,
    parse_ruff_output,
    validate_report_schema,
)


class TestGateCheck:
    """Tests for GateCheck dataclass."""

    def test_pass_passed(self) -> None:
        """PASS status means passed."""
        check = GateCheck(name="test", status=GateCheckStatus.PASS)
        assert check.passed is True
        assert check.blocking is False

    def test_skip_passed(self) -> None:
        """SKIP status means passed."""
        check = GateCheck(name="test", status=GateCheckStatus.SKIP)
        assert check.passed is True
        assert check.blocking is False

    def test_fail_not_passed(self) -> None:
        """FAIL status means not passed."""
        check = GateCheck(name="test", status=GateCheckStatus.FAIL)
        assert check.passed is False

    def test_blocking_required_fail(self) -> None:
        """Required FAIL is blocking."""
        check = GateCheck(name="test", status=GateCheckStatus.FAIL, required=True)
        assert check.blocking is True

    def test_not_blocking_optional_fail(self) -> None:
        """Optional FAIL is not blocking."""
        check = GateCheck(name="test", status=GateCheckStatus.FAIL, required=False)
        assert check.blocking is False


class TestGateReport:
    """Tests for GateReport."""

    def test_all_passed(self) -> None:
        """all_passed returns True when no blocking failures."""
        report = GateReport(
            checks=(
                GateCheck("a", GateCheckStatus.PASS),
                GateCheck("b", GateCheckStatus.PASS),
            ),
            target_mode="LIVE",
        )
        assert report.all_passed is True
        assert len(report.blocking_failures) == 0

    def test_has_blocking_failure(self) -> None:
        """blocking_failures returns failed required checks."""
        report = GateReport(
            checks=(
                GateCheck("a", GateCheckStatus.PASS),
                GateCheck("b", GateCheckStatus.FAIL, required=True),
            ),
            target_mode="LIVE",
        )
        assert report.all_passed is False
        assert len(report.blocking_failures) == 1

    def test_pass_count(self) -> None:
        """pass_count returns correct count."""
        report = GateReport(
            checks=(
                GateCheck("a", GateCheckStatus.PASS),
                GateCheck("b", GateCheckStatus.FAIL),
                GateCheck("c", GateCheckStatus.SKIP),
            ),
            target_mode="LIVE",
        )
        assert report.pass_count == 2

    def test_summary(self) -> None:
        """summary returns readable string."""
        report = GateReport(
            checks=(GateCheck("a", GateCheckStatus.PASS),),
            target_mode="LIVE",
        )
        s = report.summary()
        assert "PASS" in s
        assert "LIVE" in s


class TestCIGate:
    """Tests for CIGate."""

    def test_init(self) -> None:
        """CIGate initializes correctly."""
        gate = CIGate("LIVE")
        assert gate._target_mode == "LIVE"

    def test_add_check(self) -> None:
        """add_check adds check to list."""
        gate = CIGate()
        gate.add_check("test", GateCheckStatus.PASS)
        report = gate.generate_report()
        assert len(report.checks) == 1

    def test_check_tests_pass(self) -> None:
        """check_tests_pass adds appropriate check."""
        gate = CIGate()
        gate.check_tests_pass(True)
        report = gate.generate_report()
        assert report.checks[0].name == "tests_pass"
        assert report.checks[0].status == GateCheckStatus.PASS

    def test_check_tests_fail(self) -> None:
        """check_tests_pass records failure."""
        gate = CIGate()
        gate.check_tests_pass(False)
        report = gate.generate_report()
        assert report.checks[0].status == GateCheckStatus.FAIL

    def test_run_all_checks_pass(self) -> None:
        """run_all_checks with all True returns passing report."""
        gate = CIGate()
        report = gate.run_all_checks(
            tests_passed=True,
            lint_passed=True,
            type_check_passed=True,
            risk_limits_configured=True,
            broker_credentials_valid=True,
            model_weights_exist=True,
        )
        assert report.all_passed is True
        assert len(report.checks) == 6

    def test_run_all_checks_fail(self) -> None:
        """run_all_checks with some False returns failing report."""
        gate = CIGate()
        report = gate.run_all_checks(
            tests_passed=True,
            lint_passed=False,
            type_check_passed=True,
            risk_limits_configured=True,
            broker_credentials_valid=True,
            model_weights_exist=True,
        )
        assert report.all_passed is False
        assert len(report.blocking_failures) == 1

    def test_run_all_checks_resets(self) -> None:
        """run_all_checks resets previous checks."""
        gate = CIGate()
        gate.add_check("extra", GateCheckStatus.FAIL)
        report = gate.run_all_checks(
            tests_passed=True,
            lint_passed=True,
            type_check_passed=True,
            risk_limits_configured=True,
            broker_credentials_valid=True,
            model_weights_exist=True,
        )
        # Should only have the 6 standard checks
        assert len(report.checks) == 6


class TestExitCode:
    """Tests for ExitCode constants (军规级 v4.0)."""

    def test_exit_code_values(self) -> None:
        """Exit codes have correct values (军规级 v4.0)."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.GENERAL_ERROR == 1
        assert ExitCode.FORMAT_LINT_FAIL == 2
        assert ExitCode.TYPE_CHECK_FAIL == 3
        assert ExitCode.TEST_FAIL == 4
        assert ExitCode.COVERAGE_FAIL == 5
        assert ExitCode.RISK_CONFIG_FAIL == 6
        assert ExitCode.BROKER_CREDS_FAIL == 7
        assert ExitCode.REPLAY_FAIL == 8
        assert ExitCode.SIM_FAIL == 9
        assert ExitCode.MODEL_WEIGHTS_FAIL == 10
        assert ExitCode.SCENARIO_MISSING == 11
        assert ExitCode.POLICY_VIOLATION == 12
        assert ExitCode.CAPABILITY_MISSING == 13

    def test_exit_code_new_v4_codes(self) -> None:
        """新增的军规级 v4.0 退出码."""
        # 验证新退出码存在
        assert hasattr(ExitCode, "MODEL_WEIGHTS_FAIL")
        assert hasattr(ExitCode, "SCENARIO_MISSING")
        assert hasattr(ExitCode, "CAPABILITY_MISSING")

        # 验证退出码值不冲突
        codes = [
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.FORMAT_LINT_FAIL,
            ExitCode.TYPE_CHECK_FAIL,
            ExitCode.TEST_FAIL,
            ExitCode.COVERAGE_FAIL,
            ExitCode.RISK_CONFIG_FAIL,
            ExitCode.BROKER_CREDS_FAIL,
            ExitCode.REPLAY_FAIL,
            ExitCode.SIM_FAIL,
            ExitCode.MODEL_WEIGHTS_FAIL,
            ExitCode.SCENARIO_MISSING,
            ExitCode.POLICY_VIOLATION,
            ExitCode.CAPABILITY_MISSING,
        ]
        assert len(codes) == len(set(codes)), "Exit codes must be unique"


class TestGetExitCode:
    """Tests for get_exit_code function."""

    def test_all_passed_returns_success(self) -> None:
        """All passed returns SUCCESS."""
        report = GateReport(
            checks=(GateCheck("a", GateCheckStatus.PASS),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.SUCCESS

    def test_lint_fail_returns_format_lint(self) -> None:
        """Lint failure returns FORMAT_LINT_FAIL."""
        report = GateReport(
            checks=(GateCheck("lint_pass", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.FORMAT_LINT_FAIL

    def test_format_fail_returns_format_lint(self) -> None:
        """Format failure returns FORMAT_LINT_FAIL."""
        report = GateReport(
            checks=(GateCheck("format_pass", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.FORMAT_LINT_FAIL

    def test_type_check_fail_returns_type_check(self) -> None:
        """Type check failure returns TYPE_CHECK_FAIL."""
        report = GateReport(
            checks=(GateCheck("type_check_pass", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.TYPE_CHECK_FAIL

    def test_tests_fail_returns_test_fail(self) -> None:
        """Tests failure returns TEST_FAIL."""
        report = GateReport(
            checks=(GateCheck("tests_pass", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.TEST_FAIL

    def test_coverage_fail_returns_coverage_fail(self) -> None:
        """Coverage failure returns COVERAGE_FAIL."""
        report = GateReport(
            checks=(GateCheck("coverage_pass", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.COVERAGE_FAIL

    def test_risk_config_fail_returns_risk_config_fail(self) -> None:
        """Risk config failure returns RISK_CONFIG_FAIL."""
        report = GateReport(
            checks=(
                GateCheck(
                    "risk_limits_configured", GateCheckStatus.FAIL, required=True
                ),
            ),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.RISK_CONFIG_FAIL

    def test_broker_creds_fail_returns_broker_creds_fail(self) -> None:
        """Broker creds failure returns BROKER_CREDS_FAIL."""
        report = GateReport(
            checks=(
                GateCheck("broker_credentials", GateCheckStatus.FAIL, required=True),
            ),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.BROKER_CREDS_FAIL

    def test_model_weights_fail_returns_model_weights_fail(self) -> None:
        """Model weights failure returns MODEL_WEIGHTS_FAIL (军规级 v4.0)."""
        report = GateReport(
            checks=(
                GateCheck("model_weights_exist", GateCheckStatus.FAIL, required=True),
            ),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.MODEL_WEIGHTS_FAIL

    def test_scenarios_complete_fail_returns_scenario_missing(self) -> None:
        """Scenarios complete failure returns SCENARIO_MISSING (军规级 v4.0)."""
        report = GateReport(
            checks=(
                GateCheck("scenarios_complete", GateCheckStatus.FAIL, required=True),
            ),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.SCENARIO_MISSING

    def test_capability_present_fail_returns_capability_missing(self) -> None:
        """Capability present failure returns CAPABILITY_MISSING (军规级 v4.0)."""
        report = GateReport(
            checks=(
                GateCheck("capability_present", GateCheckStatus.FAIL, required=True),
            ),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.CAPABILITY_MISSING

    def test_unknown_fail_returns_general_error(self) -> None:
        """Unknown failure returns GENERAL_ERROR."""
        report = GateReport(
            checks=(GateCheck("unknown_check", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        assert get_exit_code(report) == ExitCode.GENERAL_ERROR


class TestCheckMode:
    """Tests for CHECK_MODE functions."""

    def test_check_mode_disabled_by_default(self) -> None:
        """CHECK_MODE is disabled by default."""
        disable_check_mode()  # Ensure clean state
        assert is_check_mode() is False

    def test_enable_check_mode(self) -> None:
        """enable_check_mode enables CHECK_MODE."""
        disable_check_mode()
        enable_check_mode()
        assert is_check_mode() is True
        disable_check_mode()

    def test_disable_check_mode(self) -> None:
        """disable_check_mode disables CHECK_MODE."""
        enable_check_mode()
        disable_check_mode()
        assert is_check_mode() is False

    def test_assert_not_check_mode_passes_when_disabled(self) -> None:
        """assert_not_check_mode passes when disabled."""
        disable_check_mode()
        assert_not_check_mode("place_order")  # Should not raise

    def test_assert_not_check_mode_raises_when_enabled(self) -> None:
        """assert_not_check_mode raises when enabled."""
        enable_check_mode()
        with pytest.raises(RuntimeError, match="BLOCKED"):
            assert_not_check_mode("place_order")
        disable_check_mode()


class TestCIStepFailure:
    """Tests for CIStepFailure dataclass."""

    def test_basic_failure(self) -> None:
        """Basic failure fields are set correctly."""
        failure = CIStepFailure(
            file="test.py",
            line=42,
            rule="E501",
            message="line too long",
        )
        assert failure.file == "test.py"
        assert failure.line == 42
        assert failure.rule == "E501"
        assert failure.message == "line too long"


class TestCIStep:
    """Tests for CIStep dataclass."""

    def test_pass_step(self) -> None:
        """PASS step has correct status."""
        step = CIStep(
            name="test",
            status=CIStepStatus.PASS,
            exit_code=0,
            duration_ms=100,
        )
        assert step.status == CIStepStatus.PASS
        assert step.exit_code == 0

    def test_fail_step(self) -> None:
        """FAIL step has correct fields."""
        step = CIStep(
            name="lint",
            status=CIStepStatus.FAIL,
            exit_code=2,
            duration_ms=200,
            summary="Some errors",
            failures=[CIStepFailure("test.py", 1, "E501", "line too long")],
            hints=["Fix the lint issue"],
        )
        assert step.status == CIStepStatus.FAIL
        assert len(step.failures) == 1
        assert len(step.hints) == 1

    def test_skip_step(self) -> None:
        """SKIP step has reason."""
        step = CIStep(
            name="test",
            status=CIStepStatus.SKIP,
            reason="previous step failed",
        )
        assert step.status == CIStepStatus.SKIP
        assert step.reason == "previous step failed"

    def test_to_dict_pass(self) -> None:
        """to_dict for PASS step."""
        step = CIStep(
            name="test", status=CIStepStatus.PASS, exit_code=0, duration_ms=100
        )
        d = step.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "PASS"
        assert d["exit_code"] == 0

    def test_to_dict_fail(self) -> None:
        """to_dict for FAIL step includes summary and failures."""
        step = CIStep(
            name="lint",
            status=CIStepStatus.FAIL,
            exit_code=2,
            duration_ms=200,
            summary="Error output",
            failures=[CIStepFailure("test.py", 1, "E501", "line too long")],
            hints=["Fix it"],
        )
        d = step.to_dict()
        assert "summary" in d
        assert "failures" in d
        assert "hints" in d

    def test_to_dict_skip(self) -> None:
        """to_dict for SKIP step includes reason."""
        step = CIStep(name="test", status=CIStepStatus.SKIP, reason="skipped")
        d = step.to_dict()
        assert d["reason"] == "skipped"


class TestCIJsonReport:
    """Tests for CIJsonReport."""

    def test_default_schema_version(self) -> None:
        """Default schema_version is 3."""
        report = CIJsonReport()
        assert report.schema_version == 3

    def test_auto_generates_timestamp(self) -> None:
        """timestamp is auto-generated."""
        report = CIJsonReport()
        assert report.timestamp
        assert "T" in report.timestamp

    def test_auto_generates_run_id(self) -> None:
        """run_id is auto-generated."""
        report = CIJsonReport()
        assert report.run_id
        assert len(report.run_id) == 36

    def test_auto_generates_exec_id(self) -> None:
        """exec_id is auto-generated."""
        report = CIJsonReport()
        assert report.exec_id
        assert "_" in report.exec_id

    def test_all_passed_when_no_failures(self) -> None:
        """all_passed is True when no FAIL steps."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.all_passed is True

    def test_all_passed_false_when_failure(self) -> None:
        """all_passed is False when FAIL step exists."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.FAIL, exit_code=1))
        assert report.all_passed is False

    def test_failed_step_returns_first_failure(self) -> None:
        """failed_step returns first failed step name."""
        report = CIJsonReport()
        report.add_step(CIStep(name="pass1", status=CIStepStatus.PASS))
        report.add_step(CIStep(name="fail1", status=CIStepStatus.FAIL, exit_code=2))
        report.add_step(CIStep(name="fail2", status=CIStepStatus.FAIL, exit_code=3))
        assert report.failed_step == "fail1"

    def test_failed_step_none_when_all_pass(self) -> None:
        """failed_step is None when all pass."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.failed_step is None

    def test_overall_pass(self) -> None:
        """overall is PASS when all_passed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.overall == "PASS"

    def test_overall_fail(self) -> None:
        """overall is FAIL when not all_passed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.FAIL, exit_code=1))
        assert report.overall == "FAIL"

    def test_exit_code_success(self) -> None:
        """exit_code is 0 when all pass."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.exit_code == 0

    def test_exit_code_from_failed_step(self) -> None:
        """exit_code comes from first failed step."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.FAIL, exit_code=4))
        assert report.exit_code == 4

    def test_to_dict_has_required_fields(self) -> None:
        """to_dict includes all required fields."""
        report = CIJsonReport(check_mode=True)
        d = report.to_dict()
        assert d["schema_version"] == 3
        assert d["type"] == "ci"
        assert "overall" in d
        assert "exit_code" in d
        assert d["check_mode"] is True
        assert "timestamp" in d
        assert "run_id" in d
        assert "exec_id" in d
        assert "artifacts" in d
        assert "steps" in d

    def test_to_json(self) -> None:
        """to_json returns valid JSON string."""
        report = CIJsonReport()
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["schema_version"] == 3

    def test_save(self) -> None:
        """save writes to file."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            report.save(path)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["schema_version"] == 3


class TestCIJsonReportV3:
    """Tests for CIJsonReportV3."""

    def test_default_values(self) -> None:
        """Default values are correct."""
        report = CIJsonReportV3()
        assert report.schema_version == 3
        assert report.type == "ci"
        assert report.check_mode is False

    def test_auto_generates_timestamp(self) -> None:
        """timestamp is auto-generated."""
        report = CIJsonReportV3()
        assert report.timestamp
        assert "T" in report.timestamp

    def test_add_step(self) -> None:
        """add_step adds to steps list."""
        report = CIJsonReportV3()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert len(report.steps) == 1

    def test_to_dict(self) -> None:
        """to_dict includes all fields."""
        report = CIJsonReportV3()
        d = report.to_dict()
        assert "schema_version" in d
        assert "type" in d
        assert "check_mode" in d

    def test_to_json(self) -> None:
        """to_json returns valid JSON."""
        report = CIJsonReportV3()
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["schema_version"] == 3

    def test_save(self) -> None:
        """save writes to file."""
        report = CIJsonReportV3()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            report.save(path)
            assert path.exists()


class TestParseOutputFunctions:
    """Tests for parse_*_output functions."""

    def test_parse_ruff_output_empty(self) -> None:
        """Empty output returns empty list."""
        failures = parse_ruff_output("")
        assert failures == []

    def test_parse_ruff_output_single_error(self) -> None:
        """Single error is parsed correctly."""
        output = "test.py:10:5: E501 line too long"
        failures = parse_ruff_output(output)
        assert len(failures) == 1
        assert failures[0].file == "test.py"
        assert failures[0].line == 10
        assert failures[0].rule == "E501"

    def test_parse_ruff_output_multiple_errors(self) -> None:
        """Multiple errors are parsed correctly."""
        output = "test.py:10:5: E501 line too long\ntest.py:20:1: F401 unused import"
        failures = parse_ruff_output(output)
        assert len(failures) == 2

    def test_parse_mypy_output_empty(self) -> None:
        """Empty output returns empty list."""
        failures = parse_mypy_output("")
        assert failures == []

    def test_parse_mypy_output_single_error(self) -> None:
        """Single error is parsed correctly."""
        output = "test.py:10: error: Invalid type"
        failures = parse_mypy_output(output)
        assert len(failures) == 1
        assert failures[0].file == "test.py"
        assert failures[0].line == 10
        assert failures[0].rule == "error"

    def test_parse_mypy_output_skips_found_line(self) -> None:
        """Found X errors line is skipped."""
        output = "Found 1 error in 1 file"
        failures = parse_mypy_output(output)
        assert failures == []

    def test_parse_pytest_output_empty(self) -> None:
        """Empty output returns empty list."""
        failures = parse_pytest_output("")
        assert failures == []

    def test_parse_pytest_output_failed_test(self) -> None:
        """FAILED test is parsed correctly."""
        output = "FAILED tests/test_foo.py::test_bar - AssertionError"
        failures = parse_pytest_output(output)
        assert len(failures) == 1
        assert "test_foo.py" in failures[0].file
        assert failures[0].rule == "FAILED"


class TestGetHintsForStep:
    """Tests for get_hints_for_step function."""

    def test_default_hints_for_format(self) -> None:
        """Default hints for format-check step."""
        hints = get_hints_for_step("format-check", [], "")
        assert len(hints) > 0

    def test_default_hints_for_lint(self) -> None:
        """Default hints for lint step."""
        hints = get_hints_for_step("lint", [], "")
        assert len(hints) > 0

    def test_specific_hints_for_e501(self) -> None:
        """Specific hints for E501 rule."""
        failures = [CIStepFailure("test.py", 1, "E501", "line too long")]
        hints = get_hints_for_step("lint", failures, "")
        assert any("Line too long" in h for h in hints)

    def test_specific_hints_for_f401(self) -> None:
        """Specific hints for F401 rule."""
        failures = [CIStepFailure("test.py", 1, "F401", "unused import")]
        hints = get_hints_for_step("lint", failures, "")
        assert any("Unused import" in h for h in hints)

    def test_max_5_hints(self) -> None:
        """Maximum 5 hints returned."""
        failures = [CIStepFailure("test.py", i, f"E{i}", "error") for i in range(10)]
        hints = get_hints_for_step("lint", failures, "")
        assert len(hints) <= 5


class TestPolicyViolation:
    """Tests for PolicyViolation dataclass."""

    def test_basic_violation(self) -> None:
        """Basic violation fields are set."""
        violation = PolicyViolation(
            code="TEST.001",
            message="Test violation",
            evidence={"key": "value"},
        )
        assert violation.code == "TEST.001"
        assert violation.message == "Test violation"
        assert violation.evidence == {"key": "value"}

    def test_default_evidence(self) -> None:
        """Evidence defaults to empty dict."""
        violation = PolicyViolation(code="TEST", message="Test")
        assert violation.evidence == {}

    def test_to_dict(self) -> None:
        """to_dict includes all fields."""
        violation = PolicyViolation(code="TEST", message="Test", evidence={"a": 1})
        d = violation.to_dict()
        assert d["code"] == "TEST"
        assert d["message"] == "Test"
        assert d["evidence"] == {"a": 1}


class TestPolicyReport:
    """Tests for PolicyReport."""

    def test_default_values(self) -> None:
        """Default values are correct."""
        report = PolicyReport()
        assert report.violations == []
        assert report.timestamp

    def test_has_violations_false_when_empty(self) -> None:
        """has_violations is False when empty."""
        report = PolicyReport()
        assert report.has_violations is False

    def test_has_violations_true_when_violations(self) -> None:
        """has_violations is True when violations exist."""
        report = PolicyReport()
        report.add_violation("TEST", "Test violation")
        assert report.has_violations is True

    def test_add_violation(self) -> None:
        """add_violation adds to list."""
        report = PolicyReport()
        report.add_violation("TEST", "Test message", {"key": "value"})
        assert len(report.violations) == 1
        assert report.violations[0].code == "TEST"

    def test_to_dict(self) -> None:
        """to_dict includes all fields."""
        report = PolicyReport()
        report.add_violation("TEST", "Test")
        d = report.to_dict()
        assert "timestamp" in d
        assert d["has_violations"] is True
        assert d["violation_count"] == 1
        assert len(d["violations"]) == 1

    def test_to_json(self) -> None:
        """to_json returns valid JSON."""
        report = PolicyReport()
        json_str = report.to_json()
        data = json.loads(json_str)
        assert "timestamp" in data

    def test_save(self) -> None:
        """save writes to file."""
        report = PolicyReport()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "policy.json"
            report.save(path)
            assert path.exists()


class TestValidateReportSchema:
    """Tests for validate_report_schema function."""

    def test_missing_file(self) -> None:
        """Missing file returns violation."""
        report = validate_report_schema("nonexistent/file.json")
        assert report.has_violations
        assert any(v.code == "SCHEMA.FILE_MISSING" for v in report.violations)

    def test_invalid_json(self) -> None:
        """Invalid JSON returns violation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.json"
            path.write_text("not valid json {")
            report = validate_report_schema(str(path))
            assert report.has_violations
            assert any(v.code == "SCHEMA.INVALID_JSON" for v in report.violations)

    def test_missing_required_fields(self) -> None:
        """Missing required fields returns violation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "incomplete.json"
            path.write_text('{"type": "ci"}')
            report = validate_report_schema(str(path))
            assert report.has_violations
            assert any(v.code == "SCHEMA.MISSING_FIELDS" for v in report.violations)

    def test_outdated_schema_version(self) -> None:
        """Schema version < 3 returns violation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "old.json"
            data = {
                "schema_version": 2,
                "type": "ci",
                "overall": "PASS",
                "exit_code": 0,
                "check_mode": True,
            }
            path.write_text(json.dumps(data))
            report = validate_report_schema(str(path))
            assert report.has_violations
            assert any(v.code == "SCHEMA.VERSION_OUTDATED" for v in report.violations)

    def test_valid_ci_report(self) -> None:
        """Valid CI report returns no violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "valid.json"
            data = {
                "schema_version": 3,
                "type": "ci",
                "overall": "PASS",
                "exit_code": 0,
                "check_mode": True,
            }
            path.write_text(json.dumps(data))
            report = validate_report_schema(str(path))
            assert not report.has_violations

    def test_replay_without_check_mode(self) -> None:
        """Replay without check_mode returns violation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "replay.json"
            data = {
                "schema_version": 3,
                "type": "replay",
                "overall": "PASS",
                "exit_code": 0,
                "check_mode": False,
                "scenarios_total": 10,
                "scenarios_passed": 10,
                "scenarios_failed": 0,
            }
            path.write_text(json.dumps(data))
            report = validate_report_schema(str(path), report_type="replay")
            assert report.has_violations
            assert any(
                v.code == "POLICY.CHECK_MODE_DISABLED" for v in report.violations
            )


class TestCheckCommandWhitelist:
    """Tests for check_command_whitelist function."""

    def test_pytest_blacklisted(self) -> None:
        """Direct pytest invocation is blacklisted."""
        report = check_command_whitelist("pytest tests/")
        assert report.has_violations
        assert any(v.code == "POLICY.COMMAND_BLACKLISTED" for v in report.violations)

    def test_ruff_blacklisted(self) -> None:
        """Direct ruff invocation is blacklisted."""
        report = check_command_whitelist("ruff check .")
        assert report.has_violations

    def test_mypy_blacklisted(self) -> None:
        """Direct mypy invocation is blacklisted."""
        report = check_command_whitelist("mypy src/")
        assert report.has_violations

    def test_python_m_pytest_blacklisted(self) -> None:
        """python -m pytest is blacklisted."""
        report = check_command_whitelist("python -m pytest tests/")
        assert report.has_violations

    def test_git_status_allowed(self) -> None:
        """Git status is allowed."""
        report = check_command_whitelist("git status")
        assert not report.has_violations


class TestLogGateReport:
    """Tests for log_gate_report function."""

    def test_log_pass_report(self) -> None:
        """Logging pass report does not raise."""
        report = GateReport(
            checks=(GateCheck("a", GateCheckStatus.PASS),),
            target_mode="LIVE",
        )
        log_gate_report(report)  # Should not raise

    def test_log_fail_report(self) -> None:
        """Logging fail report does not raise."""
        report = GateReport(
            checks=(GateCheck("a", GateCheckStatus.FAIL, required=True),),
            target_mode="LIVE",
        )
        log_gate_report(report)  # Should not raise
