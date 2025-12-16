"""
Protection Module - 风控保护层 (军规级 v4.0).

V4PRO Platform Component - Phase 2 + Phase 7
V2 SPEC: 5.9
V4 SPEC: §18 涨跌停板规则, §19 保证金制度

Exports:
- LiquidityGate: 流动性门控
- FatFingerGate: 胖手指检查
- ThrottleGate: 节流控制
- LimitPriceGuard: 涨跌停保护 (Phase 7 新增)

军规覆盖:
- M6: 熔断保护
- M13: 涨跌停感知
"""

from src.execution.protection.fat_finger import FatFingerConfig, FatFingerGate
from src.execution.protection.limit_price import (
    LimitPriceCheckOutput,
    LimitPriceCheckResult,
    LimitPriceConfig,
    LimitPriceGuard,
    LimitPrices,
    LimitStatus,
    PRODUCT_LIMIT_PCT,
    check_limit_price,
    get_default_guard,
    get_limit_prices,
)
from src.execution.protection.liquidity import LiquidityConfig, LiquidityGate
from src.execution.protection.throttle import ThrottleConfig, ThrottleGate


__all__ = [
    "FatFingerConfig",
    "FatFingerGate",
    "LimitPriceCheckOutput",
    "LimitPriceCheckResult",
    "LimitPriceConfig",
    "LimitPriceGuard",
    "LimitPrices",
    "LimitStatus",
    "LiquidityConfig",
    "LiquidityGate",
    "PRODUCT_LIMIT_PCT",
    "ThrottleConfig",
    "ThrottleGate",
    "check_limit_price",
    "get_default_guard",
    "get_limit_prices",
]
