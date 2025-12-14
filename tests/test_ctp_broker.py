"""Tests for CTP broker with lazy import."""

from __future__ import annotations

import pytest

from src.execution.ctp_broker import (
    CtpBroker,
    CtpConfig,
    CtpNotAvailableError,
)
from src.execution.order_types import Offset, OrderIntent, Side


def _make_config() -> CtpConfig:
    """Create test CTP config."""
    return CtpConfig(
        front_addr="tcp://127.0.0.1:10130",
        broker_id="9999",
        user_id="test",
        password="test123",
    )


class TestCtpBroker:
    """Tests for CtpBroker."""

    def test_init_without_sdk(self) -> None:
        """Broker initializes in mock mode when SDK not available."""
        config = _make_config()
        broker = CtpBroker(config)
        # Should not raise, just log warning
        assert broker.is_sdk_available is False
        assert broker.is_connected is False

    def test_connect_without_sdk_raises(self) -> None:
        """connect() raises CtpNotAvailableError when SDK not available."""
        config = _make_config()
        broker = CtpBroker(config)
        with pytest.raises(CtpNotAvailableError):
            broker.connect()

    def test_disconnect_safe(self) -> None:
        """disconnect() is safe to call even when not connected."""
        config = _make_config()
        broker = CtpBroker(config)
        # Should not raise
        broker.disconnect()
        assert broker.is_connected is False

    def test_place_order_mock_mode(self) -> None:
        """place_order() works in mock mode without SDK."""
        config = _make_config()
        broker = CtpBroker(config)
        intent = OrderIntent(
            symbol="au2412",
            side=Side.BUY,
            offset=Offset.OPEN,
            qty=1,
            price=500.0,
        )
        ack = broker.place_order(intent)
        assert ack.order_id.startswith("MOCK_")

    def test_place_order_increments_ref(self) -> None:
        """Order refs increment on each order."""
        config = _make_config()
        broker = CtpBroker(config)
        intent = OrderIntent(
            symbol="au2412",
            side=Side.BUY,
            offset=Offset.OPEN,
            qty=1,
            price=500.0,
        )
        ack1 = broker.place_order(intent)
        ack2 = broker.place_order(intent)
        assert ack1.order_id != ack2.order_id

    def test_repr(self) -> None:
        """__repr__ returns useful string."""
        config = _make_config()
        broker = CtpBroker(config)
        s = repr(broker)
        assert "CtpBroker" in s
        assert "9999" in s
