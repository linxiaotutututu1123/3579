from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from src.execution.broker import Broker, CloseTodayRejected, OrderAck, OrderRejected
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
    # SELL => more aggressive is LOWER price; BUY => higher price
    if reference.side == Side.SELL:
        return candidate.price < reference.price
    return candidate.price > reference.price


def _find_next_more_aggressive_close(
    intents: list[OrderIntent],
    *,
    start_index: int,
    reference: OrderIntent,
) -> int | None:
    """
    Find the next intent after start_index that:
    - matches symbol, side, qty
    - has Offset.CLOSE
    - is more aggressive than reference (price moved in aggressive direction)
    """
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
    def __init__(self, broker: Broker) -> None:
        self._broker = broker

    def execute(self, intents: Iterable[OrderIntent]) -> list[ExecutionRecord]:
        """
        Execute flatten intents sequentially. This executor is dumb on purpose:
        - tries intents in order
        - on CloseTodayRejected: jump to the next MORE aggressive CLOSE intent
        - records every attempt
        """
        intents_list = list(intents)
        records: list[ExecutionRecord] = []

        i = 0
        while i < len(intents_list):
            intent = intents_list[i]
            try:
                ack: OrderAck = self._broker.place_order(intent)
                records.append(
                    ExecutionRecord(
                        intent=intent,
                        ok=True,
                        order_id=ack.order_id,
                        note="placed",
                    )
                )
                # In real trading you'd stop once filled; here we only model attempt log.
                i += 1
            except CloseTodayRejected as e:
                records.append(
                    ExecutionRecord(
                        intent=intent,
                        ok=False,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        note="closetoday_rejected",
                    )
                )

                if intent.offset == Offset.CLOSETODAY:
                    j = _find_next_more_aggressive_close(
                        intents_list, start_index=i, reference=intent
                    )
                    if j is not None:
                        i = j
                        continue

                i += 1
            except OrderRejected as e:
                records.append(
                    ExecutionRecord(
                        intent=intent,
                        ok=False,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        note="rejected",
                    )
                )
                i += 1

        return records