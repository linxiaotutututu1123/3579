"""成本先行机制模块测试.

V4PRO Platform Component - Phase 8

测试覆盖:
- CostFirstCalculator: 成本计算器测试
- CostValidator: 成本验证器测试
- 军规合规性测试
"""

from __future__ import annotations

import pytest

from src.execution.cost_first import (
    CostAlertLevel,
    CostCheckResult,
    CostEstimate,
    CostFirstCalculator,
    CostThresholds,
    CostValidationResult,
    CostValidator,
    MarketDepth,
    create_cost_audit_event,
)


class TestMarketDepth:
    """市场深度数据测试."""

    def test_create_basic(self) -> None:
        """测试基本创建."""
        depth = MarketDepth(bid_volume=100, ask_volume=120)
        assert depth.bid_volume == 100
        assert depth.ask_volume == 120
        assert depth.bid_price == 0.0
        assert depth.ask_price == 0.0

    def test_create_with_prices(self) -> None:
        """测试带价格创建."""
        depth = MarketDepth(
            bid_volume=100,
            ask_volume=120,
            bid_price=3500.0,
            ask_price=3501.0,
            total_bid_depth=500,
            total_ask_depth=600,
        )
        assert depth.bid_price == 3500.0
        assert depth.ask_price == 3501.0
        assert depth.total_bid_depth == 500
        assert depth.total_ask_depth == 600


class TestCostFirstCalculator:
    """成本计算器测试."""

    @pytest.fixture
    def calculator(self) -> CostFirstCalculator:
        """创建计算器实例."""
        return CostFirstCalculator()

    def test_estimate_fee_open(self, calculator: CostFirstCalculator) -> None:
        """测试开仓手续费估算."""
        fee = calculator.estimate_fee(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
            is_close_today=False,
        )
        # rb按金额收费，万分之一
        # 3500 * 10 * 10 * 0.0001 = 35.0
        assert fee == 35.0

    def test_estimate_fee_close_today(self, calculator: CostFirstCalculator) -> None:
        """测试平今手续费估算."""
        fee = calculator.estimate_fee(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="sell",
            is_close_today=True,
        )
        # rb平今同样是万分之一
        assert fee == 35.0

    def test_estimate_slippage_small_order(
        self, calculator: CostFirstCalculator
    ) -> None:
        """测试小单滑点估算."""
        depth = MarketDepth(bid_volume=100, ask_volume=120)
        slippage = calculator.estimate_slippage(
            instrument="rb2501",
            price=3500.0,
            volume=10,  # 小于对手盘50%
            direction="buy",
            market_depth=depth,
        )
        # 1 tick * 1.0 * 10 * 10 = 100.0
        assert slippage == 100.0

    def test_estimate_slippage_large_order(
        self, calculator: CostFirstCalculator
    ) -> None:
        """测试大单滑点估算."""
        depth = MarketDepth(bid_volume=100, ask_volume=50)
        slippage = calculator.estimate_slippage(
            instrument="rb2501",
            price=3500.0,
            volume=100,  # 大于对手盘
            direction="buy",
            market_depth=depth,
        )
        # volume_ratio = 100/50 = 2.0, 所以是3 tick
        # 3 tick * 1.0 * 100 * 10 = 3000.0
        assert slippage == 3000.0

    def test_estimate_slippage_no_depth(self, calculator: CostFirstCalculator) -> None:
        """测试无深度信息滑点估算."""
        slippage = calculator.estimate_slippage(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
            market_depth=None,
        )
        # 默认1 tick
        assert slippage == 100.0

    def test_estimate_impact_small_order(
        self, calculator: CostFirstCalculator
    ) -> None:
        """测试小单冲击成本估算."""
        depth = MarketDepth(
            bid_volume=100,
            ask_volume=120,
            total_bid_depth=500,
            total_ask_depth=600,
        )
        impact = calculator.estimate_impact(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            market_depth=depth,
        )
        # 小单冲击很小
        assert impact > 0
        assert impact < 50  # 应该很小

    def test_estimate_impact_large_order(
        self, calculator: CostFirstCalculator
    ) -> None:
        """测试大单冲击成本估算."""
        depth = MarketDepth(
            bid_volume=50,
            ask_volume=50,
            total_bid_depth=100,
            total_ask_depth=100,
        )
        impact = calculator.estimate_impact(
            instrument="rb2501",
            price=3500.0,
            volume=200,  # 超过五档总量
            market_depth=depth,
        )
        # 大单冲击应该较大
        assert impact > 100

    def test_estimate_total_cost(self, calculator: CostFirstCalculator) -> None:
        """测试总成本估算."""
        depth = MarketDepth(bid_volume=100, ask_volume=120)
        estimate = calculator.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
            market_depth=depth,
        )

        assert isinstance(estimate, CostEstimate)
        assert estimate.instrument == "rb2501"
        assert estimate.price == 3500.0
        assert estimate.volume == 10
        assert estimate.direction == "buy"
        assert estimate.notional == 350000.0  # 3500 * 10 * 10
        assert estimate.fee > 0
        assert estimate.slippage > 0
        assert estimate.impact >= 0
        assert estimate.total_cost == estimate.fee + estimate.slippage + estimate.impact
        assert estimate.total_ratio > 0

    def test_estimate_round_trip_cost(self, calculator: CostFirstCalculator) -> None:
        """测试往返成本估算."""
        estimate = calculator.estimate_round_trip_cost(
            instrument="rb2501",
            entry_price=3500.0,
            exit_price=3520.0,
            volume=10,
            direction="buy",
            is_intraday=True,
        )

        assert "round_trip" in estimate.direction
        # 往返成本应该是单程的两倍左右
        assert estimate.fee >= 60  # 至少两笔手续费

    def test_calc_count_increment(self, calculator: CostFirstCalculator) -> None:
        """测试计算次数统计."""
        assert calculator.calc_count == 0

        calculator.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )
        assert calculator.calc_count == 1

        calculator.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="sell",
        )
        assert calculator.calc_count == 2

    def test_estimate_to_dict(self, calculator: CostFirstCalculator) -> None:
        """测试估算结果转字典."""
        estimate = calculator.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        result = estimate.to_dict()
        assert "instrument" in result
        assert "fee" in result
        assert "slippage" in result
        assert "impact" in result
        assert "total_cost" in result
        assert "total_ratio" in result


class TestCostValidator:
    """成本验证器测试."""

    @pytest.fixture
    def validator(self) -> CostValidator:
        """创建验证器实例."""
        return CostValidator()

    @pytest.fixture
    def strict_validator(self) -> CostValidator:
        """创建严格验证器实例."""
        thresholds = CostThresholds(
            max_fee_ratio=0.0001,  # 0.01%
            max_slippage_ratio=0.0001,
            max_impact_ratio=0.0001,
            max_total_ratio=0.001,
            min_rr_ratio=3.0,
        )
        return CostValidator(thresholds=thresholds)

    def test_validate_pass(self, validator: CostValidator) -> None:
        """测试验证通过场景."""
        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
            expected_profit=500.0,
            expected_loss=100.0,
        )

        assert isinstance(result, CostValidationResult)
        assert result.passed
        assert result.result == CostCheckResult.PASS
        assert result.alert_level in (CostAlertLevel.NORMAL, CostAlertLevel.WARNING)

    def test_validate_high_cost(self, strict_validator: CostValidator) -> None:
        """测试高成本拒绝场景."""
        result = strict_validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=100,  # 大单
            direction="buy",
        )

        # 严格阈值下大单应该被拒绝
        assert not result.passed
        assert result.alert_level == CostAlertLevel.BLOCK

    def test_validate_rr_ratio_check(self, validator: CostValidator) -> None:
        """测试盈亏比检查."""
        # 低盈亏比
        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
            expected_profit=50.0,  # 预期盈利很低
            expected_loss=100.0,
        )

        # 成本会被纳入亏损计算，导致盈亏比更低
        assert result.rr_ratio < 2.0

    def test_validate_batch(self, validator: CostValidator) -> None:
        """测试批量验证."""
        orders = [
            {
                "instrument": "rb2501",
                "price": 3500.0,
                "volume": 10,
                "direction": "buy",
            },
            {
                "instrument": "rb2501",
                "price": 3510.0,
                "volume": 5,
                "direction": "sell",
            },
        ]

        results = validator.validate_batch(orders)
        assert len(results) == 2
        assert all(isinstance(r, CostValidationResult) for r in results)

    def test_validation_stats(self, validator: CostValidator) -> None:
        """测试验证统计."""
        assert validator.validation_count == 0
        assert validator.reject_count == 0

        validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        stats = validator.get_stats()
        assert stats["validation_count"] == 1
        assert stats["pass_rate"] >= 0

    def test_result_to_dict(self, validator: CostValidator) -> None:
        """测试验证结果转字典."""
        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        data = result.to_dict()
        assert "result" in data
        assert "alert_level" in data
        assert "passed" in data
        assert "estimate" in data
        assert "messages" in data


class TestCostAuditEvent:
    """成本审计事件测试."""

    def test_create_audit_event(self) -> None:
        """测试创建审计事件."""
        calc = CostFirstCalculator()
        estimate = calc.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        event = create_cost_audit_event(
            estimate=estimate,
            validation=None,
            run_id="run-123",
            exec_id="exec-456",
        )

        assert event.event_type == "COST_ESTIMATE"
        assert event.run_id == "run-123"
        assert event.exec_id == "exec-456"
        assert event.instrument == "rb2501"

    def test_audit_event_with_validation(self) -> None:
        """测试带验证结果的审计事件."""
        calc = CostFirstCalculator()
        validator = CostValidator(calculator=calc)

        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        event = create_cost_audit_event(
            estimate=result.estimate,
            validation=result,
            run_id="run-123",
            exec_id="exec-456",
        )

        data = event.to_dict()
        assert "validation" in data
        assert data["validation"] is not None

    def test_audit_event_to_dict(self) -> None:
        """测试审计事件转字典."""
        calc = CostFirstCalculator()
        estimate = calc.estimate_total_cost(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        event = create_cost_audit_event(
            estimate=estimate,
            validation=None,
            run_id="run-123",
            exec_id="exec-456",
        )

        data = event.to_dict()
        assert "ts" in data
        assert "event_type" in data
        assert "run_id" in data
        assert "exec_id" in data
        assert "instrument" in data
        assert "estimate" in data


class TestMilitaryRuleCompliance:
    """军规合规性测试.

    M5: 成本先行机制
    M3: 审计日志
    """

    def test_m5_cost_first_mechanism(self) -> None:
        """M5: 成本先行 - 交易执行前必须完成成本预估."""
        calc = CostFirstCalculator()
        validator = CostValidator(calculator=calc)

        # 模拟交易意图
        instrument = "rb2501"
        price = 3500.0
        volume = 10
        direction = "buy"

        # 1. 首先进行成本预估
        estimate = calc.estimate_total_cost(
            instrument=instrument,
            price=price,
            volume=volume,
            direction=direction,
        )
        assert estimate is not None
        assert estimate.total_cost > 0

        # 2. 进行成本验证
        result = validator.validate(
            instrument=instrument,
            price=price,
            volume=volume,
            direction=direction,
            expected_profit=200.0,
            expected_loss=100.0,
        )
        assert result is not None

        # 3. 只有验证通过才能执行交易
        if result.passed:
            # 执行交易逻辑...
            pass
        else:
            # 拒绝交易
            pass

    def test_m3_audit_logging(self) -> None:
        """M3: 审计日志 - 所有成本计算结果必须可追溯."""
        calc = CostFirstCalculator()
        validator = CostValidator(calculator=calc)

        # 执行验证
        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )

        # 生成审计事件
        event = create_cost_audit_event(
            estimate=result.estimate,
            validation=result,
            run_id="run-123",
            exec_id="exec-456",
        )

        # 验证审计事件包含必要字段
        data = event.to_dict()
        assert data["ts"] > 0
        assert data["event_type"] == "COST_ESTIMATE"
        assert data["run_id"] == "run-123"
        assert data["exec_id"] == "exec-456"
        assert data["instrument"] == "rb2501"
        assert "estimate" in data
        assert "validation" in data

    def test_cost_threshold_check(self) -> None:
        """测试成本阈值检查场景."""
        thresholds = CostThresholds(
            max_total_ratio=0.005,  # 0.5%
            min_rr_ratio=2.0,
        )
        validator = CostValidator(thresholds=thresholds)

        # 正常订单应通过
        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=10,
            direction="buy",
        )
        assert result.passed or result.alert_level != CostAlertLevel.BLOCK

    def test_alert_level_escalation(self) -> None:
        """测试告警级别升级."""
        # 使用非常严格的阈值
        thresholds = CostThresholds(
            max_total_ratio=0.0001,  # 0.01%
        )
        validator = CostValidator(thresholds=thresholds)

        result = validator.validate(
            instrument="rb2501",
            price=3500.0,
            volume=100,
            direction="buy",
        )

        # 应该触发高级别告警
        assert result.alert_level in (CostAlertLevel.CRITICAL, CostAlertLevel.BLOCK)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
