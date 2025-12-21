from __future__ import annotations

from collections.abc import Sequence

from src.config import AppSettings
from src.strategy.base import Strategy
from src.strategy.dl_torch_policy import DlTorchPolicyStrategy
from src.strategy.ensemble_moe import EnsembleMoEStrategy
from src.strategy.linear_ai import LinearAIStrategy
from src.strategy.simple_ai import SimpleAIStrategy
from src.strategy.top_tier_trend_risk_parity import (
    TopTierConfig,
    TopTierTrendRiskParityStrategy,
)


def build_strategy(settings: AppSettings) -> Strategy:
    """Build strategy instance based on settings."""
    symbols: Sequence[str] = settings.strategy_symbols

    if settings.strategy_name == "simple_ai":
        return SimpleAIStrategy(symbols=list(symbols))

    if settings.strategy_name == "linear_ai":
        return LinearAIStrategy(symbols=list(symbols))

    if settings.strategy_name == "ensemble_moe":
        return EnsembleMoEStrategy(symbols=list(symbols))

    if settings.strategy_name == "dl_torch":
        return DlTorchPolicyStrategy(symbols=list(symbols))

    # Default to top_tier
    cfg = TopTierConfig(symbols=symbols)
    return TopTierTrendRiskParityStrategy(cfg)
