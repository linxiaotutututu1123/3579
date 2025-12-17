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


class NoopBroker(Broker):
    """Acknowledges orders without sending them (PAPER/testing)."""

    def __init__(self) -> None:
        self._counter = 0

    def place_order(
        self, intent: OrderIntent
    ) -> OrderAck:  # pragma: no cover - trivial
        self._counter += 1
        return OrderAck(order_id=f"noop-{self._counter}")
