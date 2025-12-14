"""Broker factory for PAPER/LIVE mode selection.

This module provides a factory function that creates the appropriate broker
based on trade mode. PAPER mode uses NoopBroker (no real orders), while
LIVE mode uses CtpBroker with full CTP SDK integration.

Key design decisions:
- PAPER path does NOT import CTP SDK or validate CTP env vars
- LIVE path validates CTP env vars and requires CTP SDK
- Factory accepts AppSettings and extracts trade_mode string
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import AppSettings
from src.execution.broker import Broker, NoopBroker
from src.trading.controls import TradeMode


if TYPE_CHECKING:
    pass


class BrokerFactoryError(Exception):
    """Raised when broker factory fails to create a broker."""


def _normalize_trade_mode(mode_str: str) -> TradeMode:
    """
    Normalize trade mode string to TradeMode enum.

    Args:
        mode_str: Trade mode string from settings (e.g. "PAPER", "LIVE")

    Returns:
        TradeMode enum value

    Raises:
        BrokerFactoryError: If mode_str is not a valid trade mode
    """
    mode_upper = mode_str.strip().upper()
    if mode_upper == "PAPER":
        return TradeMode.PAPER
    if mode_upper == "LIVE":
        return TradeMode.LIVE
    raise BrokerFactoryError(f"Unknown trade mode: {mode_str!r}. Must be 'PAPER' or 'LIVE'.")


def broker_factory(settings: AppSettings) -> Broker:
    """
    Create appropriate broker based on settings.trade_mode.

    Args:
        settings: Application settings containing trade_mode

    Returns:
        Broker instance (NoopBroker for PAPER, CtpBroker for LIVE)

    Raises:
        BrokerFactoryError: If trade mode is invalid
        CtpConfigError: If LIVE mode and CTP env vars are missing
        CtpNotAvailableError: If LIVE mode and CTP SDK is not installed
    """
    trade_mode = _normalize_trade_mode(settings.trade_mode)

    if trade_mode == TradeMode.PAPER:
        # PAPER mode: use NoopBroker, no CTP import, no env validation
        return NoopBroker()

    # LIVE mode: import CTP modules lazily and validate configuration
    # This import is deferred to avoid loading CTP SDK in PAPER mode
    from src.execution.ctp_broker import CtpBroker, validate_ctp_env

    ctp_config = validate_ctp_env(trade_mode)
    if ctp_config is None:
        # This should not happen for LIVE mode, but handle defensively
        raise BrokerFactoryError("validate_ctp_env returned None for LIVE mode (unexpected)")

    return CtpBroker(ctp_config, trade_mode=trade_mode)
