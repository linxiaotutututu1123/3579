"""Tests for LIVE mode guard."""

from __future__ import annotations

import pytest

from src.trading.live_guard import LiveModeGuard, TradeMode


class TestTradeMode:
    """Tests for TradeMode enum."""

    def test_paper_mode(self) -> None:
        """PAPER mode exists."""
        assert TradeMode.PAPER.value == "PAPER"

    def test_live_mode(self) -> None:
        """LIVE mode exists."""
        assert TradeMode.LIVE.value == "LIVE"

    def test_backtest_mode(self) -> None:
        """BACKTEST mode exists."""
        assert TradeMode.BACKTEST.value == "BACKTEST"


class TestLiveModeGuard:
    """Tests for LiveModeGuard."""

    def test_init_paper(self) -> None:
        """Guard initializes in PAPER mode."""
        guard = LiveModeGuard("paper")
        assert guard.mode == TradeMode.PAPER
        assert guard.is_paper is True
        assert guard.is_live is False

    def test_init_live(self) -> None:
        """Guard initializes in LIVE mode."""
        guard = LiveModeGuard("LIVE")
        assert guard.mode == TradeMode.LIVE
        assert guard.is_live is True
        assert guard.is_paper is False

    def test_init_case_insensitive(self) -> None:
        """Mode parsing is case-insensitive."""
        guard = LiveModeGuard("Live")
        assert guard.mode == TradeMode.LIVE

    def test_invalid_mode_raises(self) -> None:
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError):
            LiveModeGuard("INVALID")

    def test_preflight_checks_all_pass(self) -> None:
        """All pre-flight checks can pass."""
        guard = LiveModeGuard("LIVE")
        checks = guard.run_preflight_checks(
            broker_connected=True,
            risk_limits_set=True,
            strategy_validated=True,
        )
        assert len(checks) == 3
        assert guard.all_checks_passed() is True

    def test_preflight_checks_some_fail(self) -> None:
        """Failed checks are detected."""
        guard = LiveModeGuard("LIVE")
        guard.run_preflight_checks(
            broker_connected=True,
            risk_limits_set=False,
            strategy_validated=True,
        )
        assert guard.all_checks_passed() is False
        failed = guard.get_failed_checks()
        assert len(failed) == 1
        assert failed[0].check_name == "risk_limits_set"

    def test_can_trade_live_requires_live_mode(self) -> None:
        """can_trade_live returns False in PAPER mode."""
        guard = LiveModeGuard("PAPER")
        guard.run_preflight_checks(
            broker_connected=True,
            risk_limits_set=True,
            strategy_validated=True,
        )
        assert guard.can_trade_live() is False

    def test_can_trade_live_requires_all_checks(self) -> None:
        """can_trade_live requires all checks passed."""
        guard = LiveModeGuard("LIVE")
        guard.run_preflight_checks(
            broker_connected=True,
            risk_limits_set=False,
            strategy_validated=True,
        )
        assert guard.can_trade_live() is False

    def test_can_trade_live_success(self) -> None:
        """can_trade_live returns True when all conditions met."""
        guard = LiveModeGuard("LIVE")
        guard.run_preflight_checks(
            broker_connected=True,
            risk_limits_set=True,
            strategy_validated=True,
        )
        assert guard.can_trade_live() is True

    def test_add_custom_check(self) -> None:
        """Custom checks can be added."""
        guard = LiveModeGuard("LIVE")
        guard.add_check("custom_check", True, "Custom validation")
        assert len(guard._checks) == 1

    def test_all_checks_passed_empty(self) -> None:
        """all_checks_passed returns False with no checks."""
        guard = LiveModeGuard("LIVE")
        assert guard.all_checks_passed() is False
