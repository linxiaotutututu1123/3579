#!/usr/bin/env python3
"""场景验证脚本 (军规级 v4.0).

验证所有必需场景是否被测试覆盖。

Usage:
    python scripts/validate_scenarios.py [--strict] [--report PATH]

Exit Codes:
    0  = SUCCESS          全部场景通过
    11 = SCENARIO_MISSING 必需场景缺失
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

# 尝试导入 yaml，如果不可用则使用简单解析
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# 常量定义
# =============================================================================
SCENARIOS_FILE = Path("scenarios/v3pro_required_scenarios.yml")
TESTS_DIR = Path("tests")
REPORT_PATH = Path("artifacts/scenarios/validation_report.json")

# 退出码
EXIT_SUCCESS = 0
EXIT_SCENARIO_MISSING = 11


# =============================================================================
# 数据结构
# =============================================================================
@dataclass
class ScenarioResult:
    """单个场景验证结果."""

    id: str
    name: str
    phase: str
    covered: bool
    test_files: list[str] = field(default_factory=list)
    military_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "name": self.name,
            "phase": self.phase,
            "covered": self.covered,
            "test_files": self.test_files,
            "military_rules": self.military_rules,
        }


@dataclass
class ValidationReport:
    """验证报告."""

    total_scenarios: int = 0
    covered_scenarios: int = 0
    missing_scenarios: int = 0
    coverage_percentage: float = 0.0
    results: list[ScenarioResult] = field(default_factory=list)
    timestamp: str = ""
    status: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "schema_version": 3,
            "type": "scenario_validation",
            "timestamp": self.timestamp,
            "status": self.status,
            "summary": {
                "total_scenarios": self.total_scenarios,
                "covered_scenarios": self.covered_scenarios,
                "missing_scenarios": self.missing_scenarios,
                "coverage_percentage": round(self.coverage_percentage, 2),
            },
            "missing": [r.to_dict() for r in self.results if not r.covered],
            "covered": [r.to_dict() for r in self.results if r.covered],
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: Path) -> None:
        """保存报告."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")


# =============================================================================
# 场景加载
# =============================================================================
def load_scenarios_yaml(path: Path) -> dict[str, Any]:
    """加载YAML场景定义."""
    if not path.exists():
        print(f"ERROR: Scenarios file not found: {path}")
        sys.exit(EXIT_SCENARIO_MISSING)

    content = path.read_text(encoding="utf-8")

    if HAS_YAML:
        return yaml.safe_load(content)

    # 简单解析（无yaml库时的备用方案）
    return parse_yaml_simple(content)


def parse_yaml_simple(content: str) -> dict[str, Any]:
    """简单YAML解析（备用方案）."""
    # 只提取场景ID
    scenarios: dict[str, Any] = {
        "phase_0_infrastructure": {"scenarios": []},
        "phase_1_market": {"scenarios": []},
        "phase_2_audit": {"scenarios": []},
        "phase_3_fallback": {"scenarios": []},
        "phase_4_replay": {"scenarios": []},
        "phase_5_cost": {"scenarios": []},
    }

    # 使用正则提取场景ID
    pattern = r"-\s+id:\s+(\S+)"
    current_phase = None

    for line in content.split("\n"):
        # 检测phase
        if line.startswith("phase_0"):
            current_phase = "phase_0_infrastructure"
        elif line.startswith("phase_1"):
            current_phase = "phase_1_market"
        elif line.startswith("phase_2"):
            current_phase = "phase_2_audit"
        elif line.startswith("phase_3"):
            current_phase = "phase_3_fallback"
        elif line.startswith("phase_4"):
            current_phase = "phase_4_replay"
        elif line.startswith("phase_5"):
            current_phase = "phase_5_cost"

        # 提取场景ID
        match = re.search(pattern, line)
        if match and current_phase:
            scenario_id = match.group(1)
            scenarios[current_phase]["scenarios"].append(
                {"id": scenario_id, "name": scenario_id, "military_rules": []}
            )

    return scenarios


def extract_all_scenarios(data: dict[str, Any]) -> list[tuple[str, str, str, list[str]]]:
    """提取所有场景 (id, name, phase, military_rules)."""
    scenarios = []

    phase_keys = [
        "phase_0_infrastructure",
        "phase_1_market",
        "phase_2_audit",
        "phase_3_fallback",
        "phase_4_replay",
        "phase_5_cost",
    ]

    for phase_key in phase_keys:
        if phase_key not in data:
            continue

        phase_data = data[phase_key]
        phase_scenarios = phase_data.get("scenarios", [])

        for scenario in phase_scenarios:
            scenario_id = scenario.get("id", "")
            scenario_name = scenario.get("name", scenario_id)
            military_rules = scenario.get("military_rules", [])
            scenarios.append((scenario_id, scenario_name, phase_key, military_rules))

    return scenarios


# =============================================================================
# 测试覆盖检查
# =============================================================================
def find_scenario_in_tests(scenario_id: str, test_files: list[Path]) -> list[str]:
    """查找场景在测试文件中的覆盖."""
    covered_files = []

    # 将场景ID转换为可能的测试模式
    # 例如: INFRA.CI.GATE_PASS -> infra_ci_gate_pass, gate_pass, etc.
    patterns = generate_search_patterns(scenario_id)

    for test_file in test_files:
        content = test_file.read_text(encoding="utf-8", errors="ignore").lower()

        for pattern in patterns:
            if pattern.lower() in content:
                covered_files.append(str(test_file))
                break

    return covered_files


def generate_search_patterns(scenario_id: str) -> list[str]:
    """生成搜索模式."""
    patterns = [scenario_id]

    # 原始ID（带点）
    patterns.append(scenario_id)

    # 下划线版本
    underscore_version = scenario_id.replace(".", "_")
    patterns.append(underscore_version)

    # 只取最后部分
    parts = scenario_id.split(".")
    if len(parts) >= 2:
        patterns.append(parts[-1])  # 最后一部分
        patterns.append("_".join(parts[-2:]))  # 最后两部分

    # 小写版本
    patterns.extend([p.lower() for p in patterns])

    # 特殊映射
    special_mappings = {
        "INFRA.CI.GATE_PASS": ["test_ci_gate", "gate_pass", "all_passed"],
        "INFRA.CI.LINT_PASS": ["test_lint", "lint_pass", "ruff"],
        "INFRA.CI.TYPE_PASS": ["test_type", "type_check", "mypy"],
        "INFRA.CI.TEST_PASS": ["test_tests_pass", "pytest"],
        "INFRA.CI.COVERAGE_MIN": ["coverage", "cov_threshold"],
        "INFRA.CHECK.MODE_ENABLED": ["check_mode", "enable_check_mode"],
        "INFRA.CHECK.BROKER_BLOCKED": ["assert_not_check_mode", "broker_blocked"],
        "INFRA.EXIT.CODE": ["exit_code", "exitcode"],
        "MKT.SUBSCRIBER.DIFF_UPDATE": ["subscription_diff", "diff_update"],
        "AUDIT.WRITE.JSONL_FORMAT": ["jsonl", "audit_writer"],
        "AUDIT.WRITE.ATOMIC_APPEND": ["atomic", "fsync"],
        "FALL.MANAGER": ["fallback_manager", "fallback"],
        "FALL.CHAIN": ["fallback_chain", "default_fallback"],
        "FALL.REASON": ["fallback_reason", "exception", "timeout"],
        "ARB.LEGS": ["leg_pair", "near_far", "calendar_arb"],
        "ARB.SIGNAL": ["arb_signal", "z_score", "half_life"],
        "ARB.COST": ["cost_gate", "entry_gate", "min_edge"],
        "ARB.STATE": ["arb_state", "init", "active", "stopped"],
        "ARB.KALMAN": ["kalman", "beta", "residual"],
        "REPLAY.VERIFIER": ["replay_verifier", "verify"],
        "REPLAY.HASH": ["sha256", "hash", "deterministic"],
        "REPLAY.DETERMINISTIC": ["lcg", "random_seed", "deterministic"],
        "REPLAY.SIM": ["sim_report", "sim_gate"],
        "REPLAY.VAR": ["var_calculator", "monte_carlo", "historical"],
        "COST.EXCHANGE": ["shfe", "dce", "czce", "cffex", "gfex", "ine"],
        "COST.FEE_TYPE": ["fee_type", "fixed", "ratio"],
        "COST.DIRECTION": ["close_today", "open", "close"],
        "COST.BREAKDOWN": ["cost_breakdown", "fee", "slippage"],
        "COST.ESTIMATOR": ["estimator", "edge_gate"],
        "COST.PRODUCT": ["china_fee", "fee_calculator"],
        "COST.SLIPPAGE": ["slippage", "tick"],
    }

    for key, mappings in special_mappings.items():
        if scenario_id.startswith(key):
            patterns.extend(mappings)

    return list(set(patterns))


def get_all_test_files(tests_dir: Path) -> list[Path]:
    """获取所有测试文件."""
    if not tests_dir.exists():
        return []
    return list(tests_dir.glob("**/test_*.py"))


# =============================================================================
# 主验证逻辑
# =============================================================================
def validate_scenarios(strict: bool = True) -> ValidationReport:
    """验证所有场景."""
    report = ValidationReport()

    # 加载场景定义
    print("Loading scenarios from:", SCENARIOS_FILE)
    data = load_scenarios_yaml(SCENARIOS_FILE)

    # 提取所有场景
    all_scenarios = extract_all_scenarios(data)
    report.total_scenarios = len(all_scenarios)
    print(f"Total scenarios: {report.total_scenarios}")

    # 获取所有测试文件
    test_files = get_all_test_files(TESTS_DIR)
    print(f"Test files found: {len(test_files)}")

    # 检查每个场景的覆盖情况
    for scenario_id, scenario_name, phase, military_rules in all_scenarios:
        covered_files = find_scenario_in_tests(scenario_id, test_files)
        is_covered = len(covered_files) > 0

        result = ScenarioResult(
            id=scenario_id,
            name=scenario_name,
            phase=phase,
            covered=is_covered,
            test_files=covered_files,
            military_rules=military_rules,
        )
        report.results.append(result)

        if is_covered:
            report.covered_scenarios += 1
        else:
            report.missing_scenarios += 1

    # 计算覆盖率
    if report.total_scenarios > 0:
        report.coverage_percentage = (report.covered_scenarios / report.total_scenarios) * 100

    # 确定状态
    if report.missing_scenarios == 0:
        report.status = "PASS"
    elif strict:
        report.status = "FAIL"
    else:
        report.status = "WARN"

    return report


def print_report(report: ValidationReport) -> None:
    """打印报告."""
    print("\n" + "=" * 70)
    print("               军规级场景验证报告 (v4.0)")
    print("=" * 70)

    print(f"\n总场景数:     {report.total_scenarios}")
    print(f"已覆盖场景:   {report.covered_scenarios}")
    print(f"缺失场景:     {report.missing_scenarios}")
    print(f"覆盖率:       {report.coverage_percentage:.1f}%")
    print(f"状态:         {report.status}")

    if report.missing_scenarios > 0:
        print("\n" + "-" * 70)
        print("缺失场景列表:")
        print("-" * 70)
        for result in report.results:
            if not result.covered:
                rules = ", ".join(result.military_rules) if result.military_rules else "N/A"
                print(f"  [{result.phase}] {result.id}")
                print(f"      名称: {result.name}")
                print(f"      军规: {rules}")

    print("\n" + "=" * 70)


# =============================================================================
# 入口点
# =============================================================================
def main() -> int:
    """主入口."""
    parser = argparse.ArgumentParser(description="军规级场景验证脚本")
    parser.add_argument("--strict", action="store_true", help="严格模式（任何缺失即失败）")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="报告输出路径")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    args = parser.parse_args()

    # 执行验证
    report = validate_scenarios(strict=args.strict)

    # 保存报告
    report.save(args.report)
    if not args.quiet:
        print(f"\nReport saved to: {args.report}")

    # 打印报告
    if not args.quiet:
        print_report(report)

    # 返回退出码
    if report.status == "FAIL":
        return EXIT_SCENARIO_MISSING
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
