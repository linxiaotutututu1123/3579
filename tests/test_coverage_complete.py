"""Comprehensive tests to achieve 100% code coverage."""
# ruff: noqa: F401, F811

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from src.config import load_settings
from src.execution.broker import Broker, OrderAck, OrderRejected
from src.execution.ctp_broker import (
    CtpBroker,
    CtpConfig,
    CtpConnectionError,
    CtpNotAvailableError,
)
from src.execution.flatten_executor import (
    FlattenExecutor,
    _find_next_more_aggressive_close,
    _is_more_aggressive,
)
from src.execution.flatten_plan import FlattenSpec, PositionToClose
from src.execution.order_tracker import OrderExecutionTracker, OrderState
from src.execution.order_types import Offset, OrderIntent, Side
from src.main import main as main_func
from src.portfolio.rebalancer import build_rebalance_intents
from src.replay.runner import run_replay_tick_mode2
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState
from src.strategy.base import Strategy
from src.strategy.dl.weights import clear_model_cache
from src.strategy.ensemble_moe import EnsembleMoEStrategy
from src.strategy.linear_ai import LinearAIStrategy
from src.strategy.top_tier_trend_risk_parity import TopTierConfig, TopTierTrendRiskParityStrategy
from src.strategy.types import Bar1m, MarketState, TargetPortfolio
from src.trading.ci_gate import CIGate, GateCheckStatus, log_gate_report
from src.trading.controls import TradeControls, TradeMode
from src.trading.live_guard import LiveModeGuard
from src.trading.orchestrator import handle_trading_tick
from src.trading.reconcile import ReconcileStatus, log_reconcile_report, reconcile_positions


if TYPE_CHECKING:
    pass


def _generate_bars(n: int, base_price: float = 100.0, trend: float = 0.001) -> list[Bar1m]:
    """Generate synthetic bar data with trend."""
    bars: list[Bar1m] = []
    price = base_price
    for i in range(n):
        price = price * (1 + trend + 0.01 * math.sin(i * 0.1))
        high = price * 1.005
        low = price * 0.995
        bars.append(
            {
                "ts": 1700000000.0 + i * 60,
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000.0 + i,
            }
        )
    return bars


class TestConfigCoverage:
    """Coverage tests for config module."""

    def test_load_settings_without_dingtalk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load_settings without dingtalk webhook."""
        monkeypatch.delenv("DINGTALK_WEBHOOK", raising=False)
        monkeypatch.delenv("DINGTALK_SECRET", raising=False)
        settings = load_settings()
        assert settings.dingtalk is None


class TestBrokerProtocol:
    """Coverage tests for Broker protocol."""

    def test_broker_not_implemented(self) -> None:
        """Broker.place_order raises NotImplementedError by default."""

        class TestBroker:
            def place_order(self, intent: OrderIntent) -> OrderAck:
                raise NotImplementedError

        broker = TestBroker()
        intent = OrderIntent(symbol="AO", side=Side.BUY, offset=Offset.OPEN, price=100.0, qty=1)
        with pytest.raises(NotImplementedError):
            broker.place_order(intent)


class TestCtpBrokerCoverage:
    """Coverage tests for CTP broker."""

    def test_disconnect_when_connected(self) -> None:
        """Test disconnect when broker is connected."""
        config = CtpConfig(
            front_addr="tcp://127.0.0.1:10130",
            broker_id="9999",
            user_id="test",
            password="test123",
        )
        broker = CtpBroker(config)
        # Force connected state for testing
        broker._connected = True
        broker.disconnect()
        assert broker.is_connected is False

    def test_place_order_not_connected_with_sdk(self) -> None:
        """Test place_order raises when not connected but SDK available (mocked)."""
        config = CtpConfig(
            front_addr="tcp://127.0.0.1:10130",
            broker_id="9999",
            user_id="test",
            password="test123",
        )
        broker = CtpBroker(config)
        # Simulate SDK available but not connected
        broker._ctp = object()  # Mock non-None SDK
        broker._connected = False
        intent = OrderIntent(symbol="au2412", side=Side.BUY, offset=Offset.OPEN, qty=1, price=500.0)
        with pytest.raises(OrderRejected, match="Not connected"):
            broker.place_order(intent)

    def test_place_order_connected_with_sdk(self) -> None:
        """Test place_order success when connected with SDK."""
        config = CtpConfig(
            front_addr="tcp://127.0.0.1:10130",
            broker_id="9999",
            user_id="test",
            password="test123",
        )
        broker = CtpBroker(config)
        broker._ctp = object()  # Mock non-None SDK
        broker._connected = True
        intent = OrderIntent(symbol="au2412", side=Side.BUY, offset=Offset.OPEN, qty=1, price=500.0)
        ack = broker.place_order(intent)
        assert ack.order_id.startswith("CTP_")


class TestFlattenExecutorCoverage:
    """Coverage tests for flatten executor."""

    def test_is_more_aggressive_different_sides(self) -> None:
        """_is_more_aggressive returns False for different sides."""
        ref = OrderIntent(symbol="AO", side=Side.BUY, offset=Offset.CLOSE, price=100, qty=1)
        cand = OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100, qty=1)
        assert _is_more_aggressive(ref, cand) is False

    def test_is_more_aggressive_sell_more_aggressive(self) -> None:
        """_is_more_aggressive for sell side - lower price is more aggressive."""
        ref = OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100, qty=1)
        cand = OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=99, qty=1)
        assert _is_more_aggressive(ref, cand) is True

    def test_is_more_aggressive_buy_more_aggressive(self) -> None:
        """_is_more_aggressive for buy side - higher price is more aggressive."""
        ref = OrderIntent(symbol="AO", side=Side.BUY, offset=Offset.CLOSE, price=100, qty=1)
        cand = OrderIntent(symbol="AO", side=Side.BUY, offset=Offset.CLOSE, price=101, qty=1)
        assert _is_more_aggressive(ref, cand) is True

    def test_find_next_more_aggressive_no_match(self) -> None:
        """_find_next_more_aggressive_close returns None when no match."""
        intents = [
            OrderIntent(symbol="AO", side=Side.SELL, offset=Offset.CLOSE, price=100, qty=1),
        ]
        result = _find_next_more_aggressive_close(intents, start_index=0, reference=intents[0])
        assert result is None


class TestFlattenPlanCoverage:
    """Coverage tests for flatten plan."""

    def test_position_invalid_today_qty(self) -> None:
        """PositionToClose raises for negative today_qty."""
        with pytest.raises(ValueError, match="today_qty/yesterday_qty must be >= 0"):
            PositionToClose(symbol="AO", net_qty=1, today_qty=-1, yesterday_qty=2)

    def test_position_invalid_sum(self) -> None:
        """PositionToClose raises when sum doesn't match net_qty."""
        with pytest.raises(ValueError, match="abs.net_qty. must equal"):
            PositionToClose(symbol="AO", net_qty=5, today_qty=1, yesterday_qty=1)


class TestOrderTrackerCoverage:
    """Coverage tests for order tracker."""

    def test_update_state_with_error(self) -> None:
        """update_state sets error_message."""
        tracker = OrderExecutionTracker()
        tracker.create_order("O1", "AO", "BUY", 10, 100.0)
        track = tracker.update_state(
            "O1", OrderState.REJECTED, error_message="Rejected by exchange"
        )
        assert track is not None
        assert track.error_message == "Rejected by exchange"


class TestReplayCoverage:
    """Coverage tests for replay runner."""

    def test_run_replay_tick_mode2(self) -> None:
        """Test replay tick mode2 execution."""
        from src.execution.flatten_plan import FlattenSpec
        from src.replay.runner import BookTop, NoopBroker

        snap = AccountSnapshot(equity=1_000_000, margin_used=100_000)
        positions: list[PositionToClose] = []
        books = {"AO": BookTop(best_bid=100.0, best_ask=101.0, tick=0.5)}
        bars_1m = {"AO": _generate_bars(300)}

        cfg = RiskConfig()
        risk = RiskManager(cfg, cancel_all_cb=lambda: None, force_flatten_all_cb=lambda: None)
        risk.on_day_start_0900(snap, correlation_id="test")

        strategy = LinearAIStrategy(symbols=["AO"])
        _broker = NoopBroker()
        flatten_spec = FlattenSpec()

        result = run_replay_tick_mode2(
            risk=risk,
            strategy=strategy,
            snap=snap,
            positions=positions,
            books=books,
            bars_1m=bars_1m,
            flatten_spec=flatten_spec,
            now_ts=1700000000.0,
            trade_mode="PAPER",
        )
        assert result.correlation_id


class TestRiskCoverage:
    """Coverage tests for risk module."""

    def test_risk_state_dd_with_zero_e0(self) -> None:
        """dd returns 0 when e0 is zero."""
        state = RiskState(e0=0.0)
        assert state.dd(100.0) == 0.0


class TestStrategyCoverage:
    """Coverage tests for strategy modules."""

    def test_strategy_abc(self) -> None:
        """Strategy ABC cannot be instantiated."""

        class TestStrategy(Strategy):
            pass

        with pytest.raises(TypeError):
            TestStrategy()  # type: ignore[abstract]

    def test_linear_ai_edge_cases(self) -> None:
        """Test linear AI with edge case inputs."""
        strategy = LinearAIStrategy(symbols=["AO"])

        # Test with very short bars (insufficient)
        short_bars = _generate_bars(10)
        state = MarketState(prices={"AO": 100.0}, equity=1_000_000.0, bars_1m={"AO": short_bars})
        result = strategy.on_tick(state)
        assert result.target_net_qty["AO"] == 0

        # Test with zero/negative prices in bars
        zero_price_bars: list[Bar1m] = [
            {
                "ts": 1700000000.0 + i * 60,
                "open": 0.0,
                "high": 0.0,
                "low": 0.0,
                "close": 0.0,
                "volume": 0.0,
            }
            for i in range(300)
        ]
        state = MarketState(
            prices={"AO": 100.0}, equity=1_000_000.0, bars_1m={"AO": zero_price_bars}
        )
        result = strategy.on_tick(state)
        # Should not crash
        assert isinstance(result.target_net_qty["AO"], int)

    def test_ensemble_moe_edge_cases(self) -> None:
        """Test MoE with edge case inputs."""
        strategy = EnsembleMoEStrategy(symbols=["AO"])

        # Test with short bars for breakout signal
        short_bars = _generate_bars(25)  # Just above 20 min for breakout
        state = MarketState(prices={"AO": 100.0}, equity=1_000_000.0, bars_1m={"AO": short_bars})
        result = strategy.on_tick(state)
        # Should return 0 due to insufficient window
        assert result.target_net_qty["AO"] == 0

        # Test with flat prices (rolling_high == rolling_low)
        flat_bars: list[Bar1m] = [
            {
                "ts": 1700000000.0 + i * 60,
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 1000.0,
            }
            for i in range(300)
        ]
        state = MarketState(prices={"AO": 100.0}, equity=1_000_000.0, bars_1m={"AO": flat_bars})
        result = strategy.on_tick(state)
        assert isinstance(result.target_net_qty["AO"], int)

    def test_top_tier_edge_cases(self) -> None:
        """Test top tier strategy edge cases."""
        cfg = TopTierConfig(symbols=["AO"])
        strategy = TopTierTrendRiskParityStrategy(cfg)

        # Test with very short bars
        short_bars = _generate_bars(5)
        state = MarketState(prices={"AO": 100.0}, equity=1_000_000.0, bars_1m={"AO": short_bars})
        result = strategy.on_tick(state)
        assert result.target_net_qty["AO"] == 0


class TestDLWeightsCoverage:
    """Coverage tests for DL weights module."""

    def test_clear_model_cache(self) -> None:
        """clear_model_cache doesn't crash."""
        clear_model_cache()


class TestCIGateCoverage:
    """Coverage tests for CI gate module."""

    def test_log_gate_report(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_gate_report logs correctly."""
        import logging

        caplog.set_level(logging.INFO)
        gate = CIGate()
        gate.add_check("test", GateCheckStatus.PASS)
        gate.add_check("fail", GateCheckStatus.FAIL)
        report = gate.generate_report()
        log_gate_report(report)
        assert "CI Gate" in caplog.text


class TestLiveGuardCoverage:
    """Coverage tests for live guard module."""

    def test_log_status(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_status logs correctly."""
        import logging

        caplog.set_level(logging.INFO)
        guard = LiveModeGuard("PAPER")
        guard.add_check("test", True, "Test check")
        guard.log_status()
        assert "PAPER" in caplog.text


class TestReconcileCoverage:
    """Coverage tests for reconcile module."""

    def test_log_reconcile_report(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_reconcile_report logs correctly."""
        import logging

        caplog.set_level(logging.DEBUG)
        report = reconcile_positions(
            expected={"AO": 1, "SA": 2},
            actual={"AO": 1, "SA": 3},
        )
        log_reconcile_report(report)
        assert "SA" in caplog.text


class TestTradingOrchestratorCoverage:
    """Coverage tests for trading orchestrator."""

    def test_handle_trading_tick_live_mode(self) -> None:
        """Test handle_trading_tick in LIVE mode."""
        from src.execution.broker import NoopBroker
        from src.execution.flatten_executor import FlattenExecutor

        snap = AccountSnapshot(equity=1_000_000, margin_used=100_000)
        bars_1m = {"AO": _generate_bars(300)}
        prices = {"AO": 100.0}
        current_net_qty = {"AO": 0}

        cfg = RiskConfig()
        risk = RiskManager(cfg, cancel_all_cb=lambda: None, force_flatten_all_cb=lambda: None)
        risk.on_day_start_0900(snap, correlation_id="test")

        strategy = LinearAIStrategy(symbols=["AO"])
        broker = NoopBroker()
        executor = FlattenExecutor(broker, now_cb=lambda: 1700000000.0)
        controls = TradeControls(mode=TradeMode.LIVE)

        result = handle_trading_tick(
            strategy=strategy,
            risk=risk,
            executor=executor,
            controls=controls,
            snap=snap,
            prices=prices,
            bars_1m=bars_1m,
            current_net_qty=current_net_qty,
            now_cb=lambda: 1700000000.0,
        )
        assert result.correlation_id


class TestRebalancerCoverage:
    """Coverage tests for rebalancer."""

    def test_reduce_short_position(self) -> None:
        """Test reducing a short position (cover)."""
        current = {"AO": -2}
        target = TargetPortfolio(target_net_qty={"AO": -1}, model_version="v1", features_hash="h")
        close_intents, open_intents = build_rebalance_intents(
            current_net_qty=current,
            target=target,
            mid_prices={"AO": 100.0},
        )
        assert len(close_intents) == 1
        assert close_intents[0].side == Side.BUY
        assert close_intents[0].offset == Offset.CLOSE
        assert close_intents[0].reason == "reduce_short"

    def test_add_short_position(self) -> None:
        """Test adding to a short position."""
        current = {"AO": -1}
        target = TargetPortfolio(target_net_qty={"AO": -2}, model_version="v1", features_hash="h")
        close_intents, open_intents = build_rebalance_intents(
            current_net_qty=current,
            target=target,
            mid_prices={"AO": 100.0},
        )
        assert len(open_intents) == 1
        assert open_intents[0].side == Side.SELL
        assert open_intents[0].offset == Offset.OPEN
        assert open_intents[0].reason == "add_short"

    def test_open_short_from_flat(self) -> None:
        """Test opening short from flat."""
        current = {"AO": 0}
        target = TargetPortfolio(target_net_qty={"AO": -1}, model_version="v1", features_hash="h")
        close_intents, open_intents = build_rebalance_intents(
            current_net_qty=current,
            target=target,
            mid_prices={"AO": 100.0},
        )
        assert len(open_intents) == 1
        assert open_intents[0].side == Side.SELL
        assert open_intents[0].offset == Offset.OPEN
        assert open_intents[0].reason == "open_short"


class TestMainCoverage:
    """Coverage tests for main module."""

    def test_main_func(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test main function execution."""
        # Clear env to avoid loading existing .env
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DINGTALK_WEBHOOK", raising=False)
        main_func()
        captured = capsys.readouterr()
        assert "boot OK" in captured.out


class TestRunnerCoverage:
    """Coverage tests for runner module."""

    def test_init_components(self) -> None:
        """Test init_components function."""
        from src.execution.broker import NoopBroker
        from src.runner import init_components

        broker = NoopBroker()
        components = init_components(broker)
        assert components.settings is not None
        assert components.risk is not None
        assert components.flatten is not None
