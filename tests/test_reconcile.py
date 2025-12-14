"""Tests for position reconciliation."""

from __future__ import annotations

from src.trading.reconcile import (
    ReconcileReport,
    ReconcileResult,
    ReconcileStatus,
    reconcile_positions,
)


class TestReconcileResult:
    """Tests for ReconcileResult."""

    def test_match_is_ok(self) -> None:
        """MATCH status is OK."""
        r = ReconcileResult(
            symbol="AO",
            status=ReconcileStatus.MATCH,
            expected_qty=1,
            actual_qty=1,
            difference=0,
        )
        assert r.is_ok is True

    def test_mismatch_not_ok(self) -> None:
        """MISMATCH status is not OK."""
        r = ReconcileResult(
            symbol="AO",
            status=ReconcileStatus.MISMATCH,
            expected_qty=1,
            actual_qty=2,
            difference=1,
        )
        assert r.is_ok is False


class TestReconcileReport:
    """Tests for ReconcileReport."""

    def test_all_matched(self) -> None:
        """all_matched returns True when all match."""
        report = ReconcileReport(
            results=(
                ReconcileResult("AO", ReconcileStatus.MATCH, 1, 1, 0),
                ReconcileResult("SA", ReconcileStatus.MATCH, -1, -1, 0),
            ),
            timestamp=0.0,
        )
        assert report.all_matched is True
        assert len(report.mismatches) == 0

    def test_has_mismatch(self) -> None:
        """mismatches returns failed reconciliations."""
        report = ReconcileReport(
            results=(
                ReconcileResult("AO", ReconcileStatus.MATCH, 1, 1, 0),
                ReconcileResult("SA", ReconcileStatus.MISMATCH, -1, 0, 1),
            ),
            timestamp=0.0,
        )
        assert report.all_matched is False
        assert len(report.mismatches) == 1
        assert report.mismatches[0].symbol == "SA"

    def test_summary(self) -> None:
        """summary returns readable string."""
        report = ReconcileReport(
            results=(ReconcileResult("AO", ReconcileStatus.MATCH, 1, 1, 0),),
            timestamp=0.0,
        )
        s = report.summary()
        assert "OK" in s
        assert "1/1" in s


class TestReconcilePositions:
    """Tests for reconcile_positions function."""

    def test_empty_positions(self) -> None:
        """Empty positions reconcile OK."""
        report = reconcile_positions({}, {})
        assert report.all_matched is True
        assert len(report.results) == 0

    def test_matching_positions(self) -> None:
        """Matching positions reconcile OK."""
        expected = {"AO": 1, "SA": -1}
        actual = {"AO": 1, "SA": -1}
        report = reconcile_positions(expected, actual)
        assert report.all_matched is True
        assert len(report.results) == 2

    def test_mismatch_detected(self) -> None:
        """Quantity mismatch is detected."""
        expected = {"AO": 1}
        actual = {"AO": 2}
        report = reconcile_positions(expected, actual)
        assert report.all_matched is False
        r = report.results[0]
        assert r.status == ReconcileStatus.MISMATCH
        assert r.difference == 1

    def test_missing_actual(self) -> None:
        """Missing actual position is detected."""
        expected = {"AO": 1}
        actual: dict[str, int] = {}
        report = reconcile_positions(expected, actual)
        assert report.all_matched is False
        r = report.results[0]
        assert r.status == ReconcileStatus.MISSING_ACTUAL

    def test_missing_expected(self) -> None:
        """Unexpected actual position is detected."""
        expected: dict[str, int] = {}
        actual = {"AO": 1}
        report = reconcile_positions(expected, actual)
        assert report.all_matched is False
        r = report.results[0]
        assert r.status == ReconcileStatus.MISSING_EXPECTED

    def test_timestamp_preserved(self) -> None:
        """Timestamp is preserved in report."""
        report = reconcile_positions({}, {}, timestamp=12345.0)
        assert report.timestamp == 12345.0

    def test_zero_qty_match(self) -> None:
        """Zero quantities match correctly."""
        expected = {"AO": 0}
        actual = {"AO": 0}
        report = reconcile_positions(expected, actual)
        assert report.all_matched is True
