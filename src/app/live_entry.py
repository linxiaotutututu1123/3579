"""Live-trading executable entrypoint.

This module is intended for packaging (e.g., PyInstaller) on Windows.
It should not change runtime behavior of the existing application.

Behavior:
- Ensures TRADE_MODE defaults to LIVE when not already set.
- Validates required CTP environment variables are present.
- Delegates execution to src.runner.run_f21().

If run_f21 is not implemented yet, raises a clear RuntimeError.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src.execution.broker import Broker
from src.runner import LiveTickData

if TYPE_CHECKING:
    from src.strategy.base import Strategy


_REQUIRED_CTP_ENV_VARS = (
    "CTP_FRONT_ADDR",
    "CTP_BROKER_ID",
    "CTP_USER_ID",
    "CTP_PASSWORD",
)


def _missing_broker_factory(*_: object, **__: object) -> Broker:
    raise RuntimeError("broker_factory not wired for LIVE entrypoint yet.")


def _missing_strategy_factory(*_: object, **__: object) -> "Strategy":
    raise RuntimeError("strategy_factory not wired for LIVE entrypoint yet.")


def _missing_fetch_tick() -> LiveTickData:
    raise RuntimeError("fetch_tick not wired for LIVE entrypoint yet.")


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
    _validate_ctp_env()

    try:
        from src.runner import run_f21
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "F21 entrypoint not available. Implement src.runner.run_f21() first."
        ) from e

    if not callable(run_f21):
        raise RuntimeError("Implement src.runner.run_f21() first.")

    run_f21(
        broker_factory=_missing_broker_factory,
        strategy_factory=_missing_strategy_factory,
        fetch_tick=_missing_fetch_tick,
        run_forever=False,
    )


if __name__ == "__main__":
    main()
