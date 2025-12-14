from __future__ import annotations

import math

from src.strategy.linear_ai import LinearAIStrategy
from src.strategy.types import Bar1m, MarketState


def _generate_bars(n: int, base_price: float = 100.0, trend: float = 0.001) -> list[Bar1m]:
    """Generate synthetic bar data with trend."""
    bars: list[Bar1m] = []
    price = base_price
    for i in range(n):
        # Add trend and small oscillation
        price = price * (1 + trend + 0.01 * math.sin(i * 0.1))
        high = price * 1.005
        low = price * 0.995
        bars.append(
            {
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return bars


def test_linear_ai_returns_target_portfolio() -> None:
    """LinearAIStrategy returns valid TargetPortfolio."""
    symbols = ["AO", "SA", "LC"]
    strategy = LinearAIStrategy(symbols=symbols)

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
    assert result.model_version == "linear-ai-v1"


def test_linear_ai_insufficient_bars_returns_zero() -> None:
    """When bars are insufficient, qty should be 0."""
    symbols = ["AO"]
    strategy = LinearAIStrategy(symbols=symbols, window=240)

    # Only 50 bars, less than window=240
    bars_1m = {"AO": _generate_bars(50)}
    prices = {"AO": 100.0}

    state = MarketState(prices=prices, equity=1_000_000.0, bars_1m=bars_1m)
    result = strategy.on_tick(state)

    assert result.target_net_qty["AO"] == 0


def test_linear_ai_custom_weights() -> None:
    """Custom weights should be used in scoring."""
    symbols = ["AO"]
    custom_weights = {"mom_15": 2.0, "mom_60": 0.0, "vol_60": 0.0, "range_60": 0.0, "vol_shock_60": 0.0}
    strategy = LinearAIStrategy(symbols=symbols, weights=custom_weights)

    bars_1m = {"AO": _generate_bars(300, trend=0.01)}  # Strong uptrend
    prices = {"AO": 150.0}

    state = MarketState(prices=prices, equity=1_000_000.0, bars_1m=bars_1m)
    result = strategy.on_tick(state)

    # With strong uptrend and high mom_15 weight, expect positive qty
    assert result.target_net_qty["AO"] >= 0


def test_linear_ai_deterministic() -> None:
    """Same input should produce same output (deterministic)."""
    symbols = ["AO", "SA"]
    strategy = LinearAIStrategy(symbols=symbols)

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
