"""
Tests for PositionTracker.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- POS.TRACKER.TRADE_DRIVEN
- POS.RECONCILE.PERIODIC
- POS.RECONCILE.AFTER_DISCONNECT
- POS.RECONCILE.FAIL_ACTION
"""


from src.execution.auto.position_tracker import (
    Position,
    PositionTracker,
    ReconcileResult,
    ReconcileStatus,
    Trade,
)


class TestPosition:
    """Tests for Position dataclass."""

    def test_position_creation(self) -> None:
        """Test Position creation."""
        pos = Position(symbol="IF2401")
        assert pos.symbol == "IF2401"
        assert pos.long_qty == 0
        assert pos.short_qty == 0
        assert pos.net_qty == 0

    def test_position_net_qty(self) -> None:
        """Test net_qty calculation."""
        pos = Position(symbol="IF2401", long_qty=10, short_qty=3)
        assert pos.net_qty == 7

        pos = Position(symbol="IF2401", long_qty=3, short_qty=10)
        assert pos.net_qty == -7

    def test_position_to_dict(self) -> None:
        """Test Position to_dict."""
        pos = Position(symbol="IF2401", long_qty=10, short_qty=3)
        d = pos.to_dict()
        assert d["symbol"] == "IF2401"
        assert d["long_qty"] == 10
        assert d["short_qty"] == 3
        assert d["net_qty"] == 7


class TestTrade:
    """Tests for Trade dataclass."""

    def test_trade_creation(self) -> None:
        """Test Trade creation."""
        trade = Trade(
            trade_id="trade1",
            order_local_id="order1",
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            volume=5,
            price=4000.0,
        )
        assert trade.trade_id == "trade1"
        assert trade.symbol == "IF2401"
        assert trade.direction == "BUY"
        assert trade.offset == "OPEN"
        assert trade.volume == 5
        assert trade.price == 4000.0


class TestPositionTrackerTradeDriven:
    """Tests for POS.TRACKER.TRADE_DRIVEN scenario."""

    def test_buy_open_increases_long(self) -> None:
        """Test BUY + OPEN increases long position."""
        tracker = PositionTracker()
        trade = Trade(
            trade_id="t1",
            order_local_id="o1",
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            volume=10,
            price=4000.0,
        )

        tracker.on_trade(trade)

        pos = tracker.get_position("IF2401")
        assert pos is not None
        assert pos.long_qty == 10
        assert pos.short_qty == 0
        assert pos.net_qty == 10
        assert pos.long_avg_cost == 4000.0

    def test_sell_open_increases_short(self) -> None:
        """Test SELL + OPEN increases short position."""
        tracker = PositionTracker()
        trade = Trade(
            trade_id="t1",
            order_local_id="o1",
            symbol="IF2401",
            direction="SELL",
            offset="OPEN",
            volume=5,
            price=4100.0,
        )

        tracker.on_trade(trade)

        pos = tracker.get_position("IF2401")
        assert pos is not None
        assert pos.long_qty == 0
        assert pos.short_qty == 5
        assert pos.net_qty == -5
        assert pos.short_avg_cost == 4100.0

    def test_sell_close_decreases_long(self) -> None:
        """Test SELL + CLOSE decreases long position."""
        tracker = PositionTracker()

        # First buy open
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        # Then sell close
        tracker.on_trade(Trade("t2", "o2", "IF2401", "SELL", "CLOSE", 3, 4050.0))

        pos = tracker.get_position("IF2401")
        assert pos.long_qty == 7
        assert pos.net_qty == 7

    def test_buy_close_decreases_short(self) -> None:
        """Test BUY + CLOSE decreases short position."""
        tracker = PositionTracker()

        # First sell open
        tracker.on_trade(Trade("t1", "o1", "IF2401", "SELL", "OPEN", 10, 4100.0))

        # Then buy close
        tracker.on_trade(Trade("t2", "o2", "IF2401", "BUY", "CLOSE", 4, 4050.0))

        pos = tracker.get_position("IF2401")
        assert pos.short_qty == 6
        assert pos.net_qty == -6

    def test_avg_cost_calculation(self) -> None:
        """Test average cost calculation."""
        tracker = PositionTracker()

        # Buy 10 at 4000
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        # Buy 10 more at 4100
        tracker.on_trade(Trade("t2", "o2", "IF2401", "BUY", "OPEN", 10, 4100.0))

        pos = tracker.get_position("IF2401")
        assert pos.long_qty == 20
        assert pos.long_avg_cost == 4050.0  # (10*4000 + 10*4100) / 20


class TestPositionTrackerReconcile:
    """Tests for reconciliation scenarios."""

    def test_reconcile_match(self) -> None:
        """Test POS.RECONCILE.PERIODIC: positions match."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        tracker.on_trade(Trade("t2", "o2", "IF2402", "SELL", "OPEN", 5, 4100.0))

        broker_positions = {"IF2401": 10, "IF2402": -5}
        result = tracker.reconcile(broker_positions)

        assert result.status == ReconcileStatus.MATCH
        assert result.is_match()
        assert len(result.mismatches) == 0

    def test_reconcile_mismatch(self) -> None:
        """Test POS.RECONCILE.PERIODIC: positions mismatch."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        broker_positions = {"IF2401": 8}  # Broker says 8, we have 10
        result = tracker.reconcile(broker_positions)

        assert result.status == ReconcileStatus.MISMATCH
        assert not result.is_match()
        assert len(result.mismatches) == 1
        assert result.mismatches[0] == ("IF2401", 10, 8)

    def test_reconcile_extra_broker_position(self) -> None:
        """Test reconcile with extra position at broker."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        broker_positions = {"IF2401": 10, "IF2402": 5}  # We don't have IF2402
        result = tracker.reconcile(broker_positions)

        assert result.status == ReconcileStatus.MISMATCH
        assert len(result.mismatches) == 1
        assert result.mismatches[0] == ("IF2402", 0, 5)

    def test_reconcile_callback_on_mismatch(self) -> None:
        """Test POS.RECONCILE.FAIL_ACTION: callback on mismatch."""
        callbacks = []

        def on_mismatch(result: ReconcileResult) -> None:
            callbacks.append(result)

        tracker = PositionTracker(on_mismatch=on_mismatch)
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        broker_positions = {"IF2401": 8}
        tracker.reconcile(broker_positions)

        assert len(callbacks) == 1
        assert callbacks[0].status == ReconcileStatus.MISMATCH

    def test_sync_from_broker(self) -> None:
        """Test POS.RECONCILE.FAIL_ACTION: sync from broker."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        # Sync to broker's view
        broker_positions = {"IF2401": 8, "IF2402": -3}
        tracker.sync_from_broker(broker_positions)

        # Now local matches broker
        assert tracker.get_net_position("IF2401") == 8
        assert tracker.get_net_position("IF2402") == -3

    def test_sync_from_broker_clears_existing(self) -> None:
        """Test sync_from_broker clears existing positions."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        tracker.on_trade(Trade("t2", "o2", "IF2403", "SELL", "OPEN", 5, 4000.0))

        # Sync to broker's view (doesn't include IF2403)
        broker_positions = {"IF2401": 10}
        tracker.sync_from_broker(broker_positions)

        assert tracker.get_net_position("IF2401") == 10
        assert tracker.get_net_position("IF2403") == 0  # Cleared


class TestPositionTrackerPeriodic:
    """Tests for periodic reconciliation."""

    def test_should_reconcile(self) -> None:
        """Test POS.RECONCILE.PERIODIC: check if should reconcile."""
        tracker = PositionTracker()

        # Initially should reconcile (last_reconcile = 0)
        assert tracker.should_reconcile(interval_s=60.0, now=1000.0)

        # After reconcile
        tracker.reconcile({})
        tracker._last_reconcile = 1000.0

        # Not enough time passed
        assert not tracker.should_reconcile(interval_s=60.0, now=1030.0)

        # Enough time passed
        assert tracker.should_reconcile(interval_s=60.0, now=1070.0)


class TestPositionTrackerOperations:
    """Tests for PositionTracker operations."""

    def test_get_all_positions(self) -> None:
        """Test getting all positions."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        tracker.on_trade(Trade("t2", "o2", "IF2402", "SELL", "OPEN", 5, 4100.0))

        positions = tracker.get_all_positions()
        assert len(positions) == 2
        assert "IF2401" in positions
        assert "IF2402" in positions

    def test_get_net_positions(self) -> None:
        """Test getting net positions."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        tracker.on_trade(Trade("t2", "o2", "IF2402", "SELL", "OPEN", 5, 4100.0))

        net = tracker.get_net_positions()
        assert net == {"IF2401": 10, "IF2402": -5}

    def test_clear(self) -> None:
        """Test clearing positions."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        assert len(tracker) == 1

        tracker.clear()
        assert len(tracker) == 0

    def test_trade_count(self) -> None:
        """Test trade count."""
        tracker = PositionTracker()
        assert tracker.trade_count == 0

        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))
        assert tracker.trade_count == 1

        tracker.on_trade(Trade("t2", "o2", "IF2401", "BUY", "OPEN", 5, 4050.0))
        assert tracker.trade_count == 2

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        tracker = PositionTracker()
        tracker.on_trade(Trade("t1", "o1", "IF2401", "BUY", "OPEN", 10, 4000.0))

        d = tracker.to_dict()
        assert "positions" in d
        assert "net_positions" in d
        assert "trade_count" in d
