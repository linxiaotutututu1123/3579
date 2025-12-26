"""
程序化交易合规测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 测试
V4 Scenarios:
- CHINA.COMPLIANCE.RULE_CHECK: 合规规则检查
- CHINA.COMPLIANCE.REPORT_FREQUENCY: 报撤单频率检查

军规覆盖:
- M17: 程序化合规
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.compliance.programmatic_trading import (
    ComplianceReport,
    ComplianceThrottle,
    OrderAction,
    OrderRecord,
    ProgrammaticTradingCompliance,
    ThrottleConfig,
    ThrottleLevel,
    ThrottleStatus,
    create_compliance_manager,
    create_compliance_throttle,
    get_default_throttle_config,
)


# ============================================================
# 枚举测试
# ============================================================


class TestThrottleLevelEnum:
    """节流等级枚举测试."""

    def test_all_levels_exist(self) -> None:
        """测试所有等级存在."""
        assert ThrottleLevel.NORMAL.value == "NORMAL"
        assert ThrottleLevel.WARNING.value == "WARNING"
        assert ThrottleLevel.CRITICAL.value == "CRITICAL"
        assert ThrottleLevel.EXCEEDED.value == "EXCEEDED"

    def test_level_count(self) -> None:
        """测试等级数量."""
        assert len(ThrottleLevel) == 4


class TestOrderActionEnum:
    """订单操作枚举测试."""

    def test_all_actions_exist(self) -> None:
        """测试所有操作存在."""
        assert OrderAction.SUBMIT.value == "SUBMIT"
        assert OrderAction.CANCEL.value == "CANCEL"
        assert OrderAction.AMEND.value == "AMEND"

    def test_action_count(self) -> None:
        """测试操作数量."""
        assert len(OrderAction) == 3


# ============================================================
# 数据类测试
# ============================================================


class TestThrottleConfig:
    """节流配置数据类测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = ThrottleConfig()
        assert config.limit_5s == 50
        assert config.limit_daily == 20000
        assert config.warning_ratio == 0.6
        assert config.critical_ratio == 0.9
        assert config.high_freq_per_sec == 300
        assert config.cooldown_seconds == 60

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = ThrottleConfig(
            limit_5s=30,
            limit_daily=10000,
            warning_ratio=0.5,
        )
        assert config.limit_5s == 30
        assert config.limit_daily == 10000
        assert config.warning_ratio == 0.5

    def test_config_frozen(self) -> None:
        """测试配置不可变."""
        config = ThrottleConfig()
        with pytest.raises(AttributeError):
            config.limit_5s = 100  # type: ignore[misc]


class TestOrderRecord:
    """订单记录数据类测试."""

    def test_create_record(self) -> None:
        """测试创建记录."""
        now = datetime.now()
        record = OrderRecord(
            timestamp=now,
            action=OrderAction.SUBMIT,
            symbol="rb2501",
            order_id="order_001",
        )
        assert record.timestamp == now
        assert record.action == OrderAction.SUBMIT
        assert record.symbol == "rb2501"
        assert record.order_id == "order_001"


class TestThrottleStatus:
    """节流状态数据类测试."""

    def test_create_status(self) -> None:
        """测试创建状态."""
        status = ThrottleStatus(
            level=ThrottleLevel.WARNING,
            count_5s=30,
            count_daily=15000,
            count_per_sec=10,
            usage_5s_pct=0.6,
            usage_daily_pct=0.75,
            is_high_freq=False,
            can_submit=True,
            message="预警",
        )
        assert status.level == ThrottleLevel.WARNING
        assert status.count_5s == 30
        assert status.can_submit is True


# ============================================================
# ComplianceThrottle 测试 - CHINA.COMPLIANCE.REPORT_FREQUENCY
# ============================================================


class TestComplianceThrottle:
    """合规节流器测试.

    V4 Scenario: CHINA.COMPLIANCE.REPORT_FREQUENCY
    军规: M17 程序化合规
    """

    RULE_ID = "CHINA.COMPLIANCE.REPORT_FREQUENCY"

    @pytest.fixture
    def throttle(self) -> ComplianceThrottle:
        """创建节流器实例."""
        return ComplianceThrottle()

    def test_initialization(self, throttle: ComplianceThrottle) -> None:
        """测试初始化."""
        assert throttle.config is not None
        assert throttle.level == ThrottleLevel.NORMAL
        assert throttle.daily_count == 0

    def test_record_order(self, throttle: ComplianceThrottle) -> None:
        """测试记录订单."""
        now = datetime.now()
        status = throttle.record_order(OrderAction.SUBMIT, "rb2501", "order_001", now)
        assert status.count_5s == 1
        assert status.count_daily == 1
        assert status.level == ThrottleLevel.NORMAL

    def test_can_submit_normal(self, throttle: ComplianceThrottle) -> None:
        """测试正常状态可提交."""
        can, msg = throttle.can_submit()
        assert can is True
        assert "正常" in msg

    def test_warning_level(self) -> None:
        """测试预警等级触发."""
        config = ThrottleConfig(limit_5s=50, warning_ratio=0.6)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交30笔 (60%触发预警)
        for i in range(30):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.WARNING

    def test_critical_level(self) -> None:
        """测试临界等级触发."""
        config = ThrottleConfig(limit_5s=50, critical_ratio=0.9)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交45笔 (90%触发临界)
        for i in range(45):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.CRITICAL

    def test_exceeded_level(self) -> None:
        """测试超限等级触发."""
        config = ThrottleConfig(limit_5s=50)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交50笔 (100%触发超限)
        for i in range(50):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.EXCEEDED
        assert status.can_submit is False

    def test_5s_window_sliding(self) -> None:
        """测试5秒窗口滑动."""
        throttle = ComplianceThrottle()

        # 6秒前的订单
        past = datetime.now() - timedelta(seconds=6)
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "old", past)

        # 当前订单
        now = datetime.now()
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "new", now)

        # 6秒前的不计入5秒窗口
        count_5s = throttle.get_count_5s(now)
        assert count_5s == 1

    def test_daily_reset(self) -> None:
        """测试日重置."""
        throttle = ComplianceThrottle()

        # 昨天的订单
        yesterday = datetime.now() - timedelta(days=1)
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "old", yesterday)

        # 今天的订单
        now = datetime.now()
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "new", now)

        # 日计数应该是1
        assert throttle.daily_count == 1

    def test_high_frequency_per_sec(self) -> None:
        """测试每秒高频判定."""
        config = ThrottleConfig(high_freq_per_sec=5)  # 降低阈值便于测试
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 同一秒内提交5笔
        for i in range(5):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        assert throttle.is_high_frequency(now) is True

    def test_high_frequency_daily(self) -> None:
        """测试日高频判定."""
        config = ThrottleConfig(limit_daily=10, high_freq_per_sec=1000)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交10笔
        for i in range(10):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        assert throttle.is_high_frequency(now) is True

    def test_reset(self, throttle: ComplianceThrottle) -> None:
        """测试重置."""
        now = datetime.now()
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "order_001", now)
        assert throttle.daily_count == 1

        throttle.reset()
        assert throttle.daily_count == 0
        assert throttle.level == ThrottleLevel.NORMAL


# ============================================================
# ProgrammaticTradingCompliance 测试 - CHINA.COMPLIANCE.RULE_CHECK
# ============================================================


class TestProgrammaticTradingCompliance:
    """程序化交易合规管理器测试.

    V4 Scenario: CHINA.COMPLIANCE.RULE_CHECK
    军规: M17 程序化合规
    """

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"

    @pytest.fixture
    def compliance(self) -> ProgrammaticTradingCompliance:
        """创建合规管理器实例."""
        return ProgrammaticTradingCompliance()

    def test_initialization(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试初始化."""
        assert compliance.throttle is not None

    def test_can_submit(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试可提交检查."""
        can, msg = compliance.can_submit("rb2501")
        assert can is True

    def test_record_order(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试记录订单."""
        now = datetime.now()
        status = compliance.record_order(OrderAction.SUBMIT, "rb2501", "order_001", now)
        assert status.count_5s == 1

    def test_get_status(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试获取状态."""
        status = compliance.get_status()
        assert isinstance(status, ThrottleStatus)
        assert status.level == ThrottleLevel.NORMAL

    def test_generate_report(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试生成报告."""
        now = datetime.now()
        compliance.record_order(OrderAction.SUBMIT, "rb2501", "order_001", now)
        compliance.record_order(OrderAction.CANCEL, "rb2501", "order_001", now)

        report = compliance.generate_report()
        assert isinstance(report, ComplianceReport)
        assert report.total_orders == 1
        assert report.total_cancels == 1

    def test_reset_daily(self, compliance: ProgrammaticTradingCompliance) -> None:
        """测试日重置."""
        now = datetime.now()
        compliance.record_order(OrderAction.SUBMIT, "rb2501", "order_001", now)
        compliance.reset_daily()

        status = compliance.get_status()
        assert status.count_daily == 0


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_throttle_config(self) -> None:
        """测试获取默认配置."""
        config = get_default_throttle_config()
        assert isinstance(config, ThrottleConfig)
        assert config.limit_5s == 50

    def test_create_compliance_throttle(self) -> None:
        """测试创建节流器."""
        throttle = create_compliance_throttle()
        assert isinstance(throttle, ComplianceThrottle)

    def test_create_compliance_manager(self) -> None:
        """测试创建管理器."""
        manager = create_compliance_manager()
        assert isinstance(manager, ProgrammaticTradingCompliance)


# ============================================================
# 军规覆盖测试
# ============================================================


class TestMilitaryRuleM17:
    """军规 M17 程序化合规测试.

    军规: 报撤单频率必须在监管阈值内
    """

    RULE_ID = "M17.PROGRAMMATIC_COMPLIANCE"

    def test_5s_limit_enforcement(self) -> None:
        """测试5秒限制强制执行."""
        config = ThrottleConfig(limit_5s=50)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交50笔
        for i in range(50):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        # 应该不允许再提交
        can, msg = throttle.can_submit(now)
        assert can is False
        assert "超限" in msg

    def test_daily_limit_enforcement(self) -> None:
        """测试日限制强制执行."""
        config = ThrottleConfig(limit_daily=100, limit_5s=1000)  # 大5秒限制
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 提交100笔
        for i in range(100):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.EXCEEDED

    def test_high_frequency_detection(self) -> None:
        """测试高频交易检测."""
        config = ThrottleConfig(high_freq_per_sec=300)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 同一秒提交300笔
        for i in range(300):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        assert throttle.is_high_frequency(now) is True


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_exact_warning_threshold(self) -> None:
        """测试精确预警阈值."""
        config = ThrottleConfig(limit_5s=50, warning_ratio=0.6)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 正好30笔 (60%)
        for i in range(30):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.WARNING

    def test_exact_critical_threshold(self) -> None:
        """测试精确临界阈值."""
        config = ThrottleConfig(limit_5s=50, critical_ratio=0.9)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 正好45笔 (90%)
        for i in range(45):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        status = throttle.get_status(now)
        assert status.level == ThrottleLevel.CRITICAL

    def test_cooldown_period(self) -> None:
        """测试冷却期."""
        config = ThrottleConfig(limit_5s=5, cooldown_seconds=60)
        throttle = ComplianceThrottle(config)

        now = datetime.now()
        # 触发超限
        for i in range(5):
            throttle.record_order(OrderAction.SUBMIT, "rb2501", f"order_{i}", now)

        # 冷却期内不能提交
        can, msg = throttle.can_submit(now)
        assert can is False
        assert "超限" in msg or "冷却" in msg

    def test_empty_records(self) -> None:
        """测试空记录."""
        throttle = ComplianceThrottle()
        status = throttle.get_status()
        assert status.count_5s == 0
        assert status.count_daily == 0
        assert status.level == ThrottleLevel.NORMAL

    def test_multiple_symbols(self) -> None:
        """测试多合约."""
        throttle = ComplianceThrottle()

        now = datetime.now()
        throttle.record_order(OrderAction.SUBMIT, "rb2501", "order_1", now)
        throttle.record_order(OrderAction.SUBMIT, "hc2501", "order_2", now)
        throttle.record_order(OrderAction.SUBMIT, "i2501", "order_3", now)

        status = throttle.get_status(now)
        assert status.count_5s == 3

    def test_mixed_actions(self) -> None:
        """测试混合操作."""
        compliance = ProgrammaticTradingCompliance()

        now = datetime.now()
        compliance.record_order(OrderAction.SUBMIT, "rb2501", "order_1", now)
        compliance.record_order(OrderAction.CANCEL, "rb2501", "order_1", now)
        compliance.record_order(OrderAction.AMEND, "hc2501", "order_2", now)

        report = compliance.generate_report()
        assert report.total_orders == 1
        assert report.total_cancels == 1
        assert report.total_amends == 1
