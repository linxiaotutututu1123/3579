"""
策略联邦模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: §28 策略联邦, §29 信号融合, §30 风险对冲

军规覆盖:
- M1: 单一信号源 - 联邦输出为唯一信号源
- M3: 审计日志 - 完整的操作追踪
- M6: 熔断保护 - 熔断时自动回收资源
- M19: 风险归因 - 策略贡献度追踪
- M20: 跨所一致 - 策略间相关性抑制

模块组成:
- central_coordinator: 联邦中枢协调器
- registry: 策略注册与生命周期管理
- allocator: 资源分配器
- arbiter: 信号仲裁器 (冲突检测与解决)
- models: 数据模型定义
"""

from __future__ import annotations

from src.strategy.federation.arbiter import (
    ArbiterConfig,
    ArbiterDecision,
    ArbiterStatus,
    ArbitrationResult,
    SignalArbiter,
    SignalKey,
    create_arbiter,
    create_config,
)
from src.strategy.federation.allocator import (
    ResourceAllocator,
    ResourcePool,
    ResourceUsage,
    create_allocator,
)
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
from src.strategy.federation.models import (
    AuditEntry,
    AuditEventType,
    ConflictRecord,
    ConflictType,
    FederationStatus,
    ResolutionAction,
    ResourceAllocation,
    ResourceRequest,
    ResourceType,
    StrategyState,
    StrategyStatus,
)
from src.strategy.federation.registry import (
    RegistryEvent,
    RegistryEventType,
    StrategyMetadata,
    StrategyRegistry,
)


__all__ = [
    # Allocator
    "ResourceAllocator",
    "ResourcePool",
    "ResourceUsage",
    "create_allocator",
    # Central Coordinator
    "CorrelationMatrix",
    "FederationSignal",
    "SignalDirection",
    "SignalStrength",
    "StrategyFederation",
    "StrategyMember",
    "StrategySignal",
    "create_federation",
    "create_signal",
    # Models
    "AuditEntry",
    "AuditEventType",
    "ConflictRecord",
    "ConflictType",
    "FederationStatus",
    "ResolutionAction",
    "ResourceAllocation",
    "ResourceRequest",
    "ResourceType",
    "StrategyState",
    "StrategyStatus",
    # Registry
    "RegistryEvent",
    "RegistryEventType",
    "StrategyMetadata",
    "StrategyRegistry",
]
