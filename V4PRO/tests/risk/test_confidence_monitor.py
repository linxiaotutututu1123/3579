"""置信度监控模块测试.

V4PRO Platform - 置信度监控系统测试
军规覆盖: M3(完整审计), M9(错误上报), M19(风险归因)

测试场景:
- K53: CONFIDENCE.MONITOR - 置信度监控
- K54: CONFIDENCE.ALERT - 置信度告警
- K55: CONFIDENCE.HEALTH - 健康状态集成
"""

from __future__ import annotations

import pytest

from src.monitoring.health import HealthChecker, HealthState
from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceContext,
    ConfidenceLevel,
    TaskType,
)
from src.risk.confidence_monitor import (
    AlertRecord,
    ConfidenceMonitor,
    ConfidenceMonitorConfig,
    create_confidence_monitor,
    quick_monitor_check,
)


class TestConfidenceMonitorConfig:
    """ConfidenceMonitorConfig 测试类."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = ConfidenceMonitorConfig()

        assert config.low_confidence_threshold == 0.70
        assert config.alert_on_decline is True
        assert config.decline_window == 5
        assert config.alert_cooldown_seconds == 300.0
        assert config.dingtalk_config is None
        assert config.enable_health_check is True

    def test_validate_valid_config(self) -> None:
        """测试有效配置验证."""
        config = ConfidenceMonitorConfig(
            low_confidence_threshold=0.75,
            decline_window=3,
            alert_cooldown_seconds=60.0,
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_threshold(self) -> None:
        """测试无效阈值验证."""
        config = ConfidenceMonitorConfig(low_confidence_threshold=1.5)
        errors = config.validate()
        assert any("low_confidence_threshold" in e for e in errors)

    def test_validate_invalid_decline_window(self) -> None:
        """测试无效下降窗口验证."""
        config = ConfidenceMonitorConfig(decline_window=1)
        errors = config.validate()
        assert any("decline_window" in e for e in errors)


class TestAlertRecord:
    """AlertRecord 测试类."""

    def test_create_record(self) -> None:
        """测试创建告警记录."""
        record = AlertRecord(
            alert_type="LOW_CONFIDENCE",
            confidence_score=0.65,
            message="置信度过低",
        )

        assert record.alert_type == "LOW_CONFIDENCE"
        assert record.confidence_score == 0.65
        assert record.timestamp != ""
        assert record.sent_successfully is False

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        record = AlertRecord(
            alert_type="DECLINING_TREND",
            confidence_score=0.72,
            message="趋势下降",
            metadata={"window": 5},
        )

        d = record.to_dict()
        assert d["alert_type"] == "DECLINING_TREND"
        assert d["confidence_score"] == 0.72
        assert d["metadata"]["window"] == 5


class TestConfidenceMonitor:
    """ConfidenceMonitor 测试类."""

    def test_init_default_config(self) -> None:
        """测试默认配置初始化."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)

        assert monitor.assessor is assessor
        assert monitor.config.low_confidence_threshold == 0.70

    def test_check_and_alert_low_confidence(self) -> None:
        """测试低置信度告警 (K54)."""
        assessor = ConfidenceAssessor()
        config = ConfidenceMonitorConfig(
            low_confidence_threshold=0.70,
            alert_cooldown_seconds=0,  # 禁用冷却
        )
        monitor = ConfidenceMonitor(assessor, config)

        # 低置信度上下文
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=False,
            architecture_verified=False,
            has_official_docs=False,
        )
        result = assessor.assess(context)

        alert_sent = monitor.check_and_alert(result)

        assert alert_sent is True
        assert len(monitor.get_alert_history()) >= 1

    def test_check_and_alert_high_confidence_no_alert(self) -> None:
        """测试高置信度不触发告警."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)

        # 高置信度上下文
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )
        result = assessor.assess(context)

        alert_sent = monitor.check_and_alert(result)

        assert alert_sent is False

    def test_alert_cooldown(self) -> None:
        """测试告警冷却."""
        assessor = ConfidenceAssessor()
        config = ConfidenceMonitorConfig(
            low_confidence_threshold=0.70,
            alert_cooldown_seconds=1000,  # 长冷却时间
        )
        monitor = ConfidenceMonitor(assessor, config)

        # 低置信度上下文
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=False,
        )
        result = assessor.assess(context)

        # 第一次应该发送
        alert_sent1 = monitor.check_and_alert(result)
        # 第二次应该被冷却
        alert_sent2 = monitor.check_and_alert(result)

        assert alert_sent1 is True
        assert alert_sent2 is False

    def test_declining_trend_detection(self) -> None:
        """测试下降趋势检测."""
        assessor = ConfidenceAssessor()
        config = ConfidenceMonitorConfig(
            decline_window=3,
            alert_on_decline=True,
            alert_cooldown_seconds=0,
        )
        monitor = ConfidenceMonitor(assessor, config)

        # 模拟置信度下降序列
        contexts = [
            ConfidenceContext(
                task_type=TaskType.STRATEGY_EXECUTION,
                duplicate_check_complete=True,
                architecture_verified=True,
                has_official_docs=True,
                has_oss_reference=True,
                root_cause_identified=True,
            ),
            ConfidenceContext(
                task_type=TaskType.STRATEGY_EXECUTION,
                duplicate_check_complete=True,
                architecture_verified=True,
                has_official_docs=True,
                has_oss_reference=False,
                root_cause_identified=True,
            ),
            ConfidenceContext(
                task_type=TaskType.STRATEGY_EXECUTION,
                duplicate_check_complete=True,
                architecture_verified=True,
                has_official_docs=False,
                has_oss_reference=False,
                root_cause_identified=False,
            ),
        ]

        for ctx in contexts:
            result = assessor.assess(ctx)
            monitor.check_and_alert(result)

        # 应该检测到下降趋势
        stats = monitor.get_statistics()
        assert stats["alert_stats"]["total_alerts"] >= 1

    def test_get_health_status(self) -> None:
        """测试获取健康状态 (K55)."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)

        # 进行一些评估
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )
        for _ in range(5):
            result = assessor.assess(context)
            monitor.check_and_alert(result)

        status = monitor.get_health_status()

        assert status.component == "confidence"
        assert status.state in (HealthState.HEALTHY, HealthState.UNKNOWN)

    def test_register_with_health_checker(self) -> None:
        """测试注册到健康检查器 (K55)."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)
        checker = HealthChecker()

        monitor.register_with_health_checker(checker)

        assert "confidence" in checker.components

    def test_unregister_from_health_checker(self) -> None:
        """测试从健康检查器注销."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)
        checker = HealthChecker()

        monitor.register_with_health_checker(checker)
        monitor.unregister_from_health_checker(checker)

        assert "confidence" not in checker.components

    def test_get_statistics(self) -> None:
        """测试获取统计信息."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)

        stats = monitor.get_statistics()

        assert "assessor_stats" in stats
        assert "trend_analysis" in stats
        assert "alert_stats" in stats
        assert "config" in stats

    def test_reset(self) -> None:
        """测试重置."""
        assessor = ConfidenceAssessor()
        config = ConfidenceMonitorConfig(alert_cooldown_seconds=0)
        monitor = ConfidenceMonitor(assessor, config)

        # 进行一些评估和告警
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)
        result = assessor.assess(context)
        monitor.check_and_alert(result)

        # 重置
        monitor.reset()

        assert len(monitor.get_alert_history()) == 0
        stats = monitor.get_statistics()
        assert stats["alert_stats"]["total_alerts"] == 0


class TestConvenienceFunctions:
    """便捷函数测试类."""

    def test_create_confidence_monitor(self) -> None:
        """测试创建监控器."""
        monitor = create_confidence_monitor(
            low_threshold=0.75,
        )

        assert monitor.config.low_confidence_threshold == 0.75
        assert monitor.config.dingtalk_config is None

    def test_create_confidence_monitor_with_assessor(self) -> None:
        """测试使用指定评估器创建监控器."""
        assessor = ConfidenceAssessor(high_threshold=0.95)
        monitor = create_confidence_monitor(assessor=assessor)

        assert monitor.assessor is assessor

    def test_quick_monitor_check_low(self) -> None:
        """测试快速监控检查 (低置信度)."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=False,
            architecture_verified=False,
        )
        result = assessor.assess(context)

        check = quick_monitor_check(result, threshold=0.70)

        assert check["is_low"] is True
        assert check["is_critical"] is True
        assert check["needs_attention"] is True

    def test_quick_monitor_check_high(self) -> None:
        """测试快速监控检查 (高置信度)."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )
        result = assessor.assess(context)

        check = quick_monitor_check(result, threshold=0.70)

        assert check["is_low"] is False
        assert check["is_critical"] is False
        assert check["needs_attention"] is False


class TestEdgeCases:
    """边界情况测试类."""

    def test_empty_alert_history(self) -> None:
        """测试空告警历史."""
        assessor = ConfidenceAssessor()
        monitor = ConfidenceMonitor(assessor)

        history = monitor.get_alert_history()
        assert len(history) == 0

    def test_health_check_disabled(self) -> None:
        """测试健康检查禁用."""
        assessor = ConfidenceAssessor()
        config = ConfidenceMonitorConfig(enable_health_check=False)
        monitor = ConfidenceMonitor(assessor, config)
        checker = HealthChecker()

        monitor.register_with_health_checker(checker)

        # 应该不会注册
        assert "confidence" not in checker.components


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
