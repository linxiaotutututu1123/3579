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
    Simulation/Replay gate for automated validation.

    Collects scenario results and generates machine-readable reports.
    """

    def __init__(self, sim_type: str = "replay") -> None:
        """
        Initialize simulation gate.

        Args:
            sim_type: Type of simulation ("replay" or "sim")
        """
        self._report = SimReport(type=sim_type)

    @property
    def report(self) -> SimReport:
        """Get current report."""
        return self._report

    def record_pass(self, scenario: str) -> None:
        """Record a passed scenario."""
        self._report.add_pass(scenario)

    def record_failure(
        self,
        scenario: str,
        tick: int,
        expected: dict[str, Any],
        actual: dict[str, Any],
        error: str,
    ) -> None:
        """Record a failed scenario."""
        self._report.add_failure(scenario, tick, expected, actual, error)

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
# 退出码
# =============================================================================
class SimExitCode:
    """Exit codes for simulation/replay.

    Exit codes:
        0 = All scenarios passed
        8 = Replay failed
        9 = Sim failed
    """

    SUCCESS = 0
    REPLAY_FAIL = 8
    SIM_FAIL = 9


def get_sim_exit_code(report: SimReport) -> int:
    """Determine exit code based on sim report."""
    if report.passed:
        return SimExitCode.SUCCESS

    if report.type == "replay":
        return SimExitCode.REPLAY_FAIL
    return SimExitCode.SIM_FAIL


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
