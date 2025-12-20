from __future__ import annotations

from src.execution.order_types import Offset


def test_offset_open_exists() -> None:
    """Verify Offset.OPEN is defined."""
    assert hasattr(Offset, "OPEN")
    assert Offset.OPEN.value == "OPEN"


def test_offset_enum_members() -> None:
    """Verify all expected Offset members exist."""
    assert Offset.OPEN == "OPEN"
    assert Offset.CLOSE == "CLOSE"
    assert Offset.CLOSETODAY == "CLOSETODAY"
