"""
src/market/ - 合约化行情层

V3PRO+ Platform Component - Phase 0
V2 SPEC: 第 4 章

模块职责：
- 合约元数据缓存 (InstrumentCache)
- 主力/次主力选择 (UniverseSelector)
- 行情订阅管理 (Subscriber)
- L1 行情缓存 + stale 检测 (QuoteCache)
- 连续主力 bars 聚合 (BarBuilder)
- 数据质量检测 (Quality)

Required Scenarios (11 条):
- INST.CACHE.LOAD
- INST.CACHE.PERSIST
- UNIV.DOMINANT.BASIC
- UNIV.SUBDOMINANT.PAIRING
- UNIV.ROLL.COOLDOWN
- UNIV.EXPIRY.GATE
- MKT.SUBSCRIBER.DIFF_UPDATE
- MKT.STALE.SOFT
- MKT.STALE.HARD
- MKT.CONTINUITY.BARS
- MKT.QUALITY.OUTLIER
"""

from __future__ import annotations

from src.market.bar_builder import BarBuilder
from src.market.instrument_cache import InstrumentCache, InstrumentInfo
from src.market.quality import QualityChecker
from src.market.quote_cache import BookTop, QuoteCache
from src.market.subscriber import Subscriber
from src.market.universe_selector import UniverseSelector, UniverseSnapshot


__all__ = [
    "BarBuilder",
    "BookTop",
    "InstrumentCache",
    "InstrumentInfo",
    "QualityChecker",
    "QuoteCache",
    "Subscriber",
    "UniverseSelector",
    "UniverseSnapshot",
]
