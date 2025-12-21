"""
分层确认机制增强功能测试.

V4PRO Platform Component - Enhanced Execution Confirmation System Tests
军规覆盖: M5(成本先行), M6(熔断保护), M12(双重确认), M13(涨跌停感知), M15(夜盘规则), M17(程序化合规)

测试覆盖率目标: >=98%

测试场景:
1. 熔断器集成测试
2. 熔断状态检查测试
3. 硬确认超时触发熔断测试
4. 高频策略豁免测试
5. 恢复期确认级别升级测试
6. 工厂函数测试
7. 边界情况测试
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from src.execution.confirmation import (
    ConfirmationLevel,
    ConfirmationResult,
    SessionType,
    StrategyType,
    ConfirmationConfig,
    ConfirmationContext,
    ConfirmationDecision,
    ConfirmationAuditEvent,
    ConfirmationAuditEventType,
    MarketCondition,
    SoftConfirmation,
)
from src.execution.confirmation_enhanced import (
    CircuitBreakerAwareResult,
    ConfirmationAuditEventTypeExtended,
    HighFrequencyExemptionConfig,
    RecoveryPeriodConfig,
    CircuitBreakerIntegrationConfig,
    HardConfirmationEnhanced,
    ConfirmationManagerEnhanced,
    create_enhanced_confirmation_manager,
)
from src.execution.order_types import OrderIntent, Side, Offset


# ==================== Fixtures ====================


@pytest.fixture
def sample_order_intent() -> OrderIntent:
    """Create sample order intent."""
    return OrderIntent(
        symbol="IF2401",
        side=Side.BUY,
        offset=Offset.OPEN,
        price=3800.0,
        qty=10,
        reason="Test order",
    )


@pytest.fixture
def sample_market_condition() -> MarketCondition:
    """Create sample market condition."""
    return MarketCondition(
        current_volatility_pct=0.02,
        price_gap_pct=0.01,
        limit_hit_count=0,
        is_limit_up=False,
        is_limit_down=False,
    )


@pytest.fixture
def default_config() -> ConfirmationConfig:
    """Create default configuration."""
    return ConfirmationConfig()


@pytest.fixture
def sample_context(
    sample_order_intent: OrderIntent,
    sample_market_condition: MarketCondition,
) -> ConfirmationContext:
    """Create sample confirmation context."""
    return ConfirmationContext(
        order_intent=sample_order_intent,
        order_value=380_000,  # 38 wan, AUTO level
        market_condition=sample_market_condition,
        session_type=SessionType.DAY_SESSION,
        strategy_type=StrategyType.PRODUCTION,
    )


@pytest.fixture
def high_frequency_context(
    sample_order_intent: OrderIntent,
    sample_market_condition: MarketCondition,
) -> ConfirmationContext:
    """Create high frequency strategy context."""
    return ConfirmationContext(
        order_intent=sample_order_intent,
        order_value=50_000,  # 5 wan, small order
        market_condition=sample_market_condition,
        session_type=SessionType.DAY_SESSION,
        strategy_type=StrategyType.HIGH_FREQUENCY,
    )


@pytest.fixture
def mock_circuit_breaker():
    """Create mock circuit breaker."""
    from enum import Enum

    class MockCircuitBreakerState(str, Enum):
        CLOSED = "CLOSED"
        OPEN = "OPEN"
        HALF_OPEN = "HALF_OPEN"

    mock = MagicMock()
    mock.current_state = MockCircuitBreakerState.CLOSED
    return mock, MockCircuitBreakerState


# ==================== Config Tests ====================


class TestHighFrequencyExemptionConfig:
    """High frequency exemption config tests."""

    def test_default_values(self):
        """Test default values."""
        config = HighFrequencyExemptionConfig()
        assert config.enable_exemption is True
        assert config.max_order_value_for_exemption == 100_000
        assert config.max_position_ratio == 0.05
        assert config.allowed_symbols == []
        assert config.min_strategy_score == 80

    def test_custom_values(self):
        """Test custom values."""
        config = HighFrequencyExemptionConfig(
            enable_exemption=False,
            max_order_value_for_exemption=200_000,
            allowed_symbols=["IF2401", "IC2401"],
        )
        assert config.enable_exemption is False
        assert config.max_order_value_for_exemption == 200_000
        assert "IF2401" in config.allowed_symbols


class TestRecoveryPeriodConfig:
    """Recovery period config tests."""

    def test_default_values(self):
        """Test default values."""
        config = RecoveryPeriodConfig()
        assert config.upgrade_confirmation_level is True
        assert config.recovery_soft_to_hard is True
        assert config.recovery_auto_to_soft is True

    def test_disabled_upgrade(self):
        """Test disabled upgrade."""
        config = RecoveryPeriodConfig(upgrade_confirmation_level=False)
        assert config.upgrade_confirmation_level is False


class TestCircuitBreakerIntegrationConfig:
    """Circuit breaker integration config tests."""

    def test_default_values(self):
        """Test default values."""
        config = CircuitBreakerIntegrationConfig()
        assert config.enable_circuit_breaker_check is True
        assert config.enable_timeout_circuit_break is True
        assert config.block_on_circuit_break is True
        assert config.high_frequency_exemption is not None
        assert config.recovery_period is not None

    def test_disabled_integration(self):
        """Test disabled integration."""
        config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=False,
            enable_timeout_circuit_break=False,
            block_on_circuit_break=False,
        )
        assert config.enable_circuit_breaker_check is False
        assert config.enable_timeout_circuit_break is False
        assert config.block_on_circuit_break is False


# ==================== Extended Enum Tests ====================


class TestCircuitBreakerAwareResult:
    """Circuit breaker aware result tests."""

    def test_enum_values(self):
        """Test enum values."""
        assert CircuitBreakerAwareResult.CIRCUIT_BREAKER_BLOCKED.value == "CIRCUIT_BREAKER_BLOCKED"
        assert CircuitBreakerAwareResult.CIRCUIT_BREAKER_TRIGGERED.value == "CIRCUIT_BREAKER_TRIGGERED"
        assert CircuitBreakerAwareResult.RECOVERY_PERIOD_UPGRADED.value == "RECOVERY_PERIOD_UPGRADED"


class TestConfirmationAuditEventTypeExtended:
    """Extended audit event type tests."""

    def test_enum_values(self):
        """Test enum values."""
        assert ConfirmationAuditEventTypeExtended.CIRCUIT_BREAKER_CHECK.value == "CONFIRMATION.CIRCUIT_BREAKER.CHECK"
        assert ConfirmationAuditEventTypeExtended.CIRCUIT_BREAKER_BLOCKED.value == "CONFIRMATION.CIRCUIT_BREAKER.BLOCKED"
        assert ConfirmationAuditEventTypeExtended.CIRCUIT_BREAKER_TRIGGER.value == "CONFIRMATION.CIRCUIT_BREAKER.TRIGGER"


# ==================== HardConfirmationEnhanced Tests ====================


class TestHardConfirmationEnhanced:
    """Enhanced hard confirmation tests."""

    @pytest.mark.asyncio
    async def test_user_approves(
        self,
        sample_context: ConfirmationContext,
        default_config: ConfirmationConfig,
    ):
        """Test user approval."""
        async def user_approves(conf_id, ctx):
            return True

        hard = HardConfirmationEnhanced(
            config=default_config,
            user_confirm_callback=user_approves,
        )

        decision = await hard.confirm("CONF-001", sample_context)

        assert decision.result == ConfirmationResult.APPROVED
        assert "M12_USER_CONFIRM" in decision.checks_passed

    @pytest.mark.asyncio
    async def test_timeout_triggers_circuit_breaker(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test timeout triggers circuit breaker."""
        config = ConfirmationConfig(hard_confirm_timeout_seconds=0.1)
        cb_config = CircuitBreakerIntegrationConfig(
            enable_timeout_circuit_break=True,
        )

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        circuit_breaker_triggered = {"called": False}

        async def trigger_cb(reason, metadata):
            circuit_breaker_triggered["called"] = True
            circuit_breaker_triggered["reason"] = reason
            return True

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        hard = HardConfirmationEnhanced(
            config=config,
            circuit_breaker_config=cb_config,
            user_confirm_callback=slow_confirm,
            circuit_breaker_trigger_callback=trigger_cb,
        )

        decision = await hard.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M6_CIRCUIT_BREAKER" in decision.checks_failed
        assert circuit_breaker_triggered["called"] is True

    @pytest.mark.asyncio
    async def test_night_session_degraded(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test night session degradation."""
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

        hard = HardConfirmationEnhanced(
            config=config,
            user_confirm_callback=slow_confirm,
        )

        decision = await hard.confirm("CONF-001", context)

        assert decision.result == ConfirmationResult.DEGRADED


# ==================== ConfirmationManagerEnhanced Tests ====================


class TestConfirmationManagerEnhanced:
    """Enhanced confirmation manager tests."""

    @pytest.mark.asyncio
    async def test_auto_level_direct_pass(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test AUTO level direct pass."""
        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        manager = ConfirmationManagerEnhanced()
        decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.AUTO
        assert decision.result == ConfirmationResult.APPROVED

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_confirmation(
        self,
        sample_context: ConfirmationContext,
        mock_circuit_breaker,
    ):
        """Test circuit breaker blocks confirmation when OPEN."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.OPEN

        cb_config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=True,
            block_on_circuit_break=True,
        )

        manager = ConfirmationManagerEnhanced(
            circuit_breaker_config=cb_config,
            circuit_breaker=mock_cb,
        )

        # Patch the import inside the method
        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(sample_context)

        assert decision.result == ConfirmationResult.REJECTED
        assert "M6_CIRCUIT_BREAKER_BLOCK" in decision.checks_failed

    @pytest.mark.asyncio
    async def test_high_frequency_exemption_when_blocked(
        self,
        high_frequency_context: ConfirmationContext,
        mock_circuit_breaker,
    ):
        """Test high frequency exemption allows confirmation when circuit breaker is OPEN."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.OPEN

        hf_config = HighFrequencyExemptionConfig(
            enable_exemption=True,
            max_order_value_for_exemption=100_000,
        )

        cb_config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=True,
            block_on_circuit_break=True,
            high_frequency_exemption=hf_config,
        )

        manager = ConfirmationManagerEnhanced(
            circuit_breaker_config=cb_config,
            circuit_breaker=mock_cb,
        )

        # Should be exempt and pass
        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(high_frequency_context)

        # High frequency with small order should pass even when CB is OPEN
        assert decision.result == ConfirmationResult.APPROVED

    @pytest.mark.asyncio
    async def test_recovery_period_upgrades_auto_to_soft(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        mock_circuit_breaker,
    ):
        """Test recovery period upgrades AUTO to SOFT."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.HALF_OPEN

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,  # Would be AUTO normally
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        recovery_config = RecoveryPeriodConfig(
            upgrade_confirmation_level=True,
            recovery_auto_to_soft=True,
        )

        cb_config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=True,
            recovery_period=recovery_config,
        )

        manager = ConfirmationManagerEnhanced(
            circuit_breaker_config=cb_config,
            circuit_breaker=mock_cb,
        )

        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(context)

        # Should be upgraded to SOFT_CONFIRM
        assert decision.level == ConfirmationLevel.SOFT_CONFIRM

    @pytest.mark.asyncio
    async def test_recovery_period_upgrades_soft_to_hard(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        mock_circuit_breaker,
    ):
        """Test recovery period upgrades SOFT to HARD."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.HALF_OPEN

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # Would be SOFT normally
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        recovery_config = RecoveryPeriodConfig(
            upgrade_confirmation_level=True,
            recovery_soft_to_hard=True,
        )

        cb_config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=True,
            recovery_period=recovery_config,
        )

        async def quick_approve(conf_id, ctx):
            return True

        manager = ConfirmationManagerEnhanced(
            circuit_breaker_config=cb_config,
            circuit_breaker=mock_cb,
            user_confirm_callback=quick_approve,
        )

        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(context)

        # Should be upgraded to HARD_CONFIRM
        assert decision.level == ConfirmationLevel.HARD_CONFIRM

    @pytest.mark.asyncio
    async def test_no_circuit_breaker_configured(
        self,
        sample_context: ConfirmationContext,
    ):
        """Test normal operation without circuit breaker."""
        manager = ConfirmationManagerEnhanced()
        decision = await manager.confirm(sample_context)

        # Should work normally without CB
        assert decision is not None

    def test_set_circuit_breaker(
        self,
        mock_circuit_breaker,
    ):
        """Test setting circuit breaker after init."""
        mock_cb, MockState = mock_circuit_breaker
        manager = ConfirmationManagerEnhanced()

        assert manager._circuit_breaker is None

        manager.set_circuit_breaker(mock_cb)

        assert manager._circuit_breaker is mock_cb

    def test_get_circuit_breaker_state(
        self,
        mock_circuit_breaker,
    ):
        """Test getting circuit breaker state."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.CLOSED

        manager = ConfirmationManagerEnhanced(circuit_breaker=mock_cb)

        state = manager.get_circuit_breaker_state()
        assert state == "CLOSED"

    def test_get_circuit_breaker_state_not_configured(self):
        """Test getting circuit breaker state when not configured."""
        manager = ConfirmationManagerEnhanced()
        state = manager.get_circuit_breaker_state()
        assert state is None


# ==================== High Frequency Exemption Tests ====================


class TestHighFrequencyExemption:
    """High frequency exemption tests."""

    def test_exemption_enabled(self):
        """Test exemption when enabled."""
        hf_config = HighFrequencyExemptionConfig(enable_exemption=True)
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        context = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IF2401",
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=50_000,  # Small order
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        is_exempt, reason = manager._check_high_frequency_exemption(context)
        assert is_exempt is True

    def test_exemption_disabled(self):
        """Test exemption when disabled."""
        hf_config = HighFrequencyExemptionConfig(enable_exemption=False)
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        context = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IF2401",
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=50_000,
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        is_exempt, reason = manager._check_high_frequency_exemption(context)
        assert is_exempt is False
        assert "disabled" in reason.lower()

    def test_exemption_non_hf_strategy(self):
        """Test exemption denied for non-HF strategy."""
        hf_config = HighFrequencyExemptionConfig(enable_exemption=True)
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        context = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IF2401",
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=50_000,
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,  # Not HIGH_FREQUENCY
        )

        is_exempt, reason = manager._check_high_frequency_exemption(context)
        assert is_exempt is False

    def test_exemption_order_too_large(self):
        """Test exemption denied for large order."""
        hf_config = HighFrequencyExemptionConfig(
            enable_exemption=True,
            max_order_value_for_exemption=100_000,
        )
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        context = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IF2401",
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=200_000,  # Over limit
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        is_exempt, reason = manager._check_high_frequency_exemption(context)
        assert is_exempt is False
        assert "limit" in reason.lower() or "exceed" in reason.lower() or "exceed" in reason

    def test_exemption_symbol_whitelist(self):
        """Test exemption with symbol whitelist."""
        hf_config = HighFrequencyExemptionConfig(
            enable_exemption=True,
            allowed_symbols=["IF2401", "IC2401"],
        )
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        # Allowed symbol
        context1 = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IF2401",
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=50_000,
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        is_exempt, _ = manager._check_high_frequency_exemption(context1)
        assert is_exempt is True

        # Not allowed symbol
        context2 = ConfirmationContext(
            order_intent=OrderIntent(
                symbol="IH2401",  # Not in whitelist
                side=Side.BUY,
                offset=Offset.OPEN,
                price=3800.0,
                qty=10,
            ),
            order_value=50_000,
            market_condition=MarketCondition(),
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        is_exempt, reason = manager._check_high_frequency_exemption(context2)
        assert is_exempt is False


# ==================== Factory Function Tests ====================


class TestCreateEnhancedConfirmationManager:
    """Factory function tests."""

    def test_default_creation(self):
        """Test default creation."""
        manager = create_enhanced_confirmation_manager()

        assert manager is not None
        assert isinstance(manager, ConfirmationManagerEnhanced)
        assert manager._circuit_breaker is None

    def test_with_circuit_breaker(
        self,
        mock_circuit_breaker,
    ):
        """Test creation with circuit breaker."""
        mock_cb, _ = mock_circuit_breaker

        manager = create_enhanced_confirmation_manager(
            circuit_breaker=mock_cb,
            enable_circuit_breaker_integration=True,
        )

        assert manager._circuit_breaker is mock_cb

    def test_disabled_integration(self):
        """Test disabled circuit breaker integration."""
        manager = create_enhanced_confirmation_manager(
            enable_circuit_breaker_integration=False,
        )

        assert manager._cb_config.enable_circuit_breaker_check is False
        assert manager._cb_config.enable_timeout_circuit_break is False

    def test_with_callbacks(self):
        """Test creation with callbacks."""
        audit_called = {"called": False}

        def audit_cb(e):
            audit_called["called"] = True

        async def alert_cb(t, m, d):
            pass

        async def user_cb(c, ctx):
            return True

        manager = create_enhanced_confirmation_manager(
            audit_callback=audit_cb,
            alert_callback=alert_cb,
            user_confirm_callback=user_cb,
        )

        assert manager._audit_callback is audit_cb


# ==================== Integration Tests ====================


class TestEnhancedIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_full_flow_with_circuit_breaker(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        mock_circuit_breaker,
    ):
        """Test full flow with circuit breaker integration."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.CLOSED

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=300_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        audit_events = []

        manager = create_enhanced_confirmation_manager(
            circuit_breaker=mock_cb,
            enable_circuit_breaker_integration=True,
            audit_callback=lambda e: audit_events.append(e),
        )

        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(context)

        assert decision.level == ConfirmationLevel.AUTO
        assert decision.result == ConfirmationResult.APPROVED
        assert len(audit_events) >= 2  # At least start and complete

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(
        self,
        sample_context: ConfirmationContext,
        mock_circuit_breaker,
    ):
        """Test handling of circuit breaker state transitions."""
        mock_cb, MockState = mock_circuit_breaker

        manager = create_enhanced_confirmation_manager(
            circuit_breaker=mock_cb,
            enable_circuit_breaker_integration=True,
        )

        # Test CLOSED state
        mock_cb.current_state = MockState.CLOSED
        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision1 = await manager.confirm(sample_context)
        assert decision1.result != ConfirmationResult.REJECTED or "CIRCUIT_BREAKER_BLOCK" not in decision1.checks_failed

        # Test OPEN state (should block non-HF)
        mock_cb.current_state = MockState.OPEN
        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision2 = await manager.confirm(sample_context)
        assert decision2.result == ConfirmationResult.REJECTED
        assert "M6_CIRCUIT_BREAKER_BLOCK" in decision2.checks_failed

        # Test HALF_OPEN state (should allow but upgrade level)
        mock_cb.current_state = MockState.HALF_OPEN
        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision3 = await manager.confirm(sample_context)
        # Should not be blocked in HALF_OPEN
        assert "M6_CIRCUIT_BREAKER_BLOCK" not in decision3.checks_failed


# ==================== Military Rule Compliance Tests ====================


class TestEnhancedMilitaryRuleCompliance:
    """Enhanced military rule compliance tests."""

    @pytest.mark.asyncio
    async def test_m6_circuit_breaker_integration(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test M6 circuit breaker integration."""
        config = ConfirmationConfig(hard_confirm_timeout_seconds=0.1)

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        circuit_breaker_triggered = {"called": False}

        async def trigger_cb(reason, metadata):
            circuit_breaker_triggered["called"] = True
            return True

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        manager = create_enhanced_confirmation_manager(
            config=config,
            enable_circuit_breaker_integration=True,
        )
        manager._hard_confirmation._circuit_breaker_trigger = trigger_cb
        manager._hard_confirmation._user_confirm_callback = slow_confirm

        decision = await manager.confirm(context)

        # M6: Circuit breaker should be triggered on timeout
        assert "M6_CIRCUIT_BREAKER" in decision.checks_failed
        assert circuit_breaker_triggered["called"] is True

    @pytest.mark.asyncio
    async def test_m12_dual_confirmation_with_cb(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
        mock_circuit_breaker,
    ):
        """Test M12 dual confirmation with circuit breaker."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.HALF_OPEN

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=1_000_000,  # SOFT level normally
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.HIGH_FREQUENCY,
        )

        async def quick_approve(conf_id, ctx):
            return True

        manager = ConfirmationManagerEnhanced(
            circuit_breaker=mock_cb,
            user_confirm_callback=quick_approve,
        )

        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(context)

        # M12: Should be upgraded to HARD during recovery period
        assert decision.level == ConfirmationLevel.HARD_CONFIRM

    @pytest.mark.asyncio
    async def test_m15_night_session_with_cb(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test M15 night session rules with circuit breaker."""
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

        manager = create_enhanced_confirmation_manager(
            config=config,
            enable_circuit_breaker_integration=True,
            user_confirm_callback=slow_confirm,
        )

        decision = await manager.confirm(context)

        # M15: Night session should degrade, not trigger CB
        assert decision.result == ConfirmationResult.DEGRADED

    @pytest.mark.asyncio
    async def test_m17_programmatic_compliance(
        self,
        high_frequency_context: ConfirmationContext,
        mock_circuit_breaker,
    ):
        """Test M17 programmatic compliance with HF exemption."""
        mock_cb, MockState = mock_circuit_breaker
        mock_cb.current_state = MockState.OPEN

        hf_config = HighFrequencyExemptionConfig(
            enable_exemption=True,
            max_order_value_for_exemption=100_000,
        )

        cb_config = CircuitBreakerIntegrationConfig(
            enable_circuit_breaker_check=True,
            block_on_circuit_break=True,
            high_frequency_exemption=hf_config,
        )

        manager = ConfirmationManagerEnhanced(
            circuit_breaker_config=cb_config,
            circuit_breaker=mock_cb,
        )

        with patch.dict('sys.modules', {'src.guardian.circuit_breaker': MagicMock(CircuitBreakerState=MockState)}):
            decision = await manager.confirm(high_frequency_context)

        # M17: HF strategy should be exempt from CB block
        assert decision.result == ConfirmationResult.APPROVED


# ==================== Edge Case Tests ====================


class TestEnhancedEdgeCases:
    """Enhanced edge case tests."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_check_exception(
        self,
        sample_context: ConfirmationContext,
    ):
        """Test handling of circuit breaker check exception."""
        mock_cb = MagicMock()
        mock_cb.current_state = PropertyMock(side_effect=Exception("CB Error"))

        manager = ConfirmationManagerEnhanced(circuit_breaker=mock_cb)

        # Should not crash, should continue with confirmation
        decision = await manager.confirm(sample_context)
        assert decision is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_trigger_exception(
        self,
        sample_order_intent: OrderIntent,
        sample_market_condition: MarketCondition,
    ):
        """Test handling of circuit breaker trigger exception."""
        config = ConfirmationConfig(hard_confirm_timeout_seconds=0.1)

        context = ConfirmationContext(
            order_intent=sample_order_intent,
            order_value=3_000_000,
            market_condition=sample_market_condition,
            session_type=SessionType.DAY_SESSION,
            strategy_type=StrategyType.PRODUCTION,
        )

        async def failing_trigger(reason, metadata):
            raise Exception("Trigger failed")

        async def slow_confirm(conf_id, ctx):
            await asyncio.sleep(0.5)
            return True

        hard = HardConfirmationEnhanced(
            config=config,
            circuit_breaker_trigger_callback=failing_trigger,
            user_confirm_callback=slow_confirm,
        )

        # Should not crash
        decision = await hard.confirm("CONF-001", context)
        assert decision.result == ConfirmationResult.REJECTED

    @pytest.mark.asyncio
    async def test_empty_symbol_whitelist(
        self,
        high_frequency_context: ConfirmationContext,
    ):
        """Test empty symbol whitelist allows all symbols."""
        hf_config = HighFrequencyExemptionConfig(
            enable_exemption=True,
            allowed_symbols=[],  # Empty means all allowed
        )
        cb_config = CircuitBreakerIntegrationConfig(high_frequency_exemption=hf_config)
        manager = ConfirmationManagerEnhanced(circuit_breaker_config=cb_config)

        is_exempt, _ = manager._check_high_frequency_exemption(high_frequency_context)
        assert is_exempt is True
