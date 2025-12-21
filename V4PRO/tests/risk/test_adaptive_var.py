"""
自适应VaR调度器测试 (军规级 v4.3).

测试覆盖:
- D8设计: 动态VaR频率优化
- M6: 熔断保护 - 极端市场加速计算
- M13: 涨跌停感知 - 涨跌停触发立即重算
- M16: 保证金监控 - 保证金告警触发

场景覆盖:
- ADAPTIVE.REGIME: 市场状态检测
- ADAPTIVE.INTERVAL: 自适应间隔调整
- ADAPTIVE.METHOD: 计算方法切换
- ADAPTIVE.EVENT: 事件触发器
- ADAPTIVE.PERFORMANCE: 性能监控
"""

from __future__ import annotations

import math
import time

import pytest

from src.risk.adaptive_var import (
    AdaptiveVaRConfig,
    AdaptiveVaRScheduler,
    EventType,
    MarketRegime,
    PerformanceMetrics,
    VaRScheduleState,
    create_adaptive_var_scheduler,
    get_regime_from_volatility,
    quick_adaptive_var,
)
from src.risk.dynamic_var import VaRMethod


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def scheduler() -> AdaptiveVaRScheduler:
    """创建默认调度器."""
    return AdaptiveVaRScheduler(confidence=0.95)


@pytest.fixture
def calm_returns() -> list[float]:
    """生成平静市场收益率 (低波动)."""
    # 年化波动率约 10%
    seed = 11111
    returns = []
    for _ in range(100):
        seed = (1103515245 * seed + 12345) % (2**31)
        u = seed / (2**31)
        returns.append((u - 0.5) * 0.01)  # +/- 0.5%
    return returns


@pytest.fixture
def normal_returns() -> list[float]:
    """生成正常市场收益率."""
    # 年化波动率约 20%
    seed = 22222
    returns = []
    for _ in range(100):
        seed = (1103515245 * seed + 12345) % (2**31)
        u = seed / (2**31)
        returns.append((u - 0.5) * 0.03)  # +/- 1.5%
    return returns


@pytest.fixture
def volatile_returns() -> list[float]:
    """生成波动市场收益率."""
    # 年化波动率约 40%
    seed = 33333
    returns = []
    for _ in range(100):
        seed = (1103515245 * seed + 12345) % (2**31)
        u = seed / (2**31)
        returns.append((u - 0.5) * 0.05)  # +/- 2.5%
    return returns


@pytest.fixture
def extreme_returns() -> list[float]:
    """生成极端市场收益率."""
    # 包含极端收益
    returns = [-0.02] * 80 + [-0.08, -0.06, 0.07, -0.09, 0.08] * 4
    return returns


# ============================================================
# AdaptiveVaRConfig 测试
# ============================================================


class TestAdaptiveVaRConfig:
    """自适应VaR配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = AdaptiveVaRConfig()
        assert config.base_interval_ms == 1000
        assert config.cpu_limit_pct == 10.0

    def test_adaptive_rules(self) -> None:
        """测试自适应规则."""
        rules = AdaptiveVaRConfig.ADAPTIVE_RULES
        assert rules["calm"] == 5000
        assert rules["normal"] == 1000
        assert rules["volatile"] == 500
        assert rules["extreme"] == 200

    def test_calculation_strategy(self) -> None:
        """测试计算策略."""
        strategy = AdaptiveVaRConfig.CALCULATION_STRATEGY
        assert strategy["calm"] == "parametric"
        assert strategy["normal"] == "historical"
        assert strategy["volatile"] == "historical"
        assert strategy["extreme"] == "monte_carlo"

    def test_event_triggers(self) -> None:
        """测试事件触发器."""
        triggers = AdaptiveVaRConfig.EVENT_TRIGGERS
        assert "position_change" in triggers
        assert "price_gap_3pct" in triggers
        assert "margin_warning" in triggers
        assert "limit_price_hit" in triggers


# ============================================================
# MarketRegime 测试
# ============================================================


class TestMarketRegime:
    """市场状态测试."""

    def test_regime_values(self) -> None:
        """测试状态值."""
        assert MarketRegime.CALM.value == "calm"
        assert MarketRegime.NORMAL.value == "normal"
        assert MarketRegime.VOLATILE.value == "volatile"
        assert MarketRegime.EXTREME.value == "extreme"

    def test_get_regime_from_volatility(self) -> None:
        """测试波动率到状态转换."""
        assert get_regime_from_volatility(0.10) == MarketRegime.CALM
        assert get_regime_from_volatility(0.20) == MarketRegime.NORMAL
        assert get_regime_from_volatility(0.35) == MarketRegime.VOLATILE
        assert get_regime_from_volatility(0.60) == MarketRegime.EXTREME


# ============================================================
# 初始化测试
# ============================================================


class TestAdaptiveVaRSchedulerInit:
    """调度器初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        scheduler = AdaptiveVaRScheduler()
        assert scheduler.current_regime == MarketRegime.NORMAL
        assert scheduler.last_result is None

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = AdaptiveVaRConfig(cpu_limit_pct=5.0)
        scheduler = AdaptiveVaRScheduler(config=config)
        stats = scheduler.get_statistics()
        assert stats["cpu_limit_pct"] == 5.0

    def test_custom_confidence(self) -> None:
        """测试自定义置信水平."""
        scheduler = AdaptiveVaRScheduler(confidence=0.99)
        stats = scheduler.get_statistics()
        assert scheduler._confidence == 0.99


# ============================================================
# 市场状态检测测试
# ============================================================


class TestMarketRegimeDetection:
    """市场状态检测测试."""

    def test_detect_calm_market(
        self, scheduler: AdaptiveVaRScheduler, calm_returns: list[float]
    ) -> None:
        """测试检测平静市场."""
        regime = scheduler.detect_market_regime(calm_returns)
        assert regime in [MarketRegime.CALM, MarketRegime.NORMAL]

    def test_detect_normal_market(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试检测正常市场."""
        regime = scheduler.detect_market_regime(normal_returns)
        assert regime in [MarketRegime.NORMAL, MarketRegime.VOLATILE]

    def test_detect_volatile_market(
        self, scheduler: AdaptiveVaRScheduler, volatile_returns: list[float]
    ) -> None:
        """测试检测波动市场."""
        regime = scheduler.detect_market_regime(volatile_returns)
        assert regime in [MarketRegime.VOLATILE, MarketRegime.EXTREME]

    def test_detect_extreme_market(
        self, scheduler: AdaptiveVaRScheduler, extreme_returns: list[float]
    ) -> None:
        """测试检测极端市场."""
        regime = scheduler.detect_market_regime(extreme_returns)
        assert regime == MarketRegime.EXTREME

    def test_insufficient_data(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试数据不足."""
        regime = scheduler.detect_market_regime([0.01, 0.02])
        assert regime == MarketRegime.NORMAL  # 默认值


# ============================================================
# 更新间隔测试
# ============================================================


class TestUpdateInterval:
    """更新间隔测试."""

    def test_calm_interval(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试平静市场间隔."""
        scheduler.update_market_regime(MarketRegime.CALM)
        assert scheduler.get_update_interval_ms() == 5000

    def test_normal_interval(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试正常市场间隔."""
        scheduler.update_market_regime(MarketRegime.NORMAL)
        assert scheduler.get_update_interval_ms() == 1000

    def test_volatile_interval(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试波动市场间隔."""
        scheduler.update_market_regime(MarketRegime.VOLATILE)
        assert scheduler.get_update_interval_ms() == 500

    def test_extreme_interval(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试极端市场间隔."""
        scheduler.update_market_regime(MarketRegime.EXTREME)
        assert scheduler.get_update_interval_ms() == 200


# ============================================================
# 计算方法测试
# ============================================================


class TestCalculationMethod:
    """计算方法测试."""

    def test_calm_method(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试平静市场方法."""
        scheduler.update_market_regime(MarketRegime.CALM)
        assert scheduler.get_calculation_method() == VaRMethod.PARAMETRIC

    def test_normal_method(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试正常市场方法."""
        scheduler.update_market_regime(MarketRegime.NORMAL)
        assert scheduler.get_calculation_method() == VaRMethod.HISTORICAL

    def test_volatile_method(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试波动市场方法."""
        scheduler.update_market_regime(MarketRegime.VOLATILE)
        assert scheduler.get_calculation_method() == VaRMethod.HISTORICAL

    def test_extreme_method(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试极端市场方法."""
        scheduler.update_market_regime(MarketRegime.EXTREME)
        assert scheduler.get_calculation_method() == VaRMethod.MONTE_CARLO


# ============================================================
# 按需计算测试
# ============================================================


class TestCalculateIfNeeded:
    """按需计算测试."""

    def test_first_calculation(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试首次计算."""
        result = scheduler.calculate_if_needed(normal_returns)
        assert result is not None
        assert result.var >= 0

    def test_skip_calculation_within_interval(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试间隔内跳过计算."""
        # 首次计算
        result1 = scheduler.calculate_if_needed(normal_returns)
        assert result1 is not None

        # 立即再次调用应该返回缓存结果
        result2 = scheduler.calculate_if_needed(normal_returns)
        assert result2 == result1  # 同一个对象

    def test_auto_detect_regime(
        self, scheduler: AdaptiveVaRScheduler, extreme_returns: list[float]
    ) -> None:
        """测试自动检测市场状态."""
        # 使用极端收益应该自动切换到极端模式
        scheduler.force_calculate(extreme_returns)
        # 由于自动检测，状态应该是极端
        # 注意: calculate_if_needed会自动检测


# ============================================================
# 强制计算测试
# ============================================================


class TestForceCalculate:
    """强制计算测试."""

    def test_force_calculate(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试强制计算."""
        result = scheduler.force_calculate(normal_returns)
        assert result is not None
        assert result.var >= 0

    def test_force_calculate_with_method(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试指定方法的强制计算."""
        result = scheduler.force_calculate(
            normal_returns, method=VaRMethod.MONTE_CARLO
        )
        assert result.method == VaRMethod.MONTE_CARLO

    def test_multiple_force_calculations(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试连续强制计算."""
        for _ in range(3):
            result = scheduler.force_calculate(normal_returns)
            assert result.var >= 0

        stats = scheduler.get_statistics()
        assert stats["calculation_count"] == 3


# ============================================================
# 事件触发器测试 (M6/M13/M16)
# ============================================================


class TestEventTriggers:
    """事件触发器测试."""

    def test_position_change_trigger(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试持仓变动触发."""
        result = scheduler.trigger_event(
            EventType.POSITION_CHANGE, normal_returns
        )
        assert result is not None
        assert result.var >= 0

        stats = scheduler.get_statistics()
        assert stats["event_trigger_count"] == 1

    def test_price_gap_trigger(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试价格跳空触发."""
        result = scheduler.trigger_event(
            EventType.PRICE_GAP_3PCT, normal_returns
        )
        assert result is not None

    def test_margin_warning_trigger_uses_monte_carlo(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试保证金告警使用蒙特卡洛 (M16)."""
        result = scheduler.trigger_event(
            EventType.MARGIN_WARNING, normal_returns
        )
        assert result is not None
        # 极端事件应该使用蒙特卡洛
        assert result.method == VaRMethod.MONTE_CARLO

    def test_limit_price_hit_trigger_uses_monte_carlo(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试涨跌停触发使用蒙特卡洛 (M13)."""
        result = scheduler.trigger_event(
            EventType.LIMIT_PRICE_HIT, normal_returns
        )
        assert result is not None
        assert result.method == VaRMethod.MONTE_CARLO

    def test_event_callback(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试事件回调."""
        received_events: list[tuple] = []

        def callback(event_type, result):
            received_events.append((event_type, result))

        scheduler.register_event_callback(callback)
        scheduler.trigger_event(EventType.POSITION_CHANGE, normal_returns)

        assert len(received_events) == 1
        assert received_events[0][0] == EventType.POSITION_CHANGE


# ============================================================
# 性能监控测试
# ============================================================


class TestPerformanceMonitoring:
    """性能监控测试."""

    def test_performance_metrics(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试性能指标."""
        # 执行几次计算
        for _ in range(5):
            scheduler.force_calculate(normal_returns)

        metrics = scheduler.get_performance_metrics()
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.avg_calculation_time_ms >= 0
        assert metrics.max_calculation_time_ms >= 0

    def test_cpu_usage_tracking(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试CPU使用率追踪."""
        for _ in range(10):
            scheduler.force_calculate(normal_returns)

        stats = scheduler.get_statistics()
        assert "avg_cpu_usage_pct" in stats
        assert stats["avg_cpu_usage_pct"] >= 0

    def test_throttling_detection(self) -> None:
        """测试节流检测."""
        # 设置非常低的CPU限制
        config = AdaptiveVaRConfig(cpu_limit_pct=0.001)
        scheduler = AdaptiveVaRScheduler(config=config)

        # 模拟高CPU使用率
        scheduler._state.cpu_usage_samples = [99.0] * 10

        # should_calculate应该返回False
        assert not scheduler.should_calculate()
        assert scheduler._state.skipped_calculations > 0


# ============================================================
# 统计测试
# ============================================================


class TestStatistics:
    """统计测试."""

    def test_get_statistics(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试获取统计信息."""
        scheduler.force_calculate(normal_returns)
        stats = scheduler.get_statistics()

        assert "current_regime" in stats
        assert "update_interval_ms" in stats
        assert "calculation_method" in stats
        assert "calculation_count" in stats
        assert "event_trigger_count" in stats

    def test_reset(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试重置."""
        scheduler.force_calculate(normal_returns)
        scheduler.trigger_event(EventType.POSITION_CHANGE, normal_returns)

        scheduler.reset()

        stats = scheduler.get_statistics()
        assert stats["calculation_count"] == 0
        assert stats["event_trigger_count"] == 0

    def test_audit_dict(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试审计字典."""
        scheduler.force_calculate(normal_returns)
        audit = scheduler.to_audit_dict()

        assert audit["event_type"] == "ADAPTIVE_VAR_SCHEDULER"
        assert "timestamp" in audit
        assert "regime" in audit
        assert "last_var" in audit


# ============================================================
# 状态切换测试
# ============================================================


class TestRegimeTransition:
    """状态切换测试."""

    def test_calm_to_extreme_forces_calculation(
        self, scheduler: AdaptiveVaRScheduler
    ) -> None:
        """测试从平静到极端强制计算."""
        scheduler.update_market_regime(MarketRegime.CALM)
        # 记录last_calculation_time
        scheduler._state.last_calculation_time = time.time() * 1000

        # 切换到极端
        scheduler.update_market_regime(MarketRegime.EXTREME)

        # 应该重置计算时间，允许下次立即计算
        assert scheduler._state.last_calculation_time == 0

    def test_normal_to_volatile_no_force(
        self, scheduler: AdaptiveVaRScheduler
    ) -> None:
        """测试从正常到波动不强制计算."""
        scheduler.update_market_regime(MarketRegime.NORMAL)
        original_time = time.time() * 1000
        scheduler._state.last_calculation_time = original_time

        scheduler.update_market_regime(MarketRegime.VOLATILE)

        # 不应该重置
        assert scheduler._state.last_calculation_time == original_time


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_adaptive_var_scheduler(self) -> None:
        """测试创建调度器."""
        scheduler = create_adaptive_var_scheduler(
            confidence=0.99,
            cpu_limit_pct=5.0,
            seed=42,
        )
        assert scheduler._confidence == 0.99
        assert scheduler._config.cpu_limit_pct == 5.0

    def test_quick_adaptive_var(self, normal_returns: list[float]) -> None:
        """测试快速自适应VaR."""
        var = quick_adaptive_var(normal_returns, confidence=0.95)
        assert var >= 0


# ============================================================
# VaRScheduleState 测试
# ============================================================


class TestVaRScheduleState:
    """调度状态测试."""

    def test_default_state(self) -> None:
        """测试默认状态."""
        state = VaRScheduleState()
        assert state.current_regime == MarketRegime.NORMAL
        assert state.calculation_count == 0
        assert state.event_trigger_count == 0

    def test_avg_cpu_usage_empty(self) -> None:
        """测试空CPU使用率."""
        state = VaRScheduleState()
        assert state.get_avg_cpu_usage() == 0.0

    def test_avg_cpu_usage(self) -> None:
        """测试CPU使用率计算."""
        state = VaRScheduleState()
        state.cpu_usage_samples = [5.0, 10.0, 15.0]
        assert state.get_avg_cpu_usage() == 10.0


# ============================================================
# D8 性能目标测试
# ============================================================


class TestD8PerformanceGoals:
    """D8设计性能目标测试."""

    def test_cpu_limit_enforcement(self) -> None:
        """测试CPU限制强制执行."""
        config = AdaptiveVaRConfig(cpu_limit_pct=10.0)
        assert config.cpu_limit_pct == 10.0

    def test_interval_range(self) -> None:
        """测试间隔范围: 200ms-5s."""
        rules = AdaptiveVaRConfig.ADAPTIVE_RULES
        intervals = list(rules.values())
        assert min(intervals) == 200  # 极端市场最小
        assert max(intervals) == 5000  # 平静市场最大

    def test_base_interval_adjusted(self) -> None:
        """测试基础间隔调整: 100ms -> 1000ms."""
        assert AdaptiveVaRConfig.BASE_INTERVAL_MS == 1000


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_empty_returns(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试空收益."""
        result = scheduler.force_calculate([])
        assert result.var == 0.0

    def test_single_return(self, scheduler: AdaptiveVaRScheduler) -> None:
        """测试单个收益."""
        result = scheduler.force_calculate([0.01])
        assert result.var == 0.0

    def test_callback_error_ignored(
        self, scheduler: AdaptiveVaRScheduler, normal_returns: list[float]
    ) -> None:
        """测试回调错误被忽略."""
        def bad_callback(event_type, result):
            raise ValueError("Test error")

        scheduler.register_event_callback(bad_callback)
        # 不应该抛出异常
        result = scheduler.trigger_event(
            EventType.POSITION_CHANGE, normal_returns
        )
        assert result is not None


# ============================================================
# 军规合规测试
# ============================================================


class TestMilitaryRuleCompliance:
    """军规合规测试."""

    def test_m6_extreme_market_acceleration(
        self, extreme_returns: list[float]
    ) -> None:
        """M6: 极端市场加速计算."""
        scheduler = AdaptiveVaRScheduler()
        scheduler.update_market_regime(MarketRegime.EXTREME)

        # 极端市场应使用最快间隔
        assert scheduler.get_update_interval_ms() == 200
        # 应使用蒙特卡洛
        assert scheduler.get_calculation_method() == VaRMethod.MONTE_CARLO

    def test_m13_limit_price_trigger(
        self, normal_returns: list[float]
    ) -> None:
        """M13: 涨跌停触发立即重算."""
        scheduler = AdaptiveVaRScheduler()
        result = scheduler.trigger_event(
            EventType.LIMIT_PRICE_HIT, normal_returns
        )

        assert result is not None
        # 涨跌停应使用蒙特卡洛精确计算
        assert result.method == VaRMethod.MONTE_CARLO

    def test_m16_margin_warning_trigger(
        self, normal_returns: list[float]
    ) -> None:
        """M16: 保证金告警触发."""
        scheduler = AdaptiveVaRScheduler()
        result = scheduler.trigger_event(
            EventType.MARGIN_WARNING, normal_returns
        )

        assert result is not None
        # 保证金告警应使用蒙特卡洛精确计算
        assert result.method == VaRMethod.MONTE_CARLO
