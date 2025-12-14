"""Tests for strategy factory."""

from __future__ import annotations

from src.config import AppSettings
from src.strategy.dl_torch_policy import DlTorchPolicyStrategy
from src.strategy.ensemble_moe import EnsembleMoEStrategy
from src.strategy.factory import build_strategy
from src.strategy.linear_ai import LinearAIStrategy
from src.strategy.simple_ai import SimpleAIStrategy
from src.strategy.top_tier_trend_risk_parity import TopTierTrendRiskParityStrategy


class TestStrategyFactory:
    """Test strategy factory."""

    def test_default_returns_top_tier(self) -> None:
        """Default strategy_name returns TopTierTrendRiskParityStrategy."""
        settings = AppSettings(strategy_name="top_tier")
        strategy = build_strategy(settings)
        assert isinstance(strategy, TopTierTrendRiskParityStrategy)

    def test_simple_ai(self) -> None:
        """simple_ai returns SimpleAIStrategy."""
        settings = AppSettings(strategy_name="simple_ai")
        strategy = build_strategy(settings)
        assert isinstance(strategy, SimpleAIStrategy)

    def test_linear_ai(self) -> None:
        """linear_ai returns LinearAIStrategy."""
        settings = AppSettings(strategy_name="linear_ai")
        strategy = build_strategy(settings)
        assert isinstance(strategy, LinearAIStrategy)

    def test_ensemble_moe(self) -> None:
        """ensemble_moe returns EnsembleMoEStrategy."""
        settings = AppSettings(strategy_name="ensemble_moe")
        strategy = build_strategy(settings)
        assert isinstance(strategy, EnsembleMoEStrategy)

    def test_dl_torch(self) -> None:
        """dl_torch returns DlTorchPolicyStrategy."""
        settings = AppSettings(strategy_name="dl_torch")
        strategy = build_strategy(settings)
        assert isinstance(strategy, DlTorchPolicyStrategy)

    def test_unknown_strategy_defaults_to_top_tier(self) -> None:
        """Unknown strategy_name defaults to TopTierTrendRiskParityStrategy."""
        settings = AppSettings(strategy_name="unknown_xyz")
        strategy = build_strategy(settings)
        assert isinstance(strategy, TopTierTrendRiskParityStrategy)
