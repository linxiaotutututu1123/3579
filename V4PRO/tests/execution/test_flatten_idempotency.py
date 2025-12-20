from __future__ import annotations

from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


def test_flatten_runs_only_once_per_day_even_if_called_twice() -> None:
    """Test that try_start_flatten returns True only once per day."""
    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 1.0,
    )
    snap = AccountSnapshot(equity=1_000_000.0, margin_used=0.0)
    rm.on_day_start_0900(snap, correlation_id="baseline")
    rm.pop_events()

    # First call should succeed
    assert rm.try_start_flatten(correlation_id="first") is True
    events1 = rm.pop_events()
    assert any(e.type == RiskEventType.FLATTEN_STARTED for e in events1)

    # Second call while in progress should be skipped
    assert rm.try_start_flatten(correlation_id="second") is False
    events2 = rm.pop_events()
    assert any(
        e.type == RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS for e in events2
    )

    # Mark flatten done
    rm.mark_flatten_done(correlation_id="done")
    rm.pop_events()

    # Third call after completion should also be skipped
    assert rm.try_start_flatten(correlation_id="third") is False
    events3 = rm.pop_events()
    assert any(
        e.type == RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS for e in events3
    )
