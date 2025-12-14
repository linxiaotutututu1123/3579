from __future__ import annotations

import random

from src.strategy.top_tier_trend_risk_parity import TopTierConfig, TopTierTrendRiskParityStrategy
from src.strategy.types import Bar1m, MarketState


def _generate_fake_bars(n: int, base_price: float = 100.0, seed: int = 42) -> list[Bar1m]:
    """Generate n fake 1-minute bars with random walk prices."""
    random.seed(seed)
    bars: list[Bar1m] = []
    price = base_price

    for i in range(n):
        change = random.uniform(-0.5, 0.5)
        open_price = price
        high = price + abs(change) + random.uniform(0, 0.2)
        low = price - abs(change) - random.uniform(0, 0.2)
        close = price + change
        price = close

        bars.append(
            Bar1m(
                ts=float(i * 60),
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=float(random.randint(100, 1000)),
            )
        )

    return bars


def test_top_tier_strategy_smoke() -> None:
    """Smoke test: strategy runs without error and produces valid output."""
    cfg = TopTierConfig(
        symbols=("AO", "SA", "LC"),
        max_abs_qty_per_symbol=2,
    )
    strategy = TopTierTrendRiskParityStrategy(cfg)

    bars_1m = {
        "AO": _generate_fake_bars(300, base_price=100.0, seed=1),
        "SA": _generate_fake_bars(300, base_price=200.0, seed=2),
        "LC": _generate_fake_bars(300, base_price=150.0, seed=3),
    }

    prices = {
        "AO": bars_1m["AO"][-1]["close"],
        "SA": bars_1m["SA"][-1]["close"],
        "LC": bars_1m["LC"][-1]["close"],
    }

    state = MarketState(
        prices=prices,
        equity=1_000_000.0,
        bars_1m=bars_1m,
    )

    target = strategy.on_tick(state)

    assert target.model_version == "top-tier-trend-risk-parity-v1"
    assert len(target.features_hash) == 64

    assert "AO" in target.target_net_qty
    assert "SA" in target.target_net_qty
    assert "LC" in target.target_net_qty

    for sym in ("AO", "SA", "LC"):
        qty = target.target_net_qty[sym]
        assert isinstance(qty, int)
        assert abs(qty) <= cfg.max_abs_qty_per_symbol


def test_top_tier_strategy_with_insufficient_bars() -> None:
    """Strategy should handle insufficient bars gracefully."""
    cfg = TopTierConfig(symbols=("AO",), max_abs_qty_per_symbol=2)
    strategy = TopTierTrendRiskParityStrategy(cfg)

    bars_1m = {
        "AO": _generate_fake_bars(10, base_price=100.0),
    }

    state = MarketState(
        prices={"AO": 100.0},
        equity=1_000_000.0,
        bars_1m=bars_1m,
    )

    target = strategy.on_tick(state)

    assert "AO" in target.target_net_qty
    assert isinstance(target.target_net_qty["AO"], int)


def test_top_tier_strategy_deterministic() -> None:
    """Strategy should produce deterministic output for same input."""
    cfg = TopTierConfig(symbols=("AO", "SA", "LC"))

    bars_1m = {
        "AO": _generate_fake_bars(300, base_price=100.0, seed=42),
        "SA": _generate_fake_bars(300, base_price=200.0, seed=42),
        "LC": _generate_fake_bars(300, base_price=150.0, seed=42),
    }

    prices = {"AO": 100.0, "SA": 200.0, "LC": 150.0}

    state = MarketState(
        prices=prices,
        equity=1_000_000.0,
        bars_1m=bars_1m,
    )

    strategy1 = TopTierTrendRiskParityStrategy(cfg)
    target1 = strategy1.on_tick(state)

    strategy2 = TopTierTrendRiskParityStrategy(cfg)
    target2 = strategy2.on_tick(state)

    assert target1.target_net_qty == target2.target_net_qty
    assert target1.features_hash == target2.features_hash
