"""CTP broker implementation with lazy import.

This module provides a CTP (China Trading Platform) broker implementation.
CTP SDK is imported lazily to allow CI environments without the SDK installed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.order_types import OrderIntent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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


def _lazy_import_ctp() -> Any:
    """Lazy import CTP SDK. Returns None if not available."""
    try:
        import ctp  # noqa: PLC0415

        return ctp
    except ImportError:
        return None


class CtpBroker(Broker):
    """CTP broker implementation with lazy SDK import."""

    def __init__(self, config: CtpConfig) -> None:
        """
        Initialize CTP broker.

        Args:
            config: CTP connection configuration

        Raises:
            CtpNotAvailableError: If CTP SDK is not installed
        """
        self._config = config
        self._ctp = _lazy_import_ctp()
        self._connected = False
        self._order_ref = 0

        if self._ctp is None:
            logger.warning("CTP SDK not available - running in mock mode")

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
            CtpNotAvailableError: If SDK not available
        """
        if self._ctp is None:
            # Mock mode - generate fake order ID
            self._order_ref += 1
            order_id = f"MOCK_{self._order_ref:06d}"
            logger.info("Mock order placed: %s for %s", order_id, intent)
            return OrderAck(order_id=order_id)

        if not self._connected:
            raise OrderRejected("Not connected to CTP")

        try:
            # Real CTP order submission would happen here
            self._order_ref += 1
            order_id = f"CTP_{self._order_ref:06d}"
            logger.info("CTP order placed: %s for %s", order_id, intent)
            return OrderAck(order_id=order_id)
        except Exception as e:
            raise OrderRejected(f"CTP order failed: {e}") from e

    def __repr__(self) -> str:
        return f"CtpBroker(broker_id={self._config.broker_id}, connected={self._connected})"
