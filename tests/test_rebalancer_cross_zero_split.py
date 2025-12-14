from __future__ import annotations

from src.execution.order_types import Offset, Side
from src.portfolio.rebalancer import build_rebalance_intents
from src.strategy.types import TargetPortfolio


def test_cross_zero_long_to_short() -> None:
    """Test +1 -> -2: should SELL CLOSE 1, then SELL OPEN 2."""
    target = TargetPortfolio(
        target_net_qty={"AO": -2},
        model_version="test",
        features_hash="abc",
    )

    intents = build_rebalance_intents(
        current_net_qty={"AO": 1},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(intents) == 2
    assert intents[0].symbol == "AO"
    assert intents[0].side == Side.SELL
    assert intents[0].offset == Offset.CLOSE
    assert intents[0].qty == 1

    assert intents[1].symbol == "AO"
    assert intents[1].side == Side.SELL
    assert intents[1].offset == Offset.OPEN
    assert intents[1].qty == 2


def test_cross_zero_short_to_long() -> None:
    """Test -3 -> +1: should BUY CLOSE 3, then BUY OPEN 1."""
    target = TargetPortfolio(
        target_net_qty={"AO": 1},
        model_version="test",
        features_hash="abc",
    )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty={"AO": -3},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(close_intents) == 1
    assert close_intents[0].symbol == "AO"
    assert close_intents[0].side == Side.BUY
    assert close_intents[0].offset == Offset.CLOSE
    assert close_intents[0].qty == 3

    assert len(open_intents) == 1
    assert open_intents[0].symbol == "AO"
    assert open_intents[0].side == Side.BUY
    assert open_intents[0].offset == Offset.OPEN
    assert open_intents[0].qty == 1


def test_same_direction_add_long() -> None:
    """Test +1 -> +3: should BUY OPEN 2."""
    target = TargetPortfolio(
        target_net_qty={"AO": 3},
        model_version="test",
        features_hash="abc",
    )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty={"AO": 1},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(close_intents) == 0
    assert len(open_intents) == 1
    assert open_intents[0].side == Side.BUY
    assert open_intents[0].offset == Offset.OPEN
    assert open_intents[0].qty == 2


def test_same_direction_reduce_long() -> None:
    """Test +3 -> +1: should SELL CLOSE 2."""
    target = TargetPortfolio(
        target_net_qty={"AO": 1},
        model_version="test",
        features_hash="abc",
    )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty={"AO": 3},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(close_intents) == 1
    assert close_intents[0].side == Side.SELL
    assert close_intents[0].offset == Offset.CLOSE
    assert close_intents[0].qty == 2
    assert len(open_intents) == 0


def test_open_from_flat() -> None:
    """Test 0 -> +2: should BUY OPEN 2."""
    target = TargetPortfolio(
        target_net_qty={"AO": 2},
        model_version="test",
        features_hash="abc",
    )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty={"AO": 0},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(close_intents) == 0
    assert len(open_intents) == 1
    assert open_intents[0].side == Side.BUY
    assert open_intents[0].offset == Offset.OPEN
    assert open_intents[0].qty == 2


def test_no_change() -> None:
    """Test +1 -> +1: no orders."""
    target = TargetPortfolio(
        target_net_qty={"AO": 1},
        model_version="test",
        features_hash="abc",
    )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty={"AO": 1},
        target=target,
        mid_prices={"AO": 100.0},
    )

    assert len(close_intents) == 0
    assert len(open_intents) == 0
