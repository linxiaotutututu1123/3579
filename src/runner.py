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
    now_ts: float


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
    broker_factory: Callable[[AppSettings], Broker],
    strategy_factory: Callable[[AppSettings], "Strategy"],
    fetch_tick: Callable[[], LiveTickData],
    now_cb: Callable[[], float] = time.time,
    risk_cfg: RiskConfig | None = None,
    run_once: bool = False,
) -> None:
    """
    Skeleton for live runner (F21).

    Intended flow (per taskbook F21):
    1) load settings/env (including TRADE_MODE, strategy selection)
    2) build broker/executor/strategy/risk (PAPER->Noop, LIVE->Ctp via broker_factory)
    3) per tick fetch AccountSnapshot/positions/books/bars_1m via fetch_tick()
    4) call handle_risk_update(...) then handle_trading_tick(...) in order
    5) log events (stdout or artifacts/log)

    This skeleton wires dependency acquisition and guards; the main loop
    and orchestration are left for F21 implementation. handle_risk_update
    行为必须保持不变（仅在 orchestrator 内部调用）。
    """

    settings = load_settings()

    live_broker = broker_factory(settings)
    components = init_components(broker=live_broker, risk_cfg=risk_cfg)
    strategy = strategy_factory(settings)

    # TODO(F21): 主循环
    # - 09:00/on_day_start_0900
    # - handle_risk_update -> handle_trading_tick 顺序
    # - 日志落地

    if run_once:
        # 预期在 PAPER 下可执行到此处，不触发 CTP import
        _tick = fetch_tick()
        _ = (components, strategy, _tick, now_cb)
        return

    raise NotImplementedError("F21 live runner loop pending implementation.")
