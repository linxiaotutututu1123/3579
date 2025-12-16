"""
V2 Scenario Tests: UNIV.DOMINANT.BASIC, UNIV.SUBDOMINANT.PAIRING,
                   UNIV.ROLL.COOLDOWN, UNIV.EXPIRY.GATE

Phase 0 Market Layer - UniverseSelector
军规级验收测试
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.market.instrument_cache import InstrumentCache, InstrumentInfo
from src.market.universe_selector import (
    EXPIRY_BLOCK_DAYS,
    MIN_SWITCH_EDGE,
    ROLL_COOLDOWN_S,
    UniverseSelector,
)


def make_instrument(
    symbol: str,
    product: str,
    expire_date: str = "20251215",
) -> InstrumentInfo:
    """创建测试用合约信息."""
    return InstrumentInfo(
        symbol=symbol,
        product=product,
        exchange="SHFE",
        expire_date=expire_date,
        tick_size=1.0,
        multiplier=10,
        max_order_volume=500,
        position_limit=3000,
    )


@pytest.fixture
def instrument_cache() -> InstrumentCache:
    """创建测试用合约缓存."""
    cache = InstrumentCache()
    # rb品种：2501, 2505, 2510
    cache.add(make_instrument("rb2501", "rb", "20250115"))
    cache.add(make_instrument("rb2505", "rb", "20250515"))
    cache.add(make_instrument("rb2510", "rb", "20251015"))
    # hc品种：2501, 2505
    cache.add(make_instrument("hc2501", "hc", "20250115"))
    cache.add(make_instrument("hc2505", "hc", "20250515"))
    return cache


class TestUnivDominantBasic:
    """V2 Scenario: UNIV.DOMINANT.BASIC - 主力合约选择."""

    RULE_ID = "UNIV.DOMINANT.BASIC"
    COMPONENT = "UniverseSelector"

    def test_select_dominant_by_oi_volume_score(self, instrument_cache: InstrumentCache) -> None:
        """基于OI+Volume评分选择主力."""
        selector = UniverseSelector(instrument_cache)

        # rb2505 has highest score (OI*0.6 + Vol*0.4)
        oi = {"rb2501": 1000, "rb2505": 5000, "rb2510": 2000}
        vol = {"rb2501": 500, "rb2505": 3000, "rb2510": 1000}

        # Act
        snapshot = selector.select(oi, vol, now_ts=1700000000.0)

        # Assert - Evidence
        assert snapshot.dominant_by_product["rb"] == "rb2505", (
            f"[{self.RULE_ID}] Expected rb2505 as dominant, "
            f"got {snapshot.dominant_by_product.get('rb')}"
        )

    def test_dominant_in_subscribe_set(self, instrument_cache: InstrumentCache) -> None:
        """主力合约在订阅集中."""
        selector = UniverseSelector(instrument_cache)
        oi = {"rb2501": 1000, "rb2505": 5000}
        vol = {"rb2501": 500, "rb2505": 3000}

        snapshot = selector.select(oi, vol, now_ts=1700000000.0)

        assert "rb2505" in snapshot.subscribe_set, (
            f"[{self.RULE_ID}] Dominant should be in subscribe_set"
        )


class TestUnivSubdominantPairing:
    """V2 Scenario: UNIV.SUBDOMINANT.PAIRING - 次主力合约选择."""

    RULE_ID = "UNIV.SUBDOMINANT.PAIRING"
    COMPONENT = "UniverseSelector"

    def test_subdominant_not_equal_dominant(self, instrument_cache: InstrumentCache) -> None:
        """次主力 != 主力."""
        selector = UniverseSelector(instrument_cache)
        oi = {"rb2501": 1000, "rb2505": 5000, "rb2510": 3000}
        vol = {"rb2501": 500, "rb2505": 3000, "rb2510": 2000}

        snapshot = selector.select(oi, vol, now_ts=1700000000.0)

        dominant = snapshot.dominant_by_product.get("rb")
        subdominant = snapshot.subdominant_by_product.get("rb")

        # Assert - Evidence
        assert dominant != subdominant, (
            f"[{self.RULE_ID}] Subdominant ({subdominant}) must not equal dominant ({dominant})"
        )
        assert subdominant is not None, f"[{self.RULE_ID}] Subdominant should exist"

    def test_subdominant_is_second_highest_score(self, instrument_cache: InstrumentCache) -> None:
        """次主力是评分第二高的合约."""
        selector = UniverseSelector(instrument_cache)
        # Score: rb2505=5000*0.6+3000*0.4=4200, rb2510=3000*0.6+2000*0.4=2600,
        #        rb2501=1000*0.6+500*0.4=800
        oi = {"rb2501": 1000, "rb2505": 5000, "rb2510": 3000}
        vol = {"rb2501": 500, "rb2505": 3000, "rb2510": 2000}

        snapshot = selector.select(oi, vol, now_ts=1700000000.0)

        # Assert - Evidence
        assert snapshot.subdominant_by_product["rb"] == "rb2510", (
            f"[{self.RULE_ID}] Expected rb2510 as subdominant (2nd highest score)"
        )

    def test_subdominant_in_subscribe_set(self, instrument_cache: InstrumentCache) -> None:
        """次主力合约在订阅集中."""
        selector = UniverseSelector(instrument_cache)
        oi = {"rb2501": 1000, "rb2505": 5000, "rb2510": 3000}
        vol = {"rb2501": 500, "rb2505": 3000, "rb2510": 2000}

        snapshot = selector.select(oi, vol, now_ts=1700000000.0)

        assert "rb2510" in snapshot.subscribe_set, (
            f"[{self.RULE_ID}] Subdominant should be in subscribe_set"
        )


class TestUnivRollCooldown:
    """V2 Scenario: UNIV.ROLL.COOLDOWN - 主力切换冷却期."""

    RULE_ID = "UNIV.ROLL.COOLDOWN"
    COMPONENT = "UniverseSelector"

    def test_no_switch_during_cooldown(self, instrument_cache: InstrumentCache) -> None:
        """冷却期内不切换主力."""
        selector = UniverseSelector(
            instrument_cache,
            roll_cooldown_s=ROLL_COOLDOWN_S,
            min_switch_edge=0.0,  # Disable edge threshold for this test
        )

        # Initial: rb2505 is dominant
        oi1 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 2000}
        vol1 = {"rb2501": 500, "rb2505": 3000, "rb2510": 1000}
        snapshot1 = selector.select(oi1, vol1, now_ts=1700000000.0)
        assert snapshot1.dominant_by_product["rb"] == "rb2505"

        # After 100s (< cooldown 300s): rb2510 has higher score but should NOT switch
        oi2 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 20000}  # rb2510 now highest
        vol2 = {"rb2501": 500, "rb2505": 3000, "rb2510": 15000}
        snapshot2 = selector.select(oi2, vol2, now_ts=1700000100.0)

        # Assert - Evidence
        assert snapshot2.dominant_by_product["rb"] == "rb2505", (
            f"[{self.RULE_ID}] Should NOT switch during cooldown period (100s < {ROLL_COOLDOWN_S}s)"
        )

    def test_switch_after_cooldown(self, instrument_cache: InstrumentCache) -> None:
        """冷却期后可以切换主力."""
        selector = UniverseSelector(
            instrument_cache,
            roll_cooldown_s=ROLL_COOLDOWN_S,
            min_switch_edge=0.0,
        )

        # Initial
        oi1 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 2000}
        vol1 = {"rb2501": 500, "rb2505": 3000, "rb2510": 1000}
        selector.select(oi1, vol1, now_ts=1700000000.0)

        # After 400s (> cooldown 300s): can switch
        oi2 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 20000}
        vol2 = {"rb2501": 500, "rb2505": 3000, "rb2510": 15000}
        snapshot2 = selector.select(oi2, vol2, now_ts=1700000400.0)

        # Assert - Evidence
        assert snapshot2.dominant_by_product["rb"] == "rb2510", (
            f"[{self.RULE_ID}] Should switch after cooldown period (400s > {ROLL_COOLDOWN_S}s)"
        )

    def test_no_switch_below_edge_threshold(self, instrument_cache: InstrumentCache) -> None:
        """未达到切换门槛时不切换."""
        selector = UniverseSelector(
            instrument_cache,
            roll_cooldown_s=0.0,  # Disable cooldown
            min_switch_edge=MIN_SWITCH_EDGE,  # 10% threshold
        )

        # Initial: rb2505 score = 5000*0.6+3000*0.4 = 4200
        oi1 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 2000}
        vol1 = {"rb2501": 500, "rb2505": 3000, "rb2510": 1000}
        selector.select(oi1, vol1, now_ts=1700000000.0)

        # rb2510 score = 5100*0.6+3100*0.4 = 4300, edge = (4300-4200)/4200 = 2.4% < 10%
        oi2 = {"rb2501": 1000, "rb2505": 5000, "rb2510": 5100}
        vol2 = {"rb2501": 500, "rb2505": 3000, "rb2510": 3100}
        snapshot2 = selector.select(oi2, vol2, now_ts=1700000400.0)

        # Assert - Evidence
        assert snapshot2.dominant_by_product["rb"] == "rb2505", (
            f"[{self.RULE_ID}] Should NOT switch below {MIN_SWITCH_EDGE * 100}% edge"
        )


class TestUnivExpiryGate:
    """V2 Scenario: UNIV.EXPIRY.GATE - 临期合约排除."""

    RULE_ID = "UNIV.EXPIRY.GATE"
    COMPONENT = "UniverseSelector"

    def test_expiring_contract_excluded(self) -> None:
        """临期合约（<EXPIRY_BLOCK_DAYS天）被排除."""
        cache = InstrumentCache()
        # rb2501 expires on 20250115, trading_day=20250112 -> 3 days to expiry
        cache.add(make_instrument("rb2501", "rb", "20250115"))
        # rb2505 expires on 20250515 -> far from expiry
        cache.add(make_instrument("rb2505", "rb", "20250515"))

        selector = UniverseSelector(cache, expiry_block_days=EXPIRY_BLOCK_DAYS)

        # rb2501 has higher score but expires in 3 days (< 5 days block)
        oi = {"rb2501": 10000, "rb2505": 5000}
        vol = {"rb2501": 8000, "rb2505": 3000}

        snapshot = selector.select(oi, vol, now_ts=1736640000.0, trading_day="20250112")

        # Assert - Evidence
        assert snapshot.dominant_by_product["rb"] == "rb2505", (
            f"[{self.RULE_ID}] Expiring contract rb2501 (3 days) "
            f"should be excluded (threshold={EXPIRY_BLOCK_DAYS} days)"
        )

    def test_non_expiring_contract_included(self) -> None:
        """非临期合约正常参与选择."""
        cache = InstrumentCache()
        cache.add(make_instrument("rb2501", "rb", "20250115"))
        cache.add(make_instrument("rb2505", "rb", "20250515"))

        selector = UniverseSelector(cache, expiry_block_days=EXPIRY_BLOCK_DAYS)

        # trading_day=20250101 -> rb2501 has 14 days (>5), should be included
        oi = {"rb2501": 10000, "rb2505": 5000}
        vol = {"rb2501": 8000, "rb2505": 3000}

        snapshot = selector.select(oi, vol, now_ts=1735689600.0, trading_day="20250101")

        # Assert - Evidence
        assert snapshot.dominant_by_product["rb"] == "rb2501", (
            f"[{self.RULE_ID}] Non-expiring contract rb2501 (14 days) "
            f"should be included and selected as dominant"
        )
