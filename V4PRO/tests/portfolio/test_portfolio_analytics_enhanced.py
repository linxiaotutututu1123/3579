"""投资组合分析器和聚合器增强测试 (军规级 v4.0)."""

from __future__ import annotations

from src.portfolio.aggregator import (
    AggregatedPosition,
    PositionAggregator,
    PositionSnapshot,
)
from src.portfolio.analytics import PnLAttribution, PortfolioAnalytics, RiskMetrics
from src.portfolio.manager import PortfolioManager


class TestRiskMetricsDataclass:
    """风险指标数据类测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        metrics = RiskMetrics(
            gross_exposure=100000.0,
            net_exposure=50000.0,
            long_exposure=75000.0,
            short_exposure=25000.0,
            concentration=0.3,
            num_positions=5,
            num_symbols=3,
            num_strategies=2,
        )
        d = metrics.to_dict()
        assert d["gross_exposure"] == 100000.0
        assert d["net_exposure"] == 50000.0
        assert d["long_exposure"] == 75000.0
        assert d["short_exposure"] == 25000.0
        assert d["concentration"] == 0.3
        assert d["num_positions"] == 5


class TestPnLAttributionDataclass:
    """盈亏归因数据类测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        attr = PnLAttribution(
            by_symbol={"rb2501": 1000.0, "au2506": -500.0},
            by_strategy={"arb": 500.0},
            total_realized=300.0,
            total_unrealized=200.0,
        )
        d = attr.to_dict()
        assert d["by_symbol"]["rb2501"] == 1000.0
        assert d["total_realized"] == 300.0


class TestPortfolioAnalyticsEnhanced:
    """投资组合分析器增强测试."""

    def test_compute_risk_metrics_empty(self) -> None:
        """测试空组合风险指标."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)
        metrics = analytics.compute_risk_metrics()

        assert metrics.gross_exposure == 0.0
        assert metrics.net_exposure == 0.0
        assert metrics.num_positions == 0

    def test_compute_risk_metrics_with_positions(self) -> None:
        """测试有持仓的风险指标."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb", avg_price=4000.0)
        manager.update_position("au2506", 5, "trend", avg_price=500.0)
        manager.update_position("cu2503", -3, "arb", avg_price=70000.0)

        analytics = PortfolioAnalytics(manager)
        metrics = analytics.compute_risk_metrics()

        assert metrics.num_positions == 3
        assert metrics.gross_exposure > 0
        assert metrics.long_exposure > 0
        assert metrics.short_exposure > 0

    def test_compute_risk_metrics_with_prices(self) -> None:
        """测试带价格的风险指标."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb", avg_price=4000.0)

        analytics = PortfolioAnalytics(manager)
        prices = {"rb2501": 4100.0}
        metrics = analytics.compute_risk_metrics(prices)

        # 使用市场价格计算敞口
        assert metrics.long_exposure == 41000.0

    def test_compute_risk_metrics_zero_price(self) -> None:
        """测试零价格情况."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb", avg_price=0.0)

        analytics = PortfolioAnalytics(manager)
        metrics = analytics.compute_risk_metrics()

        # 应该使用回退价格1.0
        assert metrics.gross_exposure > 0

    def test_calculate_hhi_empty(self) -> None:
        """测试空列表HHI."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        hhi = analytics._calculate_hhi([], 0.0)
        assert hhi == 0.0

    def test_calculate_hhi_single(self) -> None:
        """测试单一持仓HHI."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 单一持仓，HHI = 1
        hhi = analytics._calculate_hhi([100.0], 100.0)
        assert hhi == 1.0

    def test_calculate_hhi_equal(self) -> None:
        """测试均等持仓HHI."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 4个均等持仓，HHI = 4 * (0.25)^2 = 0.25
        hhi = analytics._calculate_hhi([25.0, 25.0, 25.0, 25.0], 100.0)
        assert abs(hhi - 0.25) < 0.001

    def test_compute_pnl_attribution_empty(self) -> None:
        """测试空组合盈亏归因."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)
        attr = analytics.compute_pnl_attribution()

        assert len(attr.by_symbol) == 0
        assert len(attr.by_strategy) == 0
        assert attr.total_realized == 0.0
        assert attr.total_unrealized == 0.0

    def test_compute_pnl_attribution_with_positions(self) -> None:
        """测试有持仓的盈亏归因."""
        manager = PortfolioManager()
        manager.update_position("rb2501", 10, "arb", avg_price=4000.0)
        manager.update_position("rb2501", 5, "trend", avg_price=4100.0)
        manager.update_position("au2506", 3, "arb", avg_price=500.0)

        analytics = PortfolioAnalytics(manager)
        attr = analytics.compute_pnl_attribution()

        # 应该按合约和策略聚合
        assert "rb2501" in attr.by_symbol
        assert "arb" in attr.by_strategy

    def test_compute_sharpe_ratio_empty(self) -> None:
        """测试空收益夏普比率."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        sharpe = analytics.compute_sharpe_ratio([])
        assert sharpe == 0.0

    def test_compute_sharpe_ratio_single(self) -> None:
        """测试单收益夏普比率."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        sharpe = analytics.compute_sharpe_ratio([0.01])
        assert sharpe == 0.0

    def test_compute_sharpe_ratio_positive(self) -> None:
        """测试正收益夏普比率."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 稳定正收益，高夏普
        returns = [0.01] * 100
        sharpe = analytics.compute_sharpe_ratio(returns)
        # 由于方差为0，应该返回0
        assert sharpe == 0.0

    def test_compute_sharpe_ratio_variable(self) -> None:
        """测试波动收益夏普比率."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 有波动的收益
        returns = [0.02, -0.01, 0.015, -0.005, 0.01] * 20
        sharpe = analytics.compute_sharpe_ratio(returns)
        assert isinstance(sharpe, float)

    def test_compute_sharpe_ratio_with_risk_free(self) -> None:
        """测试带无风险利率的夏普比率."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        returns = [0.02, 0.01, 0.015, 0.008, 0.012] * 20
        sharpe = analytics.compute_sharpe_ratio(returns, risk_free_rate=0.0001)
        assert isinstance(sharpe, float)

    def test_compute_max_drawdown_empty(self) -> None:
        """测试空权益曲线最大回撤."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        dd = analytics.compute_max_drawdown([])
        assert dd == 0.0

    def test_compute_max_drawdown_single(self) -> None:
        """测试单点权益曲线最大回撤."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        dd = analytics.compute_max_drawdown([100.0])
        assert dd == 0.0

    def test_compute_max_drawdown_increasing(self) -> None:
        """测试递增权益曲线最大回撤."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 只涨不跌，无回撤
        curve = [100, 110, 120, 130, 140]
        dd = analytics.compute_max_drawdown(curve)
        assert dd == 0.0

    def test_compute_max_drawdown_with_drop(self) -> None:
        """测试有下跌的最大回撤."""
        manager = PortfolioManager()
        analytics = PortfolioAnalytics(manager)

        # 100 -> 120 -> 100 -> 110, 最大回撤 = (120-100)/120 = 16.67%
        curve = [100, 120, 100, 110]
        dd = analytics.compute_max_drawdown(curve)
        assert abs(dd - 0.1667) < 0.01


class TestPositionAggregatorEnhanced:
    """持仓聚合器增强测试."""

    def test_add_snapshot_with_metadata(self) -> None:
        """测试添加带元数据的快照."""
        agg = PositionAggregator()
        data = {
            "positions": [],
            "total_realized_pnl": 100.0,
            "total_unrealized_pnl": 50.0,
        }
        metadata = {"source": "test", "version": 1}

        snapshot = agg.add_snapshot(data, metadata)
        assert snapshot.metadata["source"] == "test"
        assert snapshot.total_pnl == 150.0

    def test_add_snapshot_trim_history(self) -> None:
        """测试快照历史裁剪."""
        agg = PositionAggregator(max_history=5)

        for i in range(10):
            agg.add_snapshot({"positions": [], "total_realized_pnl": i})

        assert agg.snapshot_count == 5
        history = agg.get_history()
        # 应该保留最新的5个
        assert history[0].total_pnl == 5.0

    def test_aggregate_positions_complex(self) -> None:
        """测试复杂持仓聚合."""
        agg = PositionAggregator()
        data = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "quantity": 10,
                    "strategy": "arb",
                    "avg_price": 4000.0,
                    "realized_pnl": 100.0,
                    "unrealized_pnl": 50.0,
                },
                {
                    "symbol": "rb2501",
                    "quantity": -5,
                    "strategy": "hedge",
                    "avg_price": 4050.0,
                    "realized_pnl": -20.0,
                    "unrealized_pnl": 30.0,
                },
                {
                    "symbol": "au2506",
                    "quantity": 3,
                    "strategy": "arb",
                    "avg_price": 500.0,
                    "realized_pnl": 10.0,
                    "unrealized_pnl": 5.0,
                },
            ],
        }

        snapshot = agg.add_snapshot(data)
        assert len(snapshot.positions) == 2  # rb2501和au2506

        # 找到rb2501的聚合持仓
        rb_pos = next((p for p in snapshot.positions if p.symbol == "rb2501"), None)
        assert rb_pos is not None
        assert rb_pos.net_quantity == 5  # 10 - 5
        assert rb_pos.gross_quantity == 15  # 10 + 5
        assert len(rb_pos.strategies) == 2

    def test_get_history_with_limit(self) -> None:
        """测试获取限制数量的历史."""
        agg = PositionAggregator()

        for i in range(10):
            agg.add_snapshot({"positions": [], "total_realized_pnl": i})

        history = agg.get_history(limit=3)
        assert len(history) == 3

    def test_get_pnl_series(self) -> None:
        """测试获取盈亏序列."""
        agg = PositionAggregator()

        for i in range(5):
            agg.add_snapshot({"positions": [], "total_realized_pnl": i * 100})

        series = agg.get_pnl_series()
        assert len(series) == 5
        assert series[0][1] == 0.0
        assert series[4][1] == 400.0

    def test_snapshot_count_property(self) -> None:
        """测试快照计数属性."""
        agg = PositionAggregator()
        assert agg.snapshot_count == 0

        agg.add_snapshot({"positions": []})
        assert agg.snapshot_count == 1

        agg.add_snapshot({"positions": []})
        assert agg.snapshot_count == 2


class TestAggregatedPositionEnhanced:
    """聚合持仓增强测试."""

    def test_to_dict_complete(self) -> None:
        """测试完整转字典."""
        pos = AggregatedPosition(
            symbol="rb2501",
            net_quantity=10,
            gross_quantity=15,
            strategies=["arb", "trend"],
            avg_price=4000.0,
            total_pnl=500.0,
        )
        d = pos.to_dict()
        assert d["symbol"] == "rb2501"
        assert d["net_quantity"] == 10
        assert d["gross_quantity"] == 15
        assert d["strategies"] == ["arb", "trend"]
        assert d["avg_price"] == 4000.0
        assert d["total_pnl"] == 500.0


class TestPositionSnapshotEnhanced:
    """持仓快照增强测试."""

    def test_to_dict_with_positions(self) -> None:
        """测试带持仓的转字典."""
        pos1 = AggregatedPosition("rb2501", 10, 10, ["arb"], 4000.0, 100.0)
        pos2 = AggregatedPosition("au2506", 5, 5, ["trend"], 500.0, 50.0)

        snapshot = PositionSnapshot(
            ts=1000.0,
            positions=[pos1, pos2],
            total_pnl=150.0,
            metadata={"source": "test"},
        )
        d = snapshot.to_dict()

        assert d["ts"] == 1000.0
        assert len(d["positions"]) == 2
        assert d["total_pnl"] == 150.0
        assert d["metadata"]["source"] == "test"
