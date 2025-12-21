"""Tests for order execution tracker."""

from __future__ import annotations

from src.execution.order_tracker import (
    OrderExecutionTracker,
    OrderState,
    OrderTrack,
)


class TestOrderTrack:
    """Tests for OrderTrack dataclass."""

    def test_remaining_qty(self) -> None:
        """remaining_qty calculated correctly."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=10,
            price=100.0,
            filled_qty=3,
        )
        assert track.remaining_qty == 7

    def test_is_terminal_filled(self) -> None:
        """FILLED is terminal."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=1,
            price=100.0,
            state=OrderState.FILLED,
        )
        assert track.is_terminal is True

    def test_is_terminal_submitted(self) -> None:
        """SUBMITTED is not terminal."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=1,
            price=100.0,
            state=OrderState.SUBMITTED,
        )
        assert track.is_terminal is False

    def test_fill_ratio(self) -> None:
        """fill_ratio calculated correctly."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=10,
            price=100.0,
            filled_qty=5,
        )
        assert track.fill_ratio == 0.5

    def test_fill_ratio_zero_qty(self) -> None:
        """fill_ratio handles zero quantity."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=0,
            price=100.0,
        )
        assert track.fill_ratio == 0.0

    def test_to_dict(self) -> None:
        """to_dict returns complete dictionary."""
        track = OrderTrack(
            order_id="O1",
            symbol="AO",
            side="BUY",
            qty=10,
            price=100.0,
        )
        d = track.to_dict()
        assert d["order_id"] == "O1"
        assert d["symbol"] == "AO"
        assert d["state"] == "PENDING"


class TestOrderExecutionTracker:
    """Tests for OrderExecutionTracker."""

    def test_create_order(self) -> None:
        """create_order adds order to tracker."""
        tracker = OrderExecutionTracker()
        track = tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        assert track.order_id == "O1"
        assert tracker.total_orders == 1

    def test_get_order(self) -> None:
        """get_order retrieves order by ID."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        track = tracker.get_order("O1")
        assert track is not None
        assert track.symbol == "AO"

    def test_get_order_not_found(self) -> None:
        """get_order returns None for unknown ID."""
        tracker = OrderExecutionTracker()
        assert tracker.get_order("UNKNOWN") is None

    def test_update_state(self) -> None:
        """update_state changes order state."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 10, 100.0)
        track = tracker.update_state("O1", OrderState.SUBMITTED)
        assert track is not None
        assert track.state == OrderState.SUBMITTED

    def test_update_state_with_fill(self) -> None:
        """update_state updates fill information."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 10, 100.0)
        track = tracker.update_state(
            "O1",
            OrderState.PARTIAL_FILL,
            filled_qty=5,
            avg_fill_price=99.5,
        )
        assert track is not None
        assert track.filled_qty == 5
        assert track.avg_fill_price == 99.5

    def test_update_state_not_found(self) -> None:
        """update_state returns None for unknown order."""
        tracker = OrderExecutionTracker()
        result = tracker.update_state("UNKNOWN", OrderState.FILLED)
        assert result is None

    def test_get_active_orders(self) -> None:
        """get_active_orders filters terminal orders."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        tracker.create_order("O2", "SA", "SELL", 1, 50.0)
        tracker.update_state("O2", OrderState.FILLED)
        active = tracker.get_active_orders()
        assert len(active) == 1
        assert active[0].order_id == "O1"

    def test_get_orders_by_symbol(self) -> None:
        """get_orders_by_symbol filters by symbol."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        tracker.create_order("O2", "SA", "SELL", 1, 50.0)
        tracker.create_order("O3", "AO", "SELL", 1, 101.0)
        ao_orders = tracker.get_orders_by_symbol("AO")
        assert len(ao_orders) == 2

    def test_clear_terminal_orders(self) -> None:
        """clear_terminal_orders removes completed orders."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        tracker.create_order("O2", "SA", "SELL", 1, 50.0)
        tracker.update_state("O2", OrderState.FILLED)
        removed = tracker.clear_terminal_orders()
        assert removed == 1
        assert tracker.total_orders == 1

    def test_active_count(self) -> None:
        """active_count returns non-terminal order count."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 1, 100.0)
        tracker.create_order("O2", "SA", "SELL", 1, 50.0)
        tracker.update_state("O2", OrderState.CANCELLED)
        assert tracker.active_count == 1
