"""
中国期货合规规则模块测试 (军规级 v4.0).

V4PRO Test Suite - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §21 程序化交易合规
V4 Scenarios:
- CHINA.COMPLIANCE.RULE_CHECK: 合规规则检查

军规覆盖测试:
- M12: 双重确认 - 大额订单需人工或二次确认
- M13: 涨跌停感知 - 订单价格必须检查涨跌停板
- M15: 夜盘跨日处理 - 夜盘交易日归属必须正确
- M17: 程序化合规 - 报撤单频率必须在监管阈值内
"""

from datetime import datetime, time

import pytest

from src.compliance.china_futures_rules import (
    ChinaFuturesComplianceChecker,
    ComplianceCheckResult,
    ComplianceConfig,
    ComplianceViolation,
    MarketContext,
    OrderInfo,
    SeverityLevel,
    ViolationType,
    check_order_compliance,
    create_compliance_checker,
    get_default_compliance_config,
)


# ============================================================
# 测试: 枚举类型
# ============================================================


class TestViolationTypeEnum:
    """ViolationType枚举测试."""

    def test_all_violation_types_defined(self) -> None:
        """测试所有违规类型已定义."""
        expected_types = [
            "PRICE_OUT_OF_LIMIT",
            "VOLUME_EXCEEDS_LIMIT",
            "POSITION_EXCEEDS_LIMIT",
            "FORBIDDEN_PRODUCT",
            "TRADING_TIME_INVALID",
            "LARGE_ORDER_NO_CONFIRM",
            "MARGIN_INSUFFICIENT",
            "NIGHT_SESSION_DISABLED",
            "DELIVERY_MONTH_RESTRICTED",
            "ACCOUNT_RESTRICTED",
        ]
        for type_name in expected_types:
            assert hasattr(ViolationType, type_name)

    def test_violation_type_values(self) -> None:
        """测试违规类型值."""
        assert ViolationType.PRICE_OUT_OF_LIMIT.value == "PRICE_OUT_OF_LIMIT"
        assert ViolationType.MARGIN_INSUFFICIENT.value == "MARGIN_INSUFFICIENT"


class TestSeverityLevelEnum:
    """SeverityLevel枚举测试."""

    def test_all_severity_levels_defined(self) -> None:
        """测试所有严重程度已定义."""
        expected_levels = ["FATAL", "SEVERE", "MAJOR", "MINOR", "INFO"]
        for level in expected_levels:
            assert hasattr(SeverityLevel, level)

    def test_severity_order(self) -> None:
        """测试严重程度含义."""
        # FATAL > SEVERE > MAJOR > MINOR > INFO
        assert SeverityLevel.FATAL.value == "FATAL"
        assert SeverityLevel.INFO.value == "INFO"


# ============================================================
# 测试: 数据类
# ============================================================


class TestComplianceViolation:
    """ComplianceViolation测试."""

    def test_violation_creation(self) -> None:
        """测试违规记录创建."""
        violation = ComplianceViolation(
            violation_type=ViolationType.PRICE_OUT_OF_LIMIT,
            severity=SeverityLevel.FATAL,
            message="价格超出涨停",
            rule_id="CHINA.COMPLIANCE.LIMIT_PRICE",
            military_rule="M13",
        )
        assert violation.violation_type == ViolationType.PRICE_OUT_OF_LIMIT
        assert violation.severity == SeverityLevel.FATAL
        assert "涨停" in violation.message
        assert violation.military_rule == "M13"

    def test_violation_frozen(self) -> None:
        """测试违规记录不可变."""
        violation = ComplianceViolation(
            violation_type=ViolationType.FORBIDDEN_PRODUCT,
            severity=SeverityLevel.FATAL,
            message="禁止品种",
            rule_id="TEST",
        )
        with pytest.raises(AttributeError):
            violation.message = "新消息"  # type: ignore[misc]


class TestComplianceConfig:
    """ComplianceConfig测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = ComplianceConfig()
        assert config.max_order_volume == 1000
        assert config.large_order_threshold == 100
        assert config.position_limit_ratio == 0.8
        assert config.allow_night_session is True
        assert config.require_large_order_confirm is True

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = ComplianceConfig(
            max_order_volume=500,
            forbidden_products=("ic", "ih"),
        )
        assert config.max_order_volume == 500
        assert "ic" in config.forbidden_products
        assert "ih" in config.forbidden_products

    def test_config_frozen(self) -> None:
        """测试配置不可变."""
        config = ComplianceConfig()
        with pytest.raises(AttributeError):
            config.max_order_volume = 2000  # type: ignore[misc]


class TestOrderInfo:
    """OrderInfo测试."""

    def test_order_info_creation(self) -> None:
        """测试订单信息创建."""
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        assert order.symbol == "rb2501"
        assert order.direction == "BUY"
        assert order.volume == 10
        assert order.confirmed is False

    def test_order_with_confirm(self) -> None:
        """测试已确认订单."""
        order = OrderInfo(
            symbol="IF2501",
            direction="SELL",
            offset="CLOSE",
            price=4000.0,
            volume=200,
            confirmed=True,
        )
        assert order.confirmed is True


class TestMarketContext:
    """MarketContext测试."""

    def test_default_context(self) -> None:
        """测试默认上下文."""
        context = MarketContext()
        assert context.last_price == 0.0
        assert context.is_trading_time is True
        assert context.is_night_session is False

    def test_context_with_limits(self) -> None:
        """测试带涨跌停的上下文."""
        context = MarketContext(
            last_settle=3450.0,
            upper_limit=3795.0,
            lower_limit=3105.0,
            position_limit=500,
        )
        assert context.upper_limit == 3795.0
        assert context.lower_limit == 3105.0


class TestComplianceCheckResult:
    """ComplianceCheckResult测试."""

    def test_compliant_result(self) -> None:
        """测试合规结果."""
        result = ComplianceCheckResult(is_compliant=True)
        assert result.is_compliant is True
        assert len(result.violations) == 0
        assert result.has_blocking_violations() is False

    def test_non_compliant_result(self) -> None:
        """测试违规结果."""
        violations = [
            ComplianceViolation(
                violation_type=ViolationType.PRICE_OUT_OF_LIMIT,
                severity=SeverityLevel.FATAL,
                message="超涨停",
                rule_id="TEST",
            ),
        ]
        result = ComplianceCheckResult(
            is_compliant=False,
            violations=violations,
        )
        assert result.is_compliant is False
        assert len(result.violations) == 1
        assert result.has_blocking_violations() is True

    def test_get_fatal_violations(self) -> None:
        """测试获取致命违规."""
        violations = [
            ComplianceViolation(
                violation_type=ViolationType.PRICE_OUT_OF_LIMIT,
                severity=SeverityLevel.FATAL,
                message="致命",
                rule_id="T1",
            ),
            ComplianceViolation(
                violation_type=ViolationType.VOLUME_EXCEEDS_LIMIT,
                severity=SeverityLevel.SEVERE,
                message="严重",
                rule_id="T2",
            ),
            ComplianceViolation(
                violation_type=ViolationType.LARGE_ORDER_NO_CONFIRM,
                severity=SeverityLevel.MAJOR,
                message="重大",
                rule_id="T3",
            ),
        ]
        result = ComplianceCheckResult(is_compliant=False, violations=violations)
        fatal = result.get_fatal_violations()
        severe = result.get_severe_violations()
        assert len(fatal) == 1
        assert len(severe) == 1
        assert fatal[0].severity == SeverityLevel.FATAL


# ============================================================
# 测试: 合规检查器 - 基础功能
# ============================================================


class TestChinaFuturesComplianceCheckerBasic:
    """ChinaFuturesComplianceChecker基础测试."""

    def test_checker_creation(self) -> None:
        """测试检查器创建."""
        checker = ChinaFuturesComplianceChecker()
        assert checker.config is not None
        assert checker.check_count == 0
        assert checker.violation_count == 0

    def test_checker_with_custom_config(self) -> None:
        """测试带自定义配置的检查器."""
        config = ComplianceConfig(max_order_volume=500)
        checker = ChinaFuturesComplianceChecker(config)
        assert checker.config.max_order_volume == 500

    def test_checker_version(self) -> None:
        """测试检查器版本."""
        checker = ChinaFuturesComplianceChecker()
        assert checker.VERSION == "4.0"

    def test_statistics(self) -> None:
        """测试统计信息."""
        checker = ChinaFuturesComplianceChecker()
        stats = checker.get_statistics()
        assert "check_count" in stats
        assert "violation_count" in stats
        assert "violation_rate" in stats
        assert stats["checker_version"] == "4.0"

    def test_reset_statistics(self) -> None:
        """测试重置统计."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        checker.check_order(order)
        assert checker.check_count == 1
        checker.reset_statistics()
        assert checker.check_count == 0


# ============================================================
# 测试: 合规检查器 - 价格检查 (军规 M13)
# ============================================================


class TestPriceComplianceCheck:
    """价格合规检查测试 (军规 M13)."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"

    def test_price_within_limit(self) -> None:
        """测试价格在涨跌停范围内."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(
            upper_limit=3795.0,
            lower_limit=3105.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        # 无价格违规
        price_violations = [
            v for v in result.violations if v.violation_type == ViolationType.PRICE_OUT_OF_LIMIT
        ]
        assert len(price_violations) == 0

    def test_price_exceeds_upper_limit(self) -> None:
        """测试价格超过涨停价."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=4000.0,  # 超过涨停价3795
            volume=10,
        )
        context = MarketContext(
            upper_limit=3795.0,
            lower_limit=3105.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        assert result.is_compliant is False
        price_violations = [
            v for v in result.violations if v.violation_type == ViolationType.PRICE_OUT_OF_LIMIT
        ]
        assert len(price_violations) == 1
        assert "涨停" in price_violations[0].message

    def test_price_below_lower_limit(self) -> None:
        """测试价格低于跌停价."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="SELL",
            offset="OPEN",
            price=3000.0,  # 低于跌停价3105
            volume=10,
        )
        context = MarketContext(
            upper_limit=3795.0,
            lower_limit=3105.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        assert result.is_compliant is False
        price_violations = [
            v for v in result.violations if v.violation_type == ViolationType.PRICE_OUT_OF_LIMIT
        ]
        assert len(price_violations) == 1
        assert "跌停" in price_violations[0].message

    def test_check_price_limit_method(self) -> None:
        """测试check_price_limit方法."""
        checker = ChinaFuturesComplianceChecker()

        # 正常价格
        ok, msg = checker.check_price_limit(3500.0, 3795.0, 3105.0)
        assert ok is True

        # 超涨停
        ok, msg = checker.check_price_limit(4000.0, 3795.0, 3105.0)
        assert ok is False
        assert "涨停" in msg

        # 超跌停
        ok, msg = checker.check_price_limit(3000.0, 3795.0, 3105.0)
        assert ok is False
        assert "跌停" in msg


# ============================================================
# 测试: 合规检查器 - 数量检查 (军规 M12)
# ============================================================


class TestVolumeComplianceCheck:
    """数量合规检查测试 (军规 M12)."""

    def test_volume_within_limit(self) -> None:
        """测试数量在限制范围内."""
        config = ComplianceConfig(max_order_volume=100)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=50,  # 小于限制100
        )
        result = checker.check_order(order)
        volume_violations = [
            v for v in result.violations if v.violation_type == ViolationType.VOLUME_EXCEEDS_LIMIT
        ]
        assert len(volume_violations) == 0

    def test_volume_exceeds_limit(self) -> None:
        """测试数量超出限制."""
        config = ComplianceConfig(max_order_volume=100)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=150,  # 超过限制100
        )
        result = checker.check_order(order)
        volume_violations = [
            v for v in result.violations if v.violation_type == ViolationType.VOLUME_EXCEEDS_LIMIT
        ]
        assert len(volume_violations) == 1
        assert volume_violations[0].severity == SeverityLevel.SEVERE

    def test_check_volume_limit_method(self) -> None:
        """测试check_volume_limit方法."""
        config = ComplianceConfig(max_order_volume=100)
        checker = ChinaFuturesComplianceChecker(config)

        # 正常数量
        ok, msg = checker.check_volume_limit(50)
        assert ok is True

        # 超限数量
        ok, msg = checker.check_volume_limit(150)
        assert ok is False
        assert "超过" in msg

        # 零数量
        ok, msg = checker.check_volume_limit(0)
        assert ok is False
        assert "大于0" in msg


# ============================================================
# 测试: 合规检查器 - 大额订单确认 (军规 M12)
# ============================================================


class TestLargeOrderConfirm:
    """大额订单确认测试 (军规 M12)."""

    def test_small_order_no_confirm_needed(self) -> None:
        """测试小额订单无需确认."""
        config = ComplianceConfig(
            large_order_threshold=100,
            require_large_order_confirm=True,
        )
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=50,  # 小于阈值100
            confirmed=False,
        )
        result = checker.check_order(order)
        large_order_violations = [
            v for v in result.violations if v.violation_type == ViolationType.LARGE_ORDER_NO_CONFIRM
        ]
        assert len(large_order_violations) == 0

    def test_large_order_needs_confirm(self) -> None:
        """测试大额订单需要确认."""
        config = ComplianceConfig(
            large_order_threshold=100,
            require_large_order_confirm=True,
        )
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=150,  # 超过阈值100
            confirmed=False,  # 未确认
        )
        result = checker.check_order(order)
        large_order_violations = [
            v for v in result.violations if v.violation_type == ViolationType.LARGE_ORDER_NO_CONFIRM
        ]
        assert len(large_order_violations) == 1
        assert large_order_violations[0].military_rule == "M12"

    def test_large_order_confirmed(self) -> None:
        """测试已确认的大额订单."""
        config = ComplianceConfig(
            large_order_threshold=100,
            require_large_order_confirm=True,
        )
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=150,
            confirmed=True,  # 已确认
        )
        result = checker.check_order(order)
        large_order_violations = [
            v for v in result.violations if v.violation_type == ViolationType.LARGE_ORDER_NO_CONFIRM
        ]
        assert len(large_order_violations) == 0

    def test_is_large_order_method(self) -> None:
        """测试is_large_order方法."""
        config = ComplianceConfig(large_order_threshold=100)
        checker = ChinaFuturesComplianceChecker(config)
        assert checker.is_large_order(50) is False
        assert checker.is_large_order(100) is True
        assert checker.is_large_order(150) is True


# ============================================================
# 测试: 合规检查器 - 持仓限额检查 (军规 M16)
# ============================================================


class TestPositionLimitCheck:
    """持仓限额检查测试 (军规 M16)."""

    def test_position_within_limit(self) -> None:
        """测试持仓在限额内."""
        config = ComplianceConfig(position_limit_ratio=0.8)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=100,
        )
        context = MarketContext(
            position_limit=500,  # 限额500, 80%=400
            current_position=200,  # 当前200, 开仓100后=300 < 400
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        position_violations = [
            v for v in result.violations if v.violation_type == ViolationType.POSITION_EXCEEDS_LIMIT
        ]
        assert len(position_violations) == 0

    def test_position_exceeds_limit(self) -> None:
        """测试持仓超出限额."""
        config = ComplianceConfig(position_limit_ratio=0.8)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=300,
        )
        context = MarketContext(
            position_limit=500,  # 限额500, 80%=400
            current_position=200,  # 当前200, 开仓300后=500 > 400
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        position_violations = [
            v for v in result.violations if v.violation_type == ViolationType.POSITION_EXCEEDS_LIMIT
        ]
        assert len(position_violations) == 1
        assert "超过限额" in position_violations[0].message

    def test_close_order_no_position_check(self) -> None:
        """测试平仓订单不检查持仓限额."""
        config = ComplianceConfig(position_limit_ratio=0.8)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="SELL",
            offset="CLOSE",  # 平仓
            price=3500.0,
            volume=300,
        )
        context = MarketContext(
            position_limit=500,
            current_position=200,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        position_violations = [
            v for v in result.violations if v.violation_type == ViolationType.POSITION_EXCEEDS_LIMIT
        ]
        assert len(position_violations) == 0

    def test_check_position_limit_method(self) -> None:
        """测试check_position_limit方法."""
        config = ComplianceConfig(position_limit_ratio=0.8)
        checker = ChinaFuturesComplianceChecker(config)

        # 在限额内
        ok, msg = checker.check_position_limit(200, 100, 500)
        assert ok is True

        # 超出限额
        ok, msg = checker.check_position_limit(200, 300, 500)
        assert ok is False
        assert "超过" in msg


# ============================================================
# 测试: 合规检查器 - 禁止品种检查 (军规 M17)
# ============================================================


class TestForbiddenProductCheck:
    """禁止品种检查测试 (军规 M17)."""

    def test_allowed_product(self) -> None:
        """测试允许的品种."""
        config = ComplianceConfig(forbidden_products=("ic", "ih"))
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",  # rb不在禁止列表
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        result = checker.check_order(order)
        forbidden_violations = [
            v for v in result.violations if v.violation_type == ViolationType.FORBIDDEN_PRODUCT
        ]
        assert len(forbidden_violations) == 0

    def test_forbidden_product(self) -> None:
        """测试禁止的品种."""
        config = ComplianceConfig(forbidden_products=("ic", "ih"))
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="IC2501",  # ic在禁止列表
            direction="BUY",
            offset="OPEN",
            price=5000.0,
            volume=10,
        )
        result = checker.check_order(order)
        forbidden_violations = [
            v for v in result.violations if v.violation_type == ViolationType.FORBIDDEN_PRODUCT
        ]
        assert len(forbidden_violations) == 1
        assert forbidden_violations[0].severity == SeverityLevel.FATAL

    def test_is_forbidden_product_method(self) -> None:
        """测试is_forbidden_product方法."""
        config = ComplianceConfig(forbidden_products=("ic", "ih"))
        checker = ChinaFuturesComplianceChecker(config)
        assert checker.is_forbidden_product("rb") is False
        assert checker.is_forbidden_product("ic") is True
        assert checker.is_forbidden_product("IC") is True  # 大小写不敏感


# ============================================================
# 测试: 合规检查器 - 交易时间检查 (军规 M15)
# ============================================================


class TestTradingTimeCheck:
    """交易时间检查测试 (军规 M15)."""

    def test_trading_time_valid(self) -> None:
        """测试有效交易时间."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(is_trading_time=True)
        result = checker.check_order(order, context)
        time_violations = [
            v for v in result.violations if v.violation_type == ViolationType.TRADING_TIME_INVALID
        ]
        assert len(time_violations) == 0

    def test_trading_time_invalid(self) -> None:
        """测试无效交易时间."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(is_trading_time=False)
        result = checker.check_order(order, context)
        time_violations = [
            v for v in result.violations if v.violation_type == ViolationType.TRADING_TIME_INVALID
        ]
        assert len(time_violations) == 1
        assert time_violations[0].military_rule == "M15"

    def test_check_trading_time_method_day_session(self) -> None:
        """测试check_trading_time方法-日盘."""
        checker = ChinaFuturesComplianceChecker()

        # 第一节 09:30
        ts = datetime(2025, 1, 6, 9, 30, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is True
        assert "日盘" in msg

        # 第二节 10:45
        ts = datetime(2025, 1, 6, 10, 45, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is True

        # 第三节 14:30
        ts = datetime(2025, 1, 6, 14, 30, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is True

    def test_check_trading_time_method_night_session(self) -> None:
        """测试check_trading_time方法-夜盘."""
        config = ComplianceConfig(allow_night_session=True)
        checker = ChinaFuturesComplianceChecker(config)

        # 夜盘 21:30
        ts = datetime(2025, 1, 6, 21, 30, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is True
        assert "夜盘" in msg

        # 凌晨 01:30
        ts = datetime(2025, 1, 7, 1, 30, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is True

    def test_check_trading_time_method_closed(self) -> None:
        """测试check_trading_time方法-收盘."""
        checker = ChinaFuturesComplianceChecker()

        # 收盘后 16:00
        ts = datetime(2025, 1, 6, 16, 0, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is False
        assert "非交易时间" in msg

        # 午休 12:00
        ts = datetime(2025, 1, 6, 12, 0, 0)
        ok, msg = checker.check_trading_time(ts)
        assert ok is False

    def test_night_session_disabled(self) -> None:
        """测试夜盘未开启."""
        config = ComplianceConfig(allow_night_session=False)
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(
            is_trading_time=True,
            is_night_session=True,
        )
        result = checker.check_order(order, context)
        night_violations = [
            v for v in result.violations if v.violation_type == ViolationType.NIGHT_SESSION_DISABLED
        ]
        assert len(night_violations) == 1


# ============================================================
# 测试: 合规检查器 - 保证金检查 (军规 M16)
# ============================================================


class TestMarginCheck:
    """保证金检查测试 (军规 M16)."""

    def test_margin_sufficient(self) -> None:
        """测试保证金充足."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(
            margin_available=100000.0,
            margin_required=50000.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        margin_violations = [
            v for v in result.violations if v.violation_type == ViolationType.MARGIN_INSUFFICIENT
        ]
        assert len(margin_violations) == 0

    def test_margin_insufficient(self) -> None:
        """测试保证金不足."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(
            margin_available=30000.0,
            margin_required=50000.0,  # 需要 > 可用
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        margin_violations = [
            v for v in result.violations if v.violation_type == ViolationType.MARGIN_INSUFFICIENT
        ]
        assert len(margin_violations) == 1
        assert margin_violations[0].severity == SeverityLevel.FATAL


# ============================================================
# 测试: 合规检查器 - 综合场景
# ============================================================


class TestComprehensiveScenarios:
    """综合场景测试."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"

    def test_fully_compliant_order(self) -> None:
        """测试完全合规的订单 - RULE_ID: CHINA.COMPLIANCE.RULE_CHECK."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
            confirmed=True,
        )
        context = MarketContext(
            last_settle=3450.0,
            upper_limit=3795.0,
            lower_limit=3105.0,
            position_limit=500,
            current_position=100,
            margin_available=100000.0,
            margin_required=35000.0,
            is_trading_time=True,
            is_night_session=False,
        )
        result = checker.check_order(order, context)
        assert result.is_compliant is True
        assert len(result.violations) == 0

    def test_multiple_violations(self) -> None:
        """测试多重违规."""
        config = ComplianceConfig(
            max_order_volume=100,
            forbidden_products=("rb",),
            require_large_order_confirm=True,
        )
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="rb2501",  # 禁止品种
            direction="BUY",
            offset="OPEN",
            price=4000.0,  # 超涨停
            volume=150,  # 超数量 + 大额未确认
        )
        context = MarketContext(
            upper_limit=3795.0,
            lower_limit=3105.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        assert result.is_compliant is False
        # 应有多个违规: 禁止品种, 超涨停, 超数量, 大额未确认
        assert len(result.violations) >= 3

    def test_violation_statistics(self) -> None:
        """测试违规统计."""
        checker = ChinaFuturesComplianceChecker()

        # 合规订单
        order1 = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        checker.check_order(order1)

        # 违规订单
        order2 = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=4000.0,  # 超涨停
            volume=10,
        )
        context = MarketContext(upper_limit=3795.0)
        checker.check_order(order2, context)

        stats = checker.get_statistics()
        assert stats["check_count"] == 2
        assert stats["violation_count"] >= 1


# ============================================================
# 测试: 便捷函数
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_compliance_config(self) -> None:
        """测试get_default_compliance_config."""
        config = get_default_compliance_config()
        assert config.max_order_volume == 1000
        assert config.large_order_threshold == 100

    def test_create_compliance_checker(self) -> None:
        """测试create_compliance_checker."""
        checker = create_compliance_checker()
        assert checker is not None
        assert checker.config is not None

        custom_config = ComplianceConfig(max_order_volume=500)
        checker2 = create_compliance_checker(custom_config)
        assert checker2.config.max_order_volume == 500

    def test_check_order_compliance_function(self) -> None:
        """测试check_order_compliance便捷函数."""
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        result = check_order_compliance(order)
        assert isinstance(result, ComplianceCheckResult)


# ============================================================
# 测试: 军规覆盖
# ============================================================


class TestMilitaryRuleM12:
    """军规M12测试 - 双重确认."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"
    MILITARY_RULE = "M12"

    def test_large_order_confirm_required(self) -> None:
        """测试大额订单需要双重确认 - M12."""
        config = ComplianceConfig(
            large_order_threshold=100,
            require_large_order_confirm=True,
        )
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="IF2501",
            direction="BUY",
            offset="OPEN",
            price=4000.0,
            volume=150,
            confirmed=False,
        )
        result = checker.check_order(order)
        violations = [v for v in result.violations if v.military_rule == "M12"]
        assert len(violations) >= 1


class TestMilitaryRuleM13:
    """军规M13测试 - 涨跌停感知."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"
    MILITARY_RULE = "M13"

    def test_price_limit_check(self) -> None:
        """测试涨跌停检查 - M13."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=4000.0,  # 超涨停
            volume=10,
        )
        context = MarketContext(upper_limit=3795.0, lower_limit=3105.0)
        result = checker.check_order(order, context)
        violations = [v for v in result.violations if v.military_rule == "M13"]
        assert len(violations) == 1


class TestMilitaryRuleM15:
    """军规M15测试 - 夜盘跨日处理."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"
    MILITARY_RULE = "M15"

    def test_trading_time_check(self) -> None:
        """测试交易时间检查 - M15."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(is_trading_time=False)
        result = checker.check_order(order, context)
        violations = [v for v in result.violations if v.military_rule == "M15"]
        assert len(violations) >= 1


class TestMilitaryRuleM16:
    """军规M16测试 - 保证金实时监控."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"
    MILITARY_RULE = "M16"

    def test_margin_check(self) -> None:
        """测试保证金检查 - M16."""
        checker = ChinaFuturesComplianceChecker()
        order = OrderInfo(
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            price=3500.0,
            volume=10,
        )
        context = MarketContext(
            margin_available=10000.0,
            margin_required=50000.0,
            is_trading_time=True,
        )
        result = checker.check_order(order, context)
        violations = [v for v in result.violations if v.military_rule == "M16"]
        assert len(violations) >= 1


class TestMilitaryRuleM17:
    """军规M17测试 - 程序化合规."""

    RULE_ID = "CHINA.COMPLIANCE.RULE_CHECK"
    MILITARY_RULE = "M17"

    def test_forbidden_product_check(self) -> None:
        """测试禁止品种检查 - M17."""
        config = ComplianceConfig(forbidden_products=("ic",))
        checker = ChinaFuturesComplianceChecker(config)
        order = OrderInfo(
            symbol="IC2501",
            direction="BUY",
            offset="OPEN",
            price=5000.0,
            volume=10,
        )
        result = checker.check_order(order)
        violations = [v for v in result.violations if v.military_rule == "M17"]
        assert len(violations) >= 1
