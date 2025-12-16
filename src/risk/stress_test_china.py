"""
中国期货市场压力测试 - StressTest (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §23 压力测试场景
V4 Scenarios:
- CHINA.STRESS.2015_CRASH: 2015股灾场景
- CHINA.STRESS.2020_OIL: 2020原油负价场景
- CHINA.STRESS.2022_LITHIUM: 2022碳酸锂场景

军规覆盖:
- M6: 熔断保护 - 触发风控阈值必须立即停止
- M19: 风险归因 - 每笔亏损必须有归因分析

功能特性:
- 历史极端场景回测 (6大历史场景)
- 组合压力测试 (价格冲击/保证金/流动性)
- 情景分析 (单品种/跨品种/系统性)
- 压力测试报告生成

示例:
    >>> from src.risk.stress_test_china import (
    ...     StressScenario,
    ...     STRESS_SCENARIOS,
    ...     run_stress_test,
    ...     StressTester,
    ... )
    >>> tester = StressTester()
    >>> result = tester.run_scenario(STRESS_SCENARIOS[0], portfolio)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class ScenarioType(Enum):
    """场景类型枚举."""

    HISTORICAL = "HISTORICAL"  # 历史场景回放
    HYPOTHETICAL = "HYPOTHETICAL"  # 假设场景
    SENSITIVITY = "SENSITIVITY"  # 敏感性分析
    REVERSE = "REVERSE"  # 反向压力测试


class ImpactLevel(Enum):
    """影响等级枚举."""

    NEGLIGIBLE = "NEGLIGIBLE"  # 可忽略 (<1%)
    MINOR = "MINOR"  # 轻微 (1%-5%)
    MODERATE = "MODERATE"  # 中等 (5%-10%)
    SIGNIFICANT = "SIGNIFICANT"  # 显著 (10%-20%)
    SEVERE = "SEVERE"  # 严重 (>20%)


class RiskAction(Enum):
    """风险响应行动枚举."""

    NONE = "NONE"  # 无需行动
    MONITOR = "MONITOR"  # 加强监控
    REDUCE = "REDUCE"  # 减仓
    HEDGE = "HEDGE"  # 对冲
    CLOSE = "CLOSE"  # 平仓


@dataclass(frozen=True)
class StressScenario:
    """压力测试场景 (不可变).

    属性:
        name: 场景名称 (唯一标识)
        description: 场景描述
        scenario_type: 场景类型
        price_shock: 价格冲击幅度 (如 -0.10 表示跌10%)
        duration_days: 持续天数
        affected_products: 受影响品种列表
        probability: 历史发生概率 (年化)
        reference_date: 参考日期 (历史场景)
        correlation_shock: 相关性冲击 (可选)
        volatility_multiplier: 波动率乘数 (可选)
        liquidity_shock: 流动性冲击 (可选, 如0.5表示流动性降50%)
    """

    name: str
    description: str
    scenario_type: ScenarioType
    price_shock: float
    duration_days: int
    affected_products: tuple[str, ...]
    probability: float = 0.01
    reference_date: date | None = None
    correlation_shock: float = 0.0
    volatility_multiplier: float = 1.0
    liquidity_shock: float = 0.0


@dataclass
class PositionExposure:
    """持仓风险敞口.

    属性:
        symbol: 合约代码
        product: 品种代码
        position: 持仓数量 (正=多, 负=空)
        value: 持仓市值
        margin: 占用保证金
        delta: Delta敞口
    """

    symbol: str
    product: str
    position: int
    value: float
    margin: float
    delta: float = 1.0  # 默认线性敞口


@dataclass
class StressTestResult:
    """压力测试结果.

    属性:
        scenario: 测试场景
        portfolio_value_before: 测试前组合价值
        portfolio_value_after: 测试后组合价值
        pnl: 盈亏
        pnl_pct: 盈亏百分比
        impact_level: 影响等级
        margin_before: 测试前保证金占用
        margin_after: 测试后保证金占用
        margin_call_amount: 追保金额
        positions_affected: 受影响持仓数
        positions_at_risk: 高风险持仓数
        position_details: 持仓详情
        recommended_action: 建议行动
        risk_metrics: 风险指标
        timestamp: 测试时间戳
    """

    scenario: StressScenario
    portfolio_value_before: float
    portfolio_value_after: float
    pnl: float
    pnl_pct: float
    impact_level: ImpactLevel
    margin_before: float
    margin_after: float
    margin_call_amount: float
    positions_affected: int
    positions_at_risk: int
    position_details: list[dict[str, Any]] = field(default_factory=list)
    recommended_action: RiskAction = RiskAction.NONE
    risk_metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class StressTestSummary:
    """压力测试汇总.

    属性:
        total_scenarios: 测试场景数
        passed: 通过数 (影响<10%)
        warning: 预警数 (影响10%-20%)
        failed: 失败数 (影响>20%)
        worst_scenario: 最差场景
        worst_pnl: 最大亏损
        worst_pnl_pct: 最大亏损百分比
        total_margin_call: 总追保金额
        results: 所有结果
    """

    total_scenarios: int
    passed: int
    warning: int
    failed: int
    worst_scenario: str
    worst_pnl: float
    worst_pnl_pct: float
    total_margin_call: float
    results: list[StressTestResult] = field(default_factory=list)


# ============================================================
# 中国期货市场历史极端场景 (按时间顺序)
# ============================================================

STRESS_SCENARIOS: tuple[StressScenario, ...] = (
    # 2015年股灾
    StressScenario(
        name="CRASH_2015",
        description="2015年股灾场景: A股暴跌引发股指期货连续跌停",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=-0.10,
        duration_days=5,
        affected_products=("IF", "IH", "IC"),
        probability=0.01,
        reference_date=date(2015, 6, 26),
        volatility_multiplier=3.0,
        liquidity_shock=0.7,  # 流动性骤降70%
    ),
    # 2016年黑色系暴涨
    StressScenario(
        name="BLACK_2016",
        description="2016年黑色系暴涨场景: 供给侧改革推动螺纹钢暴涨",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=0.06,
        duration_days=3,
        affected_products=("rb", "hc", "i", "j", "jm"),
        probability=0.02,
        reference_date=date(2016, 4, 21),
        volatility_multiplier=2.0,
    ),
    # 2020年原油负价
    StressScenario(
        name="OIL_NEGATIVE_2020",
        description="2020年原油负价场景: WTI原油期货史上首次负价格",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=-0.15,
        duration_days=1,
        affected_products=("sc", "fu", "lu"),
        probability=0.001,
        reference_date=date(2020, 4, 20),
        volatility_multiplier=5.0,
        liquidity_shock=0.5,
    ),
    # 2021年动力煤调控
    StressScenario(
        name="COAL_2021",
        description="2021年动力煤调控场景: 国家调控煤价致动力煤期货连续跌停",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=-0.10,
        duration_days=3,
        affected_products=("ZC",),
        probability=0.01,
        reference_date=date(2021, 10, 19),
        volatility_multiplier=2.5,
    ),
    # 2022年碳酸锂暴跌
    StressScenario(
        name="LITHIUM_2022",
        description="2022年碳酸锂暴跌场景: 新能源需求放缓致碳酸锂期货暴跌",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=-0.15,
        duration_days=5,
        affected_products=("LC",),
        probability=0.01,
        reference_date=date(2022, 11, 10),
        volatility_multiplier=2.0,
    ),
    # 2024年碳酸锂持续下跌
    StressScenario(
        name="LITHIUM_2024",
        description="2024年碳酸锂持续下跌场景: 产能过剩致碳酸锂期货持续阴跌",
        scenario_type=ScenarioType.HISTORICAL,
        price_shock=-0.08,
        duration_days=10,
        affected_products=("LC",),
        probability=0.02,
        reference_date=date(2024, 3, 1),
        volatility_multiplier=1.5,
    ),
)


# ============================================================
# 假设性压力场景
# ============================================================

HYPOTHETICAL_SCENARIOS: tuple[StressScenario, ...] = (
    # 系统性风险 - 全品种暴跌
    StressScenario(
        name="SYSTEMIC_CRASH",
        description="系统性危机: 全品种同时暴跌",
        scenario_type=ScenarioType.HYPOTHETICAL,
        price_shock=-0.08,
        duration_days=3,
        affected_products=("ALL",),
        probability=0.005,
        correlation_shock=0.9,  # 相关性飙升
        volatility_multiplier=3.0,
        liquidity_shock=0.6,
    ),
    # 极端单边 - 涨停板突破
    StressScenario(
        name="EXTREME_UP",
        description="极端上涨: 商品期货连续涨停",
        scenario_type=ScenarioType.HYPOTHETICAL,
        price_shock=0.12,
        duration_days=3,
        affected_products=("cu", "au", "ag"),
        probability=0.01,
        volatility_multiplier=2.5,
    ),
    # 流动性枯竭
    StressScenario(
        name="LIQUIDITY_CRISIS",
        description="流动性危机: 市场流动性骤降",
        scenario_type=ScenarioType.HYPOTHETICAL,
        price_shock=-0.05,
        duration_days=5,
        affected_products=("ALL",),
        probability=0.01,
        liquidity_shock=0.8,  # 流动性降80%
    ),
)


class StressTester:
    """压力测试器 (军规 M6, M19).

    功能:
    - 运行单个场景测试
    - 运行批量场景测试
    - 生成压力测试报告

    示例:
        >>> tester = StressTester()
        >>> result = tester.run_scenario(scenario, positions)
    """

    def __init__(
        self,
        margin_multiplier: float = 1.2,
        impact_thresholds: dict[str, float] | None = None,
    ) -> None:
        """初始化压力测试器.

        参数:
            margin_multiplier: 压力场景保证金乘数 (默认1.2倍)
            impact_thresholds: 影响等级阈值
        """
        self._margin_multiplier = margin_multiplier
        self._impact_thresholds = impact_thresholds or {
            "negligible": 0.01,
            "minor": 0.05,
            "moderate": 0.10,
            "significant": 0.20,
        }

    def run_scenario(
        self,
        scenario: StressScenario,
        positions: list[PositionExposure],
        portfolio_value: float,
        margin_used: float,
    ) -> StressTestResult:
        """运行单个压力测试场景.

        参数:
            scenario: 压力测试场景
            positions: 当前持仓列表
            portfolio_value: 当前组合价值
            margin_used: 当前保证金占用

        返回:
            压力测试结果
        """
        from datetime import datetime

        # 计算受影响持仓
        affected_positions = self._get_affected_positions(positions, scenario.affected_products)

        # 计算盈亏
        pnl = 0.0
        position_details: list[dict[str, Any]] = []
        positions_at_risk = 0

        for pos in affected_positions:
            # 计算单个持仓的压力损益
            pos_pnl = self._calculate_position_pnl(pos, scenario)
            pnl += pos_pnl

            # 判断是否高风险
            pos_pnl_pct = pos_pnl / pos.value if pos.value != 0 else 0
            is_at_risk = abs(pos_pnl_pct) > self._impact_thresholds["significant"]
            if is_at_risk:
                positions_at_risk += 1

            position_details.append(
                {
                    "symbol": pos.symbol,
                    "product": pos.product,
                    "position": pos.position,
                    "value": pos.value,
                    "pnl": pos_pnl,
                    "pnl_pct": pos_pnl_pct,
                    "is_at_risk": is_at_risk,
                }
            )

        # 计算测试后价值
        portfolio_value_after = portfolio_value + pnl
        pnl_pct = pnl / portfolio_value if portfolio_value != 0 else 0

        # 计算影响等级
        impact_level = self._calculate_impact_level(abs(pnl_pct))

        # 计算保证金影响
        margin_after = margin_used * self._margin_multiplier
        margin_call = max(0.0, margin_after - portfolio_value_after)

        # 确定建议行动
        recommended_action = self._determine_action(impact_level, margin_call)

        # 计算风险指标
        risk_metrics = self._calculate_risk_metrics(
            scenario, pnl, pnl_pct, margin_call, positions_at_risk
        )

        return StressTestResult(
            scenario=scenario,
            portfolio_value_before=portfolio_value,
            portfolio_value_after=portfolio_value_after,
            pnl=pnl,
            pnl_pct=pnl_pct,
            impact_level=impact_level,
            margin_before=margin_used,
            margin_after=margin_after,
            margin_call_amount=margin_call,
            positions_affected=len(affected_positions),
            positions_at_risk=positions_at_risk,
            position_details=position_details,
            recommended_action=recommended_action,
            risk_metrics=risk_metrics,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
        )

    def run_all_scenarios(
        self,
        positions: list[PositionExposure],
        portfolio_value: float,
        margin_used: float,
        include_hypothetical: bool = False,
    ) -> StressTestSummary:
        """运行所有压力测试场景.

        参数:
            positions: 当前持仓列表
            portfolio_value: 当前组合价值
            margin_used: 当前保证金占用
            include_hypothetical: 是否包含假设场景

        返回:
            压力测试汇总
        """
        scenarios = list(STRESS_SCENARIOS)
        if include_hypothetical:
            scenarios.extend(HYPOTHETICAL_SCENARIOS)

        results: list[StressTestResult] = []
        worst_pnl = 0.0
        worst_scenario = ""
        total_margin_call = 0.0
        passed = 0
        warning = 0
        failed = 0

        for scenario in scenarios:
            result = self.run_scenario(scenario, positions, portfolio_value, margin_used)
            results.append(result)

            # 统计
            level = result.impact_level
            is_pass = level in (
                ImpactLevel.NEGLIGIBLE,
                ImpactLevel.MINOR,
                ImpactLevel.MODERATE,
            )
            if is_pass:
                passed += 1
            elif level == ImpactLevel.SIGNIFICANT:
                warning += 1
            else:
                failed += 1

            # 追踪最差场景
            if result.pnl < worst_pnl:
                worst_pnl = result.pnl
                worst_scenario = scenario.name

            total_margin_call += result.margin_call_amount

        worst_pnl_pct = worst_pnl / portfolio_value if portfolio_value != 0 else 0

        return StressTestSummary(
            total_scenarios=len(scenarios),
            passed=passed,
            warning=warning,
            failed=failed,
            worst_scenario=worst_scenario,
            worst_pnl=worst_pnl,
            worst_pnl_pct=worst_pnl_pct,
            total_margin_call=total_margin_call,
            results=results,
        )

    def _get_affected_positions(
        self,
        positions: list[PositionExposure],
        affected_products: tuple[str, ...],
    ) -> list[PositionExposure]:
        """获取受影响的持仓.

        参数:
            positions: 所有持仓
            affected_products: 受影响品种

        返回:
            受影响的持仓列表
        """
        if "ALL" in affected_products:
            return positions

        affected = []
        for pos in positions:
            # 检查品种是否受影响 (不区分大小写)
            product_upper = pos.product.upper()
            if any(p.upper() == product_upper for p in affected_products):
                affected.append(pos)

        return affected

    def _calculate_position_pnl(
        self,
        position: PositionExposure,
        scenario: StressScenario,
    ) -> float:
        """计算单个持仓的压力损益.

        参数:
            position: 持仓敞口
            scenario: 压力场景

        返回:
            损益金额
        """
        # 基础价格冲击
        price_shock = scenario.price_shock

        # 考虑持续天数的累积效应 (简化模型)
        cumulative_shock = price_shock * scenario.duration_days

        # 考虑流动性冲击 (增加额外损失)
        if scenario.liquidity_shock > 0:
            liquidity_impact = abs(position.value) * scenario.liquidity_shock * 0.01
        else:
            liquidity_impact = 0.0

        # 计算基础损益
        base_pnl = position.value * cumulative_shock * position.delta

        # 空头反向
        if position.position < 0:
            base_pnl = -base_pnl

        # 加上流动性成本
        total_pnl = base_pnl - liquidity_impact

        return total_pnl

    def _calculate_impact_level(self, pnl_pct: float) -> ImpactLevel:
        """计算影响等级.

        参数:
            pnl_pct: 损益百分比 (绝对值)

        返回:
            影响等级
        """
        if pnl_pct < self._impact_thresholds["negligible"]:
            return ImpactLevel.NEGLIGIBLE
        if pnl_pct < self._impact_thresholds["minor"]:
            return ImpactLevel.MINOR
        if pnl_pct < self._impact_thresholds["moderate"]:
            return ImpactLevel.MODERATE
        if pnl_pct < self._impact_thresholds["significant"]:
            return ImpactLevel.SIGNIFICANT
        return ImpactLevel.SEVERE

    def _determine_action(
        self,
        impact_level: ImpactLevel,
        margin_call: float,
    ) -> RiskAction:
        """确定建议行动.

        参数:
            impact_level: 影响等级
            margin_call: 追保金额

        返回:
            建议行动
        """
        # 有追保需求
        if margin_call > 0:
            return RiskAction.CLOSE

        # 根据影响等级
        action_map = {
            ImpactLevel.NEGLIGIBLE: RiskAction.NONE,
            ImpactLevel.MINOR: RiskAction.MONITOR,
            ImpactLevel.MODERATE: RiskAction.MONITOR,
            ImpactLevel.SIGNIFICANT: RiskAction.REDUCE,
            ImpactLevel.SEVERE: RiskAction.CLOSE,
        }

        return action_map.get(impact_level, RiskAction.MONITOR)

    def _calculate_risk_metrics(
        self,
        scenario: StressScenario,
        pnl: float,
        pnl_pct: float,
        margin_call: float,
        positions_at_risk: int,
    ) -> dict[str, Any]:
        """计算风险指标.

        参数:
            scenario: 场景
            pnl: 损益
            pnl_pct: 损益百分比
            margin_call: 追保金额
            positions_at_risk: 高风险持仓数

        返回:
            风险指标字典
        """
        return {
            "scenario_probability": scenario.probability,
            "expected_loss": pnl * scenario.probability,
            "expected_loss_pct": pnl_pct * scenario.probability,
            "volatility_adjusted_loss": pnl * scenario.volatility_multiplier,
            "margin_call_risk": margin_call > 0,
            "positions_at_risk_ratio": positions_at_risk,
            "liquidity_impact": scenario.liquidity_shock,
            "correlation_impact": scenario.correlation_shock,
        }


# ============================================================
# 便捷函数
# ============================================================


def get_default_tester() -> StressTester:
    """获取默认压力测试器.

    返回:
        默认配置的压力测试器
    """
    return StressTester()


def run_stress_test(
    positions: list[PositionExposure],
    portfolio_value: float,
    margin_used: float,
    scenario_name: str | None = None,
) -> StressTestResult | StressTestSummary:
    """运行压力测试 (便捷函数).

    参数:
        positions: 持仓列表
        portfolio_value: 组合价值
        margin_used: 保证金占用
        scenario_name: 场景名称 (None表示运行所有)

    返回:
        单个结果或汇总
    """
    tester = get_default_tester()

    if scenario_name:
        # 查找指定场景
        scenario = get_scenario_by_name(scenario_name)
        if scenario is None:
            msg = f"未找到场景: {scenario_name}"
            raise ValueError(msg)
        return tester.run_scenario(scenario, positions, portfolio_value, margin_used)

    return tester.run_all_scenarios(positions, portfolio_value, margin_used)


def get_scenario_by_name(name: str) -> StressScenario | None:
    """根据名称获取场景.

    参数:
        name: 场景名称

    返回:
        场景对象或None
    """
    for scenario in STRESS_SCENARIOS:
        if scenario.name == name:
            return scenario
    for scenario in HYPOTHETICAL_SCENARIOS:
        if scenario.name == name:
            return scenario
    return None


def get_all_scenarios(include_hypothetical: bool = False) -> list[StressScenario]:
    """获取所有场景.

    参数:
        include_hypothetical: 是否包含假设场景

    返回:
        场景列表
    """
    scenarios = list(STRESS_SCENARIOS)
    if include_hypothetical:
        scenarios.extend(HYPOTHETICAL_SCENARIOS)
    return scenarios
