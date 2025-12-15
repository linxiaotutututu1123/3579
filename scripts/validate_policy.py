#!/usr/bin/env python3
"""Policy Validator (Military-Grade v3.0).

跨平台策略验证器，检测以下违规：
1. 报告文件缺失
2. JSON schema 校验失败
3. 命令白名单违规
4. 产物路径不符合约定
5. check_mode 未启用
6. context_manifest_sha 缺失

任何违规 → exit 12 (POLICY_VIOLATION)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Try to import jsonschema, but don't fail if not available
try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = logging.getLogger(__name__)

# =============================================================================
# 退出码
# =============================================================================
EXIT_SUCCESS = 0
EXIT_POLICY_VIOLATION = 12

# =============================================================================
# 固定路径约定 (D.1)
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
# 命令白名单
# =============================================================================
COMMAND_WHITELIST = [
    r"^\.\s*[\\/]?scripts[\\/]make\.ps1\s+",
    r"^make\s+",
    r"^git\s+(status|diff|log|branch|rev-parse)",
    r"^(cat|Get-Content|type)\s+",
    r"^python\s+-m\s+src\.trading\.(replay|sim)\s+",
]

COMMAND_BLACKLIST = [
    r"^pytest\b",
    r"^ruff\b",
    r"^mypy\b",
    r"^python\s+-m\s+pytest\b",
    r"^python\s+-m\s+ruff\b",
    r"^python\s+-m\s+mypy\b",
]

# =============================================================================
# 策略违规数据结构
# =============================================================================


@dataclass
class PolicyViolation:
    """单条策略违规。"""

    code: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR | WARNING


@dataclass
class PolicyReport:
    """策略检查报告。"""

    violations: list[PolicyViolation] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    checked_files: list[str] = field(default_factory=list)
    checked_commands: list[str] = field(default_factory=list)

    def add_violation(
        self,
        code: str,
        message: str,
        evidence: dict[str, Any] | None = None,
        severity: str = "ERROR",
    ) -> None:
        """添加违规记录。"""
        self.violations.append(
            PolicyViolation(
                code=code,
                message=message,
                evidence=evidence or {},
                severity=severity,
            )
        )

    @property
    def has_errors(self) -> bool:
        """是否有 ERROR 级别违规。"""
        return any(v.severity == "ERROR" for v in self.violations)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "timestamp": self.timestamp,
            "has_errors": self.has_errors,
            "violation_count": len(self.violations),
            "violations": [
                {
                    "code": v.code,
                    "message": v.message,
                    "evidence": v.evidence,
                    "severity": v.severity,
                }
                for v in self.violations
            ],
            "checked_files": self.checked_files,
            "checked_commands": self.checked_commands,
        }


# =============================================================================
# Schema 加载与校验
# =============================================================================


def load_schema(schema_path: Path) -> dict[str, Any] | None:
    """加载 JSON schema。"""
    if not schema_path.exists():
        logger.warning("Schema file not found: %s", schema_path)
        return None
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate_json_schema(
    data: dict[str, Any],
    schema: dict[str, Any],
    report: PolicyReport,
    report_type: str,
) -> bool:
    """校验 JSON 是否符合 schema。"""
    if not HAS_JSONSCHEMA:
        # 手动校验必填字段
        required = schema.get("required", [])
        missing = [f for f in required if f not in data]
        if missing:
            report.add_violation(
                code="SCHEMA.MISSING_FIELDS",
                message=f"Missing required fields in {report_type}: {missing}",
                evidence={"missing": missing, "found": list(data.keys())},
            )
            return False
        return True

    try:
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        report.add_violation(
            code="SCHEMA.VALIDATION_FAILED",
            message=f"Schema validation failed for {report_type}: {e.message}",
            evidence={
                "path": list(e.absolute_path),
                "schema_path": list(e.absolute_schema_path),
                "validator": e.validator,
                "validator_value": str(e.validator_value)[:100],
            },
        )
        return False


# =============================================================================
# 报告校验
# =============================================================================


def validate_report_file(
    report_path: Path,
    schema_path: Path,
    report_type: str,
    policy_report: PolicyReport,
) -> bool:
    """校验报告文件。"""
    policy_report.checked_files.append(str(report_path))

    # 1. 文件存在性
    if not report_path.exists():
        policy_report.add_violation(
            code="REPORT.FILE_MISSING",
            message=f"Report file not found: {report_path}",
            evidence={"expected_path": str(report_path)},
        )
        return False

    # 2. JSON 解析
    try:
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        policy_report.add_violation(
            code="REPORT.INVALID_JSON",
            message=f"Invalid JSON in report: {e}",
            evidence={"path": str(report_path), "error": str(e)},
        )
        return False

    # 3. schema_version 检查
    schema_version = data.get("schema_version")
    if schema_version is None:
        policy_report.add_violation(
            code="SCHEMA.VERSION_MISSING",
            message="Missing schema_version in report",
            evidence={"path": str(report_path)},
        )
        return False
    if not isinstance(schema_version, int) or schema_version < 3:
        policy_report.add_violation(
            code="SCHEMA.VERSION_OUTDATED",
            message=f"schema_version must be >= 3, got {schema_version}",
            evidence={"current": schema_version, "required": 3},
        )
        return False

    # 4. check_mode 检查 (sim/replay 必须为 true)
    if report_type in ("replay", "sim"):
        check_mode = data.get("check_mode")
        if check_mode is not True:
            policy_report.add_violation(
                code="POLICY.CHECK_MODE_DISABLED",
                message=f"check_mode must be true for {report_type}",
                evidence={"check_mode": check_mode},
            )
            return False

    # 5. Schema 校验
    schema = load_schema(schema_path)
    if schema:
        validate_json_schema(data, schema, policy_report, report_type)

    # 6. run_id / exec_id 检查
    if "run_id" not in data:
        policy_report.add_violation(
            code="REPORT.MISSING_RUN_ID",
            message="Missing run_id in report",
            evidence={"path": str(report_path)},
        )
    if "exec_id" not in data:
        policy_report.add_violation(
            code="REPORT.MISSING_EXEC_ID",
            message="Missing exec_id in report",
            evidence={"path": str(report_path)},
        )

    # 7. 失败结构校验 (sim/replay)
    if report_type in ("replay", "sim") and "failures" in data:
        required_fields = {"scenario", "rule_id", "component", "event_id", "expected", "actual", "error", "evidence"}
        for i, failure in enumerate(data["failures"]):
            if not isinstance(failure, dict):
                continue
            missing = required_fields - set(failure.keys())
            if missing:
                policy_report.add_violation(
                    code="FAILURE.MISSING_FIELDS",
                    message=f"Failure[{i}] missing required fields: {missing}",
                    evidence={"index": i, "missing": list(missing), "scenario": failure.get("scenario", "?")},
                )

    return not policy_report.has_errors


# =============================================================================
# 命令白名单校验
# =============================================================================


def validate_command(command: str, policy_report: PolicyReport) -> bool:
    """校验命令是否在白名单内。"""
    policy_report.checked_commands.append(command)

    # 检查黑名单
    for pattern in COMMAND_BLACKLIST:
        if re.search(pattern, command, re.IGNORECASE):
            policy_report.add_violation(
                code="COMMAND.BLACKLISTED",
                message=f"Command matches blacklist: {command}",
                evidence={"command": command, "pattern": pattern},
            )
            return False

    # 检查白名单
    for pattern in COMMAND_WHITELIST:
        if re.search(pattern, command, re.IGNORECASE):
            return True

    # 不在白名单也不在黑名单 → 警告（不阻塞）
    policy_report.add_violation(
        code="COMMAND.NOT_WHITELISTED",
        message=f"Command not in whitelist: {command}",
        evidence={"command": command},
        severity="WARNING",
    )
    return True


def validate_commands_log(log_path: Path, policy_report: PolicyReport) -> bool:
    """校验 commands.log 中的所有命令。"""
    if not log_path.exists():
        # commands.log 可能不存在（首次运行）
        return True

    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                validate_command(line, policy_report)

    return not policy_report.has_errors


# =============================================================================
# 产物路径校验
# =============================================================================


def validate_artifact_paths(policy_report: PolicyReport) -> bool:
    """校验产物路径是否符合约定。"""
    # 检查 CI 报告是否在正确路径
    ci_report = FIXED_PATHS["ci_report"]
    if ci_report.exists():
        with open(ci_report, encoding="utf-8") as f:
            data = json.load(f)
        artifacts = data.get("artifacts", {})
        if artifacts.get("report_path") != str(ci_report):
            policy_report.add_violation(
                code="ARTIFACT.PATH_MISMATCH",
                message=f"CI report path mismatch: expected {ci_report}",
                evidence={"expected": str(ci_report), "actual": artifacts.get("report_path")},
            )
            return False

    # 检查 sim 报告
    sim_report = FIXED_PATHS["sim_report"]
    if sim_report.exists():
        with open(sim_report, encoding="utf-8") as f:
            data = json.load(f)
        artifacts = data.get("artifacts", {})
        if artifacts.get("report_path") != str(sim_report):
            policy_report.add_violation(
                code="ARTIFACT.PATH_MISMATCH",
                message=f"Sim report path mismatch: expected {sim_report}",
                evidence={"expected": str(sim_report), "actual": artifacts.get("report_path")},
            )
            return False

    return True


# =============================================================================
# Context manifest 校验
# =============================================================================


def compute_context_sha(context_path: Path) -> str | None:
    """计算 context.md 的 SHA256。"""
    if not context_path.exists():
        return None
    with open(context_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def validate_context_manifest(policy_report: PolicyReport) -> bool:
    """校验 context_manifest_sha 是否存在且匹配。"""
    context_path = FIXED_PATHS["context"]
    if not context_path.exists():
        # context.md 不存在不是强制错误
        return True

    expected_sha = compute_context_sha(context_path)

    # 检查 round_summary 中是否有 context_manifest_sha
    round_summary = FIXED_PATHS["round_summary"]
    if round_summary.exists():
        with open(round_summary, encoding="utf-8") as f:
            data = json.load(f)
        actual_sha = data.get("context_manifest_sha")
        if actual_sha is None:
            policy_report.add_violation(
                code="CONTEXT.SHA_MISSING",
                message="context_manifest_sha missing in round_summary",
                evidence={"round_summary": str(round_summary)},
            )
            return False
        if actual_sha != expected_sha:
            policy_report.add_violation(
                code="CONTEXT.SHA_MISMATCH",
                message="context_manifest_sha mismatch",
                evidence={"expected": expected_sha, "actual": actual_sha},
            )
            return False

    return True


# =============================================================================
# 主入口
# =============================================================================


def run_all_validations(check_type: str = "all") -> PolicyReport:
    """运行所有策略验证。"""
    policy_report = PolicyReport()
    schema_dir = Path("scripts/json_schema")

    # CI 报告校验
    if check_type in ("all", "ci"):
        ci_schema = schema_dir / "ci_report.schema.json"
        validate_report_file(
            FIXED_PATHS["ci_report"],
            ci_schema,
            "ci",
            policy_report,
        )

    # Sim/Replay 报告校验
    if check_type in ("all", "sim", "replay"):
        sim_schema = schema_dir / "sim_report.schema.json"
        if FIXED_PATHS["sim_report"].exists():
            validate_report_file(
                FIXED_PATHS["sim_report"],
                sim_schema,
                "sim",
                policy_report,
            )

    # 命令日志校验
    if check_type in ("all", "commands"):
        validate_commands_log(FIXED_PATHS["commands_log"], policy_report)

    # 产物路径校验
    if check_type in ("all", "artifacts"):
        validate_artifact_paths(policy_report)

    # Context manifest 校验
    if check_type in ("all", "context"):
        validate_context_manifest(policy_report)

    return policy_report


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(description="Policy Validator (Military-Grade)")
    parser.add_argument(
        "--check",
        choices=["all", "ci", "sim", "replay", "commands", "artifacts", "context"],
        default="all",
        help="检查类型",
    )
    parser.add_argument("--output", type=Path, help="输出报告路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    policy_report = run_all_validations(args.check)

    # 输出报告
    report_dict = policy_report.to_dict()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        logger.info("Policy report written to: %s", args.output)

    # 打印违规
    if policy_report.violations:
        print("\n=== Policy Violations ===")
        for v in policy_report.violations:
            severity_marker = "❌" if v.severity == "ERROR" else "⚠️"
            print(f"{severity_marker} [{v.code}] {v.message}")
            if v.evidence:
                print(f"   Evidence: {json.dumps(v.evidence, ensure_ascii=False)}")
        print()

    if policy_report.has_errors:
        print(f"❌ POLICY_VIOLATION: {len([v for v in policy_report.violations if v.severity == 'ERROR'])} errors")
        return EXIT_POLICY_VIOLATION
    else:
        print("✅ Policy check passed")
        return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
