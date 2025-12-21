"""
CircuitBreaker 熔断器测试.

V4 SPEC D2: 熔断-恢复闭环测试
覆盖率目标: >= 98%

V2 Scenarios:
- GUARD.CIRCUIT_BREAKER.STATES: 5状态覆盖
- GUARD.CIRCUIT_BREAKER.TRANSITIONS: 状态转换覆盖
- GUARD.CIRCUIT_BREAKER.TRIGGERS: 触发条件覆盖
- GUARD.CIRCUIT_BREAKER.RECOVERY: 恢复流程覆盖
- GUARD.CIRCUIT_BREAKER.MANUAL: 人工干预覆盖
- GUARD.CIRCUIT_BREAKER.AUDIT: 审计日志覆盖 (M3)

军规覆盖:
- M3: 审计日志完整
- M6: 熔断保护机制完整
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.guardian.circuit_breaker import (
    VALID_CIRCUIT_BREAKER_TRANSITIONS,
    AuditRecord,
    CircuitBreaker,
    CircuitBreakerEvent,
    CircuitBreakerManager,
    CircuitBreakerMetrics,
    CircuitBreakerState,
    DefaultAuditLogger,
    RecoveryConfig,
    RecoveryProgress,
    TransitionError,
    TriggerCheckResult,
    TriggerThresholds,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_time() -> MagicMock:
    """模拟时间函数."""
    mock = MagicMock(return_value=1000.0)
    return mock


@pytest.fixture
def default_thresholds() -> TriggerThresholds:
    """默认触发阈值."""
    return TriggerThresholds()


@pytest.fixture
def default_recovery_config() -> RecoveryConfig:
    """默认恢复配置."""
    return RecoveryConfig()


@pytest.fixture
def audit_logger() -> DefaultAuditLogger:
    """审计日志记录器."""
    return DefaultAuditLogger()


@pytest.fixture
def circuit_breaker(
    mock_time: MagicMock, audit_logger: DefaultAuditLogger
) -> CircuitBreaker:
    """熔断器实例."""
    return CircuitBreaker(
        audit_logger=audit_logger,
        time_func=mock_time,
    )


@pytest.fixture
def triggered_metrics() -> CircuitBreakerMetrics:
    """会触发熔断的指标."""
    return CircuitBreakerMetrics(
        daily_loss_pct=0.05,  # > 0.03 阈值
        position_loss_pct=0.06,  # > 0.05 阈值
        margin_usage_pct=0.90,  # > 0.85 阈值
        consecutive_losses=6,  # >= 5 阈值
    )


@pytest.fixture
def safe_metrics() -> CircuitBreakerMetrics:
    """不会触发熔断的指标."""
    return CircuitBreakerMetrics(
        daily_loss_pct=0.01,
        position_loss_pct=0.02,
        margin_usage_pct=0.50,
        consecutive_losses=2,
    )


# =============================================================================
# TriggerThresholds Tests
# =============================================================================


class TestTriggerThresholds:
    """触发阈值测试."""

    def test_default_values(self) -> None:
        """测试默认阈值."""
        thresholds = TriggerThresholds()
        assert thresholds.daily_loss_pct == 0.03
        assert thresholds.position_loss_pct == 0.05
        assert thresholds.margin_usage_pct == 0.85
        assert thresholds.consecutive_losses == 5

    def test_custom_values(self) -> None:
        """测试自定义阈值."""
        thresholds = TriggerThresholds(
            daily_loss_pct=0.02,
            position_loss_pct=0.04,
            margin_usage_pct=0.80,
            consecutive_losses=3,
        )
        assert thresholds.daily_loss_pct == 0.02
        assert thresholds.position_loss_pct == 0.04
        assert thresholds.margin_usage_pct == 0.80
        assert thresholds.consecutive_losses == 3

    def test_immutability(self) -> None:
        """测试不可变性."""
        thresholds = TriggerThresholds()
        with pytest.raises(AttributeError):
            thresholds.daily_loss_pct = 0.10  # type: ignore


# =============================================================================
# RecoveryConfig Tests
# =============================================================================


class TestRecoveryConfig:
    """恢复配置测试."""

    def test_default_values(self) -> None:
        """测试默认配置."""
        config = RecoveryConfig()
        assert config.position_ratio_steps == (0.25, 0.5, 0.75, 1.0)
        assert config.step_interval_seconds == 60.0
        assert config.cooling_duration_seconds == 30.0
        assert config.full_cooling_duration_seconds == 300.0

    def test_custom_values(self) -> None:
        """测试自定义配置."""
        config = RecoveryConfig(
            position_ratio_steps=(0.5, 1.0),
            step_interval_seconds=30.0,
            cooling_duration_seconds=15.0,
            full_cooling_duration_seconds=120.0,
        )
        assert config.position_ratio_steps == (0.5, 1.0)
        assert config.step_interval_seconds == 30.0

    def test_immutability(self) -> None:
        """测试不可变性."""
        config = RecoveryConfig()
        with pytest.raises(AttributeError):
            config.step_interval_seconds = 120.0  # type: ignore


# =============================================================================
# CircuitBreakerMetrics Tests
# =============================================================================


class TestCircuitBreakerMetrics:
    """熔断器指标测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        metrics = CircuitBreakerMetrics()
        assert metrics.daily_loss_pct == 0.0
        assert metrics.position_loss_pct == 0.0
        assert metrics.margin_usage_pct == 0.0
        assert metrics.consecutive_losses == 0

    def test_to_dict(self, triggered_metrics: CircuitBreakerMetrics) -> None:
        """测试转换为字典."""
        data = triggered_metrics.to_dict()
        assert data["daily_loss_pct"] == 0.05
        assert data["position_loss_pct"] == 0.06
        assert data["margin_usage_pct"] == 0.90
        assert data["consecutive_losses"] == 6


# =============================================================================
# TriggerCheckResult Tests
# =============================================================================


class TestTriggerCheckResult:
    """触发检测结果测试."""

    def test_creation(self, triggered_metrics: CircuitBreakerMetrics) -> None:
        """测试创建."""
        result = TriggerCheckResult(
            should_trigger=True,
            trigger_reasons=["test reason"],
            metrics=triggered_metrics,
            timestamp=1000.0,
        )
        assert result.should_trigger is True
        assert len(result.trigger_reasons) == 1

    def test_to_dict(self, triggered_metrics: CircuitBreakerMetrics) -> None:
        """测试转换为字典."""
        result = TriggerCheckResult(
            should_trigger=True,
            trigger_reasons=["reason1", "reason2"],
            metrics=triggered_metrics,
            timestamp=1000.0,
        )
        data = result.to_dict()
        assert data["should_trigger"] is True
        assert len(data["trigger_reasons"]) == 2
        assert "metrics" in data
        assert data["timestamp"] == 1000.0


# =============================================================================
# AuditRecord Tests
# =============================================================================


class TestAuditRecord:
    """审计记录测试."""

    def test_creation(self) -> None:
        """测试创建."""
        record = AuditRecord(
            record_id="test-id",
            timestamp=1000.0,
            event_type="test_event",
            from_state="NORMAL",
            to_state="TRIGGERED",
            trigger_reason="test reason",
            details={"key": "value"},
        )
        assert record.record_id == "test-id"
        assert record.event_type == "test_event"

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        record = AuditRecord(
            record_id="test-id",
            timestamp=1000.0,
            event_type="test_event",
            from_state="NORMAL",
            to_state="TRIGGERED",
            trigger_reason="test reason",
            details={"key": "value"},
        )
        data = record.to_dict()
        assert data["record_id"] == "test-id"
        assert data["from_state"] == "NORMAL"
        assert data["to_state"] == "TRIGGERED"


# =============================================================================
# DefaultAuditLogger Tests (M3 军规)
# =============================================================================


class TestDefaultAuditLogger:
    """审计日志测试 - M3军规覆盖."""

    def test_log_creates_record(self, audit_logger: DefaultAuditLogger) -> None:
        """M3: 测试日志记录创建."""
        audit_logger.log(
            event_type="test_event",
            from_state="NORMAL",
            to_state="TRIGGERED",
            trigger_reason="test",
            details={},
        )
        assert len(audit_logger.records) == 1
        assert audit_logger.records[0].event_type == "test_event"

    def test_records_are_copied(self, audit_logger: DefaultAuditLogger) -> None:
        """测试记录返回副本."""
        audit_logger.log("test", "A", "B", "reason", {})
        records = audit_logger.records
        records.clear()  # 修改返回的列表
        assert len(audit_logger.records) == 1  # 原列表不受影响

    def test_get_records_by_type(self, audit_logger: DefaultAuditLogger) -> None:
        """测试按类型获取记录."""
        audit_logger.log("type_a", "A", "B", "reason", {})
        audit_logger.log("type_b", "B", "C", "reason", {})
        audit_logger.log("type_a", "C", "D", "reason", {})

        type_a_records = audit_logger.get_records_by_type("type_a")
        assert len(type_a_records) == 2

    def test_clear(self, audit_logger: DefaultAuditLogger) -> None:
        """测试清空记录."""
        audit_logger.log("test", "A", "B", "reason", {})
        audit_logger.clear()
        assert len(audit_logger.records) == 0


# =============================================================================
# RecoveryProgress Tests
# =============================================================================


class TestRecoveryProgress:
    """恢复进度测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        progress = RecoveryProgress()
        assert progress.current_step == 0
        assert progress.current_position_ratio == 0.0
        assert progress.step_start_time == 0.0
        assert progress.total_steps == 4

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        progress = RecoveryProgress(
            current_step=2,
            current_position_ratio=0.5,
            step_start_time=1000.0,
            total_steps=4,
        )
        data = progress.to_dict()
        assert data["current_step"] == 2
        assert data["current_position_ratio"] == 0.5


# =============================================================================
# CircuitBreakerState Tests
# =============================================================================


class TestCircuitBreakerState:
    """GUARD.CIRCUIT_BREAKER.STATES: 状态枚举测试."""

    def test_all_states_defined(self) -> None:
        """测试所有状态定义."""
        assert CircuitBreakerState.NORMAL.value == 0
        assert CircuitBreakerState.TRIGGERED.value == 1
        assert CircuitBreakerState.COOLING.value == 2
        assert CircuitBreakerState.RECOVERY.value == 3
        assert CircuitBreakerState.MANUAL_OVERRIDE.value == 4

    def test_state_count(self) -> None:
        """测试状态数量."""
        assert len(CircuitBreakerState) == 5


# =============================================================================
# CircuitBreaker Initialization Tests
# =============================================================================


class TestCircuitBreakerInit:
    """熔断器初始化测试."""

    def test_default_initialization(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试默认初始化."""
        assert circuit_breaker.state == CircuitBreakerState.NORMAL
        assert circuit_breaker.transition_count == 0

    def test_custom_thresholds(self, mock_time: MagicMock) -> None:
        """测试自定义阈值."""
        thresholds = TriggerThresholds(daily_loss_pct=0.02)
        cb = CircuitBreaker(thresholds=thresholds, time_func=mock_time)
        assert cb.thresholds.daily_loss_pct == 0.02

    def test_custom_recovery_config(self, mock_time: MagicMock) -> None:
        """测试自定义恢复配置."""
        config = RecoveryConfig(step_interval_seconds=30.0)
        cb = CircuitBreaker(recovery_config=config, time_func=mock_time)
        assert cb.recovery_config.step_interval_seconds == 30.0

    def test_initial_audit_log(
        self, audit_logger: DefaultAuditLogger, mock_time: MagicMock
    ) -> None:
        """M3: 测试初始化审计日志."""
        CircuitBreaker(audit_logger=audit_logger, time_func=mock_time)
        assert len(audit_logger.records) == 1
        assert audit_logger.records[0].event_type == "circuit_breaker_init"


# =============================================================================
# CircuitBreaker Trigger Conditions Tests
# =============================================================================


class TestCircuitBreakerTriggerConditions:
    """GUARD.CIRCUIT_BREAKER.TRIGGERS: 触发条件测试."""

    def test_check_daily_loss_trigger(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试日损失触发."""
        metrics = CircuitBreakerMetrics(daily_loss_pct=0.05)
        result = circuit_breaker.check_trigger_conditions(metrics)
        assert result.should_trigger is True
        assert any("daily_loss_pct" in r for r in result.trigger_reasons)

    def test_check_position_loss_trigger(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试持仓损失触发."""
        metrics = CircuitBreakerMetrics(position_loss_pct=0.06)
        result = circuit_breaker.check_trigger_conditions(metrics)
        assert result.should_trigger is True
        assert any("position_loss_pct" in r for r in result.trigger_reasons)

    def test_check_margin_usage_trigger(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试保证金使用率触发."""
        metrics = CircuitBreakerMetrics(margin_usage_pct=0.90)
        result = circuit_breaker.check_trigger_conditions(metrics)
        assert result.should_trigger is True
        assert any("margin_usage_pct" in r for r in result.trigger_reasons)

    def test_check_consecutive_losses_trigger(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试连续亏损触发."""
        metrics = CircuitBreakerMetrics(consecutive_losses=5)
        result = circuit_breaker.check_trigger_conditions(metrics)
        assert result.should_trigger is True
        assert any("consecutive_losses" in r for r in result.trigger_reasons)

    def test_check_multiple_triggers(
        self, circuit_breaker: CircuitBreaker, triggered_metrics: CircuitBreakerMetrics
    ) -> None:
        """测试多条件触发."""
        result = circuit_breaker.check_trigger_conditions(triggered_metrics)
        assert result.should_trigger is True
        assert len(result.trigger_reasons) == 4  # 所有4个条件都触发

    def test_check_no_trigger(
        self, circuit_breaker: CircuitBreaker, safe_metrics: CircuitBreakerMetrics
    ) -> None:
        """测试无触发."""
        result = circuit_breaker.check_trigger_conditions(safe_metrics)
        assert result.should_trigger is False
        assert len(result.trigger_reasons) == 0


# =============================================================================
# CircuitBreaker State Transitions Tests
# =============================================================================


class TestCircuitBreakerTransitions:
    """GUARD.CIRCUIT_BREAKER.TRANSITIONS: 状态转换测试."""

    def test_normal_to_triggered(
        self,
        circuit_breaker: CircuitBreaker,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试 NORMAL -> TRIGGERED."""
        success = circuit_breaker.trigger(triggered_metrics)
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.TRIGGERED

    def test_trigger_from_non_normal_fails(
        self,
        circuit_breaker: CircuitBreaker,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试非NORMAL状态触发失败."""
        circuit_breaker.force_state(CircuitBreakerState.COOLING)
        success = circuit_breaker.trigger(triggered_metrics)
        assert success is False

    def test_trigger_with_safe_metrics_fails(
        self,
        circuit_breaker: CircuitBreaker,
        safe_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试安全指标不触发."""
        success = circuit_breaker.trigger(safe_metrics)
        assert success is False
        assert circuit_breaker.state == CircuitBreakerState.NORMAL

    def test_triggered_to_cooling_auto(
        self,
        circuit_breaker: CircuitBreaker,
        mock_time: MagicMock,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试 TRIGGERED -> COOLING (30秒后自动)."""
        circuit_breaker.trigger(triggered_metrics)
        assert circuit_breaker.state == CircuitBreakerState.TRIGGERED

        # 推进时间30秒
        mock_time.return_value = 1030.0
        circuit_breaker.tick()
        assert circuit_breaker.state == CircuitBreakerState.COOLING

    def test_cooling_to_recovery_auto(
        self,
        circuit_breaker: CircuitBreaker,
        mock_time: MagicMock,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试 COOLING -> RECOVERY (5分钟后)."""
        # 触发 -> 冷却
        circuit_breaker.trigger(triggered_metrics)
        mock_time.return_value = 1030.0
        circuit_breaker.tick()
        assert circuit_breaker.state == CircuitBreakerState.COOLING

        # 冷却 -> 恢复 (5分钟后)
        mock_time.return_value = 1330.0  # 300秒后
        circuit_breaker.tick()
        assert circuit_breaker.state == CircuitBreakerState.RECOVERY

    def test_recovery_to_normal_gradual(
        self,
        circuit_breaker: CircuitBreaker,
        mock_time: MagicMock,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试 RECOVERY -> NORMAL (渐进式恢复)."""
        # 进入恢复状态
        circuit_breaker.trigger(triggered_metrics)
        mock_time.return_value = 1030.0
        circuit_breaker.tick()  # -> COOLING
        mock_time.return_value = 1330.0
        circuit_breaker.tick()  # -> RECOVERY

        assert circuit_breaker.state == CircuitBreakerState.RECOVERY
        assert circuit_breaker.current_position_ratio == 0.25  # 第一步

        # 推进恢复步骤
        mock_time.return_value = 1390.0  # +60秒
        circuit_breaker.tick()
        assert circuit_breaker.current_position_ratio == 0.5  # 第二步

        mock_time.return_value = 1450.0  # +60秒
        circuit_breaker.tick()
        assert circuit_breaker.current_position_ratio == 0.75  # 第三步

        mock_time.return_value = 1510.0  # +60秒
        circuit_breaker.tick()
        assert circuit_breaker.state == CircuitBreakerState.NORMAL  # 恢复完成

    def test_can_transition(self, circuit_breaker: CircuitBreaker) -> None:
        """测试 can_transition."""
        assert circuit_breaker.can_transition(CircuitBreakerEvent.TRIGGER) is True
        assert (
            circuit_breaker.can_transition(CircuitBreakerEvent.COOLING_START)
            is False
        )

    def test_get_next_state(self, circuit_breaker: CircuitBreaker) -> None:
        """测试 get_next_state."""
        next_state = circuit_breaker.get_next_state(CircuitBreakerEvent.TRIGGER)
        assert next_state == CircuitBreakerState.TRIGGERED

    def test_get_next_state_invalid(self, circuit_breaker: CircuitBreaker) -> None:
        """测试 get_next_state 无效事件."""
        next_state = circuit_breaker.get_next_state("invalid_event")
        assert next_state is None

    def test_all_valid_transitions_covered(self) -> None:
        """测试所有有效转换."""
        for (from_state, event), to_state in VALID_CIRCUIT_BREAKER_TRANSITIONS.items():
            cb = CircuitBreaker()
            cb.force_state(from_state)
            assert cb.can_transition(event) is True
            assert cb.get_next_state(event) == to_state


# =============================================================================
# CircuitBreaker Manual Override Tests
# =============================================================================


class TestCircuitBreakerManualOverride:
    """GUARD.CIRCUIT_BREAKER.MANUAL: 人工干预测试."""

    def test_manual_override_from_normal(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试从NORMAL进入人工接管."""
        success = circuit_breaker.manual_override("test override")
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_manual_override_from_triggered(
        self,
        circuit_breaker: CircuitBreaker,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试从TRIGGERED进入人工接管."""
        circuit_breaker.trigger(triggered_metrics)
        success = circuit_breaker.manual_override()
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_manual_override_from_cooling(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试从COOLING进入人工接管."""
        circuit_breaker.force_state(CircuitBreakerState.COOLING)
        success = circuit_breaker.manual_override()
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_manual_override_from_recovery(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试从RECOVERY进入人工接管."""
        circuit_breaker.force_state(CircuitBreakerState.RECOVERY)
        success = circuit_breaker.manual_override()
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_manual_override_fails_when_already_in_override(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试已在人工接管状态时再次接管失败."""
        circuit_breaker.manual_override()
        success = circuit_breaker.manual_override()
        assert success is False

    def test_manual_release_to_normal(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试人工解除到NORMAL."""
        circuit_breaker.manual_override()
        success = circuit_breaker.manual_release(to_normal=True)
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.NORMAL

    def test_manual_release_to_cooling(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试人工解除到COOLING."""
        circuit_breaker.manual_override()
        success = circuit_breaker.manual_release(to_normal=False)
        assert success is True
        assert circuit_breaker.state == CircuitBreakerState.COOLING

    def test_manual_release_fails_from_non_override(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试非人工接管状态下解除失败."""
        success = circuit_breaker.manual_release()
        assert success is False


# =============================================================================
# CircuitBreaker Properties Tests
# =============================================================================


class TestCircuitBreakerProperties:
    """熔断器属性测试."""

    def test_current_position_ratio_normal(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试NORMAL状态仓位比例."""
        assert circuit_breaker.current_position_ratio == 1.0

    def test_current_position_ratio_triggered(
        self,
        circuit_breaker: CircuitBreaker,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试TRIGGERED状态仓位比例."""
        circuit_breaker.trigger(triggered_metrics)
        assert circuit_breaker.current_position_ratio == 0.0

    def test_current_position_ratio_recovery(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试RECOVERY状态仓位比例."""
        circuit_breaker.force_state(CircuitBreakerState.RECOVERY)
        circuit_breaker._recovery_progress.current_position_ratio = 0.5
        assert circuit_breaker.current_position_ratio == 0.5

    def test_is_trading_allowed_normal(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试NORMAL状态允许交易."""
        assert circuit_breaker.is_trading_allowed is True

    def test_is_trading_allowed_recovery(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试RECOVERY状态允许交易."""
        circuit_breaker.force_state(CircuitBreakerState.RECOVERY)
        assert circuit_breaker.is_trading_allowed is True

    def test_is_trading_not_allowed_triggered(
        self,
        circuit_breaker: CircuitBreaker,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试TRIGGERED状态不允许交易."""
        circuit_breaker.trigger(triggered_metrics)
        assert circuit_breaker.is_trading_allowed is False

    def test_is_new_position_allowed(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试新开仓权限."""
        assert circuit_breaker.is_new_position_allowed is True
        circuit_breaker.force_state(CircuitBreakerState.TRIGGERED)
        assert circuit_breaker.is_new_position_allowed is False

    def test_get_state_duration(
        self, circuit_breaker: CircuitBreaker, mock_time: MagicMock
    ) -> None:
        """测试状态持续时间."""
        mock_time.return_value = 1100.0
        duration = circuit_breaker.get_state_duration()
        assert duration == 100.0  # 1100 - 1000


# =============================================================================
# CircuitBreaker Force State Tests
# =============================================================================


class TestCircuitBreakerForceState:
    """强制状态测试."""

    def test_force_state(
        self, circuit_breaker: CircuitBreaker, audit_logger: DefaultAuditLogger
    ) -> None:
        """测试强制设置状态."""
        initial_count = len(audit_logger.records)
        circuit_breaker.force_state(CircuitBreakerState.HALTED, "test")  # type: ignore
        # 注意：HALTED不在CircuitBreakerState中，用TRIGGERED代替测试
        circuit_breaker.force_state(CircuitBreakerState.TRIGGERED, "test force")
        assert circuit_breaker.state == CircuitBreakerState.TRIGGERED
        assert len(audit_logger.records) > initial_count

    def test_force_state_increments_count(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试强制状态增加计数."""
        initial_count = circuit_breaker.transition_count
        circuit_breaker.force_state(CircuitBreakerState.COOLING)
        assert circuit_breaker.transition_count == initial_count + 1

    def test_force_state_callback(self, mock_time: MagicMock) -> None:
        """测试强制状态回调."""
        callbacks: list[tuple[CircuitBreakerState, CircuitBreakerState, str]] = []

        def callback(
            from_s: CircuitBreakerState, to_s: CircuitBreakerState, reason: str
        ) -> None:
            callbacks.append((from_s, to_s, reason))

        cb = CircuitBreaker(on_state_change=callback, time_func=mock_time)
        cb.force_state(CircuitBreakerState.TRIGGERED, "forced")

        assert len(callbacks) == 1
        assert callbacks[0][1] == CircuitBreakerState.TRIGGERED
        assert "force:" in callbacks[0][2]


# =============================================================================
# CircuitBreaker to_dict Tests
# =============================================================================


class TestCircuitBreakerToDict:
    """熔断器字典转换测试."""

    def test_to_dict_contains_all_fields(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试字典包含所有字段."""
        data = circuit_breaker.to_dict()
        expected_fields = [
            "state",
            "state_value",
            "transition_count",
            "state_duration",
            "current_position_ratio",
            "is_trading_allowed",
            "is_new_position_allowed",
            "recovery_progress",
            "last_trigger_reasons",
            "thresholds",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_to_dict_values(self, circuit_breaker: CircuitBreaker) -> None:
        """测试字典值."""
        data = circuit_breaker.to_dict()
        assert data["state"] == "NORMAL"
        assert data["state_value"] == 0
        assert data["is_trading_allowed"] is True


# =============================================================================
# CircuitBreaker Tick Edge Cases Tests
# =============================================================================


class TestCircuitBreakerTickEdgeCases:
    """tick方法边界情况测试."""

    def test_tick_in_normal_state(self, circuit_breaker: CircuitBreaker) -> None:
        """测试NORMAL状态下tick."""
        state = circuit_breaker.tick()
        assert state == CircuitBreakerState.NORMAL

    def test_tick_in_manual_override(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """测试MANUAL_OVERRIDE状态下tick."""
        circuit_breaker.manual_override()
        state = circuit_breaker.tick()
        assert state == CircuitBreakerState.MANUAL_OVERRIDE

    def test_tick_triggered_not_enough_time(
        self,
        circuit_breaker: CircuitBreaker,
        mock_time: MagicMock,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """测试TRIGGERED状态时间不足."""
        circuit_breaker.trigger(triggered_metrics)
        mock_time.return_value = 1015.0  # 只过了15秒
        state = circuit_breaker.tick()
        assert state == CircuitBreakerState.TRIGGERED

    def test_tick_cooling_not_enough_time(
        self, circuit_breaker: CircuitBreaker, mock_time: MagicMock
    ) -> None:
        """测试COOLING状态时间不足."""
        circuit_breaker.force_state(CircuitBreakerState.COOLING)
        circuit_breaker._cooling_start_time = 1000.0
        mock_time.return_value = 1100.0  # 只过了100秒
        state = circuit_breaker.tick()
        assert state == CircuitBreakerState.COOLING

    def test_tick_recovery_not_enough_time(
        self, circuit_breaker: CircuitBreaker, mock_time: MagicMock
    ) -> None:
        """测试RECOVERY状态步骤时间不足."""
        circuit_breaker.force_state(CircuitBreakerState.RECOVERY)
        circuit_breaker._recovery_progress.step_start_time = 1000.0
        circuit_breaker._recovery_progress.current_step = 0
        circuit_breaker._recovery_progress.current_position_ratio = 0.25
        mock_time.return_value = 1030.0  # 只过了30秒
        state = circuit_breaker.tick()
        assert state == CircuitBreakerState.RECOVERY
        assert circuit_breaker._recovery_progress.current_step == 0


# =============================================================================
# CircuitBreaker State Change Callback Tests
# =============================================================================


class TestCircuitBreakerCallback:
    """状态变更回调测试."""

    def test_callback_on_trigger(
        self, mock_time: MagicMock, triggered_metrics: CircuitBreakerMetrics
    ) -> None:
        """测试触发时回调."""
        callbacks: list[tuple[Any, Any, str]] = []

        def callback(from_s: Any, to_s: Any, reason: str) -> None:
            callbacks.append((from_s, to_s, reason))

        cb = CircuitBreaker(on_state_change=callback, time_func=mock_time)
        cb.trigger(triggered_metrics)

        # 找到触发相关的回调
        trigger_callbacks = [c for c in callbacks if "daily_loss" in c[2]]
        assert len(trigger_callbacks) > 0

    def test_callback_on_manual_override(self, mock_time: MagicMock) -> None:
        """测试人工接管时回调."""
        callbacks: list[tuple[Any, Any, str]] = []

        def callback(from_s: Any, to_s: Any, reason: str) -> None:
            callbacks.append((from_s, to_s, reason))

        cb = CircuitBreaker(on_state_change=callback, time_func=mock_time)
        cb.manual_override("test")

        override_callbacks = [
            c for c in callbacks if c[1] == CircuitBreakerState.MANUAL_OVERRIDE
        ]
        assert len(override_callbacks) > 0


# =============================================================================
# CircuitBreaker Audit Logging Tests (M3 军规)
# =============================================================================


class TestCircuitBreakerAuditLogging:
    """M3军规: 审计日志测试."""

    def test_trigger_logs_audit(
        self,
        circuit_breaker: CircuitBreaker,
        audit_logger: DefaultAuditLogger,
        triggered_metrics: CircuitBreakerMetrics,
    ) -> None:
        """M3: 测试触发记录审计."""
        initial_count = len(audit_logger.records)
        circuit_breaker.trigger(triggered_metrics)
        assert len(audit_logger.records) > initial_count

        transition_records = audit_logger.get_records_by_type(
            "circuit_breaker_transition"
        )
        assert len(transition_records) > 0

    def test_manual_override_logs_audit(
        self,
        circuit_breaker: CircuitBreaker,
        audit_logger: DefaultAuditLogger,
    ) -> None:
        """M3: 测试人工接管记录审计."""
        circuit_breaker.manual_override("test")
        transition_records = audit_logger.get_records_by_type(
            "circuit_breaker_transition"
        )
        assert any(r.to_state == "MANUAL_OVERRIDE" for r in transition_records)

    def test_recovery_step_logs_audit(
        self,
        circuit_breaker: CircuitBreaker,
        audit_logger: DefaultAuditLogger,
        mock_time: MagicMock,
    ) -> None:
        """M3: 测试恢复步骤记录审计."""
        circuit_breaker.force_state(CircuitBreakerState.RECOVERY)
        circuit_breaker._recovery_progress.step_start_time = 1000.0
        circuit_breaker._recovery_progress.current_step = 0
        circuit_breaker._recovery_progress.current_position_ratio = 0.25
        circuit_breaker._recovery_progress.total_steps = 4

        mock_time.return_value = 1060.0
        circuit_breaker.tick()

        step_records = audit_logger.get_records_by_type(
            "circuit_breaker_recovery_step"
        )
        assert len(step_records) > 0


# =============================================================================
# CircuitBreakerManager Tests
# =============================================================================


class TestCircuitBreakerManager:
    """熔断器管理器测试."""

    def test_manager_init(self) -> None:
        """测试管理器初始化."""
        manager = CircuitBreakerManager()
        assert manager.global_breaker is not None
        assert manager.global_breaker.state == CircuitBreakerState.NORMAL

    def test_manager_get_breaker(self) -> None:
        """测试获取熔断器."""
        manager = CircuitBreakerManager()
        global_breaker = manager.get_breaker("global")
        assert global_breaker is manager.global_breaker

        non_existent = manager.get_breaker("non_existent")
        assert non_existent is None

    def test_manager_create_breaker(self) -> None:
        """测试创建熔断器."""
        manager = CircuitBreakerManager()
        custom_breaker = manager.create_breaker(
            "custom",
            thresholds=TriggerThresholds(daily_loss_pct=0.02),
        )
        assert custom_breaker is not None
        assert custom_breaker.thresholds.daily_loss_pct == 0.02
        assert manager.get_breaker("custom") is custom_breaker

    def test_manager_remove_breaker(self) -> None:
        """测试移除熔断器."""
        manager = CircuitBreakerManager()
        manager.create_breaker("custom")

        success = manager.remove_breaker("custom")
        assert success is True
        assert manager.get_breaker("custom") is None

    def test_manager_cannot_remove_global(self) -> None:
        """测试不能移除全局熔断器."""
        manager = CircuitBreakerManager()
        success = manager.remove_breaker("global")
        assert success is False
        assert manager.get_breaker("global") is not None

    def test_manager_remove_nonexistent(self) -> None:
        """测试移除不存在的熔断器."""
        manager = CircuitBreakerManager()
        success = manager.remove_breaker("nonexistent")
        assert success is False

    def test_manager_tick_all(self) -> None:
        """测试推进所有熔断器."""
        manager = CircuitBreakerManager()
        manager.create_breaker("custom")
        states = manager.tick_all()
        assert "global" in states
        assert "custom" in states

    def test_manager_get_all_states(self) -> None:
        """测试获取所有状态."""
        manager = CircuitBreakerManager()
        manager.create_breaker("custom")
        states = manager.get_all_states()
        assert states["global"] == CircuitBreakerState.NORMAL
        assert states["custom"] == CircuitBreakerState.NORMAL

    def test_manager_is_any_triggered(self) -> None:
        """测试是否有任何触发."""
        manager = CircuitBreakerManager()
        assert manager.is_any_triggered() is False

        manager.global_breaker.force_state(CircuitBreakerState.TRIGGERED)
        assert manager.is_any_triggered() is True

    def test_manager_to_dict(self) -> None:
        """测试管理器字典转换."""
        manager = CircuitBreakerManager()
        data = manager.to_dict()
        assert "breakers" in data
        assert "global" in data["breakers"]
        assert "is_any_triggered" in data


# =============================================================================
# TransitionError Tests
# =============================================================================


class TestTransitionError:
    """转换错误测试."""

    def test_transition_error_message(self) -> None:
        """测试错误消息."""
        error = TransitionError("Test error message")
        assert str(error) == "Test error message"


# =============================================================================
# CircuitBreakerEvent Tests
# =============================================================================


class TestCircuitBreakerEvent:
    """事件常量测试."""

    def test_event_constants(self) -> None:
        """测试事件常量."""
        assert CircuitBreakerEvent.TRIGGER == "trigger"
        assert CircuitBreakerEvent.COOLING_START == "cooling_start"
        assert CircuitBreakerEvent.COOLING_COMPLETE == "cooling_complete"
        assert CircuitBreakerEvent.RECOVERY_STEP == "recovery_step"
        assert CircuitBreakerEvent.RECOVERY_COMPLETE == "recovery_complete"
        assert CircuitBreakerEvent.MANUAL_OVERRIDE == "manual_override"
        assert CircuitBreakerEvent.MANUAL_RELEASE == "manual_release"
        assert CircuitBreakerEvent.MANUAL_TO_COOLING == "manual_to_cooling"


# =============================================================================
# Full State Machine Cycle Tests
# =============================================================================


class TestFullStateMachineCycle:
    """完整状态机周期测试."""

    def test_full_trigger_recovery_cycle(
        self,
        mock_time: MagicMock,
        audit_logger: DefaultAuditLogger,
    ) -> None:
        """测试完整的触发-恢复周期."""
        cb = CircuitBreaker(audit_logger=audit_logger, time_func=mock_time)

        # 1. 触发熔断
        metrics = CircuitBreakerMetrics(daily_loss_pct=0.05)
        cb.trigger(metrics)
        assert cb.state == CircuitBreakerState.TRIGGERED

        # 2. 等待30秒进入冷却
        mock_time.return_value = 1030.0
        cb.tick()
        assert cb.state == CircuitBreakerState.COOLING

        # 3. 等待5分钟进入恢复
        mock_time.return_value = 1330.0
        cb.tick()
        assert cb.state == CircuitBreakerState.RECOVERY

        # 4. 渐进恢复4步
        for i, expected_ratio in enumerate([0.5, 0.75, 1.0]):
            mock_time.return_value = 1330.0 + 60.0 * (i + 1)
            cb.tick()
            if i < 2:
                assert cb.state == CircuitBreakerState.RECOVERY
                assert cb.current_position_ratio == expected_ratio
            else:
                assert cb.state == CircuitBreakerState.NORMAL

        # 5. 验证审计日志完整
        assert len(audit_logger.records) >= 5  # 初始化 + 多次转换

    def test_manual_intervention_cycle(
        self,
        mock_time: MagicMock,
        audit_logger: DefaultAuditLogger,
    ) -> None:
        """测试人工干预周期."""
        cb = CircuitBreaker(audit_logger=audit_logger, time_func=mock_time)

        # 1. 人工接管
        cb.manual_override("紧急情况")
        assert cb.state == CircuitBreakerState.MANUAL_OVERRIDE

        # 2. 人工解除到冷却
        cb.manual_release(to_normal=False)
        assert cb.state == CircuitBreakerState.COOLING

        # 3. 等待5分钟进入恢复
        mock_time.return_value = 1300.0
        cb.tick()
        assert cb.state == CircuitBreakerState.RECOVERY

    def test_multiple_triggers_blocked(
        self,
        mock_time: MagicMock,
    ) -> None:
        """测试非NORMAL状态下多次触发被阻止."""
        cb = CircuitBreaker(time_func=mock_time)

        # 第一次触发成功
        metrics = CircuitBreakerMetrics(daily_loss_pct=0.05)
        assert cb.trigger(metrics) is True

        # 后续触发失败
        assert cb.trigger(metrics) is False
        assert cb.trigger(metrics) is False


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCasesAndErrorHandling:
    """边界情况和错误处理测试."""

    def test_recovery_with_no_steps_configured(self, mock_time: MagicMock) -> None:
        """测试配置为空步骤的恢复."""
        config = RecoveryConfig(position_ratio_steps=(1.0,))
        cb = CircuitBreaker(recovery_config=config, time_func=mock_time)

        cb.force_state(CircuitBreakerState.RECOVERY)
        cb._recovery_progress.step_start_time = 1000.0
        cb._recovery_progress.current_step = 0
        cb._recovery_progress.current_position_ratio = 1.0
        cb._recovery_progress.total_steps = 1

        mock_time.return_value = 1060.0
        cb.tick()
        assert cb.state == CircuitBreakerState.NORMAL

    def test_thresholds_boundary_values(self, mock_time: MagicMock) -> None:
        """测试阈值边界值."""
        cb = CircuitBreaker(time_func=mock_time)

        # 正好等于阈值不应触发
        metrics = CircuitBreakerMetrics(
            daily_loss_pct=0.03,  # 正好等于阈值
            consecutive_losses=4,  # 小于阈值
        )
        result = cb.check_trigger_conditions(metrics)
        assert result.should_trigger is False

        # 刚好超过阈值应触发
        metrics = CircuitBreakerMetrics(
            daily_loss_pct=0.031,  # 刚超过阈值
        )
        result = cb.check_trigger_conditions(metrics)
        assert result.should_trigger is True

    def test_consecutive_losses_boundary(self, mock_time: MagicMock) -> None:
        """测试连续亏损边界值."""
        cb = CircuitBreaker(time_func=mock_time)

        # 4次不触发
        metrics = CircuitBreakerMetrics(consecutive_losses=4)
        result = cb.check_trigger_conditions(metrics)
        assert result.should_trigger is False

        # 5次触发
        metrics = CircuitBreakerMetrics(consecutive_losses=5)
        result = cb.check_trigger_conditions(metrics)
        assert result.should_trigger is True


# =============================================================================
# Integration with Existing Guardian System Tests
# =============================================================================


class TestIntegrationWithGuardianSystem:
    """与现有Guardian系统集成测试."""

    def test_circuit_breaker_state_vs_guardian_mode(self) -> None:
        """测试熔断器状态与Guardian模式的对应关系."""
        # CircuitBreakerState 是独立的5状态设计
        # 与 GuardianMode 分开使用
        assert CircuitBreakerState.NORMAL.value == 0
        assert CircuitBreakerState.TRIGGERED.value == 1
        assert CircuitBreakerState.COOLING.value == 2
        assert CircuitBreakerState.RECOVERY.value == 3
        assert CircuitBreakerState.MANUAL_OVERRIDE.value == 4

    def test_custom_audit_logger_protocol(self, mock_time: MagicMock) -> None:
        """测试自定义审计日志协议."""

        class CustomLogger:
            def __init__(self) -> None:
                self.logs: list[dict[str, Any]] = []

            def log(
                self,
                event_type: str,
                from_state: str,
                to_state: str,
                trigger_reason: str,
                details: dict[str, Any],
            ) -> None:
                self.logs.append(
                    {
                        "event_type": event_type,
                        "from_state": from_state,
                        "to_state": to_state,
                    }
                )

        custom_logger = CustomLogger()
        cb = CircuitBreaker(audit_logger=custom_logger, time_func=mock_time)  # type: ignore
        cb.manual_override("test")

        assert len(custom_logger.logs) > 0
