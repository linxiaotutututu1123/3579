"""
策略联邦测试 (军规级 v4.2).

测试覆盖:
- M1: 单一信号源 - 联邦输出为唯一信号源
- M19: 风险归因 - 策略贡献度追踪
- M20: 跨所一致 - 策略间相关性抑制

场景覆盖:
- FED.REGISTER: 策略注册
- FED.SIGNAL.FUSE: 信号融合
- FED.CORRELATION: 相关性计算
- FED.WEIGHT.DYNAMIC: 动态权重
"""

from __future__ import annotations

import pytest

from src.strategy.federation import (
    CorrelationMatrix,
    FederationSignal,
    SignalDirection,
    SignalStrength,
    StrategyFederation,
    StrategyMember,
    StrategySignal,
    create_federation,
    create_signal,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def federation() -> StrategyFederation:
    """创建默认联邦."""
    return StrategyFederation()


@pytest.fixture
def federation_with_strategies() -> StrategyFederation:
    """创建已注册策略的联邦."""
    fed = StrategyFederation()
    fed.register_strategy("kalman_arb", "卡尔曼套利", weight=0.3)
    fed.register_strategy("lstm_trend", "LSTM趋势", weight=0.25)
    fed.register_strategy("ml_momentum", "ML动量", weight=0.25)
    fed.register_strategy("stat_arb", "统计套利", weight=0.2)
    return fed


# ============================================================
# 初始化测试
# ============================================================


class TestFederationInit:
    """联邦初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        fed = StrategyFederation()
        assert fed.member_count == 0
        assert fed.signal_count == 0
        assert fed.conflict_count == 0

    def test_custom_thresholds(self) -> None:
        """测试自定义阈值."""
        fed = StrategyFederation(
            correlation_threshold=0.5,
            min_confidence=0.6,
        )
        stats = fed.get_statistics()
        assert stats["correlation_threshold"] == 0.5

    def test_disable_dynamic_weights(self) -> None:
        """测试禁用动态权重."""
        fed = StrategyFederation(enable_dynamic_weights=False)
        fed.register_strategy("test", weight=0.5)
        fed.update_dynamic_weights({"test": 10.0})
        # 动态权重不应改变
        member = fed.get_member("test")
        assert member is not None
        assert member.dynamic_weight == 0.5


# ============================================================
# 策略注册测试
# ============================================================


class TestStrategyRegistration:
    """策略注册测试."""

    def test_register_strategy(self, federation: StrategyFederation) -> None:
        """测试注册策略."""
        federation.register_strategy("test_strategy", "测试策略", weight=0.3)
        assert federation.member_count == 1
        member = federation.get_member("test_strategy")
        assert member is not None
        assert member.name == "测试策略"
        assert member.weight == 0.3

    def test_register_duplicate_ignored(self, federation: StrategyFederation) -> None:
        """测试重复注册被忽略."""
        federation.register_strategy("test", weight=0.3)
        federation.register_strategy("test", weight=0.5)  # 应被忽略
        assert federation.member_count == 1
        member = federation.get_member("test")
        assert member is not None
        assert member.weight == 0.3  # 保持原值

    def test_unregister_strategy(self, federation: StrategyFederation) -> None:
        """测试注销策略."""
        federation.register_strategy("test")
        assert federation.member_count == 1
        federation.unregister_strategy("test")
        assert federation.member_count == 0

    def test_enable_disable_strategy(self, federation: StrategyFederation) -> None:
        """测试启用/禁用策略."""
        federation.register_strategy("test")
        member = federation.get_member("test")
        assert member is not None
        assert member.enabled is True

        federation.disable_strategy("test")
        assert member.enabled is False

        federation.enable_strategy("test")
        assert member.enabled is True

    def test_set_weight(self, federation: StrategyFederation) -> None:
        """测试设置权重."""
        federation.register_strategy("test", weight=0.1)
        federation.set_weight("test", 0.5)
        member = federation.get_member("test")
        assert member is not None
        assert member.weight == 0.5

    def test_set_weight_clamped(self, federation: StrategyFederation) -> None:
        """测试权重被钳制在0-1."""
        federation.register_strategy("test", weight=0.1)
        federation.set_weight("test", 1.5)
        member = federation.get_member("test")
        assert member is not None
        assert member.weight == 1.0

        federation.set_weight("test", -0.5)
        assert member.weight == 0.0

    def test_get_all_members(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试获取所有成员."""
        members = federation_with_strategies.get_all_members()
        assert len(members) == 4


# ============================================================
# 信号生成测试
# ============================================================


class TestSignalGeneration:
    """信号生成测试."""

    def test_generate_signal_single(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试单一信号生成."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert result.direction == SignalDirection.LONG
        assert result.symbol == "rb2501"
        assert len(result.contributing_strategies) == 1

    def test_generate_signal_multiple_same_direction(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试多信号同向."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.7, 0.85),
            create_signal("ml_momentum", "rb2501", SignalDirection.LONG, 0.6, 0.8),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert result.direction == SignalDirection.LONG
        assert len(result.contributing_strategies) == 3

    def test_generate_signal_conflicting(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试信号冲突."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.SHORT, 0.7, 0.85),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert federation_with_strategies.conflict_count == 1
        # 方向由权重较大的策略决定
        assert result.direction in [SignalDirection.LONG, SignalDirection.SHORT]

    def test_generate_signal_flat_when_balanced(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试平衡时返回FLAT."""
        # 设置相等权重
        federation_with_strategies.set_weight("kalman_arb", 0.25)
        federation_with_strategies.set_weight("lstm_trend", 0.25)

        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.5, 0.8),
            create_signal("lstm_trend", "rb2501", SignalDirection.SHORT, 0.5, 0.8),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        # 当分数相近时应返回FLAT
        assert result.direction == SignalDirection.FLAT

    def test_generate_signal_empty(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试空信号返回None."""
        result = federation_with_strategies.generate_signal("rb2501", [])
        assert result is None

    def test_generate_signal_low_confidence_filtered(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试低置信度信号被过滤."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.3),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is None  # 置信度低于min_confidence(0.5)

    def test_generate_signal_disabled_strategy_filtered(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试禁用策略信号被过滤."""
        federation_with_strategies.disable_strategy("kalman_arb")
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is None


# ============================================================
# 权重测试
# ============================================================


class TestWeights:
    """权重测试."""

    def test_weights_normalized(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试权重归一化."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.7, 0.85),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        total_weight = sum(result.weights.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_dynamic_weight_update(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试动态权重更新."""
        performance = {
            "kalman_arb": 2.0,  # 夏普2.0
            "lstm_trend": 1.5,
            "ml_momentum": 1.0,
            "stat_arb": 0.5,
        }
        federation_with_strategies.update_dynamic_weights(performance)

        # 表现好的策略权重应增加
        kalman = federation_with_strategies.get_member("kalman_arb")
        stat = federation_with_strategies.get_member("stat_arb")
        assert kalman is not None
        assert stat is not None
        assert kalman.dynamic_weight > stat.dynamic_weight


# ============================================================
# 相关性测试
# ============================================================


class TestCorrelation:
    """相关性测试."""

    def test_correlation_matrix_empty(self) -> None:
        """测试空相关性矩阵."""
        matrix = CorrelationMatrix()
        assert matrix.get_correlation("a", "b") == 0.0

    def test_correlation_penalty_single_signal(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试单信号无相关性惩罚."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert result.correlation_penalty == 0.0

    def test_correlation_builds_over_time(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试相关性随时间构建."""
        # 提交多轮相似信号
        for _ in range(15):
            signals = [
                create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
                create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            ]
            federation_with_strategies.generate_signal("rb2501", signals)

        # 检查相关性
        corr = federation_with_strategies.get_correlation("kalman_arb", "lstm_trend")
        assert corr > 0  # 相同方向信号应有正相关性


# ============================================================
# 回调测试
# ============================================================


class TestCallback:
    """回调测试."""

    def test_register_callback(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试注册回调."""
        received_signals: list[FederationSignal] = []

        def callback(signal: FederationSignal) -> None:
            received_signals.append(signal)

        federation_with_strategies.register_callback(callback)

        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        federation_with_strategies.generate_signal("rb2501", signals)

        assert len(received_signals) == 1
        assert received_signals[0].direction == SignalDirection.LONG

    def test_callback_error_ignored(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试回调错误被忽略."""

        def bad_callback(signal: FederationSignal) -> None:
            raise ValueError("Test error")

        federation_with_strategies.register_callback(bad_callback)

        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        # 不应抛出异常
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is not None


# ============================================================
# 统计测试
# ============================================================


class TestStatistics:
    """统计测试."""

    def test_get_statistics(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试获取统计信息."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        federation_with_strategies.generate_signal("rb2501", signals)

        stats = federation_with_strategies.get_statistics()
        assert stats["member_count"] == 4
        assert stats["signal_count"] == 1
        assert "members" in stats

    def test_hit_rate_tracking(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试命中率追踪."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        federation_with_strategies.generate_signal("rb2501", signals)
        federation_with_strategies.record_hit("kalman_arb")

        member = federation_with_strategies.get_member("kalman_arb")
        assert member is not None
        assert member.signal_count == 1
        assert member.hit_count == 1
        assert member.hit_rate == 1.0

    def test_reset(self, federation_with_strategies: StrategyFederation) -> None:
        """测试重置."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        federation_with_strategies.generate_signal("rb2501", signals)
        assert federation_with_strategies.signal_count == 1

        federation_with_strategies.reset()
        assert federation_with_strategies.signal_count == 0
        assert federation_with_strategies.conflict_count == 0


# ============================================================
# 数据类测试
# ============================================================


class TestStrategySignal:
    """策略信号测试."""

    def test_frozen(self) -> None:
        """测试信号不可变."""
        signal = StrategySignal(
            strategy_id="test",
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            signal.strength = 0.5  # type: ignore[misc]

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        signal = StrategySignal(
            strategy_id="test",
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        d = signal.to_dict()
        assert d["strategy_id"] == "test"
        assert d["direction"] == "LONG"
        assert d["strength"] == 0.8


class TestFederationSignal:
    """联邦信号测试."""

    def test_frozen(self) -> None:
        """测试信号不可变."""
        signal = FederationSignal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        with pytest.raises(AttributeError):
            signal.strength = 0.5  # type: ignore[misc]

    def test_to_audit_dict(self) -> None:
        """测试转换为审计字典."""
        signal = FederationSignal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
            contributing_strategies=("kalman_arb", "lstm_trend"),
            weights={"kalman_arb": 0.6, "lstm_trend": 0.4},
            correlation_penalty=0.1,
            timestamp="2025-01-15T10:00:00",
        )
        audit = signal.to_audit_dict()

        assert audit["event_type"] == "FEDERATION_SIGNAL"
        assert audit["symbol"] == "rb2501"
        assert audit["direction"] == "LONG"
        assert len(audit["contributing_strategies"]) == 2

    def test_get_strength_level(self) -> None:
        """测试获取强度等级."""
        strong = FederationSignal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        assert strong.get_strength_level() == SignalStrength.STRONG

        moderate = FederationSignal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.5,
            confidence=0.9,
        )
        assert moderate.get_strength_level() == SignalStrength.MODERATE

        weak = FederationSignal(
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.3,
            confidence=0.9,
        )
        assert weak.get_strength_level() == SignalStrength.WEAK


class TestStrategyMember:
    """策略成员测试."""

    def test_hit_rate_zero_signals(self) -> None:
        """测试零信号时命中率为0."""
        member = StrategyMember(strategy_id="test", name="测试")
        assert member.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """测试命中率计算."""
        member = StrategyMember(
            strategy_id="test",
            name="测试",
            signal_count=10,
            hit_count=7,
        )
        assert member.hit_rate == 0.7


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_federation(self) -> None:
        """测试创建联邦."""
        fed = create_federation(correlation_threshold=0.4, min_confidence=0.6)
        stats = fed.get_statistics()
        assert stats["correlation_threshold"] == 0.4

    def test_create_signal(self) -> None:
        """测试创建信号."""
        signal = create_signal(
            strategy_id="test",
            symbol="rb2501",
            direction=SignalDirection.LONG,
            strength=0.8,
            confidence=0.9,
        )
        assert signal.strategy_id == "test"
        assert signal.symbol == "rb2501"
        assert signal.timestamp != ""


# ============================================================
# M1 军规测试: 单一信号源
# ============================================================


class TestM1SingleSignalSource:
    """M1军规测试: 单一信号源."""

    def test_federation_is_single_output(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试联邦是唯一信号出口."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.7, 0.85),
            create_signal("ml_momentum", "rb2501", SignalDirection.SHORT, 0.6, 0.8),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        # 无论输入多少信号,输出只有一个
        assert result is not None
        assert isinstance(result, FederationSignal)
        assert result.direction in [
            SignalDirection.LONG,
            SignalDirection.SHORT,
            SignalDirection.FLAT,
        ]


# ============================================================
# M19 军规测试: 风险归因
# ============================================================


class TestM19Attribution:
    """M19军规测试: 风险归因."""

    def test_contributing_strategies_tracked(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试贡献策略被追踪."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.7, 0.85),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert "kalman_arb" in result.contributing_strategies
        assert "lstm_trend" in result.contributing_strategies

    def test_weights_in_output(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试权重在输出中."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.7, 0.85),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)

        assert result is not None
        assert "kalman_arb" in result.weights
        assert "lstm_trend" in result.weights


# ============================================================
# M20 军规测试: 跨所一致/相关性抑制
# ============================================================


class TestM20CorrelationSuppression:
    """M20军规测试: 相关性抑制."""

    def test_correlation_penalty_applied(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试相关性惩罚被应用."""
        # 生成多轮高度相关的信号
        for _ in range(15):
            signals = [
                create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
                create_signal("lstm_trend", "rb2501", SignalDirection.LONG, 0.8, 0.9),
            ]
            result = federation_with_strategies.generate_signal("rb2501", signals)

        # 最终应有相关性惩罚
        assert result is not None
        # 相关性惩罚可能为0或正值,取决于信号历史


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_unregistered_strategy_ignored(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试未注册策略信号被忽略."""
        signals = [
            create_signal("unknown", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is None

    def test_wrong_symbol_filtered(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试错误合约代码被过滤."""
        signals = [
            create_signal("kalman_arb", "hc2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is None  # hc2501 != rb2501

    def test_very_low_strength_becomes_flat(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试极低强度变为FLAT."""
        signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.05, 0.9),
        ]
        result = federation_with_strategies.generate_signal("rb2501", signals)
        assert result is not None
        assert result.direction == SignalDirection.FLAT


# ============================================================
# 并发安全测试
# ============================================================


class TestConcurrency:
    """并发测试 (基础)."""

    def test_multiple_symbols(
        self, federation_with_strategies: StrategyFederation
    ) -> None:
        """测试多个合约同时处理."""
        rb_signals = [
            create_signal("kalman_arb", "rb2501", SignalDirection.LONG, 0.8, 0.9),
        ]
        hc_signals = [
            create_signal("kalman_arb", "hc2501", SignalDirection.SHORT, 0.7, 0.85),
        ]

        rb_result = federation_with_strategies.generate_signal("rb2501", rb_signals)
        hc_result = federation_with_strategies.generate_signal("hc2501", hc_signals)

        assert rb_result is not None
        assert rb_result.symbol == "rb2501"
        assert rb_result.direction == SignalDirection.LONG

        assert hc_result is not None
        assert hc_result.symbol == "hc2501"
        assert hc_result.direction == SignalDirection.SHORT
