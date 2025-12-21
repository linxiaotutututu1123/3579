from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskMode
from src.strategy.types import TargetPortfolio


def clamp_target(
    *,
    risk: RiskManager,
    snap: AccountSnapshot,
    current_net_qty: Mapping[str, int],
    target: TargetPortfolio,
    max_abs_qty_per_symbol: int = 2,
    max_turnover_qty_per_tick: int = 2,
) -> tuple[TargetPortfolio, dict[str, Any]]:
    """
    Apply risk constraints to target portfolio.

    Returns:
        (clamped_target, audit_dict)
    """
    audit: dict[str, Any] = {}
    mode = risk.state.mode

    if mode in (RiskMode.COOLDOWN, RiskMode.LOCKED):
        audit["blocked_by_mode"] = mode.value
        return TargetPortfolio(
            target_net_qty=dict(current_net_qty),
            model_version=target.model_version,
            features_hash=target.features_hash,
        ), audit

    clamped_qty: dict[str, int] = {}
    symbols = set(target.target_net_qty.keys()) | set(current_net_qty.keys())

    for sym in sorted(symbols):
        tgt = target.target_net_qty.get(sym, 0)
        cur = current_net_qty.get(sym, 0)

        if mode == RiskMode.RECOVERY:
            tgt = int(round(tgt * risk.cfg.recovery_risk_multiplier))
            audit.setdefault("recovery_scaled", {})[sym] = tgt

        tgt = max(-max_abs_qty_per_symbol, min(max_abs_qty_per_symbol, tgt))

        delta = tgt - cur
        if abs(delta) > max_turnover_qty_per_tick:
            direction = 1 if delta > 0 else -1
            tgt = cur + direction * max_turnover_qty_per_tick
            audit.setdefault("turnover_clamped", {})[sym] = tgt

        decision = risk.can_open(snap)
        is_adding = (cur >= 0 and tgt > cur) or (cur <= 0 and tgt < cur)
        if not decision.allow_open and abs(tgt) > abs(cur) and is_adding:
            tgt = cur
            audit.setdefault("margin_gate_blocked_add", {})[sym] = True

        clamped_qty[sym] = tgt

    return TargetPortfolio(
        target_net_qty=clamped_qty,
        model_version=target.model_version,
        features_hash=target.features_hash,
    ), audit
