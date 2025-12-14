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

    FLATTEN_STARTED = "FLATTEN_STARTED"
    FLATTEN_SKIPPED_ALREADY_IN_PROGRESS = "FLATTEN_SKIPPED_ALREADY_IN_PROGRESS"
    FLATTEN_COMPLETED = "FLATTEN_COMPLETED"

    # HG-5
    FLATTEN_ABORTED_TOO_MANY_REJECTIONS = "FLATTEN_ABORTED_TOO_MANY_REJECTIONS"
    DATA_QUALITY_MISSING_BOOK = "DATA_QUALITY_MISSING_BOOK"


@dataclass(frozen=True)
class RiskEvent:
    type: RiskEventType
    ts: float
    correlation_id: str
    data: dict[str, Any]
