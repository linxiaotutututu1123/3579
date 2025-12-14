from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskMode(str, Enum):
    INIT = "INIT"
    NORMAL = "NORMAL"
    COOLDOWN = "COOLDOWN"
    RECOVERY = "RECOVERY"
    LOCKED = "LOCKED"


@dataclass
class RiskConfig:
    dd_limit: float = -0.03
    cooldown_seconds: int = 600
    max_margin_normal: float = 0.30
    max_margin_recovery: float = 0.10


@dataclass
class AccountSnapshot:
    equity: float
    margin_used: float

    @property
    def margin_ratio(self) -> float:
        if self.equity <= 0:
            return 1.0
        return self.margin_used / self.equity


@dataclass
class RiskState:
    e0: float | None = None
    mode: RiskMode = RiskMode.INIT
    kill_switch_fired_today: bool = False
    cooldown_end_ts: float | None = None

    # Highest-grade idempotency/anti-reentry for flatten
    flatten_in_progress: bool = False
    flatten_completed_today: bool = False

    def dd(self, equity: float) -> float:
        if self.e0 is None or self.e0 == 0:
            return 0.0
        return equity / self.e0 - 1.0
