"""Order execution tracker for monitoring order lifecycle.

Tracks order state transitions and provides execution metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OrderState(str, Enum):
    """Order lifecycle states."""

    PENDING = "PENDING"  # Order created, not yet sent
    SUBMITTED = "SUBMITTED"  # Sent to broker
    ACCEPTED = "ACCEPTED"  # Accepted by exchange
    PARTIAL_FILL = "PARTIAL_FILL"  # Partially filled
    FILLED = "FILLED"  # Fully filled
    CANCELLED = "CANCELLED"  # Cancelled
    REJECTED = "REJECTED"  # Rejected by broker/exchange
    EXPIRED = "EXPIRED"  # Order expired


@dataclass
class OrderTrack:
    """Tracking record for a single order."""

    order_id: str
    symbol: str
    side: str
    qty: int
    price: float
    state: OrderState = OrderState.PENDING
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error_message: str = ""

    @property
    def remaining_qty(self) -> int:
        """Quantity remaining to be filled."""
        return self.qty - self.filled_qty

    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.state in (
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
        )

    @property
    def fill_ratio(self) -> float:
        """Ratio of filled quantity to total quantity."""
        if self.qty == 0:
            return 0.0
        return self.filled_qty / self.qty

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "state": self.state.value,
            "filled_qty": self.filled_qty,
            "avg_fill_price": self.avg_fill_price,
            "remaining_qty": self.remaining_qty,
            "fill_ratio": self.fill_ratio,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
        }


class OrderExecutionTracker:
    """
    Tracks order execution lifecycle.

    Maintains order state and provides metrics.
    """

    def __init__(self) -> None:
        """Initialize tracker."""
        self._orders: dict[str, OrderTrack] = {}

    def create_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: int,
        price: float,
    ) -> OrderTrack:
        """
        Create and track a new order.

        Args:
            order_id: Unique order identifier
            symbol: Trading symbol
            side: BUY or SELL
            qty: Order quantity
            price: Order price

        Returns:
            OrderTrack instance
        """
        track = OrderTrack(
            order_id=order_id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
        )
        self._orders[order_id] = track
        logger.info("Order created: %s %s %d @ %.2f", symbol, side, qty, price)
        return track

    def update_state(
        self,
        order_id: str,
        new_state: OrderState,
        *,
        filled_qty: int | None = None,
        avg_fill_price: float | None = None,
        error_message: str = "",
    ) -> OrderTrack | None:
        """
        Update order state.

        Args:
            order_id: Order to update
            new_state: New order state
            filled_qty: Updated filled quantity
            avg_fill_price: Updated average fill price
            error_message: Error message if rejected

        Returns:
            Updated OrderTrack or None if not found
        """
        track = self._orders.get(order_id)
        if track is None:
            logger.warning("Order not found: %s", order_id)
            return None

        old_state = track.state
        track.state = new_state
        track.updated_at = time.time()

        if filled_qty is not None:
            track.filled_qty = filled_qty
        if avg_fill_price is not None:
            track.avg_fill_price = avg_fill_price
        if error_message:
            track.error_message = error_message

        logger.info(
            "Order %s: %s -> %s (filled=%d/%d)",
            order_id,
            old_state.value,
            new_state.value,
            track.filled_qty,
            track.qty,
        )
        return track

    def get_order(self, order_id: str) -> OrderTrack | None:
        """Get order by ID."""
        return self._orders.get(order_id)

    def get_active_orders(self) -> list[OrderTrack]:
        """Get all non-terminal orders."""
        return [o for o in self._orders.values() if not o.is_terminal]

    def get_orders_by_symbol(self, symbol: str) -> list[OrderTrack]:
        """Get all orders for a symbol."""
        return [o for o in self._orders.values() if o.symbol == symbol]

    def clear_terminal_orders(self) -> int:
        """Remove terminal orders from tracker. Returns count removed."""
        to_remove = [oid for oid, o in self._orders.items() if o.is_terminal]
        for oid in to_remove:
            del self._orders[oid]
        return len(to_remove)

    @property
    def total_orders(self) -> int:
        """Total number of tracked orders."""
        return len(self._orders)

    @property
    def active_count(self) -> int:
        """Number of active (non-terminal) orders."""
        return sum(1 for o in self._orders.values() if not o.is_terminal)
