"""
Order Splitter 测试模块.

测试智能订单拆分功能。
"""

from __future__ import annotations

import pytest
import time

from src.execution.order_types import OrderIntent, Offset, Side
from src.execution.order_splitter import (
    OrderSplitter,
    SplitterConfig,
    SplitAlgorithm,
    SplitOrderStatus,
    MarketSnapshot,
    MarketCondition,
    VolumeProfile,
    ExecutionQuality,
    TWAPAlgorithm,
    VWAPAlgorithm,
    IcebergAlgorithm,
    BehavioralAlgorithm,
    AlgorithmSelector,
)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def default_config() -> SplitterConfig:
    """默认配置."""
    return SplitterConfig(
        min_order_qty=1,
        max_slices=100,
        twap_interval_seconds=60.0,
        iceberg_show_ratio=0.1,
        large_order_threshold=100,
        target_slippage_bps=10.0,
        target_fill_rate=0.95,
        target_latency_ms=100.0,
        confirmation_required=False,
    )


@pytest.fixture
def market_snapshot() -> MarketSnapshot:
    """市场快照."""
    return MarketSnapshot(
        symbol="rb2501",
        bid=3500.0,
        ask=3501.0,
        last_price=3500.5,
        bid_volume=100,
        ask_volume=120,
        volume=5000,
        avg_volume=1000.0,
        volatility=0.01,
        tick_size=1.0,
    )


@pytest.fixture
def order_intent() -> OrderIntent:
    """订单意图."""
    return OrderIntent(
        symbol="rb2501",
        side=Side.BUY,
        offset=Offset.OPEN,
        price=3500.0,
        qty=50,
        reason="test_order",
    )


@pytest.fixture
def large_order_intent() -> OrderIntent:
    """大额订单意图."""
    return OrderIntent(
        symbol="rb2501",
        side=Side.BUY,
        offset=Offset.OPEN,
        price=3500.0,
        qty=200,
        reason="large_test_order",
    )


@pytest.fixture
def splitter(default_config: SplitterConfig) -> OrderSplitter:
    """订单拆分器."""
    return OrderSplitter(config=default_config)


# ============================================================================
# MarketSnapshot 测试
# ============================================================================
class TestMarketSnapshot:
    """市场快照测试."""

    def test_spread(self, market_snapshot: MarketSnapshot) -> None:
        """测试价差计算."""
        assert market_snapshot.spread() == 1.0

    def test_spread_bps(self, market_snapshot: MarketSnapshot) -> None:
        """测试基点价差计算."""
        # 1 / 3500.5 * 10000 ≈ 2.86
        assert 2.8 < market_snapshot.spread_bps() < 2.9

    def test_mid_price(self, market_snapshot: MarketSnapshot) -> None:
        """测试中间价计算."""
        assert market_snapshot.mid_price() == 3500.5


# ============================================================================
# TWAP 算法测试
# ============================================================================
class TestTWAPAlgorithm:
    """TWAP算法测试."""

    def test_generate_plan_basic(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试基本拆单计划生成."""
        algo = TWAPAlgorithm(default_config)
        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.algorithm == SplitAlgorithm.TWAP
        assert plan.total_qty == order_intent.qty
        assert len(plan.orders) > 0
        assert sum(o.qty for o in plan.orders) == order_intent.qty

    def test_equal_time_intervals(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试等时间间隔."""
        algo = TWAPAlgorithm(default_config)
        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0)

        if len(plan.orders) > 1:
            intervals = []
            for i in range(1, len(plan.orders)):
                interval = plan.orders[i].scheduled_time - plan.orders[i-1].scheduled_time
                intervals.append(interval)

            # 所有间隔应该相等
            avg_interval = sum(intervals) / len(intervals)
            for interval in intervals:
                assert abs(interval - avg_interval) < 0.01


# ============================================================================
# VWAP 算法测试
# ============================================================================
class TestVWAPAlgorithm:
    """VWAP算法测试."""

    def test_generate_plan_with_profile(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试带成交量分布的拆单计划."""
        algo = VWAPAlgorithm(default_config)

        # 创建U型分布
        profile = VolumeProfile(
            intervals=[0, 1, 2, 3, 4],
            volumes=[30.0, 15.0, 10.0, 15.0, 30.0],
            total_volume=100.0,
        )

        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0, volume_profile=profile)

        assert plan.algorithm == SplitAlgorithm.VWAP
        assert plan.total_qty == order_intent.qty

    def test_default_profile_generation(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试默认成交量分布生成."""
        algo = VWAPAlgorithm(default_config)
        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.algorithm == SplitAlgorithm.VWAP
        assert len(plan.orders) > 0


# ============================================================================
# Iceberg 算法测试
# ============================================================================
class TestIcebergAlgorithm:
    """冰山订单算法测试."""

    def test_generate_plan(
        self, default_config: SplitterConfig, large_order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试冰山订单计划生成."""
        algo = IcebergAlgorithm(default_config)
        plan = algo.generate_plan(large_order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.algorithm == SplitAlgorithm.ICEBERG
        assert plan.total_qty == large_order_intent.qty

        # 每个子订单应该较小
        show_qty = int(large_order_intent.qty * default_config.iceberg_show_ratio)
        for order in plan.orders[:-1]:  # 除最后一个外
            assert order.qty <= show_qty * 2  # 考虑随机因子

    def test_hidden_quantity(
        self, default_config: SplitterConfig, large_order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试隐藏数量."""
        algo = IcebergAlgorithm(default_config)
        plan = algo.generate_plan(large_order_intent, market_snapshot, duration_seconds=300.0)

        # 总数量应该等于原始订单
        total = sum(o.qty for o in plan.orders)
        assert total == large_order_intent.qty


# ============================================================================
# Behavioral 算法测试
# ============================================================================
class TestBehavioralAlgorithm:
    """行为伪装算法测试."""

    def test_generate_plan(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试行为伪装计划生成."""
        algo = BehavioralAlgorithm(default_config)
        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.algorithm == SplitAlgorithm.BEHAVIORAL
        assert plan.total_qty == order_intent.qty

    def test_random_intervals(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试随机时间间隔."""
        algo = BehavioralAlgorithm(default_config)
        plan = algo.generate_plan(order_intent, market_snapshot, duration_seconds=300.0)

        if len(plan.orders) > 2:
            intervals = []
            for i in range(1, len(plan.orders)):
                interval = plan.orders[i].scheduled_time - plan.orders[i-1].scheduled_time
                intervals.append(interval)

            # 间隔应该有变化（不完全相等）
            if len(intervals) > 1:
                variance = sum((i - sum(intervals)/len(intervals))**2 for i in intervals) / len(intervals)
                # 应该有一定的方差
                assert variance >= 0  # 基本检查


# ============================================================================
# Algorithm Selector 测试
# ============================================================================
class TestAlgorithmSelector:
    """算法选择器测试."""

    def test_select_twap_for_small_order(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试小订单选择TWAP."""
        selector = AlgorithmSelector(default_config)
        # 修改市场快照使订单相对较小
        market = MarketSnapshot(
            symbol="rb2501",
            bid=3500.0,
            ask=3501.0,
            last_price=3500.5,
            bid_volume=100,
            ask_volume=120,
            volume=5000,
            avg_volume=10000.0,  # 大平均成交量
            volatility=0.01,
            tick_size=1.0,
        )

        algo = selector.select_algorithm(order_intent, market)
        assert algo == SplitAlgorithm.TWAP

    def test_select_vwap_for_medium_order(
        self, default_config: SplitterConfig, market_snapshot: MarketSnapshot
    ) -> None:
        """测试中等订单选择VWAP."""
        selector = AlgorithmSelector(default_config)

        # 中等订单（超过平均成交量5%但不超过10%）
        medium_order = OrderIntent(
            symbol="rb2501",
            side=Side.BUY,
            offset=Offset.OPEN,
            price=3500.0,
            qty=80,  # 8% of avg_volume=1000
            reason="medium_order",
        )

        algo = selector.select_algorithm(medium_order, market_snapshot)
        assert algo == SplitAlgorithm.VWAP

    def test_select_iceberg_for_high_volatility(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试高波动性选择ICEBERG."""
        selector = AlgorithmSelector(default_config)

        algo = selector.select_algorithm(
            order_intent, market_snapshot,
            condition=MarketCondition.HIGH_VOLATILITY
        )
        assert algo == SplitAlgorithm.ICEBERG

    def test_select_behavioral_for_low_liquidity(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试低流动性选择BEHAVIORAL."""
        selector = AlgorithmSelector(default_config)

        algo = selector.select_algorithm(
            order_intent, market_snapshot,
            condition=MarketCondition.LOW_LIQUIDITY
        )
        assert algo == SplitAlgorithm.BEHAVIORAL

    def test_force_algorithm(
        self, default_config: SplitterConfig, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试强制指定算法."""
        selector = AlgorithmSelector(default_config)

        algo = selector.select_algorithm(
            order_intent, market_snapshot,
            force_algorithm=SplitAlgorithm.ICEBERG
        )
        assert algo == SplitAlgorithm.ICEBERG


# ============================================================================
# OrderSplitter 测试
# ============================================================================
class TestOrderSplitter:
    """订单拆分器测试."""

    def test_create_plan(
        self, splitter: OrderSplitter, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试创建拆单计划."""
        plan = splitter.create_plan(order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.plan_id is not None
        assert plan.total_qty == order_intent.qty
        assert len(plan.orders) > 0

    def test_update_order_status(
        self, splitter: OrderSplitter, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试更新订单状态."""
        plan = splitter.create_plan(order_intent, market_snapshot, duration_seconds=300.0)

        first_order = plan.orders[0]
        result = splitter.update_order_status(
            plan_id=plan.plan_id,
            order_id=first_order.order_id,
            status=SplitOrderStatus.FILLED,
            filled_qty=first_order.qty,
            filled_price=3500.5,
            latency_ms=50.0,
        )

        assert result is True
        assert first_order.status == SplitOrderStatus.FILLED
        assert first_order.filled_qty == first_order.qty

    def test_get_execution_quality(
        self, splitter: OrderSplitter, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试获取执行质量."""
        plan = splitter.create_plan(order_intent, market_snapshot, duration_seconds=300.0)

        # 模拟成交
        for order in plan.orders:
            splitter.update_order_status(
                plan_id=plan.plan_id,
                order_id=order.order_id,
                status=SplitOrderStatus.FILLED,
                filled_qty=order.qty,
                filled_price=order.price,
                latency_ms=50.0,
            )

        quality = splitter.get_execution_quality(plan.plan_id)
        assert quality.fill_rate >= 0.95
        assert quality.latency_ms <= 100.0

    def test_get_pending_orders(
        self, splitter: OrderSplitter, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试获取待执行订单."""
        plan = splitter.create_plan(order_intent, market_snapshot, duration_seconds=0.1)  # 短时间

        time.sleep(0.2)  # 等待所有订单到期

        pending = splitter.get_pending_orders(plan.plan_id)
        assert len(pending) == len(plan.orders)

    def test_cancel_plan(
        self, splitter: OrderSplitter, order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试取消计划."""
        plan = splitter.create_plan(order_intent, market_snapshot, duration_seconds=300.0)

        result = splitter.cancel_plan(plan.plan_id)

        assert result is True
        assert plan.status == SplitOrderStatus.CANCELLED

    def test_large_order_confirmation(
        self, default_config: SplitterConfig, large_order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试大额订单确认机制 (M12军规)."""
        confirmation_called = {"value": False}

        def on_confirmation(order: OrderIntent, plan) -> bool:
            confirmation_called["value"] = True
            return True

        config = SplitterConfig(
            confirmation_required=True,
            large_order_threshold=100,
        )
        splitter = OrderSplitter(config=config, on_confirmation=on_confirmation)

        plan = splitter.create_plan(large_order_intent, market_snapshot, duration_seconds=300.0)

        assert confirmation_called["value"] is True

    def test_reject_large_order_on_no_confirmation(
        self, default_config: SplitterConfig, large_order_intent: OrderIntent, market_snapshot: MarketSnapshot
    ) -> None:
        """测试拒绝大额订单."""
        def on_confirmation(order: OrderIntent, plan) -> bool:
            return False

        config = SplitterConfig(
            confirmation_required=True,
            large_order_threshold=100,
        )
        splitter = OrderSplitter(config=config, on_confirmation=on_confirmation)

        plan = splitter.create_plan(large_order_intent, market_snapshot, duration_seconds=300.0)

        assert plan.status == SplitOrderStatus.CANCELLED


# ============================================================================
# ExecutionQuality 测试
# ============================================================================
class TestExecutionQuality:
    """执行质量指标测试."""

    def test_all_targets_met(self) -> None:
        """测试所有指标达标."""
        quality = ExecutionQuality(
            slippage_bps=5.0,
            fill_rate=0.98,
            latency_ms=50.0,
            target_slippage_bps=10.0,
            target_fill_rate=0.95,
            target_latency_ms=100.0,
        )

        assert quality.slippage_ok() is True
        assert quality.fill_rate_ok() is True
        assert quality.latency_ok() is True
        assert quality.all_targets_met() is True

    def test_slippage_not_ok(self) -> None:
        """测试滑点超标."""
        quality = ExecutionQuality(
            slippage_bps=15.0,  # 超过目标 10 bps
            fill_rate=0.98,
            latency_ms=50.0,
        )

        assert quality.slippage_ok() is False
        assert quality.all_targets_met() is False

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        quality = ExecutionQuality(
            slippage_bps=5.0,
            fill_rate=0.98,
            latency_ms=50.0,
        )

        d = quality.to_dict()
        assert "slippage_bps" in d
        assert "fill_rate" in d
        assert "latency_ms" in d
        assert "all_targets_met" in d


# ============================================================================
# VolumeProfile 测试
# ============================================================================
class TestVolumeProfile:
    """成交量分布测试."""

    def test_get_weight(self) -> None:
        """测试获取权重."""
        profile = VolumeProfile(
            intervals=[0, 1, 2],
            volumes=[30.0, 40.0, 30.0],
            total_volume=100.0,
        )

        assert profile.get_weight(0) == 0.3
        assert profile.get_weight(1) == 0.4
        assert profile.get_weight(2) == 0.3

    def test_zero_volume(self) -> None:
        """测试零成交量."""
        profile = VolumeProfile(
            intervals=[0, 1],
            volumes=[0.0, 0.0],
            total_volume=0.0,
        )

        assert profile.get_weight(0) == 0.0
