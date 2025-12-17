"""
Tests for PairExecutor and LegManager.

V3PRO+ Platform - Phase 2
V2 Scenarios:
- PAIR.EXECUTOR.ATOMIC
- PAIR.ROLLBACK.ON_LEG_FAIL
- PAIR.AUTOHEDGE.DELTA_NEUTRAL
- PAIR.IMBALANCE.DETECT
- PAIR.BREAKER.STOP_Z
"""

from src.execution.pair.leg_manager import (
    Leg,
    LegManager,
    LegStatus,
)
from src.execution.pair.pair_executor import (
    BreakerConfig,
    PairExecutor,
    PairOrder,
    PairResult,
    PairStatus,
)


class TestLeg:
    """Tests for Leg dataclass."""

    def test_leg_creation(self) -> None:
        """Test Leg creation."""
        leg = Leg(
            leg_id="leg1",
            pair_id="pair1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
        )

        assert leg.leg_id == "leg1"
        assert leg.symbol == "IF2401"
        assert leg.direction == "BUY"
        assert leg.target_qty == 10
        assert leg.filled_qty == 0
        assert leg.status == LegStatus.PENDING

    def test_leg_fill_ratio(self) -> None:
        """Test fill ratio calculation."""
        leg = Leg(
            leg_id="leg1",
            pair_id="pair1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
            filled_qty=5,
        )

        assert leg.fill_ratio() == 0.5

    def test_leg_update_fill(self) -> None:
        """Test updating fill."""
        leg = Leg(
            leg_id="leg1",
            pair_id="pair1",
            symbol="IF2401",
            direction="BUY",
            target_qty=10,
        )

        leg.update_fill(qty=5, price=4000.0)
        assert leg.filled_qty == 5
        assert leg.avg_price == 4000.0
        assert leg.status == LegStatus.PARTIAL

        leg.update_fill(qty=5, price=4100.0)
        assert leg.filled_qty == 10
        assert leg.avg_price == 4050.0  # (5*4000 + 5*4100) / 10
        assert leg.status == LegStatus.FILLED


class TestLegManager:
    """Tests for LegManager."""

    def test_create_pair(self) -> None:
        """Test creating pair legs."""
        mgr = LegManager()

        near_leg, far_leg = mgr.create_pair(
            pair_id="pair1",
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
        )

        assert near_leg.symbol == "IF2401"
        assert near_leg.direction == "BUY"
        assert far_leg.symbol == "IF2402"
        assert far_leg.direction == "SELL"
        assert len(mgr) == 1

    def test_get_pair_legs(self) -> None:
        """Test getting pair legs."""
        mgr = LegManager()
        mgr.create_pair("pair1", "IF2401", "IF2402", "BUY", "SELL", 10)

        near, far = mgr.get_pair_legs("pair1")
        assert near is not None
        assert far is not None
        assert near.symbol == "IF2401"
        assert far.symbol == "IF2402"

    def test_update_leg(self) -> None:
        """Test updating leg fill."""
        mgr = LegManager()
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 10
        )

        assert mgr.update_leg(near_leg.leg_id, qty=5, price=4000.0)
        updated = mgr.get_leg(near_leg.leg_id)
        assert updated.filled_qty == 5


class TestLegManagerImbalance:
    """Tests for PAIR.IMBALANCE.DETECT scenario."""

    def test_check_imbalance_balanced(self) -> None:
        """Test imbalance detection when balanced."""
        mgr = LegManager(imbalance_threshold=10)
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 20
        )

        # Both legs filled equally
        mgr.update_leg(near_leg.leg_id, qty=10, price=4000.0)
        mgr.update_leg(far_leg.leg_id, qty=10, price=4100.0)

        info = mgr.check_imbalance("pair1")
        assert info is not None
        assert info.imbalance_qty == 0
        assert not info.is_imbalanced

    def test_check_imbalance_detected(self) -> None:
        """Test imbalance detection when imbalanced."""
        mgr = LegManager(imbalance_threshold=5)
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 20
        )

        # Near leg filled more
        mgr.update_leg(near_leg.leg_id, qty=15, price=4000.0)
        mgr.update_leg(far_leg.leg_id, qty=5, price=4100.0)

        info = mgr.check_imbalance("pair1")
        assert info is not None
        assert info.imbalance_qty == 10  # 15 - 5
        assert info.is_imbalanced


class TestLegManagerAutoHedge:
    """Tests for PAIR.AUTOHEDGE.DELTA_NEUTRAL scenario."""

    def test_get_hedge_order_no_imbalance(self) -> None:
        """Test no hedge order when balanced."""
        mgr = LegManager(imbalance_threshold=10)
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 20
        )

        mgr.update_leg(near_leg.leg_id, qty=10, price=4000.0)
        mgr.update_leg(far_leg.leg_id, qty=10, price=4100.0)

        hedge = mgr.get_hedge_order("pair1")
        assert hedge is None

    def test_get_hedge_order_near_leg_ahead(self) -> None:
        """Test hedge order when near leg is ahead."""
        mgr = LegManager(imbalance_threshold=5)
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 20
        )

        # Near leg filled more
        mgr.update_leg(near_leg.leg_id, qty=15, price=4000.0)
        mgr.update_leg(far_leg.leg_id, qty=5, price=4100.0)

        hedge = mgr.get_hedge_order("pair1")
        assert hedge is not None
        assert hedge["symbol"] == "IF2402"  # Hedge far leg
        assert hedge["direction"] == "SELL"
        assert hedge["qty"] == 10  # Imbalance amount

    def test_get_hedge_order_far_leg_ahead(self) -> None:
        """Test hedge order when far leg is ahead."""
        mgr = LegManager(imbalance_threshold=5)
        near_leg, far_leg = mgr.create_pair(
            "pair1", "IF2401", "IF2402", "BUY", "SELL", 20
        )

        # Far leg filled more
        mgr.update_leg(near_leg.leg_id, qty=5, price=4000.0)
        mgr.update_leg(far_leg.leg_id, qty=15, price=4100.0)

        hedge = mgr.get_hedge_order("pair1")
        assert hedge is not None
        assert hedge["symbol"] == "IF2401"  # Hedge near leg
        assert hedge["direction"] == "BUY"
        assert hedge["qty"] == 10


class TestPairOrder:
    """Tests for PairOrder dataclass."""

    def test_pair_order_spread(self) -> None:
        """Test spread calculation."""
        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
            near_price=4100.0,
            far_price=4000.0,
        )

        assert order.spread() == 100.0


class TestPairExecutor:
    """Tests for PairExecutor.

    V2 Scenario: PAIR.EXECUTOR.ATOMIC
    """

    def test_execute_pair(self) -> None:
        """Test executing pair trade."""
        executor = PairExecutor()

        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
            near_price=4100.0,
            far_price=4000.0,
        )

        pair_id = executor.execute(order)

        assert pair_id is not None
        result = executor.get_result(pair_id)
        assert result is not None
        assert result.status == PairStatus.EXECUTING

    def test_on_leg_fill(self) -> None:
        """Test processing leg fill."""
        executor = PairExecutor()

        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
            near_price=4100.0,
            far_price=4000.0,
        )

        pair_id = executor.execute(order)
        near_leg, far_leg = executor.leg_manager.get_pair_legs(pair_id)

        # Fill both legs
        executor.on_leg_fill(pair_id, near_leg.leg_id, qty=10, price=4100.0)
        executor.on_leg_fill(pair_id, far_leg.leg_id, qty=10, price=4000.0)

        result = executor.get_result(pair_id)
        assert result.status == PairStatus.COMPLETED
        assert result.near_filled == 10
        assert result.far_filled == 10
        assert result.realized_spread == 100.0


class TestPairExecutorRollback:
    """Tests for PAIR.ROLLBACK.ON_LEG_FAIL scenario."""

    def test_on_leg_fail_triggers_rollback(self) -> None:
        """Test leg failure triggers rollback."""
        rollback_called = []

        def on_rollback(pair_id: str, reason: str) -> None:
            rollback_called.append((pair_id, reason))

        executor = PairExecutor(on_rollback=on_rollback)

        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
        )

        pair_id = executor.execute(order)
        near_leg, far_leg = executor.leg_manager.get_pair_legs(pair_id)

        # Near leg fills, far leg fails
        executor.on_leg_fill(pair_id, near_leg.leg_id, qty=10, price=4100.0)
        executor.on_leg_fail(pair_id, far_leg.leg_id, "Rejected by exchange")

        result = executor.get_result(pair_id)
        assert result.status == PairStatus.ROLLED_BACK
        assert len(rollback_called) == 1

    def test_both_legs_fail_no_rollback(self) -> None:
        """Test both legs fail without rollback."""
        executor = PairExecutor()

        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
        )

        pair_id = executor.execute(order)
        near_leg, far_leg = executor.leg_manager.get_pair_legs(pair_id)

        # Both legs fail without fills
        executor.on_leg_fail(pair_id, near_leg.leg_id, "Rejected")
        executor.on_leg_fail(pair_id, far_leg.leg_id, "Rejected")

        result = executor.get_result(pair_id)
        assert result.status == PairStatus.FAILED


class TestPairExecutorBreaker:
    """Tests for PAIR.BREAKER.STOP_Z scenario."""

    def test_breaker_triggers(self) -> None:
        """Test Z-score breaker triggers."""
        config = BreakerConfig(
            max_z_score=2.0,
            lookback_periods=5,
            enabled=True,
        )
        executor = PairExecutor(breaker_config=config)

        # Build spread history
        executor._spread_history = [100.0, 102.0, 101.0, 99.0, 100.0]

        # Execute with extreme spread
        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
            near_price=4200.0,
            far_price=4000.0,  # Spread = 200, way outside normal
        )

        pair_id = executor.execute(order)
        result = executor.get_result(pair_id)
        assert result.status == PairStatus.BREAKER_STOPPED

    def test_breaker_disabled(self) -> None:
        """Test breaker can be disabled."""
        config = BreakerConfig(enabled=False)
        executor = PairExecutor(breaker_config=config)

        # Build spread history
        executor._spread_history = [100.0] * 20

        # Execute with extreme spread - should still work
        order = PairOrder(
            near_symbol="IF2401",
            far_symbol="IF2402",
            near_direction="BUY",
            far_direction="SELL",
            qty=10,
            near_price=4500.0,
            far_price=4000.0,  # Extreme spread
        )

        pair_id = executor.execute(order)
        result = executor.get_result(pair_id)
        assert result.status == PairStatus.EXECUTING  # Not stopped


class TestPairExecutorOperations:
    """Tests for PairExecutor operations."""

    def test_get_active_pairs(self) -> None:
        """Test getting active pairs."""
        executor = PairExecutor()

        order1 = PairOrder("IF2401", "IF2402", "BUY", "SELL", 10)
        order2 = PairOrder("IF2403", "IF2404", "BUY", "SELL", 5)

        pair_id1 = executor.execute(order1)
        pair_id2 = executor.execute(order2)

        active = executor.get_active_pairs()
        assert len(active) == 2
        assert pair_id1 in active
        assert pair_id2 in active

    def test_check_imbalances(self) -> None:
        """Test checking all imbalances."""
        executor = PairExecutor()
        executor._leg_manager._imbalance_threshold = 5

        order = PairOrder("IF2401", "IF2402", "BUY", "SELL", 20)
        pair_id = executor.execute(order)

        near_leg, far_leg = executor.leg_manager.get_pair_legs(pair_id)
        executor.on_leg_fill(pair_id, near_leg.leg_id, qty=15, price=4100.0)
        executor.on_leg_fill(pair_id, far_leg.leg_id, qty=5, price=4000.0)

        imbalanced = executor.check_imbalances()
        assert pair_id in imbalanced


class TestPairResult:
    """Tests for PairResult."""

    def test_pair_result_success(self) -> None:
        """Test successful pair result."""
        result = PairResult(
            pair_id="pair1",
            status=PairStatus.COMPLETED,
            near_filled=10,
            far_filled=10,
            realized_spread=100.0,
        )

        assert result.is_success()
        assert result.is_complete()

    def test_pair_result_failed(self) -> None:
        """Test failed pair result."""
        result = PairResult(
            pair_id="pair1",
            status=PairStatus.FAILED,
            error="Both legs rejected",
        )

        assert not result.is_success()
        assert result.is_complete()

    def test_pair_result_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = PairResult(
            pair_id="pair1",
            status=PairStatus.COMPLETED,
            near_filled=10,
            far_filled=10,
        )

        d = result.to_dict()
        assert d["pair_id"] == "pair1"
        assert d["status"] == "COMPLETED"
        assert d["near_filled"] == 10
