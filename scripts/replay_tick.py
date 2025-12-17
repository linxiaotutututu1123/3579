from __future__ import annotations

import json
import sys
from pathlib import Path

from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.replay.runner import FaultConfig, run_replay_tick
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/replay_tick.py <payload.json>")
        return 2

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    snap = AccountSnapshot(**payload["snap"])
    positions = [PositionToClose(**p) for p in payload["positions"]]
    books = {k: BookTop(**v) for k, v in payload["books"].items()}
    flatten_spec = (
        FlattenSpec(**payload["flatten_spec"]) if "flatten_spec" in payload else None
    )

    fault_data = payload.get("fault", {})
    fault = FaultConfig(
        missing_book_symbols=set(fault_data.get("missing_book_symbols", [])) or None,
        reject_all=bool(fault_data.get("reject_all", False)),
    )

    rm = RiskManager(
        RiskConfig(**payload.get("risk_config", {})),
        cancel_all_cb=lambda: None,
        force_flatten_all_cb=lambda: None,
        now_cb=lambda: 0.0,
    )

    if payload.get("baseline"):
        rm.on_day_start_0900(
            AccountSnapshot(**payload["baseline"]), correlation_id="replay-baseline"
        )
        rm.pop_events()

    res = run_replay_tick(
        risk=rm,
        snap=snap,
        positions=positions,
        books=books,
        flatten_spec=flatten_spec,
        fault=fault,
        now_ts=float(payload.get("now_ts", 0.0)),
        max_rejections=int(payload.get("max_rejections", 10)),
    )

    print("correlation_id:", res.correlation_id)
    print("snapshot_hash:", res.snapshot_hash)
    print("events:")
    for e in res.events:
        print(" ", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
