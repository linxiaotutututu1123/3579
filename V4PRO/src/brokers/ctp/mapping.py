"""CTP Direction/OffsetFlag mapping.

This module provides explicit mapping between internal order types
(Side, Offset) and CTP protocol constants (Direction, OffsetFlag).

All mappings are hardcoded for clarity and auditability.
Unknown values will raise ValueError to prevent silent failures.
"""

from __future__ import annotations

from src.execution.order_types import Offset, Side


class CtpMappingError(ValueError):
    """Raised when mapping fails due to unknown input value."""


# CTP Direction constants (from CTP API)
# '0' = Buy, '1' = Sell
CTP_DIRECTION_BUY: str = "0"
CTP_DIRECTION_SELL: str = "1"

# CTP OffsetFlag constants (from CTP API)
# '0' = Open, '1' = Close, '3' = CloseToday
CTP_OFFSET_OPEN: str = "0"
CTP_OFFSET_CLOSE: str = "1"
CTP_OFFSET_CLOSETODAY: str = "3"


def side_to_ctp_direction(side: Side) -> str:
    """
    Map internal Side enum to CTP Direction char.

    Args:
        side: Internal Side enum (BUY or SELL)

    Returns:
        CTP Direction char ('0' for buy, '1' for sell)

    Raises:
        CtpMappingError: If side is not a recognized Side enum value
    """
    if side == Side.BUY:
        return CTP_DIRECTION_BUY
    if side == Side.SELL:
        return CTP_DIRECTION_SELL
    raise CtpMappingError(f"Unknown Side value: {side!r}")


def offset_to_ctp_offset_flag(offset: Offset) -> str:
    """
    Map internal Offset enum to CTP OffsetFlag char.

    Args:
        offset: Internal Offset enum (OPEN, CLOSE, CLOSETODAY)

    Returns:
        CTP OffsetFlag char ('0' for open, '1' for close, '3' for closetoday)

    Raises:
        CtpMappingError: If offset is not a recognized Offset enum value
    """
    if offset == Offset.OPEN:
        return CTP_OFFSET_OPEN
    if offset == Offset.CLOSE:
        return CTP_OFFSET_CLOSE
    if offset == Offset.CLOSETODAY:
        return CTP_OFFSET_CLOSETODAY
    raise CtpMappingError(f"Unknown Offset value: {offset!r}")


def ctp_direction_to_side(direction: str) -> Side:
    """
    Map CTP Direction char back to internal Side enum.

    Args:
        direction: CTP Direction char ('0' or '1')

    Returns:
        Internal Side enum

    Raises:
        CtpMappingError: If direction is not a recognized CTP value
    """
    if direction == CTP_DIRECTION_BUY:
        return Side.BUY
    if direction == CTP_DIRECTION_SELL:
        return Side.SELL
    raise CtpMappingError(f"Unknown CTP Direction value: {direction!r}")


def ctp_offset_flag_to_offset(offset_flag: str) -> Offset:
    """
    Map CTP OffsetFlag char back to internal Offset enum.

    Args:
        offset_flag: CTP OffsetFlag char ('0', '1', or '3')

    Returns:
        Internal Offset enum

    Raises:
        CtpMappingError: If offset_flag is not a recognized CTP value
    """
    if offset_flag == CTP_OFFSET_OPEN:
        return Offset.OPEN
    if offset_flag == CTP_OFFSET_CLOSE:
        return Offset.CLOSE
    if offset_flag == CTP_OFFSET_CLOSETODAY:
        return Offset.CLOSETODAY
    raise CtpMappingError(f"Unknown CTP OffsetFlag value: {offset_flag!r}")
