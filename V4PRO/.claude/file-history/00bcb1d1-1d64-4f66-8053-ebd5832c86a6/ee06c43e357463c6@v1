from __future__ import annotations

from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.replay.runner import run_replay_tick
from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


def _make_risk_manager() -> RiskManager:
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 1.0,
    )
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    rm.on_day_start_0900(snap, correlation_id="baseline")
    rm.pop_events()
    return rm


def test_replay_is_deterministic_for_same_payload() -> None:
    """Given same payload, replay produces identical snapshot_hash."""
    snap = AccountSnapshot(equity=969_000.0, margin_used=0.0)
    positions = [PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)]
    books = {"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)}
    flatten_spec = FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0)

    rm1 = _make_risk_manager()
    r1 = run_replay_tick(
        risk=rm1,
        snap=snap,
        positions=positions,
        books=books,
        flatten_spec=flatten_spec,
        now_ts=123.0,
    )

    rm2 = _make_risk_manager()
    r2 = run_replay_tick(
        risk=rm2,
        snap=snap,
        positions=positions,
        books=books,
        flatten_spec=flatten_spec,
        now_ts=123.0,
    )

    assert r1.snapshot_hash == r2.snapshot_hash


def test_audit_snapshot_contains_correct_hash() -> None:
    """AUDIT_SNAPSHOT event contains snapshot_hash matching result."""
    rm = _make_risk_manager()

    res = run_replay_tick(
        risk=rm,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)],
        books={"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)},
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        now_ts=123.0,
    )

    audit_events = [e for e in res.events if e.type == RiskEventType.AUDIT_SNAPSHOT]
    assert len(audit_events) == 1
    assert audit_events[0].data["snapshot_hash"] == res.snapshot_hash
