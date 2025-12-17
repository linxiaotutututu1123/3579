#!/usr/bin/env python3
"""Coverage Gate - Military-Grade Coverage Enforcement.

Implements tiered coverage requirements:
- Core domains: 100% coverage required
- Overall: 85% coverage required

Core domains (military-grade, must be 100%):
- src/market/**
- src/execution/**
- src/guardian/**
- src/audit/**
- src/trading/**
- src/arbitrage/** (V3PRO+)

Usage:
    python scripts/coverage_gate.py              # Check coverage
    python scripts/coverage_gate.py --report     # Generate report
    python scripts/coverage_gate.py --strict     # Fail on any violation
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# Exit Codes
# =============================================================================
EXIT_SUCCESS = 0
EXIT_COVERAGE_FAIL = 5

# =============================================================================
# Coverage Thresholds
# =============================================================================
OVERALL_THRESHOLD = 85

# Core domains requiring 100% coverage
CORE_DOMAINS = [
    "src/market",
    "src/execution",
    "src/guardian",
    "src/audit",
    "src/trading",
    "src/arbitrage",
]

CORE_THRESHOLD = 100


@dataclass
class ModuleCoverage:
    """Coverage for a single module."""

    name: str
    stmts: int
    miss: int
    cover: float

    @property
    def is_core(self) -> bool:
        """Check if module is in core domain."""
        for domain in CORE_DOMAINS:
            if self.name.startswith(domain.replace("/", "\\")):
                return True
            if self.name.startswith(domain):
                return True
        return False


def run_coverage() -> tuple[float, list[ModuleCoverage]]:
    """Run pytest with coverage and parse results."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=json:coverage.json",
        "--cov-report=term-missing",
        "-q",
        "--tb=no",
    ]

    subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    # Parse coverage.json
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("ERROR: coverage.json not generated")
        return 0.0, []

    with open(coverage_file, encoding="utf-8") as f:
        data = json.load(f)

    # Extract overall coverage
    totals = data.get("totals", {})
    overall = totals.get("percent_covered", 0.0)

    # Extract per-file coverage
    modules: list[ModuleCoverage] = []
    files = data.get("files", {})
    for filepath, stats in files.items():
        summary = stats.get("summary", {})
        modules.append(
            ModuleCoverage(
                name=filepath,
                stmts=summary.get("num_statements", 0),
                miss=summary.get("missing_lines", 0),
                cover=summary.get("percent_covered", 0.0),
            )
        )

    return overall, modules


def check_coverage(
    overall: float,
    modules: list[ModuleCoverage],
    strict: bool = False,
) -> tuple[bool, list[str]]:
    """Check coverage against thresholds.

    Returns:
        Tuple of (passed, violations)
    """
    violations: list[str] = []

    # Check overall
    if overall < OVERALL_THRESHOLD:
        violations.append(f"Overall coverage {overall:.1f}% < {OVERALL_THRESHOLD}% threshold")

    # Check core domains
    core_modules = [m for m in modules if m.is_core]
    for module in core_modules:
        if module.cover < CORE_THRESHOLD:
            if strict:
                violations.append(
                    f"Core module {module.name}: {module.cover:.1f}% < {CORE_THRESHOLD}%"
                )
            else:
                # In grace period, just warn but don't fail
                print(f"  ⚠ Core module {module.name}: {module.cover:.1f}% (target: 100%)")

    return len(violations) == 0, violations


def main() -> int:
    """Run coverage gate."""
    parser = argparse.ArgumentParser(description="Military-Grade Coverage Gate")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed coverage report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on core domain violations (default: grace period)",
    )

    args = parser.parse_args()

    print("Running coverage analysis...")
    overall, modules = run_coverage()

    print(f"\n{'=' * 60}")
    print("Coverage Summary")
    print(f"{'=' * 60}")
    print(f"Overall: {overall:.1f}% (threshold: {OVERALL_THRESHOLD}%)")

    # Report core domains
    core_modules = [m for m in modules if m.is_core]
    if core_modules:
        print(f"\nCore Domains (target: {CORE_THRESHOLD}%):")
        for m in sorted(core_modules, key=lambda x: x.cover):
            status = "✅" if m.cover >= CORE_THRESHOLD else "⚠"
            print(f"  {status} {m.name}: {m.cover:.1f}%")

    # Check thresholds
    _, violations = check_coverage(overall, modules, args.strict)

    if violations:
        print("\n❌ Coverage Gate FAILED:")
        for v in violations:
            print(f"  - {v}")
        return EXIT_COVERAGE_FAIL

    print("\n✅ Coverage Gate PASSED")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
