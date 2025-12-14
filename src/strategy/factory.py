from __future__ import annotations

from collections.abc import Sequence

from src.config import AppSettings
from src.strategy.base import Strategy
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

    # Default to top_tier
    cfg = TopTierConfig(symbols=symbols)
    return TopTierTrendRiskParityStrategy(cfg)
