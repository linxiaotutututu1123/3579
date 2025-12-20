"""
V2 Scenario Tests: MKT.STALE.SOFT, MKT.STALE.HARD

Phase 0 Market Layer - QuoteCache
军规级验收测试
"""

from __future__ import annotations

import pytest

from src.market.quote_cache import (
    QUOTE_HARD_STALE_MS,
    QUOTE_STALE_MS,
    BookTop,
    QuoteCache,
)


def make_book(symbol: str, ts: float, last: float = 4000.0) -> BookTop:
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


class TestMktStaleSoft:
    """V2 Scenario: MKT.STALE.SOFT - 软 stale 检测."""

    RULE_ID = "MKT.STALE.SOFT"
    COMPONENT = "QuoteCache"

    def test_not_stale_within_threshold(self) -> None:
        """阈值内不 stale."""
        cache = QuoteCache(stale_ms=QUOTE_STALE_MS)

        # Book at ts=1000000 (seconds)
        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        # Check at ts=1000002 (2s later = 2000ms < 3000ms threshold)
        is_stale = cache.is_stale("rb2501", now_ts=1000002.0)

        # Assert - Evidence
        assert is_stale is False, (
            f"[{self.RULE_ID}] Should NOT be stale at 2000ms < {QUOTE_STALE_MS}ms"
        )

    def test_stale_beyond_threshold(self) -> None:
        """超过阈值则 stale."""
        cache = QuoteCache(stale_ms=QUOTE_STALE_MS)

        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        # Check at ts=1000004 (4s later = 4000ms > 3000ms threshold)
        is_stale = cache.is_stale("rb2501", now_ts=1000004.0)

        # Assert - Evidence
        assert is_stale is True, (
            f"[{self.RULE_ID}] Should be stale at 4000ms > {QUOTE_STALE_MS}ms"
        )

    def test_stale_for_missing_symbol(self) -> None:
        """不存在的合约返回 stale."""
        cache = QuoteCache()

        is_stale = cache.is_stale("nonexistent", now_ts=1000000.0)

        # Assert - Evidence
        assert is_stale is True, (
            f"[{self.RULE_ID}] Missing symbol should be treated as stale"
        )

    def test_stale_detection_with_millisecond_timestamps(self) -> None:
        """毫秒时间戳正确检测."""
        cache = QuoteCache(stale_ms=QUOTE_STALE_MS)

        # Book at ts=1700000000000 (milliseconds)
        book = make_book("rb2501", ts=1700000000000.0)
        cache.update(book)

        # Check at 4000ms later (> 3000ms threshold)
        is_stale = cache.is_stale("rb2501", now_ts=1700000004000.0)

        # Assert - Evidence
        assert is_stale is True, (
            f"[{self.RULE_ID}] Millisecond timestamps should work correctly"
        )


class TestMktStaleHard:
    """V2 Scenario: MKT.STALE.HARD - 硬 stale 检测."""

    RULE_ID = "MKT.STALE.HARD"
    COMPONENT = "QuoteCache"

    def test_not_hard_stale_within_threshold(self) -> None:
        """阈值内不 hard stale."""
        cache = QuoteCache(hard_stale_ms=QUOTE_HARD_STALE_MS)

        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        # Check at ts=1000008 (8s = 8000ms < 10000ms threshold)
        is_hard_stale = cache.is_hard_stale("rb2501", now_ts=1000008.0)

        # Assert - Evidence
        assert is_hard_stale is False, (
            f"[{self.RULE_ID}] Should NOT be hard stale at 8000ms < {QUOTE_HARD_STALE_MS}ms"
        )

    def test_hard_stale_beyond_threshold(self) -> None:
        """超过阈值则 hard stale，应禁止开仓."""
        cache = QuoteCache(hard_stale_ms=QUOTE_HARD_STALE_MS)

        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        # Check at ts=1000012 (12s = 12000ms > 10000ms threshold)
        is_hard_stale = cache.is_hard_stale("rb2501", now_ts=1000012.0)

        # Assert - Evidence
        assert is_hard_stale is True, (
            f"[{self.RULE_ID}] Should be hard stale at 12000ms > {QUOTE_HARD_STALE_MS}ms, "
            "should block new positions"
        )

    def test_hard_stale_for_missing_symbol(self) -> None:
        """不存在的合约返回 hard stale."""
        cache = QuoteCache()

        is_hard_stale = cache.is_hard_stale("nonexistent", now_ts=1000000.0)

        # Assert - Evidence
        assert is_hard_stale is True, (
            f"[{self.RULE_ID}] Missing symbol should be treated as hard stale"
        )

    def test_soft_stale_before_hard_stale(self) -> None:
        """软 stale 先于硬 stale."""
        cache = QuoteCache(stale_ms=QUOTE_STALE_MS, hard_stale_ms=QUOTE_HARD_STALE_MS)

        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        # At 5s: soft stale (>3s) but not hard stale (<10s)
        now_ts = 1000005.0
        is_soft = cache.is_stale("rb2501", now_ts)
        is_hard = cache.is_hard_stale("rb2501", now_ts)

        # Assert - Evidence
        assert is_soft is True, f"[{self.RULE_ID}] Should be soft stale at 5000ms"
        assert is_hard is False, f"[{self.RULE_ID}] Should NOT be hard stale at 5000ms"

    def test_get_stale_age_ms(self) -> None:
        """获取过期时长."""
        cache = QuoteCache()

        book = make_book("rb2501", ts=1000000.0)
        cache.update(book)

        age_ms = cache.get_stale_age_ms("rb2501", now_ts=1000005.0)

        # Assert - Evidence
        assert age_ms == 5000.0, f"[{self.RULE_ID}] Stale age should be 5000ms"

    def test_get_hard_stale_symbols(self) -> None:
        """获取所有 hard stale 的合约."""
        cache = QuoteCache(hard_stale_ms=QUOTE_HARD_STALE_MS)

        cache.update(make_book("rb2501", ts=1000000.0))
        cache.update(make_book("rb2505", ts=1000008.0))  # Fresher
        cache.update(make_book("hc2501", ts=1000000.0))

        # At 1000012: rb2501 and hc2501 are hard stale (12s), rb2505 not (4s)
        hard_stale = cache.get_hard_stale_symbols(now_ts=1000012.0)

        # Assert - Evidence
        assert set(hard_stale) == {"rb2501", "hc2501"}, (
            f"[{self.RULE_ID}] Should identify all hard stale symbols"
        )
