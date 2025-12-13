from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

from src.execution.broker import Broker, CloseTodayRejected, OrderAck, OrderRejected
from src.execution.events import ExecutionEvent, ExecutionEventType
from src.execution.order_types import Offset, OrderIntent, Side


@dataclass(frozen=True)
class ExecutionRecord:
    intent: OrderIntent
    ok: bool
    order_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    note: str = ""


def _is_more_aggressive(reference: OrderIntent, candidate: OrderIntent) -> bool:
    if reference.side != candidate.side:
        return False
    if reference.side == Side.SELL:
        return candidate.price < reference.price
    return candidate.price > reference.price


def _find_next_more_aggressive_close(
    intents: list[OrderIntent],
    *,
    start_index: int,
    reference: OrderIntent,
) -> int | None:
    for j in range(start_index + 1, len(intents)):
        cand = intents[j]
        if cand.symbol != reference.symbol:
            continue
        if cand.side != reference.side:
            continue
        if cand.qty != reference.qty:
            continue
        if cand.offset != Offset.CLOSE:
            continue
        if _is_more_aggressive(reference, cand):
            return j
    return None


class FlattenExecutor:
    def __init__(self, broker: Broker, *, now_cb=time.time) -> None:
        self._broker = broker
        self._now = now_cb
        self._events: list[ExecutionEvent] = []

    def drain_events(self) -> list[ExecutionEvent]:
        ev = self._events[:]
        self._events.clear()
        return ev

    def execute(self, intents: Iterable[OrderIntent], *, correlation_id: str = "") -> list[ExecutionRecord]:
        intents_list = list(intents)
        records: list[ExecutionRecord] = []

        i = 0
        while i < len(intents_list):
            intent = intents_list[i]
            ts = self._now()
            try:
                ack: OrderAck = self._broker.place_order(intent)
                rec = ExecutionRecord(intent=intent, ok=True, order_id=ack.order_id, note="placed")
                records.append(rec)
                self._events.append(
                    ExecutionEvent(
                        type=ExecutionEventType.ORDER_PLACED,
                        ts=ts,
                        correlation_id=correlation_id,
                        symbol=intent.symbol,
                        side=intent.side.value,
                        offset=intent.offset.value,
                        price=float(intent.price),
                        qty=int(intent.qty),
                        order_id=ack.order_id,
                        note=rec.note,
                    )
                )
                i += 1
            except CloseTodayRejected as e:
                rec = ExecutionRecord(
                    intent=intent,
                    ok=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    note="closetoday_rejected",
                )
                records.append(rec)
                self._events.append(
                    ExecutionEvent(
                        type=ExecutionEventType.ORDER_REJECTED,
                        ts=ts,
                        correlation_id=correlation_id,
                        symbol=intent.symbol,
                        side=intent.side.value,
                        offset=intent.offset.value,
                        price=float(intent.price),
                        qty=int(intent.qty),
                        error_type=rec.error_type,
                        error_message=rec.error_message,
                        note=rec.note,
                    )
                )

                if intent.offset == Offset.CLOSETODAY:
                    j = _find_next_more_aggressive_close(intents_list, start_index=i, reference=intent)
                    if j is not None:
                        i = j
                        continue
                i += 1
            except OrderRejected as e:
                rec = ExecutionRecord(
                    intent=intent,
                    ok=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    note="rejected",
                )
                records.append(rec)
                self._events.append(
                    ExecutionEvent(
                        type=ExecutionEventType.ORDER_REJECTED,
                        ts=ts,
                        correlation_id=correlation_id,
                        symbol=intent.symbol,
                        side=intent.side.value,
                        offset=intent.offset.value,
                        price=float(intent.price),
                        qty=int(intent.qty),
                        error_type=rec.error_type,
                        error_message=rec.error_message,
                        note=rec.note,
                    )
                )
                i += 1

        return records