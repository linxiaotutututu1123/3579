"""
V2 Scenario Tests: MKT.CONTINUITY.BARS

Phase 0 Market Layer - BarBuilder
军规级验收测试
"""

from __future__ import annotations

from typing import Any

from src.market.bar_builder import Bar, BarBuilder
from src.market.quote_cache import BookTop


def make_book(
    symbol: str,
    ts: float,
    last: float = 4000.0,
    volume: int = 10000,
    open_interest: int = 50000,
) -> BookTop:
    """创建测试用盘口数据."""
    return BookTop(
        symbol=symbol,
        bid=last - 1,
        ask=last + 1,
        bid_vol=100,
        ask_vol=100,
        last=last,
        volume=volume,
        open_interest=open_interest,
        ts=ts,
    )


class TestMktContinuityBars:
    """V2 Scenario: MKT.CONTINUITY.BARS - 连续主力 bars 聚合."""

    RULE_ID = "MKT.CONTINUITY.BARS"
    COMPONENT = "BarBuilder"

    def test_aggregate_ticks_to_bar(self) -> None:
        """从 tick 聚合成 bar."""
        completed_bars: list[Bar] = []

        def on_bar_complete(bar: Bar) -> None:
            completed_bars.append(bar)

        builder = BarBuilder(bar_interval_s=60, on_bar_complete=on_bar_complete)
        # Use ts=60 as clean minute boundary (60 // 60 * 60 = 60)
        builder.update_dominant("rb", "rb2501", ts=60.0)

        # Send ticks within same minute [60, 120)
        builder.on_tick("rb", make_book("rb2501", ts=60.0, last=4000.0, volume=100))
        builder.on_tick("rb", make_book("rb2501", ts=70.0, last=4010.0, volume=200))
        builder.on_tick("rb", make_book("rb2501", ts=90.0, last=3990.0, volume=300))
        builder.on_tick("rb", make_book("rb2501", ts=110.0, last=4005.0, volume=400))

        # Send tick in next minute [120, 180) to complete previous bar
        builder.on_tick("rb", make_book("rb2501", ts=120.0, last=4020.0, volume=500))

        # Assert - Evidence
        assert len(completed_bars) == 1, f"[{self.RULE_ID}] Should have 1 completed bar"
        bar = completed_bars[0]
        assert bar.symbol == "rb", f"[{self.RULE_ID}] Bar symbol should be product code"
        assert bar.open == 4000.0, f"[{self.RULE_ID}] Open should be first tick price"
        assert bar.high == 4010.0, f"[{self.RULE_ID}] High should be max price"
        assert bar.low == 3990.0, f"[{self.RULE_ID}] Low should be min price"
        assert bar.close == 4005.0, f"[{self.RULE_ID}] Close should be last tick price"

    def test_only_dominant_ticks_aggregated(self) -> None:
        """只聚合主力合约的 tick."""
        builder = BarBuilder(bar_interval_s=60)
        builder.update_dominant("rb", "rb2501", ts=1700000000.0)

        # Dominant tick
        builder.on_tick("rb", make_book("rb2501", ts=1700000000.0, last=4000.0))

        # Non-dominant tick (should be ignored)
        result2 = builder.on_tick("rb", make_book("rb2505", ts=1700000010.0, last=3900.0))

        # Assert - Evidence
        assert result2 is None, f"[{self.RULE_ID}] Non-dominant tick should return None"

        # Verify bar state only has dominant tick
        bars = builder.get_bars("rb")
        # No completed bars yet, check internal state via next tick
        builder.on_tick("rb", make_book("rb2501", ts=1700000060.0, last=4010.0))
        bars = builder.get_bars("rb")
        assert len(bars) == 1
        assert bars[0].low == 4000.0, f"[{self.RULE_ID}] Non-dominant tick should not affect bar"

    def test_roll_event_triggers_audit(self) -> None:
        """主力切换触发审计事件."""
        roll_events: list[dict[str, Any]] = []

        def on_roll(product: str, old_symbol: str, new_symbol: str, ts: float) -> None:
            roll_events.append(
                {
                    "product": product,
                    "old_symbol": old_symbol,
                    "new_symbol": new_symbol,
                    "ts": ts,
                }
            )

        builder = BarBuilder(bar_interval_s=60, on_roll_event=on_roll)

        # Initial dominant
        builder.update_dominant("rb", "rb2501", ts=1700000000.0)

        # Roll to new dominant
        builder.update_dominant("rb", "rb2505", ts=1700000100.0)

        # Assert - Evidence
        assert len(roll_events) == 1, f"[{self.RULE_ID}] Should trigger roll event"
        event = roll_events[0]
        assert event["product"] == "rb"
        assert event["old_symbol"] == "rb2501"
        assert event["new_symbol"] == "rb2505"
        assert event["ts"] == 1700000100.0

    def test_roll_forces_bar_completion(self) -> None:
        """主力切换强制完成当前 bar."""
        completed_bars: list[Bar] = []

        def on_bar_complete(bar: Bar) -> None:
            completed_bars.append(bar)

        builder = BarBuilder(bar_interval_s=60, on_bar_complete=on_bar_complete)
        builder.update_dominant("rb", "rb2501", ts=1700000000.0)

        # Build partial bar
        builder.on_tick("rb", make_book("rb2501", ts=1700000000.0, last=4000.0))
        builder.on_tick("rb", make_book("rb2501", ts=1700000030.0, last=4010.0))

        # Roll before bar would naturally complete
        builder.update_dominant("rb", "rb2505", ts=1700000040.0)

        # Assert - Evidence
        assert len(completed_bars) == 1, f"[{self.RULE_ID}] Roll should force bar completion"
        assert completed_bars[0].ts_end == 1700000040.0, (
            f"[{self.RULE_ID}] Forced bar should end at roll time"
        )

    def test_bar_interval_boundary(self) -> None:
        """Bar 边界正确对齐."""
        builder = BarBuilder(bar_interval_s=60)
        builder.update_dominant("rb", "rb2501", ts=1700000000.0)

        # Tick at 1700000045 -> bar should be [1700000000, 1700000060)
        builder.on_tick("rb", make_book("rb2501", ts=1700000045.0, last=4000.0))

        # Force completion by next minute tick
        builder.on_tick("rb", make_book("rb2501", ts=1700000060.0, last=4010.0))

        bars = builder.get_bars("rb")
        assert len(bars) == 1
        assert bars[0].ts_start == 1700000000.0, (
            f"[{self.RULE_ID}] Bar start should align to interval boundary"
        )
        assert bars[0].ts_end == 1700000060.0, (
            f"[{self.RULE_ID}] Bar end should be start + interval"
        )

    def test_get_bars_returns_time_ordered(self) -> None:
        """获取的 bars 按时间正序."""
        completed_bars: list[Bar] = []

        def on_bar_complete(bar: Bar) -> None:
            completed_bars.append(bar)

        builder = BarBuilder(bar_interval_s=60, on_bar_complete=on_bar_complete)
        builder.update_dominant("rb", "rb2501", ts=1700000000.0)

        # Create 3 bars
        for i in range(4):
            ts = 1700000000.0 + i * 60
            builder.on_tick("rb", make_book("rb2501", ts=ts, last=4000.0 + i))

        bars = builder.get_bars("rb")
        assert len(bars) == 3

        # Assert - Evidence
        for i in range(len(bars) - 1):
            assert bars[i].ts_start < bars[i + 1].ts_start, (
                f"[{self.RULE_ID}] Bars should be in time order"
            )
