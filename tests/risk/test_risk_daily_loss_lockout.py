from __future__ import annotations

from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode


def test_daily_loss_lockout_flow() -> None:
    """
    Test the full daily loss lockout flow:
    1. First breach -> COOLDOWN, cancel/flatten called once
    2. After cooldown -> RECOVERY
    3. Second breach -> LOCKED, cancel/flatten NOT called again
    """
    calls = {"cancel": 0, "flatten": 0}
    now = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    cfg = RiskConfig(dd_limit=-0.03, cooldown_seconds=90 * 60)
    rm = RiskManager(
        cfg,
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )

    rm.on_day_start_0900(
        AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid"
    )
    assert rm.state.mode.value == RiskMode.NORMAL.value
    assert rm.state.kill_switch_fired_today is False

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0), correlation_id="cid")
    assert rm.state.mode.value == RiskMode.COOLDOWN.value
    assert rm.state.kill_switch_fired_today is True
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1

    events = rm.pop_events()
    kill_events = [e for e in events if e.type == RiskEventType.KILL_SWITCH_FIRED]
    assert len(kill_events) == 1

    now["t"] = 90 * 60 + 1
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0), correlation_id="cid")
    assert rm.state.mode.value == RiskMode.RECOVERY.value

    events = rm.pop_events()
    recovery_events = [e for e in events if e.type == RiskEventType.ENTER_RECOVERY]
    assert len(recovery_events) == 1

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0), correlation_id="cid")
    assert rm.state.mode.value == RiskMode.LOCKED.value
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1

    events = rm.pop_events()
    locked_events = [e for e in events if e.type == RiskEventType.LOCKED_FOR_DAY]
    assert len(locked_events) == 1


def test_callbacks_only_called_once_on_first_breach() -> None:
    """Verify cancel/flatten callbacks are only called on first breach."""
    calls = {"cancel": 0, "flatten": 0}
    now = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    cfg = RiskConfig(dd_limit=-0.03, cooldown_seconds=1)
    rm = RiskManager(
        cfg,
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )

    rm.on_day_start_0900(
        AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid"
    )

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0), correlation_id="cid")
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1

    now["t"] = 2
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0), correlation_id="cid")
    assert rm.state.mode.value == RiskMode.RECOVERY.value

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0), correlation_id="cid")
    assert rm.state.mode.value == RiskMode.LOCKED.value
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1
