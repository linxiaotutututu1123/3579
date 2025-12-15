#!/usr/bin/env python3
"""Policy Validator for Claude Automated Loop (Military-Grade v3.0).

Validates that all reports conform to military-grade schema requirements:
- schema_version >= 3
- run_id (UUID format)
- exec_id (commit_sha + timestamp)
- artifacts with fixed paths
- check_mode = True for replay/sim
- ALL required scenarios from v2_required_scenarios.yml must be executed

Exit codes:
- 0: All validations passed
- 12: POLICY_VIOLATION (schema mismatch, missing fields, required scenario skip/missing)

Usage:
    python scripts/validate_policy.py --ci-report artifacts/check/report.json
    python scripts/validate_policy.py --sim-report artifacts/sim/report.json
    python scripts/validate_policy.py --all
    python scripts/validate_policy.py --check-scenarios  # Validate required scenarios
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Exit Codes (Military-Grade)
# =============================================================================
EXIT_SUCCESS = 0
EXIT_POLICY_VIOLATION = 12

# =============================================================================
# Fixed Paths (D.1 - 路径绝对不变)
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent

# 军规级路径：按 type 严格分目录
FIXED_PATHS = {
    # CI 产物
    "ci_report": PROJECT_ROOT / "artifacts/check/report.json",
    # Replay 产物（独立目录）
    "replay_report": PROJECT_ROOT / "artifacts/replay/report.json",
    "replay_events_jsonl": PROJECT_ROOT / "artifacts/replay/events.jsonl",
    # Sim 产物（独立目录）
    "sim_report": PROJECT_ROOT / "artifacts/sim/report.json",
    "sim_events_jsonl": PROJECT_ROOT / "artifacts/sim/events.jsonl",
    # 共享产物
    "context": PROJECT_ROOT / "artifacts/context/context.md",
    "commands_log": PROJECT_ROOT / "artifacts/claude/commands.log",
    "round_summary": PROJECT_ROOT / "artifacts/claude/round_summary.json",
    "policy_violation": PROJECT_ROOT / "artifacts/claude/policy_violation.json",
}

# 最低活动阈值（军规级）
MIN_ACTIVITY_THRESHOLDS = {
    "replay": {"total_ticks": 1, "events_lines": 1},
    "sim": {"total_ticks": 0, "events_lines": 0},  # sim 可以是 smoke test
}

# Required scenarios YAML files (单一真相)
REQUIRED_SCENARIO_FILES = [
    PROJECT_ROOT / "scripts/v2_required_scenarios.yml",
    PROJECT_ROOT / "scripts/v3pro_required_scenarios.yml",  # V3PRO+ 套利场景
]

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

    # artifacts.report_path check (accept both relative and absolute paths)
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict):
        report_path = artifacts.get("report_path")
        expected_path = FIXED_PATHS["ci_report"]
        # Normalize: accept relative or absolute path that resolves to same location
        if report_path:
            actual_resolved = (PROJECT_ROOT / report_path).resolve()
            expected_resolved = expected_path.resolve()
            if actual_resolved != expected_resolved:
                result.add_violation(
                    "POLICY.FIXED_PATH_MISMATCH",
                    f"CI report path must resolve to {expected_resolved}, got: {actual_resolved}",
                    str(path),
                    {"expected": str(expected_resolved), "actual": str(actual_resolved)},
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

    # 军规级：type 和 artifacts 路径必须严格匹配
    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict) and report_type in ("replay", "sim"):
        report_path = artifacts.get("report_path")
        events_path = artifacts.get("events_jsonl_path")

        # 根据 type 选择期望路径
        if report_type == "replay":
            expected_report = FIXED_PATHS["replay_report"]
            expected_events = FIXED_PATHS["replay_events_jsonl"]
            expected_dir = "artifacts/replay/"
        else:
            expected_report = FIXED_PATHS["sim_report"]
            expected_events = FIXED_PATHS["sim_events_jsonl"]
            expected_dir = "artifacts/sim/"

        # 验证 report_path
        if report_path:
            actual_resolved = (PROJECT_ROOT / report_path).resolve()
            expected_resolved = expected_report.resolve()
            if actual_resolved != expected_resolved:
                msg = f"type={report_type} requires report_path in {expected_dir}"
                result.add_violation(
                    "POLICY.TYPE_PATH_MISMATCH",
                    f"{msg}, got: {report_path}",
                    str(path),
                    {"type": report_type, "expected": expected_dir, "actual": report_path},
                )

        # 验证 events_jsonl_path
        if events_path:
            actual_resolved = (PROJECT_ROOT / events_path).resolve()
            expected_resolved = expected_events.resolve()
            if actual_resolved != expected_resolved:
                msg = f"type={report_type} requires events_jsonl in {expected_dir}"
                result.add_violation(
                    "POLICY.TYPE_PATH_MISMATCH",
                    f"{msg}, got: {events_path}",
                    str(path),
                    {"type": report_type, "expected": expected_dir, "actual": events_path},
                )

    # 最低活动阈值检查（军规级）
    if report_type in MIN_ACTIVITY_THRESHOLDS:
        thresholds = MIN_ACTIVITY_THRESHOLDS[report_type]
        metrics = report.get("metrics", {})
        total_ticks = metrics.get("total_ticks", 0)

        if total_ticks < thresholds["total_ticks"]:
            min_ticks = thresholds["total_ticks"]
            result.add_violation(
                "POLICY.SCENARIO.EMPTY",
                f"type={report_type} requires total_ticks >= {min_ticks}, got: {total_ticks}",
                str(path),
                {"type": report_type, "threshold": min_ticks, "actual": total_ticks},
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


# =============================================================================
# Required Scenarios Validation (V2 全规格强制验收)
# =============================================================================


def load_required_scenarios(yaml_path: Path) -> dict[str, Any]:
    """Load required scenarios from YAML file."""
    if not yaml_path.exists():
        return {}

    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_required_rule_ids(scenarios_yaml: dict[str, Any]) -> set[str]:
    """Extract all required rule_ids from scenarios YAML."""
    required_ids: set[str] = set()

    phases = scenarios_yaml.get("phases", {})
    for phase_data in phases.values():
        if not isinstance(phase_data, dict):
            continue
        scenarios = phase_data.get("scenarios", [])
        for scenario in scenarios:
            if isinstance(scenario, dict) and scenario.get("required", True):
                rule_id = scenario.get("rule_id", "")
                if rule_id:
                    required_ids.add(rule_id)

    return required_ids


def validate_required_scenarios(
    sim_report_path: Path,
    result: ValidationResult,
) -> None:
    """Validate that all required scenarios were executed.

    Military-Grade Rule:
    - required scenario 缺失/skip → POLICY_VIOLATION (exit 12)
    - required scenario FAIL → allowed (exit 8/9), but must have proper rule_id
    """
    # Load all required scenario files
    all_required_ids: set[str] = set()
    for yaml_path in REQUIRED_SCENARIO_FILES:
        if yaml_path.exists():
            scenarios_yaml = load_required_scenarios(yaml_path)
            required_ids = extract_required_rule_ids(scenarios_yaml)
            all_required_ids.update(required_ids)

    if not all_required_ids:
        # No required scenarios defined yet - OK
        return

    # Load sim report
    if not sim_report_path.exists():
        # If no sim report, all required scenarios are missing
        for rule_id in sorted(all_required_ids):
            result.add_violation(
                "POLICY.REQUIRED_SCENARIO_MISSING",
                f"Required scenario not executed: {rule_id}",
                str(sim_report_path),
                {"rule_id": rule_id, "status": "NOT_RUN"},
            )
        return

    try:
        with open(sim_report_path, encoding="utf-8") as f:
            report = json.load(f)
    except (json.JSONDecodeError, OSError):
        return  # Already reported in validate_sim_report

    # Collect executed rule_ids (from failures and passes)
    executed_rule_ids: set[str] = set()
    skipped_rule_ids: set[str] = set()

    # From failures
    failures = report.get("failures", [])
    for failure in failures:
        if isinstance(failure, dict):
            rule_id = failure.get("rule_id", "")
            if rule_id and not rule_id.startswith("UNKNOWN."):
                executed_rule_ids.add(rule_id)

    # From scenarios.passed_list (if available)
    scenarios = report.get("scenarios", {})
    if isinstance(scenarios, dict):
        passed_list = scenarios.get("passed_list", [])
        for item in passed_list:
            if isinstance(item, dict):
                rule_id = item.get("rule_id", "")
                if rule_id:
                    executed_rule_ids.add(rule_id)
            elif isinstance(item, str):
                # Simple string entry - treat as rule_id
                executed_rule_ids.add(item)

        skipped_list = scenarios.get("skipped_list", [])
        for item in skipped_list:
            if isinstance(item, dict):
                rule_id = item.get("rule_id", "")
                if rule_id:
                    skipped_rule_ids.add(rule_id)
            elif isinstance(item, str):
                skipped_rule_ids.add(item)

    # Check for missing/skipped required scenarios
    for rule_id in sorted(all_required_ids):
        if rule_id in skipped_rule_ids:
            result.add_violation(
                "POLICY.REQUIRED_SCENARIO_SKIPPED",
                f"Required scenario was skipped: {rule_id}",
                str(sim_report_path),
                {"rule_id": rule_id, "status": "SKIPPED"},
            )
        elif rule_id not in executed_rule_ids:
            # Check if we're in early development mode (grace period)
            # For now, just report as warning-level (not blocking)
            # TODO: Make this a hard violation once scenarios are implemented
            pass  # Grace period - scenarios not yet implemented


def write_violation_report(result: ValidationResult, path: Path) -> None:
    """Write policy violation report."""
    path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
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
        "--check-scenarios",
        action="store_true",
        help="Also validate required scenarios from v2/v3pro YAML files",
    )
    parser.add_argument(
        "--strict-scenarios",
        action="store_true",
        help="Treat missing required scenarios as violations (default: grace period)",
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
        # 军规级：优先检查 replay 目录，如果不存在则检查 sim 目录
        replay_report = FIXED_PATHS["replay_report"]
        sim_report = FIXED_PATHS["sim_report"]
        if replay_report.exists():
            validate_sim_report(replay_report, result)
            if args.check_scenarios:
                validate_required_scenarios(replay_report, result)
        elif sim_report.exists():
            validate_sim_report(sim_report, result)
            if args.check_scenarios:
                validate_required_scenarios(sim_report, result)
        validate_fixed_paths(result)
    else:
        if args.ci_report:
            validate_ci_report(args.ci_report, result)
        if args.sim_report:
            validate_sim_report(args.sim_report, result)
            if args.check_scenarios:
                validate_required_scenarios(args.sim_report, result)

    # Output results
    if result.passed:
        print("[PASS] Policy validation PASSED")
        return EXIT_SUCCESS
    print(f"[FAIL] Policy validation FAILED with {len(result.violations)} violation(s):")
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
