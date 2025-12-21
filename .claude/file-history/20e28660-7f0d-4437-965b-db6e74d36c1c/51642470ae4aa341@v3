"""实验性策略模块测试 (军规级 v4.0)."""

from __future__ import annotations

from datetime import datetime

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityLevel,
    MaturityScore,
    TrainingHistory,
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
            reason="Good",
        )
        assert score.weighted_score == 0.2

    def test_is_passing(self) -> None:
        """测试通过判断."""
        passing = MaturityScore("test", 0.7, 0.1, {}, "")
        failing = MaturityScore("test", 0.5, 0.1, {}, "")
        assert passing.is_passing is True
        assert failing.is_passing is False


class TestTrainingHistory:
    """训练历史测试."""

    def test_creation(self) -> None:
        """测试创建."""
        history = TrainingHistory(strategy_id="test", start_date=datetime.now())
        assert history.strategy_id == "test"

    def test_training_days(self) -> None:
        """测试训练天数."""
        history = TrainingHistory(
            strategy_id="test",
            start_date=datetime.now(),
            daily_returns=[0.01] * 50,
        )
        assert history.training_days == 50


class TestMaturityEvaluator:
    """成熟度评估器测试."""

    def test_evaluate_empty(self) -> None:
        """测试空历史评估."""
        evaluator = MaturityEvaluator()
        history = TrainingHistory(strategy_id="test", start_date=datetime.now())
        report = evaluator.evaluate(history)
        assert report.is_mature is False

    def test_evaluate_with_data(self) -> None:
        """测试有数据的评估."""
        evaluator = MaturityEvaluator()
        history = TrainingHistory(
            strategy_id="test",
            start_date=datetime.now(),
            daily_returns=[0.005] * 100,
            sharpe_ratio=2.0,
            max_drawdown=0.05,
            win_rate=0.6,
        )
        report = evaluator.evaluate(history)
        assert report.strategy_id == "test"


class TestActivationStatus:
    """启用状态测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert ActivationStatus.TRAINING.value == "training"
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
            reasons=["Not enough"],
            report=None,
            requires_manual_approval=False,
        )
        text = decision.to_display()
        assert "TRAINING" in text


class TestTrainingGateConfig:
    """训练门禁配置测试."""

    def test_creation(self) -> None:
        """测试创建."""
        config = TrainingGateConfig()
        assert config.min_training_days == 90


class TestTrainingGate:
    """训练门禁测试."""

    def test_check_activation(self) -> None:
        """测试检查启用."""
        evaluator = MaturityEvaluator()
        gate = TrainingGate(evaluator)
        history = TrainingHistory(
            strategy_id="test",
            start_date=datetime.now(),
            daily_returns=[0.01] * 10,
        )
        decision = gate.check_activation(history)
        assert decision.allowed is False


class TestTrainingStatus:
    """训练状态测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert TrainingStatus.NOT_STARTED.value == "not_started"
        assert TrainingStatus.RUNNING.value == "running"
        assert TrainingStatus.COMPLETED.value == "completed"


class TestTrainingSession:
    """训练会话测试."""

    def test_creation(self) -> None:
        """测试创建."""
        session = TrainingSession(
            session_id="test-001",
            strategy_id="test",
            strategy_name="TestStrategy",
            strategy_type="experimental",
            start_time=datetime.now(),
        )
        assert session.session_id == "test-001"
        assert session.status == TrainingStatus.NOT_STARTED

    def test_to_dict(self) -> None:
        """测试转字典."""
        session = TrainingSession(
            session_id="test-001",
            strategy_id="test",
            strategy_name="TestStrategy",
            strategy_type="experimental",
            start_time=datetime.now(),
        )
        d = session.to_dict()
        assert d["session_id"] == "test-001"


class TestTrainingMonitor:
    """训练监控器测试."""

    def test_creation(self) -> None:
        """测试创建."""
        monitor = TrainingMonitor()
        assert monitor is not None

    def test_get_session_not_found(self) -> None:
        """测试获取不存在的会话."""
        monitor = TrainingMonitor()
        result = monitor.get_session("unknown")
        assert result is None


class TestExperimentalModuleImports:
    """测试模块导入."""

    def test_import(self) -> None:
        """测试从experimental模块导入."""
        from src.strategy.experimental import (
            MaturityEvaluator,
            TrainingGate,
            TrainingMonitor,
        )

        assert MaturityEvaluator is not None
        assert TrainingGate is not None
        assert TrainingMonitor is not None
