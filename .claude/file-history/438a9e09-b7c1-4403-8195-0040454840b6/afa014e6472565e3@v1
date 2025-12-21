"""
Tests for Protection Gates.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- EXEC.PROTECTION.LIQUIDITY
- EXEC.PROTECTION.FATFINGER
- EXEC.PROTECTION.THROTTLE
"""

import pytest

from src.execution.protection.fat_finger import (
    FatFingerCheckResult,
    FatFingerConfig,
    FatFingerGate,
    OrderInput,
)
from src.execution.protection.liquidity import (
    LiquidityCheckResult,
    LiquidityConfig,
    LiquidityGate,
    Quote,
)
from src.execution.protection.throttle import (
    ThrottleCheckResult,
    ThrottleConfig,
    ThrottleGate,
)


class TestQuote:
    """Tests for Quote dataclass."""

    def test_spread_ticks(self) -> None:
        """Test spread calculation in ticks."""
        quote = Quote(
            symbol="IF2401",
            bid=4000.0,
            ask=4002.0,
            bid_volume=100,
            ask_volume=80,
            tick_size=0.2,
        )
        assert quote.spread_ticks() == 10  # (4002 - 4000) / 0.2

    def test_total_depth(self) -> None:
        """Test total depth calculation."""
        quote = Quote(
            symbol="IF2401",
            bid=4000.0,
            ask=4002.0,
            bid_volume=100,
            ask_volume=80,
            tick_size=0.2,
        )
        assert quote.total_depth() == 180


class TestLiquidityGate:
    """Tests for EXEC.PROTECTION.LIQUIDITY scenario."""

    def test_liquidity_pass(self) -> None:
        """Test liquidity check passes."""
        config = LiquidityConfig(
            max_spread_ticks=5,
            min_bid_volume=10,
            min_ask_volume=10,
            min_depth_volume=20,
        )
        gate = LiquidityGate(config=config)

        quote = Quote(
            symbol="IF2401",
            bid=4000.0,
            ask=4001.0,
            bid_volume=50,
            ask_volume=40,
            tick_size=0.2,
        )

        result = gate.check(quote)
        assert result.passed()
        assert result.result == LiquidityCheckResult.PASS

    def test_liquidity_no_quote(self) -> None:
        """Test liquidity check fails on no quote."""
        gate = LiquidityGate()
        result = gate.check(None)

        assert not result.passed()
        assert result.result == LiquidityCheckResult.NO_QUOTE

    def test_liquidity_spread_too_wide(self) -> None:
        """Test liquidity check fails on wide spread."""
        config = LiquidityConfig(max_spread_ticks=3)
        gate = LiquidityGate(config=config)

        quote = Quote(
            symbol="IF2401",
            bid=4000.0,
            ask=4010.0,  # 50 ticks with 0.2 tick size
            bid_volume=100,
            ask_volume=100,
            tick_size=0.2,
        )

        result = gate.check(quote)
        assert not result.passed()
        assert result.result == LiquidityCheckResult.SPREAD_TOO_WIDE
        assert "Spread" in result.message

    def test_liquidity_depth_too_thin(self) -> None:
        """Test liquidity check fails on thin depth."""
        config = LiquidityConfig(
            max_spread_ticks=10,
            min_bid_volume=50,
            min_ask_volume=50,
        )
        gate = LiquidityGate(config=config)

        quote = Quote(
            symbol="IF2401",
            bid=4000.0,
            ask=4001.0,
            bid_volume=30,  # Too thin
            ask_volume=100,
            tick_size=0.2,
        )

        result = gate.check(quote)
        assert not result.passed()
        assert result.result == LiquidityCheckResult.DEPTH_TOO_THIN

    def test_liquidity_stats(self) -> None:
        """Test liquidity gate statistics."""
        gate = LiquidityGate()

        quote = Quote("IF2401", 4000.0, 4001.0, 100, 100, 0.2)
        gate.check(quote)
        gate.check(None)  # Reject

        stats = gate.get_stats()
        assert stats["check_count"] == 2
        assert stats["reject_count"] == 1


class TestOrderInput:
    """Tests for OrderInput dataclass."""

    def test_notional(self) -> None:
        """Test notional calculation."""
        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=10,
            price=4000.0,
            multiplier=300.0,
        )
        assert order.notional() == 12_000_000.0  # 10 * 4000 * 300

    def test_price_deviation(self) -> None:
        """Test price deviation calculation."""
        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=10,
            price=4100.0,
            reference_price=4000.0,
        )
        assert order.price_deviation() == 0.025  # (4100-4000)/4000


class TestFatFingerGate:
    """Tests for EXEC.PROTECTION.FATFINGER scenario."""

    def test_fat_finger_pass(self) -> None:
        """Test fat finger check passes."""
        config = FatFingerConfig(
            max_qty=100,
            max_notional=10_000_000.0,
            max_price_deviation=0.05,
        )
        gate = FatFingerGate(config=config)

        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=10,
            price=4000.0,
            multiplier=300.0,  # notional = 12M but within limit
            reference_price=4000.0,
        )

        result = gate.check(order)
        assert result.passed()

    def test_fat_finger_qty_too_large(self) -> None:
        """Test fat finger check fails on large qty."""
        config = FatFingerConfig(max_qty=50)
        gate = FatFingerGate(config=config)

        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=100,  # Too large
            price=4000.0,
        )

        result = gate.check(order)
        assert not result.passed()
        assert result.result == FatFingerCheckResult.QTY_TOO_LARGE

    def test_fat_finger_notional_too_large(self) -> None:
        """Test fat finger check fails on large notional."""
        config = FatFingerConfig(max_notional=1_000_000.0)
        gate = FatFingerGate(config=config)

        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=10,
            price=4000.0,
            multiplier=300.0,  # notional = 12M
        )

        result = gate.check(order)
        assert not result.passed()
        assert result.result == FatFingerCheckResult.NOTIONAL_TOO_LARGE

    def test_fat_finger_price_deviation(self) -> None:
        """Test fat finger check fails on price deviation."""
        config = FatFingerConfig(max_price_deviation=0.03)
        gate = FatFingerGate(config=config)

        order = OrderInput(
            symbol="IF2401",
            direction="BUY",
            qty=10,
            price=4200.0,  # 5% deviation
            reference_price=4000.0,
        )

        result = gate.check(order)
        assert not result.passed()
        assert result.result == FatFingerCheckResult.PRICE_DEVIATION

    def test_fat_finger_batch_check(self) -> None:
        """Test batch checking orders."""
        gate = FatFingerGate()

        orders = [
            OrderInput("IF2401", "BUY", 10, 4000.0),
            OrderInput("IF2402", "SELL", 200, 4100.0),  # Too large
        ]

        results = gate.check_batch(orders)
        assert len(results) == 2
        assert results[0].passed()
        assert not results[1].passed()


class TestThrottleGate:
    """Tests for EXEC.PROTECTION.THROTTLE scenario."""

    def test_throttle_pass(self) -> None:
        """Test throttle check passes."""
        config = ThrottleConfig(
            max_orders_per_minute=60,
            min_interval_s=0.5,
        )
        gate = ThrottleGate(config=config)

        result = gate.check(now=1000.0)
        assert result.passed()

    def test_throttle_rate_limit(self) -> None:
        """Test throttle check fails on rate limit."""
        config = ThrottleConfig(
            max_orders_per_minute=3,
            min_interval_s=0.0,  # Disable interval check
        )
        gate = ThrottleGate(config=config)

        # Record 3 orders
        for i in range(3):
            gate.record_order(now=1000.0 + i * 0.1)

        # 4th order should fail
        result = gate.check(now=1000.5)
        assert not result.passed()
        assert result.result == ThrottleCheckResult.RATE_LIMIT_EXCEEDED

    def test_throttle_min_interval(self) -> None:
        """Test throttle check fails on min interval."""
        config = ThrottleConfig(
            max_orders_per_minute=60,
            min_interval_s=1.0,
        )
        gate = ThrottleGate(config=config)

        gate.record_order(now=1000.0)

        # Too soon
        result = gate.check(now=1000.5)
        assert not result.passed()
        assert result.result == ThrottleCheckResult.MIN_INTERVAL_VIOLATED
        assert result.wait_time_s == pytest.approx(0.5, abs=0.01)

    def test_throttle_check_and_record(self) -> None:
        """Test check_and_record auto-records on pass."""
        config = ThrottleConfig(min_interval_s=0.0)
        gate = ThrottleGate(config=config)

        result = gate.check_and_record(now=1000.0)
        assert result.passed()
        assert result.orders_in_window == 1  # Recorded

    def test_throttle_remaining_capacity(self) -> None:
        """Test remaining capacity calculation."""
        config = ThrottleConfig(max_orders_per_minute=10)
        gate = ThrottleGate(config=config)

        for i in range(5):
            gate.record_order(now=1000.0 + i)

        remaining = gate.get_remaining_capacity(now=1005.0)
        assert remaining == 5

    def test_throttle_next_available_time(self) -> None:
        """Test next available time calculation."""
        config = ThrottleConfig(
            max_orders_per_minute=2,
            min_interval_s=1.0,
            window_s=60.0,
        )
        gate = ThrottleGate(config=config)

        gate.record_order(now=1000.0)
        gate.record_order(now=1001.0)

        # Rate limited, need to wait for window
        next_time = gate.get_next_available_time(now=1001.5)
        assert next_time == 1060.0  # First order + window

    def test_throttle_window_cleanup(self) -> None:
        """Test orders expire after window."""
        config = ThrottleConfig(
            max_orders_per_minute=2,
            window_s=60.0,
        )
        gate = ThrottleGate(config=config)

        gate.record_order(now=1000.0)
        gate.record_order(now=1001.0)

        # Should fail at 1001.5
        result = gate.check(now=1001.5)
        assert not result.passed()

        # Should pass after window expires
        result = gate.check(now=1061.0)
        assert result.passed()

    def test_throttle_reset(self) -> None:
        """Test throttle reset."""
        gate = ThrottleGate()
        gate.record_order(now=1000.0)

        gate.reset()
        assert gate.get_remaining_capacity() == gate.config.max_orders_per_minute

    def test_throttle_stats(self) -> None:
        """Test throttle statistics."""
        config = ThrottleConfig(min_interval_s=1.0)
        gate = ThrottleGate(config=config)

        gate.check_and_record(now=1000.0)
        gate.check(now=1000.5)  # Rejected

        stats = gate.get_stats()
        assert stats["check_count"] == 2
        assert stats["reject_count"] == 1
