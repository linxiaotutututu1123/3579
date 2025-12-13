from __future__ import annotations

from src.execution.broker import Broker, OrderAck
from src.execution.order_types import Offset, OrderIntent, Side
from src.runner import init_components


class NoopBroker(Broker):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        return OrderAck(order_id="noop")


def test_init_components_builds_objects() -> None:
    comps = init_components(broker=NoopBroker())
    assert comps.risk is not None
    assert comps.flatten is not None
    assert comps.settings is not None