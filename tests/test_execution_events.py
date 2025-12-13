from __future__ import annotations

from src.execution.broker import Broker, CloseTodayRejected, OrderAck
from src.execution.events import ExecutionEventType
from src.execution.flatten_executor import FlattenExecutor
from src.execution.order_types import Offset, OrderIntent, Side


class ScriptedBroker(Broker):
    def __init__(self, behaviors: list[object]) -> None:
        self.behaviors = behaviors
        self.i = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        b = self.behaviors[self.i]
        self.i += 1
        if isinstance(b, Exception):
            raise b
        assert isinstance(b, OrderAck)
        return b


def test_executor_emits_events_and_drain_clears() -> None:
    now = {"t": 100.0}

    def now_cb() -> float:
        now["t"] += 1.0
        return now["t"]

    intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSETODAY, price=100.0, qty=1),
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=99.0, qty=1),
    ]

    broker = ScriptedBroker([CloseTodayRejected("no CT"), OrderAck("ok-1")])
    exe = FlattenExecutor(broker, now_cb=now_cb)

    exe.execute(intents)
    ev = exe.drain_events()

    assert [e.type for e in ev] == [
        ExecutionEventType.ORDER_REJECTED,
        ExecutionEventType.ORDER_PLACED,
    ]

    ev2 = exe.drain_events()
    assert ev2 == []
