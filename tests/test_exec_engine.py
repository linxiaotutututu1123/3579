"""
Tests for AutoOrderEngine.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- EXEC.ENGINE.PIPELINE
- EXEC.CANCEL_REPRICE.TIMEOUT
- EXEC.PARTIAL.REPRICE
"""


from src.execution.auto.engine import AutoOrderEngine, EngineConfig, OrderResult
from src.execution.auto.order_context import OrderContext
from src.execution.auto.state_machine import OrderEvent, OrderState
from src.execution.auto.timeout import TimeoutConfig, TimeoutType


class TestAutoOrderEngineBasic:
    """Basic tests for AutoOrderEngine."""

    def test_engine_creation(self) -> None:
        """Test engine creation."""
        engine = AutoOrderEngine()
        assert len(engine) == 0
        assert engine.registry is not None
        assert engine.timeout_manager is not None
        assert engine.retry_policy is not None

    def test_engine_with_config(self) -> None:
        """Test engine with custom config."""
        config = EngineConfig(
            timeout_config=TimeoutConfig(ack_timeout_s=3.0),
        )
        engine = AutoOrderEngine(config=config)
        assert engine.timeout_manager.config.ack_timeout_s == 3.0


class TestEngineSubmit:
    """Tests for EXEC.ENGINE.PIPELINE scenario."""

    def test_submit_order(self) -> None:
        """Test order submission pipeline."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)

        assert local_id == ctx.local_id
        assert engine.get_state(local_id) == OrderState.SUBMITTING
        assert len(engine) == 1

    def test_submit_registers_ack_timeout(self) -> None:
        """Test submit registers ACK timeout."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)

        assert engine.timeout_manager.has_timeout(local_id, TimeoutType.ACK)

    def test_submit_emits_event(self) -> None:
        """Test submit emits order event."""
        events = []

        def on_event(local_id: str, state: OrderState, event: OrderEvent) -> None:
            events.append((local_id, state, event))

        engine = AutoOrderEngine(on_order_event=on_event)

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)

        assert len(events) == 1
        assert events[0][0] == local_id
        assert events[0][2] == OrderEvent.SUBMIT


class TestEngineCancel:
    """Tests for cancel functionality."""

    def test_cancel_pending_order(self) -> None:
        """Test canceling pending order."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)

        # Simulate ACK
        engine.on_rtn_order(local_id, status="3")
        assert engine.get_state(local_id) == OrderState.PENDING

        # Cancel
        result = engine.cancel(local_id)
        assert result is True
        assert engine.get_state(local_id) == OrderState.CANCEL_SUBMITTING

    def test_cancel_submitting_order_fails(self) -> None:
        """Test cannot cancel order in SUBMITTING state."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        assert engine.get_state(local_id) == OrderState.SUBMITTING

        result = engine.cancel(local_id)
        assert result is False


class TestEngineRtnOrder:
    """Tests for order return handling."""

    def test_on_rtn_order_ack(self) -> None:
        """Test processing ACK response."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)

        # Simulate ACK (status='3': 未成交还在队列中)
        engine.on_rtn_order(local_id, order_sys_id="SYS001", status="3")

        assert engine.get_state(local_id) == OrderState.PENDING
        # Verify order_sys_id mapping
        retrieved = engine.registry.get_by_order_sys_id("SYS001")
        assert retrieved is not None
        assert retrieved.local_id == local_id

    def test_on_rtn_order_fill(self) -> None:
        """Test processing FILL response."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        engine.on_rtn_order(local_id, status="3")  # ACK

        # Simulate FILL (status='0': 全部成交)
        engine.on_rtn_order(local_id, status="0", filled_qty=10)

        assert engine.get_state(local_id) == OrderState.FILLED

        result = engine.get_result(local_id)
        assert result is not None
        assert result.is_success()

    def test_on_rtn_order_cancel_ack(self) -> None:
        """Test processing cancel ACK."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        engine.on_rtn_order(local_id, status="3")  # ACK
        engine.cancel(local_id)  # Request cancel

        # Simulate cancel success (status='4' means order out of queue)
        # Actually '4' with no fills triggers STATUS_4 event
        # For actual cancelled, we need CANCEL_ACK which comes differently
        # Let's simulate via the state machine directly for this test
        fsm = engine._fsm_map[local_id]
        fsm.transition(OrderEvent.CANCEL_ACK)

        assert engine.get_state(local_id) == OrderState.CANCELLED


class TestEngineRtnTrade:
    """Tests for trade return handling."""

    def test_on_rtn_trade_fill(self) -> None:
        """Test processing trade fill."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        engine.on_rtn_order(local_id, status="3")  # ACK

        # Process trade
        engine.on_rtn_trade(local_id, trade_id="T001", volume=10, price=4000.0)

        assert engine.get_state(local_id) == OrderState.FILLED

    def test_on_rtn_trade_partial_fill(self) -> None:
        """Test processing partial trade fill."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        engine.on_rtn_order(local_id, status="3")  # ACK

        # Process partial trade
        engine.on_rtn_trade(local_id, trade_id="T001", volume=5, price=4000.0)

        assert engine.get_state(local_id) == OrderState.PARTIAL_FILLED


class TestEngineTimeout:
    """Tests for EXEC.CANCEL_REPRICE.TIMEOUT scenario."""

    def test_check_timeouts(self) -> None:
        """Test checking for expired timeouts."""
        config = EngineConfig(
            timeout_config=TimeoutConfig(ack_timeout_s=5.0),
        )
        engine = AutoOrderEngine(config=config)

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        ctx.created_at = 1000.0

        local_id = engine.submit(ctx)

        # Register timeout manually with specific time
        engine.timeout_manager.cancel_all_for_order(local_id)
        engine.timeout_manager.register_ack_timeout(local_id, now=1000.0)

        # Check before expiry
        expired = engine.check_timeouts(now=1003.0)
        assert len(expired) == 0

        # Check after expiry
        expired = engine.check_timeouts(now=1006.0)
        assert len(expired) == 1
        assert expired[0] == local_id


class TestEngineActiveOrders:
    """Tests for active order tracking."""

    def test_get_active_orders(self) -> None:
        """Test getting active orders."""
        engine = AutoOrderEngine()

        ctx1 = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        ctx2 = OrderContext(
            symbol="IF2402",
            direction="SELL",
            offset="OPEN",
            qty=5,
            price=4100.0,
        )

        local_id1 = engine.submit(ctx1)
        local_id2 = engine.submit(ctx2)

        active = engine.get_active_orders()
        assert len(active) == 2
        assert local_id1 in active
        assert local_id2 in active

    def test_get_active_orders_excludes_terminal(self) -> None:
        """Test active orders excludes terminal states."""
        engine = AutoOrderEngine()

        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        local_id = engine.submit(ctx)
        engine.on_rtn_order(local_id, status="3")  # ACK
        engine.on_rtn_trade(local_id, trade_id="T001", volume=10, price=4000.0)  # FILL

        active = engine.get_active_orders()
        assert len(active) == 0


class TestOrderResult:
    """Tests for OrderResult."""

    def test_order_result_success(self) -> None:
        """Test successful order result."""
        result = OrderResult(
            local_id="order1",
            state=OrderState.FILLED,
            filled_qty=10,
            avg_price=4000.0,
        )

        assert result.is_success()
        assert not result.is_partial()

    def test_order_result_partial(self) -> None:
        """Test partial order result."""
        result = OrderResult(
            local_id="order1",
            state=OrderState.PARTIAL_CANCELLED,
            filled_qty=5,
            avg_price=4000.0,
        )

        assert not result.is_success()
        assert result.is_partial()

    def test_order_result_error(self) -> None:
        """Test error order result."""
        result = OrderResult(
            local_id="order1",
            state=OrderState.REJECTED,
            filled_qty=0,
            error="Insufficient margin",
        )

        assert not result.is_success()
        assert not result.is_partial()
        assert result.error == "Insufficient margin"
