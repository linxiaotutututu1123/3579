"""Feature extraction for DL strategy."""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from src.strategy.types import Bar1m


def build_features(bars: Sequence[Bar1m], window: int = 60) -> np.ndarray:
    """
    Build feature vector from bar data.

    Features (per window):
    - Normalized returns (window size)
    - Normalized volume (window size)
    - Range features (window size)

    Returns:
        1D numpy array of shape (feature_dim,)
    """
    if len(bars) < window:
        # Return zero vector if insufficient data
        feature_dim = window * 3  # returns + volume + range
        return np.zeros(feature_dim, dtype=np.float32)

    recent_bars = bars[-window:]

    closes = np.array([float(b["close"]) for b in recent_bars], dtype=np.float64)
    volumes = np.array([float(b["volume"]) for b in recent_bars], dtype=np.float64)
    highs = np.array([float(b["high"]) for b in recent_bars], dtype=np.float64)
    lows = np.array([float(b["low"]) for b in recent_bars], dtype=np.float64)

    # Log returns (first is 0)
    returns = np.zeros(window, dtype=np.float64)
    for i in range(1, window):
        if closes[i - 1] > 0:
            returns[i] = math.log(closes[i] / closes[i - 1])

    # Normalize returns
    ret_std = np.std(returns)
    if ret_std > 1e-8:
        returns = returns / ret_std

    # Normalize volume
    vol_mean = np.mean(volumes)
    if vol_mean > 1e-8:
        volumes = volumes / vol_mean - 1.0

    # Range features (high-low)/close
    ranges = np.zeros(window, dtype=np.float64)
    for i in range(window):
        if closes[i] > 0:
            ranges[i] = (highs[i] - lows[i]) / closes[i]

    # Normalize ranges
    range_mean = np.mean(ranges)
    range_std = np.std(ranges)
    if range_std > 1e-8:
        ranges = (ranges - range_mean) / range_std

    # Concatenate all features
    features = np.concatenate([returns, volumes, ranges]).astype(np.float32)

    return features


def get_feature_dim(window: int = 60) -> int:
    """Get the feature dimension for a given window size."""
    return window * 3
