from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.execution.events import ExecutionEvent
from src.execution.flatten_executor import FlattenExecutor
from src.portfolio.constraints import clamp_target
from src.portfolio.rebalancer import build_rebalance_intents
from src.risk.events import RiskEvent
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot
from src.strategy.base import Strategy
from src.strategy.types import Bar1m, MarketState, TargetPortfolio
from src.trading.controls import TradeControls, TradeMode
from src.trading.events import TradingEvent, TradingEventType
from src.trading.serial_exec import execute_close_then_open


Event = RiskEvent | ExecutionEvent | TradingEvent


@dataclass(frozen=True)
class TradingTickResult:
    correlation_id: str
    events: list[Event]
    target_portfolio: TargetPortfolio | None
    clamped_portfolio: TargetPortfolio | None


def handle_trading_tick(
    *,
    strategy: Strategy,
    risk: RiskManager,
    executor: FlattenExecutor,
    controls: TradeControls,
    snap: AccountSnapshot,
    prices: Mapping[str, float],
    bars_1m: Mapping[str, Sequence[Bar1m]],
    current_net_qty: Mapping[str, int],
    correlation_id: str | None = None,
    now_cb: Callable[[], float] = time.time,
) -> TradingTickResult:
    """
    Main entry point for trading tick processing (Mode 2).

    Steps:
    1. Update risk manager
    2. Generate strategy signal
    3. Clamp target portfolio
    4. Build rebalance intents
    5. Execute (LIVE) or skip (PAPER)
    """
    cid = correlation_id or uuid.uuid4().hex
    events: list[Event] = []

    risk.update(snap, correlation_id=cid)
    risk_events = risk.pop_events()
    events.extend(risk_events)

    market_state = MarketState(
        prices=prices,
        equity=snap.equity,
        bars_1m=bars_1m,
    )
    target = strategy.on_tick(market_state)

    def _sorted_qty(qty_map: Mapping[str, int]) -> dict[str, int]:
        return {sym: qty_map[sym] for sym in sorted(qty_map)}

    events.append(
        TradingEvent(
            type=TradingEventType.SIGNAL_GENERATED,
            ts=now_cb(),
            correlation_id=cid,
            data={"model_version": target.model_version, "features_hash": target.features_hash},
        )
    )

    events.append(
        TradingEvent(
            type=TradingEventType.TARGET_PORTFOLIO_SET,
            ts=now_cb(),
            correlation_id=cid,
            data={"target_net_qty": _sorted_qty(target.target_net_qty)},
        )
    )

    clamped, audit = clamp_target(
        risk=risk,
        snap=snap,
        current_net_qty=current_net_qty,
        target=target,
    )

    if clamped.target_net_qty != target.target_net_qty or audit:
        events.append(
            TradingEvent(
                type=TradingEventType.TARGET_PORTFOLIO_CLAMPED,
                ts=now_cb(),
                correlation_id=cid,
                data={"clamped_net_qty": _sorted_qty(clamped.target_net_qty), "audit": audit},
            )
        )

    close_intents, open_intents = build_rebalance_intents(
        current_net_qty=current_net_qty,
        target=clamped,
        mid_prices=prices,
    )

    all_intents = list(close_intents) + list(open_intents)
    if all_intents:
        intent_data: list[dict[str, Any]] = [
            {
                "symbol": i.symbol,
                "side": i.side.value,
                "offset": i.offset.value,
                "price": i.price,
                "qty": i.qty,
                "reason": i.reason,
            }
            for i in all_intents
        ]
        events.append(
            TradingEvent(
                type=TradingEventType.ORDERS_INTENDED,
                ts=now_cb(),
                correlation_id=cid,
                data={"intents": intent_data},
            )
        )

    if controls.mode == TradeMode.PAPER:
        return TradingTickResult(
            correlation_id=cid,
            events=events,
            target_portfolio=target,
            clamped_portfolio=clamped,
        )

    if all_intents:
        events.append(
            TradingEvent(
                type=TradingEventType.ORDERS_SENT,
                ts=now_cb(),
                correlation_id=cid,
                data={"close_count": len(close_intents), "open_count": len(open_intents)},
            )
        )

        trading_events, exec_events = execute_close_then_open(
            executor=executor,
            close_intents=close_intents,
            open_intents=open_intents,
            correlation_id=cid,
            now_cb=now_cb,
        )
        events.extend(trading_events)
        events.extend(exec_events)

    return TradingTickResult(
        correlation_id=cid,
        events=events,
        target_portfolio=target,
        clamped_portfolio=clamped,
    )
