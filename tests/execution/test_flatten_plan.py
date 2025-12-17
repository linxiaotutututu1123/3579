from __future__ import annotations

from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose, build_flatten_intents
from src.execution.order_types import Offset, Side


def test_flatten_plan_long_close_today_first_and_limit_only() -> None:
    pos = PositionToClose(symbol="AO", net_qty=5, today_qty=2, yesterday_qty=3)
    book = BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)
    spec = FlattenSpec(stage2_requotes=2, stage3_max_cross_levels=3)

    intents = build_flatten_intents(pos=pos, book=book, spec=spec)

    # Stage1 produces 2 intents (CLOSETODAY then CLOSE)
    assert intents[0].side == Side.SELL
    assert intents[0].offset == Offset.CLOSETODAY
    assert intents[0].qty == 2
    assert intents[0].price == 100.0

    assert intents[1].offset == Offset.CLOSE
    assert intents[1].qty == 3
    assert intents[1].price == 100.0

    # total intents = (stage1 2) + (stage2 2*2) + (stage3 3*2) = 2 + 4 + 6 = 12
    assert len(intents) == 12

    # For SELL, later intents should include lower prices (more aggressive)
    prices = [i.price for i in intents]
    assert min(prices) < max(prices)


def test_flatten_plan_short_generates_buy_intents_and_more_aggressive_is_higher() -> None:
    pos = PositionToClose(symbol="SA", net_qty=-4, today_qty=1, yesterday_qty=3)
    book = BookTop(best_bid=200.0, best_ask=201.0, tick=1.0)
    spec = FlattenSpec(stage2_requotes=1, stage3_max_cross_levels=2)

    intents = build_flatten_intents(pos=pos, book=book, spec=spec)

    assert intents[0].side == Side.BUY
    assert intents[0].offset == Offset.CLOSETODAY
    assert intents[0].qty == 1
    assert intents[0].price == 201.0  # stage1 near best ask

    assert intents[1].offset == Offset.CLOSE
    assert intents[1].qty == 3
    assert intents[1].price == 201.0

    prices = [i.price for i in intents]
    # For BUY, more aggressive => higher price appears later
    assert max(prices) > min(prices)


def test_flatten_plan_zero_qty_is_empty() -> None:
    pos = PositionToClose(symbol="AO", net_qty=0, today_qty=0, yesterday_qty=0)
    book = BookTop(best_bid=100.0, best_ask=101.0, tick=1.0)
    intents = build_flatten_intents(pos=pos, book=book, spec=FlattenSpec())
    assert intents == []
