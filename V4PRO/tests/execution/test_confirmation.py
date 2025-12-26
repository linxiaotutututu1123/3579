"""
分层确认机制测试.

V4PRO Platform Component - Execution Confirmation System Tests
军规覆盖: M5(成本先行), M6(熔断保护), M12(双重确认), M13(涨跌停感知)

测试覆盖率目标: >=98%

测试场景:
1. ConfirmationLevel枚举测试
2. 订单金额阈值测试
3. 市场条件阈值测试
4. 时段规则测试
5. 策略规则测试
6. SoftConfirmation测试
7. HardConfirmation测试
8. 审计日志集成测试
9. 军规合规测试
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.execution.confirmation import (
    ConfirmationLevel,
    ConfirmationResult,
    SessionType,
    StrategyType,
    OrderValueThresholds,
    MarketConditionThresholds,
    MarketCondition,
    ConfirmationConfig,
    ConfirmationContext,
    ConfirmationDecision,
    ConfirmationAuditEvent,
    ConfirmationAuditEventType,
    SESSION_RULES,
    STRATEGY_RULES,
    get_current_session_type,
    determine_confirmation_level,
    SoftConfirmation,
    HardConfirmation,
    ConfirmationManager,
)
from src.execution.order_types import OrderIntent, Side, Offset


# ==================== Fixtures ====================


@pytest.fixture
def sample_order_intent() -> OrderIntent:
    """创建示例订单意图."""
    return OrderIntent(
        symbol="IF2401",
        side=Side.BUY,
        offset=Offset.OPEN,
        price=3800.0,
        qty=10,
        reason="测试订单",
    )


@pytest.fixture
def sample_market_condition() -> MarketCondition:
    """创建示例市场条件."""
    return MarketCondition(
        current_volatility_pct=0.02,
        price_gap_pct=0.01,
        limit_hit_count=0,
        is_limit_up=False,
        is_limit_down=False,
    )


@pytest.fixture
def default_config() -> ConfirmationConfig:
    """创建默认配置."""
    return ConfirmationConfig()


@pytest.fixture
def sample_context(
    sample_order_intent: OrderIntent,
    sample_market_condition: MarketCondition,
) -> ConfirmationContext:
    """创建示例确认上下文."""
    return ConfirmationContext(
        order_intent=sample_order_intent,
        order_value=380_000,  # 38万,属于AUTO级别
        market_condition=sample_market_condition,
        session_type=SessionType.DAY_SESSION,
        strategy_type=StrategyType.PRODUCTION,
    )


# ==================== Enum Tests ====================


class TestConfirmationLevel:
    """ConfirmationLevel枚举测试."""

    def test_enum_values(self):
        """测试枚举值."""
        assert ConfirmationLevel.AUTO.value == "全自动"
        assert ConfirmationLevel.SOFT_CONFIRM.value == "软确认"
        assert ConfirmationLevel.HARD_CONFIRM.value == "硬确认"

    def test_enum_is_string(self):
        """测试枚举继承str."""
        assert isinstance(ConfirmationLevel.AUTO, str)
        assert ConfirmationLevel.AUTO == "全自动"


class TestConfirmationResult:
    """ConfirmationResult枚举测试."""

    def test_enum_values(self):
        """测试枚举值."""
        assert ConfirmationResult.APPROVED.value == "APPROVED"
        assert ConfirmationResult.REJECTED.value == "REJECTED"
        assert ConfirmationResult.TIMEOUT.value == "TIMEOUT"
        assert ConfirmationResult.DEGRADED.value == "DEGRADED"


class TestSessionType:
    """SessionType枚举测试."""

    def test_enum_values(self):
        """测试枚举值."""
        assert SessionType.DAY_SESSION.value == "DAY_SESSION"
        assert SessionType.NIGHT_SESSION.value == "NIGHT_SESSION"
        assert SessionType.VOLATILE_PERIOD.value == "VOLATILE_PERIOD"


class TestStrategyType:
    """StrategyType枚举测试."""

    def test_enum_values(self):
        """测试枚举值."""
        assert StrategyType.HIGH_FREQUENCY.value == "HIGH_FREQUENCY"
        assert StrategyType.PRODUCTION.value == "PRODUCTION"
        assert StrategyType.EXPERIMENTAL.value == "EXPERIMENTAL"


# ==================== Threshold Tests ====================


class TestOrderValueThresholds:
    """订单金额阈值测试."""

    def test_default_values(self):
        """测试默认值."""
        thresholds = OrderValueThresholds()
        assert thresholds.auto_max == 500_000
        assert thresholds.soft_confirm_max == 2_000_000

    def test_custom_values(self):
        """测试自定义值."""
        thresholds = OrderValueThresholds(
            auto_max=300_000,
            soft_confirm_max=1_000_000,
        )
        assert thresholds.auto_max == 300_000
        assert thresholds.soft_confirm_max == 1_000_000

    def test_frozen(self):
        """测试不可变性."""
        thresholds = OrderValueThresholds()
        with pytest.raises(AttributeError):
            thresholds.auto_max = 100_000


class TestMarketConditionThresholds:
    """市场条件阈值测试."""

    def test_default_values(self):
        """测试默认值."""
        thresholds = MarketConditionThresholds()
        assert thresholds.volatility_pct == 0.05
        assert thresholds.price_gap_pct == 0.03
        assert thresholds.limit_hit_count == 2

    def test_custom_values(self):
        """测试自定义值."""
        thresholds = MarketConditionThresholds(
            volatility_pct=0.10,
            price_gap_pct=0.05,
            limit_hit_count=3,
        )
        assert thresholds.volatility_pct == 0.10
        assert thresholds.price_gap_pct == 0.05
        assert thresholds.limit_hit_count == 3


# ==================== Data Class Tests ====================


class TestMarketCondition:
    """市场条件测试."""

    def test_default_values(self):
        """测试默认值."""
        condition = MarketCondition()
        assert condition.current_volatility_pct == 0.0
        assert condition.price_gap_pct == 0.0
        assert condition.limit_hit_count == 0
        assert condition.is_limit_up is False
        assert condition.is_limit_down is False

    def test_limit_up_condition(self):
        """测试涨停条件."""
        condition = MarketCondition(is_limit_up=True)
        assert condition.is_limit_up is True
        assert condition.is_limit_down is False

    def test_limit_down_condition(self):
        """测试跌停条件."""
        condition = MarketCondition(is_limit_down=True)
        assert condition.is_limit_up is False
        assert condition.is_limit_down is True


class TestConfirmationConfig:
    """确认配置测试."""

    def test_default_values(self):
        """测试默认值."""
        config = ConfirmationConfig()
        assert config.soft_confirm_timeout_seconds == 5.0
        assert config.hard_confirm_timeout_seconds == 30.0
        assert config.enable_night_session_degradation is True

    def test_custom_timeouts(self):
        """测试自定义超时."""
        config = ConfirmationConfig(
            soft_confirm_timeout_seconds=10.0,
            hard_confirm_timeout_seconds=60.0,
        )
        assert config.soft_confirm_timeout_seconds == 10.0
        assert config.hard_confirm_timeout_seconds == 60.0


class TestConfirmationContext:
    """确认上下文测试."""

    def test_to_dict(self, sample_context: ConfirmationContext):
        """测试转换为字典."""
        d = sample_context.to_dict()
        assert "order_intent" in d
        assert "order_value" in d
        assert "market_condition" in d
        assert "session_type" in d
        assert "strategy_type" in d
        assert "timestamp" in d
        assert d["order_value"] == 380_000
        assert d["session_type"] == "DAY_SESSION"

    def test_order_intent_serialization(self, sample_context: ConfirmationContext):
        """测试订单意图序列化."""
        d = sample_context.to_dict()
        intent = d["order_intent"]
        assert intent["symbol"] == "IF2401"
        assert intent["side"] == "BUY"
        assert intent["offset"] == "OPEN"
        assert intent["price"] == 3800.0
        assert intent["qty"] == 10


class TestConfirmationDecision:
    """确认决策测试."""

    def test_to_dict(self):
        """测试转换为字典."""
        decision = ConfirmationDecision(
            level=ConfirmationLevel.SOFT_CONFIRM,
            result=ConfirmationResult.APPROVED,
            reasons=["测试原因"],
            checks_passed=["M5_COST_CHECK"],
            checks_failed=[],
            elapsed_seconds=1.5,
        )
        d = decision.to_dict()
        assert d["level"] == "软确认"
        assert d["result"] == "APPROVED"
        assert "测试原因" in d["reasons"]
        assert "M5_COST_CHECK" in d["checks_passed"]
        assert d["elapsed_seconds"] == 1.5


class TestConfirmationAuditEvent:
    """确认审计事件测试."""

    def test_to_dict(self):
        """测试转换为字典."""
        event = ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_STARTED,
            confirmation_id="CONF-123",
            level="软确认",
            result="APPROVED",
            reason="测试原因",
        )
        d = event.to_dict()
        assert d["event_type"] == "CONFIRMATION.STARTED"
        assert d["confirmation_id"] == "CONF-123"
        assert d["level"] == "软确认"
        assert d["result"] == "APPROVED"

    def test_timestamp_auto_generated(self):
        """测试时间戳自动生成."""
        before = int(time.time() * 1000)
        event = ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_STARTED,
            confirmation_id="CONF-123",
        )
        after = int(time.time() * 1000)
        assert before <= event.ts <= after


# ==================== Rules Mapping Tests ====================


class TestSessionRules:
    """时段规则映射测试."""

    def test_day_session_auto(self):
        """测试日盘AUTO."""
        assert SESSION_RULES[SessionType.DAY_SESSION] == ConfirmationLevel.AUTO

    def test_night_session_soft(self):
        """测试夜盘SOFT_CONFIRM."""
        assert SESSION_RULES[SessionType.NIGHT_SESSION] == ConfirmationLevel.SOFT_CONFIRM

    def test_volatile_period_hard(self):
        """测试波动时段HARD_CONFIRM."""
        assert SESSION_RULES[SessionType.VOLATILE_PERIOD] == ConfirmationLevel.HARD_CONFIRM


class TestStrategyRules:
    """策略规则映射测试."""

    def test_high_frequency_auto(self):
        """测试高频策略AUTO."""
        assert STRATEGY_RULES[StrategyType.HIGH_FREQUENCY] == ConfirmationLevel.AUTO

    def test_production_soft(self):
        """测试生产策略SOFT_CONFIRM."""
        assert STRATEGY_RULES[StrategyType.PRODUCTION] == ConfirmationLevel.SOFT_CONFIRM

    def test_experimental_hard(self):
        """测试实验策略HARD_CONFIRM."""
        assert STRATEGY_RULES[StrategyType.EXPERIMENTAL] == ConfirmationLevel.HARD_CONFIRM


# ==================== Session Type Detection Tests ====================


class TestGetCurrentSessionType:
    """获取当前时段类型测试."""

    def test_day_session(self):
        """测试日盘时段识别."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 10, 30)
            result = get_current_session_type()
            assert result == SessionType.DAY_SESSION

    def test_night_session_before_midnight(self):
        """测试夜盘时段识别(午夜前)."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 22, 0)
            result = get_current_session_type()
            assert result == SessionType.NIGHT_SESSION

    def test_night_session_after_midnight(self):
        """测试夜盘时段识别(午夜后)."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 1, 30)
            result = get_current_session_type()
            assert result == SessionType.NIGHT_SESSION

    def test_volatile_period_morning(self):
        """测试波动时段识别(早盘)."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 9, 5)
            result = get_current_session_type()
            assert result == SessionType.VOLATILE_PERIOD

    def test_volatile_period_closing(self):
        """测试波动时段识别(收盘)."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 14, 50)
            result = get_current_session_type()
            assert result == SessionType.VOLATILE_PERIOD

    def test_non_trading_hours(self):
        """测试非交易时段."""
        with patch("src.execution.confirmation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 7, 0)
            result = get_current_session_type()
            assert result == SessionType.DAY_SESSION  # 非交易时段按日盘处理


# ==================== Level Determination Tests ====================


class TestDetermineConfirmationLevel:
    """确认级别判断测试."""

    def test_auto_level_small_order(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试小额订单AUTO级别."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,  # <50万
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.AUTO

    def test_soft_confirm_medium_order(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试中等金额订单SOFT_CONFIRM级别."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # 100万, 在50万-200万之间
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM

    def test_hard_confirm_large_order(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试大额订单HARD_CONFIRM级别."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,  # 300万, >200万
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM

    def test_soft_confirm_high_volatility(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试高波动率触发SOFT_CONFIRM."""
        market = MarketCondition(
            current_volatility_pct=0.08,  # >5%
            price_gap_pct=0.01,
            limit_hit_count=0,
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM
        assert any("波动率" in r for r in reasons)

    def test_soft_confirm_price_gap(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试跳空触发SOFT_CONFIRM."""
        market = MarketCondition(
            current_volatility_pct=0.02,
            price_gap_pct=0.05,  # >3%
            limit_hit_count=0,
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM
        assert any("跳空" in r for r in reasons)

    def test_hard_confirm_limit_hit(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试连续涨跌停触发HARD_CONFIRM."""
        market = MarketCondition(
            current_volatility_pct=0.02,
            price_gap_pct=0.01,
            limit_hit_count=3,  # >=2
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM
        assert any("涨跌停" in r for r in reasons)

    def test_soft_confirm_current_limit(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试当前涨跌停触发SOFT_CONFIRM."""
        market = MarketCondition(
            current_volatility_pct=0.02,
            price_gap_pct=0.01,
            limit_hit_count=0,
            is_limit_up=True,
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM

    def test_night_session_soft_confirm(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试夜盘时段触发SOFT_CONFIRM."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.NIGHT_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM

    def test_volatile_period_hard_confirm(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试波动时段触发HARD_CONFIRM."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.VOLATILE_PERIOD,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM

    def test_experimental_strategy_hard_confirm(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试实验策略触发HARD_CONFIRM."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.EXPERIMENTAL,
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM

    def test_multiple_factors_highest_level(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试多因素取最高级别."""
        market = MarketCondition(
            current_volatility_pct=0.08,  # SOFT
            price_gap_pct=0.01,
            limit_hit_count=3,  # HARD
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # SOFT
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,  # SOFT
        )
        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM  # 取最高级别


# ==================== SoftConfirmation Tests ====================


class TestSoftConfirmation:
    """软确认测试."""

    @pytest.mark.asyncio
    async def test_all_checks_pass(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试所有检查通过."""
        audit_events = []
        audit_callback = lambda e: audit_events.append(e)

        soft = SoftConfirmation(
            config=default_config,
            audit_callback=audit_callback,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        assert decision.level == ConfirmationLevel.SOFT_CONFIRM
        assert decision.result == ConfirmationResult.APPROVED
        assert "M6_RISK_CHECK" in decision.checks_passed
        assert "M5_COST_CHECK" in decision.checks_passed
        assert "M13_LIMIT_CHECK" in decision.checks_passed
        assert len(decision.checks_failed) == 0

    @pytest.mark.asyncio
    async def test_risk_check_fails(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试风控检查失败."""
        async def failing_risk_check(ctx):
            return False

        soft = SoftConfirmation(
            config=default_config,
            risk_check=failing_risk_check,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M6_RISK_CHECK" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_cost_check_fails(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试成本检查失败."""
        async def failing_cost_check(ctx):
            return False

        soft = SoftConfirmation(
            config=default_config,
            cost_check=failing_cost_check,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M5_COST_CHECK" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_limit_check_fails_on_limit_up_buy(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试涨停时买入检查失败."""
        market = MarketCondition(is_limit_up=True)
        context = ConfirmationContext(
            order_intent=sample_order_intent,  # BUY
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        soft = SoftConfirmation(config=default_config)
        decision = await soft.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M13_LIMIT_CHECK" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_limit_check_fails_on_limit_down_sell(
        self,
        default_config: ConfirmationConfig,
    ):
        """测试跌停时卖出检查失败."""
        order_intent = OrderIntent(
            symbol="IF2401",
            side=Side.SELL,
            offset=Offset.CLOSE,
            price=3800.0,
            qty=10,
        )
        market = MarketCondition(is_limit_down=True)
        context = ConfirmationContext(
            order_intent=order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        soft = SoftConfirmation(config=default_config)
        decision = await soft.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M13_LIMIT_CHECK" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_audit_events_emitted(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试审计事件发送."""
        audit_events = []
        audit_callback = lambda e: audit_events.append(e)

        soft = SoftConfirmation(
            config=default_config,
            audit_callback=audit_callback,
        )

        await soft.confirm("CONF-001", sample_context)

        event_types = [e.event_type for e in audit_events]
        assert ConfirmationAuditEventType.SOFT_CONFIRM_STARTED in event_types
        assert ConfirmationAuditEventType.SOFT_CONFIRM_RISK_CHECK in event_types
        assert ConfirmationAuditEventType.SOFT_CONFIRM_COST_CHECK in event_types
        assert ConfirmationAuditEventType.SOFT_CONFIRM_LIMIT_CHECK in event_types
        assert ConfirmationAuditEventType.SOFT_CONFIRM_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_timeout_auto_pass(
        self,
        sample_context: ConfirmationContext,
    ):
        """测试超时自动通过."""
        config = ConfirmationConfig(soft_confirm_timeout_seconds=0.1)

        async def slow_risk_check(ctx):
            await asyncio.sleep(0.5)
            return False  # 如果没超时会返回False

        soft = SoftConfirmation(
            config=config,
            risk_check=slow_risk_check,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        # 超时应该自动通过
        assert "风控检查超时,自动通过" in decision.reasons or decision.result == ConfirmationResult.APPROVED


# ==================== HardConfirmation Tests ====================


class TestHardConfirmation:
    """硬确认测试."""

    @pytest.mark.asyncio
    async def test_user_approves(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试用户批准."""
        async def user_approves(conf_id, ctx):
            return True

        hard = HardConfirmation(
            config=default_config,
            user_confirm_callback=user_approves,
        )

        decision = await hard.confirm("CONF-001", sample_context)

        assert decision.result == ConfirmationResult.APPROVED
        assert "M12_USER_CONFIRM" in decision.checks_passed

    @pytest.mark.asyncio
    async def test_user_rejects(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试用户拒绝."""
        async def user_rejects(conf_id, ctx):
            return False

        hard = HardConfirmation(
            config=default_config,
            user_confirm_callback=user_rejects,
        )

        decision = await hard.confirm("CONF-001", sample_context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M12_USER_CONFIRM" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_timeout_day_session_circuit_break(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试日盘超时触发熔断."""
        config = ConfirmationConfig(hard_confirm_timeout_seconds=0.1)
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        audit_events = []
        hard = HardConfirmation(
            config=config,
            audit_callback=lambda e: audit_events.append(e),
            user_confirm_callback=slow_confirm,
        )

        decision = await hard.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M6_CIRCUIT_BREAKER" in decision.checks_failed
        event_types = [e.event_type for e in audit_events]
        assert ConfirmationAuditEventType.HARD_CONFIRM_CIRCUIT_BREAK in event_types

    @pytest.mark.asyncio
    async def test_timeout_night_session_degraded(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试夜盘超时降级."""
        config = ConfirmationConfig(
            hard_confirm_timeout_seconds=0.1,
            enable_night_session_degradation=True,
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.NIGHT_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        audit_events = []
        hard = HardConfirmation(
            config=config,
            audit_callback=lambda e: audit_events.append(e),
            user_confirm_callback=slow_confirm,
        )

        decision = await hard.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.DEGRADED
        event_types = [e.event_type for e in audit_events]
        assert ConfirmationAuditEventType.HARD_CONFIRM_DEGRADED in event_types

    @pytest.mark.asyncio
    async def test_alert_callback_called(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试告警回调被调用."""
        alert_called = {"called": False, "title": "", "message": ""}

        async def mock_alert(title, message, metadata):
            alert_called["called"] = True
            alert_called["title"] = title
            alert_called["message"] = message

        async def quick_confirm(conf_id, ctx):
            return True

        hard = HardConfirmation(
            config=default_config,
            alert_callback=mock_alert,
            user_confirm_callback=quick_confirm,
        )

        await hard.confirm("CONF-001", sample_context)

        assert alert_called["called"] is True
        assert "[V4PRO]" in alert_called["title"]
        assert "IF2401" in alert_called["title"]

    @pytest.mark.asyncio
    async def test_audit_events_emitted(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试审计事件发送."""
        audit_events = []

        async def quick_confirm(conf_id, ctx):
            return True

        hard = HardConfirmation(
            config=default_config,
            audit_callback=lambda e: audit_events.append(e),
            user_confirm_callback=quick_confirm,
        )

        await hard.confirm("CONF-001", sample_context)

        event_types = [e.event_type for e in audit_events]
        assert ConfirmationAuditEventType.HARD_CONFIRM_STARTED in event_types
        assert ConfirmationAuditEventType.HARD_CONFIRM_ALERT_SENT in event_types
        assert ConfirmationAuditEventType.HARD_CONFIRM_USER_RESPONSE in event_types


# ==================== ConfirmationManager Tests ====================


class TestConfirmationManager:
    """确认管理器测试."""

    @pytest.mark.asyncio
    async def test_auto_level_direct_pass(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试AUTO级别直接通过."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        manager = ConfirmationManager()
        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.AUTO
        assert decision.result == ConfirmationResult.APPROVED

    @pytest.mark.asyncio
    async def test_soft_level_uses_soft_confirmation(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试SOFT级别使用软确认."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # 中等金额
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        manager = ConfirmationManager()
        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.SOFT_CONFIRM

    @pytest.mark.asyncio
    async def test_hard_level_uses_hard_confirmation(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试HARD级别使用硬确认."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,  # 大额
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        async def quick_approve(conf_id, ctx):
            return True

        manager = ConfirmationManager(user_confirm_callback=quick_approve)
        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.HARD_CONFIRM
        assert decision.result == ConfirmationResult.APPROVED

    @pytest.mark.asyncio
    async def test_audit_events_emitted(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试审计事件发送."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        audit_events = []
        manager = ConfirmationManager(
            audit_callback=lambda e: audit_events.append(e),
        )

        await manager.confirm(context)

        event_types = [e.event_type for e in audit_events]
        assert ConfirmationAuditEventType.CONFIRMATION_STARTED in event_types
        assert ConfirmationAuditEventType.CONFIRMATION_LEVEL_DETERMINED in event_types
        assert ConfirmationAuditEventType.CONFIRMATION_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_confirmation_id_generated(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试确认ID生成."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        audit_events = []
        manager = ConfirmationManager(
            audit_callback=lambda e: audit_events.append(e),
        )

        await manager.confirm(context)
        await manager.confirm(context)

        # 确认ID应该递增
        ids = [e.confirmation_id for e in audit_events if e.event_type == ConfirmationAuditEventType.CONFIRMATION_STARTED]
        assert len(ids) == 2
        assert ids[0] != ids[1]
        assert ids[0].startswith("CONF-")
        assert ids[1].startswith("CONF-")

    @pytest.mark.asyncio
    async def test_custom_callbacks_used(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试自定义回调被使用."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # SOFT level
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        risk_check_called = {"called": False}

        async def custom_risk_check(ctx):
            risk_check_called["called"] = True
            return True

        manager = ConfirmationManager(risk_check=custom_risk_check)
        await manager.confirm(context)

        assert risk_check_called["called"] is True


# ==================== Military Rule Compliance Tests ====================


class TestMilitaryRuleCompliance:
    """军规合规测试."""

    @pytest.mark.asyncio
    async def test_m5_cost_check_integration(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试M5成本先行机制集成."""
        cost_check_called = {"called": False}

        async def cost_check(ctx):
            cost_check_called["called"] = True
            return True

        soft = SoftConfirmation(
            config=default_config,
            cost_check=cost_check,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        assert cost_check_called["called"] is True
        assert "M5_COST_CHECK" in decision.checks_passed

    @pytest.mark.asyncio
    async def test_m6_risk_check_integration(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试M6熔断保护机制集成."""
        risk_check_called = {"called": False}

        async def risk_check(ctx):
            risk_check_called["called"] = True
            return True

        soft = SoftConfirmation(
            config=default_config,
            risk_check=risk_check,
        )

        decision = await soft.confirm("CONF-001", sample_context)

        assert risk_check_called["called"] is True
        assert "M6_RISK_CHECK" in decision.checks_passed

    @pytest.mark.asyncio
    async def test_m12_dual_confirmation(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试M12双重确认机制."""
        # 大额订单应触发HARD_CONFIRM
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        level, reasons = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.HARD_CONFIRM

    @pytest.mark.asyncio
    async def test_m13_limit_price_awareness(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试M13涨跌停感知."""
        market = MarketCondition(
            is_limit_up=True,
        )
        context = ConfirmationContext(
            order_intent=sample_order_intent,  # BUY
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        soft = SoftConfirmation(config=default_config)
        decision = await soft.confirm("CONF-001", context)

        # 涨停时买入应被拒绝
        assert decision.result == ConfirmationResult.REJECTED
        assert "M13_LIMIT_CHECK" in decision.checks_failed


# ==================== Edge Case Tests ====================


class TestEdgeCases:
    """边界情况测试."""

    def test_order_value_at_threshold(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试订单金额恰好在阈值边界."""
        # 恰好等于AUTO阈值
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=500_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, _ = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.SOFT_CONFIRM  # 边界值属于下一级别

        # 恰好等于SOFT阈值
        context2 = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=2_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level2, _ = determine_confirmation_level(context2, default_config)
        assert level2 == ConfirmationLevel.HARD_CONFIRM

    def test_volatility_at_threshold(
        self,
        sample_order_intent: OrderIntent,
        default_config: ConfirmationConfig,
    ):
        """测试波动率恰好在阈值边界."""
        market = MarketCondition(current_volatility_pct=0.05)  # 恰好等于阈值
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, _ = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.AUTO  # 等于阈值不触发

    def test_zero_order_value(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        default_config: ConfirmationConfig,
    ):
        """测试零金额订单."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=0,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )
        level, _ = determine_confirmation_level(context, default_config)
        assert level == ConfirmationLevel.AUTO

    @pytest.mark.asyncio
    async def test_no_audit_callback(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """测试无审计回调时不报错."""
        soft = SoftConfirmation(
            config=default_config,
            audit_callback=None,
        )

        # 不应抛出异常
        decision = await soft.confirm("CONF-001", sample_context)
        assert decision is not None

    @pytest.mark.asyncio
    async def test_confirmation_manager_with_all_callbacks(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试确认管理器配置所有回调."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        callbacks_called = {
            "audit": False,
            "alert": False,
            "risk": False,
            "cost": False,
            "limit": False,
        }

        def audit_cb(e):
            callbacks_called["audit"] = True

        async def alert_cb(t, m, d):
            callbacks_called["alert"] = True

        async def risk_cb(c):
            callbacks_called["risk"] = True
            return True

        async def cost_cb(c):
            callbacks_called["cost"] = True
            return True

        async def limit_cb(c):
            callbacks_called["limit"] = True
            return True

        manager = ConfirmationManager(
            audit_callback=audit_cb,
            alert_callback=alert_cb,
            risk_check=risk_cb,
            cost_check=cost_cb,
            limit_check=limit_cb,
        )

        await manager.confirm(context)

        assert callbacks_called["audit"] is True


# ==================== Integration Tests ====================


class TestIntegration:
    """集成测试."""

    @pytest.mark.asyncio
    async def test_full_soft_confirmation_flow(
        self,
        sample_order_intent: OrderIntent,
    ):
        """测试完整软确认流程."""
        market = MarketCondition(current_volatility_pct=0.08)  # 触发SOFT
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=market,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        audit_events = []
        manager = ConfirmationManager(
            audit_callback=lambda e: audit_events.append(e),
        )

        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.SOFT_CONFIRM
        assert decision.result == ConfirmationResult.APPROVED
        assert len(audit_events) >= 5  # 至少5个审计事件

    @pytest.mark.asyncio
    async def test_full_hard_confirmation_flow_approved(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试完整硬确认流程(批准)."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,  # 触发HARD
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        async def quick_approve(conf_id, ctx):
            return True

        audit_events = []
        manager = ConfirmationManager(
            audit_callback=lambda e: audit_events.append(e),
            user_confirm_callback=quick_approve,
        )

        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.HARD_CONFIRM
        assert decision.result == ConfirmationResult.APPROVED

    @pytest.mark.asyncio
    async def test_full_hard_confirmation_flow_rejected(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试完整硬确认流程(拒绝)."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        async def reject(conf_id, ctx):
            return False

        manager = ConfirmationManager(user_confirm_callback=reject)
        decision = await manager.confirm(context)

        assert decision.result == ConfirmationResult.REJECTED

    @pytest.mark.asyncio
    async def test_night_session_degradation_flow(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """测试夜盘降级完整流程."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.NIGHT_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        config = ConfirmationConfig(
            hard_confirm_timeout_seconds=0.1,
            enable_night_session_degradation=True,
        )

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        audit_events = []
        manager = ConfirmationManager(
            config=config,
            audit_callback=lambda e: audit_events.append(e),
            user_confirm_callback=slow_confirm,
        )

        decision = await manager.confirm(context)

        # 夜盘超时应降级
        assert decision.result == ConfirmationResult.DEGRADED
