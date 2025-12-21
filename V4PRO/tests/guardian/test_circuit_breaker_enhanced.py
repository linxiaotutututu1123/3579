"""
CircuitBreaker 增强组件测试.

V4PRO Platform Component - Phase 10
V4 SPEC: D2 熔断-恢复闭环

测试覆盖:
- 熔断触发器 (DailyLoss/PositionLoss/MarginUsage/ConsecutiveLoss)
- 渐进式恢复执行器 (GradualRecoveryExecutor)
- 熔断恢复闭环控制器 (CircuitBreakerController)
"""

import pytest

from src.guardian import (
    CircuitBreaker,
    CircuitBreakerController,
    CircuitBreakerMetrics,
    CircuitBreakerRiskTrigger,
    CircuitBreakerState,
    ConsecutiveLossTrigger,
    DailyLossTrigger,
    GradualRecoveryExecutor,
    MarginUsageTrigger,
    PositionLossTrigger,
    RecoveryConfig,
    RecoveryStage,
    RiskMetricsCollector,
    TriggerThresholds,
    create_default_controller,
)


class TestRiskMetricsCollector:
    """RiskMetricsCollector 测试."""

    def test_calculate_daily_loss(self) -> None:
        """测试日亏损计算."""
        collector = RiskMetricsCollector()
        collector.day_start_equity = 100000
        collector.current_equity = 95000

        metrics = collector.calculate_metrics()

        assert metrics.daily_loss_pct == pytest.approx(0.05, abs=0.001)

    def test_calculate_position_loss(self) -> None:
        """测试持仓亏损计算."""
        collector = RiskMetricsCollector()
        collector.position_cost = 50000
        collector.position_value = 45000

        metrics = collector.calculate_metrics()

        assert metrics.position_loss_pct == pytest.approx(0.10, abs=0.001)

    def test_calculate_margin_usage(self) -> None:
        """测试保证金使用率计算."""
        collector = RiskMetricsCollector()
        collector.margin_used = 80000
        collector.margin_available = 20000

        metrics = collector.calculate_metrics()

        assert metrics.margin_usage_pct == pytest.approx(0.80, abs=0.001)

    def test_record_trade_result(self) -> None:
        """测试交易结果记录."""
        collector = RiskMetricsCollector()

        # 连续亏损
        collector.record_trade_result(-100)
        collector.record_trade_result(-50)
        collector.record_trade_result(-200)

        assert collector.consecutive_losses == 3

        # 盈利重置
        collector.record_trade_result(100)
        assert collector.consecutive_losses == 0


class TestDailyLossTrigger:
    """DailyLossTrigger 测试."""

    def test_trigger_on_threshold_exceeded(self) -> None:
        """测试超过阈值触发."""
        trigger = DailyLossTrigger(threshold=0.03)
        state = {
            "day_start_equity": 100000,
            "current_equity": 96000,  # 4% 亏损
        }

        result = trigger.check(state)

        assert result.triggered is True
        assert result.trigger_name == "daily_loss"
        assert result.event_name == "circuit_breaker_trigger"
        assert trigger.last_loss_pct == pytest.approx(0.04, abs=0.001)

    def test_no_trigger_below_threshold(self) -> None:
        """测试未超过阈值不触发."""
        trigger = DailyLossTrigger(threshold=0.03)
        state = {
            "day_start_equity": 100000,
            "current_equity": 98000,  # 2% 亏损
        }

        result = trigger.check(state)

        assert result.triggered is False


class TestPositionLossTrigger:
    """PositionLossTrigger 测试."""

    def test_trigger_on_position_loss(self) -> None:
        """测试持仓亏损触发."""
        trigger = PositionLossTrigger(threshold=0.05)
        state = {
            "positions": [
                {"symbol": "rb2501", "cost": 10000, "value": 9000, "qty": 10},
            ],
        }

        result = trigger.check(state)

        assert result.triggered is True
        assert len(trigger.triggered_positions) == 1
        assert trigger.max_loss_pct == pytest.approx(0.10, abs=0.001)


class TestMarginUsageTrigger:
    """MarginUsageTrigger 测试."""

    def test_trigger_on_high_margin_usage(self) -> None:
        """测试高保证金使用率触发."""
        trigger = MarginUsageTrigger(threshold=0.85)
        state = {
            "margin_used": 90000,
            "margin_available": 10000,
        }

        result = trigger.check(state)

        assert result.triggered is True
        assert trigger.last_usage_pct == pytest.approx(0.90, abs=0.001)


class TestConsecutiveLossTrigger:
    """ConsecutiveLossTrigger 测试."""

    def test_trigger_on_consecutive_losses(self) -> None:
        """测试连续亏损触发."""
        trigger = ConsecutiveLossTrigger(threshold=5)
        state = {"consecutive_losses": 6}

        result = trigger.check(state)

        assert result.triggered is True
        assert trigger.current_count == 6

    def test_no_trigger_below_threshold(self) -> None:
        """测试未达阈值不触发."""
        trigger = ConsecutiveLossTrigger(threshold=5)
        state = {"consecutive_losses": 4}

        result = trigger.check(state)

        assert result.triggered is False


class TestCircuitBreakerRiskTrigger:
    """CircuitBreakerRiskTrigger 综合测试."""

    def test_trigger_on_any_condition(self) -> None:
        """测试任一条件满足即触发."""
        trigger = CircuitBreakerRiskTrigger(
            TriggerThresholds(
                daily_loss_pct=0.03,
                position_loss_pct=0.05,
                margin_usage_pct=0.85,
                consecutive_losses=5,
            )
        )
        # 仅日亏损触发
        state = {
            "day_start_equity": 100000,
            "current_equity": 96000,  # 4% 亏损
            "margin_used": 50000,
            "margin_available": 50000,
            "consecutive_losses": 2,
        }

        result = trigger.check(state)

        assert result.triggered is True
        assert len(result.details["trigger_reasons"]) >= 1


class TestGradualRecoveryExecutor:
    """GradualRecoveryExecutor 测试."""

    def test_initial_state(self) -> None:
        """测试初始状态."""
        breaker = CircuitBreaker()
        executor = GradualRecoveryExecutor(breaker)

        assert executor.stage == RecoveryStage.IDLE
        assert executor.current_ratio == 1.0
        assert executor.is_recovering is False

    def test_recovery_on_trigger(self) -> None:
        """测试触发后恢复."""
        breaker = CircuitBreaker(
            recovery_config=RecoveryConfig(
                cooling_duration_seconds=0.1,
                full_cooling_duration_seconds=0.1,
                step_interval_seconds=0.1,
            )
        )
        executor = GradualRecoveryExecutor(breaker)

        # 触发熔断
        metrics = CircuitBreakerMetrics(
            daily_loss_pct=0.05,
            position_loss_pct=0.0,
            margin_usage_pct=0.0,
            consecutive_losses=0,
        )
        breaker.trigger(metrics)

        # 同步状态
        executor.tick()

        assert executor.stage == RecoveryStage.COOLING
        assert executor.current_ratio == 0.0

    def test_get_scaled_position(self) -> None:
        """测试仓位缩放."""
        breaker = CircuitBreaker()
        executor = GradualRecoveryExecutor(breaker)

        target = {"rb2501": 100, "rb2505": -50}

        # NORMAL 状态返回原始目标
        scaled = executor.get_scaled_position(target)
        assert scaled == target


class TestCircuitBreakerController:
    """CircuitBreakerController 测试."""

    def test_initial_state(self) -> None:
        """测试初始状态."""
        controller = create_default_controller()

        assert controller.state == CircuitBreakerState.NORMAL
        assert controller.recovery_stage == RecoveryStage.IDLE
        assert controller.position_ratio == 1.0
        assert controller.is_trading_allowed is True
        assert controller.is_new_position_allowed is True

    def test_check_triggers_breaker(self) -> None:
        """测试检查触发熔断."""
        controller = CircuitBreakerController(
            thresholds=TriggerThresholds(daily_loss_pct=0.03),
        )

        state = {
            "day_start_equity": 100000,
            "current_equity": 95000,  # 5% 亏损
        }

        status = controller.check(state)

        assert status.breaker_state == CircuitBreakerState.TRIGGERED
        assert len(status.last_trigger_reasons) >= 1

    def test_filter_target_portfolio_normal(self) -> None:
        """测试正常状态仓位过滤."""
        controller = create_default_controller()

        target = {"rb2501": 100}
        current = {"rb2501": 50}

        filtered = controller.filter_target_portfolio(target, current)

        assert filtered == target

    def test_filter_target_portfolio_triggered(self) -> None:
        """测试触发状态仓位过滤 (仅允许减仓)."""
        controller = CircuitBreakerController(
            thresholds=TriggerThresholds(daily_loss_pct=0.03),
        )

        # 触发熔断
        state = {
            "day_start_equity": 100000,
            "current_equity": 95000,
        }
        controller.check(state)

        target = {"rb2501": 100}  # 想加仓
        current = {"rb2501": 50}  # 当前持仓

        filtered = controller.filter_target_portfolio(target, current)

        # 只能减仓或持平
        assert filtered["rb2501"] <= current["rb2501"]

    def test_manual_override(self) -> None:
        """测试人工接管."""
        controller = create_default_controller()

        result = controller.manual_override("测试接管")

        assert result is True
        assert controller.state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_manual_release(self) -> None:
        """测试人工解除."""
        controller = create_default_controller()
        controller.manual_override("测试")

        result = controller.manual_release(to_normal=True)

        assert result is True
        assert controller.state == CircuitBreakerState.NORMAL

    def test_record_trade_result(self) -> None:
        """测试记录交易结果."""
        controller = create_default_controller()

        # 记录连续亏损
        for _ in range(5):
            controller.record_trade_result(-100)

        # 检查状态
        state = {
            "day_start_equity": 100000,
            "current_equity": 100000,
        }
        status = controller.check(state)

        # 应该触发连续亏损熔断
        assert status.breaker_state == CircuitBreakerState.TRIGGERED

    def test_reset_daily(self) -> None:
        """测试日内重置."""
        controller = create_default_controller()

        controller.reset_daily(100000)

        # 检查不触发
        state = {
            "day_start_equity": 100000,
            "current_equity": 99000,  # 1% 亏损
        }
        status = controller.check(state)

        assert status.breaker_state == CircuitBreakerState.NORMAL

    def test_enable_disable(self) -> None:
        """测试启用禁用."""
        controller = create_default_controller()

        controller.disable()
        assert controller.is_enabled is False

        # 禁用时不触发熔断
        state = {
            "day_start_equity": 100000,
            "current_equity": 50000,  # 50% 亏损
        }
        status = controller.check(state)

        assert status.breaker_state == CircuitBreakerState.NORMAL

        controller.enable()
        assert controller.is_enabled is True

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        controller = create_default_controller()

        data = controller.to_dict()

        assert "enabled" in data
        assert "status" in data
        assert "breaker" in data
        assert "recovery" in data
        assert "thresholds" in data
        assert "recovery_config" in data


class TestIntegration:
    """集成测试."""

    def test_full_recovery_cycle(self) -> None:
        """测试完整恢复周期.

        NORMAL -> TRIGGERED -> COOLING -> RECOVERY -> NORMAL
        """
        # 使用快速配置
        controller = CircuitBreakerController(
            thresholds=TriggerThresholds(daily_loss_pct=0.03),
            recovery_config=RecoveryConfig(
                cooling_duration_seconds=0.01,
                full_cooling_duration_seconds=0.01,
                step_interval_seconds=0.01,
                position_ratio_steps=(0.5, 1.0),  # 简化步骤
            ),
        )

        # 1. 触发熔断
        state = {
            "day_start_equity": 100000,
            "current_equity": 95000,
        }
        controller.check(state)
        assert controller.state == CircuitBreakerState.TRIGGERED

        # 2. 推进到冷却
        import time

        time.sleep(0.02)
        controller.tick()
        assert controller.state == CircuitBreakerState.COOLING

        # 3. 推进到恢复
        time.sleep(0.02)
        controller.tick()
        assert controller.state == CircuitBreakerState.RECOVERY

        # 4. 推进恢复步骤
        time.sleep(0.02)
        controller.tick()

        # 5. 完成恢复
        time.sleep(0.02)
        controller.tick()
        assert controller.state == CircuitBreakerState.NORMAL
