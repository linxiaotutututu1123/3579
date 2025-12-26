"""
反思记忆库 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

Reflexion知识库功能:
- 经验记忆存储
- 失败教训记录
- 成功模式提取
- 相似经验检索

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
from typing import Any

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
)


class ExperienceType(Enum):
    """经验类型枚举.

    定义反思记忆的类型:
    - SUCCESS: 成功经验
    - FAILURE: 失败教训
    - INSIGHT: 洞察发现
    - WARNING: 风险警告
    - OPTIMIZATION: 优化建议
    """

    SUCCESS = auto()  # 成功经验
    FAILURE = auto()  # 失败教训
    INSIGHT = auto()  # 洞察发现
    WARNING = auto()  # 风险警告
    OPTIMIZATION = auto()  # 优化建议


class ExperienceCategory(Enum):
    """经验分类.

    按业务领域分类:
    - STRATEGY: 策略相关
    - EXECUTION: 执行相关
    - RISK: 风控相关
    - MARKET: 市场相关
    - SYSTEM: 系统相关
    """

    STRATEGY = "strategy"  # 策略经验
    EXECUTION = "execution"  # 执行经验
    RISK = "risk"  # 风控经验
    MARKET = "market"  # 市场经验
    SYSTEM = "system"  # 系统经验


@dataclass
class ExperienceContext:
    """经验上下文.

    记录经验产生时的环境信息。

    Attributes:
        market_state: 市场状态
        strategy_id: 策略ID
        symbol: 交易标的
        position: 持仓信息
        timestamp: 时间戳
        session: 交易时段
        extra: 额外信息
    """

    market_state: str = ""
    strategy_id: str = ""
    symbol: str = ""
    position: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    session: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperienceOutcome:
    """经验结果.

    记录经验的实际效果。

    Attributes:
        success: 是否成功
        pnl: 盈亏金额
        pnl_pct: 盈亏百分比
        duration: 持续时间
        slippage: 滑点
        impact: 影响程度 (1-10)
        lessons: 教训总结
    """

    success: bool = True
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration: float = 0.0
    slippage: float = 0.0
    impact: int = 5
    lessons: list[str] = field(default_factory=list)


@dataclass
class Experience:
    """经验条目.

    反思记忆的核心数据结构。

    Attributes:
        id: 经验ID
        exp_type: 经验类型
        category: 经验分类
        title: 经验标题
        description: 详细描述
        context: 上下文信息
        outcome: 结果信息
        action_taken: 采取的行动
        action_recommended: 建议的行动
        confidence: 置信度 (0-1)
        reuse_count: 复用次数
        created_at: 创建时间
        updated_at: 更新时间
        run_id: 运行ID
        tags: 标签列表
    """

    id: str
    exp_type: ExperienceType
    category: ExperienceCategory
    title: str
    description: str
    context: ExperienceContext
    outcome: ExperienceOutcome
    action_taken: str = ""
    action_recommended: str = ""
    confidence: float = 0.8
    reuse_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    run_id: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化时设置时间戳."""
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = self.created_at

    @classmethod
    def create(
        cls,
        exp_type: ExperienceType,
        category: ExperienceCategory,
        title: str,
        description: str,
        context: ExperienceContext | None = None,
        outcome: ExperienceOutcome | None = None,
        action_taken: str = "",
        action_recommended: str = "",
        confidence: float = 0.8,
        run_id: str = "",
        tags: list[str] | None = None,
    ) -> Experience:
        """创建新的经验条目.

        Args:
            exp_type: 经验类型
            category: 经验分类
            title: 标题
            description: 描述
            context: 上下文
            outcome: 结果
            action_taken: 采取的行动
            action_recommended: 建议行动
            confidence: 置信度
            run_id: 运行ID
            tags: 标签

        Returns:
            Experience 实例
        """
        return cls(
            id=str(uuid.uuid4()),
            exp_type=exp_type,
            category=category,
            title=title,
            description=description,
            context=context or ExperienceContext(),
            outcome=outcome or ExperienceOutcome(),
            action_taken=action_taken,
            action_recommended=action_recommended,
            confidence=confidence,
            run_id=run_id,
            tags=tags or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            字典表示
        """
        return {
            "id": self.id,
            "exp_type": self.exp_type.name,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "context": {
                "market_state": self.context.market_state,
                "strategy_id": self.context.strategy_id,
                "symbol": self.context.symbol,
                "position": self.context.position,
                "timestamp": self.context.timestamp,
                "session": self.context.session,
                "extra": self.context.extra,
            },
            "outcome": {
                "success": self.outcome.success,
                "pnl": self.outcome.pnl,
                "pnl_pct": self.outcome.pnl_pct,
                "duration": self.outcome.duration,
                "slippage": self.outcome.slippage,
                "impact": self.outcome.impact,
                "lessons": self.outcome.lessons,
            },
            "action_taken": self.action_taken,
            "action_recommended": self.action_recommended,
            "confidence": self.confidence,
            "reuse_count": self.reuse_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "run_id": self.run_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Experience:
        """从字典创建实例.

        Args:
            data: 字典数据

        Returns:
            Experience 实例
        """
        context_data = data.get("context", {})
        outcome_data = data.get("outcome", {})

        return cls(
            id=data["id"],
            exp_type=ExperienceType[data["exp_type"]],
            category=ExperienceCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            context=ExperienceContext(
                market_state=context_data.get("market_state", ""),
                strategy_id=context_data.get("strategy_id", ""),
                symbol=context_data.get("symbol", ""),
                position=context_data.get("position", {}),
                timestamp=context_data.get("timestamp", 0.0),
                session=context_data.get("session", ""),
                extra=context_data.get("extra", {}),
            ),
            outcome=ExperienceOutcome(
                success=outcome_data.get("success", True),
                pnl=outcome_data.get("pnl", 0.0),
                pnl_pct=outcome_data.get("pnl_pct", 0.0),
                duration=outcome_data.get("duration", 0.0),
                slippage=outcome_data.get("slippage", 0.0),
                impact=outcome_data.get("impact", 5),
                lessons=outcome_data.get("lessons", []),
            ),
            action_taken=data.get("action_taken", ""),
            action_recommended=data.get("action_recommended", ""),
            confidence=data.get("confidence", 0.8),
            reuse_count=data.get("reuse_count", 0),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            run_id=data.get("run_id", ""),
            tags=data.get("tags", []),
        )

    def to_knowledge_entry(self) -> KnowledgeEntry:
        """转换为通用知识条目.

        Returns:
            KnowledgeEntry 实例
        """
        # 根据经验类型确定优先级
        priority_map = {
            ExperienceType.FAILURE: KnowledgePriority.CRITICAL,
            ExperienceType.WARNING: KnowledgePriority.HIGH,
            ExperienceType.SUCCESS: KnowledgePriority.MEDIUM,
            ExperienceType.INSIGHT: KnowledgePriority.MEDIUM,
            ExperienceType.OPTIMIZATION: KnowledgePriority.LOW,
        }

        return KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content=self.to_dict(),
            priority=priority_map.get(self.exp_type, KnowledgePriority.MEDIUM),
            tags=self.tags + [self.exp_type.name, self.category.value],
            run_id=self.run_id,
            source="reflexion",
        )


class ReflexionStore:
    """反思记忆库.

    专门用于存储和检索交易经验的知识库。

    功能特性:
    - 记录成功和失败经验
    - 支持相似经验检索
    - 自动提取教训和建议
    - 统计经验复用情况

    军规要求:
    - M33: 知识沉淀 - 自动记录和归类经验
    - M3: 审计完整 - 所有操作记录
    - M7: 回放支持 - run_id追踪
    """

    def __init__(
        self,
        storage: KnowledgeStore[KnowledgeEntry],
        name: str = "reflexion",
    ) -> None:
        """初始化反思记忆库.

        Args:
            storage: 底层知识存储
            name: 库名称
        """
        self.storage = storage
        self.name = name
        self._stats = {
            "total_experiences": 0,
            "success_count": 0,
            "failure_count": 0,
            "reuse_total": 0,
        }

    def record(self, experience: Experience) -> str:
        """记录经验.

        Args:
            experience: 经验条目

        Returns:
            经验 ID
        """
        entry = experience.to_knowledge_entry()
        entry_id = self.storage.put(entry)

        # 更新统计
        self._stats["total_experiences"] += 1
        if experience.exp_type == ExperienceType.SUCCESS:
            self._stats["success_count"] += 1
        elif experience.exp_type == ExperienceType.FAILURE:
            self._stats["failure_count"] += 1

        return entry_id

    def record_success(
        self,
        title: str,
        description: str,
        category: ExperienceCategory,
        context: ExperienceContext | None = None,
        outcome: ExperienceOutcome | None = None,
        action_taken: str = "",
        run_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """记录成功经验.

        快捷方法用于记录成功案例。

        Args:
            title: 标题
            description: 描述
            category: 分类
            context: 上下文
            outcome: 结果
            action_taken: 采取的行动
            run_id: 运行ID
            tags: 标签

        Returns:
            经验 ID
        """
        exp = Experience.create(
            exp_type=ExperienceType.SUCCESS,
            category=category,
            title=title,
            description=description,
            context=context,
            outcome=outcome,
            action_taken=action_taken,
            run_id=run_id,
            tags=tags,
        )
        return self.record(exp)

    def record_failure(
        self,
        title: str,
        description: str,
        category: ExperienceCategory,
        context: ExperienceContext | None = None,
        outcome: ExperienceOutcome | None = None,
        action_taken: str = "",
        action_recommended: str = "",
        run_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """记录失败教训.

        快捷方法用于记录失败案例。

        Args:
            title: 标题
            description: 描述
            category: 分类
            context: 上下文
            outcome: 结果
            action_taken: 采取的行动
            action_recommended: 建议行动
            run_id: 运行ID
            tags: 标签

        Returns:
            经验 ID
        """
        exp = Experience.create(
            exp_type=ExperienceType.FAILURE,
            category=category,
            title=title,
            description=description,
            context=context,
            outcome=outcome,
            action_taken=action_taken,
            action_recommended=action_recommended,
            run_id=run_id,
            tags=tags,
        )
        return self.record(exp)

    def record_warning(
        self,
        title: str,
        description: str,
        category: ExperienceCategory,
        context: ExperienceContext | None = None,
        action_recommended: str = "",
        run_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """记录风险警告.

        Args:
            title: 标题
            description: 描述
            category: 分类
            context: 上下文
            action_recommended: 建议行动
            run_id: 运行ID
            tags: 标签

        Returns:
            经验 ID
        """
        exp = Experience.create(
            exp_type=ExperienceType.WARNING,
            category=category,
            title=title,
            description=description,
            context=context,
            action_recommended=action_recommended,
            run_id=run_id,
            tags=tags,
        )
        return self.record(exp)

    def get(self, experience_id: str) -> Experience | None:
        """获取经验.

        Args:
            experience_id: 经验 ID

        Returns:
            经验条目或 None
        """
        entry = self.storage.get(experience_id)
        if entry:
            return Experience.from_dict(entry.content)
        return None

    def search(
        self,
        exp_type: ExperienceType | None = None,
        category: ExperienceCategory | None = None,
        symbol: str | None = None,
        strategy_id: str | None = None,
        min_confidence: float = 0.0,
        min_impact: int = 0,
        success_only: bool = False,
        failure_only: bool = False,
        limit: int = 100,
    ) -> list[Experience]:
        """搜索经验.

        Args:
            exp_type: 经验类型过滤
            category: 分类过滤
            symbol: 标的过滤
            strategy_id: 策略ID过滤
            min_confidence: 最低置信度
            min_impact: 最低影响程度
            success_only: 只返回成功经验
            failure_only: 只返回失败经验
            limit: 返回数量限制

        Returns:
            匹配的经验列表
        """
        # 构建标签过滤条件
        tags: list[str] = []
        if exp_type:
            tags.append(exp_type.name)
        if category:
            tags.append(category.value)

        # 查询知识库
        entries = self.storage.query(
            knowledge_type=KnowledgeType.REFLEXION,
            tags=tags if tags else None,
            limit=limit * 2,  # 多取一些用于后续过滤
        )

        # 转换并过滤
        results: list[Experience] = []
        for entry in entries:
            exp = Experience.from_dict(entry.content)

            # 应用过滤条件
            if symbol and exp.context.symbol != symbol:
                continue
            if strategy_id and exp.context.strategy_id != strategy_id:
                continue
            if min_confidence > 0 and exp.confidence < min_confidence:
                continue
            if min_impact > 0 and exp.outcome.impact < min_impact:
                continue
            if success_only and exp.exp_type != ExperienceType.SUCCESS:
                continue
            if failure_only and exp.exp_type != ExperienceType.FAILURE:
                continue

            results.append(exp)
            if len(results) >= limit:
                break

        return results

    def find_similar(
        self,
        context: ExperienceContext,
        category: ExperienceCategory | None = None,
        limit: int = 10,
    ) -> list[Experience]:
        """查找相似经验.

        基于上下文信息查找相似的历史经验。

        Args:
            context: 当前上下文
            category: 分类过滤
            limit: 返回数量限制

        Returns:
            相似经验列表 (按相似度排序)
        """
        # 获取候选经验
        candidates = self.search(
            category=category,
            symbol=context.symbol if context.symbol else None,
            strategy_id=context.strategy_id if context.strategy_id else None,
            limit=limit * 5,
        )

        # 计算相似度并排序
        scored: list[tuple[float, Experience]] = []
        for exp in candidates:
            score = self._compute_similarity(context, exp.context)
            scored.append((score, exp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [exp for _, exp in scored[:limit]]

    def _compute_similarity(
        self,
        ctx1: ExperienceContext,
        ctx2: ExperienceContext,
    ) -> float:
        """计算上下文相似度.

        Args:
            ctx1: 上下文1
            ctx2: 上下文2

        Returns:
            相似度分数 (0-1)
        """
        score = 0.0
        weights = {
            "symbol": 0.3,
            "strategy_id": 0.25,
            "market_state": 0.25,
            "session": 0.2,
        }

        if ctx1.symbol and ctx1.symbol == ctx2.symbol:
            score += weights["symbol"]
        if ctx1.strategy_id and ctx1.strategy_id == ctx2.strategy_id:
            score += weights["strategy_id"]
        if ctx1.market_state and ctx1.market_state == ctx2.market_state:
            score += weights["market_state"]
        if ctx1.session and ctx1.session == ctx2.session:
            score += weights["session"]

        return score

    def get_lessons(
        self,
        category: ExperienceCategory | None = None,
        limit: int = 20,
    ) -> list[str]:
        """获取教训总结.

        从失败经验中提取教训列表。

        Args:
            category: 分类过滤
            limit: 返回数量限制

        Returns:
            教训列表
        """
        failures = self.search(
            category=category,
            failure_only=True,
            limit=limit,
        )

        lessons: list[str] = []
        for exp in failures:
            lessons.extend(exp.outcome.lessons)
            if exp.action_recommended:
                lessons.append(f"[建议] {exp.action_recommended}")

        return lessons[:limit]

    def get_best_practices(
        self,
        category: ExperienceCategory | None = None,
        min_confidence: float = 0.8,
        limit: int = 20,
    ) -> list[Experience]:
        """获取最佳实践.

        从成功经验中提取高置信度的最佳实践。

        Args:
            category: 分类过滤
            min_confidence: 最低置信度
            limit: 返回数量限制

        Returns:
            最佳实践经验列表
        """
        return self.search(
            category=category,
            success_only=True,
            min_confidence=min_confidence,
            limit=limit,
        )

    def mark_reused(self, experience_id: str) -> bool:
        """标记经验被复用.

        Args:
            experience_id: 经验 ID

        Returns:
            是否成功
        """
        exp = self.get(experience_id)
        if exp:
            exp.reuse_count += 1
            exp.updated_at = time.time()
            entry = exp.to_knowledge_entry()
            entry.id = experience_id
            self.storage.put(entry)
            self._stats["reuse_total"] += 1
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        return {
            **self._stats,
            "storage_stats": self.storage.get_stats(),
        }


def create_reflexion_from_decision(
    decision_event: dict[str, Any],
    outcome: ExperienceOutcome,
    exp_type: ExperienceType = ExperienceType.SUCCESS,
) -> Experience:
    """从决策事件创建反思经验.

    将审计模块的DecisionEvent转换为反思经验。

    Args:
        decision_event: 决策事件数据
        outcome: 结果信息
        exp_type: 经验类型

    Returns:
        Experience 实例
    """
    context = ExperienceContext(
        strategy_id=decision_event.get("strategy_id", ""),
        timestamp=decision_event.get("ts", time.time()),
        extra={
            "exec_id": decision_event.get("exec_id", ""),
            "feature_hash": decision_event.get("feature_hash", ""),
            "signals": decision_event.get("signals", {}),
        },
    )

    title = f"{exp_type.name}: {decision_event.get('strategy_id', 'unknown')}"
    description = f"策略决策结果 - 置信度: {decision_event.get('confidence', 0)}"

    return Experience.create(
        exp_type=exp_type,
        category=ExperienceCategory.STRATEGY,
        title=title,
        description=description,
        context=context,
        outcome=outcome,
        confidence=decision_event.get("confidence", 0.5),
        run_id=decision_event.get("run_id", ""),
    )
