from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.execution.order_types import OrderIntent


class OrderRejected(Exception):
    """Generic order rejection."""


class CloseTodayRejected(OrderRejected):
    """Raised when exchange rejects CloseToday offset for this position/order."""


@dataclass(frozen=True)
class OrderAck:
    order_id: str


class Broker(Protocol):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        """Place an order described by intent. Raises OrderRejected subclasses on failure."""
        raise NotImplementedError
