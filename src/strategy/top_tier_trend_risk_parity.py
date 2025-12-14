from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from src.strategy.base import Strategy
from src.strategy.types import MarketState, TargetPortfolio


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class TopTierConfig:
    """Configuration for top-tier trend risk parity strategy."""

    symbols: Sequence[str] = ("AO", "SA", "LC")
    mom_windows: tuple[int, int, int] = (15, 60, 240)
    mom_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)
    ewma_halflife: int = 60
    vol_floor: float = 1e-8
    max_abs_qty_per_symbol: int = 2
    smoothing_alpha: float = 0.3  # exponential smoothing for target


class TopTierTrendRiskParityStrategy(Strategy):
    """
    Multi-period trend following with risk parity position sizing.

    Features:
    - Multi-period momentum (15m, 60m, 240m log-returns)
    - EWMA volatility estimation
    - Risk parity-ish position sizing
    - Exponential smoothing to reduce turnover
    """

    def __init__(self, cfg: TopTierConfig | None = None) -> None:
        self._cfg = cfg or TopTierConfig()
        self._prev_target: dict[str, float] = {}

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        cfg = self._cfg
        symbols = list(cfg.symbols)

        signals: dict[str, float] = {}
        vols: dict[str, float] = {}
        features: dict[str, object] = {
            "mom_windows": cfg.mom_windows,
            "mom_weights": cfg.mom_weights,
            "ewma_halflife": cfg.ewma_halflife,
        }

        for sym in symbols:
            bars = state.bars_1m.get(sym, [])
            if len(bars) < max(cfg.mom_windows):
                signals[sym] = 0.0
                vols[sym] = cfg.vol_floor
                features[f"{sym}_mom"] = [0.0, 0.0, 0.0]
                features[f"{sym}_vol"] = cfg.vol_floor
                continue

            closes = np.array([b["close"] for b in bars], dtype=np.float64)
            mom_values = self._compute_momentum(closes, cfg.mom_windows)
            fused_signal = sum(w * m for w, m in zip(cfg.mom_weights, mom_values, strict=False))

            vol = self._compute_ewma_vol(closes, cfg.ewma_halflife, cfg.vol_floor)

            signals[sym] = fused_signal
            vols[sym] = vol
            features[f"{sym}_mom"] = list(mom_values)
            features[f"{sym}_vol"] = vol

        raw_targets = self._risk_parity_sizing(signals, vols, cfg.max_abs_qty_per_symbol)
        smoothed_targets = self._smooth_targets(raw_targets, cfg.smoothing_alpha)
        final_targets = {sym: int(round(smoothed_targets.get(sym, 0.0))) for sym in symbols}

        for sym in symbols:
            final_targets[sym] = max(
                -cfg.max_abs_qty_per_symbol, min(cfg.max_abs_qty_per_symbol, final_targets[sym])
            )

        features["raw_targets"] = {k: float(v) for k, v in raw_targets.items()}
        features["smoothed_targets"] = {k: float(v) for k, v in smoothed_targets.items()}
        features_hash = hashlib.sha256(_stable_json(features).encode()).hexdigest()

        return TargetPortfolio(
            target_net_qty=final_targets,
            model_version="top-tier-trend-risk-parity-v1",
            features_hash=features_hash,
        )

    def _compute_momentum(
        self, closes: np.ndarray, windows: tuple[int, int, int]
    ) -> tuple[float, float, float]:
        """Compute log-return momentum for each window."""
        results: list[float] = []
        for w in windows:
            if len(closes) < w + 1:
                results.append(0.0)
            else:
                mom = float(np.log(closes[-1] / closes[-w - 1]))
                results.append(mom)
        return (results[0], results[1], results[2])

    def _compute_ewma_vol(self, closes: np.ndarray, halflife: int, vol_floor: float) -> float:
        """Compute EWMA volatility of log returns."""
        if len(closes) < 2:
            return vol_floor

        log_returns = np.diff(np.log(closes))
        if len(log_returns) == 0:
            return vol_floor

        alpha = 1 - math.exp(-math.log(2) / halflife)
        ewma_var = 0.0
        for r in log_returns:
            ewma_var = alpha * (r * r) + (1 - alpha) * ewma_var

        vol = math.sqrt(max(ewma_var, 0.0))
        return max(vol, vol_floor)

    def _risk_parity_sizing(
        self,
        signals: dict[str, float],
        vols: dict[str, float],
        max_qty: int,
    ) -> dict[str, float]:
        """
        Risk parity-ish sizing: allocate risk budget proportional to |signal|,
        then scale by 1/vol to get position size.
        """
        total_abs_signal = sum(abs(s) for s in signals.values())
        if total_abs_signal < 1e-12:
            return {sym: 0.0 for sym in signals}

        targets: dict[str, float] = {}
        for sym, sig in signals.items():
            risk_budget = abs(sig) / total_abs_signal
            vol = vols.get(sym, 1.0)
            raw_size = risk_budget / vol
            direction = 1.0 if sig > 0 else (-1.0 if sig < 0 else 0.0)
            scaled = direction * raw_size * max_qty
            targets[sym] = scaled

        return targets

    def _smooth_targets(self, raw: dict[str, float], alpha: float) -> dict[str, float]:
        """Exponential smoothing to reduce turnover."""
        smoothed: dict[str, float] = {}
        for sym, val in raw.items():
            prev = self._prev_target.get(sym, 0.0)
            smoothed[sym] = alpha * val + (1 - alpha) * prev
        self._prev_target = smoothed.copy()
        return smoothed
