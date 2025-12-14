"""Position reconciliation for LIVE trading.

Compares expected positions with actual broker positions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ReconcileStatus(str, Enum):
    """Reconciliation status."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_EXPECTED = "MISSING_EXPECTED"
    MISSING_ACTUAL = "MISSING_ACTUAL"


@dataclass(frozen=True)
class ReconcileResult:
    """Result of position reconciliation for a single symbol."""

    symbol: str
    status: ReconcileStatus
    expected_qty: int
    actual_qty: int
    difference: int

    @property
    def is_ok(self) -> bool:
        """Check if reconciliation passed."""
        return self.status == ReconcileStatus.MATCH


@dataclass(frozen=True)
class ReconcileReport:
    """Full reconciliation report."""

    results: tuple[ReconcileResult, ...]
    timestamp: float

    @property
    def all_matched(self) -> bool:
        """Check if all positions matched."""
        return all(r.is_ok for r in self.results)

    @property
    def mismatches(self) -> list[ReconcileResult]:
        """Get list of mismatched positions."""
        return [r for r in self.results if not r.is_ok]

    def summary(self) -> str:
        """Generate summary string."""
        matched = sum(1 for r in self.results if r.is_ok)
        total = len(self.results)
        status = "OK" if self.all_matched else "MISMATCH"
        return f"Reconciliation: {status} ({matched}/{total} matched)"


def reconcile_positions(
    expected: dict[str, int],
    actual: dict[str, int],
    timestamp: float = 0.0,
) -> ReconcileReport:
    """
    Reconcile expected positions against actual broker positions.

    Args:
        expected: Expected positions (symbol -> qty)
        actual: Actual positions from broker (symbol -> qty)
        timestamp: Timestamp of reconciliation

    Returns:
        ReconcileReport with results for each symbol
    """
    all_symbols = set(expected.keys()) | set(actual.keys())
    results: list[ReconcileResult] = []

    for symbol in sorted(all_symbols):
        exp_qty = expected.get(symbol, 0)
        act_qty = actual.get(symbol, 0)
        diff = act_qty - exp_qty

        if exp_qty == act_qty:
            status = ReconcileStatus.MATCH
        elif symbol not in expected:
            status = ReconcileStatus.MISSING_EXPECTED
        elif symbol not in actual:
            status = ReconcileStatus.MISSING_ACTUAL
        else:
            status = ReconcileStatus.MISMATCH

        results.append(
            ReconcileResult(
                symbol=symbol,
                status=status,
                expected_qty=exp_qty,
                actual_qty=act_qty,
                difference=diff,
            )
        )

    return ReconcileReport(results=tuple(results), timestamp=timestamp)


def log_reconcile_report(report: ReconcileReport) -> None:
    """Log reconciliation report."""
    logger.info(report.summary())
    for r in report.results:
        if r.is_ok:
            logger.debug("  %s: MATCH (qty=%d)", r.symbol, r.actual_qty)
        else:
            logger.warning(
                "  %s: %s (expected=%d, actual=%d, diff=%d)",
                r.symbol,
                r.status.value,
                r.expected_qty,
                r.actual_qty,
                r.difference,
            )
