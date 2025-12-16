"""
涨跌停保护模块测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 Scenarios: CHINA.LIMIT.PRICE_CHECK, CHINA.LIMIT.ORDER_REJECT

军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板
"""

from __future__ import annotations

import pytest

from src.execution.protection.limit_price import (
    PRODUCT_LIMIT_PCT,
    LimitPriceCheckOutput,
    LimitPriceCheckResult,
    LimitPriceConfig,
    LimitPriceGuard,
    LimitPrices,
    LimitStatus,
    check_limit_price,
    get_default_guard,
    get_limit_prices,
)


class TestLimitPriceCheckResultEnum:
    """涨跌停检查结果枚举测试."""

    def test_all_values(self) -> None:
        """测试所有枚举值."""
        assert LimitPriceCheckResult.PASS.value == "PASS"
        assert LimitPriceCheckResult.ABOVE_LIMIT_UP.value == "ABOVE_LIMIT_UP"
        assert LimitPriceCheckResult.BELOW_LIMIT_DOWN.value == "BELOW_LIMIT_DOWN"
        assert LimitPriceCheckResult.INVALID_PRICE.value == "INVALID_PRICE"
        assert LimitPriceCheckResult.INVALID_SETTLE.value == "INVALID_SETTLE"
        assert LimitPriceCheckResult.AT_LIMIT_UP.value == "AT_LIMIT_UP"
        assert LimitPriceCheckResult.AT_LIMIT_DOWN.value == "AT_LIMIT_DOWN"


class TestLimitStatusEnum:
    """涨跌停状态枚举测试."""

    def test_all_values(self) -> None:
        """测试所有枚举值."""
        assert LimitStatus.NORMAL.value == "NORMAL"
        assert LimitStatus.AT_LIMIT_UP.value == "AT_LIMIT_UP"
        assert LimitStatus.AT_LIMIT_DOWN.value == "AT_LIMIT_DOWN"
        assert LimitStatus.NEAR_LIMIT_UP.value == "NEAR_LIMIT_UP"
        assert LimitStatus.NEAR_LIMIT_DOWN.value == "NEAR_LIMIT_DOWN"


class TestLimitPriceConfig:
    """涨跌停配置测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = LimitPriceConfig()
        assert config.default_limit_pct == 0.05
        assert config.near_limit_threshold == 0.01
        assert config.allow_limit_price_order is True
        assert config.tick_size == 1.0

    def test_custom_values(self) -> None:
        """测试自定义值."""
        config = LimitPriceConfig(
            default_limit_pct=0.10,
            near_limit_threshold=0.02,
            allow_limit_price_order=False,
            tick_size=0.5,
        )
        assert config.default_limit_pct == 0.10
        assert config.near_limit_threshold == 0.02
        assert config.allow_limit_price_order is False
        assert config.tick_size == 0.5

    def test_frozen_dataclass(self) -> None:
        """测试frozen配置不可变."""
        config = LimitPriceConfig()
        with pytest.raises(AttributeError):
            config.default_limit_pct = 0.20  # type: ignore[misc]


class TestLimitPrices:
    """涨跌停价格测试."""

    def test_basic_creation(self) -> None:
        """测试基本创建."""
        prices = LimitPrices(
            limit_up=4200.0,
            limit_down=3800.0,
            last_settle=4000.0,
            limit_pct=0.05,
            tick_size=1.0,
        )
        assert prices.limit_up == 4200.0
        assert prices.limit_down == 3800.0
        assert prices.last_settle == 4000.0
        assert prices.limit_pct == 0.05

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        prices = LimitPrices(
            limit_up=4200.0,
            limit_down=3800.0,
            last_settle=4000.0,
            limit_pct=0.05,
        )
        result = prices.to_dict()
        assert result["limit_up"] == 4200.0
        assert result["limit_down"] == 3800.0
        assert result["last_settle"] == 4000.0
        assert result["limit_pct"] == 0.05


class TestLimitPriceCheckOutput:
    """涨跌停检查输出测试."""

    def test_passed_property(self) -> None:
        """测试passed属性."""
        output_pass = LimitPriceCheckOutput(result=LimitPriceCheckResult.PASS)
        assert output_pass.passed is True

        output_reject = LimitPriceCheckOutput(result=LimitPriceCheckResult.ABOVE_LIMIT_UP)
        assert output_reject.passed is False

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        output = LimitPriceCheckOutput(
            result=LimitPriceCheckResult.PASS,
            symbol="rb2501",
            order_price=4100.0,
            limit_up=4200.0,
            limit_down=3800.0,
            last_settle=4000.0,
            limit_pct=0.05,
            message="涨跌停检查通过",
        )
        result = output.to_dict()
        assert result["result"] == "PASS"
        assert result["symbol"] == "rb2501"
        assert result["order_price"] == 4100.0
        assert result["passed"] is True


class TestProductLimitPct:
    """品种涨跌停幅度配置测试."""

    def test_index_futures(self) -> None:
        """测试股指期货涨跌停幅度 (±10%)."""
        assert PRODUCT_LIMIT_PCT["if"] == 0.10
        assert PRODUCT_LIMIT_PCT["ih"] == 0.10
        assert PRODUCT_LIMIT_PCT["ic"] == 0.10
        assert PRODUCT_LIMIT_PCT["im"] == 0.10

    def test_bond_futures(self) -> None:
        """测试国债期货涨跌停幅度 (±2%)."""
        assert PRODUCT_LIMIT_PCT["t"] == 0.02
        assert PRODUCT_LIMIT_PCT["tf"] == 0.02
        assert PRODUCT_LIMIT_PCT["ts"] == 0.02

    def test_precious_metals(self) -> None:
        """测试贵金属涨跌停幅度 (6%)."""
        assert PRODUCT_LIMIT_PCT["au"] == 0.06
        assert PRODUCT_LIMIT_PCT["ag"] == 0.06

    def test_black_series(self) -> None:
        """测试黑色系涨跌停幅度 (4%)."""
        assert PRODUCT_LIMIT_PCT["rb"] == 0.04
        assert PRODUCT_LIMIT_PCT["hc"] == 0.04
        assert PRODUCT_LIMIT_PCT["i"] == 0.04

    def test_agricultural(self) -> None:
        """测试农产品涨跌停幅度 (4%)."""
        assert PRODUCT_LIMIT_PCT["c"] == 0.04
        assert PRODUCT_LIMIT_PCT["m"] == 0.04
        assert PRODUCT_LIMIT_PCT["cf"] == 0.04


class TestLimitPriceGuardInit:
    """LimitPriceGuard初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        guard = LimitPriceGuard()
        assert guard.config.default_limit_pct == 0.05
        assert guard.check_count == 0
        assert guard.reject_count == 0
        assert guard.limit_hit_count == 0

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = LimitPriceConfig(default_limit_pct=0.10)
        guard = LimitPriceGuard(config=config)
        assert guard.config.default_limit_pct == 0.10

    def test_custom_product_limits(self) -> None:
        """测试自定义品种限制."""
        custom_limits = {"rb": 0.08, "cu": 0.07}
        guard = LimitPriceGuard(product_limits=custom_limits)
        assert guard.get_limit_pct("rb2501") == 0.08
        assert guard.get_limit_pct("cu2501") == 0.07


class TestLimitPriceGuardGetLimitPct:
    """获取品种涨跌停幅度测试."""

    def test_known_product(self) -> None:
        """测试已知品种."""
        guard = LimitPriceGuard()
        # 股指期货 10%
        assert guard.get_limit_pct("IF2501") == 0.10
        # 国债期货 2%
        assert guard.get_limit_pct("T2503") == 0.02
        # 螺纹钢 4%
        assert guard.get_limit_pct("rb2501") == 0.04
        # 黄金 6%
        assert guard.get_limit_pct("au2502") == 0.06

    def test_unknown_product_uses_default(self) -> None:
        """测试未知品种使用默认值."""
        guard = LimitPriceGuard()
        # 未知品种使用默认5%
        assert guard.get_limit_pct("xyz2501") == 0.05

    def test_case_insensitive(self) -> None:
        """测试大小写不敏感."""
        guard = LimitPriceGuard()
        assert guard.get_limit_pct("IF2501") == 0.10
        assert guard.get_limit_pct("if2501") == 0.10
        assert guard.get_limit_pct("iF2501") == 0.10


class TestLimitPriceGuardGetLimitPrices:
    """计算涨跌停价格测试."""

    def test_basic_calculation(self) -> None:
        """测试基本计算."""
        guard = LimitPriceGuard()
        # 昨结算4000，涨跌停5%
        limits = guard.get_limit_prices(4000.0, limit_pct=0.05, tick_size=1.0)
        assert limits.limit_up == 4200.0
        assert limits.limit_down == 3800.0
        assert limits.last_settle == 4000.0
        assert limits.limit_pct == 0.05

    def test_tick_size_rounding(self) -> None:
        """测试tick_size修正."""
        guard = LimitPriceGuard()
        # 昨结算4123，涨跌停5%，tick_size=10
        # 理论涨停 4123 * 1.05 = 4329.15 -> 向下取整到4320
        # 理论跌停 4123 * 0.95 = 3916.85 -> 向上取整到3920
        limits = guard.get_limit_prices(4123.0, limit_pct=0.05, tick_size=10.0)
        assert limits.limit_up == 4320.0
        assert limits.limit_down == 3920.0

    def test_symbol_based_limit_pct(self) -> None:
        """测试基于品种的涨跌停幅度."""
        guard = LimitPriceGuard()
        # 股指期货IF 10%
        limits = guard.get_limit_prices(4000.0, symbol="IF2501", tick_size=0.2)
        assert limits.limit_pct == 0.10
        assert limits.limit_up == 4400.0
        assert limits.limit_down == 3600.0


class TestLimitPriceGuardCheckOrderPrice:
    """检查订单价格测试 (军规 M13).

    RULE_ID: CHINA.LIMIT.PRICE_CHECK, CHINA.LIMIT.ORDER_REJECT
    """

    def test_pass_within_range(self) -> None:
        """测试在范围内通过.

        RULE_ID: CHINA.LIMIT.PRICE_CHECK
        """
        guard = LimitPriceGuard()
        # 昨结算4000，涨跌停5% => 涨停4200, 跌停3800
        result = guard.check_order_price(
            order_price=4100.0,
            last_settle=4000.0,
            limit_pct=0.05,
            symbol="rb2501",
        )
        assert result.passed is True
        assert result.result == LimitPriceCheckResult.PASS
        assert result.message == "涨跌停检查通过"

    def test_reject_above_limit_up(self) -> None:
        """测试超过涨停价拒绝.

        RULE_ID: CHINA.LIMIT.ORDER_REJECT
        """
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=4300.0,  # 超过涨停价4200
            last_settle=4000.0,
            limit_pct=0.05,
            symbol="rb2501",
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.ABOVE_LIMIT_UP
        assert "超过涨停价" in result.message
        assert guard.reject_count == 1

    def test_reject_below_limit_down(self) -> None:
        """测试低于跌停价拒绝.

        RULE_ID: CHINA.LIMIT.ORDER_REJECT
        """
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=3700.0,  # 低于跌停价3800
            last_settle=4000.0,
            limit_pct=0.05,
            symbol="rb2501",
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.BELOW_LIMIT_DOWN
        assert "低于跌停价" in result.message
        assert guard.reject_count == 1

    def test_invalid_order_price(self) -> None:
        """测试无效订单价格."""
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=-100.0,
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.INVALID_PRICE
        assert "无效订单价格" in result.message

    def test_invalid_settle_price(self) -> None:
        """测试无效结算价."""
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=4100.0,
            last_settle=0.0,
            limit_pct=0.05,
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.INVALID_SETTLE
        assert "无效昨结算价" in result.message

    def test_at_limit_up_allowed(self) -> None:
        """测试涨停价下单允许."""
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=4200.0,  # 等于涨停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert result.passed is True
        assert guard.limit_hit_count == 1

    def test_at_limit_up_not_allowed(self) -> None:
        """测试涨停价下单不允许."""
        config = LimitPriceConfig(allow_limit_price_order=False)
        guard = LimitPriceGuard(config=config)
        result = guard.check_order_price(
            order_price=4200.0,  # 等于涨停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.AT_LIMIT_UP
        assert "不允许涨停价下单" in result.message

    def test_at_limit_down_allowed(self) -> None:
        """测试跌停价下单允许."""
        guard = LimitPriceGuard()
        result = guard.check_order_price(
            order_price=3800.0,  # 等于跌停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert result.passed is True
        assert guard.limit_hit_count == 1

    def test_at_limit_down_not_allowed(self) -> None:
        """测试跌停价下单不允许."""
        config = LimitPriceConfig(allow_limit_price_order=False)
        guard = LimitPriceGuard(config=config)
        result = guard.check_order_price(
            order_price=3800.0,  # 等于跌停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.AT_LIMIT_DOWN
        assert "不允许跌停价下单" in result.message


class TestLimitPriceGuardGetLimitStatus:
    """获取涨跌停状态测试."""

    def test_normal_status(self) -> None:
        """测试正常状态."""
        guard = LimitPriceGuard()
        status = guard.get_limit_status(
            current_price=4100.0,
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert status == LimitStatus.NORMAL

    def test_at_limit_up_status(self) -> None:
        """测试涨停状态."""
        guard = LimitPriceGuard()
        status = guard.get_limit_status(
            current_price=4200.0,  # 涨停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert status == LimitStatus.AT_LIMIT_UP

    def test_at_limit_down_status(self) -> None:
        """测试跌停状态."""
        guard = LimitPriceGuard()
        status = guard.get_limit_status(
            current_price=3800.0,  # 跌停价
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert status == LimitStatus.AT_LIMIT_DOWN

    def test_near_limit_up_status(self) -> None:
        """测试接近涨停状态."""
        config = LimitPriceConfig(near_limit_threshold=0.01)
        guard = LimitPriceGuard(config=config)
        # 涨停价4200，距离<1% (40)的价格
        status = guard.get_limit_status(
            current_price=4170.0,  # 距离涨停价30，<40 (1%)
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert status == LimitStatus.NEAR_LIMIT_UP

    def test_near_limit_down_status(self) -> None:
        """测试接近跌停状态."""
        config = LimitPriceConfig(near_limit_threshold=0.01)
        guard = LimitPriceGuard(config=config)
        # 跌停价3800，距离<1% (40)的价格
        status = guard.get_limit_status(
            current_price=3830.0,  # 距离跌停价30，<40 (1%)
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert status == LimitStatus.NEAR_LIMIT_DOWN

    def test_invalid_price_returns_normal(self) -> None:
        """测试无效价格返回正常状态."""
        guard = LimitPriceGuard()
        assert guard.get_limit_status(0.0, 4000.0, 0.05) == LimitStatus.NORMAL
        assert guard.get_limit_status(4000.0, 0.0, 0.05) == LimitStatus.NORMAL
        assert guard.get_limit_status(-100.0, 4000.0, 0.05) == LimitStatus.NORMAL


class TestLimitPriceGuardIsAtLimit:
    """检查是否处于涨跌停测试."""

    def test_at_limit_up(self) -> None:
        """测试涨停."""
        guard = LimitPriceGuard()
        assert guard.is_at_limit(4200.0, 4000.0, 0.05) is True

    def test_at_limit_down(self) -> None:
        """测试跌停."""
        guard = LimitPriceGuard()
        assert guard.is_at_limit(3800.0, 4000.0, 0.05) is True

    def test_not_at_limit(self) -> None:
        """测试不在涨跌停."""
        guard = LimitPriceGuard()
        assert guard.is_at_limit(4100.0, 4000.0, 0.05) is False


class TestLimitPriceGuardStats:
    """统计信息测试."""

    def test_initial_stats(self) -> None:
        """测试初始统计."""
        guard = LimitPriceGuard()
        stats = guard.get_stats()
        assert stats["check_count"] == 0
        assert stats["reject_count"] == 0
        assert stats["limit_hit_count"] == 0
        assert stats["pass_rate"] == 0.0

    def test_stats_after_checks(self) -> None:
        """测试检查后的统计."""
        guard = LimitPriceGuard()
        # 通过
        guard.check_order_price(4100.0, 4000.0, 0.05)
        # 拒绝
        guard.check_order_price(4300.0, 4000.0, 0.05)
        # 通过 (涨停价)
        guard.check_order_price(4200.0, 4000.0, 0.05)

        stats = guard.get_stats()
        assert stats["check_count"] == 3
        assert stats["reject_count"] == 1
        assert stats["limit_hit_count"] == 1
        assert stats["pass_rate"] == pytest.approx(2 / 3)

    def test_reset_stats(self) -> None:
        """测试重置统计."""
        guard = LimitPriceGuard()
        guard.check_order_price(4100.0, 4000.0, 0.05)
        guard.check_order_price(4300.0, 4000.0, 0.05)
        guard.reset_stats()

        stats = guard.get_stats()
        assert stats["check_count"] == 0
        assert stats["reject_count"] == 0


class TestExtractProduct:
    """提取品种代码测试."""

    def test_lowercase_symbol(self) -> None:
        """测试小写合约代码."""
        guard = LimitPriceGuard()
        assert guard._extract_product("rb2501") == "rb"
        assert guard._extract_product("cu2503") == "cu"

    def test_uppercase_symbol(self) -> None:
        """测试大写合约代码."""
        guard = LimitPriceGuard()
        assert guard._extract_product("IF2501") == "if"
        assert guard._extract_product("T2503") == "t"

    def test_mixed_case_symbol(self) -> None:
        """测试混合大小写合约代码."""
        guard = LimitPriceGuard()
        assert guard._extract_product("Ma2501") == "ma"

    def test_empty_symbol(self) -> None:
        """测试空合约代码."""
        guard = LimitPriceGuard()
        assert guard._extract_product("") == ""


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_guard_singleton(self) -> None:
        """测试默认门控单例."""
        guard1 = get_default_guard()
        guard2 = get_default_guard()
        assert guard1 is guard2

    def test_check_limit_price_pass(self) -> None:
        """测试check_limit_price便捷函数通过."""
        passed, message = check_limit_price(
            order_price=4100.0,
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert passed is True
        assert "通过" in message

    def test_check_limit_price_reject(self) -> None:
        """测试check_limit_price便捷函数拒绝."""
        passed, message = check_limit_price(
            order_price=4300.0,
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert passed is False
        assert "涨停" in message

    def test_get_limit_prices_function(self) -> None:
        """测试get_limit_prices便捷函数."""
        limit_up, limit_down = get_limit_prices(
            last_settle=4000.0,
            limit_pct=0.05,
        )
        assert limit_up == 4200.0
        assert limit_down == 3800.0


class TestMilitaryRuleM13:
    """军规 M13 涨跌停感知测试.

    RULE_ID: CHINA.LIMIT.PRICE_CHECK, CHINA.LIMIT.ORDER_REJECT
    军规: M13 - 订单价格必须检查涨跌停板
    """

    def test_m13_price_check_basic(self) -> None:
        """M13: 基本价格检查.

        RULE_ID: CHINA.LIMIT.PRICE_CHECK
        """
        guard = LimitPriceGuard()

        # 正常价格
        result = guard.check_order_price(4100.0, 4000.0, 0.05, "rb2501")
        assert result.passed is True

        # 超过涨停
        result = guard.check_order_price(4300.0, 4000.0, 0.05, "rb2501")
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.ABOVE_LIMIT_UP

        # 低于跌停
        result = guard.check_order_price(3700.0, 4000.0, 0.05, "rb2501")
        assert result.passed is False
        assert result.result == LimitPriceCheckResult.BELOW_LIMIT_DOWN

    def test_m13_order_reject_audit(self) -> None:
        """M13: 订单拒绝可审计.

        RULE_ID: CHINA.LIMIT.ORDER_REJECT
        """
        guard = LimitPriceGuard()

        result = guard.check_order_price(4300.0, 4000.0, 0.05, "rb2501")

        # 检查审计信息完整性
        audit_dict = result.to_dict()
        assert audit_dict["result"] == "ABOVE_LIMIT_UP"
        assert audit_dict["symbol"] == "rb2501"
        assert audit_dict["order_price"] == 4300.0
        assert audit_dict["limit_up"] == 4200.0
        assert audit_dict["limit_down"] == 3800.0
        assert audit_dict["last_settle"] == 4000.0
        assert audit_dict["limit_pct"] == 0.05
        assert "超过涨停价" in audit_dict["message"]

    def test_m13_multiple_products(self) -> None:
        """M13: 多品种涨跌停检查.

        RULE_ID: CHINA.LIMIT.PRICE_CHECK
        """
        guard = LimitPriceGuard()

        # 股指期货 IF 10%
        result = guard.check_order_price(4500.0, 4000.0, symbol="IF2501")
        assert result.passed is False  # 超过10%涨停 (4400)

        # 国债期货 T 2%
        result = guard.check_order_price(102.5, 100.0, symbol="T2503")
        assert result.passed is False  # 超过2%涨停 (102)

        # 螺纹钢 rb 4%
        result = guard.check_order_price(4200.0, 4000.0, symbol="rb2501")
        assert result.passed is False  # 超过4%涨停 (4160)

    def test_m13_stats_tracking(self) -> None:
        """M13: 统计追踪.

        RULE_ID: CHINA.LIMIT.PRICE_CHECK
        """
        guard = LimitPriceGuard()

        # 5次检查：3通过，2拒绝
        guard.check_order_price(4100.0, 4000.0, 0.05)  # 通过
        guard.check_order_price(4150.0, 4000.0, 0.05)  # 通过
        guard.check_order_price(4199.0, 4000.0, 0.05)  # 通过
        guard.check_order_price(4300.0, 4000.0, 0.05)  # 拒绝
        guard.check_order_price(3700.0, 4000.0, 0.05)  # 拒绝

        stats = guard.get_stats()
        assert stats["check_count"] == 5
        assert stats["reject_count"] == 2
        assert stats["pass_rate"] == 0.6


class TestEdgeCases:
    """边界条件测试."""

    def test_very_small_limit_pct(self) -> None:
        """测试极小涨跌停幅度."""
        guard = LimitPriceGuard()
        # 0.1% 涨跌停
        limits = guard.get_limit_prices(100.0, limit_pct=0.001)
        assert limits.limit_up == 100.1
        assert limits.limit_down == 99.9

    def test_very_large_limit_pct(self) -> None:
        """测试极大涨跌停幅度."""
        guard = LimitPriceGuard()
        # 20% 涨跌停
        limits = guard.get_limit_prices(100.0, limit_pct=0.20)
        assert limits.limit_up == 120.0
        assert limits.limit_down == 80.0

    def test_price_exactly_at_boundary(self) -> None:
        """测试价格恰好在边界."""
        guard = LimitPriceGuard()

        # 恰好等于涨停价
        result = guard.check_order_price(4200.0, 4000.0, 0.05)
        assert result.passed is True  # 允许涨停价下单

        # 比涨停价高0.01
        result = guard.check_order_price(4200.01, 4000.0, 0.05)
        assert result.passed is False

        # 比跌停价低0.01
        result = guard.check_order_price(3799.99, 4000.0, 0.05)
        assert result.passed is False

    def test_tick_size_zero(self) -> None:
        """测试tick_size为0."""
        guard = LimitPriceGuard()
        # tick_size为0时不进行修正
        limits = guard.get_limit_prices(4123.0, limit_pct=0.05, tick_size=0.0)
        assert limits.limit_up == pytest.approx(4329.15)
        assert limits.limit_down == pytest.approx(3916.85)

    def test_negative_tick_size(self) -> None:
        """测试负tick_size."""
        guard = LimitPriceGuard()
        # 负tick_size不进行修正
        limits = guard.get_limit_prices(4123.0, limit_pct=0.05, tick_size=-1.0)
        assert limits.limit_up == pytest.approx(4329.15)
        assert limits.limit_down == pytest.approx(3916.85)
