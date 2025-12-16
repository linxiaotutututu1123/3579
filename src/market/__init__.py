"""
src/market/ - 合约化行情层

V4PRO Platform Component - Phase 0/7
V2 SPEC: 第 4 章

模块职责：
- 合约元数据缓存 (InstrumentCache)
- 主力/次主力选择 (UniverseSelector)
- 行情订阅管理 (Subscriber)
- L1 行情缓存 + stale 检测 (QuoteCache)
- 连续主力 bars 聚合 (BarBuilder)
- 数据质量检测 (Quality)
- 六大交易所配置 (ExchangeConfig) - Phase 7 新增
- 夜盘交易日历 (TradingCalendar) - Phase 7 新增

Required Scenarios (13+ 条):
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
- CHINA.EXCHANGE.CONFIG_LOAD (Phase 7)
- CHINA.EXCHANGE.PRODUCT_MAP (Phase 7)
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
