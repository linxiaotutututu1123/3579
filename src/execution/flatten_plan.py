from __future__ import annotations

from dataclasses import dataclass

from src.execution.order_types import Offset, OrderIntent, Side


@dataclass(frozen=True)
class BookTop:
    best_bid: float
    best_ask: float
    tick: float


@dataclass(frozen=True)
class PositionToClose:
    symbol: str
    net_qty: int
    # Split into today/yesterday quantities to model CloseToday priority.
    # Use absolute quantities here; sign is carried by net_qty.
    today_qty: int
    yesterday_qty: int

    def __post_init__(self) -> None:
        if self.today_qty < 0 or self.yesterday_qty < 0:
            raise ValueError("today_qty/yesterday_qty must be >= 0.")
        if abs(self.net_qty) != self.today_qty + self.yesterday_qty:
            raise ValueError("abs(net_qty) must equal today_qty + yesterday_qty.")


@dataclass(frozen=True)
class FlattenSpec:
    stage1_cross_ticks: int = 0
    stage2_requotes: int = 12
    stage2_step_ticks: int = 1
    stage3_max_cross_levels: int = 12


def _quantize(price: float, tick: float) -> float:
    steps = round(price / tick)
    return steps * tick


def _sell_price(book: BookTop, cross_ticks: int) -> float:
    # SELL: more aggressive => lower price
    return _quantize(book.best_bid - cross_ticks * book.tick, book.tick)


def _buy_price(book: BookTop, cross_ticks: int) -> float:
    # BUY: more aggressive => higher price
    return _quantize(book.best_ask + cross_ticks * book.tick, book.tick)


def build_flatten_intents(
    *,
    pos: PositionToClose,
    book: BookTop,
    spec: FlattenSpec,
) -> list[OrderIntent]:
    """
    Planning-only: build deterministic OrderIntents for flattening a position.
    - net_qty > 0 (long): SELL close
    - net_qty < 0 (short): BUY close
    LIMIT-only, CloseToday first.
    """
    if pos.net_qty == 0:
        return []

    side = Side.SELL if pos.net_qty > 0 else Side.BUY

    chunks: list[tuple[Offset, int]] = []
    if pos.today_qty > 0:
        chunks.append((Offset.CLOSETODAY, pos.today_qty))
    if pos.yesterday_qty > 0:
        chunks.append((Offset.CLOSE, pos.yesterday_qty))

    def price_for_cross(cross_ticks: int) -> float:
        if side == Side.SELL:
            return _sell_price(book, cross_ticks)
        return _buy_price(book, cross_ticks)

    intents: list[OrderIntent] = []

    # Stage1
    for offset, qty in chunks:
        intents.append(
            OrderIntent(
                symbol=pos.symbol,
                side=side,
                offset=offset,
                price=price_for_cross(spec.stage1_cross_ticks),
                qty=qty,
                reason="flatten:stage1",
            )
        )

    # Stage2
    for i in range(spec.stage2_requotes):
        cross = (i + 1) * spec.stage2_step_ticks
        for offset, qty in chunks:
            intents.append(
                OrderIntent(
                    symbol=pos.symbol,
                    side=side,
                    offset=offset,
                    price=price_for_cross(cross),
                    qty=qty,
                    reason=f"flatten:stage2:{i+1}",
                )
            )

    # Stage3
    for lvl in range(1, spec.stage3_max_cross_levels + 1):
        cross = lvl
        for offset, qty in chunks:
            intents.append(
                OrderIntent(
                    symbol=pos.symbol,
                    side=side,
                    offset=offset,
                    price=price_for_cross(cross),
                    qty=qty,
                    reason=f"flatten:stage3:{lvl}",
                )
            )

    return intents
