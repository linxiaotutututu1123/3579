from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json(obj: Any) -> str:
    """JSON serialize with deterministic key ordering.

    Uses allow_nan=False to reject NaN/Inf values, ensuring valid JSON output.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def stable_hash(obj: Any) -> str:
    """SHA256 hash of stable JSON representation."""
    return hashlib.sha256(stable_json(obj).encode("utf-8")).hexdigest()
