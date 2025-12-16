"""
Tests for RetryPolicy.

V3PRO+ Platform - Phase 2
V2 Scenario: EXEC.RETRY.BACKOFF
"""

from src.execution.auto.retry import (
    RepriceMode,
    RetryConfig,
    RetryPolicy,
    RetryReason,
    RetryState,
)


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self) -> None:
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_s == 1.0
        assert config.max_delay_s == 30.0
        assert config.backoff_factor == 2.0
        assert config.reprice_mode == RepriceMode.TO_BEST

    def test_custom_config(self) -> None:
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay_s=0.5,
            max_delay_s=60.0,
            backoff_factor=1.5,
            reprice_mode=RepriceMode.TO_CROSS,
        )
        assert config.max_retries == 5
        assert config.base_delay_s == 0.5
        assert config.backoff_factor == 1.5
        assert config.reprice_mode == RepriceMode.TO_CROSS


class TestRetryState:
    """Tests for RetryState."""

    def test_can_retry(self) -> None:
        """Test can_retry check."""
        state = RetryState(local_id="order1", retry_count=2)
        assert state.can_retry(max_retries=3)
        assert not state.can_retry(max_retries=2)

    def test_is_ready(self) -> None:
        """Test is_ready check."""
        now = 1000.0
        state = RetryState(
            local_id="order1",
            retry_count=1,
            next_retry_at=now + 5.0,
        )
        assert not state.is_ready(now + 3.0)
        assert state.is_ready(now + 6.0)


class TestRetryPolicyBackoff:
    """Tests for EXEC.RETRY.BACKOFF scenario."""

    def test_calculate_delay_exponential(self) -> None:
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay_s=1.0,
            backoff_factor=2.0,
            max_delay_s=30.0,
        )
        policy = RetryPolicy(config=config)

        # First retry: 1.0 * 2^0 = 1.0
        assert policy.calculate_delay(0) == 1.0

        # Second retry: 1.0 * 2^1 = 2.0
        assert policy.calculate_delay(1) == 2.0

        # Third retry: 1.0 * 2^2 = 4.0
        assert policy.calculate_delay(2) == 4.0

        # Fourth retry: 1.0 * 2^3 = 8.0
        assert policy.calculate_delay(3) == 8.0

    def test_calculate_delay_max_cap(self) -> None:
        """Test delay is capped at max_delay."""
        config = RetryConfig(
            base_delay_s=1.0,
            backoff_factor=2.0,
            max_delay_s=10.0,
        )
        policy = RetryPolicy(config=config)

        # 1.0 * 2^4 = 16.0, but capped at 10.0
        assert policy.calculate_delay(4) == 10.0

        # Higher retry counts still capped
        assert policy.calculate_delay(10) == 10.0

    def test_register_retry_increments_count(self) -> None:
        """Test register_retry increments count."""
        now = 1000.0
        policy = RetryPolicy()

        state = policy.register_retry(
            "order1",
            RetryReason.ACK_TIMEOUT,
            now=now,
        )

        assert state.retry_count == 1
        assert state.reason == RetryReason.ACK_TIMEOUT
        assert state.last_retry_at == now

    def test_register_retry_sets_next_retry_at(self) -> None:
        """Test register_retry sets next_retry_at with backoff."""
        now = 1000.0
        config = RetryConfig(base_delay_s=1.0, backoff_factor=2.0)
        policy = RetryPolicy(config=config)

        # First retry
        state = policy.register_retry("order1", RetryReason.ACK_TIMEOUT, now=now)
        assert state.next_retry_at == now + 1.0  # base_delay

        # Second retry
        state = policy.register_retry("order1", RetryReason.ACK_TIMEOUT, now=now + 2.0)
        assert state.retry_count == 2
        assert state.next_retry_at == now + 2.0 + 2.0  # base * 2

    def test_should_retry_first_time(self) -> None:
        """Test should_retry returns True for first retry."""
        policy = RetryPolicy()
        assert policy.should_retry("order1", RetryReason.ACK_TIMEOUT)

    def test_should_retry_within_max(self) -> None:
        """Test should_retry returns True within max_retries."""
        config = RetryConfig(max_retries=3)
        policy = RetryPolicy(config=config)

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert policy.should_retry("order1", RetryReason.ACK_TIMEOUT)

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert policy.should_retry("order1", RetryReason.ACK_TIMEOUT)

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert not policy.should_retry("order1", RetryReason.ACK_TIMEOUT)


class TestRetryPolicyReprice:
    """Tests for reprice calculation."""

    def test_reprice_buy_to_best(self) -> None:
        """Test reprice BUY order TO_BEST."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_BEST)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="BUY",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=1.0,
        )
        assert price == 101.0  # Ask price

    def test_reprice_sell_to_best(self) -> None:
        """Test reprice SELL order TO_BEST."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_BEST)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="SELL",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=1.0,
        )
        assert price == 99.0  # Bid price

    def test_reprice_buy_to_best_plus_tick(self) -> None:
        """Test reprice BUY order TO_BEST_PLUS_TICK."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_BEST_PLUS_TICK)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="BUY",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=0.5,
        )
        assert price == 101.5  # Ask + 1 tick

    def test_reprice_sell_to_best_plus_tick(self) -> None:
        """Test reprice SELL order TO_BEST_PLUS_TICK."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_BEST_PLUS_TICK)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="SELL",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=0.5,
        )
        assert price == 98.5  # Bid - 1 tick

    def test_reprice_buy_to_cross(self) -> None:
        """Test reprice BUY order TO_CROSS."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_CROSS)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="BUY",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=0.5,
        )
        assert price == 102.0  # Ask + 2 ticks

    def test_reprice_sell_to_cross(self) -> None:
        """Test reprice SELL order TO_CROSS."""
        config = RetryConfig(reprice_mode=RepriceMode.TO_CROSS)
        policy = RetryPolicy(config=config)

        price = policy.calculate_reprice(
            direction="SELL",
            original_price=100.0,
            bid=99.0,
            ask=101.0,
            tick_size=0.5,
        )
        assert price == 98.0  # Bid - 2 ticks


class TestRetryPolicyOperations:
    """Tests for RetryPolicy operations."""

    def test_get_state(self) -> None:
        """Test getting retry state."""
        policy = RetryPolicy()

        assert policy.get_state("order1") is None

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        state = policy.get_state("order1")
        assert state is not None
        assert state.local_id == "order1"

    def test_get_retry_count(self) -> None:
        """Test getting retry count."""
        policy = RetryPolicy()

        assert policy.get_retry_count("order1") == 0

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert policy.get_retry_count("order1") == 1

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert policy.get_retry_count("order1") == 2

    def test_clear_state(self) -> None:
        """Test clearing retry state."""
        policy = RetryPolicy()

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        assert len(policy) == 1

        assert policy.clear_state("order1")
        assert len(policy) == 0

    def test_clear_nonexistent_state(self) -> None:
        """Test clearing non-existent state."""
        policy = RetryPolicy()
        assert not policy.clear_state("order1")

    def test_get_ready_retries(self) -> None:
        """Test getting ready retries."""
        now = 1000.0
        config = RetryConfig(base_delay_s=5.0)
        policy = RetryPolicy(config=config)

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT, now=now)
        policy.register_retry("order2", RetryReason.ACK_TIMEOUT, now=now + 3.0)

        # Neither ready yet
        ready = policy.get_ready_retries(now + 2.0)
        assert len(ready) == 0

        # order1 ready
        ready = policy.get_ready_retries(now + 6.0)
        assert len(ready) == 1
        assert ready[0].local_id == "order1"

        # Both ready
        ready = policy.get_ready_retries(now + 10.0)
        assert len(ready) == 2

    def test_clear_all(self) -> None:
        """Test clearing all states."""
        policy = RetryPolicy()

        policy.register_retry("order1", RetryReason.ACK_TIMEOUT)
        policy.register_retry("order2", RetryReason.FILL_TIMEOUT)
        assert len(policy) == 2

        policy.clear()
        assert len(policy) == 0
