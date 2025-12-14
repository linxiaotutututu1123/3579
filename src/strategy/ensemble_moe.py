from __future__ import annotations

import math
from collections.abc import Sequence

from src.strategy.base import Strategy
from src.strategy.types import Bar1m, MarketState, TargetPortfolio
from src.trading.utils import stable_hash


class EnsembleMoEStrategy(Strategy):
    """
    Mixture-of-Experts ensemble strategy combining multiple signal types.

    Experts:
    - Trend following (momentum-based)
    - Mean reversion (zscore-based)
    - Breakout (price vs rolling high/low)

    Gating weights are determined by regime features (trend strength, vol level).
    """

    def __init__(
        self,
        symbols: Sequence[str],
        window: int = 240,
        max_abs_qty_per_symbol: int = 2,
    ) -> None:
        self._symbols = list(symbols)
        self._window = window
        self._max_abs_qty = max_abs_qty_per_symbol

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        all_features: dict[str, object] = {
            "params": {"window": self._window, "max_abs_qty": self._max_abs_qty},
        }
        target_net_qty: dict[str, int] = {}

        for sym in self._symbols:
            bars = state.bars_1m.get(sym, [])

            if len(bars) < self._window:
                all_features[f"{sym}_insufficient"] = True
                target_net_qty[sym] = 0
                continue

            closes = [float(b["close"]) for b in bars[-self._window :]]

            # Expert signals
            trend_sig = self._trend_signal(closes)
            meanrev_sig = self._meanrev_signal(closes)
            breakout_sig = self._breakout_signal(bars[-self._window :])

            # Regime features for gating
            regime = self._compute_regime(closes)

            # Gating weights (deterministic)
            w_trend, w_mr, w_br = self._compute_gating(regime)

            # Fused signal
            final_signal = w_trend * trend_sig + w_mr * meanrev_sig + w_br * breakout_sig

            # Position sizing
            qty = int(round(math.tanh(final_signal) * self._max_abs_qty))
            qty = max(-self._max_abs_qty, min(self._max_abs_qty, qty))
            target_net_qty[sym] = qty

            all_features[f"{sym}_experts"] = {
                "trend": trend_sig,
                "meanrev": meanrev_sig,
                "breakout": breakout_sig,
            }
            all_features[f"{sym}_regime"] = regime
            all_features[f"{sym}_gating"] = {
                "w_trend": w_trend,
                "w_mr": w_mr,
                "w_br": w_br,
            }
            all_features[f"{sym}_final_signal"] = final_signal

        features_hash = stable_hash(all_features)

        return TargetPortfolio(
            target_net_qty=target_net_qty,
            model_version="moe-ensemble-v1",
            features_hash=features_hash,
        )

    def _trend_signal(self, closes: list[float]) -> float:
        """Fused momentum signal (15/60/240 windows, weighted)."""
        mom_15 = self._log_return(closes, 15)
        mom_60 = self._log_return(closes, 60)
        mom_240 = self._log_return(closes, min(240, len(closes) - 1))

        # Weighted average
        return 0.5 * mom_15 + 0.3 * mom_60 + 0.2 * mom_240

    def _meanrev_signal(self, closes: list[float]) -> float:
        """Mean reversion signal based on zscore of recent returns."""
        if len(closes) < 60:
            return 0.0

        # Rolling mean and std
        window = min(60, len(closes))
        recent = closes[-window:]
        mean_price = sum(recent) / len(recent)
        variance = sum((p - mean_price) ** 2 for p in recent) / len(recent)
        std_price = math.sqrt(variance) if variance > 0 else 1e-8

        # Zscore of current price vs mean
        zscore = (closes[-1] - mean_price) / std_price

        # Mean reversion: negative zscore -> buy, positive -> sell
        return -zscore * 0.5

    def _breakout_signal(self, bars: Sequence[Bar1m]) -> float:
        """Breakout signal based on price position relative to rolling high/low."""
        if len(bars) < 20:
            return 0.0

        highs = [float(b["high"]) for b in bars[-60:]]
        lows = [float(b["low"]) for b in bars[-60:]]
        closes = [float(b["close"]) for b in bars[-60:]]

        rolling_high = max(highs)
        rolling_low = min(lows)
        current = closes[-1]

        if rolling_high == rolling_low:
            return 0.0

        # Position in range [0, 1]
        position = (current - rolling_low) / (rolling_high - rolling_low)

        # Breakout: near high -> bullish, near low -> bearish
        return (position - 0.5) * 2.0

    def _compute_regime(self, closes: list[float]) -> dict[str, float]:
        """Compute regime features for gating."""
        mom_60 = abs(self._log_return(closes, 60))
        vol_60 = self._rolling_vol(closes, 60)
        vol_15 = self._rolling_vol(closes, 15)

        # Noise ratio: higher means more noisy/ranging market
        noise_ratio = vol_15 / (mom_60 + 1e-8) if mom_60 > 0 else 1.0

        return {
            "trend_strength": mom_60,
            "vol_level": vol_60,
            "noise_ratio": min(noise_ratio, 10.0),  # Cap for stability
        }

    def _compute_gating(self, regime: dict[str, float]) -> tuple[float, float, float]:
        """Compute gating weights based on regime (deterministic)."""
        trend_strength = regime["trend_strength"]
        noise_ratio = regime["noise_ratio"]

        # Higher trend strength -> more weight to trend expert
        # Higher noise ratio -> more weight to mean reversion
        # Breakout gets residual weight

        # Use softmax-like normalization
        raw_trend = trend_strength * 10  # Scale up
        raw_mr = noise_ratio * 0.5
        raw_br = 1.0  # Base weight for breakout

        # Normalize to sum=1
        total = raw_trend + raw_mr + raw_br + 1e-8
        w_trend = raw_trend / total
        w_mr = raw_mr / total
        w_br = raw_br / total

        return w_trend, w_mr, w_br

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
        """Compute rolling volatility."""
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
