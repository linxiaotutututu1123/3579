from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from src.risk.events import RiskEvent, RiskEventType
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState


@dataclass(frozen=True)
class Decision:
    allow_open: bool
    reason: str = ""


CancelAllCb = Callable[[], None]
ForceFlattenAllCb = Callable[[], None]


class RiskManager:
    def __init__(
        self,
        cfg: RiskConfig,
        *,
        cancel_all_cb: CancelAllCb,
        force_flatten_all_cb: ForceFlattenAllCb,
        now_cb: Callable[[], float] = time.time,
    ) -> None:
        self.cfg = cfg
        self.state = RiskState()
        self._cancel_all = cancel_all_cb
        self._force_flatten_all = force_flatten_all_cb
        self._now = now_cb
        self._events: list[RiskEvent] = []

    def pop_events(self) -> list[RiskEvent]:
        ev, self._events = self._events, []
        return ev

    def _emit(self, type_: RiskEventType, data: dict, correlation_id: str = "") -> None:
        self._events.append(
            RiskEvent(type=type_, ts=self._now(), correlation_id=correlation_id, data=data)
        )

    def on_day_start_0900(self, snap: AccountSnapshot) -> None:
        self.state.e0 = snap.equity
        self.state.mode = RiskMode.NORMAL
        self.state.kill_switch_fired_today = False
        self.state.cooldown_end_ts = None
        self._emit(RiskEventType.BASELINE_SET, {"e0": snap.equity})

    def update(self, snap: AccountSnapshot) -> None:
        if self.state.e0 is None:
            return

        now_ts = self._now()

        # cooldown -> recovery transition happens on time
        if (
            self.state.mode == RiskMode.COOLDOWN
            and self.state.cooldown_end_ts is not None
            and now_ts >= self.state.cooldown_end_ts
        ):
            self.state.mode = RiskMode.RECOVERY
            self._emit(
                RiskEventType.ENTER_RECOVERY, {"cooldown_end_ts": self.state.cooldown_end_ts}
            )

        dd = self.state.dd(snap.equity)

        # dd breach handling
        if dd <= self.cfg.dd_limit:
            if not self.state.kill_switch_fired_today:
                self._fire_kill_switch(dd=dd, equity=snap.equity)
            elif self.state.mode == RiskMode.RECOVERY:
                self.state.mode = RiskMode.LOCKED
                self._emit(RiskEventType.LOCKED_FOR_DAY, {"dd": dd, "equity": snap.equity})

    def _fire_kill_switch(self, *, dd: float, equity: float) -> None:
        self.state.kill_switch_fired_today = True
        self.state.mode = RiskMode.COOLDOWN
        self.state.cooldown_end_ts = self._now() + self.cfg.cooldown_seconds

        self._emit(
            RiskEventType.KILL_SWITCH_FIRED,
            {"dd": dd, "equity": equity, "cooldown_end_ts": self.state.cooldown_end_ts},
        )

        self._cancel_all()
        self._force_flatten_all()

    def can_open(self, snap: AccountSnapshot) -> Decision:
        # INIT gate: until baseline(E0) is set at 09:00, forbid opening positions
        if self.state.e0 is None:
            return Decision(False, "blocked_by_init:no_baseline")

        if self.state.mode in (RiskMode.COOLDOWN, RiskMode.LOCKED):
            return Decision(False, f"blocked_by_mode:{self.state.mode.value}")

        max_margin = (
            self.cfg.max_margin_normal
            if self.state.mode == RiskMode.NORMAL
            else self.cfg.max_margin_recovery
        )
        if snap.margin_ratio > max_margin:
            return Decision(False, "blocked_by_margin_ratio")

        return Decision(True, "ok")
