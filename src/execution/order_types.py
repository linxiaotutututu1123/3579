from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Offset(str, Enum):
    CLOSETODAY = "CLOSETODAY"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: Side
    offset: Offset
    price: float
    qty: int
    reason: str = ""