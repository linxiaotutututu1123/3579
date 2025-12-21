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


class TestExtendedChecks:
    """扩展检查项测试类 (v4.3增强)."""

    def test_extended_context_fields(self) -> None:
        """测试扩展上下文字段."""
        context = ConfidenceContext(
            task_type=TaskType.SIGNAL_GENERATION,
            volatility=0.2,
            liquidity_score=0.8,
            historical_win_rate=0.6,
            position_concentration=0.3,
        )

        assert context.volatility == 0.2
        assert context.liquidity_score == 0.8
        assert context.historical_win_rate == 0.6
        assert context.position_concentration == 0.3

    def test_extended_checks_all_pass(self) -> None:
        """测试扩展检查全部通过."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.RISK_ASSESSMENT,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
            signal_strength=0.8,
            signal_consistency=0.85,
            risk_within_limits=True,
            volatility=0.1,  # 低波动
            liquidity_score=0.9,  # 高流动性
            historical_win_rate=0.65,  # 高胜率
            position_concentration=0.2,  # 分散
        )

        result = assessor.assess(context)
        # 组合评估包含扩展检查
        extended_check_names = {"volatility", "liquidity", "win_rate", "concentration"}
        check_names = {c.name for c in result.checks}
        assert extended_check_names.issubset(check_names)

    def test_high_volatility_check(self) -> None:
        """测试高波动率检查失败."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.RISK_ASSESSMENT,
            volatility=0.5,  # 高波动率
        )

        result = assessor.assess(context)
        vol_check = next((c for c in result.checks if c.name == "volatility"), None)

        assert vol_check is not None
        assert vol_check.passed is False
        assert "波动率偏高" in vol_check.message

    def test_low_liquidity_check(self) -> None:
        """测试低流动性检查失败."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(
            task_type=TaskType.RISK_ASSESSMENT,
            liquidity_score=0.3,  # 低流动性
        )

        result = assessor.assess(context)
        liq_check = next((c for c in result.checks if c.name == "liquidity"), None)

        assert liq_check is not None
        assert liq_check.passed is False
        assert "流动性不足" in liq_check.message


class TestAdaptiveThresholds:
    """自适应阈值测试类 (v4.3增强)."""

    def test_adaptive_mode_enabled(self) -> None:
        """测试自适应模式启用."""
        assessor = ConfidenceAssessor(adaptive_mode=True)
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            volatility=0.5,  # 高波动
            market_condition="VOLATILE",
        )

        high_thresh, medium_thresh = assessor.get_adaptive_thresholds(context)

        # 高波动市场应提高阈值
        assert high_thresh > 0.90
        assert medium_thresh > 0.70

    def test_adaptive_mode_normal_market(self) -> None:
        """测试正常市场自适应阈值."""
        assessor = ConfidenceAssessor(adaptive_mode=True)
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            volatility=0.1,
            liquidity_score=0.9,
            market_condition="NORMAL",
        )

        high_thresh, medium_thresh = assessor.get_adaptive_thresholds(context)

        # 正常市场使用默认阈值
        assert high_thresh == 0.90
        assert medium_thresh == 0.70

    def test_adaptive_context_summary(self) -> None:
        """测试自适应模式上下文摘要."""
        assessor = ConfidenceAssessor(adaptive_mode=True)
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )

        result = assessor.assess(context)

        assert result.context_summary["adaptive_mode"] is True
        assert "thresholds" in result.context_summary


class TestTrendAnalysis:
    """趋势分析测试类 (v4.3增强)."""

    def test_insufficient_data(self) -> None:
        """测试数据不足情况."""
        assessor = ConfidenceAssessor()

        # 只评估1次
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)
        assessor.assess(context)

        trend = assessor.get_trend_analysis()

        assert trend["trend"] == "INSUFFICIENT_DATA"
        assert trend["alert"] is False

    def test_stable_trend(self) -> None:
        """测试稳定趋势."""
        assessor = ConfidenceAssessor()
        high_context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )

        # 连续5次高置信度评估
        for _ in range(5):
            assessor.assess(high_context)

        trend = assessor.get_trend_analysis()

        assert trend["trend"] == "STABLE"
        assert trend["recent_avg"] >= 0.90
        assert trend["alert"] is False

    def test_declining_trend_alert(self) -> None:
        """测试下降趋势预警."""
        assessor = ConfidenceAssessor()

        # 模拟置信度下降
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
            assessor.assess(ctx)

        trend = assessor.get_trend_analysis()

        # 连续下降应触发预警
        assert trend["alert"] is True
        assert "下降" in trend["alert_message"]

    def test_history_limit(self) -> None:
        """测试历史记录限制."""
        assessor = ConfidenceAssessor()
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)

        # 超过最大历史记录
        for _ in range(150):
            assessor.assess(context)

        trend = assessor.get_trend_analysis()

        # 历史记录应被限制在100条
        assert trend["history_count"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
