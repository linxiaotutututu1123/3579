"""
Tests for TimeoutManager.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- EXEC.TIMEOUT.ACK
- EXEC.TIMEOUT.FILL
"""

import pytest

from src.execution.auto.timeout import (
    TimeoutConfig,
    TimeoutEntry,
    TimeoutManager,
    TimeoutType,
)


class TestTimeoutConfig:
    """Tests for TimeoutConfig."""

    def test_default_config(self) -> None:
        """Test default timeout configuration."""
        config = TimeoutConfig()
        assert config.ack_timeout_s == 5.0
        assert config.fill_timeout_s == 30.0
        assert config.cancel_timeout_s == 10.0

    def test_custom_config(self) -> None:
        """Test custom timeout configuration."""
        config = TimeoutConfig(
            ack_timeout_s=3.0,
            fill_timeout_s=60.0,
            cancel_timeout_s=15.0,
        )
        assert config.ack_timeout_s == 3.0
        assert config.fill_timeout_s == 60.0
        assert config.cancel_timeout_s == 15.0


class TestTimeoutEntry:
    """Tests for TimeoutEntry."""

    def test_entry_not_expired(self) -> None:
        """Test entry not expired."""
        now = 1000.0
        entry = TimeoutEntry(
            local_id="order1",
            timeout_type=TimeoutType.ACK,
            deadline=now + 5.0,
            created_at=now,
        )
        assert not entry.is_expired(now + 1.0)
        assert entry.remaining_s(now + 1.0) == 4.0

    def test_entry_expired(self) -> None:
        """Test entry expired."""
        now = 1000.0
        entry = TimeoutEntry(
            local_id="order1",
            timeout_type=TimeoutType.ACK,
            deadline=now + 5.0,
            created_at=now,
        )
        assert entry.is_expired(now + 6.0)
        assert entry.remaining_s(now + 6.0) == -1.0

    def test_entry_exactly_at_deadline(self) -> None:
        """Test entry at exactly deadline is expired."""
        now = 1000.0
        entry = TimeoutEntry(
            local_id="order1",
            timeout_type=TimeoutType.ACK,
            deadline=now + 5.0,
            created_at=now,
        )
        assert entry.is_expired(now + 5.0)


class TestTimeoutManagerAck:
    """Tests for EXEC.TIMEOUT.ACK scenario."""

    def test_register_ack_timeout(self) -> None:
        """Test registering ACK timeout."""
        now = 1000.0
        config = TimeoutConfig(ack_timeout_s=5.0)
        mgr = TimeoutManager(config=config)

        entry = mgr.register_ack_timeout("order1", now=now)

        assert entry.local_id == "order1"
        assert entry.timeout_type == TimeoutType.ACK
        assert entry.deadline == now + 5.0
        assert len(mgr) == 1

    def test_ack_timeout_expires(self) -> None:
        """Test ACK timeout expiration."""
        now = 1000.0
        config = TimeoutConfig(ack_timeout_s=5.0)
        mgr = TimeoutManager(config=config)

        mgr.register_ack_timeout("order1", now=now)

        # Not expired yet
        expired = mgr.check_expired(now + 4.0)
        assert len(expired) == 0

        # Expired
        expired = mgr.check_expired(now + 6.0)
        assert len(expired) == 1
        assert expired[0].local_id == "order1"
        assert expired[0].timeout_type == TimeoutType.ACK

    def test_ack_timeout_callback(self) -> None:
        """Test ACK timeout callback."""
        callbacks = []

        def on_timeout(local_id: str, timeout_type: TimeoutType) -> None:
            callbacks.append((local_id, timeout_type))

        now = 1000.0
        config = TimeoutConfig(ack_timeout_s=5.0)
        mgr = TimeoutManager(config=config, on_timeout=on_timeout)

        mgr.register_ack_timeout("order1", now=now)
        mgr.check_expired(now + 6.0)

        assert len(callbacks) == 1
        assert callbacks[0] == ("order1", TimeoutType.ACK)


class TestTimeoutManagerFill:
    """Tests for EXEC.TIMEOUT.FILL scenario."""

    def test_register_fill_timeout(self) -> None:
        """Test registering FILL timeout."""
        now = 1000.0
        config = TimeoutConfig(fill_timeout_s=30.0)
        mgr = TimeoutManager(config=config)

        entry = mgr.register_fill_timeout("order1", now=now)

        assert entry.local_id == "order1"
        assert entry.timeout_type == TimeoutType.FILL
        assert entry.deadline == now + 30.0

    def test_fill_timeout_expires(self) -> None:
        """Test FILL timeout expiration."""
        now = 1000.0
        config = TimeoutConfig(fill_timeout_s=30.0)
        mgr = TimeoutManager(config=config)

        mgr.register_fill_timeout("order1", now=now)

        # Not expired yet
        expired = mgr.check_expired(now + 25.0)
        assert len(expired) == 0

        # Expired
        expired = mgr.check_expired(now + 31.0)
        assert len(expired) == 1
        assert expired[0].timeout_type == TimeoutType.FILL


class TestTimeoutManagerCancel:
    """Tests for cancel timeout."""

    def test_register_cancel_timeout(self) -> None:
        """Test registering CANCEL timeout."""
        now = 1000.0
        config = TimeoutConfig(cancel_timeout_s=10.0)
        mgr = TimeoutManager(config=config)

        entry = mgr.register_cancel_timeout("order1", now=now)

        assert entry.local_id == "order1"
        assert entry.timeout_type == TimeoutType.CANCEL
        assert entry.deadline == now + 10.0


class TestTimeoutManagerOperations:
    """Tests for TimeoutManager operations."""

    def test_cancel_timeout(self) -> None:
        """Test canceling a timeout."""
        now = 1000.0
        mgr = TimeoutManager()

        mgr.register_ack_timeout("order1", now=now)
        assert len(mgr) == 1

        result = mgr.cancel_timeout("order1", TimeoutType.ACK)
        assert result is True
        assert len(mgr) == 0

    def test_cancel_nonexistent_timeout(self) -> None:
        """Test canceling non-existent timeout."""
        mgr = TimeoutManager()
        result = mgr.cancel_timeout("order1", TimeoutType.ACK)
        assert result is False

    def test_cancel_all_for_order(self) -> None:
        """Test canceling all timeouts for an order."""
        now = 1000.0
        mgr = TimeoutManager()

        mgr.register_ack_timeout("order1", now=now)
        mgr.register_fill_timeout("order1", now=now)
        mgr.register_cancel_timeout("order1", now=now)
        assert len(mgr) == 3

        count = mgr.cancel_all_for_order("order1")
        assert count == 3
        assert len(mgr) == 0

    def test_has_timeout(self) -> None:
        """Test checking if timeout exists."""
        now = 1000.0
        mgr = TimeoutManager()

        mgr.register_ack_timeout("order1", now=now)

        assert mgr.has_timeout("order1", TimeoutType.ACK)
        assert not mgr.has_timeout("order1", TimeoutType.FILL)
        assert not mgr.has_timeout("order2", TimeoutType.ACK)

    def test_get_entry(self) -> None:
        """Test getting timeout entry."""
        now = 1000.0
        mgr = TimeoutManager()

        mgr.register_ack_timeout("order1", now=now)

        entry = mgr.get_entry("order1", TimeoutType.ACK)
        assert entry is not None
        assert entry.local_id == "order1"

        entry = mgr.get_entry("order1", TimeoutType.FILL)
        assert entry is None

    def test_clear(self) -> None:
        """Test clearing all timeouts."""
        now = 1000.0
        mgr = TimeoutManager()

        mgr.register_ack_timeout("order1", now=now)
        mgr.register_fill_timeout("order2", now=now)
        assert len(mgr) == 2

        mgr.clear()
        assert len(mgr) == 0

    def test_multiple_orders_timeout(self) -> None:
        """Test multiple orders with timeouts."""
        now = 1000.0
        config = TimeoutConfig(ack_timeout_s=5.0)
        mgr = TimeoutManager(config=config)

        mgr.register_ack_timeout("order1", now=now)
        mgr.register_ack_timeout("order2", now=now + 2.0)
        mgr.register_ack_timeout("order3", now=now + 4.0)

        # Only order1 expired
        expired = mgr.check_expired(now + 6.0)
        assert len(expired) == 1
        assert expired[0].local_id == "order1"

        # order2 also expired
        expired = mgr.check_expired(now + 8.0)
        assert len(expired) == 1
        assert expired[0].local_id == "order2"

        # order3 expired
        expired = mgr.check_expired(now + 10.0)
        assert len(expired) == 1
        assert expired[0].local_id == "order3"
