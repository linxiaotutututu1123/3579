"""LIVE mode guard and safety checks.

Provides safeguards for transitioning to LIVE trading mode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TradeMode(str, Enum):
    """Trading mode enumeration."""

    PAPER = "PAPER"
    LIVE = "LIVE"
    BACKTEST = "BACKTEST"


@dataclass(frozen=True)
class LiveModeCheck:
    """Result of a LIVE mode pre-flight check."""

    check_name: str
    passed: bool
    message: str


class LiveModeGuard:
    """
    Guard for LIVE mode trading.

    Performs safety checks before allowing LIVE trading.
    """

    def __init__(self, mode: str) -> None:
        """
        Initialize the guard.

        Args:
            mode: Trading mode string (PAPER, LIVE, BACKTEST)
        """
        self._mode = TradeMode(mode.upper())
        self._checks: list[LiveModeCheck] = []

    @property
    def mode(self) -> TradeMode:
        """Current trading mode."""
        return self._mode

    @property
    def is_live(self) -> bool:
        """Check if in LIVE mode."""
        return self._mode == TradeMode.LIVE

    @property
    def is_paper(self) -> bool:
        """Check if in PAPER mode."""
        return self._mode == TradeMode.PAPER

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        """Add a pre-flight check result."""
        check = LiveModeCheck(check_name=name, passed=passed, message=message)
        self._checks.append(check)

    def run_preflight_checks(
        self,
        *,
        broker_connected: bool = False,
        risk_limits_set: bool = False,
        strategy_validated: bool = False,
    ) -> list[LiveModeCheck]:
        """
        Run pre-flight checks for LIVE mode.

        Args:
            broker_connected: Whether broker is connected
            risk_limits_set: Whether risk limits are configured
            strategy_validated: Whether strategy has been validated

        Returns:
            List of check results
        """
        self._checks = []

        # Check 1: Broker connection
        self.add_check(
            "broker_connected",
            broker_connected,
            "Broker must be connected for LIVE trading",
        )

        # Check 2: Risk limits
        self.add_check(
            "risk_limits_set",
            risk_limits_set,
            "Risk limits must be configured for LIVE trading",
        )

        # Check 3: Strategy validation
        self.add_check(
            "strategy_validated",
            strategy_validated,
            "Strategy must be validated before LIVE trading",
        )

        return self._checks

    def all_checks_passed(self) -> bool:
        """Check if all pre-flight checks passed."""
        if not self._checks:
            return False
        return all(c.passed for c in self._checks)

    def can_trade_live(self) -> bool:
        """
        Check if LIVE trading is allowed.

        Returns:
            True only if in LIVE mode AND all checks passed
        """
        if not self.is_live:
            return False
        return self.all_checks_passed()

    def get_failed_checks(self) -> list[LiveModeCheck]:
        """Get list of failed checks."""
        return [c for c in self._checks if not c.passed]

    def log_status(self) -> None:
        """Log current guard status."""
        logger.info("Trade mode: %s", self._mode.value)
        if self._checks:
            passed = sum(1 for c in self._checks if c.passed)
            logger.info("Pre-flight checks: %d/%d passed", passed, len(self._checks))
            for check in self._checks:
                status = "PASS" if check.passed else "FAIL"
                logger.info("  [%s] %s: %s", status, check.check_name, check.message)
