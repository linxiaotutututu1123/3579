"""
Strategy Module - 策略框架与降级管理 (军规级 v4.2).

V4PRO Platform Component - Phase 0/3/8
V2 SPEC: 第 5 章 策略框架
V4 SPEC: §28 策略联邦, §29 信号融合, §30 风险对冲

模块职责:
- 策略基类 (Strategy)
- 类型定义 (MarketState, TargetPortfolio)
- 降级管理 (FallbackManager)
- 策略工厂 (create_strategy)
- 策略联邦 (StrategyFederation) - v4.2 新增

Required Scenarios:
- STRAT.BASE.ON_TICK
- STRAT.FALLBACK.ON_EXCEPTION
- STRAT.FALLBACK.ON_TIMEOUT
- STRAT.FALLBACK.CHAIN_DEFINED
- FED.REGISTER (v4.2)
- FED.SIGNAL.FUSE (v4.2)
- FED.CORRELATION (v4.2)
"""

from __future__ import annotations

from src.strategy.base import Strategy
from src.strategy.fallback import (
    DEFAULT_FALLBACK_CHAINS,
    DEFAULT_FINAL_FALLBACK,
    FallbackConfig,
    FallbackEvent,
    FallbackManager,
    FallbackReason,
    FallbackResult,
)
from src.strategy.federation import (
    CorrelationMatrix,
    FederationSignal,
    SignalDirection,
    SignalStrength,
    StrategyFederation,
    StrategyMember,
    StrategySignal,
    create_federation,
    create_signal,
)
from src.strategy.types import Bar1m, MarketState, TargetPortfolio


__all__ = [
    # 联邦模块 (v4.2)
    "CorrelationMatrix",
    "DEFAULT_FALLBACK_CHAINS",
    "DEFAULT_FINAL_FALLBACK",
    "Bar1m",
    "FallbackConfig",
    "FallbackEvent",
    "FallbackManager",
    "FallbackReason",
    "FallbackResult",
    "FederationSignal",
    "MarketState",
    "SignalDirection",
    "SignalStrength",
    "Strategy",
    "StrategyFederation",
    "StrategyMember",
    "StrategySignal",
    "TargetPortfolio",
    "create_federation",
    "create_signal",
]
