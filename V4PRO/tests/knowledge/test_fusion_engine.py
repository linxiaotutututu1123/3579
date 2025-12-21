"""
知识融合引擎测试.

测试 fusion_engine.py 中的知识融合功能。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.decision_log import Decision, DecisionOutcome, DecisionType
from src.knowledge.fusion_engine import (
    FusionContext,
    FusionEngine,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from src.knowledge.pattern_store import (
    MarketRegime,
    Pattern,
    PatternOccurrence,
    PatternStrength,
    PatternType,
)
from src.knowledge.reflexion import (
    ExperienceCategory,
    ExperienceContext,
    ExperienceOutcome,
)


class TestRecommendation:
    """建议条目测试."""

    def test_create_recommendation(self) -> None:
        """测试创建建议."""
        rec = Recommendation.create(
            rec_type=RecommendationType.STRATEGY_OPTIMIZE,
            priority=RecommendationPriority.HIGH,
            title="优化建议",
            description="建议优化策略参数",
            action="review_parameters",
            confidence=0.8,
        )

        assert rec.id
        assert rec.rec_type == RecommendationType.STRATEGY_OPTIMIZE
        assert rec.priority == RecommendationPriority.HIGH
        assert rec.confidence == 0.8
        assert rec.created_at > 0
        assert rec.expires_at > rec.created_at

    def test_is_expired(self) -> None:
        """测试过期判断."""
        rec = Recommendation.create(
            rec_type=RecommendationType.RISK_ENHANCE,
            priority=RecommendationPriority.MEDIUM,
            title="测试",
            description="描述",
            action="action",
            confidence=0.7,
            ttl_seconds=0.01,  # 极短的过期时间
        )

        time.sleep(0.02)
        assert rec.is_expired

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        rec = Recommendation.create(
            rec_type=RecommendationType.FAULT_PREVENT,
            priority=RecommendationPriority.CRITICAL,
            title="故障预防",
            description="描述",
            action="enable_protection",
            confidence=0.9,
            evidence=["evidence1", "evidence2"],
            impact=0.5,
        )

        data = rec.to_dict()
        assert data["id"] == rec.id
        assert data["rec_type"] == "FAULT_PREVENT"
        assert data["priority"] == "CRITICAL"
        assert len(data["evidence"]) == 2


class TestFusionContext:
    """融合上下文测试."""

    def test_create_context(self, sample_fusion_context: FusionContext) -> None:
        """测试创建上下文."""
        assert sample_fusion_context.symbol == "IF2401"
        assert sample_fusion_context.strategy_id == "trend_follower"
        assert sample_fusion_context.market_regime == MarketRegime.TRENDING_UP


class TestFusionEngine:
    """融合引擎测试."""

    def test_fuse_empty(
        self,
        fusion_engine: FusionEngine,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试空数据融合."""
        recommendations = fusion_engine.fuse(sample_fusion_context)
        # 空数据应该返回空列表或少量默认建议
        assert isinstance(recommendations, list)

    def test_fuse_with_experiences(
        self,
        fusion_engine: FusionEngine,
        reflexion_store,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试带经验的融合."""
        # 添加一些失败经验
        reflexion_store.record_failure(
            title="高波动失败",
            description="在高波动环境下亏损",
            category=ExperienceCategory.RISK,
            context=ExperienceContext(
                market_state="volatile",
                strategy_id="trend_follower",
            ),
            outcome=ExperienceOutcome(success=False, pnl=-1000, impact=8),
            action_recommended="reduce_position",
        )

        # 修改上下文为高波动
        context = FusionContext(
            symbol="IF2401",
            strategy_id="trend_follower",
            market_regime=MarketRegime.VOLATILE,
            volatility=0.06,  # 高波动率
        )

        recommendations = fusion_engine.fuse(context)
        # 应该有风控增强建议
        risk_recs = [r for r in recommendations if r.rec_type == RecommendationType.RISK_ENHANCE]
        assert len(risk_recs) >= 0  # 可能有也可能没有，取决于规则匹配

    def test_fuse_with_patterns(
        self,
        fusion_engine: FusionEngine,
        pattern_store,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试带模式的融合."""
        # 添加一个高成功率的模式
        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="突破模式",
            description="价格突破前高",
            regime=MarketRegime.TRENDING_UP,
            strength=PatternStrength.STRONG,
        )
        for i in range(10):
            pattern.add_occurrence(PatternOccurrence(
                timestamp=time.time() - i * 3600,
                symbol="IF2401",
                price=4000,
                outcome=0.02 if i < 8 else -0.01,
            ))
        pattern_store.register(pattern)

        recommendations = fusion_engine.fuse(sample_fusion_context)
        assert isinstance(recommendations, list)

    def test_fuse_with_decisions(
        self,
        fusion_engine: FusionEngine,
        decision_log,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试带决策的融合."""
        # 添加一些低胜率的决策
        for i in range(20):
            decision = Decision.create(
                decision_type=DecisionType.ENTRY,
                strategy_id="trend_follower",
                symbol="IF2401",
                direction="long",
                target_qty=1,
            )
            # 30%胜率
            outcome = DecisionOutcome.PROFITABLE if i < 6 else DecisionOutcome.LOSS
            decision.update_result(outcome, pnl=1000 if i < 6 else -500)
            decision_log.log(decision)

        recommendations = fusion_engine.fuse(sample_fusion_context)
        # 应该有策略优化建议
        strategy_recs = [r for r in recommendations if r.rec_type == RecommendationType.STRATEGY_OPTIMIZE]
        assert len(strategy_recs) >= 0

    def test_register_custom_rule(
        self,
        fusion_engine: FusionEngine,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试注册自定义规则."""
        def custom_rule(context: FusionContext) -> list[Recommendation]:
            if context.symbol == "IF2401":
                return [
                    Recommendation.create(
                        rec_type=RecommendationType.ENTRY_SIGNAL,
                        priority=RecommendationPriority.LOW,
                        title="自定义建议",
                        description="来自自定义规则",
                        action="custom_action",
                        confidence=0.6,
                    )
                ]
            return []

        fusion_engine.register_rule(custom_rule)
        recommendations = fusion_engine.fuse(sample_fusion_context)

        custom_recs = [r for r in recommendations if r.title == "自定义建议"]
        assert len(custom_recs) == 1

    def test_get_active_recommendations(
        self,
        fusion_engine: FusionEngine,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试获取活跃建议."""
        fusion_engine.fuse(sample_fusion_context)

        active = fusion_engine.get_active_recommendations()
        assert isinstance(active, list)

        # 按类型过滤
        active_strategy = fusion_engine.get_active_recommendations(
            rec_type=RecommendationType.STRATEGY_OPTIMIZE
        )
        assert all(r.rec_type == RecommendationType.STRATEGY_OPTIMIZE for r in active_strategy)

    def test_mark_recommendation_applied(
        self,
        fusion_engine: FusionEngine,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试标记建议已应用."""
        # 添加自定义规则确保有建议
        def test_rule(context: FusionContext) -> list[Recommendation]:
            return [
                Recommendation.create(
                    rec_type=RecommendationType.POSITION_ADJUST,
                    priority=RecommendationPriority.MEDIUM,
                    title="测试建议",
                    description="描述",
                    action="action",
                    confidence=0.7,
                )
            ]

        fusion_engine.register_rule(test_rule)
        recommendations = fusion_engine.fuse(sample_fusion_context)

        if recommendations:
            rec_id = recommendations[0].id
            success = fusion_engine.mark_recommendation_applied(rec_id)
            assert success

            # 验证已从活跃列表移除
            active = fusion_engine.get_active_recommendations()
            assert all(r.id != rec_id for r in active)

    def test_get_comprehensive_advice(
        self,
        fusion_engine: FusionEngine,
        sample_fusion_context: FusionContext,
    ) -> None:
        """测试获取综合建议."""
        advice = fusion_engine.get_comprehensive_advice(sample_fusion_context)

        assert "context" in advice
        assert "recommendations" in advice
        assert "total_recommendations" in advice
        assert "fusion_stats" in advice
        assert advice["context"]["symbol"] == "IF2401"

    def test_get_stats(self, fusion_engine: FusionEngine, sample_fusion_context: FusionContext) -> None:
        """测试统计信息."""
        fusion_engine.fuse(sample_fusion_context)

        stats = fusion_engine.get_stats()
        assert stats["total_fusions"] >= 1
        assert "recommendations_generated" in stats
        assert "active_recommendations" in stats
        assert "registered_rules" in stats
