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
