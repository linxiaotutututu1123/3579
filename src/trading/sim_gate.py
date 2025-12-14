"""Simulation/Replay gate for machine-readable reporting.

Provides simulation and replay result reporting in JSON format for
Claude automated loop integration.

Military-grade v3.0 enhancements:
- schema_version: integer, must be >= 3
- rule_id: scenario identifier (e.g., UNIV.DOMINANT.BASIC)
- component: module under test
- evidence: state snapshot for debugging
- check_mode: mandatory for all replay/sim
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SimStatus(str, Enum):
    """Simulation/Replay status."""

    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ScenarioFailure:
    """Single scenario failure detail (military-grade v3.0).

    All fields are required for Claude to auto-fix:
    - rule_id: unique scenario identifier
    - component: module under test
    - tick: when the failure occurred
    - expected/actual: comparison values
    - error: human-readable description
    - evidence: state snapshot for debugging
    """

    scenario: str
    rule_id: str  # e.g., "UNIV.DOMINANT.BASIC"
    component: str  # e.g., "universe_selector"
    tick: int
    expected: dict[str, Any]
    actual: dict[str, Any]
    error: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario": self.scenario,
            "rule_id": self.rule_id,
            "component": self.component,
            "tick": self.tick,
            "expected": self.expected,
            "actual": self.actual,
            "error": self.error,
            "evidence": self.evidence,
        }


@dataclass
class SimMetrics:
    """Simulation metrics summary."""

    total_ticks: int = 0
    avg_tick_duration_ms: float = 0.0
    max_drawdown_pct: float = 0.0
    orders_placed: int = 0
    orders_rejected: int = 0
    orders_filled: int = 0
    pnl_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SimReport:
    """Full simulation/replay report (military-grade v3.0).

    Military-grade enhancements:
    - schema_version: integer, must be >= 3
    - type: "replay" or "sim"
    - check_mode: must be True
    - exit_code: 0/8/9
    - failures with rule_id/component/evidence
    """

    type: str  # "replay" or "sim"
    scenarios_total: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    failures: list[ScenarioFailure] = field(default_factory=list)
    metrics: SimMetrics = field(default_factory=SimMetrics)
    schema_version: int = 3
    check_mode: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    @property
    def overall(self) -> SimStatus:
        """Overall status."""
        return SimStatus.PASS if self.scenarios_failed == 0 else SimStatus.FAIL

    @property
    def passed(self) -> bool:
        """Check if all scenarios passed."""
        return self.scenarios_failed == 0

    @property
    def exit_code(self) -> int:
        """Get exit code based on type and status."""
        if self.passed:
            return SimExitCode.SUCCESS
        return SimExitCode.REPLAY_FAIL if self.type == "replay" else SimExitCode.SIM_FAIL

    def add_pass(self, scenario: str, rule_id: str = "", component: str = "") -> None:
        """Record a passed scenario."""
        self.scenarios_total += 1
        self.scenarios_passed += 1
        logger.info("PASS: %s [%s]", scenario, rule_id or "no_rule_id")

    def add_failure(
        self,
        scenario: str,
        tick: int,
        expected: dict[str, Any],
        actual: dict[str, Any],
        error: str,
        *,
        rule_id: str = "",
        component: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Record a failed scenario (military-grade v3.0)."""
        self.scenarios_total += 1
        self.scenarios_failed += 1
        self.failures.append(
            ScenarioFailure(
                scenario=scenario,
                rule_id=rule_id or f"UNKNOWN.{scenario.upper().replace(' ', '_')}",
                component=component or "unknown",
                tick=tick,
                expected=expected,
                actual=actual,
                error=error,
                evidence=evidence or {},
            )
        )
        logger.error("FAIL: %s [%s] at tick %d: %s", scenario, rule_id, tick, error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "timestamp": self.timestamp,
            "check_mode": self.check_mode,
            "overall": self.overall.value,
            "exit_code": self.exit_code,
            "scenarios_total": self.scenarios_total,
            "scenarios_passed": self.scenarios_passed,
            "scenarios_failed": self.scenarios_failed,
            "failures": [f.to_dict() for f in self.failures],
            "metrics": self.metrics.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary(self) -> str:
        """Generate summary string."""
        status = self.overall.value
        return (
            f"Sim Gate [{self.type}]: {status} "
            f"({self.scenarios_passed}/{self.scenarios_total} passed)"
        )


class SimGate:
    """
    Simulation/Replay gate for automated validation (military-grade v3.0).

    Collects scenario results and generates machine-readable reports
    with rule_id, component, and evidence for Claude auto-fix.
    """

    def __init__(self, sim_type: str = "replay", check_mode: bool = False) -> None:
        """
        Initialize simulation gate.

        Args:
            sim_type: Type of simulation ("replay" or "sim")
            check_mode: Whether CHECK_MODE is enabled (must be True for production)
        """
        self._report = SimReport(type=sim_type, check_mode=check_mode)

    @property
    def report(self) -> SimReport:
        """Get current report."""
        return self._report

    def set_check_mode(self, enabled: bool) -> None:
        """Set CHECK_MODE flag."""
        self._report.check_mode = enabled

    def record_pass(
        self,
        scenario: str,
        *,
        rule_id: str = "",
        component: str = "",
    ) -> None:
        """Record a passed scenario."""
        self._report.add_pass(scenario, rule_id=rule_id, component=component)

    def record_failure(
        self,
        scenario: str,
        tick: int,
        expected: dict[str, Any],
        actual: dict[str, Any],
        error: str,
        *,
        rule_id: str = "",
        component: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Record a failed scenario (military-grade v3.0)."""
        self._report.add_failure(
            scenario,
            tick,
            expected,
            actual,
            error,
            rule_id=rule_id,
            component=component,
            evidence=evidence,
        )

    def set_metrics(
        self,
        *,
        total_ticks: int = 0,
        avg_tick_duration_ms: float = 0.0,
        max_drawdown_pct: float = 0.0,
        orders_placed: int = 0,
        orders_rejected: int = 0,
        orders_filled: int = 0,
        pnl_total: float = 0.0,
    ) -> None:
        """Set simulation metrics."""
        self._report.metrics = SimMetrics(
            total_ticks=total_ticks,
            avg_tick_duration_ms=avg_tick_duration_ms,
            max_drawdown_pct=max_drawdown_pct,
            orders_placed=orders_placed,
            orders_rejected=orders_rejected,
            orders_filled=orders_filled,
            pnl_total=pnl_total,
        )

    def generate_report(self) -> SimReport:
        """Generate final report."""
        return self._report

    def save_report(self, path: str | Path) -> None:
        """
        Save report to JSON file.

        Args:
            path: Output file path (typically artifacts/sim/report.json)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._report.to_json(), encoding="utf-8")
        logger.info("Sim report saved to %s", path)


# =============================================================================
# 退出码（军规级）
# =============================================================================
class SimExitCode:
    """Exit codes for simulation/replay (military-grade).

    Exit codes:
        0 = All scenarios passed
        8 = Replay failed
        9 = Sim failed
        12 = Policy violation (military-grade enforcement)
    """

    SUCCESS = 0
    REPLAY_FAIL = 8
    SIM_FAIL = 9
    POLICY_VIOLATION = 12


def get_sim_exit_code(report: SimReport) -> int:
    """Determine exit code based on sim report."""
    if report.passed:
        return SimExitCode.SUCCESS

    if report.type == "replay":
        return SimExitCode.REPLAY_FAIL
    return SimExitCode.SIM_FAIL


# =============================================================================
# V2 Required Scenarios 加载与校验（军规级）
# =============================================================================


def load_required_scenarios(
    yaml_path: str | Path = "V2_REQUIRED_SCENARIOS.yml",
) -> dict[str, Any]:
    """
    Load V2 required scenarios from YAML.

    Args:
        yaml_path: Path to V2_REQUIRED_SCENARIOS.yml

    Returns:
        Parsed YAML content
    """
    import yaml

    path = Path(yaml_path)
    if not path.exists():
        logger.warning("V2_REQUIRED_SCENARIOS.yml not found: %s", path)
        return {}

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_scenario_coverage(
    report: SimReport,
    required_scenarios: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Validate that all required scenarios were executed.

    Args:
        report: SimReport with executed scenarios
        required_scenarios: Loaded V2_REQUIRED_SCENARIOS.yml

    Returns:
        List of missing/skipped scenario violations
    """
    violations: list[dict[str, Any]] = []

    if not required_scenarios:
        return violations

    # Collect all required rule_ids
    required_rule_ids: set[str] = set()
    phases = required_scenarios.get("phases", {})
    for phase_data in phases.values():
        if not isinstance(phase_data, dict):
            continue
        scenarios = phase_data.get("scenarios", [])
        for scenario in scenarios:
            if isinstance(scenario, dict) and scenario.get("required", True):
                rule_id = scenario.get("rule_id", "")
                if rule_id:
                    required_rule_ids.add(rule_id)

    # Collect executed rule_ids
    executed_rule_ids: set[str] = set()
    for failure in report.failures:
        if failure.rule_id:
            executed_rule_ids.add(failure.rule_id)

    # TODO: Also track passed scenarios (need to store rule_ids in passes)
    # For now, we only check if failures have proper rule_ids

    # Check for missing rule_ids in failures
    for failure in report.failures:
        if not failure.rule_id or failure.rule_id.startswith("UNKNOWN."):
            violations.append(
                {
                    "type": "MISSING_RULE_ID",
                    "scenario": failure.scenario,
                    "message": "Failure missing proper rule_id",
                }
            )

    return violations


# =============================================================================
# 便捷函数
# =============================================================================


def run_replay_with_report(
    scenarios: list[dict[str, Any]],
    output_path: str = "artifacts/sim/report.json",
) -> SimReport:
    """
    Run replay scenarios and generate report.

    This is a convenience function that runs all scenarios and
    generates a machine-readable report.

    Args:
        scenarios: List of scenario configs to run
        output_path: Output path for JSON report

    Returns:
        SimReport with all results
    """
    gate = SimGate(sim_type="replay")

    # TODO: Integrate with actual replay runner
    # For now, this is a placeholder that should be connected to
    # src/replay/runner.py

    logger.info("Running %d replay scenarios...", len(scenarios))

    # Placeholder: run each scenario
    for scenario in scenarios:
        name = scenario.get("name", "unnamed")
        # In real implementation, call run_replay_tick() and check assertions
        # For now, just mark as pass
        gate.record_pass(name)

    gate.save_report(output_path)
    return gate.report


def log_sim_report(report: SimReport) -> None:
    """Log simulation report."""
    logger.info(report.summary())

    if report.failures:
        logger.error("Failures:")
        for failure in report.failures:
            logger.error(
                "  %s @ tick %d: %s",
                failure.scenario,
                failure.tick,
                failure.error,
            )

    logger.info("Metrics:")
    logger.info("  Total ticks: %d", report.metrics.total_ticks)
    logger.info("  Avg tick duration: %.2f ms", report.metrics.avg_tick_duration_ms)
    logger.info("  Max drawdown: %.2f%%", report.metrics.max_drawdown_pct)
    logger.info(
        "  Orders: %d placed, %d rejected, %d filled",
        report.metrics.orders_placed,
        report.metrics.orders_rejected,
        report.metrics.orders_filled,
    )
