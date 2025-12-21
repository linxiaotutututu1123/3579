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
from src.market.exchange_config import (
    Exchange,
    ExchangeConfig,
    NightSessionEnd,
    TradingSession,
    get_all_exchanges,
    get_exchange_by_code,
    get_exchange_config,
    get_exchange_for_product,
    get_night_session_end,
    get_night_session_end_for_product,
    get_products_by_category,
    get_products_by_exchange,
    get_trading_sessions,
    has_night_session,
)
from src.market.instrument_cache import InstrumentCache, InstrumentInfo
from src.market.quality import QualityChecker
from src.market.quote_cache import BookTop, QuoteCache
from src.market.subscriber import Subscriber
from src.market.trading_calendar import (
    ChinaTradingCalendar,
    TradingDayInfo,
    TradingPeriod,
    get_default_calendar,
    get_trading_day,
    is_trading_day,
    is_trading_time,
)
from src.market.universe_selector import UniverseSelector, UniverseSnapshot


__all__ = [
    # 原有模块
    "BarBuilder",
    "BookTop",
    # Phase 7 新增: 夜盘交易日历
    "ChinaTradingCalendar",
    # Phase 7 新增: 六大交易所配置
    "Exchange",
    "ExchangeConfig",
    "InstrumentCache",
    "InstrumentInfo",
    "NightSessionEnd",
    "QualityChecker",
    "QuoteCache",
    "Subscriber",
    "TradingDayInfo",
    "TradingPeriod",
    "TradingSession",
    "UniverseSelector",
    "UniverseSnapshot",
    "get_all_exchanges",
    "get_default_calendar",
    "get_exchange_by_code",
    "get_exchange_config",
    "get_exchange_for_product",
    "get_night_session_end",
    "get_night_session_end_for_product",
    "get_products_by_category",
    "get_products_by_exchange",
    "get_trading_day",
    "get_trading_sessions",
    "has_night_session",
    "is_trading_day",
    "is_trading_time",
]
