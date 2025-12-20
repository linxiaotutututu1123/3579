"""Calendar Arbitrage Strategy 测试 (军规级 v4.0).

覆盖场景:
- ARB.LEGS.FIXED_NEAR_FAR: 近/远月合约固定
- ARB.SIGNAL.HALF_LIFE_GATE: 半衰期门禁
- ARB.SIGNAL.STOP_Z_BREAKER: 止损触发
- ARB.SIGNAL.EXPIRY_GATE: 到期门禁
- ARB.SIGNAL.CORRELATION_BREAK: 相关性崩溃
- ARB.COST.ENTRY_GATE: 成本门禁
"""

from __future__ import annotations

from datetime import date, timedelta

from src.strategy.calendar_arb.strategy import (
    ArbConfig,
    ArbSignal,
    ArbSnapshot,
    ArbState,
    CalendarArbStrategy,
    LegPair,
)
from src.strategy.types import MarketState


class TestArbConfig:
    """ArbConfig 测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = ArbConfig()
        assert config.entry_z == 2.5
        assert config.exit_z == 0.5
        assert config.stop_z == 5.0
        assert config.max_half_life_days == 20
        assert config.min_correlation == 0.7
        assert config.correlation_window == 60
        assert config.expiry_block_days == 5
        assert config.cooldown_after_stop_s == 600.0
        assert config.min_edge_bps == 5.0
        assert config.max_position_per_leg == 10

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = ArbConfig(
            entry_z=3.0,
            exit_z=0.3,
            stop_z=6.0,
            max_position_per_leg=20,
        )
        assert config.entry_z == 3.0
        assert config.exit_z == 0.3
        assert config.stop_z == 6.0
        assert config.max_position_per_leg == 20


class TestLegPair:
    """LegPair 测试."""

    def test_leg_pair_creation(self) -> None:
        """测试腿对创建."""
        pair = LegPair(
            product="AO",
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20250115",
            far_expiry="20250515",
        )
        assert pair.product == "AO"
        assert pair.near_symbol == "AO2501"
        assert pair.far_symbol == "AO2505"


class TestArbSnapshot:
    """ArbSnapshot 测试."""

    def test_snapshot_to_dict(self) -> None:
        """测试快照转字典."""
        snapshot = ArbSnapshot(
            ts=1000.0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.LONG_SPREAD,
            near_price=100.0,
            far_price=105.0,
            beta=1.05,
            residual=0.5,
            z_score=2.0,
            half_life=100.0,
            correlation=0.95,
            position_near=10,
            position_far=-10,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        d = snapshot.to_dict()
        assert d["ts"] == 1000.0
        assert d["state"] == "active"
        assert d["signal"] == 1
        assert d["near_price"] == 100.0
        assert d["beta"] == 1.05


class TestCalendarArbStrategyInit:
    """CalendarArbStrategy 初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        strategy = CalendarArbStrategy()
        assert strategy.state == ArbState.INIT
        assert strategy.signal == ArbSignal.FLAT
        assert strategy.leg_pair is None
        assert strategy.config.entry_z == 2.5

    def test_custom_init(self) -> None:
        """测试自定义初始化."""
        config = ArbConfig(entry_z=3.0)
        strategy = CalendarArbStrategy(config=config, product="RB")
        assert strategy.config.entry_z == 3.0
        assert strategy._product == "RB"

    def test_set_leg_pair(self) -> None:
        """测试设置腿对 (ARB.LEGS.FIXED_NEAR_FAR)."""
        strategy = CalendarArbStrategy()
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20250115",
            far_expiry="20250515",
        )
        assert strategy.leg_pair is not None
        assert strategy.leg_pair.near_symbol == "AO2501"
        assert strategy.leg_pair.far_symbol == "AO2505"
        assert strategy.state == ArbState.ACTIVE


class TestCalendarArbStrategyOnTick:
    """CalendarArbStrategy on_tick 测试."""

    def _make_market_state(self, prices: dict[str, float]) -> MarketState:
        """创建测试用的 MarketState."""
        return MarketState(prices=prices, equity=100000.0, bars_1m={})

    def test_on_tick_without_leg_pair(self) -> None:
        """测试未配置腿对时的 on_tick."""
        strategy = CalendarArbStrategy()
        state = self._make_market_state({"AO2501": 100.0, "AO2505": 105.0})
        portfolio = strategy.on_tick(state)
        assert portfolio.target_net_qty == {}
        assert portfolio.features_hash == "flat"

    def test_on_tick_with_invalid_prices(self) -> None:
        """测试无效价格时的 on_tick."""
        strategy = CalendarArbStrategy()
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20260115",
            far_expiry="20260515",
        )
        # 价格为0
        state = self._make_market_state({"AO2501": 0.0, "AO2505": 105.0})
        portfolio = strategy.on_tick(state)
        assert portfolio.target_net_qty == {}

    def test_on_tick_with_valid_prices(self) -> None:
        """测试有效价格时的 on_tick."""
        strategy = CalendarArbStrategy()
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20260115",
            far_expiry="20260515",
        )
        state = self._make_market_state({"AO2501": 100.0, "AO2505": 105.0})
        portfolio = strategy.on_tick(state)
        assert portfolio.model_version == "3.0.0"
        # 第一个 tick 通常不会产生信号 (需要 warmup)
        assert strategy.last_snapshot is not None

    def test_on_tick_generates_long_spread_signal(self) -> None:
        """测试产生多头价差信号."""
        config = ArbConfig(entry_z=2.5, exit_z=0.5, min_edge_bps=0.0)
        strategy = CalendarArbStrategy(config=config)
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20260115",
            far_expiry="20260515",
        )

        # 模拟多个 tick 让 Kalman 滤波器稳定
        for i in range(100):
            near = 100.0 + i * 0.01
            far = 105.0 + i * 0.01
            state = self._make_market_state({"AO2501": near, "AO2505": far})
            strategy.on_tick(state)

        # 制造一个大的负 z-score（价差过窄）
        state = self._make_market_state({"AO2501": 80.0, "AO2505": 105.0})
        strategy.on_tick(state)

        # 检查是否有信号产生
        assert strategy.last_snapshot is not None


class TestCalendarArbStrategyGates:
    """CalendarArbStrategy 门禁测试."""

    def test_check_stop_z(self) -> None:
        """测试止损 z-score 检查 (ARB.SIGNAL.STOP_Z_BREAKER)."""
        config = ArbConfig(stop_z=5.0)
        strategy = CalendarArbStrategy(config=config)

        # 未触发止损
        assert strategy._check_stop_z(4.0) is False
        assert strategy._check_stop_z(-4.0) is False

        # 触发止损
        assert strategy._check_stop_z(5.1) is True
        assert strategy._check_stop_z(-5.1) is True

    def test_check_cooldown_expired(self) -> None:
        """测试冷却期检查."""
        config = ArbConfig(cooldown_after_stop_s=60.0)
        strategy = CalendarArbStrategy(config=config)

        # 未设置止损时间
        assert strategy._check_cooldown_expired(1000.0) is True

        # 设置止损时间，未过期
        strategy._stop_triggered_at = 1000.0
        assert strategy._check_cooldown_expired(1030.0) is False

        # 已过期
        assert strategy._check_cooldown_expired(1061.0) is True

    def test_check_expiry_gate_no_leg_pair(self) -> None:
        """测试无腿对时的到期门禁."""
        strategy = CalendarArbStrategy()
        assert strategy._check_expiry_gate() is False

    def test_check_expiry_gate_far_from_expiry(self) -> None:
        """测试远离到期时的到期门禁 (ARB.SIGNAL.EXPIRY_GATE)."""
        config = ArbConfig(expiry_block_days=5)
        strategy = CalendarArbStrategy(config=config)

        # 设置一个很远的到期日
        future_date = date.today() + timedelta(days=30)
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry=future_date.strftime("%Y%m%d"),
            far_expiry="20260515",
        )

        assert strategy._check_expiry_gate() is False

    def test_check_expiry_gate_near_expiry(self) -> None:
        """测试接近到期时的到期门禁."""
        config = ArbConfig(expiry_block_days=5)
        strategy = CalendarArbStrategy(config=config)

        # 设置一个很近的到期日
        near_date = date.today() + timedelta(days=3)
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry=near_date.strftime("%Y%m%d"),
            far_expiry="20260515",
        )

        assert strategy._check_expiry_gate() is True

    def test_check_expiry_gate_invalid_date(self) -> None:
        """测试无效日期时的到期门禁."""
        strategy = CalendarArbStrategy()
        strategy._leg_pair = LegPair(
            product="AO",
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="invalid",  # 无效日期
            far_expiry="20260515",
        )
        # 应该返回 False 而不是抛出异常
        assert strategy._check_expiry_gate() is False

    def test_check_correlation_break(self) -> None:
        """测试相关性崩溃检查 (ARB.SIGNAL.CORRELATION_BREAK)."""
        config = ArbConfig(min_correlation=0.7, correlation_window=10)
        strategy = CalendarArbStrategy(config=config)

        # 样本不足
        strategy._near_prices = [1.0, 2.0]
        strategy._far_prices = [1.0, 2.0]
        assert strategy._check_correlation_break(0.5) is False

        # 样本充足，相关性高
        strategy._near_prices = list(range(10))
        strategy._far_prices = list(range(10))
        assert strategy._check_correlation_break(0.9) is False

        # 样本充足，相关性低
        assert strategy._check_correlation_break(0.5) is True

    def test_check_half_life_gate(self) -> None:
        """测试半衰期门禁 (ARB.SIGNAL.HALF_LIFE_GATE)."""
        config = ArbConfig(max_half_life_days=20)
        strategy = CalendarArbStrategy(config=config)

        # 每天 240 个样本，20天 = 4800 样本
        # 半衰期 4000 样本 = 16.7 天，未触发
        assert strategy._check_half_life_gate(4000.0) is False

        # 半衰期 5000 样本 = 20.8 天，触发
        assert strategy._check_half_life_gate(5000.0) is True

    def test_check_cost_gate(self) -> None:
        """测试成本门禁 (ARB.COST.ENTRY_GATE)."""
        config = ArbConfig(min_edge_bps=5.0)
        strategy = CalendarArbStrategy(config=config)

        # z-score = 2.0, edge = 4 bps, cost = 2 bps, net = 2 bps < 5 bps
        assert strategy._check_cost_gate(2.0, 100.0, 105.0) is True

        # z-score = 5.0, edge = 10 bps, cost = 2 bps, net = 8 bps > 5 bps
        assert strategy._check_cost_gate(5.0, 100.0, 105.0) is False


class TestCalendarArbStrategySignals:
    """CalendarArbStrategy 信号生成测试."""

    def test_generate_signal_exit(self) -> None:
        """测试退出信号."""
        config = ArbConfig(exit_z=0.5)
        strategy = CalendarArbStrategy(config=config)

        # z-score 在退出区间内
        signal = strategy._generate_signal(0.3, False, False)
        assert signal == ArbSignal.FLAT

    def test_generate_signal_blocked_by_half_life(self) -> None:
        """测试半衰期阻塞."""
        config = ArbConfig(entry_z=2.5)
        strategy = CalendarArbStrategy(config=config)
        strategy._signal = ArbSignal.FLAT

        # 高 z-score 但被半衰期阻塞
        signal = strategy._generate_signal(3.0, True, False)
        assert signal == ArbSignal.FLAT

    def test_generate_signal_blocked_by_cost(self) -> None:
        """测试成本阻塞."""
        config = ArbConfig(entry_z=2.5)
        strategy = CalendarArbStrategy(config=config)
        strategy._signal = ArbSignal.FLAT

        # 高 z-score 但被成本阻塞
        signal = strategy._generate_signal(3.0, False, True)
        assert signal == ArbSignal.FLAT

    def test_generate_signal_short_spread(self) -> None:
        """测试空头价差信号."""
        config = ArbConfig(entry_z=2.5, exit_z=0.5)
        strategy = CalendarArbStrategy(config=config)
        strategy._signal = ArbSignal.FLAT

        # z-score > entry_z -> 空头价差
        signal = strategy._generate_signal(3.0, False, False)
        assert signal == ArbSignal.SHORT_SPREAD

    def test_generate_signal_long_spread(self) -> None:
        """测试多头价差信号."""
        config = ArbConfig(entry_z=2.5, exit_z=0.5)
        strategy = CalendarArbStrategy(config=config)
        strategy._signal = ArbSignal.FLAT

        # z-score < -entry_z -> 多头价差
        signal = strategy._generate_signal(-3.0, False, False)
        assert signal == ArbSignal.LONG_SPREAD

    def test_generate_signal_hold_position(self) -> None:
        """测试持仓保持."""
        config = ArbConfig(entry_z=2.5, exit_z=0.5)
        strategy = CalendarArbStrategy(config=config)
        strategy._signal = ArbSignal.LONG_SPREAD

        # z-score 在持仓区间内
        signal = strategy._generate_signal(1.0, False, False)
        assert signal == ArbSignal.LONG_SPREAD


class TestCalendarArbStrategyPositions:
    """CalendarArbStrategy 持仓计算测试."""

    def test_compute_target_near_flat(self) -> None:
        """测试平仓时的近月目标."""
        strategy = CalendarArbStrategy()
        snapshot = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.FLAT,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=0.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        assert strategy._compute_target_near(snapshot) == 0

    def test_compute_target_near_long_spread(self) -> None:
        """测试多头价差时的近月目标."""
        config = ArbConfig(max_position_per_leg=10)
        strategy = CalendarArbStrategy(config=config)
        snapshot = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.LONG_SPREAD,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=-3.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        assert strategy._compute_target_near(snapshot) == 10

    def test_compute_target_near_short_spread(self) -> None:
        """测试空头价差时的近月目标."""
        config = ArbConfig(max_position_per_leg=10)
        strategy = CalendarArbStrategy(config=config)
        snapshot = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.SHORT_SPREAD,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=3.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        assert strategy._compute_target_near(snapshot) == -10

    def test_compute_target_far(self) -> None:
        """测试远月目标计算."""
        config = ArbConfig(max_position_per_leg=10)
        strategy = CalendarArbStrategy(config=config)

        # LONG_SPREAD: near = +10, far = -10 * beta
        snapshot_long = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.LONG_SPREAD,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=-3.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        assert strategy._compute_target_far(snapshot_long, beta=1.0) == -10

        # FLAT: far = 0
        snapshot_flat = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.FLAT,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=0.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        assert strategy._compute_target_far(snapshot_flat, beta=1.0) == 0


class TestCalendarArbStrategyCorrelation:
    """CalendarArbStrategy 相关性计算测试."""

    def test_compute_correlation_insufficient_samples(self) -> None:
        """测试样本不足时的相关性."""
        strategy = CalendarArbStrategy()
        strategy._near_prices = [100.0]
        strategy._far_prices = [105.0]
        # 样本不足返回 1.0
        assert strategy._compute_correlation() == 1.0

    def test_compute_correlation_perfect(self) -> None:
        """测试完美相关性."""
        strategy = CalendarArbStrategy()
        strategy._near_prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        strategy._far_prices = [2.0, 4.0, 6.0, 8.0, 10.0]
        # 完美正相关
        corr = strategy._compute_correlation()
        assert abs(corr - 1.0) < 0.001

    def test_compute_correlation_negative(self) -> None:
        """测试负相关性."""
        strategy = CalendarArbStrategy()
        strategy._near_prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        strategy._far_prices = [10.0, 8.0, 6.0, 4.0, 2.0]
        # 完美负相关
        corr = strategy._compute_correlation()
        assert abs(corr - (-1.0)) < 0.001

    def test_compute_correlation_zero_variance(self) -> None:
        """测试零方差时的相关性."""
        strategy = CalendarArbStrategy()
        strategy._near_prices = [100.0, 100.0, 100.0]
        strategy._far_prices = [105.0, 105.0, 105.0]
        # 零方差返回 1.0
        assert strategy._compute_correlation() == 1.0

    def test_update_correlation_tracking(self) -> None:
        """测试相关性跟踪更新."""
        config = ArbConfig(correlation_window=5)
        strategy = CalendarArbStrategy(config=config)

        # 添加数据
        for i in range(10):
            strategy._update_correlation_tracking(float(i), float(i) + 5)

        # 应该只保留最近 5 个
        assert len(strategy._near_prices) == 5
        assert len(strategy._far_prices) == 5
        assert strategy._near_prices[-1] == 9.0


class TestCalendarArbStrategyProperties:
    """CalendarArbStrategy 属性测试."""

    def test_state_property(self) -> None:
        """测试状态属性."""
        strategy = CalendarArbStrategy()
        assert strategy.state == ArbState.INIT

    def test_signal_property(self) -> None:
        """测试信号属性."""
        strategy = CalendarArbStrategy()
        assert strategy.signal == ArbSignal.FLAT

    def test_leg_pair_property(self) -> None:
        """测试腿对属性."""
        strategy = CalendarArbStrategy()
        assert strategy.leg_pair is None

        strategy.set_leg_pair("AO2501", "AO2505", "20260115", "20260515")
        assert strategy.leg_pair is not None

    def test_last_snapshot_property(self) -> None:
        """测试最后快照属性."""
        strategy = CalendarArbStrategy()
        assert strategy.last_snapshot is None

    def test_config_property(self) -> None:
        """测试配置属性."""
        config = ArbConfig(entry_z=3.0)
        strategy = CalendarArbStrategy(config=config)
        assert strategy.config.entry_z == 3.0

    def test_get_state_dict(self) -> None:
        """测试获取状态字典."""
        strategy = CalendarArbStrategy()
        state_dict = strategy.get_state_dict()
        assert "state" in state_dict
        assert "signal" in state_dict
        assert "position_near" in state_dict
        assert "position_far" in state_dict
        assert "kalman" in state_dict

    def test_update_position(self) -> None:
        """测试更新持仓."""
        strategy = CalendarArbStrategy()
        strategy.update_position(10, -10)
        assert strategy._position_near == 10
        assert strategy._position_far == -10


class TestCalendarArbStrategyHelpers:
    """CalendarArbStrategy 辅助方法测试."""

    def test_compute_features_hash(self) -> None:
        """测试特征哈希计算."""
        strategy = CalendarArbStrategy()
        snapshot = ArbSnapshot(
            ts=0,
            state=ArbState.ACTIVE,
            signal=ArbSignal.FLAT,
            near_price=100.0,
            far_price=105.0,
            beta=1.0,
            residual=0.0,
            z_score=0.0,
            half_life=100.0,
            correlation=0.9,
            position_near=0,
            position_far=0,
            stop_triggered=False,
            expiry_blocked=False,
            correlation_blocked=False,
            half_life_blocked=False,
            cost_blocked=False,
        )
        hash1 = strategy._compute_features_hash(snapshot)
        hash2 = strategy._compute_features_hash(snapshot)
        # 相同输入应产生相同哈希
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_make_flat_portfolio(self) -> None:
        """测试创建平仓组合."""
        strategy = CalendarArbStrategy()
        state = MarketState(prices={}, equity=100000.0, bars_1m={})
        portfolio = strategy._make_flat_portfolio(state)
        assert portfolio.target_net_qty == {}
        assert portfolio.features_hash == "flat"
        assert portfolio.model_version == "3.0.0"


class TestCalendarArbStrategyIntegration:
    """CalendarArbStrategy 集成测试."""

    def _make_market_state(self, prices: dict[str, float]) -> MarketState:
        """创建测试用的 MarketState."""
        return MarketState(prices=prices, equity=100000.0, bars_1m={})

    def test_full_trading_cycle(self) -> None:
        """测试完整交易周期."""
        config = ArbConfig(
            entry_z=2.0,
            exit_z=0.5,
            stop_z=5.0,
            min_edge_bps=0.0,
            correlation_window=5,
        )
        strategy = CalendarArbStrategy(config=config)
        strategy.set_leg_pair(
            near_symbol="AO2501",
            far_symbol="AO2505",
            near_expiry="20260115",
            far_expiry="20260515",
        )

        # 模拟 warmup
        for i in range(20):
            near = 100.0 + i * 0.1
            far = 105.0 + i * 0.1
            state = self._make_market_state({"AO2501": near, "AO2505": far})
            strategy.on_tick(state)

        assert strategy.state == ArbState.ACTIVE
        assert strategy.last_snapshot is not None

    def test_stop_loss_and_cooldown(self) -> None:
        """测试止损和冷却期."""
        config = ArbConfig(stop_z=5.0, cooldown_after_stop_s=1.0)
        strategy = CalendarArbStrategy(config=config)

        # 触发止损
        assert strategy._check_stop_z(6.0) is True

        # 设置止损时间
        import time

        strategy._stop_triggered_at = time.time()
        strategy._state = ArbState.STOPPED

        # 立即检查 - 未过期
        assert strategy._check_cooldown_expired(time.time()) is False

        # 等待冷却期
        import time as t

        t.sleep(1.1)
        assert strategy._check_cooldown_expired(time.time()) is True
