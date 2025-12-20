from __future__ import annotations

from src.portfolio.constraints import clamp_target
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode
from src.strategy.types import TargetPortfolio


def _make_risk_manager(mode: RiskMode = RiskMode.NORMAL) -> RiskManager:
    rm = RiskManager(
        RiskConfig(
            max_margin_normal=0.70,
            max_margin_recovery=0.50,
            recovery_risk_multiplier=0.30,
        ),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0), correlation_id="cid")
    rm.state.mode = mode
    return rm


def test_recovery_scales_target_by_multiplier() -> None:
    """In RECOVERY mode, target qty should be scaled by recovery_risk_multiplier (0.3)."""
    rm = _make_risk_manager(RiskMode.RECOVERY)
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0)

    target = TargetPortfolio(
        target_net_qty={"AO": 2, "SA": -2, "LC": 1},
        model_version="test",
        features_hash="abc",
    )

    clamped, audit = clamp_target(
        risk=rm,
        snap=snap,
        current_net_qty={"AO": 0, "SA": 0, "LC": 0},
        target=target,
    )

    assert "recovery_scaled" in audit
    assert clamped.target_net_qty["AO"] == 1
    assert clamped.target_net_qty["SA"] == -1
    assert clamped.target_net_qty["LC"] == 0


def test_margin_gate_blocks_add_but_allows_reduce() -> None:
    """When margin gate blocks, adding position is blocked but reducing is allowed."""
    rm = _make_risk_manager(RiskMode.NORMAL)
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=750_000.0)

    target = TargetPortfolio(
        target_net_qty={"AO": 2, "SA": 0},
        model_version="test",
        features_hash="abc",
    )

    clamped, audit = clamp_target(
        risk=rm,
        snap=snap,
        current_net_qty={"AO": 1, "SA": 1},
        target=target,
    )

    assert clamped.target_net_qty["AO"] == 1
    assert clamped.target_net_qty["SA"] == 0
    assert "margin_gate_blocked_add" in audit


def test_cooldown_blocks_all_trading() -> None:
    """In COOLDOWN mode, target should equal current (no trading)."""
    rm = _make_risk_manager(RiskMode.COOLDOWN)
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0)

    target = TargetPortfolio(
        target_net_qty={"AO": 2},
        model_version="test",
        features_hash="abc",
    )

    clamped, audit = clamp_target(
        risk=rm,
        snap=snap,
        current_net_qty={"AO": 1},
        target=target,
    )

    assert clamped.target_net_qty["AO"] == 1
    assert audit.get("blocked_by_mode") == "COOLDOWN"


def test_locked_blocks_all_trading() -> None:
    """In LOCKED mode, target should equal current (no trading)."""
    rm = _make_risk_manager(RiskMode.LOCKED)
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=100_000.0)

    target = TargetPortfolio(
        target_net_qty={"AO": 2},
        model_version="test",
        features_hash="abc",
    )

    clamped, audit = clamp_target(
        risk=rm,
        snap=snap,
        current_net_qty={"AO": 1},
        target=target,
    )

    assert clamped.target_net_qty["AO"] == 1
    assert audit.get("blocked_by_mode") == "LOCKED"
