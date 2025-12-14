from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import AppSettings, load_settings
from src.execution.broker import Broker
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, PositionToClose
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig

if TYPE_CHECKING:
    from src.strategy.base import Strategy
    from src.strategy.types import Bar1m


@dataclass(frozen=True)
class Components:
    settings: AppSettings
    risk: RiskManager
    flatten: FlattenExecutor


@dataclass(frozen=True)
class LiveTickData:
    snap: AccountSnapshot
    positions: Sequence[PositionToClose]
    books: Mapping[str, BookTop]
    bars_1m: Mapping[str, Sequence[Bar1m]]


def init_components(*, broker: Broker, risk_cfg: RiskConfig | None = None) -> Components:
    """
    App composition root.
    - Loads settings/env
    - Wires RiskManager + Executor
    - Returns components (no side effects like network calls)
    """
    settings = load_settings()

    cfg = risk_cfg or RiskConfig()

    # callbacks are stubs; later wire to Broker/OMS cancel/flatten
    def cancel_all() -> None:
        # placeholder: integrate with OMS later
        return

    def force_flatten_all() -> None:
        # placeholder: integrate with flatten runner later
        return

    risk = RiskManager(cfg, cancel_all_cb=cancel_all, force_flatten_all_cb=force_flatten_all)
    flatten = FlattenExecutor(broker)

    return Components(settings=settings, risk=risk, flatten=flatten)


def run_f21(
    *,
    broker: Broker | None = None,
    risk_cfg: RiskConfig | None = None,
    broker_factory: Callable[[AppSettings], Broker] | None = None,
    strategy_factory: Callable[[AppSettings], "Strategy"] | None = None,
    fetch_tick: Callable[[], LiveTickData] | None = None,
    now_cb: Callable[[], float] = time.time,
) -> None:
    """
    Skeleton for live runner (F21).

    Intended flow (per taskbook F21):
    1) load settings/env (including TRADE_MODE, strategy selection)
    2) build broker/executor/strategy/risk (PAPER->Noop, LIVE->Ctp via broker_factory)
    3) per tick fetch AccountSnapshot/positions/books/bars_1m via fetch_tick()
    4) call handle_risk_update(...) then handle_trading_tick(...) in order
    5) log events (stdout or artifacts/log)

    This skeleton only wires dependency acquisition and guards; the main loop
    and orchestration are left for F21 implementation. handle_risk_update
    behavior must remain untouched.
    """

    settings = load_settings()

    if broker is None and broker_factory is None:
        raise NotImplementedError("Provide broker or broker_factory before running F21.")
    if strategy_factory is None:
        raise NotImplementedError("Provide strategy_factory before running F21.")
    if fetch_tick is None:
        raise NotImplementedError("Provide fetch_tick (LiveTickData) before running F21.")

    live_broker = broker or broker_factory(settings)
    components = init_components(broker=live_broker, risk_cfg=risk_cfg)
    strategy = strategy_factory(settings)

    _ = (components, strategy, now_cb)
    raise NotImplementedError("F21 live runner loop pending implementation.")
