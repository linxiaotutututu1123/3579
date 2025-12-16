"""实验性策略模块测试 (军规级 v4.0)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityLevel,
    MaturityScore,
    TrainingHistory,
    TrainingRecord,
)
from src.strategy.experimental.training_gate import (
    ActivationDecision,
    ActivationStatus,
    TrainingGate,
    TrainingGateConfig,
)
from src.strategy.experimental.training_monitor import (
    TrainingMonitor,
    TrainingProgress,
    TrainingSession,
    TrainingStatus,
)


class TestMaturityLevel:
    """成熟度级别测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert MaturityLevel.EMBRYONIC.value == "embryonic"
        assert MaturityLevel.DEVELOPING.value == "developing"
        assert MaturityLevel.GROWING.value == "growing"
        assert MaturityLevel.MATURING.value == "maturing"
        assert MaturityLevel.MATURE.value == "mature"


class TestMaturityScore:
    """成熟度分数测试."""

    def test_weighted_score(self) -> None:
        """测试加权分数."""
        score = MaturityScore(
            dimension="stability",
            score=0.8,
            weight=0.25,
            details={"sharpe": 0.9},
            reason="Good stability",
        )
        assert score.weighted_score == 0.2

    def test_is_passing(self) -> None:
        """测试通过判断."""
        passing = MaturityScore("test", 0.7, 0.1, {}, "")
        failing = MaturityScore("test", 0.5, 0.1, {}, "")
        assert passing.is_passing is True
        assert failing.is_passing is False


class TestTrainingRecord:
    """训练记录测试."""

    def test_creation(self) -> None:
        """测试创建."""
        record = TrainingRecord(
            date=datetime.now().date(),
            returns=0.01,
            sharpe=1.5,
            max_drawdown=0.05,
            win_rate=0.6,
            trades=100,
        )
        assert record.returns == 0.01
        assert record.sharpe == 1.5


class TestTrainingHistory:
    """训练历史测试."""

    def test_add_record(self) -> None:
        """测试添加记录."""
        history = TrainingHistory(strategy_id="test")
        record = TrainingRecord(
            date=datetime.now().date(),
            returns=0.01,
            sharpe=1.5,
            max_drawdown=0.05,
            win_rate=0.6,
            trades=100,
        )
        history.add_record(record)
        assert len(history.records) == 1

    def test_training_days(self) -> None:
        """测试训练天数."""
        history = TrainingHistory(strategy_id="test")
        for i in range(10):
            record = TrainingRecord(
                date=(datetime.now() - timedelta(days=i)).date(),
                returns=0.01,
                sharpe=1.5,
                max_drawdown=0.05,
                win_rate=0.6,
                trades=100,
            )
            history.add_record(record)
        assert history.training_days >= 10


class TestMaturityEvaluator:
    """成熟度评估器测试."""

    def test_evaluate_empty_history(self) -> None:
        """测试空历史评估."""
        evaluator = MaturityEvaluator()
        history = TrainingHistory(strategy_id="test")
        report = evaluator.evaluate(history)
        assert report.is_mature is False
        assert report.total_score == 0.0

    def test_evaluate_with_records(self) -> None:
        """测试有记录的评估."""
        evaluator = MaturityEvaluator()
        history = TrainingHistory(strategy_id="test")

        # 添加足够的记录
        for i in range(100):
            record = TrainingRecord(
                date=(datetime.now() - timedelta(days=i)).date(),
                returns=0.005,
                sharpe=2.0,
                max_drawdown=0.03,
                win_rate=0.65,
                trades=50,
            )
            history.add_record(record)

        report = evaluator.evaluate(history)
        assert report.total_score >= 0
        assert report.strategy_id == "test"

    def test_get_level(self) -> None:
        """测试获取级别."""
        evaluator = MaturityEvaluator()
        assert evaluator._get_level(0.1) == MaturityLevel.EMBRYONIC
        assert evaluator._get_level(0.3) == MaturityLevel.DEVELOPING
        assert evaluator._get_level(0.5) == MaturityLevel.GROWING
        assert evaluator._get_level(0.7) == MaturityLevel.MATURING
        assert evaluator._get_level(0.9) == MaturityLevel.MATURE

    def test_evaluate_stability(self) -> None:
        """测试稳定性评估."""
        evaluator = MaturityEvaluator()
        history = TrainingHistory(strategy_id="test")
        for i in range(30):
            record = TrainingRecord(
                date=(datetime.now() - timedelta(days=i)).date(),
                returns=0.01,
                sharpe=2.0,
                max_drawdown=0.02,
                win_rate=0.7,
                trades=100,
            )
            history.add_record(record)

        score = evaluator._evaluate_stability(history)
        assert score.dimension == "stability"
        assert 0 <= score.score <= 1


class TestActivationStatus:
    """启用状态测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert ActivationStatus.TRAINING.value == "training"
        assert ActivationStatus.PENDING_REVIEW.value == "pending"
        assert ActivationStatus.APPROVED.value == "approved"


class TestActivationDecision:
    """启用决策测试."""

    def test_to_display(self) -> None:
        """测试显示文本."""
        decision = ActivationDecision(
            allowed=False,
            status=ActivationStatus.TRAINING,
            maturity_pct=0.5,
            training_days=30,
            remaining_days=60,
            reasons=["Not enough training"],
            report=None,
            requires_manual_approval=False,
        )
        text = decision.to_display()
        assert "TRAINING" in text
        assert "50.0%" in text


class TestTrainingGateConfig:
    """训练门禁配置测试."""

    def test_defaults(self) -> None:
        """测试默认值."""
        config = TrainingGateConfig()
        assert config.min_training_days == 90
        assert config.min_maturity_pct == 0.8
        assert config.min_dimension_pct == 0.6


class TestTrainingGate:
    """训练门禁测试."""

    def test_check_activation_insufficient_training(self) -> None:
        """测试训练不足."""
        evaluator = MaturityEvaluator()
        gate = TrainingGate(evaluator)
        history = TrainingHistory(strategy_id="test")

        # 添加少量记录
        for i in range(10):
            record = TrainingRecord(
                date=(datetime.now() - timedelta(days=i)).date(),
                returns=0.01,
                sharpe=2.0,
                max_drawdown=0.02,
                win_rate=0.7,
                trades=100,
            )
            history.add_record(record)

        decision = gate.check_activation(history)
        assert decision.allowed is False
        assert decision.remaining_days > 0

    def test_can_activate(self) -> None:
        """测试能否启用."""
        evaluator = MaturityEvaluator()
        gate = TrainingGate(evaluator)
        history = TrainingHistory(strategy_id="test")

        # 不添加记录，应该不能启用
        assert gate.can_activate(history) is False


class TestTrainingStatus:
    """训练状态测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert TrainingStatus.NOT_STARTED.value == "not_started"
        assert TrainingStatus.IN_PROGRESS.value == "in_progress"
        assert TrainingStatus.COMPLETED.value == "completed"


class TestTrainingProgress:
    """训练进度测试."""

    def test_creation(self) -> None:
        """测试创建."""
        progress = TrainingProgress(
            current_day=30,
            total_days=90,
            current_maturity=0.5,
            target_maturity=0.8,
        )
        assert progress.days_remaining == 60
        assert progress.maturity_gap == 0.3


class TestTrainingSession:
    """训练会话测试."""

    def test_creation(self) -> None:
        """测试创建."""
        session = TrainingSession(
            session_id="test-001",
            strategy_id="test",
            started_at=datetime.now(),
        )
        assert session.session_id == "test-001"
        assert session.status == TrainingStatus.NOT_STARTED

    def test_to_dict(self) -> None:
        """测试转字典."""
        session = TrainingSession(
            session_id="test-001",
            strategy_id="test",
            started_at=datetime.now(),
        )
        d = session.to_dict()
        assert d["session_id"] == "test-001"


class TestTrainingMonitor:
    """训练监控器测试."""

    def test_create_session(self) -> None:
        """测试创建会话."""
        monitor = TrainingMonitor()
        session = monitor.create_session("test")
        assert session.strategy_id == "test"
        assert session.status == TrainingStatus.NOT_STARTED

    def test_start_session(self) -> None:
        """测试开始会话."""
        monitor = TrainingMonitor()
        session = monitor.create_session("test")
        monitor.start_session(session.session_id)
        updated = monitor.get_session(session.session_id)
        assert updated.status == TrainingStatus.IN_PROGRESS

    def test_get_session(self) -> None:
        """测试获取会话."""
        monitor = TrainingMonitor()
        session = monitor.create_session("test")
        retrieved = monitor.get_session(session.session_id)
        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self) -> None:
        """测试获取不存在的会话."""
        monitor = TrainingMonitor()
        with pytest.raises(KeyError):
            monitor.get_session("unknown")

    def test_list_sessions(self) -> None:
        """测试列出会话."""
        monitor = TrainingMonitor()
        monitor.create_session("test1")
        monitor.create_session("test2")
        sessions = monitor.list_sessions()
        assert len(sessions) == 2

    def test_record_progress(self) -> None:
        """测试记录进度."""
        monitor = TrainingMonitor()
        session = monitor.create_session("test")
        monitor.start_session(session.session_id)

        record = TrainingRecord(
            date=datetime.now().date(),
            returns=0.01,
            sharpe=1.5,
            max_drawdown=0.05,
            win_rate=0.6,
            trades=100,
        )
        monitor.record_progress(session.session_id, record)

        updated = monitor.get_session(session.session_id)
        assert len(updated.history.records) == 1

    def test_get_progress(self) -> None:
        """测试获取进度."""
        monitor = TrainingMonitor()
        session = monitor.create_session("test")
        monitor.start_session(session.session_id)

        progress = monitor.get_progress(session.session_id)
        assert progress.current_day >= 0


class TestExperimentalModuleImports:
    """测试模块导入."""

    def test_import_from_experimental(self) -> None:
        """测试从experimental模块导入."""
        from src.strategy.experimental import (
            MaturityEvaluator,
            TrainingGate,
            TrainingMonitor,
        )

        assert MaturityEvaluator is not None
        assert TrainingGate is not None
        assert TrainingMonitor is not None
