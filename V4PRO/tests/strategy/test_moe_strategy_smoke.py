from __future__ import annotations

import math

from src.strategy.ensemble_moe import EnsembleMoEStrategy
from src.strategy.types import Bar1m, MarketState


def _generate_bars(
    n: int, base_price: float = 100.0, trend: float = 0.001
) -> list[Bar1m]:
    """Generate synthetic bar data with trend."""
    bars: list[Bar1m] = []
    price = base_price
    for i in range(n):
        price = price * (1 + trend + 0.01 * math.sin(i * 0.1))
        high = price * 1.005
        low = price * 0.995
        bars.append(
            {
                "ts": 1700000000.0 + i * 60,
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000.0 + i,
            }
        )
    return bars


def test_moe_strategy_returns_valid_portfolio() -> None:
    """EnsembleMoEStrategy returns valid TargetPortfolio."""
    symbols = ["AO", "SA", "LC"]
    strategy = EnsembleMoEStrategy(symbols=symbols)

    bars_1m = {
        "AO": _generate_bars(300, base_price=100.0, trend=0.001),
        "SA": _generate_bars(300, base_price=200.0, trend=-0.0005),
        "LC": _generate_bars(300, base_price=150.0, trend=0.0002),
    }
    prices = {"AO": 110.0, "SA": 190.0, "LC": 155.0}

    state = MarketState(prices=prices, equity=1_000_000.0, bars_1m=bars_1m)
    result = strategy.on_tick(state)

    # Check keys cover symbols
    assert set(result.target_net_qty.keys()) == set(symbols)

    # Check qty type and range
    for sym in symbols:
        qty = result.target_net_qty[sym]
        assert isinstance(qty, int)
        assert abs(qty) <= 2

    # Check features_hash is 64 hex
    assert len(result.features_hash) == 64
    assert all(c in "0123456789abcdef" for c in result.features_hash)

    # Check model_version
    assert result.model_version == "moe-ensemble-v1"


def test_moe_strategy_gating_weights_sum_to_one() -> None:
    """Gating weights should sum to 1 (internal method test)."""
    symbols = ["AO"]
    strategy = EnsembleMoEStrategy(symbols=symbols)

    # Test _compute_gating directly with sample regime
    regime = {"trend_strength": 0.05, "vol_level": 0.02, "noise_ratio": 2.0}
    w_trend, w_mr, w_br = strategy._compute_gating(regime)

    # Gating weights must sum to 1
    total = w_trend + w_mr + w_br
    assert abs(total - 1.0) < 1e-6, f"Gating weights sum to {total}, expected 1.0"

    # All weights must be non-negative
    assert w_trend >= 0
    assert w_mr >= 0
    assert w_br >= 0


def test_moe_strategy_insufficient_bars() -> None:
    """With insufficient bars, qty should be 0."""
    symbols = ["AO"]
    strategy = EnsembleMoEStrategy(symbols=symbols, window=240)

    bars_1m = {"AO": _generate_bars(50)}
    prices = {"AO": 100.0}

    state = MarketState(prices=prices, equity=1_000_000.0, bars_1m=bars_1m)
    result = strategy.on_tick(state)

    assert result.target_net_qty["AO"] == 0


def test_moe_strategy_deterministic() -> None:
    """Same input should produce same output."""
    symbols = ["AO", "SA"]
    strategy = EnsembleMoEStrategy(symbols=symbols)

    bars_1m = {
        "AO": _generate_bars(300),
        "SA": _generate_bars(300),
    }
    prices = {"AO": 100.0, "SA": 200.0}
    state = MarketState(prices=prices, equity=1_000_000.0, bars_1m=bars_1m)

    result1 = strategy.on_tick(state)
    result2 = strategy.on_tick(state)

    assert result1.target_net_qty == result2.target_net_qty
    assert result1.features_hash == result2.features_hash
