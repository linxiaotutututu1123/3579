"""
中国期货压力测试测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 测试
V4 Scenarios:
- CHINA.STRESS.2015_CRASH: 2015股灾场景
- CHINA.STRESS.2020_OIL: 2020原油负价场景
- CHINA.STRESS.2022_LITHIUM: 2022碳酸锂场景

军规覆盖:
- M6: 熔断保护
- M19: 风险归因
"""

from __future__ import annotations

from datetime import date

import pytest

from src.risk.stress_test_china import (
    HYPOTHETICAL_SCENARIOS,
    STRESS_SCENARIOS,
    ImpactLevel,
    PositionExposure,
    RiskAction,
    ScenarioType,
    StressScenario,
    StressTester,
    StressTestResult,
    StressTestSummary,
    get_all_scenarios,
    get_default_tester,
    get_scenario_by_name,
    run_stress_test,
)


# ============================================================
# 枚举测试
# ============================================================


class TestScenarioTypeEnum:
    """场景类型枚举测试."""

    def test_all_types_exist(self) -> None:
        """测试所有类型存在."""
        assert ScenarioType.HISTORICAL.value == "HISTORICAL"
        assert ScenarioType.HYPOTHETICAL.value == "HYPOTHETICAL"
        assert ScenarioType.SENSITIVITY.value == "SENSITIVITY"
        assert ScenarioType.REVERSE.value == "REVERSE"

    def test_type_count(self) -> None:
        """测试类型数量."""
        assert len(ScenarioType) == 4


class TestImpactLevelEnum:
    """影响等级枚举测试."""

    def test_all_levels_exist(self) -> None:
        """测试所有等级存在."""
        assert ImpactLevel.NEGLIGIBLE.value == "NEGLIGIBLE"
        assert ImpactLevel.MINOR.value == "MINOR"
        assert ImpactLevel.MODERATE.value == "MODERATE"
        assert ImpactLevel.SIGNIFICANT.value == "SIGNIFICANT"
        assert ImpactLevel.SEVERE.value == "SEVERE"

    def test_level_count(self) -> None:
        """测试等级数量."""
        assert len(ImpactLevel) == 5


class TestRiskActionEnum:
    """风险行动枚举测试."""

    def test_all_actions_exist(self) -> None:
        """测试所有行动存在."""
        assert RiskAction.NONE.value == "NONE"
        assert RiskAction.MONITOR.value == "MONITOR"
        assert RiskAction.REDUCE.value == "REDUCE"
        assert RiskAction.HEDGE.value == "HEDGE"
        assert RiskAction.CLOSE.value == "CLOSE"

    def test_action_count(self) -> None:
        """测试行动数量."""
        assert len(RiskAction) == 5


# ============================================================
# 数据类测试
# ============================================================


class TestStressScenario:
    """压力测试场景数据类测试."""

    def test_create_scenario(self) -> None:
        """测试创建场景."""
        scenario = StressScenario(
            name="TEST_SCENARIO",
            description="测试场景",
            scenario_type=ScenarioType.HISTORICAL,
            price_shock=-0.10,
            duration_days=3,
            affected_products=("IF", "IH"),
            probability=0.01,
            reference_date=date(2025, 1, 1),
        )
        assert scenario.name == "TEST_SCENARIO"
        assert scenario.price_shock == -0.10
        assert scenario.duration_days == 3
        assert "IF" in scenario.affected_products

    def test_scenario_frozen(self) -> None:
        """测试场景不可变."""
        scenario = StressScenario(
            name="TEST",
            description="Test",
            scenario_type=ScenarioType.HISTORICAL,
            price_shock=-0.10,
            duration_days=1,
            affected_products=("IF",),
        )
        with pytest.raises(AttributeError):
            scenario.name = "CHANGED"  # type: ignore[misc]


class TestPositionExposure:
    """持仓风险敞口数据类测试."""

    def test_create_exposure(self) -> None:
        """测试创建敞口."""
        exposure = PositionExposure(
            symbol="IF2501",
            product="IF",
            position=10,
            value=1000000.0,
            margin=100000.0,
            delta=1.0,
        )
        assert exposure.symbol == "IF2501"
        assert exposure.product == "IF"
        assert exposure.position == 10
        assert exposure.value == 1000000.0

    def test_short_position(self) -> None:
        """测试空头持仓."""
        exposure = PositionExposure(
            symbol="IF2501",
            product="IF",
            position=-10,
            value=-1000000.0,
            margin=100000.0,
        )
        assert exposure.position < 0


# ============================================================
# 预定义场景测试
# ============================================================


class TestStressScenarios:
    """预定义压力场景测试."""

    def test_stress_scenarios_count(self) -> None:
        """测试历史场景数量."""
        assert len(STRESS_SCENARIOS) == 6

    def test_hypothetical_scenarios_count(self) -> None:
        """测试假设场景数量."""
        assert len(HYPOTHETICAL_SCENARIOS) == 3

    def test_crash_2015_scenario(self) -> None:
        """测试2015股灾场景."""
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None
        assert scenario.name == "CRASH_2015"
        assert scenario.price_shock == -0.10
        assert scenario.duration_days == 5
        assert "IF" in scenario.affected_products

    def test_oil_negative_2020_scenario(self) -> None:
        """测试2020原油负价场景."""
        scenario = get_scenario_by_name("OIL_NEGATIVE_2020")
        assert scenario is not None
        assert scenario.price_shock == -0.15
        assert "sc" in scenario.affected_products

    def test_lithium_2022_scenario(self) -> None:
        """测试2022碳酸锂场景."""
        scenario = get_scenario_by_name("LITHIUM_2022")
        assert scenario is not None
        assert scenario.price_shock == -0.15
        assert "LC" in scenario.affected_products

    def test_all_scenarios_have_required_fields(self) -> None:
        """测试所有场景都有必填字段."""
        for scenario in STRESS_SCENARIOS:
            assert scenario.name
            assert scenario.description
            assert scenario.scenario_type is not None
            assert scenario.price_shock != 0
            assert scenario.duration_days > 0
            assert len(scenario.affected_products) > 0


# ============================================================
# StressTester 测试 - CHINA.STRESS.2015_CRASH
# ============================================================


class TestStressTester2015Crash:
    """2015股灾场景测试.

    V4 Scenario: CHINA.STRESS.2015_CRASH
    军规: M6 熔断保护
    """

    RULE_ID = "CHINA.STRESS.2015_CRASH"

    @pytest.fixture
    def tester(self) -> StressTester:
        """创建测试器."""
        return StressTester()

    @pytest.fixture
    def if_positions(self) -> list[PositionExposure]:
        """创建股指期货持仓."""
        return [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=10,
                value=1000000.0,
                margin=120000.0,
            ),
            PositionExposure(
                symbol="IH2501",
                product="IH",
                position=5,
                value=500000.0,
                margin=60000.0,
            ),
        ]

    def test_crash_2015_scenario(
        self, tester: StressTester, if_positions: list[PositionExposure]
    ) -> None:
        """测试2015股灾场景影响."""
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            if_positions,
            portfolio_value=1500000.0,
            margin_used=180000.0,
        )

        assert result.pnl < 0  # 应该亏损
        assert result.positions_affected == 2  # 两个股指期货持仓
        assert result.impact_level in (
            ImpactLevel.MODERATE,
            ImpactLevel.SIGNIFICANT,
            ImpactLevel.SEVERE,
        )

    def test_crash_2015_unaffected_position(self, tester: StressTester) -> None:
        """测试2015股灾不影响商品持仓."""
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        # 螺纹钢持仓不受股指期货影响
        rb_positions = [
            PositionExposure(
                symbol="rb2501",
                product="rb",
                position=10,
                value=500000.0,
                margin=50000.0,
            )
        ]

        result = tester.run_scenario(
            scenario,
            rb_positions,
            portfolio_value=500000.0,
            margin_used=50000.0,
        )

        assert result.positions_affected == 0
        assert result.pnl == 0.0


# ============================================================
# StressTester 测试 - CHINA.STRESS.2020_OIL
# ============================================================


class TestStressTester2020Oil:
    """2020原油负价场景测试.

    V4 Scenario: CHINA.STRESS.2020_OIL
    军规: M6 熔断保护
    """

    RULE_ID = "CHINA.STRESS.2020_OIL"

    def test_oil_negative_scenario(self) -> None:
        """测试原油负价场景."""
        tester = StressTester()
        scenario = get_scenario_by_name("OIL_NEGATIVE_2020")
        assert scenario is not None

        positions = [
            PositionExposure(
                symbol="sc2501",
                product="sc",
                position=5,
                value=800000.0,
                margin=120000.0,
            )
        ]

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=800000.0,
            margin_used=120000.0,
        )

        assert result.pnl < 0
        assert result.positions_affected == 1
        # 15%冲击 + 50%流动性冲击 = 严重影响
        assert result.impact_level in (ImpactLevel.SIGNIFICANT, ImpactLevel.SEVERE)


# ============================================================
# StressTester 测试 - CHINA.STRESS.2022_LITHIUM
# ============================================================


class TestStressTester2022Lithium:
    """2022碳酸锂场景测试.

    V4 Scenario: CHINA.STRESS.2022_LITHIUM
    军规: M6 熔断保护
    """

    RULE_ID = "CHINA.STRESS.2022_LITHIUM"

    def test_lithium_crash_scenario(self) -> None:
        """测试碳酸锂暴跌场景."""
        tester = StressTester()
        scenario = get_scenario_by_name("LITHIUM_2022")
        assert scenario is not None

        positions = [
            PositionExposure(
                symbol="LC2501",
                product="LC",
                position=3,
                value=600000.0,
                margin=90000.0,
            )
        ]

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=600000.0,
            margin_used=90000.0,
        )

        assert result.pnl < 0
        # 15%×5天 = 75%累计冲击
        assert result.impact_level == ImpactLevel.SEVERE


# ============================================================
# StressTester 核心功能测试
# ============================================================


class TestStressTesterCore:
    """压力测试器核心功能测试."""

    def test_tester_initialization(self) -> None:
        """测试初始化."""
        tester = StressTester()
        assert tester._margin_multiplier == 1.2

    def test_custom_margin_multiplier(self) -> None:
        """测试自定义保证金乘数."""
        tester = StressTester(margin_multiplier=1.5)
        assert tester._margin_multiplier == 1.5

    def test_run_all_scenarios(self) -> None:
        """测试运行所有场景."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        summary = tester.run_all_scenarios(
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
        )

        assert isinstance(summary, StressTestSummary)
        assert summary.total_scenarios == len(STRESS_SCENARIOS)
        assert len(summary.results) == len(STRESS_SCENARIOS)

    def test_run_all_with_hypothetical(self) -> None:
        """测试包含假设场景."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="cu2501",
                product="cu",
                position=10,
                value=800000.0,
                margin=80000.0,
            )
        ]

        summary = tester.run_all_scenarios(
            positions,
            portfolio_value=800000.0,
            margin_used=80000.0,
            include_hypothetical=True,
        )

        expected_count = len(STRESS_SCENARIOS) + len(HYPOTHETICAL_SCENARIOS)
        assert summary.total_scenarios == expected_count

    def test_empty_positions(self) -> None:
        """测试空持仓."""
        tester = StressTester()
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            positions=[],
            portfolio_value=100000.0,
            margin_used=0.0,
        )

        assert result.pnl == 0.0
        assert result.positions_affected == 0


# ============================================================
# 影响等级计算测试
# ============================================================


class TestImpactLevelCalculation:
    """影响等级计算测试."""

    def test_negligible_impact(self) -> None:
        """测试可忽略影响."""
        tester = StressTester()
        level = tester._calculate_impact_level(0.005)
        assert level == ImpactLevel.NEGLIGIBLE

    def test_minor_impact(self) -> None:
        """测试轻微影响."""
        tester = StressTester()
        level = tester._calculate_impact_level(0.03)
        assert level == ImpactLevel.MINOR

    def test_moderate_impact(self) -> None:
        """测试中等影响."""
        tester = StressTester()
        level = tester._calculate_impact_level(0.07)
        assert level == ImpactLevel.MODERATE

    def test_significant_impact(self) -> None:
        """测试显著影响."""
        tester = StressTester()
        level = tester._calculate_impact_level(0.15)
        assert level == ImpactLevel.SIGNIFICANT

    def test_severe_impact(self) -> None:
        """测试严重影响."""
        tester = StressTester()
        level = tester._calculate_impact_level(0.25)
        assert level == ImpactLevel.SEVERE


# ============================================================
# 建议行动测试
# ============================================================


class TestRecommendedAction:
    """建议行动测试."""

    def test_action_with_margin_call(self) -> None:
        """测试有追保时的行动."""
        tester = StressTester()
        action = tester._determine_action(ImpactLevel.MINOR, margin_call=10000.0)
        assert action == RiskAction.CLOSE

    def test_action_negligible(self) -> None:
        """测试可忽略影响的行动."""
        tester = StressTester()
        action = tester._determine_action(ImpactLevel.NEGLIGIBLE, margin_call=0.0)
        assert action == RiskAction.NONE

    def test_action_moderate(self) -> None:
        """测试中等影响的行动."""
        tester = StressTester()
        action = tester._determine_action(ImpactLevel.MODERATE, margin_call=0.0)
        assert action == RiskAction.MONITOR

    def test_action_severe(self) -> None:
        """测试严重影响的行动."""
        tester = StressTester()
        action = tester._determine_action(ImpactLevel.SEVERE, margin_call=0.0)
        assert action == RiskAction.CLOSE


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_tester(self) -> None:
        """测试获取默认测试器."""
        tester = get_default_tester()
        assert isinstance(tester, StressTester)

    def test_get_scenario_by_name_exists(self) -> None:
        """测试按名称获取存在的场景."""
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None
        assert scenario.name == "CRASH_2015"

    def test_get_scenario_by_name_not_exists(self) -> None:
        """测试按名称获取不存在的场景."""
        scenario = get_scenario_by_name("NOT_EXISTS")
        assert scenario is None

    def test_get_scenario_hypothetical(self) -> None:
        """测试获取假设场景."""
        scenario = get_scenario_by_name("SYSTEMIC_CRASH")
        assert scenario is not None
        assert scenario.scenario_type == ScenarioType.HYPOTHETICAL

    def test_get_all_scenarios(self) -> None:
        """测试获取所有场景."""
        scenarios = get_all_scenarios()
        assert len(scenarios) == len(STRESS_SCENARIOS)

    def test_get_all_scenarios_with_hypothetical(self) -> None:
        """测试获取所有场景含假设."""
        scenarios = get_all_scenarios(include_hypothetical=True)
        expected = len(STRESS_SCENARIOS) + len(HYPOTHETICAL_SCENARIOS)
        assert len(scenarios) == expected

    def test_run_stress_test_single(self) -> None:
        """测试运行单个场景."""
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        result = run_stress_test(
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
            scenario_name="CRASH_2015",
        )

        assert isinstance(result, StressTestResult)

    def test_run_stress_test_all(self) -> None:
        """测试运行所有场景."""
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        result = run_stress_test(
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
        )

        assert isinstance(result, StressTestSummary)

    def test_run_stress_test_invalid_scenario(self) -> None:
        """测试无效场景名."""
        positions: list[PositionExposure] = []

        with pytest.raises(ValueError, match="未找到场景"):
            run_stress_test(
                positions,
                portfolio_value=100000.0,
                margin_used=0.0,
                scenario_name="INVALID_SCENARIO",
            )


# ============================================================
# 军规覆盖测试
# ============================================================


class TestMilitaryRuleM6:
    """军规 M6 熔断保护测试.

    军规: 触发风控阈值必须立即停止
    """

    RULE_ID = "M6.STRESS_TEST"

    def test_severe_impact_triggers_close(self) -> None:
        """测试严重影响触发平仓."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=100,  # 大仓位
                value=10000000.0,
                margin=1200000.0,
            )
        ]

        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=10000000.0,
            margin_used=1200000.0,
        )

        # 大仓位在股灾中应该触发严重影响
        if result.impact_level == ImpactLevel.SEVERE:
            assert result.recommended_action == RiskAction.CLOSE


class TestMilitaryRuleM19:
    """军规 M19 风险归因测试.

    军规: 每笔亏损必须有归因分析
    """

    RULE_ID = "M19.RISK_ATTRIBUTION"

    def test_risk_metrics_provided(self) -> None:
        """测试风险指标提供."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=10,
                value=1000000.0,
                margin=120000.0,
            )
        ]

        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=1000000.0,
            margin_used=120000.0,
        )

        # 验证风险指标存在
        assert "scenario_probability" in result.risk_metrics
        assert "expected_loss" in result.risk_metrics
        assert "volatility_adjusted_loss" in result.risk_metrics
        assert "margin_call_risk" in result.risk_metrics

    def test_position_details_attribution(self) -> None:
        """测试持仓详情归因."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=10,
                value=1000000.0,
                margin=120000.0,
            )
        ]

        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=1000000.0,
            margin_used=120000.0,
        )

        # 验证持仓详情包含归因
        assert len(result.position_details) > 0
        for detail in result.position_details:
            assert "symbol" in detail
            assert "pnl" in detail
            assert "pnl_pct" in detail
            assert "is_at_risk" in detail


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_zero_portfolio_value(self) -> None:
        """测试零组合价值."""
        tester = StressTester()
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        result = tester.run_scenario(
            scenario,
            positions=[],
            portfolio_value=0.0,
            margin_used=0.0,
        )

        assert result.pnl_pct == 0.0

    def test_all_products_affected(self) -> None:
        """测试ALL品种影响."""
        tester = StressTester()
        scenario = get_scenario_by_name("SYSTEMIC_CRASH")
        assert scenario is not None
        assert "ALL" in scenario.affected_products

        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            ),
            PositionExposure(
                symbol="rb2501",
                product="rb",
                position=10,
                value=300000.0,
                margin=30000.0,
            ),
        ]

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=800000.0,
            margin_used=90000.0,
        )

        # 所有持仓都应该受影响
        assert result.positions_affected == 2

    def test_short_position_profit_on_crash(self) -> None:
        """测试空头在下跌时获利."""
        tester = StressTester()
        scenario = StressScenario(
            name="TEST_CRASH",
            description="测试下跌",
            scenario_type=ScenarioType.HYPOTHETICAL,
            price_shock=-0.10,
            duration_days=1,
            affected_products=("IF",),
        )

        # 空头持仓
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=-10,  # 空头
                value=-1000000.0,
                margin=120000.0,
            )
        ]

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=1000000.0,
            margin_used=120000.0,
        )

        # 空头在下跌时应该获利 (pnl > 0)
        assert result.pnl > 0


# ============================================================
# StressTestResult 格式测试
# ============================================================


class TestStressTestResultFormat:
    """压力测试结果格式测试."""

    def test_result_has_all_fields(self) -> None:
        """测试结果包含所有字段."""
        tester = StressTester()
        scenario = get_scenario_by_name("CRASH_2015")
        assert scenario is not None

        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        result = tester.run_scenario(
            scenario,
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
        )

        # 验证所有字段
        assert result.scenario == scenario
        assert result.portfolio_value_before == 500000.0
        assert isinstance(result.portfolio_value_after, float)
        assert isinstance(result.pnl, float)
        assert isinstance(result.pnl_pct, float)
        assert isinstance(result.impact_level, ImpactLevel)
        assert result.margin_before == 60000.0
        assert isinstance(result.margin_after, float)
        assert isinstance(result.margin_call_amount, float)
        assert isinstance(result.positions_affected, int)
        assert isinstance(result.positions_at_risk, int)
        assert isinstance(result.position_details, list)
        assert isinstance(result.recommended_action, RiskAction)
        assert isinstance(result.risk_metrics, dict)
        assert isinstance(result.timestamp, str)


# ============================================================
# StressTestSummary 格式测试
# ============================================================


class TestStressTestSummaryFormat:
    """压力测试汇总格式测试."""

    def test_summary_has_all_fields(self) -> None:
        """测试汇总包含所有字段."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        summary = tester.run_all_scenarios(
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
        )

        assert isinstance(summary.total_scenarios, int)
        assert isinstance(summary.passed, int)
        assert isinstance(summary.warning, int)
        assert isinstance(summary.failed, int)
        assert isinstance(summary.worst_scenario, str)
        assert isinstance(summary.worst_pnl, float)
        assert isinstance(summary.worst_pnl_pct, float)
        assert isinstance(summary.total_margin_call, float)
        assert isinstance(summary.results, list)

    def test_summary_statistics_consistent(self) -> None:
        """测试汇总统计一致性."""
        tester = StressTester()
        positions = [
            PositionExposure(
                symbol="IF2501",
                product="IF",
                position=5,
                value=500000.0,
                margin=60000.0,
            )
        ]

        summary = tester.run_all_scenarios(
            positions,
            portfolio_value=500000.0,
            margin_used=60000.0,
        )

        # passed + warning + failed = total
        assert summary.passed + summary.warning + summary.failed == summary.total_scenarios
