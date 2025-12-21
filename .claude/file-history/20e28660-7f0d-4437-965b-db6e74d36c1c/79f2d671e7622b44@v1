"""投资组合模块测试 (军规级 v4.0)."""

from __future__ import annotations

import pytest

from src.portfolio import PortfolioAnalytics, PortfolioManager, PositionAggregator
from src.portfolio.aggregator import AggregatedPosition, PositionSnapshot
from src.portfolio.manager import PortfolioConfig, PositionEntry


class TestAggregatedPosition:
    """聚合持仓测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        pos = AggregatedPosition(
            symbol="rb2501",
            net_quantity=10,
            gross_quantity=10,
            strategies=["arb"],
            avg_price=4000.0,
            total_pnl=1000.0,
        )
        d = pos.to_dict()
        assert d["symbol"] == "rb2501"
        assert d["net_quantity"] == 10


class TestPositionSnapshot:
    """持仓快照测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        pos = AggregatedPosition("rb2501", 10, 10, ["arb"], 4000.0, 1000.0)
        snapshot = PositionSnapshot(ts=1000.0, positions=[pos], total_pnl=1000.0)
        d = snapshot.to_dict()
        assert d["ts"] == 1000.0
        assert len(d["positions"]) == 1


class TestPositionAggregator:
    """持仓聚合器测试."""

    def test_add_snapshot(self) -> None:
        """测试添加快照."""
        agg = PositionAggregator()
        data = {
            "positions": [
                {"symbol": "rb2501", "quantity": 10, "strategy": "arb", "pnl": 100},
            ],
            "total_pnl": 100,
        }
        snapshot = agg.add_snapshot(data)
        assert len(snapshot.positions) == 1

    def test_get_history(self) -> None:
        """测试获取历史."""
        agg = PositionAggregator()
        agg.add_snapshot({"positions": [], "total_pnl": 0})
        agg.add_snapshot({"positions": [], "total_pnl": 0})
        history = agg.get_history()
        assert len(history) == 2

    def test_max_history(self) -> None:
        """测试历史限制."""
        agg = PositionAggregator(max_history=5)
        for i in range(10):
            agg.add_snapshot({"positions": [], "total_pnl": float(i)})
        assert len(agg.get_history()) == 5

    def test_get_latest(self) -> None:
        """测试获取最新."""
        agg = PositionAggregator()
        agg.add_snapshot({"positions": [], "total_pnl": 100})
        latest = agg.get_latest()
        assert latest is not None
        assert latest.total_pnl == 100

    def test_get_latest_empty(self) -> None:
        """测试空时获取最新."""
        agg = PositionAggregator()
        assert agg.get_latest() is None

    def test_clear(self) -> None:
        """测试清空."""
        agg = PositionAggregator()
        agg.add_snapshot({"positions": [], "total_pnl": 0})
        agg.clear()
        assert len(agg.get_history()) == 0


class TestPositionEntry:
    """持仓条目测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        entry = PositionEntry(
            symbol="rb2501",
            quantity=10,
            strategy="arb",
            avg_price=4000.0,
        )
        d = entry.to_dict()
        assert d["symbol"] == "rb2501"
        assert d["quantity"] == 10


class TestPortfolioConfig:
    """投资组合配置测试."""

    def test_defaults(self) -> None:
        """测试默认值."""
        config = PortfolioConfig()
        assert config.max_position_per_symbol == 100
        assert config.max_total_position == 1000


class TestPortfolioManager:
    """投资组合管理器测试."""

    def test_update_position(self) -> None:
        """测试更新持仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        assert manager.get_net_position("rb2501") == 10

    def test_update_position_multiple_strategies(self) -> None:
        """测试多策略更新."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("rb2501", 5, "trend")
        assert manager.get_net_position("rb2501") == 15

    def test_update_position_opposite(self) -> None:
        """测试相反方向更新."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("rb2501", -5, "hedge")
        assert manager.get_net_position("rb2501") == 5

    def test_get_position(self) -> None:
        """测试获取持仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        pos = manager.get_position("rb2501", "arb")
        assert pos is not None
        assert pos.quantity == 10

    def test_get_position_not_found(self) -> None:
        """测试获取不存在的持仓."""
        manager = PortfolioManager()
        assert manager.get_position("unknown", "unknown") is None

    def test_get_net_position_not_found(self) -> None:
        """测试获取不存在的净持仓."""
        manager = PortfolioManager()
        assert manager.get_net_position("unknown") == 0

    def test_get_all_positions(self) -> None:
        """测试获取所有持仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("au2506", 5, "trend")
        positions = manager.get_all_positions()
        assert len(positions) == 2

    def test_get_positions_by_strategy(self) -> None:
        """测试按策略获取持仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("au2506", 5, "arb")
        manager.update_position("cu2503", 3, "trend")
        positions = manager.get_positions_by_strategy("arb")
        assert len(positions) == 2

    def test_get_positions_by_symbol(self) -> None:
        """测试按合约获取持仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("rb2501", 5, "trend")
        positions = manager.get_positions_by_symbol("rb2501")
        assert len(positions) == 2

    def test_close_position(self) -> None:
        """测试平仓."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.close_position("rb2501", "arb")
        assert manager.get_net_position("rb2501") == 0

    def test_get_snapshot(self) -> None:
        """测试获取快照."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        snapshot = manager.get_snapshot()
        assert "positions" in snapshot
        assert "total_positions" in snapshot

    def test_position_limit_exceeded(self) -> None:
        """测试持仓限额超限."""
        config = PortfolioConfig(max_position_per_symbol=10)
        manager = PortfolioManager(config)
        manager.update_position("rb2501", 10, "arb")
        # 超限更新应该被拒绝
        with pytest.raises(ValueError):
            manager.update_position("rb2501", 5, "trend")

    def test_position_limit_disabled(self) -> None:
        """测试禁用持仓限额."""
        config = PortfolioConfig(
            max_position_per_symbol=10,
            enable_position_limits=False,
        )
        manager = PortfolioManager(config)
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("rb2501", 5, "trend")  # 不应抛出异常
        assert manager.get_net_position("rb2501") == 15


class TestPortfolioAnalytics:
    """投资组合分析测试."""

    def test_compute_risk_metrics(self) -> None:
        """测试计算风险指标."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb", avg_price=4000.0)
        analytics = PortfolioAnalytics(manager)
        metrics = analytics.compute_risk_metrics()
        assert "total_exposure" in metrics
        assert "position_count" in metrics

    def test_compute_risk_metrics_empty(self) -> None:
        """测试空组合风险指标."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)
        metrics = analytics.compute_risk_metrics()
        assert metrics["position_count"] == 0

    def test_get_concentration(self) -> None:
        """测试获取集中度."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("au2506", 5, "arb")
        analytics = PortfolioAnalytics(manager)
        concentration = analytics.get_concentration()
        assert len(concentration) >= 2

    def test_get_strategy_breakdown(self) -> None:
        """测试获取策略分解."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb")
        manager.update_position("au2506", 5, "trend")
        analytics = PortfolioAnalytics(manager)
        breakdown = analytics.get_strategy_breakdown()
        assert "arb" in breakdown
        assert "trend" in breakdown


class TestPortfolioModuleImports:
    """测试模块导入."""

    def test_import_from_portfolio(self) -> None:
        """测试从portfolio模块导入."""
        from src.portfolio import PortfolioAnalytics, PortfolioManager, PositionAggregator

        assert PortfolioManager is not None
        assert PortfolioAnalytics is not None
        assert PositionAggregator is not None
