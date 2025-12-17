"""
V2 Scenario Tests: MKT.STALE.SOFT, MKT.STALE.HARD

Phase 0 Market Layer - QuoteCache
军规级验收测试
"""

from __future__ import annotations

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


class TestBookTopProperties:
    """BookTop 属性测试 - 100% 覆盖率补充."""

    def test_mid_with_valid_bid_ask(self) -> None:
        """有效买卖价时计算中间价."""
        book = make_book("rb2501", ts=1000000.0, last=4000.0)
        # bid=3999, ask=4001
        assert book.mid == 4000.0, "Mid should be (bid+ask)/2"

    def test_mid_with_zero_bid(self) -> None:
        """买价为0时返回最新价."""
        book = BookTop(
            symbol="rb2501",
            bid=0.0,
            ask=4001.0,
            bid_vol=0,
            ask_vol=100,
            last=4000.0,
            volume=10000,
            open_interest=50000,
            ts=1000000.0,
        )
        assert book.mid == 4000.0, "Mid should be last when bid=0"

    def test_mid_with_zero_ask(self) -> None:
        """卖价为0时返回最新价."""
        book = BookTop(
            symbol="rb2501",
            bid=3999.0,
            ask=0.0,
            bid_vol=100,
            ask_vol=0,
            last=4000.0,
            volume=10000,
            open_interest=50000,
            ts=1000000.0,
        )
        assert book.mid == 4000.0, "Mid should be last when ask=0"

    def test_spread_with_valid_bid_ask(self) -> None:
        """有效买卖价时计算价差."""
        book = make_book("rb2501", ts=1000000.0, last=4000.0)
        # bid=3999, ask=4001
        assert book.spread == 2.0, "Spread should be ask-bid"

    def test_spread_with_zero_bid(self) -> None:
        """买价为0时价差为0."""
        book = BookTop(
            symbol="rb2501",
            bid=0.0,
            ask=4001.0,
            bid_vol=0,
            ask_vol=100,
            last=4000.0,
            volume=10000,
            open_interest=50000,
            ts=1000000.0,
        )
        assert book.spread == 0.0, "Spread should be 0 when bid=0"

    def test_spread_with_zero_ask(self) -> None:
        """卖价为0时价差为0."""
        book = BookTop(
            symbol="rb2501",
            bid=3999.0,
            ask=0.0,
            bid_vol=100,
            ask_vol=0,
            last=4000.0,
            volume=10000,
            open_interest=50000,
            ts=1000000.0,
        )
        assert book.spread == 0.0, "Spread should be 0 when ask=0"

    def test_spread_bps_with_valid_mid(self) -> None:
        """有效中间价时计算基点价差."""
        book = make_book("rb2501", ts=1000000.0, last=4000.0)
        # mid=4000, spread=2, bps = 2/4000*10000 = 5
        assert book.spread_bps == 5.0, "Spread bps should be spread/mid*10000"

    def test_spread_bps_with_zero_mid(self) -> None:
        """中间价为0时基点价差为0."""
        book = BookTop(
            symbol="rb2501",
            bid=0.0,
            ask=0.0,
            bid_vol=0,
            ask_vol=0,
            last=0.0,
            volume=0,
            open_interest=0,
            ts=1000000.0,
        )
        assert book.spread_bps == 0.0, "Spread bps should be 0 when mid=0"


class TestQuoteCacheExtended:
    """QuoteCache 扩展测试 - 100% 覆盖率补充."""

    def test_get_returns_none_for_missing(self) -> None:
        """不存在的合约返回 None."""
        cache = QuoteCache()
        assert cache.get("nonexistent") is None

    def test_get_stale_age_for_missing_returns_inf(self) -> None:
        """不存在的合约过期时长为 inf."""
        cache = QuoteCache()
        age = cache.get_stale_age_ms("nonexistent", now_ts=1000000.0)
        assert age == float("inf"), "Missing symbol should have inf stale age"

    def test_get_stale_age_with_millisecond_timestamps(self) -> None:
        """毫秒时间戳计算过期时长."""
        cache = QuoteCache()
        book = make_book("rb2501", ts=1700000000000.0)
        cache.update(book)

        age = cache.get_stale_age_ms("rb2501", now_ts=1700000005000.0)
        assert age == 5000.0, "Should return age in milliseconds"

    def test_all_symbols(self) -> None:
        """获取所有缓存的合约代码."""
        cache = QuoteCache()
        cache.update(make_book("rb2501", ts=1000000.0))
        cache.update(make_book("hc2501", ts=1000000.0))

        symbols = cache.all_symbols()
        assert set(symbols) == {"rb2501", "hc2501"}

    def test_get_stale_symbols(self) -> None:
        """获取所有 stale 的合约代码."""
        cache = QuoteCache(stale_ms=QUOTE_STALE_MS)
        cache.update(make_book("rb2501", ts=1000000.0))
        cache.update(make_book("hc2501", ts=1000005.0))  # Fresher

        # At 1000006: rb2501 is stale (6s>3s), hc2501 not (1s<3s)
        stale = cache.get_stale_symbols(now_ts=1000006.0)
        assert stale == ["rb2501"], "Should identify stale symbols"

    def test_clear(self) -> None:
        """清空缓存."""
        cache = QuoteCache()
        cache.update(make_book("rb2501", ts=1000000.0))
        cache.clear()

        assert len(cache) == 0
        assert cache.get("rb2501") is None

    def test_len(self) -> None:
        """返回缓存数量."""
        cache = QuoteCache()
        assert len(cache) == 0

        cache.update(make_book("rb2501", ts=1000000.0))
        assert len(cache) == 1

        cache.update(make_book("hc2501", ts=1000000.0))
        assert len(cache) == 2
