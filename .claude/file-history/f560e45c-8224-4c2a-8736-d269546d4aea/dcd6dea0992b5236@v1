"""
V2 Scenario Tests: INST.CACHE.LOAD, INST.CACHE.PERSIST

Phase 0 Market Layer - InstrumentCache
军规级验收测试
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.market.instrument_cache import InstrumentCache, InstrumentInfo


class TestInstCacheLoad:
    """V2 Scenario: INST.CACHE.LOAD - 合约缓存加载."""

    RULE_ID = "INST.CACHE.LOAD"
    COMPONENT = "InstrumentCache"

    def test_load_from_valid_json_file(self) -> None:
        """从有效JSON文件加载合约信息."""
        # Arrange
        data = [
            {
                "symbol": "rb2501",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 1.0,
                "multiplier": 10,
                "max_order_volume": 500,
                "position_limit": 3000,
            },
            {
                "symbol": "rb2505",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250515",
                "tick_size": 1.0,
                "multiplier": 10,
                "max_order_volume": 500,
                "position_limit": 3000,
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            filepath = f.name

        try:
            # Act
            cache = InstrumentCache()
            loaded = cache.load_from_file(filepath)

            # Assert - Evidence
            assert loaded == 2, f"[{self.RULE_ID}] Expected 2 instruments, got {loaded}"
            assert cache.get("rb2501") is not None
            assert cache.get("rb2505") is not None
            assert cache.get("rb2501").product == "rb"
            assert cache.get("rb2501").tick_size == 1.0
        finally:
            Path(filepath).unlink()

    def test_load_file_not_found_returns_zero(self) -> None:
        """文件不存在时返回0."""
        cache = InstrumentCache()
        loaded = cache.load_from_file("/nonexistent/path.json")

        assert loaded == 0, f"[{self.RULE_ID}] Expected 0 for missing file"

    def test_load_invalid_json_returns_zero(self) -> None:
        """无效JSON返回0."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json {{{")
            filepath = f.name

        try:
            cache = InstrumentCache()
            loaded = cache.load_from_file(filepath)
            assert loaded == 0, f"[{self.RULE_ID}] Expected 0 for invalid JSON"
        finally:
            Path(filepath).unlink()

    def test_get_by_product_returns_all_contracts(self) -> None:
        """按品种获取所有合约."""
        cache = InstrumentCache()
        cache.add(
            InstrumentInfo(
                symbol="rb2501",
                product="rb",
                exchange="SHFE",
                expire_date="20250115",
                tick_size=1.0,
                multiplier=10,
                max_order_volume=500,
                position_limit=3000,
            )
        )
        cache.add(
            InstrumentInfo(
                symbol="rb2505",
                product="rb",
                exchange="SHFE",
                expire_date="20250515",
                tick_size=1.0,
                multiplier=10,
                max_order_volume=500,
                position_limit=3000,
            )
        )
        cache.add(
            InstrumentInfo(
                symbol="hc2501",
                product="hc",
                exchange="SHFE",
                expire_date="20250115",
                tick_size=1.0,
                multiplier=10,
                max_order_volume=500,
                position_limit=3000,
            )
        )

        rb_contracts = cache.get_by_product("rb")
        assert len(rb_contracts) == 2, f"[{self.RULE_ID}] Expected 2 rb contracts"
        assert all(c.product == "rb" for c in rb_contracts)


class TestInstCachePersist:
    """V2 Scenario: INST.CACHE.PERSIST - 合约缓存持久化."""

    RULE_ID = "INST.CACHE.PERSIST"
    COMPONENT = "InstrumentCache"

    def test_persist_atomic_write(self) -> None:
        """原子写入（tmp + rename）."""
        cache = InstrumentCache()
        cache.add(
            InstrumentInfo(
                symbol="rb2501",
                product="rb",
                exchange="SHFE",
                expire_date="20250115",
                tick_size=1.0,
                multiplier=10,
                max_order_volume=500,
                position_limit=3000,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "instruments.json"

            # Act
            result = cache.persist(str(filepath))

            # Assert - Evidence
            assert result is True, f"[{self.RULE_ID}] Persist should return True"
            assert filepath.exists(), f"[{self.RULE_ID}] File should exist"

            # Verify content
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            assert len(data) == 1
            assert data[0]["symbol"] == "rb2501"

    def test_persist_and_reload_roundtrip(self) -> None:
        """持久化后可重新加载（round-trip）."""
        # Arrange
        cache1 = InstrumentCache()
        cache1.add(
            InstrumentInfo(
                symbol="rb2501",
                product="rb",
                exchange="SHFE",
                expire_date="20250115",
                tick_size=1.0,
                multiplier=10,
                max_order_volume=500,
                position_limit=3000,
            )
        )
        cache1.add(
            InstrumentInfo(
                symbol="hc2501",
                product="hc",
                exchange="SHFE",
                expire_date="20250115",
                tick_size=2.0,
                multiplier=10,
                max_order_volume=400,
                position_limit=2000,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "instruments.json"

            # Act - persist
            cache1.persist(str(filepath))

            # Act - reload
            cache2 = InstrumentCache()
            loaded = cache2.load_from_file(str(filepath))

            # Assert - Evidence
            assert loaded == 2, f"[{self.RULE_ID}] Should reload 2 instruments"
            rb = cache2.get("rb2501")
            assert rb is not None
            assert rb.tick_size == 1.0
            hc = cache2.get("hc2501")
            assert hc is not None
            assert hc.tick_size == 2.0
