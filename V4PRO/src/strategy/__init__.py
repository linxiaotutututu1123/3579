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
- 单一信号源机制 (signal/) - D7-P0 新增

Required Scenarios:
- STRAT.BASE.ON_TICK
- STRAT.FALLBACK.ON_EXCEPTION
- STRAT.FALLBACK.ON_TIMEOUT
- STRAT.FALLBACK.CHAIN_DEFINED
- FED.REGISTER (v4.2)
- FED.SIGNAL.FUSE (v4.2)
- FED.CORRELATION (v4.2)
- SIGNAL.SOURCE.UNIQUE (M1)
- SIGNAL.VALIDATE (M1)
- SIGNAL.CONFLICT.RESOLVE (M1)

军规覆盖:
- M1: 单一信号源 - 信号源唯一性保证
- M3: 审计日志 - 完整信号追溯
- M4: 降级兜底 - 策略降级链
- M7: 场景回放 - 信号可重放
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
from src.strategy.signal import (
    # 信号源定义
    SignalPriority,
    SignalSource,
    SignalSourceID,
    SignalType,
    SourceStatus,
    TradingSignal,
    create_signal_source,
    generate_source_id,
    # 信号验证
    SignalValidator,
    ValidationErrorCode,
    ValidationResult,
    ValidationSeverity,
    create_validator,
    # 信号源注册表
    RegistryEvent,
    RegistryEventType,
    SignalSourceRegistry,
    SourceMetadata,
    get_registry,
    get_source,
    register_source,
    unregister_source,
    # 冲突解决
    ConflictInfo,
    ConflictSeverity,
    ConflictType,
    ResolutionResult,
    ResolutionStrategy,
    SignalConflictResolver,
    create_conflict_resolver,
    resolve_conflicts,
)
from src.strategy.types import Bar1m, MarketState, TargetPortfolio


__all__ = [
    # 基础模块
    "Bar1m",
    "MarketState",
    "Strategy",
    "TargetPortfolio",
    # 降级模块
    "DEFAULT_FALLBACK_CHAINS",
    "DEFAULT_FINAL_FALLBACK",
    "FallbackConfig",
    "FallbackEvent",
    "FallbackManager",
    "FallbackReason",
    "FallbackResult",
    # 联邦模块 (v4.2)
    "CorrelationMatrix",
    "FederationSignal",
    "SignalDirection",
    "SignalStrength",
    "StrategyFederation",
    "StrategyMember",
    "StrategySignal",
    "create_federation",
    "create_signal",
    # 信号源模块 (D7-P0 M1军规)
    "SignalPriority",
    "SignalSource",
    "SignalSourceID",
    "SignalType",
    "SourceStatus",
    "TradingSignal",
    "create_signal_source",
    "generate_source_id",
    # 信号验证模块
    "SignalValidator",
    "ValidationErrorCode",
    "ValidationResult",
    "ValidationSeverity",
    "create_validator",
    # 信号源注册表模块
    "RegistryEvent",
    "RegistryEventType",
    "SignalSourceRegistry",
    "SourceMetadata",
    "get_registry",
    "get_source",
    "register_source",
    "unregister_source",
    # 冲突解决模块
    "ConflictInfo",
    "ConflictSeverity",
    "ConflictType",
    "ResolutionResult",
    "ResolutionStrategy",
    "SignalConflictResolver",
    "create_conflict_resolver",
    "resolve_conflicts",
]
