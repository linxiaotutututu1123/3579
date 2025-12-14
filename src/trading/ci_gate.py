"""CI gate checks for LIVE mode deployment.

Provides pre-deployment checks that must pass before LIVE trading.
Also provides machine-readable JSON report generation for Claude automated loop.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GateCheckStatus(str, Enum):
    """Gate check status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class GateCheck:
    """Single gate check result."""

    name: str
    status: GateCheckStatus
    message: str = ""
    required: bool = True

    @property
    def passed(self) -> bool:
        """Check if this gate passed or was skipped."""
        return self.status in (GateCheckStatus.PASS, GateCheckStatus.SKIP)

    @property
    def blocking(self) -> bool:
        """Check if this failure blocks deployment."""
        return self.required and self.status == GateCheckStatus.FAIL


@dataclass(frozen=True)
class GateReport:
    """Full CI gate report."""

    checks: tuple[GateCheck, ...]
    target_mode: str

    @property
    def all_passed(self) -> bool:
        """Check if all required checks passed."""
        return not any(c.blocking for c in self.checks)

    @property
    def blocking_failures(self) -> list[GateCheck]:
        """Get list of blocking failures."""
        return [c for c in self.checks if c.blocking]

    @property
    def pass_count(self) -> int:
        """Number of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    def summary(self) -> str:
        """Generate summary string."""
        status = "PASS" if self.all_passed else "FAIL"
        return (
            f"CI Gate [{self.target_mode}]: {status} ({self.pass_count}/{len(self.checks)} passed)"
        )


class CIGate:
    """
    CI gate for LIVE mode deployment.

    Runs a series of checks before allowing LIVE deployment.
    """

    def __init__(self, target_mode: str = "LIVE") -> None:
        """
        Initialize CI gate.

        Args:
            target_mode: Target deployment mode
        """
        self._target_mode = target_mode.upper()
        self._checks: list[GateCheck] = []

    def add_check(
        self,
        name: str,
        status: GateCheckStatus,
        message: str = "",
        *,
        required: bool = True,
    ) -> None:
        """Add a gate check."""
        self._checks.append(GateCheck(name=name, status=status, message=message, required=required))

    def check_tests_pass(self, test_passed: bool) -> None:
        """Check if all tests passed."""
        self.add_check(
            "tests_pass",
            GateCheckStatus.PASS if test_passed else GateCheckStatus.FAIL,
            "All tests must pass",
        )

    def check_lint_pass(self, lint_passed: bool) -> None:
        """Check if linting passed."""
        self.add_check(
            "lint_pass",
            GateCheckStatus.PASS if lint_passed else GateCheckStatus.FAIL,
            "Code must pass linting",
        )

    def check_type_check_pass(self, type_check_passed: bool) -> None:
        """Check if type checking passed."""
        self.add_check(
            "type_check_pass",
            GateCheckStatus.PASS if type_check_passed else GateCheckStatus.FAIL,
            "Code must pass type checking",
        )

    def check_risk_limits_configured(self, configured: bool) -> None:
        """Check if risk limits are configured."""
        self.add_check(
            "risk_limits_configured",
            GateCheckStatus.PASS if configured else GateCheckStatus.FAIL,
            "Risk limits must be configured for LIVE",
        )

    def check_broker_credentials(self, credentials_valid: bool) -> None:
        """Check if broker credentials are valid."""
        self.add_check(
            "broker_credentials",
            GateCheckStatus.PASS if credentials_valid else GateCheckStatus.FAIL,
            "Broker credentials must be valid",
        )

    def check_model_weights_exist(self, weights_exist: bool) -> None:
        """Check if model weights exist in repo."""
        self.add_check(
            "model_weights_exist",
            GateCheckStatus.PASS if weights_exist else GateCheckStatus.FAIL,
            "Model weights must be in repository",
        )

    def generate_report(self) -> GateReport:
        """Generate gate report."""
        return GateReport(
            checks=tuple(self._checks),
            target_mode=self._target_mode,
        )

    def run_all_checks(
        self,
        *,
        tests_passed: bool = False,
        lint_passed: bool = False,
        type_check_passed: bool = False,
        risk_limits_configured: bool = False,
        broker_credentials_valid: bool = False,
        model_weights_exist: bool = False,
    ) -> GateReport:
        """
        Run all standard CI gate checks.

        Args:
            tests_passed: Whether tests passed
            lint_passed: Whether linting passed
            type_check_passed: Whether type checking passed
            risk_limits_configured: Whether risk limits are set
            broker_credentials_valid: Whether broker creds are valid
            model_weights_exist: Whether model weights exist

        Returns:
            GateReport with all check results
        """
        self._checks = []  # Reset checks
        self.check_tests_pass(tests_passed)
        self.check_lint_pass(lint_passed)
        self.check_type_check_pass(type_check_passed)
        self.check_risk_limits_configured(risk_limits_configured)
        self.check_broker_credentials(broker_credentials_valid)
        self.check_model_weights_exist(model_weights_exist)
        return self.generate_report()


def log_gate_report(report: GateReport) -> None:
    """Log gate report."""
    logger.info(report.summary())
    for check in report.checks:
        status_str = check.status.value
        req_str = "[REQ]" if check.required else "[OPT]"
        logger.info("  %s %s %s: %s", req_str, status_str, check.name, check.message)
    if report.blocking_failures:
        logger.error("Blocking failures: %d", len(report.blocking_failures))


# =============================================================================
# 退出码约定
# =============================================================================
class ExitCode:
    """Standard exit codes for CI gate.

    Exit codes:
        0 = All checks passed
        1 = General error (unexpected)
        2 = Format or Lint check failed
        3 = Type check failed
        4 = Test failed
        5 = Coverage threshold not met
        6 = Risk limits not configured
        7 = Broker credentials invalid
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    FORMAT_LINT_FAIL = 2
    TYPE_CHECK_FAIL = 3
    TEST_FAIL = 4
    COVERAGE_FAIL = 5
    RISK_CONFIG_FAIL = 6
    BROKER_CREDS_FAIL = 7


def get_exit_code(report: GateReport) -> int:
    """Determine exit code based on gate report.

    Returns appropriate exit code based on first blocking failure.
    """
    if report.all_passed:
        return ExitCode.SUCCESS

    # Check failures in order of priority
    for check in report.blocking_failures:
        if check.name in ("format_pass", "lint_pass"):
            return ExitCode.FORMAT_LINT_FAIL
        if check.name == "type_check_pass":
            return ExitCode.TYPE_CHECK_FAIL
        if check.name == "tests_pass":
            return ExitCode.TEST_FAIL
        if check.name == "coverage_pass":
            return ExitCode.COVERAGE_FAIL
        if check.name == "risk_limits_configured":
            return ExitCode.RISK_CONFIG_FAIL
        if check.name == "broker_credentials":
            return ExitCode.BROKER_CREDS_FAIL

    return ExitCode.GENERAL_ERROR


# =============================================================================
# CHECK 模式硬禁令
# =============================================================================
_CHECK_MODE_ENABLED: bool = False


def enable_check_mode() -> None:
    """Enable CHECK mode - blocks all broker operations."""
    global _CHECK_MODE_ENABLED
    _CHECK_MODE_ENABLED = True
    logger.warning("CHECK_MODE enabled - broker.place_order will be blocked")


def disable_check_mode() -> None:
    """Disable CHECK mode."""
    global _CHECK_MODE_ENABLED
    _CHECK_MODE_ENABLED = False


def is_check_mode() -> bool:
    """Check if CHECK mode is active."""
    return _CHECK_MODE_ENABLED


def assert_not_check_mode(operation: str = "place_order") -> None:
    """Assert that we are NOT in CHECK mode.

    Raises:
        RuntimeError: If CHECK mode is enabled and broker operation is attempted.

    Usage:
        # In broker.place_order():
        assert_not_check_mode("place_order")
    """
    if _CHECK_MODE_ENABLED:
        msg = f"BLOCKED: {operation} is forbidden in CHECK_MODE=1"
        logger.error(msg)
        raise RuntimeError(msg)
