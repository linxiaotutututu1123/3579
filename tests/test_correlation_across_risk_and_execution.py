from __future__ import annotations

from src.execution.broker import Broker, OrderAck
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import handle_risk_update
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


class OkBroker(Broker):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        return OrderAck(order_id="ok-1")


def test_correlation_id_propagates_from_risk_to_execution_events() -> None:
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 1.0,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="baseline")
    rm.pop_events()

    exe = FlattenExecutor(OkBroker(), now_cb=lambda: 2.0)

    res = handle_risk_update(
        risk=rm,
        executor=exe,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)],
        books={"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)},
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        now_cb=lambda: 3.0,
    )

    # Must contain kill switch + at least one execution event, all sharing res.correlation_id
    assert any(isinstance(e, RiskEvent) and e.type == RiskEventType.KILL_SWITCH_FIRED for e in res.events)
    cids = {getattr(e, "correlation_id") for e in res.events}
    assert cids == {res.correlation_id}