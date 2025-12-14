from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import OrchestratorResult, handle_risk_update
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot


@dataclass(frozen=True)
class FaultConfig:
    """Fault injection configuration for replay."""

    missing_book_symbols: set[str] | None = None
    reject_all: bool = False


class RejectAllBroker(Broker):
    """Broker that rejects all orders (for fault injection)."""

    def place_order(self, intent: OrderIntent) -> OrderAck:
        raise OrderRejected(f"fault-injection: reject_all for {intent.symbol}")


class NoopBroker(Broker):
    """Broker that accepts all orders (for replay without real broker)."""

    def __init__(self) -> None:
        self._counter = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self._counter += 1
        return OrderAck(order_id=f"replay-{self._counter}")


def run_replay_tick(
    *,
    risk: RiskManager,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
    flatten_spec: FlattenSpec | None = None,
    fault: FaultConfig | None = None,
    now_ts: float = 0.0,
    max_rejections: int = 10,
) -> OrchestratorResult:
    """
    Run a single tick replay with optional fault injection.

    This function is deterministic: given the same inputs, it produces
    the same snapshot_hash and event sequence (modulo correlation_id).
    """
    fault = fault or FaultConfig()

    # Apply fault: missing_book_symbols
    effective_books: dict[str, BookTop] = {}
    for sym, book in books.items():
        if fault.missing_book_symbols and sym in fault.missing_book_symbols:
            continue
        effective_books[sym] = book

    # Select broker based on fault config
    broker: Broker = RejectAllBroker() if fault.reject_all else NoopBroker()

    executor = FlattenExecutor(broker, now_cb=lambda: now_ts)

    return handle_risk_update(
        risk=risk,
        executor=executor,
        snap=snap,
        positions=positions,
        books=effective_books,
        flatten_spec=flatten_spec,
        now_cb=lambda: now_ts,
        max_rejections=max_rejections,
    )
