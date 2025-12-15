"""Tests for Sim module (Military-Grade v3.0)."""

from __future__ import annotations

from src.trading.sim import parse_test_output, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_default_level(self) -> None:
        """Default level is INFO."""
        setup_logging(verbose=False)
        # No assertion - just ensures no errors

    def test_verbose_level(self) -> None:
        """Verbose mode uses DEBUG."""
        setup_logging(verbose=True)
        # No assertion - just ensures no errors


class TestParseTestOutput:
    """Tests for parse_test_output function."""

    def test_empty_output(self) -> None:
        """Empty output returns zeros."""
        passed, failed, failures = parse_test_output("")
        assert passed == 0
        assert failed == 0
        assert failures == []

    def test_all_passed(self) -> None:
        """Parse all passed output."""
        output = """
============================== 20 passed in 5.0s ==============================
"""
        passed, failed, failures = parse_test_output(output)
        assert passed == 20
        assert failed == 0
        assert failures == []

    def test_mixed_results(self) -> None:
        """Parse mixed pass/fail output."""
        output = """
FAILED tests/test_sim.py::test_backtest_scenario
2 failed, 18 passed in 10.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert passed == 18
        assert failed == 2
        assert "test_backtest_scenario" in failures

    def test_multiple_failures(self) -> None:
        """Parse multiple failures."""
        output = """
FAILED tests/test_sim.py::test_one
FAILED tests/test_sim.py::test_two
2 failed in 1.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert failed == 2
        assert len(failures) == 2
        assert "test_one" in failures
        assert "test_two" in failures

    def test_no_double_colon(self) -> None:
        """Handle failure line without ::."""
        output = """
FAILED tests/test_sim.py
1 failed in 1.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert failed == 1
        assert "tests/test_sim.py" in failures
