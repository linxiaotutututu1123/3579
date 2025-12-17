"""Tests for CTP mapping module (F18).

Covers:
- Side → CTP Direction mapping
- Offset → CTP OffsetFlag mapping
- Reverse mappings
- Unknown value raises CtpMappingError
"""

from __future__ import annotations

import pytest

from src.brokers.ctp.mapping import (
    CTP_DIRECTION_BUY,
    CTP_DIRECTION_SELL,
    CTP_OFFSET_CLOSE,
    CTP_OFFSET_CLOSETODAY,
    CTP_OFFSET_OPEN,
    CtpMappingError,
    ctp_direction_to_side,
    ctp_offset_flag_to_offset,
    offset_to_ctp_offset_flag,
    side_to_ctp_direction,
)
from src.execution.order_types import Offset, Side


class TestSideToCTPDirection:
    """Tests for side_to_ctp_direction."""

    def test_buy_maps_to_0(self) -> None:
        """Side.BUY maps to CTP Direction '0'."""
        assert side_to_ctp_direction(Side.BUY) == "0"
        assert side_to_ctp_direction(Side.BUY) == CTP_DIRECTION_BUY

    def test_sell_maps_to_1(self) -> None:
        """Side.SELL maps to CTP Direction '1'."""
        assert side_to_ctp_direction(Side.SELL) == "1"
        assert side_to_ctp_direction(Side.SELL) == CTP_DIRECTION_SELL

    def test_unknown_side_raises(self) -> None:
        """Unknown Side value raises CtpMappingError."""
        # Create a mock "unknown" side by passing invalid input
        # Since Side is an enum, we test the error path by checking the function
        # rejects non-enum values when type checking is bypassed
        with pytest.raises(CtpMappingError) as exc_info:
            side_to_ctp_direction("INVALID")  # type: ignore[arg-type]
        assert "Unknown Side value" in str(exc_info.value)


class TestOffsetToCTPOffsetFlag:
    """Tests for offset_to_ctp_offset_flag."""

    def test_open_maps_to_0(self) -> None:
        """Offset.OPEN maps to CTP OffsetFlag '0'."""
        assert offset_to_ctp_offset_flag(Offset.OPEN) == "0"
        assert offset_to_ctp_offset_flag(Offset.OPEN) == CTP_OFFSET_OPEN

    def test_close_maps_to_1(self) -> None:
        """Offset.CLOSE maps to CTP OffsetFlag '1'."""
        assert offset_to_ctp_offset_flag(Offset.CLOSE) == "1"
        assert offset_to_ctp_offset_flag(Offset.CLOSE) == CTP_OFFSET_CLOSE

    def test_closetoday_maps_to_3(self) -> None:
        """Offset.CLOSETODAY maps to CTP OffsetFlag '3'."""
        assert offset_to_ctp_offset_flag(Offset.CLOSETODAY) == "3"
        assert offset_to_ctp_offset_flag(Offset.CLOSETODAY) == CTP_OFFSET_CLOSETODAY

    def test_unknown_offset_raises(self) -> None:
        """Unknown Offset value raises CtpMappingError."""
        with pytest.raises(CtpMappingError) as exc_info:
            offset_to_ctp_offset_flag("INVALID")  # type: ignore[arg-type]
        assert "Unknown Offset value" in str(exc_info.value)


class TestCTPDirectionToSide:
    """Tests for ctp_direction_to_side (reverse mapping)."""

    def test_0_maps_to_buy(self) -> None:
        """CTP Direction '0' maps to Side.BUY."""
        assert ctp_direction_to_side("0") == Side.BUY

    def test_1_maps_to_sell(self) -> None:
        """CTP Direction '1' maps to Side.SELL."""
        assert ctp_direction_to_side("1") == Side.SELL

    def test_unknown_direction_raises(self) -> None:
        """Unknown CTP Direction raises CtpMappingError."""
        with pytest.raises(CtpMappingError) as exc_info:
            ctp_direction_to_side("9")
        assert "Unknown CTP Direction value" in str(exc_info.value)

    def test_empty_string_raises(self) -> None:
        """Empty string raises CtpMappingError."""
        with pytest.raises(CtpMappingError):
            ctp_direction_to_side("")


class TestCTPOffsetFlagToOffset:
    """Tests for ctp_offset_flag_to_offset (reverse mapping)."""

    def test_0_maps_to_open(self) -> None:
        """CTP OffsetFlag '0' maps to Offset.OPEN."""
        assert ctp_offset_flag_to_offset("0") == Offset.OPEN

    def test_1_maps_to_close(self) -> None:
        """CTP OffsetFlag '1' maps to Offset.CLOSE."""
        assert ctp_offset_flag_to_offset("1") == Offset.CLOSE

    def test_3_maps_to_closetoday(self) -> None:
        """CTP OffsetFlag '3' maps to Offset.CLOSETODAY."""
        assert ctp_offset_flag_to_offset("3") == Offset.CLOSETODAY

    def test_unknown_offset_flag_raises(self) -> None:
        """Unknown CTP OffsetFlag raises CtpMappingError."""
        with pytest.raises(CtpMappingError) as exc_info:
            ctp_offset_flag_to_offset("9")
        assert "Unknown CTP OffsetFlag value" in str(exc_info.value)

    def test_2_is_not_valid(self) -> None:
        """CTP OffsetFlag '2' (CloseYesterday) is not mapped and raises."""
        # Note: '2' is CloseYesterday in CTP, but we don't support it
        with pytest.raises(CtpMappingError):
            ctp_offset_flag_to_offset("2")


class TestRoundTrip:
    """Tests for round-trip consistency."""

    def test_side_round_trip(self) -> None:
        """Side -> CTP -> Side round trip is consistent."""
        for side in Side:
            ctp_dir = side_to_ctp_direction(side)
            back = ctp_direction_to_side(ctp_dir)
            assert back == side

    def test_offset_round_trip(self) -> None:
        """Offset -> CTP -> Offset round trip is consistent."""
        for offset in Offset:
            ctp_flag = offset_to_ctp_offset_flag(offset)
            back = ctp_offset_flag_to_offset(ctp_flag)
            assert back == offset
