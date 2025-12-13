from __future__ import annotations

from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


def test_init_gate_blocks_open_until_baseline_set() -> None:
    def cancel_all() -> None:
        pass

    def flatten_all() -> None:
        pass

    rm = RiskManager(RiskConfig(), cancel_all_cb=cancel_all, force_flatten_all_cb=flatten_all)

    d = rm.can_open(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    assert d.allow_open is False
    assert d.reason == "blocked_by_init:no_baseline"

    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    d2 = rm.can_open(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    assert d2.allow_open is True
