"""策略生命周期管理器测试 (军规级 v4.2).

测试覆盖:
- M18: 实验性门禁 - 未成熟策略禁止实盘启用
- M12: 双重确认 - 大额调整需人工审批
- M19: 风险归因 - 策略表现追踪

场景覆盖:
- LIFECYCLE.REGISTER: 策略注册
- LIFECYCLE.MATURITY: 成熟度更新
- LIFECYCLE.ALLOCATION: 资金分配
- LIFECYCLE.TRANSITION: 状态转换
- LIFECYCLE.APPROVAL: 人工审批
"""

from __future__ import annotations

import pytest

from src.strategy.experimental.strategy_lifecycle import (
    ALLOCATION_CONFIGS,
    AllocationTier,
    LifecycleStage,
    StrategyLifecycleManager,
    StrategyState,
    TransitionEvent,
    create_lifecycle_manager,
    get_allocation_for_maturity,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def manager() -> StrategyLifecycleManager:
    """创建默认管理器."""
    return StrategyLifecycleManager()


@pytest.fixture
def manager_no_auto() -> StrategyLifecycleManager:
    """创建禁用自动转换的管理器."""
    return StrategyLifecycleManager(auto_transition=False)


@pytest.fixture
def manager_no_approval() -> StrategyLifecycleManager:
    """创建不需要审批的管理器."""
    return StrategyLifecycleManager(require_approval_for_production=False)


# ============================================================
# 初始化测试
# ============================================================


class TestLifecycleManagerInit:
    """管理器初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        manager = StrategyLifecycleManager()
        stats = manager.get_statistics()
        assert stats["total_strategies"] == 0
        assert stats["total_promotions"] == 0
        assert stats["total_demotions"] == 0

    def test_custom_init(self) -> None:
        """测试自定义初始化."""
        manager = StrategyLifecycleManager(
            auto_transition=False,
            require_approval_for_production=False,
        )
        assert manager._auto_transition is False
        assert manager._require_approval_for_production is False


# ============================================================
# 策略注册测试
# ============================================================


class TestStrategyRegistration:
    """策略注册测试."""

    def test_register_strategy(self, manager: StrategyLifecycleManager) -> None:
        """测试注册策略."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")

        assert state.strategy_id == "ppo_v1"
        assert state.strategy_name == "PPO策略"
        assert state.strategy_type == "rl"
        assert state.stage == LifecycleStage.INCUBATION
        assert state.allocation_tier == AllocationTier.ZERO

    def test_register_duplicate_returns_existing(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试重复注册返回现有策略."""
        state1 = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state2 = manager.register_strategy("ppo_v1", "不同名称", "dl")

        assert state1 is state2
        assert state2.strategy_name == "PPO策略"  # 保持原名

    def test_unregister_strategy(self, manager: StrategyLifecycleManager) -> None:
        """测试注销策略."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        assert manager.get_strategy("ppo_v1") is not None

        result = manager.unregister_strategy("ppo_v1")
        assert result is True
        assert manager.get_strategy("ppo_v1") is None

    def test_get_all_strategies(self, manager: StrategyLifecycleManager) -> None:
        """测试获取所有策略."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        manager.register_strategy("lstm_v1", "LSTM策略", "dl")
        manager.register_strategy("stat_v1", "统计策略", "statistical")

        strategies = manager.get_all_strategies()
        assert len(strategies) == 3


# ============================================================
# 成熟度更新测试
# ============================================================


class TestMaturityUpdate:
    """成熟度更新测试."""

    def test_update_maturity_basic(
        self, manager_no_auto: StrategyLifecycleManager
    ) -> None:
        """测试基本成熟度更新."""
        manager_no_auto.register_strategy("ppo_v1", "PPO策略", "rl")
        manager_no_auto.update_maturity("ppo_v1", 0.75)

        state = manager_no_auto.get_strategy("ppo_v1")
        assert state is not None
        assert state.maturity_pct == 0.75

    def test_update_maturity_clamped(
        self, manager_no_auto: StrategyLifecycleManager
    ) -> None:
        """测试成熟度被钳制在0-1范围."""
        manager_no_auto.register_strategy("ppo_v1", "PPO策略", "rl")

        manager_no_auto.update_maturity("ppo_v1", 1.5)
        state = manager_no_auto.get_strategy("ppo_v1")
        assert state is not None
        assert state.maturity_pct == 1.0

        manager_no_auto.update_maturity("ppo_v1", -0.5)
        assert state.maturity_pct == 0.0

    def test_update_maturity_triggers_transition(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试成熟度更新触发自动转换."""
        manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")

        # 更新到80%以上应触发转换
        _ = manager_no_approval.update_maturity("ppo_v1", 0.85)

        # 应从孵化期转到发展期
        state = manager_no_approval.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage in [LifecycleStage.DEVELOPMENT, LifecycleStage.VALIDATION]


# ============================================================
# 资金分配测试
# ============================================================


class TestAllocation:
    """资金分配测试."""

    def test_incubation_zero_allocation(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试孵化期零分配."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.allowed is False
        assert allocation.config.max_capital_pct == 0.0

    def test_validation_trial_allocation(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试验证期试运行分配."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.allocation_tier = AllocationTier.TRIAL

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.allowed is True
        assert allocation.config.max_capital_pct == 0.05

    def test_production_normal_allocation(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试生产期正常分配."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.PRODUCTION
        state.allocation_tier = AllocationTier.NORMAL

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.allowed is True
        assert allocation.config.max_capital_pct == 0.20

    def test_unregistered_strategy_no_allocation(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试未注册策略无分配."""
        allocation = manager.get_allocation("nonexistent")
        assert allocation.allowed is False
        assert "未注册" in allocation.reason

    def test_allocation_enhanced_for_high_performance(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试高表现策略增强分配."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.PRODUCTION
        state.allocation_tier = AllocationTier.NORMAL
        state.maturity_pct = 0.95
        state.performance.sharpe_ratio = 2.0

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.config.tier == AllocationTier.MAXIMUM


# ============================================================
# 状态转换测试
# ============================================================


class TestStateTransition:
    """状态转换测试."""

    def test_auto_promotion_incubation_to_development(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试自动晋升: 孵化期到发展期."""
        manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")

        _ = manager_no_approval.update_maturity("ppo_v1", 0.85)

        state = manager_no_approval.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage in [LifecycleStage.DEVELOPMENT, LifecycleStage.VALIDATION]
        assert state.promotion_count >= 1

    def test_demotion_on_poor_performance(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试表现不佳时降级."""
        state = manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.PRODUCTION
        state.allocation_tier = AllocationTier.NORMAL

        # 更新差表现
        _ = manager_no_approval.update_performance(
            "ppo_v1",
            sharpe_ratio=0.3,
            max_drawdown=0.18,
        )

        state = manager_no_approval.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.DEGRADED

    def test_suspension_on_severe_drawdown(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试严重回撤时暂停."""
        state = manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.PRODUCTION
        state.allocation_tier = AllocationTier.NORMAL

        # 更新严重回撤
        manager_no_approval.update_performance(
            "ppo_v1",
            max_drawdown=0.30,
        )

        state = manager_no_approval.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.SUSPENDED
        assert state.allocation_tier == AllocationTier.ZERO

    def test_recovery_from_degraded(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试从降级期恢复."""
        state = manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.DEGRADED
        state.allocation_tier = AllocationTier.MINIMAL

        # 更新好表现
        manager_no_approval.update_performance(
            "ppo_v1",
            sharpe_ratio=1.5,
            max_drawdown=0.08,
        )

        state = manager_no_approval.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.VALIDATION


# ============================================================
# 人工审批测试
# ============================================================


class TestManualApproval:
    """人工审批测试."""

    def test_pending_transition_for_production(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试进入生产期需要审批."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.maturity_pct = 0.90
        state.performance.sharpe_ratio = 1.5
        state.performance.win_rate = 0.55
        state.performance.max_drawdown = 0.08

        # 触发转换检查
        manager._check_and_transition("ppo_v1", "test")

        # 应该有待审批转换
        pending = manager.get_pending_transitions()
        assert len(pending) == 1
        assert pending[0].strategy_id == "ppo_v1"

    def test_approve_transition(self, manager: StrategyLifecycleManager) -> None:
        """测试批准转换."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.maturity_pct = 0.90
        state.performance.sharpe_ratio = 1.5
        state.performance.win_rate = 0.55
        state.performance.max_drawdown = 0.08

        # 触发并审批
        manager._check_and_transition("ppo_v1", "test")
        event = manager.approve_transition("ppo_v1", "CLAUDE上校")

        assert event is not None
        assert event.approved_by == "CLAUDE上校"

        state = manager.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.PRODUCTION

    def test_reject_transition(self, manager: StrategyLifecycleManager) -> None:
        """测试拒绝转换."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.maturity_pct = 0.90
        state.performance.sharpe_ratio = 1.5
        state.performance.win_rate = 0.55
        state.performance.max_drawdown = 0.08

        # 触发并拒绝
        manager._check_and_transition("ppo_v1", "test")
        result = manager.reject_transition("ppo_v1", "审核员", "风险过高")

        assert result is True
        assert len(manager.get_pending_transitions()) == 0

        state = manager.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.VALIDATION  # 保持不变


# ============================================================
# 回调测试
# ============================================================


class TestCallbacks:
    """回调测试."""

    def test_transition_callback(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试转换回调."""
        received_events: list[TransitionEvent] = []

        def callback(event: TransitionEvent) -> None:
            received_events.append(event)

        manager_no_approval.register_transition_callback(callback)
        manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")
        manager_no_approval.update_maturity("ppo_v1", 0.85)

        assert len(received_events) >= 1

    def test_alert_callback(self, manager: StrategyLifecycleManager) -> None:
        """测试告警回调."""
        received_alerts: list[tuple[str, str]] = []

        def callback(strategy_id: str, message: str) -> None:
            received_alerts.append((strategy_id, message))

        manager.register_alert_callback(callback)

        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.maturity_pct = 0.90
        state.performance.sharpe_ratio = 1.5
        state.performance.win_rate = 0.55
        state.performance.max_drawdown = 0.08

        # 触发需要审批的转换
        manager._check_and_transition("ppo_v1", "test")

        assert len(received_alerts) >= 1

    def test_callback_error_ignored(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试回调错误被忽略."""

        def bad_callback(event: TransitionEvent) -> None:
            raise ValueError("Test error")

        manager_no_approval.register_transition_callback(bad_callback)
        manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")

        # 不应抛出异常
        manager_no_approval.update_maturity("ppo_v1", 0.85)


# ============================================================
# 统计测试
# ============================================================


class TestStatistics:
    """统计测试."""

    def test_get_statistics(self, manager: StrategyLifecycleManager) -> None:
        """测试获取统计信息."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        manager.register_strategy("lstm_v1", "LSTM策略", "dl")

        stats = manager.get_statistics()
        assert stats["total_strategies"] == 2
        assert "stage_distribution" in stats
        assert "tier_distribution" in stats

    def test_get_strategies_by_stage(self, manager: StrategyLifecycleManager) -> None:
        """测试按阶段获取策略."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        manager.register_strategy("lstm_v1", "LSTM策略", "dl")

        state2 = manager.get_strategy("lstm_v1")
        assert state2 is not None
        state2.stage = LifecycleStage.VALIDATION

        incubation = manager.get_strategies_by_stage(LifecycleStage.INCUBATION)
        validation = manager.get_strategies_by_stage(LifecycleStage.VALIDATION)

        assert len(incubation) == 1
        assert len(validation) == 1

    def test_get_transition_history(
        self, manager_no_approval: StrategyLifecycleManager
    ) -> None:
        """测试获取转换历史."""
        manager_no_approval.register_strategy("ppo_v1", "PPO策略", "rl")
        manager_no_approval.update_maturity("ppo_v1", 0.85)

        history = manager_no_approval.get_transition_history("ppo_v1")
        assert len(history) >= 1

    def test_reset(self, manager: StrategyLifecycleManager) -> None:
        """测试重置."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        assert manager.get_statistics()["total_strategies"] == 1

        manager.reset()
        assert manager.get_statistics()["total_strategies"] == 0


# ============================================================
# 数据类测试
# ============================================================


class TestDataClasses:
    """数据类测试."""

    def test_strategy_state_to_audit_dict(self) -> None:
        """测试策略状态转审计字典."""
        state = StrategyState(
            strategy_id="ppo_v1",
            strategy_name="PPO策略",
            strategy_type="rl",
            stage=LifecycleStage.VALIDATION,
            allocation_tier=AllocationTier.TRIAL,
            maturity_pct=0.75,
        )

        audit = state.to_audit_dict()
        assert audit["event_type"] == "STRATEGY_STATE"
        assert audit["strategy_id"] == "ppo_v1"
        assert audit["stage"] == "验证期"
        assert audit["allocation_tier"] == "试运行"

    def test_transition_event_to_audit_dict(self) -> None:
        """测试转换事件转审计字典."""
        event = TransitionEvent(
            strategy_id="ppo_v1",
            from_stage=LifecycleStage.INCUBATION,
            to_stage=LifecycleStage.DEVELOPMENT,
            from_tier=AllocationTier.ZERO,
            to_tier=AllocationTier.ZERO,
            reason="成熟度达标",
            triggered_by="auto",
        )

        audit = event.to_audit_dict()
        assert audit["event_type"] == "STRATEGY_TRANSITION"
        assert audit["from_stage"] == "孵化期"
        assert audit["to_stage"] == "发展期"


class TestAllocationConfig:
    """分配配置测试."""

    def test_allocation_configs_exist(self) -> None:
        """测试分配配置存在."""
        for tier in AllocationTier:
            assert tier in ALLOCATION_CONFIGS

    def test_allocation_tiers_ordered(self) -> None:
        """测试分配等级有序."""
        tiers = [
            AllocationTier.ZERO,
            AllocationTier.TRIAL,
            AllocationTier.MINIMAL,
            AllocationTier.NORMAL,
            AllocationTier.ENHANCED,
            AllocationTier.MAXIMUM,
        ]

        prev_pct = 0.0
        for tier in tiers:
            config = ALLOCATION_CONFIGS[tier]
            assert config.max_capital_pct >= prev_pct
            prev_pct = config.max_capital_pct


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_lifecycle_manager(self) -> None:
        """测试创建管理器."""
        manager = create_lifecycle_manager(auto_transition=False)
        assert manager._auto_transition is False

    def test_get_allocation_for_maturity(self) -> None:
        """测试根据成熟度获取分配."""
        # 低成熟度
        config = get_allocation_for_maturity(0.30)
        assert config.tier == AllocationTier.ZERO

        # 中成熟度
        config = get_allocation_for_maturity(0.70)
        assert config.tier == AllocationTier.TRIAL

        # 高成熟度
        config = get_allocation_for_maturity(0.85)
        assert config.tier == AllocationTier.NORMAL

        # 极高成熟度
        config = get_allocation_for_maturity(0.98)
        assert config.tier == AllocationTier.MAXIMUM


# ============================================================
# 军规测试
# ============================================================


class TestM18ExperimentalGate:
    """M18军规测试: 实验性门禁."""

    def test_immature_strategy_no_allocation(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试未成熟策略无资金分配."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")
        manager.update_maturity("ppo_v1", 0.50)  # 50%成熟度

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.config.max_capital_pct == 0.0

    def test_incubation_stage_blocked(self, manager: StrategyLifecycleManager) -> None:
        """测试孵化期策略被阻止."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        assert state.stage == LifecycleStage.INCUBATION

        allocation = manager.get_allocation("ppo_v1")
        assert allocation.allowed is False


class TestM12DoubleConfirm:
    """M12军规测试: 双重确认."""

    def test_production_requires_approval(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试进入生产期需要人工审批."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.stage = LifecycleStage.VALIDATION
        state.maturity_pct = 0.90
        state.performance.sharpe_ratio = 1.5
        state.performance.win_rate = 0.55
        state.performance.max_drawdown = 0.08

        # 触发转换
        manager._check_and_transition("ppo_v1", "test")

        # 应该在待审批列表
        pending = manager.get_pending_transitions()
        assert len(pending) == 1

        # 状态应未变
        state = manager.get_strategy("ppo_v1")
        assert state is not None
        assert state.stage == LifecycleStage.VALIDATION


class TestM19RiskAttribution:
    """M19军规测试: 风险归因."""

    def test_performance_tracking(self, manager: StrategyLifecycleManager) -> None:
        """测试策略表现追踪."""
        manager.register_strategy("ppo_v1", "PPO策略", "rl")

        manager.update_performance(
            "ppo_v1",
            sharpe_ratio=1.5,
            max_drawdown=0.10,
            win_rate=0.55,
            profit_factor=1.8,
        )

        state = manager.get_strategy("ppo_v1")
        assert state is not None
        assert state.performance.sharpe_ratio == 1.5
        assert state.performance.max_drawdown == 0.10

    def test_audit_dict_includes_performance(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试审计字典包含表现数据."""
        state = manager.register_strategy("ppo_v1", "PPO策略", "rl")
        state.performance.sharpe_ratio = 1.5
        state.performance.max_drawdown = 0.10

        audit = state.to_audit_dict()
        assert "sharpe_ratio" in audit
        assert "max_drawdown" in audit


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_update_nonexistent_strategy(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试更新不存在的策略."""
        result = manager.update_maturity("nonexistent", 0.5)
        assert result is None

    def test_approve_nonexistent_pending(
        self, manager: StrategyLifecycleManager
    ) -> None:
        """测试批准不存在的待审批."""
        result = manager.approve_transition("nonexistent", "approver")
        assert result is None

    def test_unregister_nonexistent(self, manager: StrategyLifecycleManager) -> None:
        """测试注销不存在的策略."""
        result = manager.unregister_strategy("nonexistent")
        assert result is False

    def test_empty_transition_history(self, manager: StrategyLifecycleManager) -> None:
        """测试空转换历史."""
        history = manager.get_transition_history("ppo_v1")
        assert history == []
