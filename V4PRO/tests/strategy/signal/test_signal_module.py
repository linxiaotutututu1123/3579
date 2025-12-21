"""
信号模块测试套件 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制测试
测试覆盖: M1, M3, M7 军规

测试场景:
- SIGNAL.SOURCE.CREATE: 信号源创建
- SIGNAL.SOURCE.UNIQUE_ID: 信号源唯一ID
- SIGNAL.CREATE: 信号创建
- SIGNAL.VALIDATE: 信号验证
- SIGNAL.REGISTRY: 信号源注册
- SIGNAL.CONFLICT: 冲突检测与解决
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from src.strategy.signal import (
    ConflictInfo,
    ConflictSeverity,
    ConflictType,
    ResolutionResult,
    ResolutionStrategy,
    SignalConflictResolver,
    SignalDirection,
    SignalPriority,
    SignalSource,
    SignalSourceID,
    SignalSourceRegistry,
    SignalType,
    SignalValidator,
    SourceStatus,
    TradingSignal,
    ValidationErrorCode,
    ValidationResult,
    create_conflict_resolver,
    create_signal_source,
    create_validator,
    generate_source_id,
    get_registry,
    register_source,
    resolve_conflicts,
    unregister_source,
)


# ============================================================
# SignalSourceID 测试
# ============================================================


class TestSignalSourceID:
    """信号源ID测试类."""

    def test_generate_creates_unique_id(self) -> None:
        """测试: 生成唯一信号源ID."""
        id1 = generate_source_id("strategy_a", "inst_001")
        id2 = generate_source_id("strategy_a", "inst_001")

        # 即使相同策略和实例，nonce也应不同
        assert id1.full_id != id2.full_id
        assert id1.strategy_id == id2.strategy_id
        assert id1.instance_id == id2.instance_id
        assert id1.nonce != id2.nonce

    def test_full_id_format(self) -> None:
        """测试: 完整ID格式."""
        source_id = generate_source_id("kalman_arb", "inst_001")

        assert source_id.full_id.startswith("kalman_arb:inst_001:")
        assert len(source_id.full_id.split(":")) == 3

    def test_to_dict(self) -> None:
        """测试: 转换为字典."""
        source_id = generate_source_id("test_strategy", "test_instance")
        data = source_id.to_dict()

        assert "strategy_id" in data
        assert "instance_id" in data
        assert "nonce" in data
        assert "created_at" in data
        assert "full_id" in data


# ============================================================
# SignalSource 测试
# ============================================================


class TestSignalSource:
    """信号源测试类."""

    def test_create_signal_source(self) -> None:
        """测试: 创建信号源."""
        source = create_signal_source("kalman_arb", "inst_001")

        assert source.strategy_id == "kalman_arb"
        assert source.instance_id == "inst_001"
        assert source.is_active()
        assert source.signal_counter == 0

    def test_source_unique_id(self) -> None:
        """测试: M1军规 - 信号源唯一ID."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_a")

        # 即使相同策略，信号源ID也应唯一
        assert source1.full_source_id != source2.full_source_id

    def test_create_signal(self) -> None:
        """测试: 创建交易信号."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        assert signal.source_id == source.full_source_id
        assert signal.symbol == "rb2501"
        assert signal.direction == SignalDirection.LONG
        assert signal.strength == 0.8
        assert signal.confidence == 0.9
        assert not signal.is_expired()

    def test_signal_signature_verification(self) -> None:
        """测试: M1军规 - 信号签名验证."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        # 验证签名
        assert source.verify_signal(signal)

        # 创建另一个源，不应能验证
        other_source = create_signal_source("other_strategy")
        assert not other_source.verify_signal(signal)

    def test_signal_expiration(self) -> None:
        """测试: 信号过期."""
        source = create_signal_source("kalman_arb", signal_ttl=0.1)
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        assert not signal.is_expired()
        time.sleep(0.15)
        assert signal.is_expired()

    def test_source_status_lifecycle(self) -> None:
        """测试: 信号源状态生命周期."""
        source = create_signal_source("kalman_arb")

        assert source.status == SourceStatus.ACTIVE
        assert source.is_active()

        source.suspend()
        assert source.status == SourceStatus.SUSPENDED
        assert not source.is_active()

        source.activate()
        assert source.status == SourceStatus.ACTIVE
        assert source.is_active()

        source.disable()
        assert source.status == SourceStatus.DISABLED
        assert not source.is_active()

    def test_inactive_source_cannot_create_signal(self) -> None:
        """测试: 非活跃信号源不能创建信号."""
        source = create_signal_source("kalman_arb")
        source.suspend()

        with pytest.raises(ValueError, match="not active"):
            source.create_signal(
                symbol="rb2501",
                direction=SignalDirection.LONG,
                strength=0.8,
                confidence=0.9,
            )

    def test_signal_counter_increments(self) -> None:
        """测试: 信号计数器递增."""
        source = create_signal_source("kalman_arb")

        assert source.signal_counter == 0

        source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        assert source.signal_counter == 1

        source.create_signal(
            symbol="rb2502",
            direction=SignalDirection.SHORT,
            strength=0.7,
            confidence=0.85,
        )
        assert source.signal_counter == 2


# ============================================================
# SignalValidator 测试
# ============================================================


class TestSignalValidator:
    """信号验证器测试类."""

    def test_validate_valid_signal(self) -> None:
        """测试: 验证有效信号."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        validator = create_validator()
        validator.register_source(source)

        result = validator.validate(signal)
        assert result.is_valid
        assert result.error_code == ValidationErrorCode.NONE

    def test_validate_unregistered_source(self) -> None:
        """测试: M1军规 - 验证未注册的信号源."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        validator = create_validator()
        # 未注册信号源

        result = validator.validate(signal)
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.SOURCE_NOT_REGISTERED

    def test_validate_expired_signal(self) -> None:
        """测试: 验证过期信号."""
        source = create_signal_source("kalman_arb", signal_ttl=0.1)
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        validator = create_validator()
        validator.register_source(source)

        time.sleep(0.15)
        result = validator.validate(signal)
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.SIGNAL_EXPIRED

    def test_validate_duplicate_signal(self) -> None:
        """测试: 验证重复信号."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        validator = create_validator()
        validator.register_source(source)

        # 第一次验证通过
        result1 = validator.validate(signal)
        assert result1.is_valid

        # 第二次验证应检测为重复
        result2 = validator.validate(signal)
        assert not result2.is_valid
        assert result2.error_code == ValidationErrorCode.DUPLICATE_SIGNAL

    def test_validate_inactive_source(self) -> None:
        """测试: 验证非活跃信号源的信号."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        validator = create_validator()
        validator.register_source(source)

        # 暂停信号源
        source.suspend()

        result = validator.validate(signal)
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.SOURCE_INACTIVE

    def test_validate_invalid_signature(self) -> None:
        """测试: M1军规 - 验证无效签名."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        # 创建另一个源并注册
        other_source = create_signal_source("kalman_arb", "inst_001")
        other_source.source_id = source.source_id  # 伪造源ID

        validator = create_validator()
        validator.register_source(other_source)

        # 签名验证应失败
        result = validator.validate(signal, strict_mode=True)
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.INVALID_SIGNATURE

    def test_validation_statistics(self) -> None:
        """测试: 验证统计信息."""
        source = create_signal_source("kalman_arb", "inst_001")
        validator = create_validator()
        validator.register_source(source)

        # 创建几个信号进行验证
        for i in range(5):
            signal = source.create_signal(
                symbol=f"rb250{i}",
                direction=SignalDirection.LONG,
                strength=0.8,
                confidence=0.9,
            )
            validator.validate(signal)

        stats = validator.get_validation_statistics()
        assert stats["total_validations"] == 5
        assert stats["passed"] == 5
        assert stats["pass_rate"] == 1.0


# ============================================================
# SignalSourceRegistry 测试
# ============================================================


class TestSignalSourceRegistry:
    """信号源注册表测试类."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """每个测试前重置注册表."""
        SignalSourceRegistry.reset_instance()

    def test_singleton_pattern(self) -> None:
        """测试: 单例模式."""
        registry1 = SignalSourceRegistry.get_instance()
        registry2 = SignalSourceRegistry.get_instance()

        assert registry1 is registry2

    def test_register_source(self) -> None:
        """测试: 注册信号源."""
        registry = get_registry()
        source = create_signal_source("kalman_arb", "inst_001")

        assert registry.register(source)
        assert registry.is_registered(source.full_source_id)
        assert registry.source_count == 1

    def test_unregister_source(self) -> None:
        """测试: 注销信号源."""
        registry = get_registry()
        source = create_signal_source("kalman_arb", "inst_001")

        registry.register(source)
        assert registry.source_count == 1

        assert registry.unregister(source.full_source_id)
        assert not registry.is_registered(source.full_source_id)
        assert registry.source_count == 0

    def test_get_source(self) -> None:
        """测试: 获取信号源."""
        registry = get_registry()
        source = create_signal_source("kalman_arb", "inst_001")
        registry.register(source)

        retrieved = registry.get_source(source.full_source_id)
        assert retrieved is source

    def test_get_sources_by_strategy(self) -> None:
        """测试: 按策略获取信号源."""
        registry = get_registry()

        source1 = create_signal_source("kalman_arb", "inst_001")
        source2 = create_signal_source("kalman_arb", "inst_002")
        source3 = create_signal_source("lstm_trend", "inst_001")

        registry.register(source1)
        registry.register(source2)
        registry.register(source3)

        kalman_sources = registry.get_sources_by_strategy("kalman_arb")
        assert len(kalman_sources) == 2

        lstm_sources = registry.get_sources_by_strategy("lstm_trend")
        assert len(lstm_sources) == 1

    def test_activate_suspend_source(self) -> None:
        """测试: 激活和暂停信号源."""
        registry = get_registry()
        source = create_signal_source("kalman_arb", "inst_001")
        registry.register(source)

        assert registry.is_active(source.full_source_id)

        registry.suspend(source.full_source_id)
        assert not registry.is_active(source.full_source_id)

        registry.activate(source.full_source_id)
        assert registry.is_active(source.full_source_id)

    def test_get_active_sources(self) -> None:
        """测试: 获取活跃信号源."""
        registry = get_registry()

        source1 = create_signal_source("kalman_arb", "inst_001")
        source2 = create_signal_source("lstm_trend", "inst_001")

        registry.register(source1)
        registry.register(source2)

        assert registry.active_source_count == 2

        registry.suspend(source1.full_source_id)
        assert registry.active_source_count == 1

        active_sources = registry.get_active_sources()
        assert len(active_sources) == 1
        assert active_sources[0].strategy_id == "lstm_trend"

    def test_registry_events(self) -> None:
        """测试: 注册表事件."""
        registry = get_registry()
        source = create_signal_source("kalman_arb", "inst_001")

        events_received: list = []
        registry.register_callback(lambda e: events_received.append(e))

        registry.register(source)
        registry.suspend(source.full_source_id)
        registry.activate(source.full_source_id)
        registry.unregister(source.full_source_id)

        assert len(events_received) == 4

    def test_convenience_functions(self) -> None:
        """测试: 便捷函数."""
        source = create_signal_source("kalman_arb", "inst_001")

        assert register_source(source)
        assert get_registry().is_registered(source.full_source_id)

        retrieved = get_registry().get_source(source.full_source_id)
        assert retrieved is source

        assert unregister_source(source.full_source_id)
        assert not get_registry().is_registered(source.full_source_id)


# ============================================================
# SignalConflictResolver 测试
# ============================================================


class TestSignalConflictResolver:
    """信号冲突解决器测试类."""

    def test_detect_direction_conflict(self) -> None:
        """测试: M1军规 - 检测方向冲突."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal_long = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        signal_short = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.7,
            confidence=0.85,
        )

        resolver = create_conflict_resolver()
        conflicts = resolver.detect_conflicts([signal_long, signal_short])

        assert len(conflicts) > 0
        assert conflicts[0].conflict_type == ConflictType.DIRECTION_CONFLICT

    def test_detect_source_duplicate(self) -> None:
        """测试: 检测同源重复信号."""
        source = create_signal_source("strategy_a")

        signal1 = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        signal2 = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.75,
            confidence=0.85,
        )

        resolver = create_conflict_resolver()
        conflicts = resolver.detect_conflicts([signal1, signal2])

        source_duplicates = [
            c for c in conflicts
            if c.conflict_type == ConflictType.SOURCE_DUPLICATE
        ]
        assert len(source_duplicates) > 0

    def test_resolve_by_priority(self) -> None:
        """测试: M1军规 - 按优先级解决冲突."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal_high = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
            priority=SignalPriority.HIGH,
        )
        signal_normal = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.9,
            confidence=0.95,
            priority=SignalPriority.NORMAL,
        )

        resolver = create_conflict_resolver(strategy=ResolutionStrategy.PRIORITY_FIRST)
        result = resolver.resolve([signal_high, signal_normal])

        assert result.resolved
        assert result.winner_signal is signal_high

    def test_resolve_by_confidence(self) -> None:
        """测试: 按置信度解决冲突."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal_low_conf = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.9,
            confidence=0.7,
        )
        signal_high_conf = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.7,
            confidence=0.95,
        )

        resolver = create_conflict_resolver(strategy=ResolutionStrategy.CONFIDENCE_WEIGHTED)
        result = resolver.resolve([signal_low_conf, signal_high_conf])

        assert result.resolved
        assert result.winner_signal is signal_high_conf

    def test_resolve_by_strength(self) -> None:
        """测试: 按强度解决冲突."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal_weak = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.5,
            confidence=0.9,
        )
        signal_strong = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.9,
            confidence=0.7,
        )

        resolver = create_conflict_resolver(strategy=ResolutionStrategy.STRENGTH_WEIGHTED)
        result = resolver.resolve([signal_weak, signal_strong])

        assert result.resolved
        assert result.winner_signal is signal_strong

    def test_reject_all_strategy(self) -> None:
        """测试: 全部拒绝策略."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal1 = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        signal2 = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.7,
            confidence=0.85,
        )

        resolver = create_conflict_resolver(strategy=ResolutionStrategy.REJECT_ALL)
        result = resolver.resolve([signal1, signal2])

        assert not result.resolved or result.winner_signal is None

    def test_convenience_resolve_function(self) -> None:
        """测试: 便捷解决函数."""
        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        signal1 = source1.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
            priority=SignalPriority.HIGH,
        )
        signal2 = source2.create_signal(
            symbol="rb2501",
            direction=SignalDirection.SHORT,
            strength=0.9,
            confidence=0.95,
            priority=SignalPriority.NORMAL,
        )

        winner = resolve_conflicts([signal1, signal2], ResolutionStrategy.PRIORITY_FIRST)
        assert winner is signal1

    def test_resolver_statistics(self) -> None:
        """测试: 解决器统计信息."""
        resolver = create_conflict_resolver()

        source1 = create_signal_source("strategy_a")
        source2 = create_signal_source("strategy_b")

        for i in range(3):
            signal1 = source1.create_signal(
                symbol=f"rb250{i}",
                direction=SignalDirection.LONG,
                strength=0.8,
                confidence=0.9,
            )
            signal2 = source2.create_signal(
                symbol=f"rb250{i}",
                direction=SignalDirection.SHORT,
                strength=0.7,
                confidence=0.85,
            )
            resolver.resolve([signal1, signal2])

        stats = resolver.get_statistics()
        assert stats["total_resolutions"] == 3
        assert stats["total_conflicts"] > 0


# ============================================================
# 集成测试
# ============================================================


class TestSignalModuleIntegration:
    """信号模块集成测试."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """每个测试前重置注册表."""
        SignalSourceRegistry.reset_instance()

    def test_full_signal_lifecycle(self) -> None:
        """测试: M1军规 - 完整信号生命周期."""
        # 1. 创建信号源
        source = create_signal_source("kalman_arb", "inst_001")

        # 2. 注册信号源
        registry = get_registry()
        registry.register(source)

        # 3. 创建验证器并注册源
        validator = create_validator()
        validator.register_source(source)

        # 4. 创建信号
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        # 5. 验证信号
        result = validator.validate(signal)
        assert result.is_valid

        # 6. 验证信号来源
        assert signal.source_id == source.full_source_id
        assert source.verify_signal(signal)

    def test_multi_source_conflict_resolution(self) -> None:
        """测试: M1军规 - 多信号源冲突解决."""
        # 创建多个信号源
        sources = [
            create_signal_source("kalman_arb", "inst_001"),
            create_signal_source("lstm_trend", "inst_001"),
            create_signal_source("moe_ensemble", "inst_001"),
        ]

        # 注册所有信号源
        registry = get_registry()
        validator = create_validator()
        for source in sources:
            registry.register(source)
            validator.register_source(source)

        # 创建冲突信号
        signals = [
            sources[0].create_signal(
                symbol="rb2501",
                direction=SignalDirection.LONG,
                strength=0.8,
                confidence=0.9,
                priority=SignalPriority.NORMAL,
            ),
            sources[1].create_signal(
                symbol="rb2501",
                direction=SignalDirection.SHORT,
                strength=0.7,
                confidence=0.85,
                priority=SignalPriority.HIGH,
            ),
            sources[2].create_signal(
                symbol="rb2501",
                direction=SignalDirection.LONG,
                strength=0.75,
                confidence=0.88,
                priority=SignalPriority.NORMAL,
            ),
        ]

        # 验证所有信号
        for signal in signals:
            result = validator.validate(signal)
            assert result.is_valid

        # 解决冲突
        resolver = create_conflict_resolver(strategy=ResolutionStrategy.PRIORITY_FIRST)
        result = resolver.resolve(signals)

        assert result.resolved
        assert result.winner_signal.source_id == sources[1].full_source_id

    def test_audit_trail(self) -> None:
        """测试: M3军规 - 审计追踪."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        # 生成审计记录
        source_audit = source.to_audit_record()
        signal_audit = signal.to_audit_record()

        # 验证审计记录包含必要信息
        assert "event_type" in source_audit
        assert "event_time" in source_audit
        assert "source_id" in source_audit

        assert "event_type" in signal_audit
        assert "signal_id" in signal_audit
        assert "source_id" in signal_audit
        assert "direction" in signal_audit

    def test_signal_replay_compatibility(self) -> None:
        """测试: M7军规 - 信号回放兼容性."""
        source = create_signal_source("kalman_arb", "inst_001")
        signal = source.create_signal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )

        # 转换为可序列化格式
        signal_dict = signal.to_dict()

        # 验证可序列化
        assert isinstance(signal_dict["signal_id"], str)
        assert isinstance(signal_dict["source_id"], str)
        assert isinstance(signal_dict["timestamp"], float)
        assert isinstance(signal_dict["direction"], str)
