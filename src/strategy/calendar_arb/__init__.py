"""
日历套利模块 (军规级 v4.0).

V4PRO Platform Component - Phase 3 + Phase 7 中国期货特化
V4 SPEC: §8 Phase 3, §12 Phase 7

功能特性:
- 日历价差套利策略 (CalendarArbStrategy)
- Kalman滤波动态Beta估计 (KalmanBetaEstimator)
- 交割感知移仓换月 (DeliveryAwareCalendarArb)
- 主力合约切换检测 (MainContractDetector)

军规覆盖:
- M6: 熔断保护
- M15: 夜盘跨日处理

Scenarios (18 total):
- Fallback (3): ON_EXCEPTION, ON_TIMEOUT, CHAIN_DEFINED
- Kalman (3): BETA_ESTIMATE, RESIDUAL_ZSCORE, BETA_BOUND
- Strategy (6): LEGS_FIXED, HALF_LIFE_GATE, STOP_Z_BREAKER,
                EXPIRY_GATE, CORRELATION_BREAK, COST_ENTRY_GATE
- Delivery (2): DELIVERY_AWARE, POSITION_TRANSFER

示例:
    >>> from src.strategy.calendar_arb import (
    ...     CalendarArbStrategy,
    ...     DeliveryAwareCalendarArb,
    ...     DeliveryConfig,
    ... )
"""

from __future__ import annotations

from src.strategy.calendar_arb.delivery_aware import (
    ContractInfo,
    DeliveryAwareCalendarArb,
    DeliveryConfig,
    DeliverySnapshot,
    DeliveryStatus,
    MainContractDetector,
    RollPlan,
    RollSignal,
    check_contract_delivery,
    create_delivery_aware_strategy,
    get_default_delivery_config,
)
from src.strategy.calendar_arb.kalman_beta import (
    KalmanBetaEstimator,
    KalmanConfig,
    KalmanResult,
)
from src.strategy.calendar_arb.strategy import (
    ArbConfig,
    ArbSignal,
    ArbSnapshot,
    ArbState,
    CalendarArbStrategy,
    LegPair,
)


__all__ = [
    "ArbConfig",
    "ArbSignal",
    "ArbSnapshot",
    "ArbState",
    "CalendarArbStrategy",
    "ContractInfo",
    "DeliveryAwareCalendarArb",
    "DeliveryConfig",
    "DeliverySnapshot",
    "DeliveryStatus",
    "KalmanBetaEstimator",
    "KalmanConfig",
    "KalmanResult",
    "LegPair",
    "MainContractDetector",
    "RollPlan",
    "RollSignal",
    "check_contract_delivery",
    "create_delivery_aware_strategy",
    "get_default_delivery_config",
]
