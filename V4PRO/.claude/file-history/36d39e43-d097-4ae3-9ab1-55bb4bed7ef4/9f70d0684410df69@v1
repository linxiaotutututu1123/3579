from __future__ import annotations

from dataclasses import dataclass

from src.execution.broker import Broker, OrderAck
from src.execution.flatten_executor import FlattenExecutor
from src.execution.order_types import OrderIntent
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig
from src.strategy.simple_ai import SimpleAIStrategy
from src.trading.controls import TradeControls, TradeMode
from src.trading.events import TradingEventType
from src.trading.orchestrator import handle_trading_tick


@dataclass
class OrderRecord:
    intent: OrderIntent
    order_id: str


class CountingBroker(Broker):
    """Broker that counts orders placed."""

    def __init__(self) -> None:
        self.order_count = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self.order_count += 1
        return OrderAck(order_id=f"order_{self.order_count}")


def test_paper_mode_does_not_place_orders() -> None:
    """In PAPER mode, no orders should be placed via broker."""
    broker = CountingBroker()
    executor = FlattenExecutor(broker)

    rm = RiskManager(
        RiskConfig(),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid")

    strategy = SimpleAIStrategy(symbols=["AO", "SA", "LC"])
    controls = TradeControls(mode=TradeMode.PAPER)

    result = handle_trading_tick(
        strategy=strategy,
        risk=rm,
        executor=executor,
        controls=controls,
        snap=AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0),
        prices={"AO": 100.0, "SA": 200.0, "LC": 150.0},
        bars_1m={"AO": [], "SA": [], "LC": []},
        current_net_qty={"AO": 0, "SA": 0, "LC": 0},
    )

    assert broker.order_count == 0

    event_types = [e.type for e in result.events if hasattr(e, "type")]
    assert TradingEventType.SIGNAL_GENERATED in event_types
    assert TradingEventType.TARGET_PORTFOLIO_SET in event_types
    assert TradingEventType.ORDERS_INTENDED in event_types

    assert TradingEventType.ORDERS_SENT not in event_types


def test_paper_mode_returns_target_portfolio() -> None:
    """PAPER mode should return target and clamped portfolios."""
    broker = CountingBroker()
    executor = FlattenExecutor(broker)

    rm = RiskManager(
        RiskConfig(),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid")

    strategy = SimpleAIStrategy(symbols=["AO"])
    controls = TradeControls(mode=TradeMode.PAPER)

    result = handle_trading_tick(
        strategy=strategy,
        risk=rm,
        executor=executor,
        controls=controls,
        snap=AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0),
        prices={"AO": 100.0},
        bars_1m={"AO": []},
        current_net_qty={"AO": 0},
    )

    assert result.target_portfolio is not None
    assert result.clamped_portfolio is not None
    assert "AO" in result.target_portfolio.target_net_qty


def test_correlation_id_propagates() -> None:
    """Correlation ID should propagate through all events."""
    broker = CountingBroker()
    executor = FlattenExecutor(broker)

    rm = RiskManager(
        RiskConfig(),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid")

    strategy = SimpleAIStrategy(symbols=["AO"])
    controls = TradeControls(mode=TradeMode.PAPER)

    result = handle_trading_tick(
        strategy=strategy,
        risk=rm,
        executor=executor,
        controls=controls,
        snap=AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0),
        prices={"AO": 100.0},
        bars_1m={"AO": []},
        current_net_qty={"AO": 0},
        correlation_id="test_cid_123",
    )

    assert result.correlation_id == "test_cid_123"

    for event in result.events:
        assert event.correlation_id == "test_cid_123"
