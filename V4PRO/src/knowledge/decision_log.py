"""
决策日志 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

决策知识库功能:
- 决策过程记录
- 决策链路追踪
- 决策效果评估
- 决策模式分析

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


class DecisionType(Enum):
    """决策类型枚举.

    定义系统支持的决策类型:
    - ENTRY: 入场决策
    - EXIT: 出场决策
    - SCALE: 加减仓决策
    - HOLD: 持仓决策
    - SKIP: 跳过决策
    - EMERGENCY: 紧急决策
    """

    ENTRY = auto()  # 入场
    EXIT = auto()  # 出场
    SCALE = auto()  # 加减仓
    HOLD = auto()  # 持仓
    SKIP = auto()  # 跳过
    EMERGENCY = auto()  # 紧急


class DecisionOutcome(Enum):
    """决策结果.

    - PROFITABLE: 盈利
    - LOSS: 亏损
    - BREAKEVEN: 平局
    - PENDING: 待定
    - CANCELLED: 取消
    """

    PROFITABLE = "profitable"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class DecisionContext:
    """决策上下文.

    记录决策时的环境信息。

    Attributes:
        market_price: 市场价格
        bid_price: 买一价
        ask_price: 卖一价
        position: 当前持仓
        portfolio_value: 组合价值
        available_margin: 可用保证金
        volatility: 波动率
        market_regime: 市场状态
        session: 交易时段
        extra: 额外信息
    """

    market_price: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    position: dict[str, int] = field(default_factory=dict)
    portfolio_value: float = 0.0
    available_margin: float = 0.0
    volatility: float = 0.0
    market_regime: str = ""
    session: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRationale:
    """决策依据.

    记录做出决策的原因和依据。

    Attributes:
        signals: 触发信号列表
        indicators: 指标值
        rules_triggered: 触发的规则
        confidence: 置信度
        risk_assessment: 风险评估
        model_predictions: 模型预测
        human_notes: 人工备注
    """

    signals: list[str] = field(default_factory=list)
    indicators: dict[str, float] = field(default_factory=dict)
    rules_triggered: list[str] = field(default_factory=list)
    confidence: float = 0.8
    risk_assessment: dict[str, Any] = field(default_factory=dict)
    model_predictions: dict[str, float] = field(default_factory=dict)
    human_notes: str = ""


@dataclass
class DecisionResult:
    """决策结果.

    记录决策执行后的结果。

    Attributes:
        outcome: 结果类型
        executed: 是否执行
        execution_price: 执行价格
        slippage: 滑点
        pnl: 盈亏金额
        pnl_pct: 盈亏百分比
        duration: 持续时间
        evaluation_score: 评估分数
        lessons: 总结教训
    """

    outcome: DecisionOutcome = DecisionOutcome.PENDING
    executed: bool = False
    execution_price: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration: float = 0.0
    evaluation_score: float = 0.0
    lessons: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """决策条目.

    决策日志的核心数据结构。

    Attributes:
        id: 决策ID
        decision_type: 决策类型
        strategy_id: 策略ID
        symbol: 交易标的
        direction: 方向 (long/short)
        target_qty: 目标数量
        context: 决策上下文
        rationale: 决策依据
        result: 决策结果
        run_id: 运行ID
        parent_decision_id: 父决策ID (用于决策链)
        created_at: 创建时间
        updated_at: 更新时间
        tags: 标签列表
    """

    id: str
    decision_type: DecisionType
    strategy_id: str
    symbol: str
    direction: str
    target_qty: int
    context: DecisionContext
    rationale: DecisionRationale
    result: DecisionResult = field(default_factory=DecisionResult)
    run_id: str = ""
    parent_decision_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
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
        decision_type: DecisionType,
        strategy_id: str,
        symbol: str,
        direction: str,
        target_qty: int,
        context: DecisionContext | None = None,
        rationale: DecisionRationale | None = None,
        run_id: str = "",
        parent_decision_id: str = "",
        tags: list[str] | None = None,
    ) -> Decision:
        """创建新的决策条目.

        Args:
            decision_type: 决策类型
            strategy_id: 策略ID
            symbol: 标的
            direction: 方向
            target_qty: 目标数量
            context: 上下文
            rationale: 依据
            run_id: 运行ID
            parent_decision_id: 父决策ID
            tags: 标签

        Returns:
            Decision 实例
        """
        return cls(
            id=str(uuid.uuid4()),
            decision_type=decision_type,
            strategy_id=strategy_id,
            symbol=symbol,
            direction=direction,
            target_qty=target_qty,
            context=context or DecisionContext(),
            rationale=rationale or DecisionRationale(),
            run_id=run_id,
            parent_decision_id=parent_decision_id,
            tags=tags or [],
        )

    def update_result(
        self,
        outcome: DecisionOutcome,
        pnl: float = 0.0,
        pnl_pct: float = 0.0,
        execution_price: float = 0.0,
        slippage: float = 0.0,
        lessons: list[str] | None = None,
    ) -> None:
        """更新决策结果.

        Args:
            outcome: 结果类型
            pnl: 盈亏金额
            pnl_pct: 盈亏百分比
            execution_price: 执行价格
            slippage: 滑点
            lessons: 教训总结
        """
        self.result = DecisionResult(
            outcome=outcome,
            executed=True,
            execution_price=execution_price,
            slippage=slippage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration=time.time() - self.created_at,
            lessons=lessons or [],
        )
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            字典表示
        """
        return {
            "id": self.id,
            "decision_type": self.decision_type.name,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "target_qty": self.target_qty,
            "context": {
                "market_price": self.context.market_price,
                "bid_price": self.context.bid_price,
                "ask_price": self.context.ask_price,
                "position": self.context.position,
                "portfolio_value": self.context.portfolio_value,
                "available_margin": self.context.available_margin,
                "volatility": self.context.volatility,
                "market_regime": self.context.market_regime,
                "session": self.context.session,
                "extra": self.context.extra,
            },
            "rationale": {
                "signals": self.rationale.signals,
                "indicators": self.rationale.indicators,
                "rules_triggered": self.rationale.rules_triggered,
                "confidence": self.rationale.confidence,
                "risk_assessment": self.rationale.risk_assessment,
                "model_predictions": self.rationale.model_predictions,
                "human_notes": self.rationale.human_notes,
            },
            "result": {
                "outcome": self.result.outcome.value,
                "executed": self.result.executed,
                "execution_price": self.result.execution_price,
                "slippage": self.result.slippage,
                "pnl": self.result.pnl,
                "pnl_pct": self.result.pnl_pct,
                "duration": self.result.duration,
                "evaluation_score": self.result.evaluation_score,
                "lessons": self.result.lessons,
            },
            "run_id": self.run_id,
            "parent_decision_id": self.parent_decision_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Decision:
        """从字典创建实例.

        Args:
            data: 字典数据

        Returns:
            Decision 实例
        """
        ctx_data = data.get("context", {})
        rat_data = data.get("rationale", {})
        res_data = data.get("result", {})

        decision = cls(
            id=data["id"],
            decision_type=DecisionType[data["decision_type"]],
            strategy_id=data["strategy_id"],
            symbol=data["symbol"],
            direction=data["direction"],
            target_qty=data["target_qty"],
            context=DecisionContext(
                market_price=ctx_data.get("market_price", 0.0),
                bid_price=ctx_data.get("bid_price", 0.0),
                ask_price=ctx_data.get("ask_price", 0.0),
                position=ctx_data.get("position", {}),
                portfolio_value=ctx_data.get("portfolio_value", 0.0),
                available_margin=ctx_data.get("available_margin", 0.0),
                volatility=ctx_data.get("volatility", 0.0),
                market_regime=ctx_data.get("market_regime", ""),
                session=ctx_data.get("session", ""),
                extra=ctx_data.get("extra", {}),
            ),
            rationale=DecisionRationale(
                signals=rat_data.get("signals", []),
                indicators=rat_data.get("indicators", {}),
                rules_triggered=rat_data.get("rules_triggered", []),
                confidence=rat_data.get("confidence", 0.8),
                risk_assessment=rat_data.get("risk_assessment", {}),
                model_predictions=rat_data.get("model_predictions", {}),
                human_notes=rat_data.get("human_notes", ""),
            ),
            result=DecisionResult(
                outcome=DecisionOutcome(res_data.get("outcome", "pending")),
                executed=res_data.get("executed", False),
                execution_price=res_data.get("execution_price", 0.0),
                slippage=res_data.get("slippage", 0.0),
                pnl=res_data.get("pnl", 0.0),
                pnl_pct=res_data.get("pnl_pct", 0.0),
                duration=res_data.get("duration", 0.0),
                evaluation_score=res_data.get("evaluation_score", 0.0),
                lessons=res_data.get("lessons", []),
            ),
            run_id=data.get("run_id", ""),
            parent_decision_id=data.get("parent_decision_id", ""),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            tags=data.get("tags", []),
        )
        return decision

    def to_knowledge_entry(self) -> KnowledgeEntry:
        """转换为通用知识条目.

        Returns:
            KnowledgeEntry 实例
        """
        # 根据决策类型和结果确定优先级
        if self.decision_type == DecisionType.EMERGENCY:
            priority = KnowledgePriority.CRITICAL
        elif self.result.outcome == DecisionOutcome.LOSS:
            priority = KnowledgePriority.HIGH
        elif self.result.outcome == DecisionOutcome.PROFITABLE:
            priority = KnowledgePriority.MEDIUM
        else:
            priority = KnowledgePriority.LOW

        return KnowledgeEntry.create(
            knowledge_type=KnowledgeType.DECISION,
            content=self.to_dict(),
            priority=priority,
            tags=self.tags + [self.decision_type.name, self.symbol],
            run_id=self.run_id,
            source="decision_log",
        )


class DecisionLog:
    """决策日志库.

    专门用于记录和分析交易决策的知识库。

    功能特性:
    - 决策记录和追踪
    - 决策链路分析
    - 决策效果评估
    - 决策模式识别

    军规要求:
    - M33: 知识沉淀 - 自动记录决策
    - M3: 审计完整 - 所有决策可追溯
    - M7: 回放支持 - 支持决策回放
    """

    def __init__(
        self,
        storage: KnowledgeStore[KnowledgeEntry],
        name: str = "decision_log",
    ) -> None:
        """初始化决策日志.

        Args:
            storage: 底层知识存储
            name: 库名称
        """
        self.storage = storage
        self.name = name
        self._stats = {
            "total_decisions": 0,
            "profitable_count": 0,
            "loss_count": 0,
            "pending_count": 0,
        }

    def log(self, decision: Decision) -> str:
        """记录决策.

        Args:
            decision: 决策条目

        Returns:
            决策 ID
        """
        entry = decision.to_knowledge_entry()
        entry_id = self.storage.put(entry)

        self._stats["total_decisions"] += 1
        if decision.result.outcome == DecisionOutcome.PROFITABLE:
            self._stats["profitable_count"] += 1
        elif decision.result.outcome == DecisionOutcome.LOSS:
            self._stats["loss_count"] += 1
        else:
            self._stats["pending_count"] += 1

        return entry_id

    def get(self, decision_id: str) -> Decision | None:
        """获取决策.

        Args:
            decision_id: 决策 ID

        Returns:
            决策条目或 None
        """
        entry = self.storage.get(decision_id)
        if entry:
            return Decision.from_dict(entry.content)
        return None

    def update(self, decision: Decision) -> str:
        """更新决策.

        Args:
            decision: 决策条目

        Returns:
            决策 ID
        """
        decision.updated_at = time.time()
        entry = decision.to_knowledge_entry()
        entry.id = decision.id
        return self.storage.put(entry)

    def complete_decision(
        self,
        decision_id: str,
        outcome: DecisionOutcome,
        pnl: float = 0.0,
        pnl_pct: float = 0.0,
        execution_price: float = 0.0,
        slippage: float = 0.0,
        lessons: list[str] | None = None,
    ) -> bool:
        """完成决策并更新结果.

        Args:
            decision_id: 决策 ID
            outcome: 结果类型
            pnl: 盈亏金额
            pnl_pct: 盈亏百分比
            execution_price: 执行价格
            slippage: 滑点
            lessons: 教训总结

        Returns:
            是否成功
        """
        decision = self.get(decision_id)
        if decision:
            # 更新统计
            old_outcome = decision.result.outcome
            if old_outcome == DecisionOutcome.PENDING:
                self._stats["pending_count"] -= 1

            decision.update_result(
                outcome=outcome,
                pnl=pnl,
                pnl_pct=pnl_pct,
                execution_price=execution_price,
                slippage=slippage,
                lessons=lessons,
            )
            self.update(decision)

            if outcome == DecisionOutcome.PROFITABLE:
                self._stats["profitable_count"] += 1
            elif outcome == DecisionOutcome.LOSS:
                self._stats["loss_count"] += 1

            return True
        return False

    def search(
        self,
        decision_type: DecisionType | None = None,
        strategy_id: str | None = None,
        symbol: str | None = None,
        outcome: DecisionOutcome | None = None,
        min_confidence: float = 0.0,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        """搜索决策.

        Args:
            decision_type: 决策类型过滤
            strategy_id: 策略ID过滤
            symbol: 标的过滤
            outcome: 结果过滤
            min_confidence: 最低置信度
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            匹配的决策列表
        """
        # 构建标签过滤
        tags: list[str] = []
        if decision_type:
            tags.append(decision_type.name)
        if symbol:
            tags.append(symbol)

        # 查询知识库
        entries = self.storage.query(
            knowledge_type=KnowledgeType.DECISION,
            tags=tags if tags else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit * 2,
        )

        # 转换并过滤
        results: list[Decision] = []
        for entry in entries:
            decision = Decision.from_dict(entry.content)

            if strategy_id and decision.strategy_id != strategy_id:
                continue
            if outcome and decision.result.outcome != outcome:
                continue
            if min_confidence > 0 and decision.rationale.confidence < min_confidence:
                continue

            results.append(decision)
            if len(results) >= limit:
                break

        return results

    def get_decision_chain(self, decision_id: str) -> list[Decision]:
        """获取决策链路.

        从指定决策向上追溯整个决策链。

        Args:
            decision_id: 起始决策 ID

        Returns:
            决策链列表 (从根到叶)
        """
        chain: list[Decision] = []
        current_id = decision_id

        while current_id:
            decision = self.get(current_id)
            if not decision:
                break
            chain.append(decision)
            current_id = decision.parent_decision_id

        chain.reverse()
        return chain

    def get_child_decisions(self, parent_id: str) -> list[Decision]:
        """获取子决策.

        Args:
            parent_id: 父决策 ID

        Returns:
            子决策列表
        """
        all_decisions = self.search(limit=1000)
        return [d for d in all_decisions if d.parent_decision_id == parent_id]

    def analyze_strategy(
        self,
        strategy_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> dict[str, Any]:
        """分析策略决策表现.

        Args:
            strategy_id: 策略ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            分析结果
        """
        decisions = self.search(
            strategy_id=strategy_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        if not decisions:
            return {"strategy_id": strategy_id, "total_decisions": 0}

        # 统计分析
        total = len(decisions)
        profitable = sum(1 for d in decisions if d.result.outcome == DecisionOutcome.PROFITABLE)
        losses = sum(1 for d in decisions if d.result.outcome == DecisionOutcome.LOSS)
        pending = sum(1 for d in decisions if d.result.outcome == DecisionOutcome.PENDING)

        completed = [d for d in decisions if d.result.executed]
        total_pnl = sum(d.result.pnl for d in completed)
        avg_pnl = total_pnl / len(completed) if completed else 0

        confidences = [d.rationale.confidence for d in decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "strategy_id": strategy_id,
            "total_decisions": total,
            "profitable_count": profitable,
            "loss_count": losses,
            "pending_count": pending,
            "win_rate": profitable / (profitable + losses) if (profitable + losses) > 0 else 0,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "avg_confidence": avg_confidence,
            "by_type": {
                dt.name: sum(1 for d in decisions if d.decision_type == dt)
                for dt in DecisionType
            },
        }

    def get_lessons_learned(
        self,
        strategy_id: str | None = None,
        loss_only: bool = True,
        limit: int = 20,
    ) -> list[str]:
        """获取教训总结.

        Args:
            strategy_id: 策略ID过滤
            loss_only: 只从亏损决策中提取
            limit: 返回数量限制

        Returns:
            教训列表
        """
        outcome_filter = DecisionOutcome.LOSS if loss_only else None
        decisions = self.search(
            strategy_id=strategy_id,
            outcome=outcome_filter,
            limit=limit,
        )

        lessons: list[str] = []
        for decision in decisions:
            lessons.extend(decision.result.lessons)

        return lessons[:limit]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        return {
            **self._stats,
            "win_rate": (
                self._stats["profitable_count"]
                / (self._stats["profitable_count"] + self._stats["loss_count"])
                if (self._stats["profitable_count"] + self._stats["loss_count"]) > 0
                else 0
            ),
            "storage_stats": self.storage.get_stats(),
        }
