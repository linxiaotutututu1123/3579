from __future__ import annotations

from dataclasses import dataclass

from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.flatten_executor import FlattenExecutor
from src.execution.order_types import Offset, OrderIntent, Side
from src.trading.events import TradingEventType
from src.trading.serial_exec import execute_close_then_open


@dataclass
class OrderRecord:
    intent: OrderIntent
    order_id: str


class RecordingBroker(Broker):
    """Broker that records all orders placed."""

    def __init__(self) -> None:
        self.orders: list[OrderRecord] = []
        self._counter = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self._counter += 1
        order_id = f"order_{self._counter}"
        self.orders.append(OrderRecord(intent=intent, order_id=order_id))
        return OrderAck(order_id=order_id)


class RejectCloseBroker(Broker):
    """Broker that rejects all CLOSE orders."""

    def __init__(self) -> None:
        self.orders: list[OrderRecord] = []
        self._counter = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        if intent.offset == Offset.CLOSE:
            raise OrderRejected("Close order rejected")
        self._counter += 1
        order_id = f"order_{self._counter}"
        self.orders.append(OrderRecord(intent=intent, order_id=order_id))
        return OrderAck(order_id=order_id)


def test_close_orders_execute_before_open() -> None:
    """Verify close orders are executed before open orders."""
    broker = RecordingBroker()
    executor = FlattenExecutor(broker)

    close_intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100.0, qty=1),
    ]
    open_intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.OPEN, price=100.0, qty=2),
    ]

    trading_events, exec_events = execute_close_then_open(
        executor=executor,
        close_intents=close_intents,
        open_intents=open_intents,
        correlation_id="cid",
    )

    assert len(broker.orders) == 2
    assert broker.orders[0].intent.offset == Offset.CLOSE
    assert broker.orders[1].intent.offset == Offset.OPEN

    batch_finished = [e for e in trading_events if e.type == TradingEventType.EXEC_BATCH_FINISHED]
    assert len(batch_finished) == 1
    assert batch_finished[0].data["open_skipped"] is False


def test_close_rejection_skips_open_orders() -> None:
    """When close order is rejected, open orders should be skipped."""
    broker = RejectCloseBroker()
    executor = FlattenExecutor(broker)

    close_intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100.0, qty=1),
    ]
    open_intents = [
        OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.OPEN, price=100.0, qty=2),
    ]

    trading_events, exec_events = execute_close_then_open(
        executor=executor,
        close_intents=close_intents,
        open_intents=open_intents,
        correlation_id="cid",
    )

    assert len(broker.orders) == 0

    skip_events = [
        e for e in trading_events if e.type == TradingEventType.OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE
    ]
    assert len(skip_events) == 1
    assert skip_events[0].data["skipped_open_count"] == 1

    batch_finished = [e for e in trading_events if e.type == TradingEventType.EXEC_BATCH_FINISHED]
    assert len(batch_finished) == 1
    assert batch_finished[0].data["open_skipped"] is True


def test_empty_close_intents_executes_open() -> None:
    """When there are no close intents, open intents should execute."""
    broker = RecordingBroker()
    executor = FlattenExecutor(broker)

    close_intents: list[OrderIntent] = []
    open_intents = [
        OrderIntent(symbol="AO", side=Side.BUY, offset=Offset.OPEN, price=100.0, qty=1),
    ]

    trading_events, exec_events = execute_close_then_open(
        executor=executor,
        close_intents=close_intents,
        open_intents=open_intents,
        correlation_id="cid",
    )

    assert len(broker.orders) == 1
    assert broker.orders[0].intent.offset == Offset.OPEN
