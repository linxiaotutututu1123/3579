from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict


class Bar1m(TypedDict):
    """1-minute OHLCV bar."""

    ts: float  # epoch seconds, minute-aligned
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketState:
    """Snapshot of market state for strategy consumption."""

    prices: Mapping[str, float]  # mid/last prices
    equity: float
    bars_1m: Mapping[str, Sequence[Bar1m]]  # oldest -> newest


@dataclass(frozen=True)
class TargetPortfolio:
    """Strategy output: target net positions."""

    target_net_qty: Mapping[str, int]
    model_version: str
    features_hash: str
