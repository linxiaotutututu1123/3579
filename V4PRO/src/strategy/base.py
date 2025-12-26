from __future__ import annotations

from abc import ABC, abstractmethod

from src.strategy.types import MarketState, TargetPortfolio


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    @abstractmethod
    def on_tick(self, state: MarketState) -> TargetPortfolio:
        """Generate target portfolio based on current market state."""
        raise NotImplementedError
