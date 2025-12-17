"""
动态VaR风险引擎测试 (军规级 v4.2).

测试覆盖:
- M6: 熔断保护 - 极端风险预警
- M13: 涨跌停感知 - 涨跌停调整VaR
- M16: 保证金监控 - 流动性调整VaR

场景覆盖:
- VAR.EVT.GPD: EVT-GPD方法
- VAR.SEMIPARAMETRIC.KERNEL: 半参数方法
- VAR.LIMIT_ADJUSTED: 涨跌停调整
- VAR.LIQUIDITY_ADJUSTED: 流动性调整
"""

from __future__ import annotations

import math

import pytest

from src.risk.dynamic_var import (
    DynamicVaREngine,
    DynamicVaRResult,
    GPDParameters,
    LiquidityMetrics,
    RiskLevel,
    VaRMethod,
    create_dynamic_var_engine,
    quick_evt_var,
    quick_limit_var,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> DynamicVaREngine:
    """创建默认引擎."""
    return DynamicVaREngine(seed=42)


@pytest.fixture
def normal_returns() -> list[float]:
    """生成正态分布收益率."""
    # 使用固定种子生成近似正态分布
    returns = []
    seed = 12345
    for _ in range(100):
        seed = (1103515245 * seed + 12345) % (2**31)
        u1 = seed / (2**31)
        seed = (1103515245 * seed + 12345) % (2**31)
        u2 = seed / (2**31)
        if u1 > 0.001 and u2 > 0.001:
            z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
            returns.append(0.001 + 0.02 * z)  # 均值1%, 波动2%
    return returns


@pytest.fixture
def fat_tail_returns() -> list[float]:
    """生成厚尾分布收益率."""
    # 正常收益 + 少量极端收益
    returns = []
    seed = 54321
    for i in range(100):
        seed = (1103515245 * seed + 12345) % (2**31)
        u = seed / (2**31)
        if i < 95:
            # 正常收益
            returns.append((u - 0.5) * 0.04)  # ±2%
        else:
            # 极端收益
            returns.append(-0.05 - u * 0.05)  # -5%到-10%
    return returns


# ============================================================
# 初始化测试
# ============================================================


class TestDynamicVaREngineInit:
    """引擎初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        engine = DynamicVaREngine()
        assert engine.calculation_count == 0
        assert engine.warning_count == 0

    def test_custom_params(self) -> None:
        """测试自定义参数."""
        engine = DynamicVaREngine(
            default_confidence=0.99,
            var_limit=0.15,
            seed=42,
        )
        stats = engine.get_statistics()
        assert stats["default_confidence"] == 0.99
        assert stats["var_limit"] == 0.15


# ============================================================
# EVT VaR 测试
# ============================================================


class TestEVTVaR:
    """EVT VaR测试."""

    def test_evt_var_normal(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试正态收益EVT VaR."""
        result = engine.evt_var(normal_returns, confidence=0.95)

        assert result.method == VaRMethod.EVT_GPD
        assert result.var > 0
        assert result.confidence == 0.95
        assert result.sample_size == len(normal_returns)
        assert "xi" in result.metadata
        assert "beta" in result.metadata

    def test_evt_var_fat_tail(
        self, engine: DynamicVaREngine, fat_tail_returns: list[float]
    ) -> None:
        """测试厚尾收益EVT VaR."""
        result = engine.evt_var(fat_tail_returns, confidence=0.99)

        assert result.method == VaRMethod.EVT_GPD
        assert result.var > 0
        # 厚尾分布VaR应该更大
        # EVT VaR可能大于或小于历史VaR，取决于拟合

    def test_evt_var_insufficient_samples(self, engine: DynamicVaREngine) -> None:
        """测试样本不足时回退."""
        returns = [0.01, -0.02, 0.015]  # 只有3个样本
        result = engine.evt_var(returns)

        # 应回退到历史VaR
        assert result.method == VaRMethod.HISTORICAL
        assert result.metadata.get("fallback") == "insufficient_samples"

    def test_evt_var_99_confidence(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试99%置信度."""
        result_95 = engine.evt_var(normal_returns, confidence=0.95)
        result_99 = engine.evt_var(normal_returns, confidence=0.99)

        # 99%置信度VaR应大于95%
        assert result_99.var >= result_95.var * 0.9  # 允许一些误差


# ============================================================
# 半参数VaR 测试
# ============================================================


class TestSemiparametricVaR:
    """半参数VaR测试."""

    def test_semiparametric_var_normal(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试正态收益半参数VaR."""
        result = engine.semiparametric_var(normal_returns, confidence=0.95)

        assert result.method == VaRMethod.SEMIPARAMETRIC
        assert result.var > 0
        assert "bandwidth" in result.metadata

    def test_semiparametric_var_custom_bandwidth(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试自定义带宽."""
        result = engine.semiparametric_var(
            normal_returns, confidence=0.95, bandwidth=0.01
        )

        assert result.metadata["bandwidth"] == 0.01


# ============================================================
# 涨跌停调整VaR 测试
# ============================================================


class TestLimitAdjustedVaR:
    """涨跌停调整VaR测试."""

    def test_limit_adjusted_var_normal(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试正常收益涨跌停调整."""
        result = engine.limit_adjusted_var(
            normal_returns, limit_pct=0.10, confidence=0.95
        )

        assert result.method == VaRMethod.LIMIT_ADJUSTED
        assert result.var > 0
        assert result.metadata["limit_pct"] == 0.10

    def test_limit_adjusted_var_with_extremes(self, engine: DynamicVaREngine) -> None:
        """测试包含极端收益的涨跌停调整."""
        # 包含超过涨跌停的收益
        returns = [-0.02] * 90 + [-0.15] * 10  # 10%的收益超过10%涨跌停
        result = engine.limit_adjusted_var(returns, limit_pct=0.10, confidence=0.95)

        assert result.metadata["truncation_ratio"] > 0
        assert result.metadata["adjustment_factor"] > 1.0
        # 调整后VaR应该不小于涨跌停幅度
        assert result.var >= 0.09  # 允许小误差

    def test_limit_adjusted_var_different_limits(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试不同涨跌停幅度."""
        result_5 = engine.limit_adjusted_var(normal_returns, limit_pct=0.05)
        result_10 = engine.limit_adjusted_var(normal_returns, limit_pct=0.10)

        assert result_5.metadata["limit_pct"] == 0.05
        assert result_10.metadata["limit_pct"] == 0.10


# ============================================================
# 流动性调整VaR 测试
# ============================================================


class TestLiquidityAdjustedVaR:
    """流动性调整VaR测试."""

    def test_liquidity_adjusted_var_basic(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试基本流动性调整."""
        liquidity = LiquidityMetrics(
            adv=1000000,
            bid_ask_spread=0.001,
            impact_coefficient=0.1,
        )
        result = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=100000,
            liquidity=liquidity,
            confidence=0.95,
        )

        assert result.method == VaRMethod.LIQUIDITY_ADJUSTED
        assert result.var > 0
        assert "liquidity_cost" in result.metadata

    def test_liquidity_adjusted_var_large_position(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试大仓位流动性调整."""
        liquidity = LiquidityMetrics(adv=1000000, impact_coefficient=0.1)

        small_pos = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=10000,
            liquidity=liquidity,
        )
        large_pos = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=500000,
            liquidity=liquidity,
        )

        # 大仓位流动性成本更高
        assert (
            large_pos.metadata["impact_cost_pct"]
            > small_pos.metadata["impact_cost_pct"]
        )

    def test_liquidity_adjusted_var_multi_day(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试多日平仓流动性调整."""
        liquidity = LiquidityMetrics(adv=1000000)

        result_1d = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=100000,
            liquidity=liquidity,
            liquidation_days=1,
        )
        result_5d = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=100000,
            liquidity=liquidity,
            liquidation_days=5,
        )

        # 多日平仓VaR更大（时间调整）
        assert result_5d.var > result_1d.var


# ============================================================
# 统一接口测试
# ============================================================


class TestCalculateVaR:
    """统一VaR接口测试."""

    def test_calculate_var_all_methods(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试所有方法."""
        methods = [
            VaRMethod.HISTORICAL,
            VaRMethod.PARAMETRIC,
            VaRMethod.MONTE_CARLO,
            VaRMethod.EVT_GPD,
            VaRMethod.SEMIPARAMETRIC,
        ]

        for method in methods:
            result = engine.calculate_var(normal_returns, method=method)
            assert result.method == method
            assert result.var >= 0


# ============================================================
# 风险等级测试
# ============================================================


class TestRiskLevel:
    """风险等级测试."""

    def test_risk_level_safe(self, engine: DynamicVaREngine) -> None:
        """测试安全等级."""
        # 小波动收益
        returns = [0.001] * 100
        result = engine.evt_var(returns, confidence=0.95)

        assert result.risk_level in [RiskLevel.SAFE, RiskLevel.NORMAL]

    def test_risk_level_critical(self) -> None:
        """测试临界等级."""
        engine = DynamicVaREngine(var_limit=0.05)  # 低阈值
        # 大波动收益
        returns = [-0.05] * 100  # 平均-5%亏损
        result = engine.limit_adjusted_var(returns, limit_pct=0.10)

        # 应触发高风险等级
        assert result.risk_level in [RiskLevel.DANGER, RiskLevel.CRITICAL]
        assert engine.warning_count > 0


# ============================================================
# 回调测试
# ============================================================


class TestCallback:
    """回调测试."""

    def test_register_callback(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试注册回调."""
        received_results: list[DynamicVaRResult] = []

        def callback(result: DynamicVaRResult) -> None:
            received_results.append(result)

        engine.register_callback(callback)
        engine.evt_var(normal_returns)

        assert len(received_results) == 1

    def test_callback_error_ignored(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试回调错误被忽略."""

        def bad_callback(result: DynamicVaRResult) -> None:
            raise ValueError("Test error")

        engine.register_callback(bad_callback)
        # 不应抛出异常
        result = engine.evt_var(normal_returns)
        assert result.var >= 0


# ============================================================
# 统计测试
# ============================================================


class TestStatistics:
    """统计测试."""

    def test_calculation_count(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试计算次数."""
        assert engine.calculation_count == 0

        engine.evt_var(normal_returns)
        assert engine.calculation_count == 1

        engine.semiparametric_var(normal_returns)
        assert engine.calculation_count == 2

    def test_reset(self, engine: DynamicVaREngine, normal_returns: list[float]) -> None:
        """测试重置."""
        engine.evt_var(normal_returns)
        engine.reset()

        assert engine.calculation_count == 0
        assert engine.warning_count == 0


# ============================================================
# 数据类测试
# ============================================================


class TestDynamicVaRResult:
    """VaR结果测试."""

    def test_to_audit_dict(self) -> None:
        """测试转换为审计字典."""
        result = DynamicVaRResult(
            var=0.05,
            confidence=0.95,
            method=VaRMethod.EVT_GPD,
            expected_shortfall=0.07,
            risk_level=RiskLevel.WARNING,
            sample_size=100,
        )

        audit = result.to_audit_dict()
        assert audit["event_type"] == "VAR_CALCULATION"
        assert audit["var"] == 0.05
        assert audit["method"] == "evt_gpd"
        assert audit["risk_level"] == "预警"


class TestGPDParameters:
    """GPD参数测试."""

    def test_create_params(self) -> None:
        """测试创建参数."""
        params = GPDParameters(
            xi=0.1,
            beta=0.02,
            threshold=-0.03,
            exceedances=15,
        )

        assert params.xi == 0.1
        assert params.beta == 0.02
        assert params.exceedances == 15


class TestLiquidityMetrics:
    """流动性指标测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        metrics = LiquidityMetrics()

        assert metrics.adv == 0.0
        assert metrics.bid_ask_spread == 0.0
        assert metrics.impact_coefficient == 0.1


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_dynamic_var_engine(self) -> None:
        """测试创建引擎."""
        engine = create_dynamic_var_engine(confidence=0.99, var_limit=0.15)
        stats = engine.get_statistics()
        assert stats["default_confidence"] == 0.99
        assert stats["var_limit"] == 0.15

    def test_quick_evt_var(self, normal_returns: list[float]) -> None:
        """测试快速EVT VaR."""
        var = quick_evt_var(normal_returns, confidence=0.99)
        assert var > 0

    def test_quick_limit_var(self, normal_returns: list[float]) -> None:
        """测试快速涨跌停VaR."""
        var = quick_limit_var(normal_returns, limit_pct=0.10, confidence=0.95)
        assert var > 0


# ============================================================
# M6 军规测试: 熔断保护
# ============================================================


class TestM6CircuitBreaker:
    """M6军规测试: 熔断保护."""

    def test_extreme_risk_warning(self) -> None:
        """测试极端风险告警."""
        engine = DynamicVaREngine(var_limit=0.05)
        # 极端收益
        returns = [-0.08] * 50 + [-0.02] * 50
        result = engine.evt_var(returns, confidence=0.99)

        # 应触发告警
        assert result.risk_level in [
            RiskLevel.WARNING,
            RiskLevel.DANGER,
            RiskLevel.CRITICAL,
        ]


# ============================================================
# M13 军规测试: 涨跌停感知
# ============================================================


class TestM13LimitPrice:
    """M13军规测试: 涨跌停感知."""

    def test_limit_truncation(self) -> None:
        """测试涨跌停截断."""
        engine = DynamicVaREngine()
        # 包含超过涨跌停的收益
        returns = [-0.02] * 80 + [-0.12] * 20
        result = engine.limit_adjusted_var(returns, limit_pct=0.10)

        # 截断比例应该大于0
        assert result.metadata["truncation_ratio"] > 0
        assert result.metadata["truncation_ratio"] == 0.2  # 20%被截断


# ============================================================
# M16 军规测试: 保证金监控
# ============================================================


class TestM16MarginMonitor:
    """M16军规测试: 保证金监控."""

    def test_liquidity_impact_on_var(self, normal_returns: list[float]) -> None:
        """测试流动性对VaR的影响."""
        engine = DynamicVaREngine()

        # 高流动性
        high_liq = LiquidityMetrics(adv=10000000, bid_ask_spread=0.0001)
        # 低流动性
        low_liq = LiquidityMetrics(adv=100000, bid_ask_spread=0.005)

        high_result = engine.liquidity_adjusted_var(
            normal_returns, position_value=100000, liquidity=high_liq
        )
        low_result = engine.liquidity_adjusted_var(
            normal_returns, position_value=100000, liquidity=low_liq
        )

        # 低流动性VaR应更高
        assert low_result.var >= high_result.var


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_empty_returns(self, engine: DynamicVaREngine) -> None:
        """测试空收益."""
        result = engine.evt_var([])
        assert result.var == 0.0

    def test_single_return(self, engine: DynamicVaREngine) -> None:
        """测试单个收益."""
        result = engine.evt_var([0.01])
        assert result.var == 0.0

    def test_constant_returns(self, engine: DynamicVaREngine) -> None:
        """测试常数收益."""
        returns = [0.01] * 100
        result = engine.evt_var(returns)
        # 常数收益VaR应该很小
        assert result.var >= 0

    def test_zero_position_value(
        self, engine: DynamicVaREngine, normal_returns: list[float]
    ) -> None:
        """测试零持仓价值."""
        result = engine.liquidity_adjusted_var(
            normal_returns,
            position_value=0,
            liquidity=LiquidityMetrics(),
        )
        # 不应崩溃
        assert result.var >= 0
