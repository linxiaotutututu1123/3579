from __future__ import annotations

from src.execution.broker import Broker, OrderAck
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import handle_risk_update
from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


class CountingBroker(Broker):
    def __init__(self) -> None:
        self.calls = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self.calls += 1
        return OrderAck(order_id=f"oid-{self.calls}")


def test_flatten_runs_only_once_per_day_even_if_called_twice() -> None:
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 1.0,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="baseline")
    rm.pop_events()

    broker = CountingBroker()
    exe = FlattenExecutor(broker, now_cb=lambda: 2.0)

    kwargs = dict(
        risk=rm,
        executor=exe,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)],
        books={"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)},
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        now_cb=lambda: 3.0,
    )

    res1 = handle_risk_update(**kwargs)
    assert any(getattr(e, "type", None) == RiskEventType.FLATTEN_STARTED for e in res1.events)
    assert broker.calls >= 1

    calls_after_first = broker.calls

    res2 = handle_risk_update(**kwargs)
    # second call should skip flatten (already completed today)
    assert any(getattr(e, "type", None) == RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS for e in res2.events)
    assert broker.calls == calls_after_first