from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TradingEventType(str, Enum):
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    TARGET_PORTFOLIO_SET = "TARGET_PORTFOLIO_SET"
    TARGET_PORTFOLIO_CLAMPED = "TARGET_PORTFOLIO_CLAMPED"
    ORDERS_INTENDED = "ORDERS_INTENDED"
    ORDERS_SENT = "ORDERS_SENT"
    EXEC_BATCH_STARTED = "EXEC_BATCH_STARTED"
    EXEC_BATCH_FINISHED = "EXEC_BATCH_FINISHED"
    OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE = "OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE"


@dataclass(frozen=True)
class TradingEvent:
    type: TradingEventType
    ts: float
    correlation_id: str
    data: dict[str, Any]
