import types
from typing import TYPE_CHECKING

import pytest

from src import runner
from src.execution.broker import Broker, OrderAck
from src.execution.flatten_plan import BookTop, PositionToClose
from src.execution.order_types import OrderIntent
from src.risk.state import AccountSnapshot
from src.strategy.base import Strategy
from src.strategy.types import MarketState, TargetPortfolio


class FakeBroker(Broker):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        return OrderAck(order_id=f"paper-{intent.symbol}")


class FakeStrategy(Strategy):
    def on_tick(self, state: MarketState) -> TargetPortfolio:
        return TargetPortfolio(model_version="v0", features_hash="hash", target_net_qty={})


def test_run_f21_paper_calls_risk_then_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    call_order: list[str] = []

    def fake_handle_risk_update(**kwargs: object) -> types.SimpleNamespace:
        call_order.append("risk")
        return types.SimpleNamespace(correlation_id="cid", events=[], execution_records=[])

    def fake_handle_trading_tick(**kwargs: object) -> types.SimpleNamespace:
        call_order.append("trade")
        return types.SimpleNamespace(
            correlation_id="cid",
            events=[],
            target_portfolio=None,
            clamped_portfolio=None,
        )

    monkeypatch.setenv("TRADE_MODE", "PAPER")
    monkeypatch.setattr(runner, "handle_risk_update", fake_handle_risk_update)
    monkeypatch.setattr(runner, "handle_trading_tick", fake_handle_trading_tick)

    tick = runner.LiveTickData(
        snap=AccountSnapshot(equity=100_000, margin_used=0),
        positions=[PositionToClose(symbol="AU", net_qty=0, today_qty=0, yesterday_qty=0)],
        books={"AU": BookTop(best_bid=10.0, best_ask=10.2, tick=0.2)},
        bars_1m={"AU": []},
        now_ts=0.0,
    )

    def fake_fetch_tick() -> runner.LiveTickData:
        return tick

    def fake_broker_factory(
        settings: runner.AppSettings,
    ) -> Broker:  # should not import CTP in PAPER
        return FakeBroker()

    def fake_strategy_factory(settings: runner.AppSettings) -> Strategy:
        return FakeStrategy()

    runner.run_f21(
        broker_factory=fake_broker_factory,
        strategy_factory=fake_strategy_factory,
        fetch_tick=fake_fetch_tick,
        run_forever=False,
    )

    assert call_order == ["risk", "trade"]
