"""
信号模块 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制
V4 SPEC: M1军规 - 一个交易信号只能来自一个策略实例

军规覆盖:
- M1: 单一信号源 - 信号源唯一性保证
- M3: 审计日志 - 完整信号追溯
- M7: 场景回放 - 信号可重放

模块组成:
- source: 信号源定义 (SignalSource, TradingSignal)
- validator: 信号验证 (SignalValidator)
- registry: 信号源注册表 (SignalSourceRegistry)
- conflict_resolver: 冲突解决 (SignalConflictResolver)

核心功能:
1. 信号源唯一ID生成和验证
2. 信号源注册与生命周期管理
3. 信号验证和签名校验
4. 信号冲突检测与解决
5. 完整审计日志支持

示例:
    >>> from src.strategy.signal import (
    ...     SignalSource,
    ...     SignalSourceRegistry,
    ...     SignalValidator,
    ...     SignalConflictResolver,
    ...     SignalDirection,
    ... )
    >>> # 创建信号源
    >>> source = SignalSource(strategy_id="kalman_arb", instance_id="inst_001")
    >>> # 注册到全局注册表
    >>> registry = SignalSourceRegistry.get_instance()
    >>> registry.register(source)
    >>> # 创建信号
    >>> signal = source.create_signal(
    ...     symbol="rb2501",
    ...     direction=SignalDirection.LONG,
    ...     strength=0.8,
    ...     confidence=0.9
    ... )
    >>> # 验证信号
    >>> validator = SignalValidator()
    >>> validator.register_source(source)
    >>> result = validator.validate(signal)
    >>> if result.is_valid:
    ...     process_signal(signal)
"""

from __future__ import annotations

# 从 conflict_resolver 模块导出
from src.strategy.signal.conflict_resolver import (
    ConflictInfo,
    ConflictSeverity,
    ConflictType,
    ResolutionResult,
    ResolutionStrategy,
    SignalConflictResolver,
    create_conflict_resolver,
    resolve_conflicts,
)

# 从 registry 模块导出
from src.strategy.signal.registry import (
    RegistryEvent,
    RegistryEventType,
    SignalSourceRegistry,
    SourceMetadata,
    get_registry,
    get_source,
    register_source,
    unregister_source,
)

# 从 source 模块导出
from src.strategy.signal.source import (
    SignalDirection,
    SignalPriority,
    SignalSource,
    SignalSourceID,
    SignalType,
    SourceStatus,
    TradingSignal,
    create_signal_source,
    generate_source_id,
)

# 从 validator 模块导出
from src.strategy.signal.validator import (
    SignalValidator,
    ValidationErrorCode,
    ValidationResult,
    ValidationSeverity,
    create_validator,
)


__all__ = [
    # source.py - 信号源定义
    "SignalDirection",
    "SignalPriority",
    "SignalSource",
    "SignalSourceID",
    "SignalType",
    "SourceStatus",
    "TradingSignal",
    "create_signal_source",
    "generate_source_id",
    # validator.py - 信号验证
    "SignalValidator",
    "ValidationErrorCode",
    "ValidationResult",
    "ValidationSeverity",
    "create_validator",
    # registry.py - 信号源注册表
    "RegistryEvent",
    "RegistryEventType",
    "SignalSourceRegistry",
    "SourceMetadata",
    "get_registry",
    "get_source",
    "register_source",
    "unregister_source",
    # conflict_resolver.py - 冲突解决
    "ConflictInfo",
    "ConflictSeverity",
    "ConflictType",
    "ResolutionResult",
    "ResolutionStrategy",
    "SignalConflictResolver",
    "create_conflict_resolver",
    "resolve_conflicts",
]


# ============================================================
# 模块级便捷API
# ============================================================


def create_source_and_register(
    strategy_id: str,
    instance_id: str | None = None,
    signal_ttl: float = 60.0,
    tags: list[str] | None = None,
) -> SignalSource:
    """创建信号源并注册到全局注册表.

    参数:
        strategy_id: 策略ID
        instance_id: 实例ID (可选)
        signal_ttl: 信号生存时间
        tags: 标签列表

    返回:
        已注册的SignalSource实例
    """
    source = create_signal_source(
        strategy_id=strategy_id,
        instance_id=instance_id,
        signal_ttl=signal_ttl,
    )
    register_source(source, tags)
    return source


def validate_and_resolve(
    signals: list[TradingSignal],
    validator: SignalValidator | None = None,
    resolver: SignalConflictResolver | None = None,
) -> TradingSignal | None:
    """验证并解决信号冲突.

    参数:
        signals: 信号列表
        validator: 验证器 (可选)
        resolver: 冲突解决器 (可选)

    返回:
        胜出的有效信号或None
    """
    if not signals:
        return None

    # 使用默认验证器
    if validator is None:
        validator = create_validator()

    # 使用默认解决器
    if resolver is None:
        resolver = create_conflict_resolver()

    # 验证所有信号
    valid_signals = []
    for signal in signals:
        result = validator.validate(signal, strict_mode=False)
        if result.is_valid:
            valid_signals.append(signal)

    if not valid_signals:
        return None

    if len(valid_signals) == 1:
        return valid_signals[0]

    # 解决冲突
    return resolve_conflicts(valid_signals)
