"""Portfolio Management Module (Military-Grade v3.0).

This module provides portfolio-level position management and analysis
as specified in V3PRO_UPGRADE_PLAN extension modules (Chapter 24).

Components:
- PortfolioManager: Portfolio-level position aggregation
- PortfolioAnalytics: Risk metrics and analytics
- PositionAggregator: Multi-strategy position aggregation

Example:
    from src.portfolio import PortfolioManager, PortfolioAnalytics

    manager = PortfolioManager()
    manager.update_position("AO2501", 10, "calendar_arb")

    analytics = PortfolioAnalytics(manager)
    risk_metrics = analytics.compute_risk_metrics()
"""

from __future__ import annotations

from src.portfolio.aggregator import PositionAggregator
from src.portfolio.analytics import PortfolioAnalytics
from src.portfolio.manager import PortfolioManager


__all__ = [
    "PortfolioAnalytics",
    "PortfolioManager",
    "PositionAggregator",
]
