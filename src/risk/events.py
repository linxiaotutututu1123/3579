from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskEventType(str, Enum):
    BASELINE_SET = "BASELINE_SET"
    KILL_SWITCH_FIRED = "KILL_SWITCH_FIRED"
    ENTER_RECOVERY = "ENTER_RECOVERY"
    LOCKED_FOR_DAY = "LOCKED_FOR_DAY"
    AUDIT_SNAPSHOT = "AUDIT_SNAPSHOT"


@dataclass(frozen=True)
class RiskEvent:
    type: RiskEventType
    ts: float
    correlation_id: str
    data: dict[str, Any]
