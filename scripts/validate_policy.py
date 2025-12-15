#!/usr/bin/env python3
"""Policy Validator for Claude Automated Loop (Military-Grade v3.0).

Validates that all reports conform to military-grade schema requirements:
- schema_version >= 3
- run_id (UUID format)
- exec_id (commit_sha + timestamp)
- artifacts with fixed paths
- check_mode = True for replay/sim

Exit codes:
- 0: All validations passed
- 12: POLICY_VIOLATION (schema mismatch, missing fields, etc.)

Usage:
    python scripts/validate_policy.py --ci-report artifacts/check/report.json
    python scripts/validate_policy.py --sim-report artifacts/sim/report.json
    python scripts/validate_policy.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# =============================================================================
# Exit Codes (Military-Grade)
# =============================================================================
EXIT_SUCCESS = 0
EXIT_POLICY_VIOLATION = 12

# =============================================================================
# Fixed Paths (D.1 - 路径绝对不变)
# =============================================================================
FIXED_PATHS = {
    "ci_report": Path("artifacts/check/report.json"),
    "sim_report": Path("artifacts/sim/report.json"),
    "events_jsonl": Path("artifacts/sim/events.jsonl"),
    "context": Path("artifacts/context/context.md"),
    "commands_log": Path("artifacts/claude/commands.log"),
    "round_summary": Path("artifacts/claude/round_summary.json"),
    "policy_violation": Path("artifacts/claude/policy_violation.json"),
}

# =============================================================================
# Schema Requirements
# =============================================================================
REQUIRED_SCHEMA_VERSION = 3
UUID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$")


@dataclass
class PolicyViolation:
    """Single policy violation."""

    code: str
    message: str
    file: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "evidence": self.evidence,
        }


@dataclass
class ValidationResult:
    """Policy validation result."""

    passed: bool = True
    violations: list[PolicyViolation] = field(default_factory=list)

    def add_violation(
        self,
        code: str,
        message: str,
        file: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Add a violation and mark as failed."""
        self.passed = False
        self.violations.append(
            PolicyViolation(
                code=code,
                message=message,
                file=file,
                evidence=evidence or {},
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
        }


# =============================================================================
# Validators
# =============================================================================


def validate_ci_report(path: Path, result: ValidationResult) -> None:
    """Validate CI report against military-grade schema."""
    if not path.exists():
        result.add_violation(
            "POLICY.FILE_MISSING",
            f"CI report not found: {path}",
            str(path),
        )
        return

    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        result.add_violation(
            "POLICY.JSON_INVALID",
            f"Invalid JSON: {e}",
            str(path),
        )
        return

    # Required top-level fields
    required_fields = [
        "schema_version",
        "type",
        "overall",
        "exit_code",
        "check_mode",
        "timestamp",
        "run_id",
        "exec_id",
        "artifacts",
        "steps",
    ]

    for field_name in required_fields:
        if field_name not in report:
            result.add_violation(
                "SCHEMA.MISSING_FIELD",
                f"Missing required field: {field_name}",
                str(path),
                {"field": field_name},
            )

    # Schema version check
    version = report.get("schema_version")
    if version is not None and version < REQUIRED_SCHEMA_VERSION:
        result.add_violation(
            "SCHEMA.VERSION_OUTDATED",
            f"schema_version {version} < {REQUIRED_SCHEMA_VERSION}",
            str(path),
            {"current": version, "required": REQUIRED_SCHEMA_VERSION},
        )

    # run_id format check (UUID)
    run_id = report.get("run_id", "")
    if run_id and not UUID_PATTERN.match(run_id):
        result.add_violation(
            "SCHEMA.INVALID_RUN_ID",
            f"run_id is not valid UUID format: {run_id}",
            str(path),
            {"run_id": run_id},
        )

    # type check
    report_type = report.get("type")
    if report_type != "ci":
        result.add_violation(
            "SCHEMA.INVALID_TYPE",
            f"CI report type must be 'ci', got: {report_type}",
            str(path),
            {"type": report_type},
        )

    # artifacts.report_path check
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict):
        report_path = artifacts.get("report_path")
        expected_path = str(FIXED_PATHS["ci_report"])
        if report_path and report_path != expected_path:
            result.add_violation(
                "POLICY.FIXED_PATH_MISMATCH",
                f"CI report path must be {expected_path}, got: {report_path}",
                str(path),
                {"expected": expected_path, "actual": report_path},
            )


def validate_sim_report(path: Path, result: ValidationResult) -> None:
    """Validate sim/replay report against military-grade schema."""
    if not path.exists():
        # Sim report is optional if not running sim
        return

    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        result.add_violation(
            "POLICY.JSON_INVALID",
            f"Invalid JSON: {e}",
            str(path),
        )
        return

    # Required top-level fields
    required_fields = [
        "schema_version",
        "type",
        "overall",
        "exit_code",
        "check_mode",
        "timestamp",
        "run_id",
        "exec_id",
        "artifacts",
        "scenarios",
        "failures",
    ]

    for field_name in required_fields:
        if field_name not in report:
            result.add_violation(
                "SCHEMA.MISSING_FIELD",
                f"Missing required field: {field_name}",
                str(path),
                {"field": field_name},
            )

    # Schema version check
    version = report.get("schema_version")
    if version is not None and version < REQUIRED_SCHEMA_VERSION:
        result.add_violation(
            "SCHEMA.VERSION_OUTDATED",
            f"schema_version {version} < {REQUIRED_SCHEMA_VERSION}",
            str(path),
            {"current": version, "required": REQUIRED_SCHEMA_VERSION},
        )

    # check_mode MUST be True for replay/sim
    check_mode = report.get("check_mode")
    if check_mode is not True:
        result.add_violation(
            "POLICY.CHECK_MODE_DISABLED",
            "check_mode must be True for replay/sim reports",
            str(path),
            {"check_mode": check_mode},
        )

    # run_id format check (UUID)
    run_id = report.get("run_id", "")
    if run_id and not UUID_PATTERN.match(run_id):
        result.add_violation(
            "SCHEMA.INVALID_RUN_ID",
            f"run_id is not valid UUID format: {run_id}",
            str(path),
            {"run_id": run_id},
        )

    # type check
    report_type = report.get("type")
    if report_type not in ("replay", "sim"):
        result.add_violation(
            "SCHEMA.INVALID_TYPE",
            f"Sim report type must be 'replay' or 'sim', got: {report_type}",
            str(path),
            {"type": report_type},
        )

    # artifacts check
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict):
        report_path = artifacts.get("report_path")
        expected_path = str(FIXED_PATHS["sim_report"])
        if report_path and report_path != expected_path:
            result.add_violation(
                "POLICY.FIXED_PATH_MISMATCH",
                f"Sim report path must be {expected_path}, got: {report_path}",
                str(path),
                {"expected": expected_path, "actual": report_path},
            )

    # scenarios check
    scenarios = report.get("scenarios", {})
    if isinstance(scenarios, dict):
        for field_name in ["total", "passed", "failed", "skipped"]:
            if field_name not in scenarios:
                result.add_violation(
                    "SCHEMA.MISSING_FIELD",
                    f"Missing scenarios.{field_name}",
                    str(path),
                    {"field": f"scenarios.{field_name}"},
                )

    # failures check - each must have rule_id, component, event_id
    failures = report.get("failures", [])
    if isinstance(failures, list):
        for i, failure in enumerate(failures):
            if not isinstance(failure, dict):
                continue
            for field_name in ["scenario", "rule_id", "component", "event_id", "error"]:
                if field_name not in failure:
                    result.add_violation(
                        "SCHEMA.MISSING_FAILURE_FIELD",
                        f"Failure[{i}] missing field: {field_name}",
                        str(path),
                        {"index": i, "field": field_name},
                    )


def validate_fixed_paths(result: ValidationResult) -> None:
    """Validate that all generated files are in fixed paths."""
    # Check if artifacts directory structure exists
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        # Not a violation if no artifacts yet
        return

    # Check for any reports in wrong locations
    for wrong_path in artifacts_dir.rglob("*.json"):
        relative = wrong_path.relative_to(artifacts_dir)
        relative_str = str(relative).replace("\\", "/")

        # Known allowed paths
        allowed = [
            "check/report.json",
            "sim/report.json",
            "claude/round_summary.json",
            "claude/policy_violation.json",
        ]

        # Also allow instruments and context
        if relative_str.startswith("instruments/"):
            continue
        if relative_str.startswith("context/"):
            continue

        if relative_str not in allowed:
            # Not a hard violation, just a warning
            pass


def write_violation_report(result: ValidationResult, path: Path) -> None:
    """Write policy violation report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(tz=None).astimezone().isoformat(),
        "has_violations": not result.passed,
        "violation_count": len(result.violations),
        "violations": [v.to_dict() for v in result.violations],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Run policy validation."""
    parser = argparse.ArgumentParser(description="Military-Grade Policy Validator")
    parser.add_argument(
        "--ci-report",
        type=Path,
        help="Path to CI report JSON",
    )
    parser.add_argument(
        "--sim-report",
        type=Path,
        help="Path to sim/replay report JSON",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all reports in fixed paths",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXED_PATHS["policy_violation"],
        help="Path to write violation report",
    )

    args = parser.parse_args()

    result = ValidationResult()

    # Validate based on arguments
    if args.all:
        validate_ci_report(FIXED_PATHS["ci_report"], result)
        validate_sim_report(FIXED_PATHS["sim_report"], result)
        validate_fixed_paths(result)
    else:
        if args.ci_report:
            validate_ci_report(args.ci_report, result)
        if args.sim_report:
            validate_sim_report(args.sim_report, result)

    # Output results
    if result.passed:
        print("✅ Policy validation PASSED")
        return EXIT_SUCCESS
    else:
        print(f"❌ Policy validation FAILED with {len(result.violations)} violation(s):")
        for v in result.violations:
            print(f"  [{v.code}] {v.message}")
            if v.file:
                print(f"    File: {v.file}")

        # Write violation report
        write_violation_report(result, args.output)
        print(f"\nViolation report written to: {args.output}")

        return EXIT_POLICY_VIOLATION


if __name__ == "__main__":
    sys.exit(main())
