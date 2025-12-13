from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskMode(str, Enum):
    NORMAL = "NORMAL"
    COOLDOWN = "COOLDOWN"
    RECOVERY = "RECOVERY"
    LOCKED = "LOCKED"


@dataclass(frozen=True)
class RiskConfig:
    dd_limit: float = -0.03
    cooldown_seconds: int = 90 * 60
    recovery_risk_multiplier: float = 0.30
    max_margin_normal: float = 0.70
    max_margin_recovery: float = 0.40


@dataclass(frozen=True)
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
    mode: RiskMode = RiskMode.NORMAL
    kill_switch_fired_today: bool = False
    e0: float | None = None
    cooldown_end_ts: float | None = None

    def dd(self, equity_now: float) -> float:
        if self.e0 is None or self.e0 == 0:
            return 0.0
        return (equity_now - self.e0) / self.e0
