"""训练监控器增强测试 (军规级 v4.0)."""

from __future__ import annotations

from datetime import datetime

from src.strategy.experimental.training_monitor import (
    TrainingMonitor,
    TrainingProgress,
    TrainingSession,
    TrainingStatus,
)


class TestTrainingStatusEnum:
    """训练状态枚举测试."""

    def test_all_status_values(self) -> None:
        """测试所有状态值."""
        assert TrainingStatus.NOT_STARTED.value == "not_started"
        assert TrainingStatus.RUNNING.value == "running"
        assert TrainingStatus.PAUSED.value == "paused"
        assert TrainingStatus.COMPLETED.value == "completed"
        assert TrainingStatus.FAILED.value == "failed"
        assert TrainingStatus.CANCELLED.value == "cancelled"


class TestTrainingSessionEnhanced:
    """训练会话增强测试."""

    def test_to_dict_full(self) -> None:
        """测试完整转字典."""
        session = TrainingSession(
            session_id="test-123",
            strategy_id="strat-1",
            strategy_name="TestStrategy",
            strategy_type="experimental",
            start_time=datetime(2025, 1, 1, 10, 0, 0),
            status=TrainingStatus.RUNNING,
            last_update=datetime(2025, 1, 2, 10, 0, 0),
            notes=["note1", "note2"],
        )
        d = session.to_dict()
        assert d["session_id"] == "test-123"
        assert d["strategy_name"] == "TestStrategy"
        assert d["status"] == "running"
        assert "2025-01-01" in d["start_time"]
        assert d["training_days"] == 0  # No history
        assert len(d["notes"]) == 2

    def test_to_dict_no_last_update(self) -> None:
        """测试无最后更新时间."""
        session = TrainingSession(
            session_id="test-123",
            strategy_id="strat-1",
            strategy_name="TestStrategy",
            strategy_type="experimental",
            start_time=datetime(2025, 1, 1),
        )
        d = session.to_dict()
        assert d["last_update"] is None


class TestTrainingMonitorEnhanced:
    """训练监控器增强测试."""

    def test_start_session(self) -> None:
        """测试开始会话."""
        monitor = TrainingMonitor()
        session = monitor.start_session(
            strategy_id="strat-1",
            strategy_name="TestStrategy",
            strategy_type="experimental",
        )
        assert session.session_id is not None
        assert session.status == TrainingStatus.RUNNING
        assert session.history is not None

    def test_record_daily_updates_statistics(self) -> None:
        """测试记录每日数据更新统计."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录多天数据
        for i in range(25):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01 if i % 2 == 0 else -0.005,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.02,
            )

        assert session.history is not None
        assert len(session.history.daily_returns) == 25
        assert session.history.sharpe_ratio != 0  # 应该被计算

    def test_record_daily_no_session(self) -> None:
        """测试无会话时记录."""
        monitor = TrainingMonitor()
        # 不应该抛出异常
        monitor.record_daily("nonexistent", 0.01, 100, 1, "trending", -0.02)

    def test_get_progress_basic(self) -> None:
        """测试获取基本进度."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录一些数据
        for _ in range(30):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.01,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None
        assert progress.days_elapsed == 30
        assert progress.days_remaining == 60  # 90 - 30

    def test_get_progress_no_session(self) -> None:
        """测试无会话时获取进度."""
        monitor = TrainingMonitor()
        progress = monitor.get_progress("nonexistent")
        assert progress is None

    def test_pause_and_resume_session(self) -> None:
        """测试暂停和恢复会话."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 暂停
        result = monitor.pause_session(session.session_id)
        assert result is True
        assert session.status == TrainingStatus.PAUSED

        # 再次暂停应该失败
        result = monitor.pause_session(session.session_id)
        assert result is False

        # 恢复
        result = monitor.resume_session(session.session_id)
        assert result is True
        assert session.status == TrainingStatus.RUNNING

        # 再次恢复应该失败
        result = monitor.resume_session(session.session_id)
        assert result is False

    def test_pause_nonexistent_session(self) -> None:
        """测试暂停不存在的会话."""
        monitor = TrainingMonitor()
        assert monitor.pause_session("nonexistent") is False

    def test_resume_nonexistent_session(self) -> None:
        """测试恢复不存在的会话."""
        monitor = TrainingMonitor()
        assert monitor.resume_session("nonexistent") is False

    def test_cancel_session(self) -> None:
        """测试取消会话."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        result = monitor.cancel_session(session.session_id, "测试取消")
        assert result is True
        assert session.status == TrainingStatus.CANCELLED
        assert "测试取消" in session.notes[0]

    def test_cancel_nonexistent_session(self) -> None:
        """测试取消不存在的会话."""
        monitor = TrainingMonitor()
        assert monitor.cancel_session("nonexistent", "reason") is False

    def test_add_note(self) -> None:
        """测试添加备注."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        result = monitor.add_note(session.session_id, "这是测试备注")
        assert result is True
        assert len(session.notes) == 1
        assert "测试备注" in session.notes[0]

    def test_add_note_nonexistent_session(self) -> None:
        """测试给不存在会话添加备注."""
        monitor = TrainingMonitor()
        assert monitor.add_note("nonexistent", "note") is False

    def test_get_all_sessions(self) -> None:
        """测试获取所有会话."""
        monitor = TrainingMonitor()
        monitor.start_session("s1", "Test1", "exp")
        monitor.start_session("s2", "Test2", "exp")
        monitor.start_session("s3", "Test3", "exp")

        sessions = monitor.get_all_sessions()
        assert len(sessions) == 3

    def test_get_session(self) -> None:
        """测试获取单个会话."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        found = monitor.get_session(session.session_id)
        assert found is not None
        assert found.strategy_id == "s1"

    def test_export_report(self) -> None:
        """测试导出报告."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录一些数据
        for _ in range(20):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.01,
            )

        report = monitor.export_report(session.session_id)
        assert report is not None
        assert "session" in report
        assert "progress" in report
        assert "maturity_report" in report

    def test_export_report_nonexistent(self) -> None:
        """测试导出不存在会话的报告."""
        monitor = TrainingMonitor()
        report = monitor.export_report("nonexistent")
        assert report is None


class TestTrainingMonitorTrend:
    """趋势计算测试."""

    def test_calculate_trend_improving(self) -> None:
        """测试改善趋势."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 模拟进度历史（递增）
        for i in range(20):
            monitor._progress_history[session.session_id].append(0.3 + i * 0.02)

        trend = monitor._calculate_trend(session.session_id)
        assert trend == "improving"

    def test_calculate_trend_declining(self) -> None:
        """测试下降趋势."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 模拟进度历史（递减）
        for i in range(20):
            monitor._progress_history[session.session_id].append(0.7 - i * 0.02)

        trend = monitor._calculate_trend(session.session_id)
        assert trend == "declining"

    def test_calculate_trend_stable(self) -> None:
        """测试稳定趋势."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 模拟进度历史（稳定）
        for _ in range(20):
            monitor._progress_history[session.session_id].append(0.5)

        trend = monitor._calculate_trend(session.session_id)
        assert trend == "stable"

    def test_calculate_trend_insufficient_data(self) -> None:
        """测试数据不足时的趋势."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 只有少量数据
        monitor._progress_history[session.session_id] = [0.3, 0.4]

        trend = monitor._calculate_trend(session.session_id)
        assert trend == "stable"


class TestTrainingMonitorAlerts:
    """告警生成测试."""

    def test_generate_alerts_low_score(self) -> None:
        """测试低分告警."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录少量数据（低分）
        for _ in range(5):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.001,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.01,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None
        # 应该有告警（训练天数少）
        assert len(progress.alerts) > 0

    def test_generate_alerts_long_training_low_score(self) -> None:
        """测试长时间训练但低分的告警."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录90天数据但表现差
        for _ in range(95):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.0001,  # 非常低的收益
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.3,  # 高回撤
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None
        # 应该有关于策略逻辑的告警
        alerts_text = " ".join(progress.alerts)
        assert "90天" in alerts_text or "未达标" in alerts_text or "得分" in alerts_text


class TestTrainingProgressDisplay:
    """训练进度显示测试."""

    def test_display_basic(self) -> None:
        """测试基本显示."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "TestStrategy", "experimental")

        for _ in range(30):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.02,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None

        display = progress.display()
        assert "TestStrategy" in display
        assert "experimental" in display
        assert "训练进度" in display

    def test_display_all_statuses(self) -> None:
        """测试所有状态的显示文本."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        for _ in range(20):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.02,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None

        # 测试不同状态
        for status in TrainingStatus:
            session.status = status
            display = progress.display()
            assert len(display) > 0

    def test_progress_bar_methods(self) -> None:
        """测试进度条方法."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        for _ in range(20):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.01,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.02,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None

        big_bar = progress._big_progress_bar(0.5)
        assert "[" in big_bar
        assert "]" in big_bar

        mini_bar = progress._mini_progress_bar(0.5)
        assert "█" in mini_bar or "░" in mini_bar

    def test_display_reached_threshold(self) -> None:
        """测试达到门槛时的显示."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录足够多的好数据
        for _ in range(100):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.02,
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.01,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None
        display = progress.display()
        # 应该有相关内容
        assert "天" in display


class TestTrainingMonitorETA:
    """ETA计算测试."""

    def test_eta_with_progress_trend(self) -> None:
        """测试有进度趋势时的ETA."""
        monitor = TrainingMonitor()
        session = monitor.start_session("s1", "Test", "exp")

        # 记录足够数据以计算ETA
        for i in range(100):
            monitor.record_daily(
                session_id=session.session_id,
                daily_return=0.005 + i * 0.0001,  # 递增收益
                daily_position=100.0,
                daily_signal=1.0,
                market_regime="trending",
                drawdown=-0.02,
            )

        progress = monitor.get_progress(session.session_id)
        assert progress is not None
        # eta可能为None或datetime，取决于是否达标
        # 重要的是不会抛出异常
