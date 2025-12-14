"""Paper-trading executable entrypoint.

This module is intended for packaging (e.g., PyInstaller) on Windows.
It should not change runtime behavior of the existing application.

Behavior:
- Ensures TRADE_MODE defaults to PAPER when not already set.
- Delegates execution to src.runner.run_f21().

If run_f21 is not implemented yet, raises a clear RuntimeError.
"""

from __future__ import annotations

import os

from src.execution.broker import Broker
from src.runner import LiveTickData


def _missing_broker_factory(*_: object, **__: object) -> Broker:
    raise RuntimeError("broker_factory not wired for PAPER entrypoint yet.")


def _missing_strategy_factory(*_: object, **__: object):
    raise RuntimeError("strategy_factory not wired for PAPER entrypoint yet.")


def _missing_fetch_tick() -> LiveTickData:
    raise RuntimeError("fetch_tick not wired for PAPER entrypoint yet.")


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

    run_f21(
        broker_factory=_missing_broker_factory,
        strategy_factory=_missing_strategy_factory,
        fetch_tick=_missing_fetch_tick,
        run_forever=False,
    )


if __name__ == "__main__":
    main()
