"""Tests for Replay module (Military-Grade v3.0)."""

from __future__ import annotations

from src.trading.replay import parse_test_output, setup_logging


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
============================== 10 passed in 2.5s ==============================
"""
        passed, failed, failures = parse_test_output(output)
        assert passed == 10
        assert failed == 0
        assert failures == []

    def test_mixed_results(self) -> None:
        """Parse mixed pass/fail output."""
        output = """
FAILED tests/test_replay.py::test_deterministic_replay
3 failed, 7 passed in 5.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert passed == 7
        assert failed == 3
        assert "test_deterministic_replay" in failures

    def test_multiple_failures(self) -> None:
        """Parse multiple failures."""
        output = """
FAILED tests/test_replay.py::test_one
FAILED tests/test_replay.py::test_two
FAILED tests/test_replay.py::test_three
3 failed in 1.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert failed == 3
        assert len(failures) == 3
        assert "test_one" in failures
        assert "test_two" in failures
        assert "test_three" in failures

    def test_no_double_colon(self) -> None:
        """Handle failure line without ::."""
        output = """
FAILED tests/test_replay.py
1 failed in 1.0s
"""
        passed, failed, failures = parse_test_output(output)
        assert failed == 1
        assert "tests/test_replay.py" in failures
