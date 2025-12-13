from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.execution.flatten_executor import ExecutionRecord, FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose, build_flatten_intents
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot


@dataclass(frozen=True)
class OrchestratorResult:
    risk_events: list[RiskEvent]
    execution_records: list[ExecutionRecord]
    correlation_id: str
    snapshot_hash: str


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_snapshot(
    *,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
    # if you want: include risk cfg knobs too
) -> str:
    pos_data = [
        {
            "symbol": p.symbol,
            "net_qty": p.net_qty,
            "today_qty": p.today_qty,
            "yesterday_qty": p.yesterday_qty,
        }
        for p in sorted(positions, key=lambda x: x.symbol)
    ]
    book_data = {
        k: {"best_bid": v.best_bid, "best_ask": v.best_ask, "tick": v.tick}
        for k, v in sorted(books.items(), key=lambda kv: kv[0])
    }
    payload = {
        "snap": {"equity": snap.equity, "margin_used": snap.margin_used},
        "positions": pos_data,
        "books": book_data,
    }
    raw = _stable_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def handle_risk_update(
    *,
    risk: RiskManager,
    executor: FlattenExecutor,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
    flatten_spec: FlattenSpec | None = None,
) -> OrchestratorResult:
    correlation_id = uuid.uuid4().hex
    snapshot_hash = _hash_snapshot(snap=snap, positions=positions, books=books)

    risk.update(snap)
    raw_risk_events = risk.pop_events()

    # Attach correlation_id and prepend snapshot audit event.
    ts = raw_risk_events[0].ts if raw_risk_events else executor._now()  # type: ignore[attr-defined]
    risk_events: list[RiskEvent] = [
        RiskEvent(
            type=RiskEventType.AUDIT_SNAPSHOT,
            ts=ts,
            correlation_id=correlation_id,
            data={"snapshot_hash": snapshot_hash},
        )
    ]
    risk_events.extend(
        RiskEvent(type=e.type, ts=e.ts, correlation_id=correlation_id, data=e.data)
        for e in raw_risk_events
    )

    exec_records: list[ExecutionRecord] = []

    fired = any(e.type == RiskEventType.KILL_SWITCH_FIRED for e in raw_risk_events)
    if fired:
        spec = flatten_spec or FlattenSpec()
        for pos in positions:
            book = books.get(pos.symbol)
            if book is None:
                continue
            intents = build_flatten_intents(pos=pos, book=book, spec=spec)
            exec_records.extend(executor.execute(intents, correlation_id=correlation_id))

    return OrchestratorResult(
        risk_events=risk_events,
        execution_records=exec_records,
        correlation_id=correlation_id,
        snapshot_hash=snapshot_hash,
    )
