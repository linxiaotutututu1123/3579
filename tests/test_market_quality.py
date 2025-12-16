"""
V2 Scenario Tests: MKT.QUALITY.OUTLIER, MKT.QUALITY.GAP, MKT.QUALITY.DISORDER

Phase 0 Market Layer - QualityChecker
军规级验收测试
"""

from __future__ import annotations

import pytest

from src.market.instrument_cache import InstrumentInfo
from src.market.quality import QualityChecker, QualityEvent, QualityIssue
from src.market.quote_cache import BookTop


def make_book(
    symbol: str,
    ts: float,
    last: float = 4000.0,
) -> BookTop:
    """创建测试用盘口数据."""
    return BookTop(
        symbol=symbol,
        bid=last - 1,
        ask=last + 1,
        bid_vol=100,
        ask_vol=100,
        last=last,
        volume=10000,
        open_interest=50000,
        ts=ts,
    )


def make_instrument(symbol: str, tick_size: float = 1.0) -> InstrumentInfo:
    """创建测试用合约信息."""
    return InstrumentInfo(
        symbol=symbol,
        product=symbol[:2],
        exchange="SHFE",
        expire_date="20251215",
        tick_size=tick_size,
        multiplier=10,
        max_order_volume=500,
        position_limit=3000,
    )


class TestMktQualityOutlier:
    """V2 Scenario: MKT.QUALITY.OUTLIER - 异常值检测."""

    RULE_ID = "MKT.QUALITY.OUTLIER"
    COMPONENT = "QualityChecker"

    def test_no_outlier_within_threshold(self) -> None:
        """阈值内的价格变动不算异常."""
        checker = QualityChecker(outlier_ticks_threshold=50)
        checker.register_instrument(make_instrument("rb2501", tick_size=1.0))

        # First tick
        checker.check(make_book("rb2501", ts=1000000.0, last=4000.0))

        # Second tick: 30 ticks change (< 50 threshold)
        events = checker.check(make_book("rb2501", ts=1000001.0, last=4030.0))

        # Assert - Evidence
        outlier_events = [e for e in events if e.issue == QualityIssue.OUTLIER]
        assert len(outlier_events) == 0, (
            f"[{self.RULE_ID}] 30 ticks change should NOT trigger outlier"
        )

    def test_outlier_beyond_threshold(self) -> None:
        """超过阈值的价格变动标记为异常."""
        checker = QualityChecker(outlier_ticks_threshold=50)
        checker.register_instrument(make_instrument("rb2501", tick_size=1.0))

        # First tick
        checker.check(make_book("rb2501", ts=1000000.0, last=4000.0))

        # Second tick: 60 ticks change (> 50 threshold)
        events = checker.check(make_book("rb2501", ts=1000001.0, last=4060.0))

        # Assert - Evidence
        outlier_events = [e for e in events if e.issue == QualityIssue.OUTLIER]
        assert len(outlier_events) == 1, f"[{self.RULE_ID}] 60 ticks change should trigger outlier"
        assert outlier_events[0].symbol == "rb2501"
        assert outlier_events[0].details["ticks_change"] == 60.0

    def test_outlier_negative_jump(self) -> None:
        """负向价格跳变也检测."""
        checker = QualityChecker(outlier_ticks_threshold=50)
        checker.register_instrument(make_instrument("rb2501", tick_size=1.0))

        checker.check(make_book("rb2501", ts=1000000.0, last=4000.0))
        events = checker.check(make_book("rb2501", ts=1000001.0, last=3940.0))

        # Assert - Evidence
        outlier_events = [e for e in events if e.issue == QualityIssue.OUTLIER]
        assert len(outlier_events) == 1, (
            f"[{self.RULE_ID}] Negative 60 ticks should trigger outlier"
        )

    def test_outlier_callback_invoked(self) -> None:
        """异常检测触发回调."""
        received_events: list[QualityEvent] = []

        def on_event(event: QualityEvent) -> None:
            received_events.append(event)

        checker = QualityChecker(outlier_ticks_threshold=50, on_quality_event=on_event)
        checker.register_instrument(make_instrument("rb2501", tick_size=1.0))

        checker.check(make_book("rb2501", ts=1000000.0, last=4000.0))
        checker.check(make_book("rb2501", ts=1000001.0, last=4060.0))

        # Assert - Evidence
        assert len(received_events) == 1, f"[{self.RULE_ID}] Callback should be invoked for outlier"
        assert received_events[0].issue == QualityIssue.OUTLIER


class TestMktQualityGap:
    """V2 Scenario: MKT.QUALITY.GAP - 行情间隙检测."""

    RULE_ID = "MKT.QUALITY.GAP"
    COMPONENT = "QualityChecker"

    def test_no_gap_within_threshold(self) -> None:
        """阈值内的时间间隙不报告."""
        checker = QualityChecker(gap_threshold_ms=5000.0)

        # First tick
        checker.check(make_book("rb2501", ts=1000000.0))

        # Second tick: 3000ms later (< 5000ms threshold)
        events = checker.check(make_book("rb2501", ts=1000003.0))

        # Assert - Evidence
        gap_events = [e for e in events if e.issue == QualityIssue.GAP]
        assert len(gap_events) == 0, f"[{self.RULE_ID}] 3000ms gap should NOT trigger"

    def test_gap_beyond_threshold(self) -> None:
        """超过阈值的时间间隙标记为 gap."""
        checker = QualityChecker(gap_threshold_ms=5000.0)

        checker.check(make_book("rb2501", ts=1000000.0))
        events = checker.check(make_book("rb2501", ts=1000008.0))  # 8000ms gap

        # Assert - Evidence
        gap_events = [e for e in events if e.issue == QualityIssue.GAP]
        assert len(gap_events) == 1, f"[{self.RULE_ID}] 8000ms gap should trigger"
        assert gap_events[0].details["gap_ms"] == 8000.0

    def test_gap_with_millisecond_timestamps(self) -> None:
        """毫秒时间戳正确检测间隙."""
        checker = QualityChecker(gap_threshold_ms=5000.0)

        checker.check(make_book("rb2501", ts=1700000000000.0))
        events = checker.check(make_book("rb2501", ts=1700000008000.0))

        # Assert - Evidence
        gap_events = [e for e in events if e.issue == QualityIssue.GAP]
        assert len(gap_events) == 1, (
            f"[{self.RULE_ID}] Millisecond timestamp gap detection should work"
        )


class TestMktQualityDisorder:
    """V2 Scenario: MKT.QUALITY.DISORDER - 时间乱序检测."""

    RULE_ID = "MKT.QUALITY.DISORDER"
    COMPONENT = "QualityChecker"

    def test_disorder_detected_and_dropped(self) -> None:
        """时间倒退被检测并丢弃."""
        checker = QualityChecker()

        # First tick at ts=1000010
        checker.check(make_book("rb2501", ts=1000010.0, last=4000.0))

        # Second tick at ts=1000005 (time went backwards!)
        events = checker.check(make_book("rb2501", ts=1000005.0, last=4010.0))

        # Assert - Evidence
        disorder_events = [e for e in events if e.issue == QualityIssue.DISORDER]
        assert len(disorder_events) == 1, (
            f"[{self.RULE_ID}] Backwards timestamp should trigger disorder"
        )
        assert "dropped" in disorder_events[0].details["message"].lower()

    def test_disorder_does_not_update_cache(self) -> None:
        """乱序数据不更新缓存."""
        checker = QualityChecker()

        # First tick
        checker.check(make_book("rb2501", ts=1000010.0, last=4000.0))

        # Disordered tick (should be dropped)
        checker.check(make_book("rb2501", ts=1000005.0, last=9999.0))

        # Next normal tick should compare against ts=1000010, not ts=1000005
        events = checker.check(make_book("rb2501", ts=1000015.0, last=4010.0))

        # Assert - Evidence
        # Should not have gap event (5s from 1000010), not from disordered 1000005
        gap_events = [e for e in events if e.issue == QualityIssue.GAP]
        assert len(gap_events) == 0, f"[{self.RULE_ID}] Disordered tick should not update cache"

    def test_equal_timestamp_not_disorder(self) -> None:
        """相同时间戳不算乱序."""
        checker = QualityChecker()

        checker.check(make_book("rb2501", ts=1000010.0, last=4000.0))
        events = checker.check(make_book("rb2501", ts=1000010.0, last=4001.0))

        # Assert - Evidence
        disorder_events = [e for e in events if e.issue == QualityIssue.DISORDER]
        assert len(disorder_events) == 0, (
            f"[{self.RULE_ID}] Equal timestamp should NOT trigger disorder"
        )


class TestQualityCheckerMultipleIssues:
    """多种质量问题组合测试."""

    def test_outlier_and_gap_same_tick(self) -> None:
        """同一tick可能同时有outlier和gap."""
        checker = QualityChecker(outlier_ticks_threshold=50, gap_threshold_ms=5000.0)
        checker.register_instrument(make_instrument("rb2501", tick_size=1.0))

        checker.check(make_book("rb2501", ts=1000000.0, last=4000.0))

        # 8s later with 60 tick price jump
        events = checker.check(make_book("rb2501", ts=1000008.0, last=4060.0))

        # Assert
        issues = {e.issue for e in events}
        assert QualityIssue.OUTLIER in issues
        assert QualityIssue.GAP in issues

    def test_clear_resets_state(self) -> None:
        """clear 重置状态."""
        checker = QualityChecker()

        checker.check(make_book("rb2501", ts=1000000.0))
        checker.clear("rb2501")

        # After clear, first tick should not compare with previous
        events = checker.check(make_book("rb2501", ts=1000100.0))

        assert len(events) == 0, "After clear, no previous state to compare"
