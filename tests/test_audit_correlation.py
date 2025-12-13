from __future__ import annotations

from src.execution.broker import Broker, OrderAck
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import handle_risk_update
from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


class NoopBroker(Broker):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        return OrderAck(order_id="oid-1")


def test_audit_snapshot_event_and_correlation_id_are_added() -> None:
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 0.0,
    )
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    snap2 = AccountSnapshot(equity=970_000.0, margin_used=0.0)
    rm.on_day_start_0900(snap, correlation_id="test")
    rm.update(snap2, correlation_id="test")
    exe = FlattenExecutor(NoopBroker(), now_cb=lambda: 123.0)

    res = handle_risk_update(
        risk=rm,
        executor=exe,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)],
        books={"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)},
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        now_cb=lambda: 999.0,
    )

    assert res.correlation_id != ""
    assert len(res.snapshot_hash) == 64  # sha256 hex

    # first event is always the audit snapshot
    assert res.risk_events[0].type == RiskEventType.AUDIT_SNAPSHOT
    assert res.risk_events[0].ts == 999.0
    assert res.risk_events[0].correlation_id == res.correlation_id
    assert res.risk_events[0].data["snapshot_hash"] == res.snapshot_hash

    # all risk events share the same correlation_id
    assert {e.correlation_id for e in res.risk_events} == {res.correlation_id}
