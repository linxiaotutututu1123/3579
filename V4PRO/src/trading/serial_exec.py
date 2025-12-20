from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from src.execution.events import ExecutionEvent, ExecutionEventType
from src.execution.flatten_executor import FlattenExecutor
from src.execution.order_types import OrderIntent
from src.trading.events import TradingEvent, TradingEventType


def execute_close_then_open(
    *,
    executor: FlattenExecutor,
    close_intents: Sequence[OrderIntent],
    open_intents: Sequence[OrderIntent],
    correlation_id: str,
    now_cb: Callable[[], float] = time.time,
) -> tuple[list[TradingEvent], list[ExecutionEvent]]:
    """
    Execute close orders first, then open orders.

    If any close order is rejected, skip all open orders.

    Returns:
        (trading_events, execution_events)
    """
    trading_events: list[TradingEvent] = []
    all_exec_events: list[ExecutionEvent] = []

    trading_events.append(
        TradingEvent(
            type=TradingEventType.EXEC_BATCH_STARTED,
            ts=now_cb(),
            correlation_id=correlation_id,
            data={"close_count": len(close_intents), "open_count": len(open_intents)},
        )
    )

    if close_intents:
        executor.execute(close_intents, correlation_id=correlation_id)
        close_events = executor.drain_events()
        all_exec_events.extend(close_events)

        has_rejection = any(
            e.type == ExecutionEventType.ORDER_REJECTED for e in close_events
        )

        if has_rejection:
            trading_events.append(
                TradingEvent(
                    type=TradingEventType.OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE,
                    ts=now_cb(),
                    correlation_id=correlation_id,
                    data={"skipped_open_count": len(open_intents)},
                )
            )
            trading_events.append(
                TradingEvent(
                    type=TradingEventType.EXEC_BATCH_FINISHED,
                    ts=now_cb(),
                    correlation_id=correlation_id,
                    data={
                        "close_executed": True,
                        "open_executed": False,
                        "open_skipped": True,
                    },
                )
            )
            return trading_events, all_exec_events

    if open_intents:
        executor.execute(open_intents, correlation_id=correlation_id)
        open_events = executor.drain_events()
        all_exec_events.extend(open_events)

    trading_events.append(
        TradingEvent(
            type=TradingEventType.EXEC_BATCH_FINISHED,
            ts=now_cb(),
            correlation_id=correlation_id,
            data={
                "close_executed": bool(close_intents),
                "open_executed": bool(open_intents),
                "open_skipped": False,
            },
        )
    )

    return trading_events, all_exec_events
