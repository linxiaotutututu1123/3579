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
- MarginMonitor: 保证金监控 (Phase 7 新增)

军规覆盖:
- M6: 熔断保护
- M13: 涨跌停感知
- M16: 保证金实时监控
"""

from src.execution.protection.fat_finger import FatFingerConfig, FatFingerGate
from src.execution.protection.limit_price import (
    PRODUCT_LIMIT_PCT,
    LimitPriceCheckOutput,
    LimitPriceCheckResult,
    LimitPriceConfig,
    LimitPriceGuard,
    LimitPrices,
    LimitStatus,
    check_limit_price,
    get_default_guard,
    get_limit_prices,
)
from src.execution.protection.liquidity import LiquidityConfig, LiquidityGate
from src.execution.protection.margin_monitor import (
    MarginAlert,
    MarginConfig,
    MarginLevel,
    MarginMonitor,
    MarginSnapshot,
    MarginStatus,
    OpenPositionCheckResult,
    can_open,
    check_margin,
    get_default_monitor,
)
from src.execution.protection.throttle import ThrottleConfig, ThrottleGate


__all__ = [
    "PRODUCT_LIMIT_PCT",
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
    "MarginAlert",
    "MarginConfig",
    "MarginLevel",
    "MarginMonitor",
    "MarginSnapshot",
    "MarginStatus",
    "OpenPositionCheckResult",
    "ThrottleConfig",
    "ThrottleGate",
    "can_open",
    "check_limit_price",
    "check_margin",
    "get_default_guard",
    "get_default_monitor",
    "get_limit_prices",
]
