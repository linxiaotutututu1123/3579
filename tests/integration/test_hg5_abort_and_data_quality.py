from __future__ import annotations

from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import handle_risk_update
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


class AlwaysRejectBroker(Broker):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        raise OrderRejected("no")


def test_abort_after_too_many_rejections_and_emit_missing_book() -> None:
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 1.0,
    )
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    rm.on_day_start_0900(snap, correlation_id="baseline")
    rm.pop_events()

    exe = FlattenExecutor(AlwaysRejectBroker(), now_cb=lambda: 2.0)

    res = handle_risk_update(
        risk=rm,
        executor=exe,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[
            # MISS first (no book) -> DATA_QUALITY_MISSING_BOOK
            PositionToClose(symbol="MISS", net_qty=1, today_qty=1, yesterday_qty=0),
            # AO second (has book, will be rejected) -> FLATTEN_ABORTED_TOO_MANY_REJECTIONS
            PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0),
        ],
        books={
            "AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0),
        },
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        now_cb=lambda: 3.0,
        max_rejections=1,
    )

    risk_events = [e for e in res.events if isinstance(e, RiskEvent)]
    has_missing_book = any(
        e.type == RiskEventType.DATA_QUALITY_MISSING_BOOK and e.data["symbol"] == "MISS"
        for e in risk_events
    )
    assert has_missing_book
    assert any(
        e.type == RiskEventType.FLATTEN_ABORTED_TOO_MANY_REJECTIONS for e in risk_events
    )
