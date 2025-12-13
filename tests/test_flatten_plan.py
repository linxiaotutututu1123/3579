from __future__ import annotations

from src.execution.flatten_plan import BookTop, FlattenPolicy, plan_force_flatten
from src.execution.order_types import Offset, Side


def test_force_flatten_long_prefers_close_today_then_close() -> None:
    policy = FlattenPolicy(tick_size=1.0, stage2_requotes=2, max_cross_levels=3)
    intents = plan_force_flatten(
        symbol="AO",
        book=BookTop(best_bid=100.0, best_ask=101.0),
        net_pos=10,
        close_today_qty=4,
        policy=policy,
    )

    # total price points = 1 + stage2(2) + stage3(3) = 6
    assert len(intents) == 6 * 2  # (CLOSETODAY intents) + (CLOSE intents)

    first = intents[0]
    assert first.side == Side.SELL
    assert first.offset == Offset.CLOSETODAY
    assert first.qty == 4
    assert first.price == 100.0

    # last of closetoday block should still be CLOSETODAY
    assert intents[5].offset == Offset.CLOSETODAY
    # first of close block
    assert intents[6].offset == Offset.CLOSE
    assert intents[6].qty == 6


def test_force_flatten_short_uses_best_ask_and_steps_up() -> None:
    policy = FlattenPolicy(tick_size=0.5, stage2_requotes=1, max_cross_levels=2)
    intents = plan_force_flatten(
        symbol="SA",
        book=BookTop(best_bid=200.0, best_ask=200.5),
        net_pos=-3,
        close_today_qty=3,
        policy=policy,
    )

    assert len(intents) == (1 + 1 + 2) * 1  # only CLOSETODAY, no remaining CLOSE
    assert all(i.side == Side.BUY for i in intents)
    assert all(i.offset == Offset.CLOSETODAY for i in intents)

    prices = [i.price for i in intents]
    assert prices == [200.5, 201.0, 201.5, 202.0]


def test_close_today_qty_cannot_exceed_position() -> None:
    import pytest

    policy = FlattenPolicy()
    with pytest.raises(ValueError):
        plan_force_flatten(
            symbol="LC",
            book=BookTop(best_bid=10.0, best_ask=11.0),
            net_pos=2,
            close_today_qty=3,
            policy=policy,
        )
