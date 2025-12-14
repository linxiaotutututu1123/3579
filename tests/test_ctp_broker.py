"""Tests for CTP broker with lazy import."""

from __future__ import annotations

import pytest

from src.execution.ctp_broker import (
    CtpBroker,
    CtpConfig,
    CtpConfigError,
    CtpNotAvailableError,
    validate_ctp_env,
)
from src.execution.order_types import Offset, OrderIntent, Side
from src.trading.controls import TradeMode


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


class TestValidateCtpEnv:
    """Tests for validate_ctp_env function."""

    def test_paper_mode_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PAPER mode does not require CTP config and returns None."""
        # Even with no env vars set, PAPER should return None
        for var in ("CTP_FRONT_ADDR", "CTP_BROKER_ID", "CTP_USER_ID", "CTP_PASSWORD"):
            monkeypatch.delenv(var, raising=False)

        result = validate_ctp_env(TradeMode.PAPER)
        assert result is None

    def test_live_mode_missing_vars_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LIVE mode with missing vars raises CtpConfigError with clear message."""
        # Clear all CTP env vars
        for var in ("CTP_FRONT_ADDR", "CTP_BROKER_ID", "CTP_USER_ID", "CTP_PASSWORD"):
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(CtpConfigError) as exc_info:
            validate_ctp_env(TradeMode.LIVE)

        error_msg = str(exc_info.value)
        assert "CTP_FRONT_ADDR" in error_msg
        assert "CTP_BROKER_ID" in error_msg
        assert "CTP_USER_ID" in error_msg
        assert "CTP_PASSWORD" in error_msg
        assert "LIVE mode" in error_msg

    def test_live_mode_partial_vars_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LIVE mode with partial vars raises and lists only missing ones."""
        monkeypatch.setenv("CTP_FRONT_ADDR", "tcp://127.0.0.1:10130")
        monkeypatch.setenv("CTP_BROKER_ID", "9999")
        monkeypatch.delenv("CTP_USER_ID", raising=False)
        monkeypatch.delenv("CTP_PASSWORD", raising=False)

        with pytest.raises(CtpConfigError) as exc_info:
            validate_ctp_env(TradeMode.LIVE)

        error_msg = str(exc_info.value)
        assert "CTP_FRONT_ADDR" not in error_msg  # This one is set
        assert "CTP_BROKER_ID" not in error_msg  # This one is set
        assert "CTP_USER_ID" in error_msg
        assert "CTP_PASSWORD" in error_msg

    def test_live_mode_all_required_vars_returns_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LIVE mode with all required vars returns valid CtpConfig."""
        monkeypatch.setenv("CTP_FRONT_ADDR", "tcp://180.168.146.187:10130")
        monkeypatch.setenv("CTP_BROKER_ID", "9999")
        monkeypatch.setenv("CTP_USER_ID", "testuser")
        monkeypatch.setenv("CTP_PASSWORD", "testpass")
        monkeypatch.delenv("CTP_APP_ID", raising=False)
        monkeypatch.delenv("CTP_AUTH_CODE", raising=False)

        result = validate_ctp_env(TradeMode.LIVE)

        assert result is not None
        assert result.front_addr == "tcp://180.168.146.187:10130"
        assert result.broker_id == "9999"
        assert result.user_id == "testuser"
        assert result.password == "testpass"
        assert result.app_id == ""  # Optional, defaults to empty
        assert result.auth_code == ""  # Optional, defaults to empty

    def test_live_mode_optional_vars_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """LIVE mode includes optional vars when set."""
        monkeypatch.setenv("CTP_FRONT_ADDR", "tcp://180.168.146.187:10130")
        monkeypatch.setenv("CTP_BROKER_ID", "9999")
        monkeypatch.setenv("CTP_USER_ID", "testuser")
        monkeypatch.setenv("CTP_PASSWORD", "testpass")
        monkeypatch.setenv("CTP_APP_ID", "simnow_client")
        monkeypatch.setenv("CTP_AUTH_CODE", "auth123")

        result = validate_ctp_env(TradeMode.LIVE)

        assert result is not None
        assert result.app_id == "simnow_client"
        assert result.auth_code == "auth123"
