"""置信度评估模块测试.

V4PRO Platform - 置信度评估系统测试
军规覆盖: M3(完整审计), M19(风险归因)

测试场景:
- K50: CONFIDENCE.PRE_EXEC - 预执行置信度检查
- K51: CONFIDENCE.SIGNAL - 信号置信度评估
- K52: CONFIDENCE.AUDIT - 置信度审计追踪
"""

from __future__ import annotations

import pytest

from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceContext,
    ConfidenceLevel,
    TaskType,
    assess_pre_execution,
    assess_signal,
    format_confidence_report,
)


class TestConfidenceAssessor:
    """ConfidenceAssessor 测试类."""

    def test_high_confidence_pre_execution(self) -> None:
        """测试高置信度预执行评估 (K50)."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            task_name="test_strategy",
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )

        result = assessor.assess(context)

        assert result.score >= 0.90
        assert result.level == ConfidenceLevel.HIGH
        assert result.can_proceed is True
        assert len(result.passed_checks) == 5
        assert len(result.failed_checks) == 0

    def test_medium_confidence_pre_execution(self) -> None:
        """测试中等置信度预执行评估."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            task_name="test_strategy",
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=False,  # 缺少OSS参考
            root_cause_identified=False,  # 未识别根因
        )

        result = assessor.assess(context)

        assert 0.70 <= result.score < 0.90
        assert result.level == ConfidenceLevel.MEDIUM
        assert result.can_proceed is False
        assert len(result.failed_checks) == 2

    def test_low_confidence_pre_execution(self) -> None:
        """测试低置信度预执行评估."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            task_name="test_strategy",
            duplicate_check_complete=False,
            architecture_verified=False,
            has_official_docs=False,
            has_oss_reference=False,
            root_cause_identified=False,
        )

        result = assessor.assess(context)

        assert result.score < 0.70
        assert result.level == ConfidenceLevel.LOW
        assert result.can_proceed is False
        assert len(result.passed_checks) == 0

    def test_high_confidence_signal(self) -> None:
        """测试高置信度信号评估 (K51)."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.SIGNAL_GENERATION,
            symbol="rb2501",
            strategy_id="kalman_arb",
            signal_strength=0.8,
            signal_consistency=0.85,
            market_condition="NORMAL",
            risk_within_limits=True,
        )

        result = assessor.assess(context)

        assert result.score >= 0.90
        assert result.level == ConfidenceLevel.HIGH
        assert result.can_proceed is True

    def test_low_confidence_signal_weak_strength(self) -> None:
        """测试低信号强度导致的低置信度."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.SIGNAL_GENERATION,
            symbol="rb2501",
            strategy_id="test_strategy",
            signal_strength=0.3,  # 弱信号
            signal_consistency=0.4,  # 低一致性
            market_condition="VOLATILE",  # 异常市场
            risk_within_limits=False,  # 超出风险限制
        )

        result = assessor.assess(context)

        assert result.score < 0.70
        assert result.level == ConfidenceLevel.LOW
        assert result.can_proceed is False

    def test_audit_dict_format(self) -> None:
        """测试审计日志格式 (K52, M3)."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            task_name="audit_test",
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )

        result = assessor.assess(context)
        audit_dict = result.to_audit_dict()

        assert "event_type" in audit_dict
        assert audit_dict["event_type"] == "CONFIDENCE_ASSESSMENT"
        assert "score" in audit_dict
        assert "level" in audit_dict
        assert "checks" in audit_dict
        assert "timestamp" in audit_dict
        assert isinstance(audit_dict["checks"], list)

    def test_statistics_tracking(self) -> None:
        """测试统计信息跟踪."""
        assessor = ConfidenceAssessor()

        # 高置信度
        high_context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )
        assessor.assess(high_context)

        # 低置信度
        low_context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=False,
            architecture_verified=False,
            has_official_docs=False,
            has_oss_reference=False,
            root_cause_identified=False,
        )
        assessor.assess(low_context)

        stats = assessor.get_statistics()

        assert stats["total_assessments"] == 2
        assert stats["high_confidence_count"] == 1
        assert stats["low_confidence_count"] == 1

    def test_custom_thresholds(self) -> None:
        """测试自定义阈值."""
        assessor = ConfidenceAssessor(
            high_threshold=0.95,
            medium_threshold=0.80,
        )
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=False,  # 85%分数
        )

        result = assessor.assess(context)

        # 85% < 95% 所以是中等置信度
        assert result.level == ConfidenceLevel.MEDIUM


class TestConvenienceFunctions:
    """便捷函数测试类."""

    def test_assess_pre_execution(self) -> None:
        """测试 assess_pre_execution 便捷函数."""
        result = assess_pre_execution(
            "test_task",
            duplicate_check=True,
            architecture_verified=True,
            has_docs=True,
            has_oss=True,
            root_cause=True,
        )

        assert result.score >= 0.90
        assert result.level == ConfidenceLevel.HIGH

    def test_assess_signal(self) -> None:
        """测试 assess_signal 便捷函数."""
        result = assess_signal(
            "rb2501",
            "kalman_arb",
            strength=0.8,
            consistency=0.85,
            market_condition="NORMAL",
            risk_ok=True,
        )

        assert result.score >= 0.90
        assert result.level == ConfidenceLevel.HIGH

    def test_format_confidence_report(self) -> None:
        """测试置信度报告格式化."""
        result = assess_pre_execution(
            "test_task",
            duplicate_check=True,
            architecture_verified=True,
            has_docs=True,
            has_oss=True,
            root_cause=True,
        )

        report = format_confidence_report(result)

        assert "置信度评估报告" in report
        assert "置信度:" in report
        assert "✅" in report


class TestConfidenceContext:
    """ConfidenceContext 测试类."""

    def test_default_values(self) -> None:
        """测试默认值."""
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)

        assert context.task_name == ""
        assert context.symbol == ""
        assert context.duplicate_check_complete is False
        assert context.signal_strength == 0.0
        assert context.market_condition == "NORMAL"
        assert context.risk_within_limits is True

    def test_all_task_types(self) -> None:
        """测试所有任务类型."""
        assessor = ConfidenceAssessor()

        for task_type in TaskType:
            context = ConfidenceContext(
                task_type=task_type,
                duplicate_check_complete=True,
                architecture_verified=True,
                has_official_docs=True,
                has_oss_reference=True,
                root_cause_identified=True,
                signal_strength=0.8,
                signal_consistency=0.85,
                risk_within_limits=True,
            )
            result = assessor.assess(context)
            assert result.score > 0


class TestConfidenceLevel:
    """ConfidenceLevel 测试类."""

    def test_level_values(self) -> None:
        """测试等级值."""
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"


class TestEdgeCases:
    """边界情况测试类."""

    def test_boundary_high_threshold(self) -> None:
        """测试高阈值边界 (正好90%)."""
        assessor = ConfidenceAssessor()
        # 4项通过 = 0.25 + 0.25 + 0.20 + 0.15 = 0.85
        # 5项通过 = 1.0
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )

        result = assessor.assess(context)
        assert result.level == ConfidenceLevel.HIGH

    def test_boundary_medium_threshold(self) -> None:
        """测试中等阈值边界 (正好70%)."""
        assessor = ConfidenceAssessor()
        # 3项通过 = 0.25 + 0.25 + 0.20 = 0.70
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=False,
            root_cause_identified=False,
        )

        result = assessor.assess(context)
        assert result.level == ConfidenceLevel.MEDIUM

    def test_reset_statistics(self) -> None:
        """测试统计重置."""
        assessor = ConfidenceAssessor()

        # 进行一些评估
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)
        assessor.assess(context)
        assessor.assess(context)

        # 重置
        assessor.reset_statistics()
        stats = assessor.get_statistics()

        assert stats["total_assessments"] == 0
        assert stats["high_confidence_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
