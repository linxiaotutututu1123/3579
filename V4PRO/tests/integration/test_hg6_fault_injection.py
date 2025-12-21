from __future__ import annotations

from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.replay.runner import FaultConfig, run_replay_tick
from src.risk.events import RiskEvent, RiskEventType
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


def test_fault_injection_missing_book() -> None:
    """missing_book_symbols fault produces DATA_QUALITY_MISSING_BOOK event."""
    rm = _make_risk_manager()

    res = run_replay_tick(
        risk=rm,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[
            PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0),
            PositionToClose(symbol="MISS", net_qty=1, today_qty=1, yesterday_qty=0),
        ],
        books={
            "AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0),
            "MISS": BookTop(best_bid=1.0, best_ask=2.0, tick=1.0),
        },
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        fault=FaultConfig(missing_book_symbols={"MISS"}),
        now_ts=123.0,
    )

    risk_events = [e for e in res.events if isinstance(e, RiskEvent)]
    has_missing = any(
        e.type == RiskEventType.DATA_QUALITY_MISSING_BOOK and e.data["symbol"] == "MISS"
        for e in risk_events
    )
    assert has_missing


def test_fault_injection_reject_all() -> None:
    """reject_all fault produces FLATTEN_ABORTED_TOO_MANY_REJECTIONS event."""
    rm = _make_risk_manager()

    res = run_replay_tick(
        risk=rm,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[
            PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0)
        ],
        books={"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)},
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        fault=FaultConfig(reject_all=True),
        now_ts=123.0,
        max_rejections=1,
    )

    risk_events = [e for e in res.events if isinstance(e, RiskEvent)]
    has_abort = any(
        e.type == RiskEventType.FLATTEN_ABORTED_TOO_MANY_REJECTIONS for e in risk_events
    )
    assert has_abort


def test_fault_injection_combined() -> None:
    """Combined faults: missing_book + reject_all both trigger their events."""
    rm = _make_risk_manager()

    res = run_replay_tick(
        risk=rm,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),
        positions=[
            PositionToClose(symbol="MISS", net_qty=1, today_qty=1, yesterday_qty=0),
            PositionToClose(symbol="AO", net_qty=1, today_qty=1, yesterday_qty=0),
        ],
        books={
            "AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0),
            "MISS": BookTop(best_bid=1.0, best_ask=2.0, tick=1.0),
        },
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
        fault=FaultConfig(missing_book_symbols={"MISS"}, reject_all=True),
        now_ts=123.0,
        max_rejections=1,
    )

    risk_events = [e for e in res.events if isinstance(e, RiskEvent)]

    has_missing = any(
        e.type == RiskEventType.DATA_QUALITY_MISSING_BOOK and e.data["symbol"] == "MISS"
        for e in risk_events
    )
    has_abort = any(
        e.type == RiskEventType.FLATTEN_ABORTED_TOO_MANY_REJECTIONS for e in risk_events
    )

    assert has_missing
    assert has_abort
