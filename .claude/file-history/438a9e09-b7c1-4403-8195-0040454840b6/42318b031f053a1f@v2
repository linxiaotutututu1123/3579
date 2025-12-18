"""
CostEstimator 测试.

V2 Scenarios:
- COST.MODEL.FEE_ESTIMATE: 手续费估计
- COST.MODEL.SLIPPAGE_ESTIMATE: 滑点估计
- COST.MODEL.IMPACT_ESTIMATE: 市场冲击估计
- COST.GATE.EDGE_CHECK: edge gate 检查
"""

from src.cost.estimator import CostBreakdown, CostEstimator


class TestCostEstimator:
    """CostEstimator 测试类."""

    def test_cost_model_fee_estimate_basic(self) -> None:
        """COST.MODEL.FEE_ESTIMATE: 基本手续费估计."""
        estimator = CostEstimator()

        # 名义金额 100000，默认费率 0.0001
        fee = estimator.fee_estimate("AO2501", notional=100000.0)

        # 100000 * 0.0001 = 10
        assert fee == 10.0

    def test_cost_model_fee_estimate_custom_rate(self) -> None:
        """COST.MODEL.FEE_ESTIMATE: 自定义费率."""
        estimator = CostEstimator(fee_rates={"AO": 0.0002})

        fee = estimator.fee_estimate("AO2501", notional=100000.0)

        # 100000 * 0.0002 = 20
        assert fee == 20.0

    def test_cost_model_fee_estimate_close_today(self) -> None:
        """COST.MODEL.FEE_ESTIMATE: 平今加收."""
        estimator = CostEstimator()

        fee_normal = estimator.fee_estimate("AO2501", notional=100000.0)
        fee_close_today = estimator.fee_estimate(
            "AO2501", notional=100000.0, is_close_today=True
        )

        # 平今加收 3 倍
        assert fee_close_today == fee_normal * CostEstimator.CLOSE_TODAY_MULTIPLIER

    def test_cost_model_fee_estimate_set_rate(self) -> None:
        """COST.MODEL.FEE_ESTIMATE: 动态设置费率."""
        estimator = CostEstimator()

        estimator.set_fee_rate("SA", 0.0003)
        fee = estimator.fee_estimate("SA2501", notional=100000.0)

        # 100000 * 0.0003 = 30
        assert fee == 30.0

    def test_cost_model_fee_estimate_get_rate(self) -> None:
        """COST.MODEL.FEE_ESTIMATE: 获取费率."""
        estimator = CostEstimator(fee_rates={"AO": 0.0002})

        assert estimator.get_fee_rate("AO") == 0.0002
        assert estimator.get_fee_rate("UNKNOWN") == CostEstimator.DEFAULT_FEE_RATE

    def test_cost_model_slippage_estimate_basic(self) -> None:
        """COST.MODEL.SLIPPAGE_ESTIMATE: 基本滑点估计."""
        estimator = CostEstimator()

        # qty=10, depth=100
        slippage = estimator.slippage_estimate("AO2501", qty=10, depth=100)

        # 滑点 = 0.5 * (1 + 10/100) * 1.0 * 10 * 10 = 0.5 * 1.1 * 100 = 55
        expected = CostEstimator.SLIPPAGE_BASE_TICKS * (1.0 + 10 / 100) * 1.0 * 10 * 10
        assert slippage == expected

    def test_cost_model_slippage_estimate_zero_depth(self) -> None:
        """COST.MODEL.SLIPPAGE_ESTIMATE: 深度为零时使用保守估计."""
        estimator = CostEstimator()

        # depth=0 时默认为 1
        slippage = estimator.slippage_estimate("AO2501", qty=10, depth=0)

        # 滑点 = 0.5 * (1 + 10/1) * 1.0 * 10 * 10 = 0.5 * 11 * 100 = 550
        expected = CostEstimator.SLIPPAGE_BASE_TICKS * (1.0 + 10 / 1) * 1.0 * 10 * 10
        assert slippage == expected

    def test_cost_model_slippage_estimate_large_qty(self) -> None:
        """COST.MODEL.SLIPPAGE_ESTIMATE: 大单量滑点更大."""
        estimator = CostEstimator()

        small_qty = estimator.slippage_estimate("AO2501", qty=10, depth=100)
        large_qty = estimator.slippage_estimate("AO2501", qty=50, depth=100)

        assert large_qty > small_qty

    def test_cost_model_impact_estimate_basic(self) -> None:
        """COST.MODEL.IMPACT_ESTIMATE: 基本市场冲击估计."""
        estimator = CostEstimator()

        # qty=100, adv=10000
        impact = estimator.impact_estimate("AO2501", qty=100, adv=10000.0)

        # participation = 100/10000 = 0.01
        # impact_ticks = 0.1 * sqrt(0.01) * 100 = 0.1 * 0.1 * 100 = 1
        # impact = 1 * 1.0 * 10 * 100 = 1000
        assert impact > 0

    def test_cost_model_impact_estimate_zero_adv(self) -> None:
        """COST.MODEL.IMPACT_ESTIMATE: ADV为零时使用保守估计."""
        estimator = CostEstimator()

        # adv=0 时默认为 1000
        impact = estimator.impact_estimate("AO2501", qty=100, adv=0)

        assert impact > 0

    def test_cost_model_impact_estimate_small_qty(self) -> None:
        """COST.MODEL.IMPACT_ESTIMATE: 小单量冲击小."""
        estimator = CostEstimator()

        small_impact = estimator.impact_estimate("AO2501", qty=10, adv=10000.0)
        large_impact = estimator.impact_estimate("AO2501", qty=100, adv=10000.0)

        assert small_impact < large_impact

    def test_cost_gate_edge_check_pass(self) -> None:
        """COST.GATE.EDGE_CHECK: edge 大于成本时通过."""
        estimator = CostEstimator()

        # signal_edge > total_cost
        passed = estimator.edge_gate(signal_edge=100.0, total_cost=50.0)

        assert passed is True

    def test_cost_gate_edge_check_fail(self) -> None:
        """COST.GATE.EDGE_CHECK: edge 小于成本时不通过."""
        estimator = CostEstimator()

        # signal_edge < total_cost
        passed = estimator.edge_gate(signal_edge=30.0, total_cost=50.0)

        assert passed is False

    def test_cost_gate_edge_check_equal(self) -> None:
        """COST.GATE.EDGE_CHECK: edge 等于成本时不通过."""
        estimator = CostEstimator()

        # signal_edge == total_cost
        passed = estimator.edge_gate(signal_edge=50.0, total_cost=50.0)

        assert passed is False

    def test_cost_gate_edge_check_with_breakdown(self) -> None:
        """COST.GATE.EDGE_CHECK: 带分解的 edge gate 检查."""
        estimator = CostEstimator()

        cost = CostBreakdown(fee=10.0, slippage=20.0, impact=20.0, total=50.0)

        passed, net_edge = estimator.edge_gate_with_breakdown(
            signal_edge=100.0, cost=cost
        )

        assert passed is True
        assert net_edge == 50.0

    def test_cost_gate_edge_check_with_breakdown_fail(self) -> None:
        """COST.GATE.EDGE_CHECK: 带分解的 edge gate 检查失败."""
        estimator = CostEstimator()

        cost = CostBreakdown(fee=10.0, slippage=20.0, impact=20.0, total=50.0)

        passed, net_edge = estimator.edge_gate_with_breakdown(
            signal_edge=30.0, cost=cost
        )

        assert passed is False
        assert net_edge == -20.0

    def test_total_cost_breakdown(self) -> None:
        """测试总成本分解."""
        estimator = CostEstimator()

        cost = estimator.total_cost(
            symbol="AO2501",
            qty=10,
            notional=100000.0,
            depth=100,
            adv=10000.0,
        )

        assert isinstance(cost, CostBreakdown)
        assert cost.fee > 0
        assert cost.slippage > 0
        assert cost.impact > 0
        assert cost.total == cost.fee + cost.slippage + cost.impact

    def test_total_cost_close_today(self) -> None:
        """测试平今总成本."""
        estimator = CostEstimator()

        cost_normal = estimator.total_cost(
            symbol="AO2501",
            qty=10,
            notional=100000.0,
            depth=100,
            adv=10000.0,
            is_close_today=False,
        )

        cost_close_today = estimator.total_cost(
            symbol="AO2501",
            qty=10,
            notional=100000.0,
            depth=100,
            adv=10000.0,
            is_close_today=True,
        )

        # 平今手续费更高
        assert cost_close_today.fee > cost_normal.fee
        # 滑点和冲击相同
        assert cost_close_today.slippage == cost_normal.slippage
        assert cost_close_today.impact == cost_normal.impact

    def test_cost_breakdown_per_unit(self) -> None:
        """测试成本分解的 per_unit 属性."""
        cost = CostBreakdown(fee=10.0, slippage=20.0, impact=30.0, total=60.0)

        assert cost.per_unit == 60.0

    def test_extract_product_from_symbol(self) -> None:
        """测试从合约代码提取品种."""
        estimator = CostEstimator()

        # 通过设置费率间接验证品种提取
        estimator.set_fee_rate("AO", 0.0002)
        fee = estimator.fee_estimate("AO2501", notional=100000.0)

        # 如果品种提取正确，应该使用 AO 的费率
        assert fee == 100000.0 * 0.0002

    def test_extract_product_mixed_symbols(self) -> None:
        """测试不同格式的合约代码."""
        estimator = CostEstimator(fee_rates={"SA": 0.0003, "rb": 0.0002})

        fee_sa = estimator.fee_estimate("SA2501", notional=100000.0)
        fee_rb = estimator.fee_estimate("rb2505", notional=100000.0)

        assert fee_sa == 100000.0 * 0.0003
        assert fee_rb == 100000.0 * 0.0002

    def test_default_tick_size_and_multiplier(self) -> None:
        """测试默认 tick_size 和 multiplier."""
        estimator = CostEstimator()

        # 没有 instrument_cache 时使用默认值
        # 默认 tick_size=1.0, multiplier=10
        slippage = estimator.slippage_estimate("AO2501", qty=10, depth=100)

        # 滑点 = 0.5 * (1 + 0.1) * 1.0 * 10 * 10 = 55
        expected = 0.5 * 1.1 * 1.0 * 10 * 10
        assert slippage == expected
