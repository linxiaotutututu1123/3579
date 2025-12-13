from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from src.execution.broker import Broker
from src.execution.flatten_executor import ExecutionRecord, FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose, build_flatten_intents
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot


@dataclass(frozen=True)
class OrchestratorResult:
    risk_events: list[RiskEvent]
    execution_records: list[ExecutionRecord]


def handle_risk_update(
    *,
    risk: RiskManager,
    executor: FlattenExecutor,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
    flatten_spec: FlattenSpec | None = None,
) -> OrchestratorResult:
    """
    Glue code:
    - update risk state
    - drain risk events
    - if kill switch fired, generate flatten intents for each position and execute
    """
    risk.update(snap)
    risk_events = risk.drain_events()

    exec_records: list[ExecutionRecord] = []

    fired = any(e.type == RiskEventType.KILL_SWITCH_FIRED for e in risk_events)
    if fired:
        spec = flatten_spec or FlattenSpec()
        for pos in positions:
            book = books.get(pos.symbol)
            if book is None:
                # no market data => skip (future: alert)
                continue
            intents = build_flatten_intents(pos=pos, book=book, spec=spec)
            exec_records.extend(executor.execute(intents))

    return OrchestratorResult(risk_events=risk_events, execution_records=exec_records)
