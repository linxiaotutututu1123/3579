"""Calendar Arbitrage Module (Military-Grade v3.0).

This module implements calendar spread arbitrage between near and far
month contracts as specified in V2 SPEC Chapter 9.

Components:
- CalendarArbStrategy: Main strategy class
- KalmanBetaEstimator: Kalman filter for beta estimation
- ArbConfig: Strategy configuration
- KalmanConfig: Kalman filter configuration

Required Scenarios (12 total):
- Fallback (3): ON_EXCEPTION, ON_TIMEOUT, CHAIN_DEFINED (in fallback.py)
- Kalman (3): BETA_ESTIMATE, RESIDUAL_ZSCORE, BETA_BOUND
- Strategy (6): LEGS_FIXED, HALF_LIFE_GATE, STOP_Z_BREAKER,
                EXPIRY_GATE, CORRELATION_BREAK, COST_ENTRY_GATE

Example:
    from src.strategy.calendar_arb import (
        CalendarArbStrategy,
        ArbConfig,
        KalmanBetaEstimator,
        KalmanConfig,
    )

    # Configure strategy
    config = ArbConfig(
        entry_z=2.5,
        exit_z=0.5,
        stop_z=5.0,
        max_half_life_days=20,
    )

    # Create strategy
    strategy = CalendarArbStrategy(config, product="AO")

    # Set leg pair
    strategy.set_leg_pair(
        near_symbol="AO2501",
        far_symbol="AO2505",
        near_expiry="20250115",
        far_expiry="20250515",
    )

    # Process tick
    portfolio = strategy.on_tick(market_state)
"""

from __future__ import annotations

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
    "KalmanBetaEstimator",
    "KalmanConfig",
    "KalmanResult",
    "LegPair",
]
