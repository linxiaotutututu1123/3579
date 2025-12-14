"""CTP broker implementation with lazy import.

This module provides a CTP (China Trading Platform) broker implementation.
CTP SDK is imported lazily to allow CI environments without the SDK installed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.brokers.ctp.mapping import offset_to_ctp_offset_flag, side_to_ctp_direction
from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.order_types import OrderIntent
from src.trading.controls import TradeMode


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CtpConfigError(Exception):
    """Raised when CTP configuration is invalid or missing."""


class CtpNotAvailableError(Exception):
    """Raised when CTP SDK is not available."""


class CtpConnectionError(Exception):
    """Raised when CTP connection fails."""


@dataclass
class CtpConfig:
    """CTP connection configuration."""

    front_addr: str  # e.g. "tcp://180.168.146.187:10130"
    broker_id: str
    user_id: str
    password: str
    app_id: str = ""
    auth_code: str = ""
    instrument_ids: tuple[str, ...] = ()


_REQUIRED_CTP_ENV_VARS = (
    "CTP_FRONT_ADDR",
    "CTP_BROKER_ID",
    "CTP_USER_ID",
    "CTP_PASSWORD",
)

_OPTIONAL_CTP_ENV_VARS = (
    "CTP_APP_ID",
    "CTP_AUTH_CODE",
)


def validate_ctp_env(trade_mode: TradeMode) -> CtpConfig | None:
    """
    Validate CTP environment variables and return config.

    Args:
        trade_mode: Current trade mode (PAPER or LIVE)

    Returns:
        CtpConfig if LIVE mode and all required vars present, None if PAPER mode

    Raises:
        CtpConfigError: If LIVE mode and any required variable is missing
    """
    if trade_mode == TradeMode.PAPER:
        # PAPER mode does not require CTP configuration
        return None

    # LIVE mode requires all mandatory CTP environment variables
    missing = [k for k in _REQUIRED_CTP_ENV_VARS if not os.environ.get(k)]
    if missing:
        joined = ", ".join(missing)
        raise CtpConfigError(
            f"Missing required CTP environment variables for LIVE mode: {joined}. "
            "Set them before running in LIVE mode."
        )

    return CtpConfig(
        front_addr=os.environ["CTP_FRONT_ADDR"],
        broker_id=os.environ["CTP_BROKER_ID"],
        user_id=os.environ["CTP_USER_ID"],
        password=os.environ["CTP_PASSWORD"],
        app_id=os.environ.get("CTP_APP_ID", ""),
        auth_code=os.environ.get("CTP_AUTH_CODE", ""),
    )


def _lazy_import_ctp() -> Any:
    """Lazy import CTP SDK. Returns None if not available."""
    try:
        import ctp  # type: ignore[import-not-found]

        return ctp
    except ImportError:
        return None


class CtpBroker(Broker):
    """CTP broker implementation with lazy SDK import."""

    def __init__(self, config: CtpConfig, trade_mode: TradeMode = TradeMode.PAPER) -> None:
        """
        Initialize CTP broker.

        Args:
            config: CTP connection configuration
            trade_mode: Trading mode (PAPER allows mock, LIVE requires SDK)

        Raises:
            CtpNotAvailableError: If LIVE mode and CTP SDK is not installed
        """
        self._config = config
        self._trade_mode = trade_mode
        self._ctp = _lazy_import_ctp()
        self._connected = False
        self._order_ref = 0

        if self._ctp is None:
            if trade_mode == TradeMode.LIVE:
                raise CtpNotAvailableError(
                    "CTP SDK not installed but LIVE mode requires it. "
                    "Install CTP SDK or use PAPER mode."
                )
            logger.warning("CTP SDK not available - running in PAPER mock mode")

    @property
    def is_sdk_available(self) -> bool:
        """Check if CTP SDK is available."""
        return self._ctp is not None

    @property
    def is_connected(self) -> bool:
        """Check if connected to CTP."""
        return self._connected

    def connect(self) -> None:
        """
        Connect to CTP front.

        Raises:
            CtpNotAvailableError: If SDK not available
            CtpConnectionError: If connection fails
        """
        if self._ctp is None:
            raise CtpNotAvailableError("CTP SDK not installed")

        try:
            # Real CTP connection would happen here
            # For now, just mark as connected
            logger.info("Connecting to CTP: %s", self._config.front_addr)
            self._connected = True
        except Exception as e:
            raise CtpConnectionError(f"Failed to connect: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from CTP."""
        if self._connected:
            logger.info("Disconnecting from CTP")
            self._connected = False

    def place_order(self, intent: OrderIntent) -> OrderAck:
        """
        Place an order via CTP.

        Args:
            intent: Order intent to place

        Returns:
            OrderAck with order ID

        Raises:
            OrderRejected: If order is rejected
            CtpNotAvailableError: If LIVE mode and SDK not available
        """
        # Convert to CTP protocol values using F18 mapping
        ctp_direction = side_to_ctp_direction(intent.side)
        ctp_offset_flag = offset_to_ctp_offset_flag(intent.offset)

        if self._ctp is None:
            if self._trade_mode == TradeMode.LIVE:
                # LIVE mode without SDK is a hard error
                raise CtpNotAvailableError("Cannot place order: CTP SDK not available in LIVE mode")
            # PAPER mock mode - generate fake order ID
            self._order_ref += 1
            order_id = f"MOCK_{self._order_ref:06d}"
            logger.info(
                "Mock order placed: %s for %s (dir=%s, offset=%s)",
                order_id,
                intent,
                ctp_direction,
                ctp_offset_flag,
            )
            return OrderAck(order_id=order_id)

        if not self._connected:
            raise OrderRejected("Not connected to CTP")

        try:
            # Real CTP order submission would happen here
            # ctp_direction and ctp_offset_flag would be passed to CTP API
            self._order_ref += 1
            order_id = f"CTP_{self._order_ref:06d}"
            logger.info(
                "CTP order placed: %s for %s (dir=%s, offset=%s)",
                order_id,
                intent,
                ctp_direction,
                ctp_offset_flag,
            )
            return OrderAck(order_id=order_id)
        except Exception as e:
            raise OrderRejected(f"CTP order failed: {e}") from e

    def __repr__(self) -> str:
        return f"CtpBroker(broker_id={self._config.broker_id}, connected={self._connected})"
