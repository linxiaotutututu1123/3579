"""
反思记忆库测试.

测试 reflexion.py 中的经验存储功能。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.reflexion import (
    Experience,
    ExperienceCategory,
    ExperienceContext,
    ExperienceOutcome,
    ExperienceType,
    ReflexionStore,
    create_reflexion_from_decision,
)
from src.knowledge.base import KnowledgeType


class TestExperience:
    """经验条目测试."""

    def test_create_experience(self) -> None:
        """测试创建经验."""
        exp = Experience.create(
            exp_type=ExperienceType.SUCCESS,
            category=ExperienceCategory.STRATEGY,
            title="测试经验",
            description="这是一个测试经验",
        )

        assert exp.id
        assert exp.exp_type == ExperienceType.SUCCESS
        assert exp.category == ExperienceCategory.STRATEGY
        assert exp.title == "测试经验"
        assert exp.created_at > 0

    def test_experience_with_context(self, sample_experience: Experience) -> None:
        """测试带上下文的经验."""
        assert sample_experience.context.strategy_id == "trend_follower"
        assert sample_experience.context.symbol == "IF2401"
        assert sample_experience.context.market_state == "trending_up"

    def test_experience_with_outcome(self, sample_experience: Experience) -> None:
        """测试带结果的经验."""
        assert sample_experience.outcome.success
        assert sample_experience.outcome.pnl == 5000.0
        assert sample_experience.outcome.pnl_pct == 0.05
        assert sample_experience.outcome.impact == 8

    def test_to_dict(self, sample_experience: Experience) -> None:
        """测试转换为字典."""
        data = sample_experience.to_dict()

        assert data["id"] == sample_experience.id
        assert data["exp_type"] == "SUCCESS"
        assert data["category"] == "strategy"
        assert data["title"] == sample_experience.title
        assert "context" in data
        assert "outcome" in data

    def test_from_dict(self, sample_experience: Experience) -> None:
        """测试从字典创建."""
        data = sample_experience.to_dict()
        restored = Experience.from_dict(data)

        assert restored.id == sample_experience.id
        assert restored.exp_type == sample_experience.exp_type
        assert restored.category == sample_experience.category
        assert restored.context.symbol == sample_experience.context.symbol

    def test_to_knowledge_entry(self, sample_experience: Experience) -> None:
        """测试转换为知识条目."""
        entry = sample_experience.to_knowledge_entry()

        assert entry.knowledge_type == KnowledgeType.REFLEXION
        assert entry.content["id"] == sample_experience.id
        assert "SUCCESS" in entry.tags
        assert "strategy" in entry.tags


class TestReflexionStore:
    """反思记忆库测试."""

    def test_record_experience(
        self,
        reflexion_store: ReflexionStore,
        sample_experience: Experience,
    ) -> None:
        """测试记录经验."""
        exp_id = reflexion_store.record(sample_experience)
        assert exp_id

        retrieved = reflexion_store.get(exp_id)
        assert retrieved is not None
        assert retrieved.title == sample_experience.title

    def test_record_success(self, reflexion_store: ReflexionStore) -> None:
        """测试记录成功经验."""
        exp_id = reflexion_store.record_success(
            title="成功案例",
            description="描述",
            category=ExperienceCategory.EXECUTION,
            context=ExperienceContext(symbol="IF2401"),
            outcome=ExperienceOutcome(success=True, pnl=1000),
        )

        exp = reflexion_store.get(exp_id)
        assert exp is not None
        assert exp.exp_type == ExperienceType.SUCCESS

    def test_record_failure(self, reflexion_store: ReflexionStore) -> None:
        """测试记录失败经验."""
        exp_id = reflexion_store.record_failure(
            title="失败案例",
            description="描述",
            category=ExperienceCategory.RISK,
            outcome=ExperienceOutcome(success=False, pnl=-500),
            action_recommended="减少仓位",
        )

        exp = reflexion_store.get(exp_id)
        assert exp is not None
        assert exp.exp_type == ExperienceType.FAILURE
        assert exp.action_recommended == "减少仓位"

    def test_record_warning(self, reflexion_store: ReflexionStore) -> None:
        """测试记录警告."""
        exp_id = reflexion_store.record_warning(
            title="风险警告",
            description="高波动率环境",
            category=ExperienceCategory.MARKET,
            action_recommended="谨慎操作",
        )

        exp = reflexion_store.get(exp_id)
        assert exp is not None
        assert exp.exp_type == ExperienceType.WARNING

    def test_search_by_type(self, reflexion_store: ReflexionStore) -> None:
        """测试按类型搜索."""
        # 记录不同类型的经验
        reflexion_store.record_success(
            title="成功1",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_failure(
            title="失败1",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        successes = reflexion_store.search(exp_type=ExperienceType.SUCCESS)
        assert len(successes) >= 1
        assert all(e.exp_type == ExperienceType.SUCCESS for e in successes)

    def test_search_by_category(self, reflexion_store: ReflexionStore) -> None:
        """测试按分类搜索."""
        reflexion_store.record_success(
            title="策略经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_success(
            title="风控经验",
            description="描述",
            category=ExperienceCategory.RISK,
        )

        results = reflexion_store.search(category=ExperienceCategory.STRATEGY)
        assert len(results) >= 1

    def test_search_by_symbol(self, reflexion_store: ReflexionStore) -> None:
        """测试按标的搜索."""
        reflexion_store.record_success(
            title="IF2401经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(symbol="IF2401"),
        )

        results = reflexion_store.search(symbol="IF2401")
        assert len(results) >= 1
        assert results[0].context.symbol == "IF2401"

    def test_search_by_strategy(self, reflexion_store: ReflexionStore) -> None:
        """测试按策略搜索."""
        reflexion_store.record_success(
            title="趋势策略经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(strategy_id="trend_follower"),
        )

        results = reflexion_store.search(strategy_id="trend_follower")
        assert len(results) >= 1

    def test_search_success_only(self, reflexion_store: ReflexionStore) -> None:
        """测试只搜索成功经验."""
        reflexion_store.record_success(
            title="成功",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_failure(
            title="失败",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        results = reflexion_store.search(success_only=True)
        assert all(e.exp_type == ExperienceType.SUCCESS for e in results)

    def test_search_failure_only(self, reflexion_store: ReflexionStore) -> None:
        """测试只搜索失败经验."""
        reflexion_store.record_success(
            title="成功",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_failure(
            title="失败",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        results = reflexion_store.search(failure_only=True)
        assert all(e.exp_type == ExperienceType.FAILURE for e in results)

    def test_find_similar(self, reflexion_store: ReflexionStore) -> None:
        """测试查找相似经验."""
        # 记录一些经验
        reflexion_store.record_success(
            title="IF2401趋势经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(
                symbol="IF2401",
                strategy_id="trend_follower",
                market_state="trending_up",
            ),
        )

        # 查找相似经验
        similar_context = ExperienceContext(
            symbol="IF2401",
            strategy_id="trend_follower",
        )
        similar = reflexion_store.find_similar(similar_context)
        assert len(similar) >= 1

    def test_get_lessons(self, reflexion_store: ReflexionStore) -> None:
        """测试获取教训."""
        reflexion_store.record_failure(
            title="失败案例",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            outcome=ExperienceOutcome(
                success=False,
                lessons=["教训1", "教训2"],
            ),
            action_recommended="建议行动",
        )

        lessons = reflexion_store.get_lessons()
        assert len(lessons) >= 1
        assert "教训1" in lessons or "教训2" in lessons or "[建议]" in lessons[0]

    def test_get_best_practices(self, reflexion_store: ReflexionStore) -> None:
        """测试获取最佳实践."""
        reflexion_store.record_success(
            title="高置信度成功",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            confidence=0.9,
        )
        reflexion_store.record_success(
            title="低置信度成功",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            confidence=0.5,
        )

        practices = reflexion_store.get_best_practices(min_confidence=0.8)
        assert all(p.confidence >= 0.8 for p in practices)

    def test_mark_reused(self, reflexion_store: ReflexionStore) -> None:
        """测试标记复用."""
        exp_id = reflexion_store.record_success(
            title="经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        success = reflexion_store.mark_reused(exp_id)
        assert success

        exp = reflexion_store.get(exp_id)
        assert exp is not None
        assert exp.reuse_count == 1

    def test_get_stats(self, reflexion_store: ReflexionStore) -> None:
        """测试统计信息."""
        reflexion_store.record_success(
            title="成功",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_failure(
            title="失败",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        stats = reflexion_store.get_stats()
        assert stats["total_experiences"] >= 2
        assert stats["success_count"] >= 1
        assert stats["failure_count"] >= 1


class TestCreateReflexionFromDecision:
    """从决策创建反思测试."""

    def test_create_from_decision(self) -> None:
        """测试从决策事件创建."""
        decision_event = {
            "ts": time.time(),
            "run_id": "run-123",
            "exec_id": "exec-456",
            "strategy_id": "trend_follower",
            "feature_hash": "abc123",
            "confidence": 0.8,
            "signals": {"momentum": 0.5},
        }

        outcome = ExperienceOutcome(
            success=True,
            pnl=5000,
            pnl_pct=0.05,
        )

        exp = create_reflexion_from_decision(
            decision_event=decision_event,
            outcome=outcome,
            exp_type=ExperienceType.SUCCESS,
        )

        assert exp.exp_type == ExperienceType.SUCCESS
        assert exp.category == ExperienceCategory.STRATEGY
        assert exp.context.strategy_id == "trend_follower"
        assert exp.run_id == "run-123"
        assert exp.confidence == 0.8
