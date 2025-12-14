from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import OrchestratorResult, handle_risk_update
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot

if TYPE_CHECKING:
    from src.strategy.base import Strategy
    from src.strategy.types import Bar1m
    from src.trading.orchestrator import TradingTickResult


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


def run_replay_tick_mode2(
    *,
    risk: RiskManager,
    snap: AccountSnapshot,
    books: Mapping[str, BookTop],
    bars_1m: Mapping[str, Sequence[Bar1m]],
    strategy: Strategy,
    current_net_qty: Mapping[str, int],
    fault: FaultConfig | None = None,
    now_ts: float = 0.0,
    correlation_id: str | None = None,
) -> TradingTickResult:
    """
    Run a single tick replay for Mode 2 (trading pipeline).

    Replay always uses PAPER mode to prevent accidental order placement.

    Args:
        risk: RiskManager instance
        snap: Current account snapshot
        books: Order book data for mid price calculation
        bars_1m: 1-minute bar data for strategy (oldest to newest)
        strategy: Strategy instance
        current_net_qty: Current net positions
        fault: Optional fault injection config
        now_ts: Timestamp for this tick
        correlation_id: Optional correlation ID for tracing

    Returns:
        TradingTickResult with all events and portfolio info
    """
    from src.trading.controls import TradeControls, TradeMode
    from src.trading.orchestrator import handle_trading_tick

    fault = fault or FaultConfig()

    # Select broker based on fault config
    broker: Broker = RejectAllBroker() if fault.reject_all else NoopBroker()
    executor = FlattenExecutor(broker, now_cb=lambda: now_ts)

    # Calculate mid prices from books
    prices: dict[str, float] = {}
    for sym, book in books.items():
        if fault.missing_book_symbols and sym in fault.missing_book_symbols:
            continue
        prices[sym] = (book.best_bid + book.best_ask) / 2.0

    # Always use PAPER mode in replay to prevent accidental orders
    controls = TradeControls(mode=TradeMode.PAPER)

    return handle_trading_tick(
        strategy=strategy,
        risk=risk,
        executor=executor,
        controls=controls,
        snap=snap,
        prices=prices,
        bars_1m=bars_1m,
        current_net_qty=current_net_qty,
        correlation_id=correlation_id,
        now_cb=lambda: now_ts,
    )
