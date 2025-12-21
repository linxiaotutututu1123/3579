"""
决策日志测试.

测试 decision_log.py 中的决策记录功能。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.decision_log import (
    Decision,
    DecisionContext,
    DecisionLog,
    DecisionOutcome,
    DecisionRationale,
    DecisionResult,
    DecisionType,
)
from src.knowledge.base import KnowledgeType


class TestDecision:
    """决策条目测试."""

    def test_create_decision(self) -> None:
        """测试创建决策."""
        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="trend_follower",
            symbol="IF2401",
            direction="long",
            target_qty=2,
        )

        assert decision.id
        assert decision.decision_type == DecisionType.ENTRY
        assert decision.strategy_id == "trend_follower"
        assert decision.symbol == "IF2401"
        assert decision.direction == "long"
        assert decision.target_qty == 2

    def test_decision_with_context(self, sample_decision: Decision) -> None:
        """测试带上下文的决策."""
        assert sample_decision.context.market_price == 4000.0
        assert sample_decision.context.volatility == 0.02
        assert sample_decision.context.market_regime == "trending_up"

    def test_decision_with_rationale(self, sample_decision: Decision) -> None:
        """测试带依据的决策."""
        assert "breakout_signal" in sample_decision.rationale.signals
        assert sample_decision.rationale.confidence == 0.8
        assert "rsi" in sample_decision.rationale.indicators

    def test_update_result(self, sample_decision: Decision) -> None:
        """测试更新结果."""
        sample_decision.update_result(
            outcome=DecisionOutcome.PROFITABLE,
            pnl=5000.0,
            pnl_pct=0.05,
            execution_price=4001.0,
            slippage=1.0,
            lessons=["及时止盈"],
        )

        assert sample_decision.result.outcome == DecisionOutcome.PROFITABLE
        assert sample_decision.result.pnl == 5000.0
        assert sample_decision.result.executed
        assert "及时止盈" in sample_decision.result.lessons

    def test_to_dict(self, sample_decision: Decision) -> None:
        """测试转换为字典."""
        data = sample_decision.to_dict()

        assert data["id"] == sample_decision.id
        assert data["decision_type"] == "ENTRY"
        assert data["strategy_id"] == sample_decision.strategy_id
        assert "context" in data
        assert "rationale" in data
        assert "result" in data

    def test_from_dict(self, sample_decision: Decision) -> None:
        """测试从字典创建."""
        data = sample_decision.to_dict()
        restored = Decision.from_dict(data)

        assert restored.id == sample_decision.id
        assert restored.decision_type == sample_decision.decision_type
        assert restored.strategy_id == sample_decision.strategy_id
        assert restored.context.market_price == sample_decision.context.market_price

    def test_to_knowledge_entry(self, sample_decision: Decision) -> None:
        """测试转换为知识条目."""
        entry = sample_decision.to_knowledge_entry()

        assert entry.knowledge_type == KnowledgeType.DECISION
        assert "ENTRY" in entry.tags
        assert "IF2401" in entry.tags


class TestDecisionLog:
    """决策日志测试."""

    def test_log_decision(
        self,
        decision_log: DecisionLog,
        sample_decision: Decision,
    ) -> None:
        """测试记录决策."""
        decision_id = decision_log.log(sample_decision)
        assert decision_id

        retrieved = decision_log.get(decision_id)
        assert retrieved is not None
        assert retrieved.symbol == sample_decision.symbol

    def test_update_decision(
        self,
        decision_log: DecisionLog,
        sample_decision: Decision,
    ) -> None:
        """测试更新决策."""
        decision_log.log(sample_decision)

        sample_decision.rationale.confidence = 0.9
        decision_log.update(sample_decision)

        retrieved = decision_log.get(sample_decision.id)
        assert retrieved is not None
        assert retrieved.rationale.confidence == 0.9

    def test_complete_decision(self, decision_log: DecisionLog) -> None:
        """测试完成决策."""
        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision_id = decision_log.log(decision)

        success = decision_log.complete_decision(
            decision_id=decision_id,
            outcome=DecisionOutcome.PROFITABLE,
            pnl=1000.0,
            pnl_pct=0.01,
            execution_price=4001.0,
            slippage=1.0,
            lessons=["好决策"],
        )
        assert success

        retrieved = decision_log.get(decision_id)
        assert retrieved is not None
        assert retrieved.result.outcome == DecisionOutcome.PROFITABLE
        assert retrieved.result.pnl == 1000.0

    def test_search_by_type(self, decision_log: DecisionLog) -> None:
        """测试按类型搜索."""
        entry_decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        exit_decision = Decision.create(
            decision_type=DecisionType.EXIT,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=0,
        )

        decision_log.log(entry_decision)
        decision_log.log(exit_decision)

        results = decision_log.search(decision_type=DecisionType.ENTRY)
        assert len(results) >= 1
        assert all(d.decision_type == DecisionType.ENTRY for d in results)

    def test_search_by_strategy(self, decision_log: DecisionLog) -> None:
        """测试按策略搜索."""
        decision1 = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="strategy_a",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision2 = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="strategy_b",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )

        decision_log.log(decision1)
        decision_log.log(decision2)

        results = decision_log.search(strategy_id="strategy_a")
        assert len(results) >= 1
        assert all(d.strategy_id == "strategy_a" for d in results)

    def test_search_by_symbol(self, decision_log: DecisionLog) -> None:
        """测试按标的搜索."""
        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IC2401",
            direction="long",
            target_qty=1,
        )
        decision_log.log(decision)

        results = decision_log.search(symbol="IC2401")
        assert len(results) >= 1
        assert all(d.symbol == "IC2401" for d in results)

    def test_search_by_outcome(self, decision_log: DecisionLog) -> None:
        """测试按结果搜索."""
        profitable = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        profitable.update_result(DecisionOutcome.PROFITABLE, pnl=1000)

        loss = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        loss.update_result(DecisionOutcome.LOSS, pnl=-500)

        decision_log.log(profitable)
        decision_log.log(loss)

        results = decision_log.search(outcome=DecisionOutcome.PROFITABLE)
        assert all(d.result.outcome == DecisionOutcome.PROFITABLE for d in results)

    def test_search_by_time_range(self, decision_log: DecisionLog) -> None:
        """测试按时间范围搜索."""
        now = time.time()

        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision_log.log(decision)

        results = decision_log.search(
            start_time=now - 60,
            end_time=now + 60,
        )
        assert len(results) >= 1

    def test_get_decision_chain(self, decision_log: DecisionLog) -> None:
        """测试获取决策链."""
        parent = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=2,
        )
        parent_id = decision_log.log(parent)

        child = Decision.create(
            decision_type=DecisionType.SCALE,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=3,
            parent_decision_id=parent_id,
        )
        child_id = decision_log.log(child)

        chain = decision_log.get_decision_chain(child_id)
        assert len(chain) == 2
        assert chain[0].id == parent_id
        assert chain[1].id == child_id

    def test_get_child_decisions(self, decision_log: DecisionLog) -> None:
        """测试获取子决策."""
        parent = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=2,
        )
        parent_id = decision_log.log(parent)

        for i in range(3):
            child = Decision.create(
                decision_type=DecisionType.SCALE,
                strategy_id="test",
                symbol="IF2401",
                direction="long",
                target_qty=2 + i,
                parent_decision_id=parent_id,
            )
            decision_log.log(child)

        children = decision_log.get_child_decisions(parent_id)
        assert len(children) == 3

    def test_analyze_strategy(self, decision_log: DecisionLog) -> None:
        """测试策略分析."""
        # 创建一些决策
        for i in range(10):
            decision = Decision.create(
                decision_type=DecisionType.ENTRY,
                strategy_id="test_strategy",
                symbol="IF2401",
                direction="long",
                target_qty=1,
                rationale=DecisionRationale(confidence=0.8),
            )
            outcome = DecisionOutcome.PROFITABLE if i < 7 else DecisionOutcome.LOSS
            pnl = 1000 if i < 7 else -500
            decision.update_result(outcome, pnl=pnl)
            decision_log.log(decision)

        analysis = decision_log.analyze_strategy("test_strategy")

        assert analysis["strategy_id"] == "test_strategy"
        assert analysis["total_decisions"] == 10
        assert analysis["profitable_count"] == 7
        assert analysis["loss_count"] == 3
        assert analysis["win_rate"] == pytest.approx(0.7, rel=0.01)

    def test_get_lessons_learned(self, decision_log: DecisionLog) -> None:
        """测试获取教训."""
        decision = Decision.create(
            decision_type=DecisionType.ENTRY,
            strategy_id="test",
            symbol="IF2401",
            direction="long",
            target_qty=1,
        )
        decision.update_result(
            DecisionOutcome.LOSS,
            pnl=-500,
            lessons=["不要追涨", "设置止损"],
        )
        decision_log.log(decision)

        lessons = decision_log.get_lessons_learned(loss_only=True)
        assert len(lessons) >= 1

    def test_get_stats(self, decision_log: DecisionLog) -> None:
        """测试统计信息."""
        # 创建一些决策
        for i in range(5):
            decision = Decision.create(
                decision_type=DecisionType.ENTRY,
                strategy_id="test",
                symbol="IF2401",
                direction="long",
                target_qty=1,
            )
            if i < 3:
                decision.update_result(DecisionOutcome.PROFITABLE, pnl=1000)
            else:
                decision.update_result(DecisionOutcome.LOSS, pnl=-500)
            decision_log.log(decision)

        stats = decision_log.get_stats()
        assert stats["total_decisions"] >= 5
        assert stats["profitable_count"] >= 3
        assert stats["loss_count"] >= 2
