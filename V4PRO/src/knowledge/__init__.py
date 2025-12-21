"""
知识库模块 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

知识库核心架构:
- 经验知识库 (Reflexion): 反思记忆存储
- 模式知识库 (Patterns): 市场模式存储
- 决策知识库 (Decisions): 决策日志存储
- 知识融合引擎: 策略优化/风控增强/故障预防
- 知识沉淀管理: 自动归档/版本控制/价值评估

分层存储方案:
- HOT (热数据): Redis/Memory - 最近7天
- WARM (温数据): SQLite - 7-90天
- COLD (冷数据): File - 90天以上

军规覆盖:
- M33: 知识沉淀机制 (核心实现)
- M3: 审计日志完整
- M7: 场景回放支持

Usage:
    from src.knowledge import (
        # 基础类型
        KnowledgeEntry,
        KnowledgeType,
        KnowledgePriority,
        StorageTier,

        # 存储层
        TieredStorage,
        TieredStorageConfig,
        HotStorage,
        WarmStorage,
        ColdStorage,

        # 知识沉淀管理 (M33军规)
        KnowledgePrecipitator,
        KnowledgeVersion,
        PrecipitationLevel,
        PrecipitationRule,

        # 经验知识库
        ReflexionStore,
        Experience,
        ExperienceType,
        ExperienceCategory,

        # 模式知识库
        PatternStore,
        Pattern,
        PatternType,
        MarketRegime,

        # 决策知识库
        DecisionLog,
        Decision,
        DecisionType,
        DecisionOutcome,

        # 融合引擎
        FusionEngine,
        FusionContext,
        Recommendation,
        RecommendationType,

        # 查询接口
        KnowledgeQuery,
        SearchQuery,
        SearchResult,
        SearchScope,
    )

    # 快速创建知识库系统
    storage = TieredStorage()
    reflexion = ReflexionStore(storage)
    patterns = PatternStore(storage)
    decisions = DecisionLog(storage)
    fusion = FusionEngine(reflexion, patterns, decisions)
    query = KnowledgeQuery(reflexion, patterns, decisions)

    # 知识沉淀管理 (M33军规合规)
    precipitator = KnowledgePrecipitator(storage)
    # 自动维护和归档
    precipitator.run_maintenance()
    # 获取沉淀报告
    report = precipitator.get_precipitation_report(days=7)
"""

from src.knowledge.base import (
    STORAGE_TIER_THRESHOLDS,
    KnowledgeAuditRecord,
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
    QueryContext,
    StorageTier,
    validate_knowledge_entry,
)
from src.knowledge.decision_log import (
    Decision,
    DecisionContext,
    DecisionLog,
    DecisionOutcome,
    DecisionRationale,
    DecisionResult,
    DecisionType,
)
from src.knowledge.fusion_engine import (
    FusionContext,
    FusionEngine,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from src.knowledge.pattern_store import (
    COMMON_PATTERNS,
    MarketRegime,
    Pattern,
    PatternOccurrence,
    PatternSignature,
    PatternStore,
    PatternStrength,
    PatternType,
)
from src.knowledge.precipitator import (
    KnowledgePrecipitator,
    KnowledgeVersion,
    MaintenanceAction,
    PrecipitationLevel,
    PrecipitationRecord,
    PrecipitationRule,
)
from src.knowledge.query import (
    KnowledgeQuery,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchScope,
    SortOrder,
)
from src.knowledge.reflexion import (
    Experience,
    ExperienceCategory,
    ExperienceContext,
    ExperienceOutcome,
    ExperienceType,
    ReflexionStore,
    create_reflexion_from_decision,
)
from src.knowledge.storage import (
    ColdStorage,
    HotStorage,
    TieredStorage,
    TieredStorageConfig,
    WarmStorage,
)


__all__ = [
    # ========== base.py ==========
    # 核心类型
    "KnowledgeEntry",
    "KnowledgeType",
    "KnowledgePriority",
    "StorageTier",
    "STORAGE_TIER_THRESHOLDS",
    # 基类和辅助
    "KnowledgeStore",
    "KnowledgeAuditRecord",
    "QueryContext",
    "validate_knowledge_entry",
    # ========== storage.py ==========
    # 分层存储
    "TieredStorage",
    "TieredStorageConfig",
    "HotStorage",
    "WarmStorage",
    "ColdStorage",
    # ========== precipitator.py ==========
    # 知识沉淀管理 (M33军规)
    "KnowledgePrecipitator",
    "KnowledgeVersion",
    "MaintenanceAction",
    "PrecipitationLevel",
    "PrecipitationRecord",
    "PrecipitationRule",
    # ========== reflexion.py ==========
    # 反思记忆库
    "ReflexionStore",
    "Experience",
    "ExperienceType",
    "ExperienceCategory",
    "ExperienceContext",
    "ExperienceOutcome",
    "create_reflexion_from_decision",
    # ========== pattern_store.py ==========
    # 模式存储
    "PatternStore",
    "Pattern",
    "PatternType",
    "PatternStrength",
    "PatternSignature",
    "PatternOccurrence",
    "MarketRegime",
    "COMMON_PATTERNS",
    # ========== decision_log.py ==========
    # 决策日志
    "DecisionLog",
    "Decision",
    "DecisionType",
    "DecisionOutcome",
    "DecisionContext",
    "DecisionRationale",
    "DecisionResult",
    # ========== fusion_engine.py ==========
    # 融合引擎
    "FusionEngine",
    "FusionContext",
    "Recommendation",
    "RecommendationType",
    "RecommendationPriority",
    # ========== query.py ==========
    # 查询接口
    "KnowledgeQuery",
    "SearchQuery",
    "SearchResult",
    "SearchResponse",
    "SearchScope",
    "SortOrder",
]
