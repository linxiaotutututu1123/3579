from __future__ import annotations

from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode


def test_events_baseline_kill_switch_recovery() -> None:
    calls = {"cancel": 0, "flatten": 0}
    now = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )

    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    ev = rm.pop_events()
    assert [e.type for e in ev] == [RiskEventType.BASELINE_SET]

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.COOLDOWN
    ev = rm.pop_events()
    assert [e.type for e in ev] == [RiskEventType.KILL_SWITCH_FIRED]
    assert calls["cancel"] == 1 and calls["flatten"] == 1

    now["t"] = 11
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.RECOVERY  # type: ignore[comparison-overlap]
    ev = rm.pop_events()
    assert [e.type for e in ev] == [RiskEventType.ENTER_RECOVERY]


def test_events_locked_for_day_on_second_breach() -> None:
    now = {"t": 0.0}

    def now_cb() -> float:
        return now["t"]

    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=1),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=now_cb,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    rm.pop_events()

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    rm.pop_events()

    now["t"] = 2
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0))
    rm.pop_events()

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.LOCKED
    ev = rm.pop_events()
    assert [e.type for e in ev] == [RiskEventType.LOCKED_FOR_DAY]
