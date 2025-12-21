"""
策略联邦模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: §28 策略联邦, §29 信号融合, §30 风险对冲

军规覆盖:
- M1: 单一信号源 - 联邦输出为唯一信号源
- M19: 风险归因 - 策略贡献度追踪
- M20: 跨所一致 - 策略间相关性抑制

模块组成:
- central_coordinator: 联邦中枢协调器
"""

from __future__ import annotations

from src.strategy.federation.central_coordinator import (
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


__all__ = [
    "CorrelationMatrix",
    "FederationSignal",
    "SignalDirection",
    "SignalStrength",
    "StrategyFederation",
    "StrategyMember",
    "StrategySignal",
    "create_federation",
    "create_signal",
]
