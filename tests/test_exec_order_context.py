"""
Tests for OrderContext and OrderContextRegistry.

V3PRO+ Platform - Phase 2
V2 Scenario: EXEC.ID.MAPPING
"""

import pytest

from src.execution.auto.order_context import OrderContext, OrderContextRegistry


class TestOrderContext:
    """Tests for OrderContext."""

    def test_order_context_creation(self) -> None:
        """Test basic OrderContext creation."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        assert ctx.symbol == "IF2401"
        assert ctx.direction == "BUY"
        assert ctx.offset == "OPEN"
        assert ctx.qty == 10
        assert ctx.price == 4000.0
        assert ctx.local_id is not None
        assert len(ctx.local_id) == 36  # UUID format

    def test_order_context_set_order_ref(self) -> None:
        """Test setting order reference."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        assert not ctx.has_order_ref()
        ctx.set_order_ref("REF001")
        assert ctx.has_order_ref()
        assert ctx.order_ref == "REF001"

    def test_order_context_set_order_sys_id(self) -> None:
        """Test setting order system ID."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        assert not ctx.has_order_sys_id()
        ctx.set_order_sys_id("SYS001")
        assert ctx.has_order_sys_id()
        assert ctx.order_sys_id == "SYS001"

    def test_order_context_set_session_info(self) -> None:
        """Test setting session info."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        ctx.set_session_info(front_id=1, session_id=12345)
        assert ctx.front_id == 1
        assert ctx.session_id == 12345

    def test_order_context_can_cancel_by_sys_id(self) -> None:
        """Test can_cancel_by_sys_id."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        assert not ctx.can_cancel_by_sys_id()
        ctx.set_order_sys_id("SYS001")
        assert ctx.can_cancel_by_sys_id()

    def test_order_context_can_cancel_by_ref(self) -> None:
        """Test can_cancel_by_ref."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        assert not ctx.can_cancel_by_ref()
        ctx.set_order_ref("REF001")
        assert not ctx.can_cancel_by_ref()  # Still needs front_id
        ctx.set_session_info(front_id=1, session_id=12345)
        assert ctx.can_cancel_by_ref()

    def test_order_context_to_dict(self) -> None:
        """Test conversion to dictionary."""
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        ctx.set_order_ref("REF001")
        ctx.set_order_sys_id("SYS001")

        d = ctx.to_dict()
        assert d["symbol"] == "IF2401"
        assert d["direction"] == "BUY"
        assert d["offset"] == "OPEN"
        assert d["qty"] == 10
        assert d["price"] == 4000.0
        assert d["order_ref"] == "REF001"
        assert d["order_sys_id"] == "SYS001"


class TestOrderContextRegistry:
    """Tests for OrderContextRegistry.

    V2 Scenario: EXEC.ID.MAPPING
    """

    def test_registry_register_and_get(self) -> None:
        """Test registering and getting context."""
        registry = OrderContextRegistry()
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )

        registry.register(ctx)
        assert len(registry) == 1

        retrieved = registry.get_by_local_id(ctx.local_id)
        assert retrieved is not None
        assert retrieved.symbol == "IF2401"

    def test_registry_update_order_ref_mapping(self) -> None:
        """Test EXEC.ID.MAPPING: order_ref bidirectional mapping."""
        registry = OrderContextRegistry()
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        registry.register(ctx)

        # Update order_ref
        assert registry.update_order_ref(ctx.local_id, "REF001")

        # Can retrieve by order_ref
        retrieved = registry.get_by_order_ref("REF001")
        assert retrieved is not None
        assert retrieved.local_id == ctx.local_id

    def test_registry_update_order_sys_id_mapping(self) -> None:
        """Test EXEC.ID.MAPPING: order_sys_id bidirectional mapping."""
        registry = OrderContextRegistry()
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        registry.register(ctx)

        # Update order_sys_id
        assert registry.update_order_sys_id(ctx.local_id, "SYS001")

        # Can retrieve by order_sys_id
        retrieved = registry.get_by_order_sys_id("SYS001")
        assert retrieved is not None
        assert retrieved.local_id == ctx.local_id

    def test_registry_update_nonexistent_fails(self) -> None:
        """Test updating non-existent context returns False."""
        registry = OrderContextRegistry()
        assert not registry.update_order_ref("nonexistent", "REF001")
        assert not registry.update_order_sys_id("nonexistent", "SYS001")

    def test_registry_get_nonexistent_returns_none(self) -> None:
        """Test getting non-existent context returns None."""
        registry = OrderContextRegistry()
        assert registry.get_by_local_id("nonexistent") is None
        assert registry.get_by_order_ref("nonexistent") is None
        assert registry.get_by_order_sys_id("nonexistent") is None

    def test_registry_remove(self) -> None:
        """Test removing context."""
        registry = OrderContextRegistry()
        ctx = OrderContext(
            symbol="IF2401",
            direction="BUY",
            offset="OPEN",
            qty=10,
            price=4000.0,
        )
        registry.register(ctx)
        registry.update_order_ref(ctx.local_id, "REF001")
        registry.update_order_sys_id(ctx.local_id, "SYS001")

        assert registry.remove(ctx.local_id)
        assert len(registry) == 0
        assert registry.get_by_local_id(ctx.local_id) is None
        assert registry.get_by_order_ref("REF001") is None
        assert registry.get_by_order_sys_id("SYS001") is None

    def test_registry_remove_nonexistent(self) -> None:
        """Test removing non-existent context returns False."""
        registry = OrderContextRegistry()
        assert not registry.remove("nonexistent")

    def test_registry_get_all(self) -> None:
        """Test getting all contexts."""
        registry = OrderContextRegistry()
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
            offset="CLOSE",
            qty=5,
            price=4100.0,
        )
        registry.register(ctx1)
        registry.register(ctx2)

        all_contexts = registry.get_all()
        assert len(all_contexts) == 2
        symbols = {c.symbol for c in all_contexts}
        assert symbols == {"IF2401", "IF2402"}
