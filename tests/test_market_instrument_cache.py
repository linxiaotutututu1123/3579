"""
V2 Scenario Tests: INST.CACHE.LOAD, INST.CACHE.PERSIST

Phase 0 Market Layer - InstrumentCache
军规级验收测试
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.market.instrument_cache import InstrumentCache


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
            filepath = Path(f.name)

        try:
            # Act
            cache = InstrumentCache()
            cache.load_from_file(filepath)

            # Assert - Evidence
            assert len(cache) == 2, f"[{self.RULE_ID}] Expected 2 instruments, got {len(cache)}"
            rb2501 = cache.get("rb2501")
            rb2505 = cache.get("rb2505")
            assert rb2501 is not None, f"[{self.RULE_ID}] rb2501 should exist"
            assert rb2505 is not None, f"[{self.RULE_ID}] rb2505 should exist"
            assert rb2501.product == "rb"
            assert rb2501.tick_size == 1.0
        finally:
            filepath.unlink()

    def test_load_file_not_found_raises(self) -> None:
        """文件不存在时抛出异常."""
        cache = InstrumentCache()
        try:
            cache.load_from_file(Path("/nonexistent/path.json"))
            raise AssertionError(f"[{self.RULE_ID}] Should raise FileNotFoundError")
        except FileNotFoundError:
            pass  # Expected

    def test_load_invalid_json_raises(self) -> None:
        """无效JSON抛出异常."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not valid json {{{")
            filepath = Path(f.name)

        try:
            cache = InstrumentCache()
            try:
                cache.load_from_file(filepath)
                raise AssertionError(f"[{self.RULE_ID}] Should raise JSONDecodeError")
            except json.JSONDecodeError:
                pass  # Expected
        finally:
            filepath.unlink()

    def test_get_by_product_returns_all_contracts(self) -> None:
        """按品种获取所有合约."""
        data = [
            {
                "symbol": "rb2501",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 1.0,
                "multiplier": 10,
            },
            {
                "symbol": "rb2505",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250515",
                "tick_size": 1.0,
                "multiplier": 10,
            },
            {
                "symbol": "hc2501",
                "product": "hc",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 1.0,
                "multiplier": 10,
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            filepath = Path(f.name)

        try:
            cache = InstrumentCache()
            cache.load_from_file(filepath)

            rb_contracts = cache.get_by_product("rb")
            assert len(rb_contracts) == 2, f"[{self.RULE_ID}] Expected 2 rb contracts"
            assert all(c.product == "rb" for c in rb_contracts)
        finally:
            filepath.unlink()


class TestInstCachePersist:
    """V2 Scenario: INST.CACHE.PERSIST - 合约缓存持久化."""

    RULE_ID = "INST.CACHE.PERSIST"
    COMPONENT = "InstrumentCache"

    def test_persist_atomic_write(self) -> None:
        """原子写入（tmp + rename）."""
        # First load some data
        data = [
            {
                "symbol": "rb2501",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 1.0,
                "multiplier": 10,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Load data
            load_path = Path(tmpdir) / "source.json"
            with open(load_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            cache = InstrumentCache()
            cache.load_from_file(load_path)

            # Persist
            persist_path = Path(tmpdir) / "instruments.json"
            cache.persist(persist_path, trading_day="20250115")

            # Assert - Evidence
            assert persist_path.exists(), f"[{self.RULE_ID}] File should exist"

            # Verify content
            with open(persist_path, encoding="utf-8") as f:
                saved_data = json.load(f)
            assert saved_data["trading_day"] == "20250115"
            assert len(saved_data["instruments"]) == 1
            assert saved_data["instruments"][0]["symbol"] == "rb2501"

    def test_persist_and_reload_roundtrip(self) -> None:
        """持久化后可重新加载（round-trip）."""
        data = [
            {
                "symbol": "rb2501",
                "product": "rb",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 1.0,
                "multiplier": 10,
            },
            {
                "symbol": "hc2501",
                "product": "hc",
                "exchange": "SHFE",
                "expire_date": "20250115",
                "tick_size": 2.0,
                "multiplier": 10,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Load initial data
            load_path = Path(tmpdir) / "source.json"
            with open(load_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            cache1 = InstrumentCache()
            cache1.load_from_file(load_path)

            # Persist
            persist_path = Path(tmpdir) / "instruments.json"
            cache1.persist(persist_path, trading_day="20250115")

            # Reload
            cache2 = InstrumentCache()
            cache2.load_from_file(persist_path)

            # Assert - Evidence
            assert len(cache2) == 2, f"[{self.RULE_ID}] Should reload 2 instruments"
            rb = cache2.get("rb2501")
            assert rb is not None
            assert rb.tick_size == 1.0
            hc = cache2.get("hc2501")
            assert hc is not None
            assert hc.tick_size == 2.0
