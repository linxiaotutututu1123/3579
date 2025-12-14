from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from src.strategy.base import Strategy
from src.strategy.types import Bar1m, MarketState, TargetPortfolio
from src.trading.utils import stable_hash


# Default weights for linear combination of features
DEFAULT_WEIGHTS: dict[str, float] = {
    "mom_15": 0.8,
    "mom_60": 0.5,
    "vol_60": -0.7,  # Higher vol -> smaller position
    "range_60": -0.3,
    "vol_shock_60": 0.2,
}


class LinearAIStrategy(Strategy):
    """
    AI-style linear strategy without torch dependency.

    Uses weighted sum of hand-crafted features to generate trading signals.
    Deterministic and auditable via features_hash.
    """

    def __init__(
        self,
        symbols: Sequence[str],
        weights: Mapping[str, float] | None = None,
        window: int = 240,
        max_abs_qty_per_symbol: int = 2,
    ) -> None:
        self._symbols = list(symbols)
        self._weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)
        self._window = window
        self._max_abs_qty = max_abs_qty_per_symbol

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        all_features: dict[str, object] = {
            "weights": self._weights,
            "params": {"window": self._window, "max_abs_qty": self._max_abs_qty},
        }
        target_net_qty: dict[str, int] = {}

        for sym in self._symbols:
            bars = state.bars_1m.get(sym, [])
            features = self._compute_features(bars, sym)
            all_features[f"{sym}_features"] = features

            if features.get("insufficient_bars", False):
                target_net_qty[sym] = 0
                continue

            score = self._compute_score(features)
            qty = int(round(math.tanh(score) * self._max_abs_qty))
            qty = max(-self._max_abs_qty, min(self._max_abs_qty, qty))
            target_net_qty[sym] = qty

        features_hash = stable_hash(all_features)

        return TargetPortfolio(
            target_net_qty=target_net_qty,
            model_version="linear-ai-v1",
            features_hash=features_hash,
        )

    def _compute_features(self, bars: Sequence[Bar1m], symbol: str) -> dict[str, object]:
        """Compute features from bar data."""
        if len(bars) < self._window:
            return {"insufficient_bars": True, "symbol": symbol}

        closes = [float(b["close"]) for b in bars[-self._window :]]
        n = len(closes)

        # Momentum features (log returns over window)
        mom_15 = self._log_return(closes, 15) if n >= 15 else 0.0
        mom_60 = self._log_return(closes, 60) if n >= 60 else 0.0

        # Volatility (std of returns over window)
        vol_60 = self._rolling_vol(closes, 60) if n >= 60 else 0.0

        # Range (high-low / close)
        range_60 = self._rolling_range(bars[-60:]) if len(bars) >= 60 else 0.0

        # Vol shock (recent vol vs longer vol)
        vol_15 = self._rolling_vol(closes, 15) if n >= 15 else 0.0
        vol_shock_60 = (vol_15 / (vol_60 + 1e-8)) - 1.0 if vol_60 > 0 else 0.0

        return {
            "insufficient_bars": False,
            "symbol": symbol,
            "mom_15": mom_15,
            "mom_60": mom_60,
            "vol_60": vol_60,
            "range_60": range_60,
            "vol_shock_60": vol_shock_60,
        }

    def _compute_score(self, features: dict[str, object]) -> float:
        """Compute linear score from features and weights."""
        score = 0.0
        for name, weight in self._weights.items():
            val = features.get(name, 0.0)
            if isinstance(val, (int, float)):
                score += weight * float(val)
        return score

    def _log_return(self, closes: list[float], window: int) -> float:
        """Compute log return over window."""
        if len(closes) < window + 1:
            return 0.0
        old = closes[-(window + 1)]
        new = closes[-1]
        if old <= 0:
            return 0.0
        return math.log(new / old)

    def _rolling_vol(self, closes: list[float], window: int) -> float:
        """Compute rolling volatility (std of log returns)."""
        if len(closes) < window + 1:
            return 0.0
        returns = []
        for i in range(len(closes) - window, len(closes)):
            if closes[i - 1] > 0:
                returns.append(math.log(closes[i] / closes[i - 1]))
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(var)

    def _rolling_range(self, bars: Sequence[Bar1m]) -> float:
        """Compute average (high-low)/close over bars."""
        if not bars:
            return 0.0
        total = 0.0
        count = 0
        for b in bars:
            c = float(b["close"])
            if c > 0:
                h = float(b["high"])
                lo = float(b["low"])
                total += (h - lo) / c
                count += 1
        return total / count if count > 0 else 0.0
