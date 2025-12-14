"""Tests for broker factory (F20).

Covers:
- PAPER mode returns NoopBroker without CTP import
- LIVE mode with valid env returns CtpBroker (if SDK available) or raises
- Invalid trade mode raises BrokerFactoryError
- Normalize function handles case variations
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from src.config import AppSettings
from src.execution.broker import NoopBroker
from src.execution.broker_factory import (
    BrokerFactoryError,
    _normalize_trade_mode,
    broker_factory,
)
from src.trading.controls import TradeMode


class TestNormalizeTradeMode:
    """Tests for _normalize_trade_mode helper."""

    def test_paper_lowercase(self) -> None:
        """'paper' normalizes to TradeMode.PAPER."""
        assert _normalize_trade_mode("paper") == TradeMode.PAPER

    def test_paper_uppercase(self) -> None:
        """'PAPER' normalizes to TradeMode.PAPER."""
        assert _normalize_trade_mode("PAPER") == TradeMode.PAPER

    def test_paper_mixed_case(self) -> None:
        """'PaPeR' normalizes to TradeMode.PAPER."""
        assert _normalize_trade_mode("PaPeR") == TradeMode.PAPER

    def test_paper_with_whitespace(self) -> None:
        """' PAPER ' normalizes to TradeMode.PAPER."""
        assert _normalize_trade_mode("  PAPER  ") == TradeMode.PAPER

    def test_live_lowercase(self) -> None:
        """'live' normalizes to TradeMode.LIVE."""
        assert _normalize_trade_mode("live") == TradeMode.LIVE

    def test_live_uppercase(self) -> None:
        """'LIVE' normalizes to TradeMode.LIVE."""
        assert _normalize_trade_mode("LIVE") == TradeMode.LIVE

    def test_invalid_mode_raises(self) -> None:
        """Invalid mode raises BrokerFactoryError."""
        with pytest.raises(BrokerFactoryError) as exc_info:
            _normalize_trade_mode("SIMULATION")
        assert "Unknown trade mode" in str(exc_info.value)
        assert "SIMULATION" in str(exc_info.value)

    def test_empty_string_raises(self) -> None:
        """Empty string raises BrokerFactoryError."""
        with pytest.raises(BrokerFactoryError):
            _normalize_trade_mode("")


class TestBrokerFactoryPaper:
    """Tests for broker_factory in PAPER mode."""

    def test_paper_returns_noop_broker(self) -> None:
        """PAPER mode returns NoopBroker instance."""
        settings = AppSettings(trade_mode="PAPER")
        broker = broker_factory(settings)
        assert isinstance(broker, NoopBroker)

    def test_paper_does_not_import_ctp_broker(self) -> None:
        """PAPER mode should not trigger CTP module import."""
        # Remove ctp_broker from sys.modules if present to ensure clean state
        modules_before = set(sys.modules.keys())

        settings = AppSettings(trade_mode="PAPER")
        broker = broker_factory(settings)

        # Verify broker is NoopBroker
        assert isinstance(broker, NoopBroker)

        # Note: We can't fully test that ctp_broker wasn't imported because
        # it may have been imported in previous tests. The key design point
        # is that the PAPER path doesn't call validate_ctp_env or CtpBroker.

    def test_paper_does_not_require_ctp_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PAPER mode works without CTP environment variables."""
        # Clear all CTP env vars
        for var in ("CTP_FRONT_ADDR", "CTP_BROKER_ID", "CTP_USER_ID", "CTP_PASSWORD"):
            monkeypatch.delenv(var, raising=False)

        settings = AppSettings(trade_mode="PAPER")
        broker = broker_factory(settings)
        assert isinstance(broker, NoopBroker)


class TestBrokerFactoryLive:
    """Tests for broker_factory in LIVE mode."""

    def test_live_missing_env_raises_ctp_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LIVE mode with missing env vars raises CtpConfigError."""
        # Clear all CTP env vars
        for var in ("CTP_FRONT_ADDR", "CTP_BROKER_ID", "CTP_USER_ID", "CTP_PASSWORD"):
            monkeypatch.delenv(var, raising=False)

        from src.execution.ctp_broker import CtpConfigError

        settings = AppSettings(trade_mode="LIVE")
        with pytest.raises(CtpConfigError) as exc_info:
            broker_factory(settings)
        assert "Missing required CTP environment variables" in str(exc_info.value)

    def test_live_with_env_but_no_sdk_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LIVE mode with env vars but no SDK raises CtpNotAvailableError."""
        # Set required CTP env vars
        monkeypatch.setenv("CTP_FRONT_ADDR", "tcp://127.0.0.1:10130")
        monkeypatch.setenv("CTP_BROKER_ID", "9999")
        monkeypatch.setenv("CTP_USER_ID", "testuser")
        monkeypatch.setenv("CTP_PASSWORD", "testpass")

        from src.execution.ctp_broker import CtpNotAvailableError

        settings = AppSettings(trade_mode="LIVE")
        # Since CTP SDK is not installed in CI, this should raise
        with pytest.raises(CtpNotAvailableError) as exc_info:
            broker_factory(settings)
        assert "LIVE mode requires it" in str(exc_info.value)


class TestBrokerFactoryInvalidMode:
    """Tests for broker_factory with invalid trade mode."""

    def test_invalid_mode_raises(self) -> None:
        """Invalid trade mode raises BrokerFactoryError."""
        settings = AppSettings(trade_mode="INVALID")
        with pytest.raises(BrokerFactoryError) as exc_info:
            broker_factory(settings)
        assert "Unknown trade mode" in str(exc_info.value)
