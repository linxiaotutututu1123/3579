"""投资组合管理模块 (军规级 v3.0).

本模块提供投资组合级别的持仓管理和分析功能，
参照 V3PRO_UPGRADE_PLAN 扩展模块规划 (第24章)。

组件:
- PortfolioManager: 投资组合级持仓聚合
- PortfolioAnalytics: 风险指标和分析
- PositionAggregator: 多策略持仓聚合

示例:
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
