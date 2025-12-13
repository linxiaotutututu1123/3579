from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import LiteralString, Protocol, TypeAlias

from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState


@dataclass(frozen=True)
class Decision:
    allow_open: bool
    reason: str = ""


CancelAllCb: TypeAlias = Callable[[], None]
ForceFlattenAllCb: TypeAlias = Callable[[], None]


class NowCb(Protocol):
    def __call__(self) -> float: ...


class RiskManager:
    cfg: RiskConfig
    state: RiskState

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
        self._cancel_all: CancelAllCb = cancel_all_cb
        self._force_flatten_all: ForceFlattenAllCb = force_flatten_all_cb
        self._now: NowCb = now_cb

    def on_day_start_0900(self, snap: AccountSnapshot) -> None:
        self.state.e0 = snap.equity
        self.state.mode = RiskMode.NORMAL
        self.state.kill_switch_fired_today = False
        self.state.cooldown_end_ts = None

    def update(self, snap: AccountSnapshot) -> None:
        if self.state.e0 is None:
            return

        now_ts: float = self._now()

        # 冷却期：只负责到点切换 RECOVERY，不做 dd 触发/锁仓判定
        if self.state.mode == RiskMode.COOLDOWN:
            if self.state.cooldown_end_ts is not None and now_ts >= self.state.cooldown_end_ts:
                self.state.mode = RiskMode.RECOVERY
            return

        dd: float = self.state.dd(equity_now=snap.equity)

        if dd <= self.cfg.dd_limit:
            if not self.state.kill_switch_fired_today:
                self._fire_kill_switch()
            else:
                self.state.mode = RiskMode.LOCKED

    def _fire_kill_switch(self) -> None:
        self.state.kill_switch_fired_today = True
        self.state.mode = RiskMode.COOLDOWN
        self.state.cooldown_end_ts = self._now() + self.cfg.cooldown_seconds
        self._cancel_all()
        self._force_flatten_all()

    def can_open(self, snap: AccountSnapshot) -> Decision:
        if self.state.mode in (RiskMode.COOLDOWN, RiskMode.LOCKED):
            reason: LiteralString = f"blocked_by_mode:{self.state.mode.value}"
            return Decision(allow_open=False, reason=reason)

        max_margin = (
            self.cfg.max_margin_normal
            if self.state.mode == RiskMode.NORMAL
            else self.cfg.max_margin_recovery
        )
        if snap.margin_ratio > max_margin:
            return Decision(allow_open=False, reason="blocked_by_margin_ratio")

        return Decision(allow_open=True, reason="ok")
