"""Contract tests for all strategies.

Validates that all strategy implementations conform to the Strategy interface contract.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

from src.strategy.base import Strategy
from src.strategy.dl_torch_policy import DlTorchPolicyStrategy
from src.strategy.ensemble_moe import EnsembleMoEStrategy
from src.strategy.linear_ai import LinearAIStrategy
from src.strategy.simple_ai import SimpleAIStrategy
from src.strategy.top_tier_trend_risk_parity import (
    TopTierConfig,
    TopTierTrendRiskParityStrategy,
)
from src.strategy.types import Bar1m, MarketState, TargetPortfolio

if TYPE_CHECKING:
    pass


def _make_market_state(symbols: Sequence[str], bar_count: int = 60) -> MarketState:
    """Create a test MarketState with realistic bar data."""
    bars: dict[str, list[Bar1m]] = {}
    for sym in symbols:
        sym_bars = []
        for i in range(bar_count):
            bar = Bar1m(
                open=100.0 + i * 0.1,
                high=100.5 + i * 0.1,
                low=99.5 + i * 0.1,
                close=100.2 + i * 0.1,
                volume=1000 + i * 10,
            )
            sym_bars.append(bar)
        bars[sym] = sym_bars
    return MarketState(bars=bars)


def _make_strategy_factory(
    name: str,
) -> Callable[[Sequence[str]], Strategy]:
    """Create a factory function for the given strategy name."""
    if name == "simple_ai":
        return lambda syms: SimpleAIStrategy(symbols=list(syms))
    if name == "linear_ai":
        return lambda syms: LinearAIStrategy(symbols=list(syms))
    if name == "ensemble_moe":
        return lambda syms: EnsembleMoEStrategy(symbols=list(syms))
    if name == "dl_torch":
        return lambda syms: DlTorchPolicyStrategy(symbols=list(syms))
    if name == "top_tier":
        return lambda syms: TopTierTrendRiskParityStrategy(TopTierConfig(symbols=syms))
    raise ValueError(f"Unknown strategy: {name}")


ALL_STRATEGIES = ["simple_ai", "linear_ai", "ensemble_moe", "dl_torch", "top_tier"]


class TestStrategyContract:
    """Contract tests for all Strategy implementations."""

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_is_strategy_subclass(self, strategy_name: str) -> None:
        """All strategies are subclasses of Strategy."""
        symbols = ["AO", "SA"]
        factory = _make_strategy_factory(strategy_name)
        strategy = factory(symbols)
        assert isinstance(strategy, Strategy)

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_on_tick_returns_target_portfolio(self, strategy_name: str) -> None:
        """on_tick returns a TargetPortfolio instance."""
        symbols = ["AO", "SA"]
        factory = _make_strategy_factory(strategy_name)
        strategy = factory(symbols)
        state = _make_market_state(symbols)
        result = strategy.on_tick(state)
        assert isinstance(result, TargetPortfolio)

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_on_tick_returns_valid_quantities(self, strategy_name: str) -> None:
        """on_tick returns quantities that are finite numbers."""
        symbols = ["AO", "SA"]
        factory = _make_strategy_factory(strategy_name)
        strategy = factory(symbols)
        state = _make_market_state(symbols)
        result = strategy.on_tick(state)

        for sym, qty in result.targets.items():
            assert sym in symbols, f"Unexpected symbol {sym}"
            assert isinstance(qty, (int, float)), f"qty for {sym} is not numeric"
            assert qty == qty, f"qty for {sym} is NaN"  # NaN check

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_on_tick_deterministic(self, strategy_name: str) -> None:
        """on_tick is deterministic - same input yields same output."""
        symbols = ["AO", "SA"]
        factory = _make_strategy_factory(strategy_name)
        strategy1 = factory(symbols)
        strategy2 = factory(symbols)
        state = _make_market_state(symbols)

        result1 = strategy1.on_tick(state)
        result2 = strategy2.on_tick(state)

        assert result1.targets == result2.targets

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_handles_empty_bars(self, strategy_name: str) -> None:
        """Strategy handles empty bars gracefully."""
        symbols = ["AO", "SA"]
        factory = _make_strategy_factory(strategy_name)
        strategy = factory(symbols)
        # Some bars may be empty
        state = MarketState(bars={"AO": [], "SA": []})
        result = strategy.on_tick(state)
        # Should not crash, should return valid TargetPortfolio
        assert isinstance(result, TargetPortfolio)

    @pytest.mark.parametrize("strategy_name", ALL_STRATEGIES)
    def test_handles_missing_symbols_in_state(self, strategy_name: str) -> None:
        """Strategy handles missing symbols in market state."""
        symbols = ["AO", "SA", "LC"]
        factory = _make_strategy_factory(strategy_name)
        strategy = factory(symbols)
        # Only provide bars for some symbols
        state = _make_market_state(["AO"])
        result = strategy.on_tick(state)
        assert isinstance(result, TargetPortfolio)
