from __future__ import annotations

from collections.abc import Mapping

from src.execution.order_types import Offset, OrderIntent, Side
from src.strategy.types import TargetPortfolio


def build_rebalance_intents(
    *,
    current_net_qty: Mapping[str, int],
    target: TargetPortfolio,
    mid_prices: Mapping[str, float],
) -> tuple[list[OrderIntent], list[OrderIntent]]:
    """
    Build order intents to rebalance from current to target positions.

    Handles cross-zero splits:
    - +1 -> -2: SELL CLOSE 1, then SELL OPEN 2
    - -3 -> +1: BUY CLOSE 3, then BUY OPEN 1

    Returns:
        (close_intents, open_intents)
    """
    close_intents: list[OrderIntent] = []
    open_intents: list[OrderIntent] = []

    symbols = set(target.target_net_qty.keys()) | set(current_net_qty.keys())

    for sym in symbols:
        cur = current_net_qty.get(sym, 0)
        tgt = target.target_net_qty.get(sym, 0)
        delta = tgt - cur

        if delta == 0:
            continue

        price = mid_prices.get(sym, 0.0)

        if cur > 0 and tgt < 0:
            close_intents.append(OrderIntent(
                symbol=sym,
                side=Side.SELL,
                offset=Offset.CLOSE,
                price=price,
                qty=cur,
                reason="close_long_before_short",
            ))
            open_intents.append(OrderIntent(
                symbol=sym,
                side=Side.SELL,
                offset=Offset.OPEN,
                price=price,
                qty=abs(tgt),
                reason="open_short_after_close",
            ))
        elif cur < 0 and tgt > 0:
            close_intents.append(OrderIntent(
                symbol=sym,
                side=Side.BUY,
                offset=Offset.CLOSE,
                price=price,
                qty=abs(cur),
                reason="close_short_before_long",
            ))
            open_intents.append(OrderIntent(
                symbol=sym,
                side=Side.BUY,
                offset=Offset.OPEN,
                price=price,
                qty=tgt,
                reason="open_long_after_close",
            ))
        elif cur > 0 and tgt >= 0:
            if delta > 0:
                open_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.BUY,
                    offset=Offset.OPEN,
                    price=price,
                    qty=delta,
                    reason="add_long",
                ))
            else:
                close_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.SELL,
                    offset=Offset.CLOSE,
                    price=price,
                    qty=abs(delta),
                    reason="reduce_long",
                ))
        elif cur < 0 and tgt <= 0:
            if delta < 0:
                open_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.SELL,
                    offset=Offset.OPEN,
                    price=price,
                    qty=abs(delta),
                    reason="add_short",
                ))
            else:
                close_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.BUY,
                    offset=Offset.CLOSE,
                    price=price,
                    qty=delta,
                    reason="reduce_short",
                ))
        elif cur == 0:
            if tgt > 0:
                open_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.BUY,
                    offset=Offset.OPEN,
                    price=price,
                    qty=tgt,
                    reason="open_long",
                ))
            else:
                open_intents.append(OrderIntent(
                    symbol=sym,
                    side=Side.SELL,
                    offset=Offset.OPEN,
                    price=price,
                    qty=abs(tgt),
                    reason="open_short",
                ))

    return close_intents, open_intents
