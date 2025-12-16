"""
Tests for ExecContext.

V3PRO+ Platform - Phase 2
V2 Scenario: EXEC.CONTEXT.TRACKING
"""


from src.execution.auto.exec_context import (
    ExecContext,
    ExecContextManager,
    ExecOrder,
    ExecStatus,
)


class TestExecOrder:
    """Tests for ExecOrder."""

    def test_exec_order_creation(self) -> None:
        """Test ExecOrder creation."""
        order = ExecOrder(
            local_id="order1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
        )

        assert order.local_id == "order1"
        assert order.symbol == "IF2401"
        assert order.direction == "BUY"
        assert order.target_qty == 10
        assert order.filled_qty == 0
        assert order.status == "PENDING"

    def test_exec_order_is_complete(self) -> None:
        """Test ExecOrder is_complete check."""
        order = ExecOrder(
            local_id="order1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
            filled_qty=5,
        )

        assert not order.is_complete()

        order.filled_qty = 10
        assert order.is_complete()

    def test_exec_order_remaining_qty(self) -> None:
        """Test ExecOrder remaining_qty calculation."""
        order = ExecOrder(
            local_id="order1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
            filled_qty=3,
        )

        assert order.remaining_qty() == 7


class TestExecContext:
    """Tests for ExecContext.

    V2 Scenario: EXEC.CONTEXT.TRACKING
    """

    def test_exec_context_creation(self) -> None:
        """Test ExecContext creation."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={"IF2401": 10, "IF2402": -5},
            current_portfolio={"IF2401": 5},
        )

        assert ctx.run_id == "run1"
        assert ctx.strategy_id == "strat1"
        assert ctx.exec_id is not None
        assert len(ctx.exec_id) == 36  # UUID format
        assert ctx.status == ExecStatus.PENDING

    def test_exec_context_get_delta(self) -> None:
        """Test EXEC.CONTEXT.TRACKING: delta calculation."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={"IF2401": 10, "IF2402": -5},
            current_portfolio={"IF2401": 5, "IF2403": 3},
        )

        delta = ctx.get_delta()
        assert delta["IF2401"] == 5  # 10 - 5
        assert delta["IF2402"] == -5  # -5 - 0
        assert delta["IF2403"] == -3  # 0 - 3

    def test_exec_context_add_order(self) -> None:
        """Test adding orders to context."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        order = ExecOrder(
            local_id="order1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
        )
        ctx.add_order(order)

        assert len(ctx.orders) == 1
        assert ctx.get_order("order1") is not None

    def test_exec_context_update_order(self) -> None:
        """Test updating order in context."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        order = ExecOrder(
            local_id="order1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
        )
        ctx.add_order(order)

        assert ctx.update_order("order1", filled_qty=5, status="PARTIAL")
        assert ctx.get_order("order1").filled_qty == 5
        assert ctx.get_order("order1").status == "PARTIAL"

    def test_exec_context_progress(self) -> None:
        """Test progress tracking."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        ctx.add_order(ExecOrder("o1", "IF2401", "BUY", 10, filled_qty=10))
        ctx.add_order(ExecOrder("o2", "IF2402", "SELL", 5, filled_qty=3))

        completed, total = ctx.get_progress()
        assert completed == 1
        assert total == 2

    def test_exec_context_fill_rate(self) -> None:
        """Test fill rate calculation."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        ctx.add_order(ExecOrder("o1", "IF2401", "BUY", 10, filled_qty=8))
        ctx.add_order(ExecOrder("o2", "IF2402", "SELL", 10, filled_qty=5))

        fill_rate = ctx.get_fill_rate()
        assert fill_rate == 0.65  # 13 / 20

    def test_exec_context_start(self) -> None:
        """Test starting execution."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        ctx.start()
        assert ctx.status == ExecStatus.RUNNING
        assert ctx.started_at > 0
        assert ctx.is_running()

    def test_exec_context_complete(self) -> None:
        """Test completing execution."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        ctx.start()
        ctx.complete()
        assert ctx.status == ExecStatus.COMPLETED
        assert ctx.completed_at > 0
        assert ctx.is_complete()

    def test_exec_context_fail(self) -> None:
        """Test failing execution."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        ctx.start()
        ctx.fail("Network error")
        assert ctx.status == ExecStatus.FAILED
        assert ctx.error == "Network error"

    def test_exec_context_to_dict(self) -> None:
        """Test conversion to dictionary."""
        ctx = ExecContext(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={"IF2401": 10},
            current_portfolio={"IF2401": 5},
        )

        d = ctx.to_dict()
        assert d["run_id"] == "run1"
        assert d["strategy_id"] == "strat1"
        assert d["status"] == "PENDING"


class TestExecContextManager:
    """Tests for ExecContextManager."""

    def test_manager_create(self) -> None:
        """Test creating context via manager."""
        mgr = ExecContextManager()

        ctx = mgr.create(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={"IF2401": 10},
            current_portfolio={"IF2401": 5},
        )

        assert ctx.run_id == "run1"
        assert len(mgr) == 1

    def test_manager_get(self) -> None:
        """Test getting context from manager."""
        mgr = ExecContextManager()

        ctx = mgr.create(
            run_id="run1",
            strategy_id="strat1",
            target_portfolio={},
            current_portfolio={},
        )

        retrieved = mgr.get(ctx.exec_id)
        assert retrieved is not None
        assert retrieved.run_id == "run1"

    def test_manager_get_active(self) -> None:
        """Test getting active contexts."""
        mgr = ExecContextManager()

        ctx1 = mgr.create("run1", "strat1", {}, {})
        ctx2 = mgr.create("run2", "strat1", {}, {})

        ctx1.start()  # Running
        # ctx2 is still pending

        active = mgr.get_active()
        assert len(active) == 1
        assert active[0].run_id == "run1"

    def test_manager_complete_moves_to_history(self) -> None:
        """Test completing context moves to history."""
        mgr = ExecContextManager()

        ctx = mgr.create("run1", "strat1", {}, {})
        exec_id = ctx.exec_id
        ctx.complete()

        assert mgr.complete(exec_id)
        assert len(mgr) == 0

        history = mgr.get_history()
        assert len(history) == 1
        assert history[0].exec_id == exec_id

    def test_manager_history_limit(self) -> None:
        """Test history limit."""
        mgr = ExecContextManager(max_history=2)

        for i in range(3):
            ctx = mgr.create(f"run{i}", "strat1", {}, {})
            ctx.complete()
            mgr.complete(ctx.exec_id)

        history = mgr.get_history()
        assert len(history) == 2
        assert history[0].run_id == "run1"
        assert history[1].run_id == "run2"
