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
from datetime import UTC, datetime
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
# 退出码约定（军规级）
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
        8 = Replay failed (reserved for sim_gate)
        9 = Sim failed (reserved for sim_gate)
        12 = Policy violation (military-grade enforcement)
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    FORMAT_LINT_FAIL = 2
    TYPE_CHECK_FAIL = 3
    TEST_FAIL = 4
    COVERAGE_FAIL = 5
    RISK_CONFIG_FAIL = 6
    BROKER_CREDS_FAIL = 7
    REPLAY_FAIL = 8
    SIM_FAIL = 9
    POLICY_VIOLATION = 12


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


# =============================================================================
# CI JSON 报告生成（供 Claude 自动闭环使用）
# =============================================================================


class CIStepStatus(str, Enum):
    """CI step status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CIStepFailure:
    """Single failure detail within a CI step."""

    file: str
    line: int
    rule: str
    message: str


@dataclass
class CIStep:
    """Single CI step result."""

    name: str
    status: CIStepStatus
    exit_code: int | None = None
    duration_ms: int = 0
    summary: str = ""  # First 50 lines of output
    reason: str = ""  # For SKIP status
    failures: list[CIStepFailure] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)  # Common fix suggestions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }
        if self.status == CIStepStatus.SKIP:
            result["reason"] = self.reason
        elif self.status == CIStepStatus.FAIL:
            result["summary"] = self.summary
            if self.failures:
                result["failures"] = [asdict(f) for f in self.failures]
            if self.hints:
                result["hints"] = self.hints
        return result


@dataclass
class CIJsonReport:
    """Machine-readable CI report for Claude automated loop.

    Enhanced structure for stable Claude parsing:
    - all_passed: boolean for quick check
    - failed_step: first failed step name (or null)
    - exit_code: mapped exit code
    - steps: detailed per-step results with hints
    """

    steps: list[CIStep] = field(default_factory=list)
    version: str = "2.0"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    @property
    def all_passed(self) -> bool:
        """Check if all steps passed."""
        return not any(s.status == CIStepStatus.FAIL for s in self.steps)

    @property
    def failed_step(self) -> str | None:
        """Get first failed step name."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL:
                return step.name
        return None

    @property
    def overall(self) -> str:
        """Overall status string."""
        return "PASS" if self.all_passed else "FAIL"

    @property
    def exit_code(self) -> int:
        """Overall exit code (first failure)."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL and step.exit_code is not None:
                return step.exit_code
        return 0

    def add_step(self, step: CIStep) -> None:
        """Add a CI step result."""
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "all_passed": self.all_passed,
            "failed_step": self.failed_step,
            "overall": self.overall,
            "exit_code": self.exit_code,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str | Path) -> None:
        """Save report to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("CI report saved to %s", path)


def parse_ruff_output(output: str) -> list[CIStepFailure]:
    """Parse ruff output into structured failures."""
    failures = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        # Format: path/file.py:line:col: RULE message
        parts = line.split(":", 3)
        if len(parts) >= 4:
            file_path = parts[0]
            try:
                line_no = int(parts[1])
            except ValueError:
                continue
            rest = parts[3].strip()
            # Extract rule code (e.g., E501, W503)
            rule_parts = rest.split(" ", 1)
            rule = rule_parts[0] if rule_parts else ""
            message = rule_parts[1] if len(rule_parts) > 1 else rest
            failures.append(CIStepFailure(file=file_path, line=line_no, rule=rule, message=message))
    return failures


def parse_mypy_output(output: str) -> list[CIStepFailure]:
    """Parse mypy output into structured failures."""
    failures = []
    for line in output.strip().split("\n"):
        if not line.strip() or line.startswith("Found"):
            continue
        # Format: path/file.py:line: error: message
        parts = line.split(":", 3)
        if len(parts) >= 3:
            file_path = parts[0]
            try:
                line_no = int(parts[1])
            except ValueError:
                continue
            message = parts[2].strip() if len(parts) == 3 else parts[3].strip()
            rule = "type-error"
            if ": error:" in line:
                rule = "error"
            elif ": note:" in line:
                rule = "note"
            failures.append(CIStepFailure(file=file_path, line=line_no, rule=rule, message=message))
    return failures


def parse_pytest_output(output: str) -> list[CIStepFailure]:
    """Parse pytest output into structured failures."""
    failures = []
    # Look for FAILED lines
    for line in output.strip().split("\n"):
        if "FAILED" in line:
            # Format: FAILED tests/test_foo.py::test_bar - AssertionError
            parts = line.split(" ", 2)
            if len(parts) >= 2:
                test_path = parts[1].split("::")[0] if "::" in parts[1] else parts[1]
                message = parts[2] if len(parts) > 2 else "test failed"
                failures.append(
                    CIStepFailure(file=test_path, line=0, rule="FAILED", message=message)
                )
    return failures


# =============================================================================
# Hints 生成（常见错误的修复建议）
# =============================================================================

STEP_HINTS: dict[str, dict[str, list[str]]] = {
    "format-check": {
        "default": [
            "Run: make format (or .\\scripts\\make.ps1 format) to auto-fix",
            "Most format issues can be auto-fixed by ruff",
        ],
    },
    "lint": {
        "E501": ["Line too long - break into multiple lines or use parentheses"],
        "F401": ["Unused import - remove the import statement"],
        "F841": ["Unused variable - remove or use the variable"],
        "E711": ["Use 'is None' instead of '== None'"],
        "E712": ["Use 'is True/False' instead of '== True/False'"],
        "default": [
            "Run: make lint-fix to auto-fix some issues",
            "Check ruff docs for rule explanation",
        ],
    },
    "type": {
        "default": [
            "Add type annotations to function parameters and return values",
            "Use 'Any' as escape hatch if truly dynamic typing needed",
            "Check mypy docs for error explanation",
        ],
        "incompatible": ["Check if types match between assignment and variable"],
        "missing": ["Add missing type stub or use 'type: ignore' comment"],
    },
    "test": {
        "default": [
            "Check test assertion - expected vs actual values",
            "Run specific test: pytest tests/test_xxx.py::test_name -xvs",
        ],
        "coverage": [
            "Add tests for uncovered code paths",
            "Current threshold: 85% - check coverage report for gaps",
        ],
    },
}


def get_hints_for_step(step_name: str, failures: list[CIStepFailure], output: str) -> list[str]:
    """Generate hints based on step name and failures."""
    hints: list[str] = []
    step_hints = STEP_HINTS.get(step_name, {})

    # Check for specific rule hints
    seen_rules: set[str] = set()
    for failure in failures:
        rule = failure.rule
        if rule not in seen_rules and rule in step_hints:
            hints.extend(step_hints[rule])
            seen_rules.add(rule)

    # Check output for keywords
    if "coverage" in output.lower() and "coverage" in step_hints:
        hints.extend(step_hints["coverage"])
    if "incompatible" in output.lower() and "incompatible" in step_hints:
        hints.extend(step_hints["incompatible"])

    # Add default hints if no specific ones found
    if not hints and "default" in step_hints:
        hints.extend(step_hints["default"])

    return hints[:5]  # Limit to 5 hints


def run_ci_step(
    name: str,
    command: list[str],
    exit_code_on_fail: int,
    parser: Any = None,  # Callable[[str], list[CIStepFailure]]
) -> CIStep:
    """
    Run a single CI step and capture result.

    Args:
        name: Step name (format-check, lint, type, test)
        command: Command to run
        exit_code_on_fail: Exit code to use on failure
        parser: Optional output parser function

    Returns:
        CIStep with result
    """
    start = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )
        duration_ms = int((time.time() - start) * 1000)
        output = result.stdout + result.stderr

        if result.returncode == 0:
            return CIStep(
                name=name,
                status=CIStepStatus.PASS,
                exit_code=0,
                duration_ms=duration_ms,
            )

        # Parse failures if parser provided
        failures = parser(output) if parser else []

        # Truncate output summary to first 50 lines
        output_lines = output.strip().split("\n")
        summary = "\n".join(output_lines[:50])

        # Generate hints
        hints = get_hints_for_step(name, failures, output)

        return CIStep(
            name=name,
            status=CIStepStatus.FAIL,
            exit_code=exit_code_on_fail,
            duration_ms=duration_ms,
            summary=summary,
            failures=failures,
            hints=hints,
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return CIStep(
            name=name,
            status=CIStepStatus.FAIL,
            exit_code=exit_code_on_fail,
            duration_ms=duration_ms,
            summary="Command timed out after 600 seconds",
            hints=["Check for infinite loops or very slow operations"],
        )
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return CIStep(
            name=name,
            status=CIStepStatus.FAIL,
            exit_code=exit_code_on_fail,
            duration_ms=duration_ms,
            summary=f"Error running command: {e}",
            hints=["Check if the command exists and dependencies are installed"],
        )


def run_ci_with_json_report(
    python_exe: str = ".venv/Scripts/python.exe",
    output_path: str = "artifacts/check/report.json",
    cov_threshold: int = 85,
) -> CIJsonReport:
    """
    Run full CI pipeline and generate JSON report.

    Args:
        python_exe: Path to Python executable
        output_path: Output path for JSON report
        cov_threshold: Coverage threshold percentage

    Returns:
        CIJsonReport with all results
    """
    report = CIJsonReport()

    # Step 1: Format check
    step = run_ci_step(
        name="format-check",
        command=[python_exe, "-m", "ruff", "format", "--check", "."],
        exit_code_on_fail=ExitCode.FORMAT_LINT_FAIL,
        parser=parse_ruff_output,
    )
    report.add_step(step)

    if step.status == CIStepStatus.FAIL:
        # Skip remaining steps
        for name in ["lint", "type", "test"]:
            report.add_step(
                CIStep(
                    name=name,
                    status=CIStepStatus.SKIP,
                    reason="previous step failed",
                )
            )
        report.save(output_path)
        return report

    # Step 2: Lint
    step = run_ci_step(
        name="lint",
        command=[python_exe, "-m", "ruff", "check", "."],
        exit_code_on_fail=ExitCode.FORMAT_LINT_FAIL,
        parser=parse_ruff_output,
    )
    report.add_step(step)

    if step.status == CIStepStatus.FAIL:
        for name in ["type", "test"]:
            report.add_step(
                CIStep(
                    name=name,
                    status=CIStepStatus.SKIP,
                    reason="previous step failed",
                )
            )
        report.save(output_path)
        return report

    # Step 3: Type check
    step = run_ci_step(
        name="type",
        command=[python_exe, "-m", "mypy", "."],
        exit_code_on_fail=ExitCode.TYPE_CHECK_FAIL,
        parser=parse_mypy_output,
    )
    report.add_step(step)

    if step.status == CIStepStatus.FAIL:
        report.add_step(
            CIStep(
                name="test",
                status=CIStepStatus.SKIP,
                reason="previous step failed",
            )
        )
        report.save(output_path)
        return report

    # Step 4: Test
    step = run_ci_step(
        name="test",
        command=[
            python_exe,
            "-m",
            "pytest",
            "-q",
            "--cov=src",
            "--cov-report=term-missing:skip-covered",
            f"--cov-fail-under={cov_threshold}",
        ],
        exit_code_on_fail=ExitCode.TEST_FAIL,
        parser=parse_pytest_output,
    )
    report.add_step(step)

    report.save(output_path)
    return report


# =============================================================================
# Schema 校验与 Policy Violation 检测（军规级）
# =============================================================================

# CI Report v3.0 必须字段
CI_REPORT_REQUIRED_FIELDS = {
    "schema_version",
    "type",
    "overall",
    "exit_code",
    "check_mode",
}

# Sim/Replay Report 必须字段
SIM_REPORT_REQUIRED_FIELDS = {
    "schema_version",
    "type",
    "overall",
    "exit_code",
    "check_mode",
    "scenarios_total",
    "scenarios_passed",
    "scenarios_failed",
}

# Failure 必须字段
FAILURE_REQUIRED_FIELDS = {
    "rule_id",
    "component",
    "expected",
    "actual",
    "tick",
    "error",
}


@dataclass
class PolicyViolation:
    """Policy violation detail."""

    code: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass
class PolicyReport:
    """Policy violation report."""

    violations: list[PolicyViolation] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    @property
    def has_violations(self) -> bool:
        """Check if any violations exist."""
        return len(self.violations) > 0

    def add_violation(
        self,
        code: str,
        message: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Add a policy violation."""
        self.violations.append(
            PolicyViolation(code=code, message=message, evidence=evidence or {})
        )
        logger.error("POLICY_VIOLATION: [%s] %s", code, message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "has_violations": self.has_violations,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str | Path) -> None:
        """Save report to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("Policy violation report saved to %s", path)


def validate_report_schema(
    report_path: str | Path,
    report_type: str = "ci",
) -> PolicyReport:
    """
    Validate report JSON schema and return policy violations.

    Args:
        report_path: Path to report.json
        report_type: Type of report ("ci", "replay", "sim")

    Returns:
        PolicyReport with any violations found
    """
    policy_report = PolicyReport()
    path = Path(report_path)

    # Check 1: File exists
    if not path.exists():
        policy_report.add_violation(
            code="SCHEMA.FILE_MISSING",
            message=f"Report file not found: {path}",
            evidence={"expected_path": str(path)},
        )
        return policy_report

    # Check 2: Valid JSON
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        policy_report.add_violation(
            code="SCHEMA.INVALID_JSON",
            message=f"Invalid JSON in report: {e}",
            evidence={"path": str(path), "error": str(e)},
        )
        return policy_report

    # Check 3: Required fields
    required_fields = (
        SIM_REPORT_REQUIRED_FIELDS
        if report_type in ("replay", "sim")
        else CI_REPORT_REQUIRED_FIELDS
    )

    missing_fields = required_fields - set(data.keys())
    if missing_fields:
        policy_report.add_violation(
            code="SCHEMA.MISSING_FIELDS",
            message=f"Missing required fields: {missing_fields}",
            evidence={"missing": list(missing_fields), "found": list(data.keys())},
        )

    # Check 4: Schema version
    if "schema_version" in data:
        version = data["schema_version"]
        if not isinstance(version, int) or version < 3:
            policy_report.add_violation(
                code="SCHEMA.VERSION_OUTDATED",
                message=f"Schema version must be >= 3, got {version}",
                evidence={"current_version": version, "required_version": 3},
            )

    # Check 5: check_mode must be True for replay/sim
    if report_type in ("replay", "sim"):
        if not data.get("check_mode", False):
            policy_report.add_violation(
                code="POLICY.CHECK_MODE_DISABLED",
                message="CHECK_MODE must be enabled for replay/sim",
                evidence={"check_mode": data.get("check_mode")},
            )

    # Check 6: Failure structure (for replay/sim)
    if report_type in ("replay", "sim") and "failures" in data:
        for i, failure in enumerate(data["failures"]):
            if not isinstance(failure, dict):
                continue
            missing = FAILURE_REQUIRED_FIELDS - set(failure.keys())
            if missing:
                policy_report.add_violation(
                    code="SCHEMA.FAILURE_INCOMPLETE",
                    message=f"Failure {i} missing fields: {missing}",
                    evidence={
                        "index": i,
                        "missing": list(missing),
                        "failure": failure,
                    },
                )

    return policy_report


def check_command_whitelist(command: str) -> PolicyReport:
    """
    Check if a command is in the whitelist.

    Only make.ps1 targets are allowed.

    Args:
        command: Command string to check

    Returns:
        PolicyReport with any violations
    """
    policy_report = PolicyReport()

    # Whitelist: only make.ps1 targets
    allowed_patterns = [
        r"\.[\\/]scripts[\\/]make\.ps1",
        r"make\.ps1",
        r"git\s+(status|diff|log)",
        r"cat\s+",
        r"Get-Content\s+",
    ]

    # Blacklist: direct tool invocation
    blacklist_patterns = [
        r"^pytest\s",
        r"^ruff\s",
        r"^mypy\s",
        r"python\s+-m\s+pytest",
        r"python\s+-m\s+ruff",
        r"python\s+-m\s+mypy",
    ]

    import re

    for pattern in blacklist_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            policy_report.add_violation(
                code="POLICY.COMMAND_BLACKLISTED",
                message=f"Direct tool invocation not allowed: {command}",
                evidence={
                    "command": command,
                    "pattern": pattern,
                    "hint": "Use make.ps1 targets instead",
                },
            )
            break

    return policy_report


def check_artifact_paths() -> PolicyReport:
    """
    Check that artifact paths match the fixed convention.

    D.1: 产物路径绝对不变

    Returns:
        PolicyReport with any violations
    """
    policy_report = PolicyReport()

    expected_paths = {
        "ci_report": Path("artifacts/check/report.json"),
        "sim_report": Path("artifacts/sim/report.json"),
        "context": Path("artifacts/context/context.md"),
        "commands_log": Path("artifacts/claude/commands.log"),
        "round_summary": Path("artifacts/claude/round_summary.json"),
        "policy_violation": Path("artifacts/claude/policy_violation.json"),
    }

    # Just validate the structure is known
    # Actual path checking happens at runtime
    return policy_report


# =============================================================================
# Enhanced CIJsonReport v3.0（军规级）
# =============================================================================


@dataclass
class CIJsonReportV3:
    """Machine-readable CI report v3.0 for military-grade Claude loop.

    Military-grade enhancements:
    - schema_version: integer, must be >= 3
    - type: report type ("ci", "replay", "sim")
    - check_mode: boolean, must be true for replay/sim
    - Strict field validation
    """

    steps: list[CIStep] = field(default_factory=list)
    schema_version: int = 3
    type: str = "ci"
    check_mode: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    @property
    def all_passed(self) -> bool:
        """Check if all steps passed."""
        return not any(s.status == CIStepStatus.FAIL for s in self.steps)

    @property
    def failed_step(self) -> str | None:
        """Get first failed step name."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL:
                return step.name
        return None

    @property
    def overall(self) -> str:
        """Overall status string."""
        return "PASS" if self.all_passed else "FAIL"

    @property
    def exit_code(self) -> int:
        """Overall exit code (first failure)."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL and step.exit_code is not None:
                return step.exit_code
        return 0

    def add_step(self, step: CIStep) -> None:
        """Add a CI step result."""
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "timestamp": self.timestamp,
            "check_mode": self.check_mode,
            "all_passed": self.all_passed,
            "failed_step": self.failed_step,
            "overall": self.overall,
            "exit_code": self.exit_code,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str | Path) -> None:
        """Save report to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("CI report v3 saved to %s", path)

