from __future__ import annotations

from src.execution.broker import Broker, CloseTodayRejected, OrderAck, OrderRejected
from src.execution.flatten_executor import FlattenExecutor
from src.execution.order_types import Offset, OrderIntent, Side


class DummyBroker(Broker):
    def __init__(self, behaviors: list[object]) -> None:
        # behaviors: each call consumes one:
        # - OrderAck => success
        # - Exception => raise
        self._it = iter(behaviors)
        self.seen: list[OrderIntent] = []

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self.seen.append(intent)
        b = next(self._it)
        if isinstance(b, Exception):
            raise b
        assert isinstance(b, OrderAck)
        return b


def test_closetoday_rejected_jumps_to_more_aggressive_close() -> None:
    # intents are ordered from less aggressive to more aggressive:
    # i0: CLOSETODAY @100 (reject with CloseTodayRejected)
    # i1: CLOSE     @100 (should be skipped; not more aggressive)
    # i2: CLOSE     @99  (more aggressive; should be jumped to and succeed)
    intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSETODAY, price=100.0, qty=2),
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100.0, qty=2),
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=99.0, qty=2),
    ]

    broker = DummyBroker([CloseTodayRejected("no CT"), OrderAck("ok-1")])
    exe = FlattenExecutor(broker)

    records = exe.execute(intents)

    # We attempted intent0 then jumped directly to intent2; intent1 should not be tried.
    assert [r.intent.price for r in records] == [100.0, 99.0]
    assert broker.seen[0].offset == Offset.CLOSETODAY
    assert broker.seen[1].offset == Offset.CLOSE

    assert records[0].ok is False
    assert records[0].note == "closetoday_rejected"
    assert records[1].ok is True


def test_generic_reject_does_not_jump() -> None:
    intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSETODAY, price=100.0, qty=2),
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=99.0, qty=2),
    ]
    broker = DummyBroker([OrderRejected("no"), OrderAck("ok-2")])
    exe = FlattenExecutor(broker)

    records = exe.execute(intents)

    # doesn't jump; just proceeds sequentially
    assert [r.intent.price for r in records] == [100.0, 99.0]
    assert records[0].ok is False
    assert records[1].ok is True


def test_closetoday_rejected_without_more_aggressive_close_falls_through() -> None:
    intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSETODAY, price=100.0, qty=2),
        # only CLOSE at same price => not more aggressive => no jump destination
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100.0, qty=2),
    ]
    broker = DummyBroker([CloseTodayRejected("no CT"), OrderAck("ok-3")])
    exe = FlattenExecutor(broker)

    records = exe.execute(intents)

    # falls through sequentially to next (even though not more aggressive)
    assert [r.intent.price for r in records] == [100.0, 100.0]
    assert broker.seen[1].offset == Offset.CLOSE
