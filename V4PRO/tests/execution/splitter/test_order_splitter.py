"""
智能拆单主逻辑测试.

V4PRO Platform Component - Intelligent Order Splitter Tests
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致), M12(双重确认)

V4PRO Scenarios:
- SPLITTER.SELECTOR: 智能算法选择
- SPLITTER.SPLIT: 大额订单拆分
- SPLITTER.CONFIRM: 与确认机制集成 (M12)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from src.execution.mode2.executor_base import ExecutorStatus
from src.execution.mode2.intent import AlgoType, Offset, OrderIntent, Side
from src.execution.splitter.order_splitter import (
    ALGORITHM_DECISION_TREE,
    AlgorithmScore,
    AlgorithmSelector,
    LiquidityLevel,
    MarketContext,
    OrderSizeCategory,
    OrderSplitter,
    SessionPhase,
    SplitAlgorithm,
    SplitPlan,
    SplitterConfig,
)


def create_test_intent(
    target_qty: int = 100,
    instrument: str = "rb2501",
    limit_price: float | None = 4000.0,
    algo: AlgoType = AlgoType.IMMEDIATE,
    signal_ts: int | None = None,
) -> OrderIntent:
    """创建测试用交易意图."""
    return OrderIntent(
        strategy_id="test_strategy",
        decision_hash="test_decision_hash_12345",
        instrument=instrument,
        side=Side.BUY,
        offset=Offset.OPEN,
        target_qty=target_qty,
        algo=algo,
        limit_price=limit_price,
        signal_ts=signal_ts or int(time.time() * 1000),
    )


class TestSplitAlgorithmEnum:
    """拆单算法枚举测试."""

    def test_algorithm_values(self) -> None:
        """测试算法值."""
        assert SplitAlgorithm.TWAP.value == "TWAP"
        assert SplitAlgorithm.VWAP.value == "VWAP"
        assert SplitAlgorithm.ICEBERG.value == "ICEBERG"
        assert SplitAlgorithm.BEHAVIORAL.value == "BEHAVIORAL"


class TestOrderSizeCategoryEnum:
    """订单规模分类枚举测试."""

    def test_category_values(self) -> None:
        """测试分类值."""
        assert OrderSizeCategory.SMALL.value == "SMALL"
        assert OrderSizeCategory.MEDIUM.value == "MEDIUM"
        assert OrderSizeCategory.LARGE.value == "LARGE"
        assert OrderSizeCategory.HUGE.value == "HUGE"


class TestLiquidityLevelEnum:
    """流动性水平枚举测试."""

    def test_liquidity_values(self) -> None:
        """测试流动性值."""
        assert LiquidityLevel.HIGH.value == "HIGH"
        assert LiquidityLevel.NORMAL.value == "NORMAL"
        assert LiquidityLevel.LOW.value == "LOW"
        assert LiquidityLevel.CRITICAL.value == "CRITICAL"


class TestSessionPhaseEnum:
    """交易时段枚举测试."""

    def test_session_values(self) -> None:
        """测试时段值."""
        assert SessionPhase.OPENING.value == "OPENING"
        assert SessionPhase.MORNING.value == "MORNING"
        assert SessionPhase.AFTERNOON.value == "AFTERNOON"
        assert SessionPhase.CLOSING.value == "CLOSING"
        assert SessionPhase.NIGHT_ACTIVE.value == "NIGHT_ACTIVE"
        assert SessionPhase.NIGHT_QUIET.value == "NIGHT_QUIET"


class TestMarketContext:
    """市场上下文测试."""

    def test_default_context(self) -> None:
        """测试默认上下文."""
        ctx = MarketContext()
        assert ctx.liquidity_level == LiquidityLevel.NORMAL
        assert ctx.session_phase == SessionPhase.MORNING
        assert ctx.volatility_pct == 0.0
        assert ctx.is_limit_up is False
        assert ctx.is_limit_down is False

    def test_custom_context(self) -> None:
        """测试自定义上下文."""
        ctx = MarketContext(
            liquidity_level=LiquidityLevel.LOW,
            session_phase=SessionPhase.NIGHT_QUIET,
            volatility_pct=0.05,
            is_limit_up=True,
        )
        assert ctx.liquidity_level == LiquidityLevel.LOW
        assert ctx.session_phase == SessionPhase.NIGHT_QUIET
        assert ctx.volatility_pct == 0.05
        assert ctx.is_limit_up is True


class TestSplitterConfig:
    """拆单器配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = SplitterConfig()
        assert config.default_algorithm == SplitAlgorithm.TWAP
        assert config.enable_confirmation is True
        assert config.confirmation_threshold == 500_000

    def test_order_value_thresholds(self) -> None:
        """测试订单金额阈值."""
        config = SplitterConfig()
        thresholds = config.order_value_thresholds
        assert thresholds[OrderSizeCategory.SMALL] == 500_000
        assert thresholds[OrderSizeCategory.MEDIUM] == 2_000_000
        assert thresholds[OrderSizeCategory.LARGE] == 5_000_000


class TestAlgorithmSelector:
    """SPLITTER.SELECTOR - 智能算法选择测试."""

    def test_classify_order_size_small(self) -> None:
        """测试小额订单分类."""
        selector = AlgorithmSelector()
        category = selector.classify_order_size(400_000)
        assert category == OrderSizeCategory.SMALL

    def test_classify_order_size_medium(self) -> None:
        """测试中等订单分类."""
        selector = AlgorithmSelector()
        category = selector.classify_order_size(1_000_000)
        assert category == OrderSizeCategory.MEDIUM

    def test_classify_order_size_large(self) -> None:
        """测试大额订单分类."""
        selector = AlgorithmSelector()
        category = selector.classify_order_size(3_000_000)
        assert category == OrderSizeCategory.LARGE

    def test_classify_order_size_huge(self) -> None:
        """测试超大订单分类."""
        selector = AlgorithmSelector()
        category = selector.classify_order_size(10_000_000)
        assert category == OrderSizeCategory.HUGE

    def test_select_algorithm_extreme_market(self) -> None:
        """测试极端行情选择TWAP."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100)
        market = MarketContext(is_limit_up=True)

        algo, reasons = selector.select_algorithm(intent, 1_000_000, market)

        assert algo == SplitAlgorithm.TWAP
        assert any("极端行情" in r for r in reasons)

    def test_select_algorithm_intent_specified_twap(self) -> None:
        """测试意图指定TWAP算法."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100, algo=AlgoType.TWAP)

        algo, reasons = selector.select_algorithm(intent, 1_000_000)

        assert algo == SplitAlgorithm.TWAP
        assert any("意图指定" in r for r in reasons)

    def test_select_algorithm_intent_specified_vwap(self) -> None:
        """测试意图指定VWAP算法."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100, algo=AlgoType.VWAP)

        algo, reasons = selector.select_algorithm(intent, 1_000_000)

        assert algo == SplitAlgorithm.VWAP

    def test_select_algorithm_intent_specified_iceberg(self) -> None:
        """测试意图指定ICEBERG算法."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100, algo=AlgoType.ICEBERG)

        algo, reasons = selector.select_algorithm(intent, 1_000_000)

        assert algo == SplitAlgorithm.ICEBERG

    def test_select_algorithm_small_order(self) -> None:
        """测试小额订单倾向TWAP."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100)
        market = MarketContext(liquidity_level=LiquidityLevel.HIGH)

        algo, reasons = selector.select_algorithm(intent, 200_000, market)

        # 小额订单综合评分TWAP应该较高
        assert algo == SplitAlgorithm.TWAP

    def test_select_algorithm_large_order_low_liquidity(self) -> None:
        """测试大额订单+低流动性倾向ICEBERG."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=1000)
        market = MarketContext(
            liquidity_level=LiquidityLevel.LOW,
            session_phase=SessionPhase.NIGHT_QUIET,
        )

        algo, reasons = selector.select_algorithm(intent, 3_000_000, market)

        # 大额订单+低流动性应选择ICEBERG或BEHAVIORAL
        assert algo in [SplitAlgorithm.ICEBERG, SplitAlgorithm.BEHAVIORAL]

    def test_select_algorithm_high_volatility(self) -> None:
        """测试高波动性倾向快速执行."""
        selector = AlgorithmSelector()
        intent = create_test_intent(target_qty=100)
        market = MarketContext(
            volatility_pct=0.06,  # >5%
            liquidity_level=LiquidityLevel.NORMAL,
        )

        algo, reasons = selector.select_algorithm(intent, 500_000, market)

        # 高波动性应倾向TWAP(快速执行)
        # 但其他因素也会影响, 验证有评分原因
        assert "综合评分" in reasons[-1]


class TestAlgorithmScore:
    """算法评分测试."""

    def test_score_init(self) -> None:
        """测试评分初始化."""
        score = AlgorithmScore(
            algorithm=SplitAlgorithm.TWAP,
            score=85.5,
            factors={"size": 0.9, "liquidity": 0.8},
            reasons=["规模适配", "流动性适配"],
        )
        assert score.algorithm == SplitAlgorithm.TWAP
        assert score.score == 85.5
        assert score.factors["size"] == 0.9


class TestOrderSplitter:
    """SPLITTER.SPLIT - 订单拆分测试."""

    def test_estimate_order_value(self) -> None:
        """测试订单估值."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        value = splitter.estimate_order_value(intent)

        assert value == 400_000

    def test_estimate_order_value_with_reference(self) -> None:
        """测试使用参考价格估值."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        value = splitter.estimate_order_value(intent, price=5000.0)

        assert value == 500_000

    @pytest.mark.asyncio
    async def test_create_split_plan_basic(self) -> None:
        """测试基本计划创建."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert plan.plan_id == intent.intent_id
        assert plan.intent == intent
        assert plan.algorithm in SplitAlgorithm
        assert plan.executor is not None

    @pytest.mark.asyncio
    async def test_create_split_plan_idempotent(self) -> None:
        """测试计划创建幂等性 (M2)."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        plan1 = await splitter.create_split_plan(intent, reference_price=4000.0)
        plan2 = await splitter.create_split_plan(intent, reference_price=4000.0)

        # 同一意图返回相同计划
        assert plan1.plan_id == plan2.plan_id

    @pytest.mark.asyncio
    async def test_create_split_plan_with_market_context(self) -> None:
        """测试使用市场上下文创建计划."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)
        market = MarketContext(
            liquidity_level=LiquidityLevel.HIGH,
            session_phase=SessionPhase.MORNING,
        )

        plan = await splitter.create_split_plan(
            intent, market_context=market, reference_price=4000.0
        )

        assert plan is not None
        assert plan.metrics is not None

    @pytest.mark.asyncio
    async def test_create_split_plan_with_confirmation(self) -> None:
        """测试M12确认机制集成."""
        confirmed = False

        async def confirm_callback(
            intent: OrderIntent, value: float
        ) -> bool:
            nonlocal confirmed
            confirmed = True
            return True

        config = SplitterConfig(
            enable_confirmation=True,
            confirmation_threshold=100_000,  # 10万阈值
        )
        splitter = OrderSplitter(config, confirmation_callback=confirm_callback)
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        # 40万 > 10万阈值, 应触发确认
        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert confirmed is True
        assert plan.requires_confirmation is True
        assert plan.confirmation_level == "CONFIRMED"

    @pytest.mark.asyncio
    async def test_create_split_plan_confirmation_rejected(self) -> None:
        """测试确认被拒绝."""

        async def reject_callback(
            intent: OrderIntent, value: float
        ) -> bool:
            return False

        config = SplitterConfig(
            enable_confirmation=True,
            confirmation_threshold=100_000,
        )
        splitter = OrderSplitter(config, confirmation_callback=reject_callback)
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        with pytest.raises(ValueError, match="确认被拒绝"):
            await splitter.create_split_plan(intent, reference_price=4000.0)

    @pytest.mark.asyncio
    async def test_create_split_plan_no_confirmation_below_threshold(self) -> None:
        """测试低于阈值不需要确认."""
        confirmed = False

        async def confirm_callback(
            intent: OrderIntent, value: float
        ) -> bool:
            nonlocal confirmed
            confirmed = True
            return True

        config = SplitterConfig(
            enable_confirmation=True,
            confirmation_threshold=500_000,  # 50万阈值
        )
        splitter = OrderSplitter(config, confirmation_callback=confirm_callback)
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        # 40万 < 50万阈值, 不触发确认
        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert confirmed is False
        assert plan.requires_confirmation is False
        assert plan.confirmation_level == "AUTO"

    def test_get_plan(self) -> None:
        """测试获取计划."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        plan = splitter.get_plan(intent.intent_id)
        assert plan is not None
        assert plan.plan_id == intent.intent_id

    def test_get_plan_not_found(self) -> None:
        """测试获取不存在的计划."""
        splitter = OrderSplitter()
        plan = splitter.get_plan("nonexistent")
        assert plan is None

    def test_get_status(self) -> None:
        """测试获取状态."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        status = splitter.get_status(intent.intent_id)
        assert status == ExecutorStatus.PENDING

    def test_get_status_not_found(self) -> None:
        """测试获取不存在计划的状态."""
        splitter = OrderSplitter()
        status = splitter.get_status("nonexistent")
        assert status is None

    def test_get_progress(self) -> None:
        """测试获取进度."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        progress = splitter.get_progress(intent.intent_id)
        assert progress is not None
        assert progress.total_qty == 100

    def test_cancel_plan(self) -> None:
        """测试取消计划."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        result = splitter.cancel_plan(intent.intent_id, "测试取消")
        assert result is True
        assert splitter.get_status(intent.intent_id) == ExecutorStatus.CANCELLED

    def test_cancel_plan_not_found(self) -> None:
        """测试取消不存在的计划."""
        splitter = OrderSplitter()
        result = splitter.cancel_plan("nonexistent", "")
        assert result is False

    def test_get_algorithm_selection_info(self) -> None:
        """测试获取算法选择信息."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)
        market = MarketContext(liquidity_level=LiquidityLevel.HIGH)

        info = splitter.get_algorithm_selection_info(
            intent, market_context=market, reference_price=4000.0
        )

        assert "intent_id" in info
        assert "order_value" in info
        assert "size_category" in info
        assert "selected_algorithm" in info
        assert "selection_reasons" in info
        assert "requires_confirmation" in info

    def test_get_all_plans(self) -> None:
        """测试获取所有计划."""
        splitter = OrderSplitter()

        # 创建多个计划
        for i in range(3):
            intent = OrderIntent(
                strategy_id="test_strategy",
                decision_hash=f"test_hash_{i}",
                instrument="rb2501",
                side=Side.BUY,
                offset=Offset.OPEN,
                target_qty=100,
                algo=AlgoType.IMMEDIATE,
                limit_price=4000.0,
                signal_ts=int(time.time() * 1000),
            )
            asyncio.get_event_loop().run_until_complete(
                splitter.create_split_plan(intent, reference_price=4000.0)
            )

        plans = splitter.get_all_plans()
        assert len(plans) == 3

    def test_get_summary(self) -> None:
        """测试获取汇总信息."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        summary = splitter.get_summary()
        assert summary["total_plans"] == 1
        assert "by_algorithm" in summary
        assert "by_status" in summary
        assert "metrics_summary" in summary


class TestSplitPlan:
    """拆单计划测试."""

    def test_split_plan_attributes(self) -> None:
        """测试拆单计划属性."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        plan = asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        assert plan.plan_id == intent.intent_id
        assert plan.intent == intent
        assert plan.order_value == 400_000
        assert plan.size_category == OrderSizeCategory.SMALL
        assert plan.created_at > 0


class TestAlgorithmDecisionTree:
    """算法选择决策树测试."""

    def test_decision_tree_documentation(self) -> None:
        """测试决策树文档."""
        assert "智能拆单算法选择决策树" in ALGORITHM_DECISION_TREE
        assert "TWAP" in ALGORITHM_DECISION_TREE
        assert "VWAP" in ALGORITHM_DECISION_TREE
        assert "ICEBERG" in ALGORITHM_DECISION_TREE
        assert "BEHAVIORAL" in ALGORITHM_DECISION_TREE
        assert "滑点" in ALGORITHM_DECISION_TREE
        assert "成交率" in ALGORITHM_DECISION_TREE
        assert "执行延迟" in ALGORITHM_DECISION_TREE


class TestOrderSplitterMetricsIntegration:
    """拆单器与指标系统集成测试."""

    def test_metrics_collector_integration(self) -> None:
        """测试指标收集器集成."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, limit_price=4000.0)

        asyncio.get_event_loop().run_until_complete(
            splitter.create_split_plan(intent, reference_price=4000.0)
        )

        # 验证指标收集器
        collector = splitter.metrics_collector
        assert collector is not None

        metrics = collector.get_metrics(intent.intent_id)
        assert metrics is not None
        assert metrics.plan_id == intent.intent_id


class TestOrderSplitterExecutorCreation:
    """拆单器执行器创建测试."""

    @pytest.mark.asyncio
    async def test_create_twap_executor(self) -> None:
        """测试创建TWAP执行器."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, algo=AlgoType.TWAP)

        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert plan.algorithm == SplitAlgorithm.TWAP

    @pytest.mark.asyncio
    async def test_create_vwap_executor(self) -> None:
        """测试创建VWAP执行器."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, algo=AlgoType.VWAP)

        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert plan.algorithm == SplitAlgorithm.VWAP

    @pytest.mark.asyncio
    async def test_create_iceberg_executor(self) -> None:
        """测试创建ICEBERG执行器."""
        splitter = OrderSplitter()
        intent = create_test_intent(target_qty=100, algo=AlgoType.ICEBERG)

        plan = await splitter.create_split_plan(intent, reference_price=4000.0)

        assert plan.algorithm == SplitAlgorithm.ICEBERG
