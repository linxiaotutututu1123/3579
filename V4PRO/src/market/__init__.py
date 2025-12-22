"""
src/market/ - 合约化行情层

V4PRO Platform Component - Phase 0/7/9
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
- 主力合约追踪器 (MainContractTracker) - v4.1 新增
- 配置验证加载器 (ConfigLoader) - v4.1 新增
- 涨跌停处理器 (LimitHandler) - Phase 9 新增

Required Scenarios (15+ 条):
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
- MAIN.CONTRACT.DETECT (v4.1)
- MAIN.CONTRACT.SWITCH (v4.1)
- CONFIG.VALIDATE.PYDANTIC (v4.1)
- CHINA.LIMIT.STATE_DETECT (Phase 9)
- CHINA.LIMIT.PRICE_ADJUST (Phase 9)
"""

from __future__ import annotations

from src.market.bar_builder import BarBuilder
from src.market.config_loader import (
    ConfigValidator,
    ExchangeConfigModel,
    ExchangeInfoModel,
    ProductModel,
    TradingSessionModel,
    TradingSessionsModel,
    get_all_products_from_configs,
    load_all_exchanges,
    load_exchange_config,
    validate_exchange_config,
)
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
from src.market.limit_handler import (
    LimitHandlerConfig,
    LimitPriceHandler,
    LimitPriceInfo,
    LimitState,
    PriceValidationOutput,
    PriceValidationResult,
    SymbolLimitState,
    calculate_limit_prices,
    detect_limit_state,
    get_default_handler,
    validate_and_adjust_price,
)
from src.market.main_contract_tracker import (
    ContractMetrics,
    ContractSwitchEvent,
    MainContractTracker,
    ProductState,
    SwitchReason,
    create_tracker,
    extract_product,
    is_main_month,
)
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
    # v4.1 新增: 配置验证
    "ConfigValidator",
    # v4.1 新增: 主力合约追踪器
    "ContractMetrics",
    "ContractSwitchEvent",
    # Phase 7 新增: 六大交易所配置
    "Exchange",
    "ExchangeConfig",
    "ExchangeConfigModel",
    "ExchangeInfoModel",
    "InstrumentCache",
    "InstrumentInfo",
    # Phase 9 新增: 涨跌停处理器
    "LimitHandlerConfig",
    "LimitPriceHandler",
    "LimitPriceInfo",
    "LimitState",
    "MainContractTracker",
    "NightSessionEnd",
    "ProductModel",
    "PriceValidationOutput",
    "PriceValidationResult",
    "ProductState",
    "QualityChecker",
    "QuoteCache",
    "Subscriber",
    "SwitchReason",
    "SymbolLimitState",
    "TradingDayInfo",
    "TradingPeriod",
    "TradingSession",
    "TradingSessionModel",
    "TradingSessionsModel",
    "UniverseSelector",
    "UniverseSnapshot",
    "calculate_limit_prices",
    "create_tracker",
    "detect_limit_state",
    "extract_product",
    "get_all_exchanges",
    "get_all_products_from_configs",
    "get_default_calendar",
    "get_default_handler",
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
    "is_main_month",
    "is_trading_day",
    "is_trading_time",
    "load_all_exchanges",
    "load_exchange_config",
    "validate_and_adjust_price",
    "validate_exchange_config",
]
