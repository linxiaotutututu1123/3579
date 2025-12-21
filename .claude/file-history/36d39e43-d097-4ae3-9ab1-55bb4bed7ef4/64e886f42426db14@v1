from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from src.strategy.base import Strategy
from src.strategy.types import MarketState, TargetPortfolio


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class SimpleAIStrategy(Strategy):
    """Simple placeholder strategy for pipeline testing."""

    def __init__(self, symbols: Sequence[str]) -> None:
        self._symbols = list(symbols)

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        features: dict[str, float] = {}
        target_net_qty: dict[str, int] = {}

        for sym in self._symbols:
            price = state.prices.get(sym, 0.0)
            features[sym] = price
            target_net_qty[sym] = 1 if price > 0 else 0

        features_hash = hashlib.sha256(_stable_json(features).encode()).hexdigest()

        return TargetPortfolio(
            target_net_qty=target_net_qty,
            model_version="simple-ai-v1",
            features_hash=features_hash,
        )
