"""
知识库模块测试配置.

提供测试夹具和通用工具。
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from typing import Generator

import pytest

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeType,
)
from src.knowledge.decision_log import (
    Decision,
    DecisionContext,
    DecisionLog,
    DecisionOutcome,
    DecisionRationale,
    DecisionType,
)
from src.knowledge.fusion_engine import FusionContext, FusionEngine
from src.knowledge.pattern_store import (
    MarketRegime,
    Pattern,
    PatternOccurrence,
    PatternSignature,
    PatternStore,
    PatternStrength,
    PatternType,
)
from src.knowledge.query import KnowledgeQuery
from src.knowledge.reflexion import (
    Experience,
    ExperienceCategory,
    ExperienceContext,
    ExperienceOutcome,
    ExperienceType,
    ReflexionStore,
)
from src.knowledge.storage import (
    ColdStorage,
    HotStorage,
    TieredStorage,
    TieredStorageConfig,
    WarmStorage,
)
from src.knowledge.precipitator import (
    KnowledgePrecipitator,
    PrecipitationLevel,
    PrecipitationRule,
    MaintenanceAction,
)


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """创建临时目录."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def hot_storage() -> HotStorage:
    """创建热存储实例."""
    return HotStorage(name="test_hot", max_items=100, ttl_seconds=3600)


@pytest.fixture
def warm_storage(temp_dir: str) -> WarmStorage:
    """创建温存储实例."""
    db_path = os.path.join(temp_dir, "test_warm.db")
    return WarmStorage(name="test_warm", db_path=db_path)


@pytest.fixture
def cold_storage(temp_dir: str) -> ColdStorage:
    """创建冷存储实例."""
    storage_dir = os.path.join(temp_dir, "test_cold")
    return ColdStorage(name="test_cold", storage_dir=storage_dir, compress=False)


@pytest.fixture
def tiered_storage(temp_dir: str) -> TieredStorage:
    """创建分层存储实例."""
    config = TieredStorageConfig(
        hot_max_items=100,
        hot_ttl_seconds=3600,
        warm_db_path=os.path.join(temp_dir, "tiered_warm.db"),
        cold_dir_path=os.path.join(temp_dir, "tiered_cold"),
        audit_enabled=False,
    )
    return TieredStorage(config=config, name="test_tiered")


@pytest.fixture
def sample_entry() -> KnowledgeEntry:
    """创建示例知识条目."""
    return KnowledgeEntry.create(
        knowledge_type=KnowledgeType.REFLEXION,
        content={"key": "value", "data": [1, 2, 3]},
        priority=KnowledgePriority.MEDIUM,
        tags=["test", "sample"],
        run_id="run-123",
        source="test",
    )


@pytest.fixture
def reflexion_store(tiered_storage: TieredStorage) -> ReflexionStore:
    """创建反思记忆库实例."""
    return ReflexionStore(storage=tiered_storage, name="test_reflexion")


@pytest.fixture
def pattern_store(tiered_storage: TieredStorage) -> PatternStore:
    """创建模式存储实例."""
    return PatternStore(storage=tiered_storage, name="test_patterns")


@pytest.fixture
def decision_log(tiered_storage: TieredStorage) -> DecisionLog:
    """创建决策日志实例."""
    return DecisionLog(storage=tiered_storage, name="test_decisions")


@pytest.fixture
def fusion_engine(
    reflexion_store: ReflexionStore,
    pattern_store: PatternStore,
    decision_log: DecisionLog,
) -> FusionEngine:
    """创建融合引擎实例."""
    return FusionEngine(
        reflexion_store=reflexion_store,
        pattern_store=pattern_store,
        decision_log=decision_log,
    )


@pytest.fixture
def knowledge_query(
    reflexion_store: ReflexionStore,
    pattern_store: PatternStore,
    decision_log: DecisionLog,
) -> KnowledgeQuery:
    """创建查询引擎实例."""
    return KnowledgeQuery(
        reflexion_store=reflexion_store,
        pattern_store=pattern_store,
        decision_log=decision_log,
    )


@pytest.fixture
def sample_experience() -> Experience:
    """创建示例经验."""
    return Experience.create(
        exp_type=ExperienceType.SUCCESS,
        category=ExperienceCategory.STRATEGY,
        title="成功的趋势跟踪",
        description="在上升趋势中跟随突破信号入场",
        context=ExperienceContext(
            market_state="trending_up",
            strategy_id="trend_follower",
            symbol="IF2401",
            session="day",
        ),
        outcome=ExperienceOutcome(
            success=True,
            pnl=5000.0,
            pnl_pct=0.05,
            impact=8,
            lessons=["及时止盈很重要"],
        ),
        confidence=0.85,
        tags=["trend", "breakout"],
    )


@pytest.fixture
def sample_pattern() -> Pattern:
    """创建示例模式."""
    pattern = Pattern.create(
        pattern_type=PatternType.BREAKOUT,
        name="突破前高",
        description="价格突破前期高点形成新趋势",
        regime=MarketRegime.TRENDING_UP,
        strength=PatternStrength.STRONG,
        signature=PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        ),
        tags=["breakout", "bullish"],
    )
    # 添加历史出现记录
    pattern.add_occurrence(PatternOccurrence(
        timestamp=time.time() - 86400,
        symbol="IF2401",
        price=4000.0,
        outcome=0.02,
        confidence=0.8,
    ))
    return pattern


@pytest.fixture
def sample_decision() -> Decision:
    """创建示例决策."""
    return Decision.create(
        decision_type=DecisionType.ENTRY,
        strategy_id="trend_follower",
        symbol="IF2401",
        direction="long",
        target_qty=2,
        context=DecisionContext(
            market_price=4000.0,
            bid_price=3999.0,
            ask_price=4001.0,
            position={},
            portfolio_value=1000000.0,
            volatility=0.02,
            market_regime="trending_up",
            session="day",
        ),
        rationale=DecisionRationale(
            signals=["breakout_signal"],
            indicators={"rsi": 65, "macd": 0.5},
            rules_triggered=["trend_following"],
            confidence=0.8,
        ),
        tags=["entry", "trend"],
    )


@pytest.fixture
def sample_fusion_context() -> FusionContext:
    """创建示例融合上下文."""
    return FusionContext(
        symbol="IF2401",
        strategy_id="trend_follower",
        market_regime=MarketRegime.TRENDING_UP,
        position={"IF2401": 2},
        portfolio_value=1000000.0,
        volatility=0.02,
        session="day",
    )


@pytest.fixture
def precipitator(tiered_storage: TieredStorage, temp_dir: str) -> KnowledgePrecipitator:
    """创建知识沉淀管理器实例."""
    archive_dir = os.path.join(temp_dir, "archive")
    return KnowledgePrecipitator(
        storage=tiered_storage,
        archive_dir=archive_dir,
        auto_maintenance=False,  # 测试时禁用自动维护
    )
