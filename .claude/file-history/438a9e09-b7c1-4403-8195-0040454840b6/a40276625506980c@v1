"""Portfolio Analytics (Military-Grade v3.0).

Provides risk metrics and analytics for portfolio management.

Features:
- Exposure calculation
- Concentration metrics
- P&L attribution
- Risk metrics

Example:
    analytics = PortfolioAnalytics(portfolio_manager)
    metrics = analytics.compute_risk_metrics()
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.portfolio.manager import PortfolioManager


@dataclass
class RiskMetrics:
    """Portfolio risk metrics.

    Attributes:
        gross_exposure: Total absolute position value
        net_exposure: Net position value (long - short)
        long_exposure: Total long position value
        short_exposure: Total short position value (absolute)
        concentration: Herfindahl-Hirschman Index (0-1)
        num_positions: Number of positions
        num_symbols: Number of unique symbols
        num_strategies: Number of active strategies
    """

    gross_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    concentration: float
    num_positions: int
    num_symbols: int
    num_strategies: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gross_exposure": self.gross_exposure,
            "net_exposure": self.net_exposure,
            "long_exposure": self.long_exposure,
            "short_exposure": self.short_exposure,
            "concentration": self.concentration,
            "num_positions": self.num_positions,
            "num_symbols": self.num_symbols,
            "num_strategies": self.num_strategies,
        }


@dataclass
class PnLAttribution:
    """P&L attribution by dimension.

    Attributes:
        by_symbol: P&L by symbol
        by_strategy: P&L by strategy
        total_realized: Total realized P&L
        total_unrealized: Total unrealized P&L
    """

    by_symbol: dict[str, float]
    by_strategy: dict[str, float]
    total_realized: float
    total_unrealized: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "by_symbol": self.by_symbol,
            "by_strategy": self.by_strategy,
            "total_realized": self.total_realized,
            "total_unrealized": self.total_unrealized,
        }


class PortfolioAnalytics:
    """Portfolio analytics and risk metrics calculator."""

    def __init__(self, manager: PortfolioManager) -> None:
        """Initialize analytics.

        Args:
            manager: Portfolio manager instance
        """
        self._manager = manager

    def compute_risk_metrics(
        self, prices: dict[str, float] | None = None
    ) -> RiskMetrics:
        """Compute portfolio risk metrics.

        Args:
            prices: Optional price dictionary for valuation

        Returns:
            Risk metrics
        """
        positions = self._manager.get_all_positions()

        if not positions:
            return RiskMetrics(
                gross_exposure=0.0,
                net_exposure=0.0,
                long_exposure=0.0,
                short_exposure=0.0,
                concentration=0.0,
                num_positions=0,
                num_symbols=0,
                num_strategies=0,
            )

        prices = prices or {}

        # Calculate exposures
        long_exp = 0.0
        short_exp = 0.0
        position_values: list[float] = []

        for pos in positions:
            price = prices.get(pos.symbol, pos.avg_price)
            if price <= 0:
                price = 1.0  # Fallback
            value = abs(pos.quantity * price)
            position_values.append(value)

            if pos.quantity > 0:
                long_exp += value
            else:
                short_exp += value

        gross_exp = long_exp + short_exp
        net_exp = long_exp - short_exp

        # Calculate concentration (HHI)
        concentration = self._calculate_hhi(position_values, gross_exp)

        return RiskMetrics(
            gross_exposure=gross_exp,
            net_exposure=net_exp,
            long_exposure=long_exp,
            short_exposure=short_exp,
            concentration=concentration,
            num_positions=len(positions),
            num_symbols=len(self._manager.symbols),
            num_strategies=len(self._manager.strategies),
        )

    def _calculate_hhi(
        self, position_values: list[float], total: float
    ) -> float:
        """Calculate Herfindahl-Hirschman Index.

        Args:
            position_values: List of position values
            total: Total portfolio value

        Returns:
            HHI (0-1, higher = more concentrated)
        """
        if total <= 0:
            return 0.0

        hhi = 0.0
        for value in position_values:
            weight = value / total
            hhi += weight * weight

        return hhi

    def compute_pnl_attribution(self) -> PnLAttribution:
        """Compute P&L attribution by symbol and strategy.

        Returns:
            P&L attribution
        """
        positions = self._manager.get_all_positions()

        by_symbol: dict[str, float] = {}
        by_strategy: dict[str, float] = {}
        total_realized = 0.0
        total_unrealized = 0.0

        for pos in positions:
            total_pnl = pos.realized_pnl + pos.unrealized_pnl
            total_realized += pos.realized_pnl
            total_unrealized += pos.unrealized_pnl

            # By symbol
            by_symbol[pos.symbol] = by_symbol.get(pos.symbol, 0.0) + total_pnl

            # By strategy
            by_strategy[pos.strategy] = (
                by_strategy.get(pos.strategy, 0.0) + total_pnl
            )

        return PnLAttribution(
            by_symbol=by_symbol,
            by_strategy=by_strategy,
            total_realized=total_realized,
            total_unrealized=total_unrealized,
        )

    def compute_sharpe_ratio(
        self, returns: list[float], risk_free_rate: float = 0.0
    ) -> float:
        """Compute Sharpe ratio from returns.

        Args:
            returns: List of periodic returns
            risk_free_rate: Risk-free rate (same period as returns)

        Returns:
            Sharpe ratio (annualized if daily returns assumed)
        """
        if len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns)
        excess_return = mean_return - risk_free_rate

        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev < 1e-10:
            return 0.0

        # Assume daily returns, annualize
        annualization_factor = math.sqrt(252)
        return (excess_return / std_dev) * annualization_factor

    def compute_max_drawdown(self, equity_curve: list[float]) -> float:
        """Compute maximum drawdown from equity curve.

        Args:
            equity_curve: List of equity values over time

        Returns:
            Maximum drawdown (as positive percentage, e.g., 0.1 = 10%)
        """
        if len(equity_curve) < 2:
            return 0.0

        max_dd = 0.0
        peak = equity_curve[0]

        for value in equity_curve:
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak
                max_dd = max(max_dd, dd)

        return max_dd
