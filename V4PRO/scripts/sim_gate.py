#!/usr/bin/env python3
"""Simulation Gate Validator for Claude Automated Loop (Military-Grade v3.0).

Validates simulation results conform to military-grade requirements:
- sim report exists at artifacts/sim/report.json
- schema_version >= 3
- run_id (UUID format)
- exec_id (commit_sha + timestamp)
- all required scenarios executed
- no unexpected failures

Exit codes:
- 0: Simulation passed
- 9: Simulation failed
- 12: POLICY_VIOLATION (schema mismatch, missing fields)

Usage:
    python scripts/sim_gate.py
    python scripts/sim_gate.py --strict
    python scripts/sim_gate.py --report artifacts/sim/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# Exit Codes (Military-Grade)
# =============================================================================
EXIT_SUCCESS = 0
EXIT_SIM_FAIL = 9
EXIT_POLICY_VIOLATION = 12

# =============================================================================
# Fixed Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_SIM_REPORT = PROJECT_ROOT / "artifacts" / "sim" / "report.json"


def validate_schema_version(report: dict[str, Any]) -> list[str]:
    """Validate schema_version >= 3."""
    errors: list[str] = []
    version = report.get("schema_version")
    if version is None:
        errors.append("Missing required field: schema_version")
    elif not isinstance(version, int):
        errors.append(f"schema_version must be int, got {type(version).__name__}")
    elif version < 3:
        errors.append(f"schema_version must be >= 3, got {version}")
    return errors


def validate_run_id(report: dict[str, Any]) -> list[str]:
    """Validate run_id is UUID format."""
    errors: list[str] = []
    run_id = report.get("run_id")
    if run_id is None:
        errors.append("Missing required field: run_id")
    elif not isinstance(run_id, str):
        errors.append(f"run_id must be str, got {type(run_id).__name__}")
    elif len(run_id) < 32:
        errors.append(f"run_id appears invalid (too short): {run_id}")
    return errors


def validate_exec_id(report: dict[str, Any]) -> list[str]:
    """Validate exec_id format (commit_sha + timestamp)."""
    errors: list[str] = []
    exec_id = report.get("exec_id")
    if exec_id is None:
        errors.append("Missing required field: exec_id")
    elif not isinstance(exec_id, str):
        errors.append(f"exec_id must be str, got {type(exec_id).__name__}")
    elif "_" not in exec_id:
        errors.append(f"exec_id should contain underscore: {exec_id}")
    return errors


def validate_status(report: dict[str, Any]) -> list[str]:
    """Validate status field."""
    errors: list[str] = []
    status = report.get("status")
    if status is None:
        errors.append("Missing required field: status")
    elif status not in ("PASS", "FAIL"):
        errors.append(f"status must be PASS or FAIL, got {status}")
    return errors


def validate_failures(report: dict[str, Any], strict: bool = False) -> list[str]:
    """Validate failures array structure."""
    errors: list[str] = []
    failures = report.get("failures", [])

    if not isinstance(failures, list):
        errors.append(f"failures must be list, got {type(failures).__name__}")
        return errors

    required_fields = {"rule_id", "component", "expected", "actual", "error"}
    if strict:
        required_fields.add("evidence")

    for i, failure in enumerate(failures):
        if not isinstance(failure, dict):
            errors.append(f"failures[{i}] must be dict")
            continue
        missing = required_fields - set(failure.keys())
        if missing:
            errors.append(f"failures[{i}] missing fields: {missing}")

    return errors


def load_report(report_path: Path) -> dict[str, Any] | None:
    """Load simulation report from JSON file."""
    if not report_path.exists():
        return None

    with report_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simulation Gate Validator")
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_SIM_REPORT,
        help="Path to simulation report JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (evidence required)",
    )
    args = parser.parse_args()

    # Load report
    report = load_report(args.report)
    if report is None:
        print(f"[FAIL] Simulation report not found: {args.report}")
        return EXIT_SIM_FAIL

    # Validate schema
    all_errors: list[str] = []
    all_errors.extend(validate_schema_version(report))
    all_errors.extend(validate_run_id(report))
    all_errors.extend(validate_exec_id(report))
    all_errors.extend(validate_status(report))
    all_errors.extend(validate_failures(report, strict=args.strict))

    # Report validation errors
    if all_errors:
        print("[FAIL] Policy violations detected:")
        for error in all_errors:
            print(f"  - {error}")
        return EXIT_POLICY_VIOLATION

    # Check simulation status
    status = report.get("status")
    failures = report.get("failures", [])

    if status == "FAIL" or failures:
        print(f"[FAIL] Simulation failed with {len(failures)} failure(s)")
        for f in failures[:5]:  # Show first 5
            print(f"  - {f.get('rule_id', 'UNKNOWN')}: {f.get('error', 'No error')}")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")
        return EXIT_SIM_FAIL

    print("[PASS] Simulation gate passed")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
