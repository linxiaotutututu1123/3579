"""Paper-trading executable entrypoint.

This module is intended for packaging (e.g., PyInstaller) on Windows.
It should not change runtime behavior of the existing application.

Behavior:
- Ensures TRADE_MODE defaults to PAPER when not already set.
- Delegates execution to src.runner.run_f21().

Uses broker_factory from F20 for automatic PAPER/LIVE broker selection.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.config import AppSettings
from src.execution.broker_factory import broker_factory
from src.runner import LiveTickData
from src.strategy.factory import build_strategy

if TYPE_CHECKING:
    from src.strategy.base import Strategy


def _strategy_factory(settings: AppSettings) -> Strategy:
    """Build strategy from settings."""
    return build_strategy(settings.strategy_name, settings.strategy_symbols)


def _missing_fetch_tick() -> LiveTickData:
    """Placeholder for tick fetcher - can use replay or simulated data."""
    raise RuntimeError(
        "fetch_tick not implemented. "
        "Implement a tick source (e.g., replay data) for paper trading."
    )


def main() -> None:
    os.environ.setdefault("TRADE_MODE", "PAPER")

    try:
        from src.runner import run_f21
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "F21 entrypoint not available. Implement src.runner.run_f21() first."
        ) from e

    if not callable(run_f21):
        raise RuntimeError("Implement src.runner.run_f21() first.")

    # broker_factory (from F20) returns NoopBroker for PAPER mode
    run_f21(
        broker_factory=broker_factory,
        strategy_factory=_strategy_factory,
        fetch_tick=_missing_fetch_tick,
        run_forever=True,
    )


if __name__ == "__main__":
    main()
