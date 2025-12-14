from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.execution.events import ExecutionEvent
from src.execution.flatten_executor import ExecutionRecord, FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose, build_flatten_intents
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot

NowCb = Callable[[], float]
Event = RiskEvent | ExecutionEvent


@dataclass(frozen=True)
class OrchestratorResult:
    correlation_id: str
    snapshot_hash: str
    events: list[Event]
    execution_records: list[ExecutionRecord]


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_snapshot(
    *,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
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
        sym: {"best_bid": b.best_bid, "best_ask": b.best_ask, "tick": b.tick}
        for sym, b in sorted(books.items(), key=lambda kv: kv[0])
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
    now_cb: NowCb = time.time,
) -> OrchestratorResult:
    """
    Highest-grade tick handler:
    - generate correlation_id
    - compute snapshot hash
    - update risk (risk events are emitted at the source with correlation_id)
    - if kill switch fired: execute flatten with correlation_id, and collect execution events
    - return unified event stream (audit + risk + execution)
    """
    correlation_id = uuid.uuid4().hex
    snapshot_hash = _hash_snapshot(snap=snap, positions=positions, books=books)

    # Risk updates emit correlated events at the source (RiskManager is highest-grade already)
    risk.update(snap, correlation_id=correlation_id)
    risk_events = risk.pop_events()

    audit_event = RiskEvent(
        type=RiskEventType.AUDIT_SNAPSHOT,
        ts=now_cb(),
        correlation_id=correlation_id,
        data={"snapshot_hash": snapshot_hash},
    )

    exec_records: list[ExecutionRecord] = []
    exec_events: list[ExecutionEvent] = []

    fired = any(e.type == RiskEventType.KILL_SWITCH_FIRED for e in risk_events)
    if fired:
        spec = flatten_spec or FlattenSpec()
        for pos in positions:
            book = books.get(pos.symbol)
            if book is None:
                # Highest-grade next step: emit DataQuality event + alert.
                continue
            intents = build_flatten_intents(pos=pos, book=book, spec=spec)
            exec_records.extend(executor.execute(intents, correlation_id=correlation_id))

        exec_events = executor.drain_events()

    events: list[Event] = [audit_event, *risk_events, *exec_events]
    return OrchestratorResult(
        correlation_id=correlation_id,
        snapshot_hash=snapshot_hash,
        events=events,
        execution_records=exec_records,
    )