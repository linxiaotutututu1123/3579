"""
Tests for OrderFSM - Order State Machine.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- FSM.STRICT.TRANSITIONS
- FSM.TOLERANT.IDEMPOTENT
- FSM.CANCEL_WHILE_FILL
- FSM.STATUS_4_MAPPING
"""

import pytest

from src.execution.auto.state_machine import (
    CANCELLABLE_STATES,
    TERMINAL_STATES,
    OrderEvent,
    OrderFSM,
    OrderState,
    handle_cancel_while_fill,
    handle_status_4,
)


class TestOrderStateEnum:
    """Tests for OrderState enum."""

    def test_terminal_states(self) -> None:
        """Test terminal states set."""
        assert OrderState.FILLED in TERMINAL_STATES
        assert OrderState.CANCELLED in TERMINAL_STATES
        assert OrderState.PARTIAL_CANCELLED in TERMINAL_STATES
        assert OrderState.CANCEL_REJECTED in TERMINAL_STATES
        assert OrderState.REJECTED in TERMINAL_STATES
        assert OrderState.ERROR in TERMINAL_STATES
        assert len(TERMINAL_STATES) == 6

    def test_cancellable_states(self) -> None:
        """Test cancellable states set."""
        assert OrderState.PENDING in CANCELLABLE_STATES
        assert OrderState.PARTIAL_FILLED in CANCELLABLE_STATES
        assert len(CANCELLABLE_STATES) == 2


class TestOrderFSMBasic:
    """Basic tests for OrderFSM."""

    def test_fsm_initial_state(self) -> None:
        """Test FSM initial state."""
        fsm = OrderFSM()
        assert fsm.state == OrderState.CREATED
        assert not fsm.is_terminal()
        assert fsm.transition_count == 0

    def test_fsm_custom_initial_state(self) -> None:
        """Test FSM with custom initial state."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        assert fsm.state == OrderState.PENDING

    def test_fsm_mode_strict(self) -> None:
        """Test FSM strict mode."""
        fsm = OrderFSM(mode="strict")
        assert fsm.mode == "strict"

    def test_fsm_mode_tolerant(self) -> None:
        """Test FSM tolerant mode."""
        fsm = OrderFSM(mode="tolerant")
        assert fsm.mode == "tolerant"


class TestFSMStrictTransitions:
    """Tests for FSM.STRICT.TRANSITIONS scenario."""

    def test_created_to_submitting(self) -> None:
        """Test CREATED -> SUBMITTING on SUBMIT."""
        fsm = OrderFSM()
        fsm.transition(OrderEvent.SUBMIT)
        assert fsm.state == OrderState.SUBMITTING
        assert fsm.transition_count == 1

    def test_submitting_to_pending(self) -> None:
        """Test SUBMITTING -> PENDING on ACK."""
        fsm = OrderFSM(initial_state=OrderState.SUBMITTING)
        fsm.transition(OrderEvent.ACK)
        assert fsm.state == OrderState.PENDING

    def test_submitting_to_rejected(self) -> None:
        """Test SUBMITTING -> REJECTED on REJECT."""
        fsm = OrderFSM(initial_state=OrderState.SUBMITTING)
        fsm.transition(OrderEvent.REJECT)
        assert fsm.state == OrderState.REJECTED
        assert fsm.is_terminal()

    def test_pending_to_filled(self) -> None:
        """Test PENDING -> FILLED on FILL."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        fsm.transition(OrderEvent.FILL, filled_qty=10)
        assert fsm.state == OrderState.FILLED
        assert fsm.is_terminal()
        assert fsm.filled_qty == 10

    def test_pending_to_partial_filled(self) -> None:
        """Test PENDING -> PARTIAL_FILLED on PARTIAL_FILL."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        fsm.transition(OrderEvent.PARTIAL_FILL, filled_qty=5)
        assert fsm.state == OrderState.PARTIAL_FILLED
        assert fsm.filled_qty == 5

    def test_partial_filled_to_filled(self) -> None:
        """Test PARTIAL_FILLED -> FILLED on FILL."""
        fsm = OrderFSM(initial_state=OrderState.PARTIAL_FILLED)
        fsm._filled_qty = 5  # Already partially filled
        fsm.transition(OrderEvent.FILL, filled_qty=5)
        assert fsm.state == OrderState.FILLED
        assert fsm.filled_qty == 10

    def test_pending_to_cancel_submitting(self) -> None:
        """Test PENDING -> CANCEL_SUBMITTING on CANCEL_REQUEST."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        fsm.transition(OrderEvent.CANCEL_REQUEST)
        assert fsm.state == OrderState.CANCEL_SUBMITTING

    def test_cancel_submitting_to_cancelled(self) -> None:
        """Test CANCEL_SUBMITTING -> CANCELLED on CANCEL_ACK."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        fsm.transition(OrderEvent.CANCEL_ACK)
        assert fsm.state == OrderState.CANCELLED
        assert fsm.is_terminal()

    def test_cancel_submitting_to_cancel_rejected(self) -> None:
        """Test CANCEL_SUBMITTING -> CANCEL_REJECTED on CANCEL_REJECT."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        fsm.transition(OrderEvent.CANCEL_REJECT)
        assert fsm.state == OrderState.CANCEL_REJECTED
        assert fsm.is_terminal()

    def test_submitting_to_querying_on_ack_timeout(self) -> None:
        """Test SUBMITTING -> QUERYING on ACK_TIMEOUT."""
        fsm = OrderFSM(initial_state=OrderState.SUBMITTING)
        fsm.transition(OrderEvent.ACK_TIMEOUT)
        assert fsm.state == OrderState.QUERYING

    def test_partial_filled_to_chase_pending(self) -> None:
        """Test PARTIAL_FILLED -> CHASE_PENDING on CHASE."""
        fsm = OrderFSM(initial_state=OrderState.PARTIAL_FILLED)
        fsm.transition(OrderEvent.CHASE)
        assert fsm.state == OrderState.CHASE_PENDING


class TestFSMTolerantIdempotent:
    """Tests for FSM.TOLERANT.IDEMPOTENT scenario."""

    def test_terminal_state_ignores_events(self) -> None:
        """Test terminal state ignores all events (idempotent)."""
        fsm = OrderFSM(initial_state=OrderState.FILLED, mode="tolerant")

        # All these should be ignored
        fsm.transition(OrderEvent.FILL)
        assert fsm.state == OrderState.FILLED

        fsm.transition(OrderEvent.CANCEL_REQUEST)
        assert fsm.state == OrderState.FILLED

        fsm.transition(OrderEvent.ACK)
        assert fsm.state == OrderState.FILLED

    def test_tolerant_mode_ignores_invalid_transition(self) -> None:
        """Test tolerant mode ignores invalid transitions."""
        fsm = OrderFSM(initial_state=OrderState.PENDING, mode="tolerant")

        # Invalid transition (PENDING + ACK)
        fsm.transition(OrderEvent.ACK)
        assert fsm.state == OrderState.PENDING  # State unchanged

    def test_strict_mode_raises_on_invalid_transition(self) -> None:
        """Test strict mode raises on invalid transitions."""
        fsm = OrderFSM(initial_state=OrderState.PENDING, mode="strict")

        with pytest.raises(ValueError, match="No transition"):
            fsm.transition(OrderEvent.ACK)

    def test_invalid_transition_callback(self) -> None:
        """Test invalid transition callback is called."""
        callback_called = []

        def on_invalid(state: OrderState, event: OrderEvent, reason: str) -> None:
            callback_called.append((state, event, reason))

        fsm = OrderFSM(
            initial_state=OrderState.PENDING,
            mode="tolerant",
            on_invalid_transition=on_invalid,
        )
        fsm.transition(OrderEvent.ACK)

        assert len(callback_called) == 1
        assert callback_called[0][0] == OrderState.PENDING
        assert callback_called[0][1] == OrderEvent.ACK


class TestFSMCancelWhileFill:
    """Tests for FSM.CANCEL_WHILE_FILL scenario."""

    def test_cancel_submitting_receives_fill(self) -> None:
        """Test CANCEL_SUBMITTING + FILL -> FILLED."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        result = handle_cancel_while_fill(fsm, OrderEvent.FILL)
        assert result == OrderState.FILLED
        assert fsm.is_terminal()

    def test_cancel_submitting_receives_partial_fill(self) -> None:
        """Test CANCEL_SUBMITTING + PARTIAL_FILL -> PARTIAL_CANCELLED."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        result = handle_cancel_while_fill(fsm, OrderEvent.PARTIAL_FILL)
        assert result == OrderState.PARTIAL_CANCELLED
        assert fsm.is_terminal()


class TestFSMStatus4Mapping:
    """Tests for FSM.STATUS_4_MAPPING scenario."""

    def test_status_4_no_fills_to_error(self) -> None:
        """Test STATUS_4 with no fills -> ERROR."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        result = handle_status_4(fsm, has_fills=False)
        assert result == OrderState.ERROR
        assert fsm.is_terminal()

    def test_status_4_with_fills_to_partial_cancelled(self) -> None:
        """Test STATUS_4 with fills -> PARTIAL_CANCELLED."""
        fsm = OrderFSM(initial_state=OrderState.CANCEL_SUBMITTING)
        fsm._filled_qty = 5  # Has fills
        result = handle_status_4(fsm, has_fills=True)
        assert result == OrderState.PARTIAL_CANCELLED
        assert fsm.is_terminal()


class TestFSMCanCancel:
    """Tests for can_cancel functionality."""

    def test_can_cancel_pending(self) -> None:
        """Test can cancel from PENDING state."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        assert fsm.can_cancel()

    def test_can_cancel_partial_filled(self) -> None:
        """Test can cancel from PARTIAL_FILLED state."""
        fsm = OrderFSM(initial_state=OrderState.PARTIAL_FILLED)
        assert fsm.can_cancel()

    def test_cannot_cancel_submitting(self) -> None:
        """Test cannot cancel from SUBMITTING state."""
        fsm = OrderFSM(initial_state=OrderState.SUBMITTING)
        assert not fsm.can_cancel()

    def test_cannot_cancel_terminal(self) -> None:
        """Test cannot cancel from terminal state."""
        fsm = OrderFSM(initial_state=OrderState.FILLED)
        assert not fsm.can_cancel()


class TestFSMReset:
    """Tests for FSM reset functionality."""

    def test_reset_to_created(self) -> None:
        """Test reset to CREATED state."""
        fsm = OrderFSM()
        fsm.transition(OrderEvent.SUBMIT)
        fsm.transition(OrderEvent.ACK)
        assert fsm.state == OrderState.PENDING
        assert fsm.transition_count == 2

        fsm.reset()
        assert fsm.state == OrderState.CREATED
        assert fsm.transition_count == 0
        assert fsm.filled_qty == 0

    def test_reset_to_custom_state(self) -> None:
        """Test reset to custom state."""
        fsm = OrderFSM()
        fsm.transition(OrderEvent.SUBMIT)
        fsm.reset(OrderState.PENDING)
        assert fsm.state == OrderState.PENDING


class TestFSMToDict:
    """Tests for FSM to_dict functionality."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        fsm = OrderFSM(initial_state=OrderState.PENDING)
        fsm._filled_qty = 5

        d = fsm.to_dict()
        assert d["state"] == "PENDING"
        assert d["mode"] == "tolerant"
        assert d["is_terminal"] is False
        assert d["can_cancel"] is True
        assert d["filled_qty"] == 5
