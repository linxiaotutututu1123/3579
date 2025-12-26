"""
知识查询接口 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

知识查询功能:
- 统一查询接口
- 跨库联合查询
- 语义搜索
- 相关性排序

军规覆盖:
- M33: 知识沉淀机制
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, TypeVar

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
    QueryContext,
)
from src.knowledge.decision_log import Decision, DecisionLog, DecisionType
from src.knowledge.pattern_store import MarketRegime, Pattern, PatternStore, PatternType
from src.knowledge.reflexion import (
    Experience,
    ExperienceCategory,
    ExperienceType,
    ReflexionStore,
)


class SearchScope(Enum):
    """搜索范围.

    - ALL: 所有知识库
    - REFLEXION: 仅反思库
    - PATTERN: 仅模式库
    - DECISION: 仅决策库
    """

    ALL = auto()
    REFLEXION = auto()
    PATTERN = auto()
    DECISION = auto()


class SortOrder(Enum):
    """排序顺序.

    - RELEVANCE: 按相关性
    - RECENCY: 按时间
    - PRIORITY: 按优先级
    - CONFIDENCE: 按置信度
    """

    RELEVANCE = auto()
    RECENCY = auto()
    PRIORITY = auto()
    CONFIDENCE = auto()


@dataclass
class SearchQuery:
    """搜索查询.

    Attributes:
        keywords: 关键词列表
        scope: 搜索范围
        knowledge_types: 知识类型过滤
        tags: 标签过滤
        min_priority: 最低优先级
        symbol: 标的过滤
        strategy_id: 策略过滤
        start_time: 开始时间
        end_time: 结束时间
        sort_by: 排序方式
        limit: 返回数量限制
        offset: 偏移量
    """

    keywords: list[str] = field(default_factory=list)
    scope: SearchScope = SearchScope.ALL
    knowledge_types: list[KnowledgeType] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    min_priority: KnowledgePriority | None = None
    symbol: str = ""
    strategy_id: str = ""
    start_time: float | None = None
    end_time: float | None = None
    sort_by: SortOrder = SortOrder.RELEVANCE
    limit: int = 100
    offset: int = 0


@dataclass
class SearchResult:
    """搜索结果.

    Attributes:
        id: 结果ID
        source: 来源 (reflexion/pattern/decision)
        knowledge_type: 知识类型
        title: 标题
        summary: 摘要
        content: 原始内容
        score: 相关性分数
        tags: 标签
        created_at: 创建时间
        metadata: 元数据
    """

    id: str
    source: str
    knowledge_type: KnowledgeType
    title: str
    summary: str
    content: dict[str, Any]
    score: float
    tags: list[str] = field(default_factory=list)
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """搜索响应.

    Attributes:
        query: 原始查询
        results: 结果列表
        total_count: 总结果数
        took_ms: 耗时 (毫秒)
        facets: 分面统计
    """

    query: SearchQuery
    results: list[SearchResult]
    total_count: int
    took_ms: float
    facets: dict[str, dict[str, int]] = field(default_factory=dict)


class KnowledgeQuery:
    """知识查询引擎.

    提供统一的知识查询接口，支持跨库联合查询。

    功能特性:
    - 统一查询接口
    - 关键词搜索
    - 跨库联合查询
    - 相关性排序
    - 分面统计

    军规要求:
    - M33: 知识沉淀 - 支持知识检索
    - M3: 审计完整 - 记录查询日志
    - M7: 回放支持 - 支持历史查询
    """

    def __init__(
        self,
        reflexion_store: ReflexionStore | None = None,
        pattern_store: PatternStore | None = None,
        decision_log: DecisionLog | None = None,
        base_storage: KnowledgeStore[KnowledgeEntry] | None = None,
    ) -> None:
        """初始化查询引擎.

        Args:
            reflexion_store: 反思记忆库
            pattern_store: 模式存储
            decision_log: 决策日志
            base_storage: 基础存储 (可选)
        """
        self.reflexion = reflexion_store
        self.patterns = pattern_store
        self.decisions = decision_log
        self.base_storage = base_storage

        self._query_history: list[dict[str, Any]] = []
        self._stats = {
            "total_queries": 0,
            "avg_took_ms": 0.0,
            "cache_hits": 0,
        }

    def search(self, query: SearchQuery) -> SearchResponse:
        """执行搜索查询.

        Args:
            query: 搜索查询

        Returns:
            搜索响应
        """
        start_time = time.time()
        self._stats["total_queries"] += 1

        results: list[SearchResult] = []

        # 根据范围搜索不同知识库
        if query.scope in [SearchScope.ALL, SearchScope.REFLEXION]:
            if self.reflexion:
                results.extend(self._search_reflexion(query))

        if query.scope in [SearchScope.ALL, SearchScope.PATTERN]:
            if self.patterns:
                results.extend(self._search_patterns(query))

        if query.scope in [SearchScope.ALL, SearchScope.DECISION]:
            if self.decisions:
                results.extend(self._search_decisions(query))

        # 排序
        results = self._sort_results(results, query.sort_by)

        # 计算分面
        facets = self._compute_facets(results)

        # 分页
        total_count = len(results)
        results = results[query.offset : query.offset + query.limit]

        took_ms = (time.time() - start_time) * 1000

        # 更新统计
        self._update_stats(took_ms)

        # 记录查询历史
        self._record_query(query, total_count, took_ms)

        return SearchResponse(
            query=query,
            results=results,
            total_count=total_count,
            took_ms=took_ms,
            facets=facets,
        )

    def _search_reflexion(self, query: SearchQuery) -> list[SearchResult]:
        """搜索反思库.

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        if not self.reflexion:
            return []

        # 转换查询参数
        exp_type = None
        category = None

        # 从标签推断类型
        for tag in query.tags:
            try:
                exp_type = ExperienceType[tag.upper()]
            except KeyError:
                pass
            try:
                category = ExperienceCategory(tag.lower())
            except ValueError:
                pass

        # 执行搜索
        experiences = self.reflexion.search(
            exp_type=exp_type,
            category=category,
            symbol=query.symbol if query.symbol else None,
            strategy_id=query.strategy_id if query.strategy_id else None,
            limit=query.limit * 2,
        )

        # 转换为统一结果
        results: list[SearchResult] = []
        for exp in experiences:
            score = self._compute_relevance(exp.to_dict(), query.keywords)
            if score > 0 or not query.keywords:
                results.append(
                    SearchResult(
                        id=exp.id,
                        source="reflexion",
                        knowledge_type=KnowledgeType.REFLEXION,
                        title=exp.title,
                        summary=exp.description[:200],
                        content=exp.to_dict(),
                        score=score,
                        tags=exp.tags,
                        created_at=exp.created_at,
                        metadata={
                            "exp_type": exp.exp_type.name,
                            "category": exp.category.value,
                            "confidence": exp.confidence,
                        },
                    )
                )

        return results

    def _search_patterns(self, query: SearchQuery) -> list[SearchResult]:
        """搜索模式库.

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        if not self.patterns:
            return []

        # 转换查询参数
        pattern_type = None
        regime = None

        for tag in query.tags:
            try:
                pattern_type = PatternType[tag.upper()]
            except KeyError:
                pass
            try:
                regime = MarketRegime(tag.lower())
            except ValueError:
                pass

        # 执行搜索
        patterns = self.patterns.search(
            pattern_type=pattern_type,
            regime=regime,
            symbol=query.symbol if query.symbol else None,
            limit=query.limit * 2,
        )

        # 转换为统一结果
        results: list[SearchResult] = []
        for pattern in patterns:
            score = self._compute_relevance(pattern.to_dict(), query.keywords)
            if score > 0 or not query.keywords:
                results.append(
                    SearchResult(
                        id=pattern.id,
                        source="pattern",
                        knowledge_type=KnowledgeType.PATTERN,
                        title=pattern.name,
                        summary=pattern.description[:200],
                        content=pattern.to_dict(),
                        score=score,
                        tags=pattern.tags,
                        created_at=pattern.created_at,
                        metadata={
                            "pattern_type": pattern.pattern_type.name,
                            "regime": pattern.regime.value,
                            "success_rate": pattern.success_rate,
                        },
                    )
                )

        return results

    def _search_decisions(self, query: SearchQuery) -> list[SearchResult]:
        """搜索决策库.

        Args:
            query: 搜索查询

        Returns:
            搜索结果列表
        """
        if not self.decisions:
            return []

        # 转换查询参数
        decision_type = None

        for tag in query.tags:
            try:
                decision_type = DecisionType[tag.upper()]
            except KeyError:
                pass

        # 执行搜索
        decisions = self.decisions.search(
            decision_type=decision_type,
            symbol=query.symbol if query.symbol else None,
            strategy_id=query.strategy_id if query.strategy_id else None,
            start_time=query.start_time,
            end_time=query.end_time,
            limit=query.limit * 2,
        )

        # 转换为统一结果
        results: list[SearchResult] = []
        for decision in decisions:
            score = self._compute_relevance(decision.to_dict(), query.keywords)
            title = f"{decision.decision_type.name}: {decision.symbol} ({decision.direction})"
            if score > 0 or not query.keywords:
                results.append(
                    SearchResult(
                        id=decision.id,
                        source="decision",
                        knowledge_type=KnowledgeType.DECISION,
                        title=title,
                        summary=f"目标数量: {decision.target_qty}, 置信度: {decision.rationale.confidence:.1%}",
                        content=decision.to_dict(),
                        score=score,
                        tags=decision.tags,
                        created_at=decision.created_at,
                        metadata={
                            "decision_type": decision.decision_type.name,
                            "outcome": decision.result.outcome.value,
                            "pnl": decision.result.pnl,
                        },
                    )
                )

        return results

    def _compute_relevance(
        self,
        content: dict[str, Any],
        keywords: list[str],
    ) -> float:
        """计算内容与关键词的相关性分数.

        Args:
            content: 内容字典
            keywords: 关键词列表

        Returns:
            相关性分数 (0-1)
        """
        if not keywords:
            return 0.5  # 无关键词时返回默认分数

        # 将内容转换为文本
        text = str(content).lower()

        # 统计关键词匹配
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return matches / len(keywords)

    def _sort_results(
        self,
        results: list[SearchResult],
        sort_by: SortOrder,
    ) -> list[SearchResult]:
        """排序搜索结果.

        Args:
            results: 结果列表
            sort_by: 排序方式

        Returns:
            排序后的结果列表
        """
        if sort_by == SortOrder.RELEVANCE:
            results.sort(key=lambda r: r.score, reverse=True)
        elif sort_by == SortOrder.RECENCY:
            results.sort(key=lambda r: r.created_at, reverse=True)
        elif sort_by == SortOrder.PRIORITY:
            # 从元数据提取优先级相关信息
            def get_priority(r: SearchResult) -> float:
                if "confidence" in r.metadata:
                    return r.metadata["confidence"]
                if "success_rate" in r.metadata:
                    return r.metadata["success_rate"]
                return r.score
            results.sort(key=get_priority, reverse=True)
        elif sort_by == SortOrder.CONFIDENCE:
            def get_confidence(r: SearchResult) -> float:
                return r.metadata.get("confidence", r.score)
            results.sort(key=get_confidence, reverse=True)

        return results

    def _compute_facets(
        self,
        results: list[SearchResult],
    ) -> dict[str, dict[str, int]]:
        """计算分面统计.

        Args:
            results: 结果列表

        Returns:
            分面统计字典
        """
        facets: dict[str, dict[str, int]] = {
            "source": {},
            "knowledge_type": {},
            "tags": {},
        }

        for result in results:
            # 来源统计
            source = result.source
            facets["source"][source] = facets["source"].get(source, 0) + 1

            # 知识类型统计
            kt = result.knowledge_type.name
            facets["knowledge_type"][kt] = facets["knowledge_type"].get(kt, 0) + 1

            # 标签统计
            for tag in result.tags[:5]:  # 限制标签数量
                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1

        return facets

    def _update_stats(self, took_ms: float) -> None:
        """更新统计信息.

        Args:
            took_ms: 查询耗时
        """
        total = self._stats["total_queries"]
        avg = self._stats["avg_took_ms"]
        self._stats["avg_took_ms"] = (avg * (total - 1) + took_ms) / total

    def _record_query(
        self,
        query: SearchQuery,
        total_count: int,
        took_ms: float,
    ) -> None:
        """记录查询历史.

        Args:
            query: 查询
            total_count: 结果数量
            took_ms: 耗时
        """
        self._query_history.append({
            "timestamp": time.time(),
            "keywords": query.keywords,
            "scope": query.scope.name,
            "total_count": total_count,
            "took_ms": took_ms,
        })

        # 只保留最近1000条
        if len(self._query_history) > 1000:
            self._query_history = self._query_history[-1000:]

    def quick_search(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """快速搜索.

        简化的搜索接口。

        Args:
            keyword: 关键词
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        query = SearchQuery(
            keywords=[keyword] if keyword else [],
            limit=limit,
            sort_by=SortOrder.RELEVANCE,
        )
        response = self.search(query)
        return response.results

    def search_by_symbol(
        self,
        symbol: str,
        scope: SearchScope = SearchScope.ALL,
        limit: int = 50,
    ) -> list[SearchResult]:
        """按标的搜索.

        Args:
            symbol: 交易标的
            scope: 搜索范围
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        query = SearchQuery(
            symbol=symbol,
            scope=scope,
            limit=limit,
            sort_by=SortOrder.RECENCY,
        )
        response = self.search(query)
        return response.results

    def search_by_strategy(
        self,
        strategy_id: str,
        scope: SearchScope = SearchScope.ALL,
        limit: int = 50,
    ) -> list[SearchResult]:
        """按策略搜索.

        Args:
            strategy_id: 策略ID
            scope: 搜索范围
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        query = SearchQuery(
            strategy_id=strategy_id,
            scope=scope,
            limit=limit,
            sort_by=SortOrder.RECENCY,
        )
        response = self.search(query)
        return response.results

    def get_recent(
        self,
        scope: SearchScope = SearchScope.ALL,
        hours: int = 24,
        limit: int = 50,
    ) -> list[SearchResult]:
        """获取最近的知识.

        Args:
            scope: 搜索范围
            hours: 时间范围 (小时)
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        start_time = time.time() - hours * 3600
        query = SearchQuery(
            scope=scope,
            start_time=start_time,
            limit=limit,
            sort_by=SortOrder.RECENCY,
        )
        response = self.search(query)
        return response.results

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        return {
            **self._stats,
            "query_history_size": len(self._query_history),
        }

    def get_query_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取查询历史.

        Args:
            limit: 返回数量限制

        Returns:
            查询历史列表
        """
        return self._query_history[-limit:]
