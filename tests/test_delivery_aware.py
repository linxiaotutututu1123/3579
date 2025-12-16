"""
交割感知套利测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 测试
V4 Scenarios:
- CHINA.ARB.DELIVERY_AWARE: 交割感知套利
- CHINA.ARB.POSITION_TRANSFER: 移仓换月逻辑

军规覆盖:
- M6: 熔断保护
- M15: 夜盘跨日处理
"""

from __future__ import annotations

from datetime import date

import pytest

from src.strategy.calendar_arb.delivery_aware import (
    ContractInfo,
    DeliveryAwareCalendarArb,
    DeliveryConfig,
    DeliverySnapshot,
    DeliveryStatus,
    MainContractDetector,
    RollPlan,
    RollSignal,
    check_contract_delivery,
    create_delivery_aware_strategy,
    get_default_delivery_config,
)


# ============================================================
# 枚举测试
# ============================================================


class TestRollSignalEnum:
    """移仓信号枚举测试."""

    def test_all_signals_exist(self) -> None:
        """测试所有信号存在."""
        assert RollSignal.HOLD.value == "HOLD"
        assert RollSignal.PREPARE.value == "PREPARE"
        assert RollSignal.ROLL_NOW.value == "ROLL_NOW"
        assert RollSignal.FORCE_CLOSE.value == "FORCE_CLOSE"

    def test_signal_count(self) -> None:
        """测试信号数量."""
        assert len(RollSignal) == 4


class TestDeliveryStatusEnum:
    """交割状态枚举测试."""

    def test_all_statuses_exist(self) -> None:
        """测试所有状态存在."""
        assert DeliveryStatus.SAFE.value == "SAFE"
        assert DeliveryStatus.NORMAL.value == "NORMAL"
        assert DeliveryStatus.WARNING.value == "WARNING"
        assert DeliveryStatus.CRITICAL.value == "CRITICAL"
        assert DeliveryStatus.EXPIRED.value == "EXPIRED"

    def test_status_count(self) -> None:
        """测试状态数量."""
        assert len(DeliveryStatus) == 5


# ============================================================
# 数据类测试
# ============================================================


class TestDeliveryConfig:
    """交割配置数据类测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = DeliveryConfig()
        assert config.warning_days == 10
        assert config.critical_days == 5
        assert config.force_close_days == 2
        assert config.roll_spread_limit == 0.02
        assert config.auto_roll_enabled is True
        assert config.max_roll_slippage == 0.005

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = DeliveryConfig(
            warning_days=15,
            critical_days=7,
            force_close_days=3,
        )
        assert config.warning_days == 15
        assert config.critical_days == 7
        assert config.force_close_days == 3

    def test_config_frozen(self) -> None:
        """测试配置不可变."""
        config = DeliveryConfig()
        with pytest.raises(AttributeError):
            config.warning_days = 20  # type: ignore[misc]


class TestContractInfo:
    """合约信息数据类测试."""

    def test_create_contract(self) -> None:
        """测试创建合约."""
        contract = ContractInfo(
            symbol="rb2501",
            product="rb",
            delivery_date=date(2025, 1, 15),
            is_main=True,
            volume=100000,
            open_interest=50000,
        )
        assert contract.symbol == "rb2501"
        assert contract.product == "rb"
        assert contract.delivery_date == date(2025, 1, 15)
        assert contract.is_main is True


class TestRollPlan:
    """移仓计划数据类测试."""

    def test_create_plan(self) -> None:
        """测试创建计划."""
        plan = RollPlan(
            from_contract="rb2501",
            to_contract="rb2505",
            signal=RollSignal.PREPARE,
            days_to_delivery=8,
            status=DeliveryStatus.WARNING,
            spread_pct=0.01,
            estimated_cost=100.0,
            reason="距交割8天, 建议准备移仓",
        )
        assert plan.from_contract == "rb2501"
        assert plan.to_contract == "rb2505"
        assert plan.signal == RollSignal.PREPARE
        assert plan.days_to_delivery == 8


# ============================================================
# DeliveryAwareCalendarArb 测试 - CHINA.ARB.DELIVERY_AWARE
# ============================================================


class TestDeliveryAwareCalendarArb:
    """交割感知套利策略测试.

    V4 Scenario: CHINA.ARB.DELIVERY_AWARE
    军规: M6 熔断保护, M15 夜盘跨日处理
    """

    RULE_ID = "CHINA.ARB.DELIVERY_AWARE"

    @pytest.fixture
    def strategy(self) -> DeliveryAwareCalendarArb:
        """创建策略实例."""
        return DeliveryAwareCalendarArb()

    @pytest.fixture
    def registered_strategy(self) -> DeliveryAwareCalendarArb:
        """创建注册了合约的策略."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
                is_main=True,
            )
        )
        strategy.register_contract(
            ContractInfo(
                symbol="rb2505",
                product="rb",
                delivery_date=date(2025, 5, 15),
            )
        )
        return strategy

    def test_initialization(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试初始化."""
        assert strategy.config is not None
        assert strategy.config.warning_days == 10

    def test_register_contract(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试注册合约."""
        contract = ContractInfo(
            symbol="rb2501",
            product="rb",
            delivery_date=date(2025, 1, 15),
            is_main=True,
        )
        strategy.register_contract(contract)

        assert strategy.get_contract("rb2501") is not None
        assert strategy.get_main_contract("rb") == "rb2501"

    def test_check_delivery_safe(self, registered_strategy: DeliveryAwareCalendarArb) -> None:
        """测试安全期检查."""
        # 距离交割50天
        current = date(2024, 11, 26)
        plan = registered_strategy.check_delivery("rb2501", current)
        assert plan is None  # 安全期无需移仓

    def test_check_delivery_warning(self, registered_strategy: DeliveryAwareCalendarArb) -> None:
        """测试预警期检查."""
        # 距离交割8天
        current = date(2025, 1, 7)
        plan = registered_strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.signal == RollSignal.PREPARE
        assert plan.status == DeliveryStatus.WARNING

    def test_check_delivery_critical(self, registered_strategy: DeliveryAwareCalendarArb) -> None:
        """测试危险期检查."""
        # 距离交割3天
        current = date(2025, 1, 12)
        plan = registered_strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.signal == RollSignal.ROLL_NOW
        assert plan.status == DeliveryStatus.CRITICAL

    def test_check_delivery_force_close(
        self, registered_strategy: DeliveryAwareCalendarArb
    ) -> None:
        """测试强制平仓检查."""
        # 距离交割1天
        current = date(2025, 1, 14)
        plan = registered_strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.signal == RollSignal.FORCE_CLOSE

    def test_check_delivery_expired(self, registered_strategy: DeliveryAwareCalendarArb) -> None:
        """测试过期合约检查."""
        # 已过交割日
        current = date(2025, 1, 20)
        plan = registered_strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.signal == RollSignal.FORCE_CLOSE
        assert plan.status == DeliveryStatus.EXPIRED

    def test_check_delivery_unknown_contract(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试未知合约检查."""
        plan = strategy.check_delivery("unknown")
        assert plan is None


# ============================================================
# 移仓换月逻辑测试 - CHINA.ARB.POSITION_TRANSFER
# ============================================================


class TestPositionTransfer:
    """移仓换月逻辑测试.

    V4 Scenario: CHINA.ARB.POSITION_TRANSFER
    军规: M15 夜盘跨日处理
    """

    RULE_ID = "CHINA.ARB.POSITION_TRANSFER"

    @pytest.fixture
    def strategy(self) -> DeliveryAwareCalendarArb:
        """创建带合约的策略."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )
        strategy.register_contract(
            ContractInfo(
                symbol="rb2505",
                product="rb",
                delivery_date=date(2025, 5, 15),
                is_main=True,
            )
        )
        return strategy

    def test_should_roll_true(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试需要移仓."""
        current = date(2025, 1, 7)  # 8天
        assert strategy.should_roll("rb2501", current) is True

    def test_should_roll_false(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试不需要移仓."""
        current = date(2024, 11, 1)  # 远期
        assert strategy.should_roll("rb2501", current) is False

    def test_should_force_close_true(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试需要强制平仓."""
        current = date(2025, 1, 14)  # 1天
        assert strategy.should_force_close("rb2501", current) is True

    def test_should_force_close_false(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试不需要强制平仓."""
        current = date(2025, 1, 7)  # 8天
        assert strategy.should_force_close("rb2501", current) is False

    def test_get_roll_target(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试获取移仓目标."""
        target = strategy.get_roll_target("rb2501")
        assert target == "rb2505"

    def test_get_roll_target_not_found(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试获取移仓目标未找到."""
        target = strategy.get_roll_target("unknown")
        assert target is None

    def test_check_all_positions(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试检查所有持仓."""
        current = date(2025, 1, 7)
        snapshot = strategy.check_all_positions(["rb2501"], current)

        assert isinstance(snapshot, DeliverySnapshot)
        assert snapshot.current_date == current
        assert len(snapshot.roll_plans) == 1
        assert snapshot.roll_plans[0].signal == RollSignal.PREPARE

    def test_check_all_positions_with_warnings(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试检查带预警的持仓."""
        current = date(2025, 1, 12)  # 3天
        snapshot = strategy.check_all_positions(["rb2501"], current)

        assert len(snapshot.warnings) > 0
        assert "rb2501" in snapshot.warnings[0]

    def test_calculate_roll_cost(self, strategy: DeliveryAwareCalendarArb) -> None:
        """测试计算移仓成本."""
        cost = strategy.calculate_roll_cost(
            from_price=4200.0,
            to_price=4250.0,
            volume=10,
            multiplier=10.0,
            fee_rate=0.0001,
        )

        assert "spread_pnl" in cost
        assert "total_fee" in cost
        assert "total_slippage" in cost
        assert "total_cost" in cost

        # 价差损益 = (4250-4200) * 10 * 10 = 5000
        assert cost["spread_pnl"] == 5000.0


# ============================================================
# 主力合约切换检测测试
# ============================================================


class TestMainContractDetector:
    """主力合约切换检测器测试."""

    def test_initialization(self) -> None:
        """测试初始化."""
        detector = MainContractDetector()
        assert detector._volume_threshold == 1.5

    def test_update_and_detect(self) -> None:
        """测试更新和检测."""
        detector = MainContractDetector()

        # 初始主力
        detector.update("rb2501", "rb", volume=100000, open_interest=50000)
        new_main = detector.detect_switch("rb")
        assert new_main == "rb2501"

    def test_detect_switch(self) -> None:
        """测试检测切换."""
        detector = MainContractDetector(volume_threshold=1.5)

        # 设置初始主力
        detector.update("rb2501", "rb", volume=100000, open_interest=50000)
        detector.detect_switch("rb")

        # 新合约成交量超过1.5倍时切换
        detector.update("rb2505", "rb", volume=160000, open_interest=60000)
        new_main = detector.detect_switch("rb")
        assert new_main == "rb2505"

    def test_no_switch_below_threshold(self) -> None:
        """测试低于阈值不切换."""
        detector = MainContractDetector(volume_threshold=1.5)

        # 设置初始主力
        detector.update("rb2501", "rb", volume=100000, open_interest=50000)
        detector.detect_switch("rb")

        # 新合约成交量未超过1.5倍
        detector.update("rb2505", "rb", volume=140000, open_interest=60000)
        new_main = detector.detect_switch("rb")
        assert new_main is None  # 不切换

    def test_get_main_contract(self) -> None:
        """测试获取主力合约."""
        detector = MainContractDetector()
        detector.update("rb2501", "rb", volume=100000, open_interest=50000)
        detector.detect_switch("rb")

        main = detector.get_main_contract("rb")
        assert main == "rb2501"


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_delivery_config(self) -> None:
        """测试获取默认配置."""
        config = get_default_delivery_config()
        assert isinstance(config, DeliveryConfig)
        assert config.warning_days == 10

    def test_create_delivery_aware_strategy(self) -> None:
        """测试创建策略."""
        strategy = create_delivery_aware_strategy()
        assert isinstance(strategy, DeliveryAwareCalendarArb)

    def test_create_with_config(self) -> None:
        """测试带配置创建."""
        config = DeliveryConfig(warning_days=15)
        strategy = create_delivery_aware_strategy(config)
        assert strategy.config.warning_days == 15

    def test_check_contract_delivery(self) -> None:
        """测试检查合约交割便捷函数."""
        plan = check_contract_delivery(
            symbol="rb2501",
            delivery_date=date(2025, 1, 15),
            current_date=date(2025, 1, 7),
        )
        assert plan is not None
        assert plan.signal == RollSignal.PREPARE

    def test_check_contract_delivery_safe(self) -> None:
        """测试安全期便捷函数."""
        plan = check_contract_delivery(
            symbol="rb2501",
            delivery_date=date(2025, 1, 15),
            current_date=date(2024, 11, 1),
        )
        assert plan is None


# ============================================================
# 军规覆盖测试
# ============================================================


class TestMilitaryRuleM6:
    """军规 M6 熔断保护测试.

    军规: 触发风控阈值必须立即停止
    """

    RULE_ID = "M6.DELIVERY_PROTECTION"

    def test_force_close_on_critical(self) -> None:
        """测试危险期强制平仓."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 距交割1天
        current = date(2025, 1, 14)
        assert strategy.should_force_close("rb2501", current) is True

    def test_warning_before_critical(self) -> None:
        """测试危险期前有预警."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 距交割8天 (预警期)
        current = date(2025, 1, 7)
        plan = strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.signal == RollSignal.PREPARE  # 预警


class TestMilitaryRuleM15:
    """军规 M15 夜盘跨日处理测试.

    军规: 交易日归属必须正确
    """

    RULE_ID = "M15.DELIVERY_DATE"

    def test_delivery_date_calculation(self) -> None:
        """测试交割日期计算."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 精确计算天数
        current = date(2025, 1, 10)  # 距交割5天
        plan = strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.days_to_delivery == 5


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_exact_warning_threshold(self) -> None:
        """测试精确预警阈值."""
        config = DeliveryConfig(warning_days=10)
        strategy = DeliveryAwareCalendarArb(config)
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 正好10天
        current = date(2025, 1, 5)
        plan = strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.status == DeliveryStatus.WARNING

    def test_exact_critical_threshold(self) -> None:
        """测试精确危险阈值."""
        config = DeliveryConfig(critical_days=5)
        strategy = DeliveryAwareCalendarArb(config)
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 正好5天
        current = date(2025, 1, 10)
        plan = strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.status == DeliveryStatus.CRITICAL

    def test_same_day_delivery(self) -> None:
        """测试交割当天."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
            )
        )

        # 交割当天
        current = date(2025, 1, 15)
        plan = strategy.check_delivery("rb2501", current)
        assert plan is not None
        assert plan.days_to_delivery == 0
        assert plan.signal == RollSignal.FORCE_CLOSE

    def test_empty_positions(self) -> None:
        """测试空持仓列表."""
        strategy = DeliveryAwareCalendarArb()
        snapshot = strategy.check_all_positions([])
        assert len(snapshot.positions) == 0
        assert len(snapshot.roll_plans) == 0

    def test_multiple_products(self) -> None:
        """测试多品种."""
        strategy = DeliveryAwareCalendarArb()
        strategy.register_contract(
            ContractInfo(
                symbol="rb2501",
                product="rb",
                delivery_date=date(2025, 1, 15),
                is_main=True,
            )
        )
        strategy.register_contract(
            ContractInfo(
                symbol="hc2501",
                product="hc",
                delivery_date=date(2025, 1, 15),
                is_main=True,
            )
        )

        assert strategy.get_main_contract("rb") == "rb2501"
        assert strategy.get_main_contract("hc") == "hc2501"
