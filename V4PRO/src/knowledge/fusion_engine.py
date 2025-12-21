"""
知识融合引擎 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

知识融合引擎功能:
- 策略优化建议
- 风控增强建议
- 故障预防建议
- 跨知识库融合

军规覆盖:
- M33: 知识沉淀机制
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
)
from src.knowledge.decision_log import Decision, DecisionLog, DecisionOutcome
from src.knowledge.pattern_store import MarketRegime, Pattern, PatternStore
from src.knowledge.reflexion import (
    Experience,
    ExperienceCategory,
    ExperienceContext,
    ExperienceType,
    ReflexionStore,
)


class RecommendationType(Enum):
    """建议类型枚举.

    - STRATEGY_OPTIMIZE: 策略优化
    - RISK_ENHANCE: 风控增强
    - FAULT_PREVENT: 故障预防
    - ENTRY_SIGNAL: 入场信号
    - EXIT_SIGNAL: 出场信号
    - POSITION_ADJUST: 仓位调整
    """

    STRATEGY_OPTIMIZE = auto()
    RISK_ENHANCE = auto()
    FAULT_PREVENT = auto()
    ENTRY_SIGNAL = auto()
    EXIT_SIGNAL = auto()
    POSITION_ADJUST = auto()


class RecommendationPriority(Enum):
    """建议优先级.

    - CRITICAL: 必须立即处理
    - HIGH: 高优先级
    - MEDIUM: 中优先级
    - LOW: 低优先级
    """

    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class Recommendation:
    """融合建议.

    知识融合引擎输出的建议。

    Attributes:
        id: 建议ID
        rec_type: 建议类型
        priority: 优先级
        title: 标题
        description: 描述
        action: 建议动作
        confidence: 置信度
        evidence: 证据来源
        impact: 影响程度
        expires_at: 过期时间
        created_at: 创建时间
        metadata: 元数据
    """

    id: str
    rec_type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    action: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    impact: float = 0.0
    expires_at: float = 0.0
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化时设置时间戳."""
        if not self.created_at:
            self.created_at = time.time()
        if not self.expires_at:
            # 默认1小时过期
            self.expires_at = self.created_at + 3600

    @property
    def is_expired(self) -> bool:
        """检查是否已过期."""
        return time.time() > self.expires_at

    @classmethod
    def create(
        cls,
        rec_type: RecommendationType,
        priority: RecommendationPriority,
        title: str,
        description: str,
        action: str,
        confidence: float,
        evidence: list[str] | None = None,
        impact: float = 0.0,
        ttl_seconds: float = 3600,
        metadata: dict[str, Any] | None = None,
    ) -> Recommendation:
        """创建新建议.

        Args:
            rec_type: 建议类型
            priority: 优先级
            title: 标题
            description: 描述
            action: 建议动作
            confidence: 置信度
            evidence: 证据来源
            impact: 影响程度
            ttl_seconds: 有效期
            metadata: 元数据

        Returns:
            Recommendation 实例
        """
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            rec_type=rec_type,
            priority=priority,
            title=title,
            description=description,
            action=action,
            confidence=confidence,
            evidence=evidence or [],
            impact=impact,
            expires_at=now + ttl_seconds,
            created_at=now,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "rec_type": self.rec_type.name,
            "priority": self.priority.name,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "impact": self.impact,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class FusionContext:
    """融合上下文.

    用于知识融合的当前环境信息。

    Attributes:
        symbol: 当前标的
        strategy_id: 当前策略
        market_regime: 市场状态
        position: 当前持仓
        portfolio_value: 组合价值
        volatility: 波动率
        session: 交易时段
        extra: 额外信息
    """

    symbol: str = ""
    strategy_id: str = ""
    market_regime: MarketRegime = MarketRegime.RANGING
    position: dict[str, int] = field(default_factory=dict)
    portfolio_value: float = 0.0
    volatility: float = 0.0
    session: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class FusionEngine:
    """知识融合引擎.

    融合经验库、模式库、决策库的知识，生成优化建议。

    功能特性:
    - 策略优化: 基于历史决策和经验优化策略参数
    - 风控增强: 基于失败经验和风险模式增强风控
    - 故障预防: 基于历史故障模式预防潜在问题

    军规要求:
    - M33: 知识沉淀 - 融合多源知识
    - M3: 审计完整 - 记录融合过程
    - M7: 回放支持 - 支持建议回放
    """

    def __init__(
        self,
        reflexion_store: ReflexionStore,
        pattern_store: PatternStore,
        decision_log: DecisionLog,
        storage: KnowledgeStore[KnowledgeEntry] | None = None,
    ) -> None:
        """初始化融合引擎.

        Args:
            reflexion_store: 反思记忆库
            pattern_store: 模式存储
            decision_log: 决策日志
            storage: 可选的融合结果存储
        """
        self.reflexion = reflexion_store
        self.patterns = pattern_store
        self.decisions = decision_log
        self.storage = storage

        self._active_recommendations: list[Recommendation] = []
        self._fusion_rules: list[Callable[[FusionContext], list[Recommendation]]] = []
        self._stats = {
            "total_fusions": 0,
            "recommendations_generated": 0,
            "recommendations_applied": 0,
        }

        # 注册默认融合规则
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """注册默认融合规则."""
        self._fusion_rules.extend([
            self._rule_strategy_optimization,
            self._rule_risk_enhancement,
            self._rule_fault_prevention,
            self._rule_pattern_signal,
            self._rule_market_regime_adaptation,
            self._rule_position_sizing,
            self._rule_correlation_warning,
        ])

    def register_rule(
        self,
        rule: Callable[[FusionContext], list[Recommendation]],
    ) -> None:
        """注册自定义融合规则.

        Args:
            rule: 融合规则函数
        """
        self._fusion_rules.append(rule)

    def fuse(self, context: FusionContext) -> list[Recommendation]:
        """执行知识融合.

        根据当前上下文融合多源知识，生成建议。

        Args:
            context: 融合上下文

        Returns:
            建议列表
        """
        self._stats["total_fusions"] += 1

        # 清理过期建议
        self._cleanup_expired()

        # 执行所有融合规则
        recommendations: list[Recommendation] = []
        for rule in self._fusion_rules:
            try:
                rule_recommendations = rule(context)
                recommendations.extend(rule_recommendations)
            except Exception:
                # 规则执行失败不影响其他规则
                continue

        # 按优先级排序
        recommendations.sort(key=lambda r: r.priority.value, reverse=True)

        # 缓存活跃建议
        self._active_recommendations = recommendations
        self._stats["recommendations_generated"] += len(recommendations)

        # 可选存储
        if self.storage:
            for rec in recommendations:
                self._store_recommendation(rec, context)

        return recommendations

    def _cleanup_expired(self) -> None:
        """清理过期建议."""
        self._active_recommendations = [
            r for r in self._active_recommendations if not r.is_expired
        ]

    def _store_recommendation(
        self,
        rec: Recommendation,
        context: FusionContext,
    ) -> str:
        """存储建议到知识库.

        Args:
            rec: 建议
            context: 上下文

        Returns:
            条目 ID
        """
        if not self.storage:
            return ""

        entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.STRATEGY,
            content={
                "recommendation": rec.to_dict(),
                "context": {
                    "symbol": context.symbol,
                    "strategy_id": context.strategy_id,
                    "market_regime": context.market_regime.value,
                },
            },
            priority=KnowledgePriority(rec.priority.value),
            tags=[rec.rec_type.name, context.symbol, context.strategy_id],
            source="fusion_engine",
        )
        return self.storage.put(entry)

    def _rule_strategy_optimization(
        self,
        context: FusionContext,
    ) -> list[Recommendation]:
        """策略优化规则.

        基于历史决策表现优化策略。

        Args:
            context: 融合上下文

        Returns:
            优化建议列表
        """
        recommendations: list[Recommendation] = []

        if not context.strategy_id:
            return recommendations

        # 获取策略分析
        analysis = self.decisions.analyze_strategy(context.strategy_id)
        win_rate = analysis.get("win_rate", 0)
        total_decisions = analysis.get("total_decisions", 0)

        if total_decisions < 10:
            return recommendations

        # 低胜率警告
        if win_rate < 0.4:
            rec = Recommendation.create(
                rec_type=RecommendationType.STRATEGY_OPTIMIZE,
                priority=RecommendationPriority.HIGH,
                title=f"策略 {context.strategy_id} 胜率过低",
                description=f"当前胜率 {win_rate:.1%}，建议检查策略参数",
                action="review_strategy_parameters",
                confidence=0.8,
                evidence=[f"Based on {total_decisions} historical decisions"],
                impact=0.3,
            )
            recommendations.append(rec)

        # 获取成功经验
        best_practices = self.reflexion.get_best_practices(
            category=ExperienceCategory.STRATEGY,
            min_confidence=0.8,
            limit=5,
        )

        for practice in best_practices:
            if practice.context.strategy_id == context.strategy_id:
                rec = Recommendation.create(
                    rec_type=RecommendationType.STRATEGY_OPTIMIZE,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"参考最佳实践: {practice.title}",
                    description=practice.description,
                    action=practice.action_taken,
                    confidence=practice.confidence,
                    evidence=[f"Experience ID: {practice.id}"],
                )
                recommendations.append(rec)

        return recommendations

    def _rule_risk_enhancement(
        self,
        context: FusionContext,
    ) -> list[Recommendation]:
        """风控增强规则.

        基于失败经验和风险模式增强风控。

        Args:
            context: 融合上下文

        Returns:
            风控建议列表
        """
        recommendations: list[Recommendation] = []

        # 查找相似的失败经验
        failures = self.reflexion.search(
            category=ExperienceCategory.RISK,
            failure_only=True,
            limit=10,
        )

        for failure in failures:
            # 检查是否与当前上下文相关
            if failure.context.market_state == context.market_regime.value:
                rec = Recommendation.create(
                    rec_type=RecommendationType.RISK_ENHANCE,
                    priority=RecommendationPriority.HIGH,
                    title=f"风险警告: {failure.title}",
                    description=failure.description,
                    action=failure.action_recommended or "reduce_position",
                    confidence=failure.confidence,
                    evidence=[f"Similar failure: {failure.id}"],
                    impact=failure.outcome.impact / 10.0,
                )
                recommendations.append(rec)

        # 检查高波动率环境
        if context.volatility > 0.05:  # 5%波动率阈值
            # 查找波动率相关模式
            volatile_patterns = self.patterns.get_by_regime(
                regime=MarketRegime.VOLATILE,
                min_success_rate=0.5,
                limit=5,
            )

            if volatile_patterns:
                rec = Recommendation.create(
                    rec_type=RecommendationType.RISK_ENHANCE,
                    priority=RecommendationPriority.HIGH,
                    title="高波动率风控建议",
                    description=f"当前波动率 {context.volatility:.1%}，建议降低仓位",
                    action="reduce_position_by_50pct",
                    confidence=0.85,
                    evidence=[f"Pattern: {p.name}" for p in volatile_patterns[:3]],
                    impact=0.5,
                )
                recommendations.append(rec)

        return recommendations

    def _rule_fault_prevention(
        self,
        context: FusionContext,
    ) -> list[Recommendation]:
        """故障预防规则.

        基于历史故障模式预防潜在问题。

        Args:
            context: 融合上下文

        Returns:
            故障预防建议列表
        """
        recommendations: list[Recommendation] = []

        # 查找系统类故障经验
        system_failures = self.reflexion.search(
            category=ExperienceCategory.SYSTEM,
            failure_only=True,
            limit=10,
        )

        for failure in system_failures:
            # 检查是否在相同时段
            if failure.context.session == context.session:
                rec = Recommendation.create(
                    rec_type=RecommendationType.FAULT_PREVENT,
                    priority=RecommendationPriority.CRITICAL,
                    title=f"故障预防: {failure.title}",
                    description=failure.description,
                    action=failure.action_recommended or "enable_circuit_breaker",
                    confidence=failure.confidence,
                    evidence=[f"Historical failure: {failure.id}"],
                    impact=failure.outcome.impact / 10.0,
                    ttl_seconds=1800,  # 30分钟有效期
                )
                recommendations.append(rec)

        return recommendations

    def _rule_pattern_signal(
        self,
        context: FusionContext,
    ) -> list[Recommendation]:
        """模式信号规则.

        基于市场模式生成交易信号建议。

        Args:
            context: 融合上下文

        Returns:
            信号建议列表
        """
        recommendations: list[Recommendation] = []

        # 获取当前市场状态下的有效模式
        active_patterns = self.patterns.get_by_regime(
            regime=context.market_regime,
            min_success_rate=0.6,
            limit=5,
        )

        for pattern in active_patterns:
            # 根据模式类型确定建议类型
            from src.knowledge.pattern_store import PatternType

            if pattern.pattern_type in [PatternType.REVERSAL, PatternType.BREAKOUT]:
                rec_type = RecommendationType.ENTRY_SIGNAL
                action = "consider_entry"
            elif pattern.pattern_type == PatternType.TREND:
                rec_type = RecommendationType.POSITION_ADJUST
                action = "trend_following"
            else:
                continue

            rec = Recommendation.create(
                rec_type=rec_type,
                priority=RecommendationPriority.MEDIUM,
                title=f"模式信号: {pattern.name}",
                description=pattern.description,
                action=action,
                confidence=pattern.success_rate,
                evidence=[
                    f"Pattern: {pattern.id}",
                    f"Success rate: {pattern.success_rate:.1%}",
                    f"Avg return: {pattern.avg_return:.2%}",
                ],
                impact=abs(pattern.avg_return),
                metadata={
                    "pattern_type": pattern.pattern_type.name,
                    "strength": pattern.strength.name,
                },
            )
            recommendations.append(rec)

        return recommendations

    def get_active_recommendations(
        self,
        rec_type: RecommendationType | None = None,
        min_priority: RecommendationPriority | None = None,
        min_confidence: float = 0.0,
    ) -> list[Recommendation]:
        """获取活跃建议.

        Args:
            rec_type: 建议类型过滤
            min_priority: 最低优先级
            min_confidence: 最低置信度

        Returns:
            活跃建议列表
        """
        self._cleanup_expired()

        results = self._active_recommendations
        if rec_type:
            results = [r for r in results if r.rec_type == rec_type]
        if min_priority:
            results = [r for r in results if r.priority.value >= min_priority.value]
        if min_confidence > 0:
            results = [r for r in results if r.confidence >= min_confidence]

        return results

    def mark_recommendation_applied(self, rec_id: str) -> bool:
        """标记建议已应用.

        Args:
            rec_id: 建议 ID

        Returns:
            是否成功
        """
        for rec in self._active_recommendations:
            if rec.id == rec_id:
                self._stats["recommendations_applied"] += 1
                self._active_recommendations.remove(rec)
                return True
        return False

    def get_comprehensive_advice(
        self,
        context: FusionContext,
        top_n: int = 5,
    ) -> dict[str, Any]:
        """获取综合建议.

        融合所有知识源，生成综合建议报告。

        Args:
            context: 融合上下文
            top_n: 每类返回前N条建议

        Returns:
            综合建议报告
        """
        # 执行融合
        all_recommendations = self.fuse(context)

        # 按类型分组
        by_type: dict[str, list[Recommendation]] = {}
        for rec in all_recommendations:
            type_name = rec.rec_type.name
            if type_name not in by_type:
                by_type[type_name] = []
            if len(by_type[type_name]) < top_n:
                by_type[type_name].append(rec)

        # 提取关键教训
        lessons = self.reflexion.get_lessons(
            category=ExperienceCategory.STRATEGY
            if context.strategy_id
            else None,
            limit=5,
        )

        # 获取相关模式
        patterns = self.patterns.get_by_regime(
            regime=context.market_regime,
            min_success_rate=0.5,
            limit=5,
        )

        return {
            "context": {
                "symbol": context.symbol,
                "strategy_id": context.strategy_id,
                "market_regime": context.market_regime.value,
                "volatility": context.volatility,
            },
            "recommendations": {
                type_name: [r.to_dict() for r in recs]
                for type_name, recs in by_type.items()
            },
            "total_recommendations": len(all_recommendations),
            "key_lessons": lessons[:5],
            "active_patterns": [p.name for p in patterns],
            "fusion_stats": self.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        return {
            **self._stats,
            "active_recommendations": len(self._active_recommendations),
            "registered_rules": len(self._fusion_rules),
        }
