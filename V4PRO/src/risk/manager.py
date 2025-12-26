from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from src.risk.events import RiskEvent, RiskEventType
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState


@dataclass(frozen=True)
class Decision:
    allow_open: bool
    reason: str = ""


CancelAllCb = Callable[[], None]
ForceFlattenAllCb = Callable[[], None]


class NowCb(Protocol):
    def __call__(self) -> float: ...


class RiskManager:
    def __init__(
        self,
        cfg: RiskConfig,
        *,
        cancel_all_cb: CancelAllCb,
        force_flatten_all_cb: ForceFlattenAllCb,
        now_cb: NowCb = time.time,
    ) -> None:
        self.cfg = cfg
        self.state = RiskState()
        self._cancel_all = cancel_all_cb
        self._force_flatten_all = force_flatten_all_cb
        self._now = now_cb
        self._events: list[RiskEvent] = []

    def pop_events(self) -> list[RiskEvent]:
        ev = self._events[:]
        self._events.clear()
        return ev

    def emit(
        self,
        *,
        event_type: RiskEventType,
        correlation_id: str,
        data: dict[str, Any],
    ) -> None:
        self._events.append(
            RiskEvent(
                type=event_type,
                ts=self._now(),
                correlation_id=correlation_id,
                data=data,
            )
        )

    def on_day_start_0900(self, snap: AccountSnapshot, *, correlation_id: str) -> None:
        self.state.e0 = snap.equity
        self.state.mode = RiskMode.NORMAL
        self.state.kill_switch_fired_today = False
        self.state.cooldown_end_ts = None

        # reset highest-grade idempotency flags for the new day
        self.state.flatten_in_progress = False
        self.state.flatten_completed_today = False

        self._events.append(
            RiskEvent(
                type=RiskEventType.BASELINE_SET,
                ts=self._now(),
                correlation_id=correlation_id,
                data={"e0": snap.equity},
            )
        )

    def update(self, snap: AccountSnapshot, *, correlation_id: str) -> None:
        if self.state.e0 is None:
            return

        now_ts = self._now()

        if self.state.mode == RiskMode.COOLDOWN:
            if (
                self.state.cooldown_end_ts is not None
                and now_ts >= self.state.cooldown_end_ts
            ):
                self.state.mode = RiskMode.RECOVERY
                self._events.append(
                    RiskEvent(
                        type=RiskEventType.ENTER_RECOVERY,
                        ts=now_ts,
                        correlation_id=correlation_id,
                        data={"cooldown_end_ts": self.state.cooldown_end_ts},
                    )
                )
            return

        dd = self.state.dd(snap.equity)

        if dd <= self.cfg.dd_limit:
            if not self.state.kill_switch_fired_today:
                self._fire_kill_switch(correlation_id=correlation_id)
            else:
                self.state.mode = RiskMode.LOCKED
                self._events.append(
                    RiskEvent(
                        type=RiskEventType.LOCKED_FOR_DAY,
                        ts=now_ts,
                        correlation_id=correlation_id,
                        data={"dd": dd},
                    )
                )

    def _fire_kill_switch(self, *, correlation_id: str) -> None:
        now_ts = self._now()
        self.state.kill_switch_fired_today = True
        self.state.mode = RiskMode.COOLDOWN
        self.state.cooldown_end_ts = now_ts + self.cfg.cooldown_seconds

        self._cancel_all()
        self._force_flatten_all()

        self._events.append(
            RiskEvent(
                type=RiskEventType.KILL_SWITCH_FIRED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={"cooldown_end_ts": self.state.cooldown_end_ts},
            )
        )

    # ---------- Highest-grade flatten idempotency ----------
    def try_start_flatten(self, *, correlation_id: str) -> bool:
        """
        Returns True exactly once per day (first successful start).
        Subsequent attempts are skipped (either in-progress or already completed today).
        """
        now_ts = self._now()

        if self.state.flatten_in_progress:
            self._events.append(
                RiskEvent(
                    type=RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS,
                    ts=now_ts,
                    correlation_id=correlation_id,
                    data={},
                )
            )
            return False

        if self.state.flatten_completed_today:
            # Reuse the same event type to keep it minimal; data indicates why.
            self._events.append(
                RiskEvent(
                    type=RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS,
                    ts=now_ts,
                    correlation_id=correlation_id,
                    data={"reason": "already_completed_today"},
                )
            )
            return False

        self.state.flatten_in_progress = True
        self._events.append(
            RiskEvent(
                type=RiskEventType.FLATTEN_STARTED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={},
            )
        )
        return True

    def mark_flatten_done(self, *, correlation_id: str) -> None:
        now_ts = self._now()
        self.state.flatten_in_progress = False
        self.state.flatten_completed_today = True
        self._events.append(
            RiskEvent(
                type=RiskEventType.FLATTEN_COMPLETED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={},
            )
        )

    def can_open(self, snap: AccountSnapshot) -> Decision:
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
