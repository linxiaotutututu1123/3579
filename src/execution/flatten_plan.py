from __future__ import annotations

from dataclasses import dataclass

from src.execution.order_types import Offset, OrderIntent, Side


@dataclass(frozen=True)
class FlattenPolicy:
    """
    Implements SPEC_RISK force-flatten *planning*.
    Execution (placing/canceling orders) will come later.

    Stages:
    - Stage1: hold near best for t1 seconds (here we only emit the initial quote)
    - Stage2: dt requotes, each step moves 1 tick further through the book
    - Stage3: more aggressive crossing, bounded by max_cross_levels
    """

    t1_seconds: int = 5
    stage2_dt_seconds: int = 2
    stage2_requotes: int = 12
    tick_size: float = 1.0
    max_cross_levels: int = 12


@dataclass(frozen=True)
class BookTop:
    best_bid: float
    best_ask: float


def _clamp_qty(qty: int) -> int:
    if qty < 0:
        raise ValueError("qty must be >= 0")
    return qty


def plan_force_flatten(
    *,
    symbol: str,
    book: BookTop,
    net_pos: int,
    close_today_qty: int,
    policy: FlattenPolicy,
) -> list[OrderIntent]:
    """
    Returns a list of OrderIntent to try sequentially.
    - net_pos > 0: long -> need SELL to flatten
    - net_pos < 0: short -> need BUY to flatten
    - close_today_qty: quantity eligible for CLOSETODAY (<= abs(net_pos))
    """
    _clamp_qty(abs(net_pos))
    close_today_qty = _clamp_qty(close_today_qty)

    abs_pos = abs(net_pos)
    if abs_pos == 0:
        return []

    if close_today_qty > abs_pos:
        raise ValueError("close_today_qty cannot exceed abs(net_pos)")

    side = Side.SELL if net_pos > 0 else Side.BUY

    # price ladder: stage1 (1 quote) + stage2 (n quotes) + stage3 (up to max cross levels)
    # For SELL: start at best_bid then step down (worse price) by tick to get filled.
    # For BUY : start at best_ask then step up  (worse price) by tick to get filled.
    start = book.best_bid if side == Side.SELL else book.best_ask
    step = -policy.tick_size if side == Side.SELL else policy.tick_size

    prices: list[float] = []
    prices.append(start)  # stage1 quote
    for i in range(1, policy.stage2_requotes + 1):
        prices.append(start + step * i)  # stage2 requotes
    for i in range(
        policy.stage2_requotes + 1, policy.stage2_requotes + policy.max_cross_levels + 1
    ):
        prices.append(start + step * i)  # stage3 bounded

    intents: list[OrderIntent] = []
    remaining = abs_pos

    def emit(offset: Offset, qty: int, reason: str) -> None:
        if qty <= 0:
            return
        for p in prices:
            intents.append(
                OrderIntent(
                    symbol=symbol,
                    side=side,
                    offset=offset,
                    price=p,
                    qty=qty,
                    reason=reason,
                )
            )

    # Prefer CLOSETODAY first (SPEC) then fallback CLOSE for remaining
    ct = min(close_today_qty, remaining)
    emit(Offset.CLOSETODAY, ct, "force_flatten:prefer_closetoday")
    remaining -= ct
    emit(Offset.CLOSE, remaining, "force_flatten:fallback_close")

    return intents
