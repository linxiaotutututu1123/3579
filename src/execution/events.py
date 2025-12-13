from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionEventType(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_REJECTED = "ORDER_REJECTED"


@dataclass(frozen=True)
class ExecutionEvent:
    type: ExecutionEventType
    ts: float
    symbol: str
    side: str
    offset: str
    price: float
    qty: int
    order_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    note: str = ""
