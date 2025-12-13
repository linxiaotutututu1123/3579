from __future__ import annotations

from src.risk.manager import Decision, RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode


def test_kill_switch_then_cooldown_then_recovery() -> None:
    calls: dict[str, int] = {"cancel": 0, "flatten": 0}
    now: dict[str, float] = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    cfg: RiskConfig = RiskConfig(dd_limit=-0.03, cooldown_seconds=90 * 60)
    rm: RiskManager = RiskManager(
        cfg=cfg,
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )

    rm.on_day_start_0900(
        snap=AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    )
    assert rm.state.mode == RiskMode.NORMAL

    rm.update(snap=AccountSnapshot(equity=969_000.0, margin_used=0.0))
    mode: RiskMode = rm.state.mode
    assert mode == RiskMode.COOLDOWN
    
    assert rm.state.kill_switch_fired_today is True
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1

    now["t"] = 60 * 60
    rm.update(snap=AccountSnapshot(equity=969_000.0, margin_used=0.0))
    mode2: RiskMode = rm.state.mode
    assert mode2 == RiskMode.COOLDOWN

    now["t"] = 90 * 60 + 1
    rm.update(snap=AccountSnapshot(equity=980_000.0, margin_used=0.0))
    mode3: RiskMode = rm.state.mode
    assert mode3 == RiskMode.RECOVERY


def test_second_breach_locks_for_day() -> None:
    calls: dict[str, int] = {"cancel": 0, "flatten": 0}
    now: dict[str, float] = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    rm: RiskManager = RiskManager(
        cfg=RiskConfig(dd_limit=-0.03, cooldown_seconds=1),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )
    rm.on_day_start_0900(snap=AccountSnapshot(equity=1_000_000.0, margin_used=0.0))

    rm.update(snap=AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.COOLDOWN
    assert calls["cancel"] == 1

    now["t"] = 2
    rm.update(snap=AccountSnapshot(equity=980_000.0, margin_used=0.0))
    mode2: RiskMode = rm.state.mode
    assert mode2 == RiskMode.RECOVERY
    rm.update(snap=AccountSnapshot(equity=969_000.0, margin_used=0.0))
    mode3: RiskMode = rm.state.mode
    assert mode3 == RiskMode.LOCKED
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1


def test_margin_gate_blocks_open_in_recovery() -> None:
    calls: dict[str, int] = {"cancel": 0, "flatten": 0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    rm: RiskManager = RiskManager(
        cfg=RiskConfig(max_margin_recovery=0.40),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
    )
    rm.on_day_start_0900(
        snap=AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    )

    rm.state.mode = RiskMode.RECOVERY
    snap: AccountSnapshot = AccountSnapshot(equity=1_000_000.0, margin_used=450_000.0)
    d: Decision = rm.can_open(snap=snap)
    assert d.allow_open is False
    assert d.reason == "blocked_by_margin_ratio"
