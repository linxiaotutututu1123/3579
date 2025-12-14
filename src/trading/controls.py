from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TradeMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass
class TradeControls:
    mode: TradeMode = TradeMode.PAPER
