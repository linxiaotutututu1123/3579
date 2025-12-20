"""Live-trading executable entrypoint.

This module is intended for packaging (e.g., PyInstaller) on Windows.
It should not change runtime behavior of the existing application.

Behavior:
- Ensures TRADE_MODE defaults to LIVE when not already set.
- Validates required CTP environment variables are present.
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


_REQUIRED_CTP_ENV_VARS = (
    "CTP_FRONT_ADDR",
    "CTP_BROKER_ID",
    "CTP_USER_ID",
    "CTP_PASSWORD",
)


def _strategy_factory(settings: AppSettings) -> Strategy:
    """Build strategy from settings."""
    return build_strategy(settings)


def _missing_fetch_tick() -> LiveTickData:
    """Placeholder for live tick fetcher - must be implemented for real trading."""
    raise RuntimeError(
        "fetch_tick not implemented. "
        "Implement a live tick source (e.g., CTP market data) to enable trading."
    )


def _validate_ctp_env() -> None:
    missing = [k for k in _REQUIRED_CTP_ENV_VARS if not os.environ.get(k)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Missing required CTP environment variables for LIVE mode: "
            f"{joined}. Set them before running 3579-live."
        )


def main() -> None:
    os.environ.setdefault("TRADE_MODE", "LIVE")

    try:
        from src.runner import run_f21
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "F21 entrypoint not available. Implement src.runner.run_f21() first."
        ) from e

    if not callable(run_f21):
        raise TypeError("Implement src.runner.run_f21() first.")

    # broker_factory (from F20) handles LIVE CTP validation internally
    # when it detects TRADE_MODE=LIVE and calls validate_ctp_env()
    run_f21(
        broker_factory=broker_factory,
        strategy_factory=_strategy_factory,
        fetch_tick=_missing_fetch_tick,
        run_forever=True,
    )


if __name__ == "__main__":
    main()
