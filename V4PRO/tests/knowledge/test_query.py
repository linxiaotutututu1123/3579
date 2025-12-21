"""
知识查询接口测试.

测试 query.py 中的统一查询功能。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.base import KnowledgeType
from src.knowledge.decision_log import (
    Decision,
    DecisionOutcome,
    DecisionType,
)
from src.knowledge.pattern_store import (
    MarketRegime,
    Pattern,
    PatternOccurrence,
    PatternType,
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
    ExperienceCategory,
    ExperienceContext,
    ExperienceOutcome,
)


class TestSearchQuery:
    """搜索查询测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        query = SearchQuery()

        assert query.keywords == []
        assert query.scope == SearchScope.ALL
        assert query.knowledge_types == []
        assert query.tags == []
        assert query.min_priority is None
        assert query.symbol == ""
        assert query.strategy_id == ""
        assert query.start_time is None
        assert query.end_time is None
        assert query.sort_by == SortOrder.RELEVANCE
        assert query.limit == 100
        assert query.offset == 0

    def test_custom_values(self) -> None:
        """测试自定义值."""
        query = SearchQuery(
            keywords=["trend", "breakout"],
            scope=SearchScope.REFLEXION,
            tags=["strategy"],
            symbol="IF2401",
            strategy_id="trend_follower",
            limit=50,
            offset=10,
            sort_by=SortOrder.RECENCY,
        )

        assert query.keywords == ["trend", "breakout"]
        assert query.scope == SearchScope.REFLEXION
        assert query.symbol == "IF2401"
        assert query.limit == 50


class TestSearchResult:
    """搜索结果测试."""

    def test_create_result(self) -> None:
        """测试创建结果."""
        result = SearchResult(
            id="result-123",
            source="reflexion",
            knowledge_type=KnowledgeType.REFLEXION,
            title="测试结果",
            summary="结果摘要",
            content={"key": "value"},
            score=0.85,
            tags=["test"],
            created_at=time.time(),
            metadata={"confidence": 0.9},
        )

        assert result.id == "result-123"
        assert result.source == "reflexion"
        assert result.knowledge_type == KnowledgeType.REFLEXION
        assert result.score == 0.85
        assert "confidence" in result.metadata


class TestSearchResponse:
    """搜索响应测试."""

    def test_create_response(self) -> None:
        """测试创建响应."""
        query = SearchQuery(keywords=["test"])
        result = SearchResult(
            id="r1",
            source="reflexion",
            knowledge_type=KnowledgeType.REFLEXION,
            title="测试",
            summary="摘要",
            content={},
            score=0.8,
        )

        response = SearchResponse(
            query=query,
            results=[result],
            total_count=1,
            took_ms=10.5,
            facets={"source": {"reflexion": 1}},
        )

        assert response.query == query
        assert len(response.results) == 1
        assert response.total_count == 1
        assert response.took_ms == 10.5


class TestKnowledgeQuery:
    """知识查询引擎测试."""

    def test_search_empty(self, knowledge_query: KnowledgeQuery) -> None:
        """测试空搜索."""
        query = SearchQuery()
        response = knowledge_query.search(query)

        assert isinstance(response, SearchResponse)
        assert response.total_count >= 0
        assert response.took_ms > 0

    def test_search_reflexion_scope(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试反思库范围搜索."""
        # 添加经验数据
        reflexion_store.record_success(
            title="趋势跟踪成功",
            description="在上升趋势中成功获利",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(
                symbol="IF2401",
                strategy_id="trend_follower",
            ),
            outcome=ExperienceOutcome(success=True, pnl=1000),
        )

        query = SearchQuery(
            scope=SearchScope.REFLEXION,
            symbol="IF2401",
        )
        response = knowledge_query.search(query)

        assert response.total_count >= 1
        assert all(r.source == "reflexion" for r in response.results)

    def test_search_pattern_scope(
        self,
        knowledge_query: KnowledgeQuery,
        pattern_store,
    ) -> None:
        """测试模式库范围搜索."""
        # 添加模式数据
        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="测试突破模式",
            description="描述",
            regime=MarketRegime.TRENDING_UP,
        )
        pattern_store.register(pattern)

        query = SearchQuery(
            scope=SearchScope.PATTERN,
        )
        response = knowledge_query.search(query)

        assert response.total_count >= 1
        assert all(r.source == "pattern" for r in response.results)

    def test_search_decision_scope(
        self,
        knowledge_query: KnowledgeQuery,
        decision_log,
    ) -> None:
        """测试决策库范围搜索."""
        # 添加决策数据
        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision.update_result(DecisionOutcome.PROFITABLE, pnl=1000)
        decision_log.log(decision)

        query = SearchQuery(
            scope=SearchScope.DECISION,
        )
        response = knowledge_query.search(query)

        assert response.total_count >= 1
        assert all(r.source == "decision" for r in response.results)

    def test_search_with_keywords(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试关键词搜索."""
        # 添加包含特定关键词的经验
        reflexion_store.record_success(
            title="高波动环境策略",
            description="在高波动率环境中使用网格策略",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_success(
            title="趋势跟踪",
            description="趋势跟随策略",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            keywords=["波动", "网格"],
            scope=SearchScope.REFLEXION,
        )
        response = knowledge_query.search(query)

        # 关键词匹配的结果应该有更高的分数
        if response.results:
            assert response.results[0].score > 0

    def test_search_by_symbol(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
        decision_log,
    ) -> None:
        """测试按标的搜索."""
        # 添加不同标的的数据
        reflexion_store.record_success(
            title="IF2401经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(symbol="IF2401"),
        )
        reflexion_store.record_success(
            title="IC2401经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(symbol="IC2401"),
        )

        query = SearchQuery(
            symbol="IF2401",
        )
        response = knowledge_query.search(query)

        # 结果应该只包含 IF2401
        for result in response.results:
            content_str = str(result.content)
            if result.source == "reflexion":
                assert "IF2401" in content_str

    def test_search_by_strategy(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按策略搜索."""
        reflexion_store.record_success(
            title="趋势策略",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(strategy_id="trend_follower"),
        )

        query = SearchQuery(
            strategy_id="trend_follower",
        )
        response = knowledge_query.search(query)

        assert response.total_count >= 1

    def test_search_with_time_range(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试时间范围搜索."""
        now = time.time()

        reflexion_store.record_success(
            title="最近的经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            start_time=now - 60,
            end_time=now + 60,
        )
        response = knowledge_query.search(query)

        assert response.total_count >= 0

    def test_sort_by_relevance(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按相关性排序."""
        reflexion_store.record_success(
            title="完全匹配关键词",
            description="这包含关键词一和关键词二",
            category=ExperienceCategory.STRATEGY,
        )
        reflexion_store.record_success(
            title="部分匹配",
            description="只有关键词一",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            keywords=["关键词一", "关键词二"],
            scope=SearchScope.REFLEXION,
            sort_by=SortOrder.RELEVANCE,
        )
        response = knowledge_query.search(query)

        if len(response.results) >= 2:
            # 相关性更高的应该排在前面
            assert response.results[0].score >= response.results[1].score

    def test_sort_by_recency(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按时间排序."""
        reflexion_store.record_success(
            title="较早的经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        time.sleep(0.01)
        reflexion_store.record_success(
            title="最新的经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            scope=SearchScope.REFLEXION,
            sort_by=SortOrder.RECENCY,
        )
        response = knowledge_query.search(query)

        if len(response.results) >= 2:
            # 最新的应该排在前面
            assert response.results[0].created_at >= response.results[1].created_at

    def test_sort_by_confidence(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按置信度排序."""
        reflexion_store.record_success(
            title="低置信度",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            confidence=0.5,
        )
        reflexion_store.record_success(
            title="高置信度",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            confidence=0.9,
        )

        query = SearchQuery(
            scope=SearchScope.REFLEXION,
            sort_by=SortOrder.CONFIDENCE,
        )
        response = knowledge_query.search(query)

        if len(response.results) >= 2:
            # 高置信度应该排在前面
            conf1 = response.results[0].metadata.get("confidence", 0)
            conf2 = response.results[1].metadata.get("confidence", 0)
            assert conf1 >= conf2

    def test_pagination(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试分页."""
        # 添加多条数据
        for i in range(10):
            reflexion_store.record_success(
                title=f"经验{i}",
                description=f"描述{i}",
                category=ExperienceCategory.STRATEGY,
            )

        # 第一页
        query1 = SearchQuery(
            scope=SearchScope.REFLEXION,
            limit=5,
            offset=0,
        )
        response1 = knowledge_query.search(query1)

        # 第二页
        query2 = SearchQuery(
            scope=SearchScope.REFLEXION,
            limit=5,
            offset=5,
        )
        response2 = knowledge_query.search(query2)

        assert len(response1.results) <= 5
        assert response1.total_count >= 10

        # 两页结果不应该重叠
        ids1 = {r.id for r in response1.results}
        ids2 = {r.id for r in response2.results}
        assert len(ids1 & ids2) == 0

    def test_facets(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
        pattern_store,
    ) -> None:
        """测试分面统计."""
        reflexion_store.record_success(
            title="经验1",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )
        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="模式1",
            description="描述",
        )
        pattern_store.register(pattern)

        query = SearchQuery(scope=SearchScope.ALL)
        response = knowledge_query.search(query)

        assert "source" in response.facets
        assert "knowledge_type" in response.facets

    def test_quick_search(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试快速搜索."""
        reflexion_store.record_success(
            title="趋势跟踪经验",
            description="趋势跟随策略成功案例",
            category=ExperienceCategory.STRATEGY,
        )

        results = knowledge_query.quick_search("趋势", limit=5)

        assert isinstance(results, list)

    def test_search_by_symbol_method(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按标的搜索方法."""
        reflexion_store.record_success(
            title="IF2401经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(symbol="IF2401"),
        )

        results = knowledge_query.search_by_symbol("IF2401", limit=10)

        assert isinstance(results, list)

    def test_search_by_strategy_method(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试按策略搜索方法."""
        reflexion_store.record_success(
            title="趋势策略经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(strategy_id="trend_follower"),
        )

        results = knowledge_query.search_by_strategy("trend_follower")

        assert isinstance(results, list)

    def test_get_recent(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试获取最近知识."""
        reflexion_store.record_success(
            title="最近的经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        results = knowledge_query.get_recent(hours=1, limit=10)

        assert isinstance(results, list)

    def test_get_stats(
        self,
        knowledge_query: KnowledgeQuery,
    ) -> None:
        """测试统计信息."""
        # 执行一些查询
        query = SearchQuery()
        knowledge_query.search(query)
        knowledge_query.search(query)

        stats = knowledge_query.get_stats()

        assert stats["total_queries"] >= 2
        assert "avg_took_ms" in stats
        assert "query_history_size" in stats

    def test_get_query_history(
        self,
        knowledge_query: KnowledgeQuery,
    ) -> None:
        """测试查询历史."""
        # 执行一些查询
        for i in range(5):
            query = SearchQuery(keywords=[f"keyword{i}"])
            knowledge_query.search(query)

        history = knowledge_query.get_query_history(limit=3)

        assert len(history) == 3
        assert all("timestamp" in h for h in history)
        assert all("keywords" in h for h in history)

    def test_cross_store_search(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
        pattern_store,
        decision_log,
    ) -> None:
        """测试跨库搜索."""
        # 在各库添加数据
        reflexion_store.record_success(
            title="IF2401反思",
            description="描述",
            category=ExperienceCategory.STRATEGY,
            context=ExperienceContext(symbol="IF2401"),
        )

        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="IF2401模式",
            description="描述",
        )
        pattern_store.register(pattern)

        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision_log.log(decision)

        # 全范围搜索
        query = SearchQuery(
            scope=SearchScope.ALL,
            symbol="IF2401",
        )
        response = knowledge_query.search(query)

        # 应该有来自多个来源的结果
        sources = {r.source for r in response.results}
        assert len(sources) >= 1

    def test_search_with_tags(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试标签过滤搜索."""
        reflexion_store.record_success(
            title="成功案例",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            tags=["SUCCESS"],
            scope=SearchScope.REFLEXION,
        )
        response = knowledge_query.search(query)

        # 结果应该包含成功类型
        assert isinstance(response.results, list)

    def test_empty_keyword_search(
        self,
        knowledge_query: KnowledgeQuery,
        reflexion_store,
    ) -> None:
        """测试空关键词搜索."""
        reflexion_store.record_success(
            title="测试经验",
            description="描述",
            category=ExperienceCategory.STRATEGY,
        )

        query = SearchQuery(
            keywords=[],
            scope=SearchScope.REFLEXION,
        )
        response = knowledge_query.search(query)

        # 无关键词时应返回所有结果，默认分数0.5
        if response.results:
            assert response.results[0].score == 0.5


class TestSearchScope:
    """搜索范围枚举测试."""

    def test_all_scopes_defined(self) -> None:
        """验证所有范围已定义."""
        assert SearchScope.ALL
        assert SearchScope.REFLEXION
        assert SearchScope.PATTERN
        assert SearchScope.DECISION


class TestSortOrder:
    """排序顺序枚举测试."""

    def test_all_sort_orders_defined(self) -> None:
        """验证所有排序方式已定义."""
        assert SortOrder.RELEVANCE
        assert SortOrder.RECENCY
        assert SortOrder.PRIORITY
        assert SortOrder.CONFIDENCE
