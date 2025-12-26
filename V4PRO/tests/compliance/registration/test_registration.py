"""
程序化交易备案模块测试 (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案

测试覆盖:
- RegistrationRegistry: 备案登记中心测试
- ComplianceValidator: 合规验证器测试
- RegulatoryReporter: 监管报送器测试
- OrderFrequencyMonitor: 订单频率监控器测试

军规验证:
- M3: 审计日志完整 - 验证审计回调被正确调用
- M7: 场景回放 - 验证数据可重放
- M17: 程序化合规 - 验证合规阈值检查

合规阈值测试 (D7-P1):
- 报撤单比例: <=50%
- 撤单频率: <=500次/秒
- 订单间隔: >=100ms
- 审计延迟: <=1s
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import pytest

from src.compliance.registration.registry import (
    RegistrationRegistry,
    RegistrationStatus,
    RegistrationInfo,
    StrategyRegistration,
    create_registration_registry,
)
from src.compliance.registration.validator import (
    ComplianceValidator,
    ComplianceValidatorConfig,
    ComplianceMetrics,
    OrderFrequencyMonitor,
    ValidationResult,
    ViolationLevel,
    ViolationType,
    create_compliance_validator,
)
from src.compliance.registration.reporter import (
    RegulatoryReporter,
    ReportType,
    ReportFormat,
    ReportStatus,
    create_regulatory_reporter,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def audit_events() -> list[dict[str, Any]]:
    """审计事件收集器."""
    return []


@pytest.fixture
def audit_callback(audit_events: list[dict[str, Any]]):
    """审计回调函数."""

    def callback(event: dict[str, Any]) -> None:
        audit_events.append(event)

    return callback


@pytest.fixture
def registry(audit_callback) -> RegistrationRegistry:
    """创建备案登记中心."""
    return RegistrationRegistry(audit_callback=audit_callback)


@pytest.fixture
def validator(audit_callback) -> ComplianceValidator:
    """创建合规验证器."""
    return ComplianceValidator(audit_callback=audit_callback)


@pytest.fixture
def reporter(registry, validator, audit_callback) -> RegulatoryReporter:
    """创建监管报送器."""
    return RegulatoryReporter(registry, validator, audit_callback=audit_callback)


# ============================================================
# RegistrationRegistry Tests
# ============================================================


class TestRegistrationRegistry:
    """备案登记中心测试."""

    def test_register_account_success(self, registry: RegistrationRegistry) -> None:
        """测试账户备案成功."""
        reg_info = registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
            contact_info="zhangsan@example.com",
        )

        assert reg_info is not None
        assert reg_info.account_id == "test_account_001"
        assert reg_info.account_type == "programmatic"
        assert reg_info.responsible_person == "Zhang San"
        assert reg_info.status == RegistrationStatus.PENDING
        assert reg_info.registration_id.startswith("REG-")

    def test_register_account_duplicate(self, registry: RegistrationRegistry) -> None:
        """测试重复账户备案."""
        registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        with pytest.raises(ValueError, match="已存在备案记录"):
            registry.register_account(
                account_id="test_account_001",
                account_type="programmatic",
                responsible_person="Li Si",
            )

    def test_register_strategy_success(self, registry: RegistrationRegistry) -> None:
        """测试策略注册成功."""
        registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        strategy = registry.register_strategy(
            account_id="test_account_001",
            strategy_id="trend_following_v1",
            strategy_type="TREND",
            strategy_name="Trend Following Strategy",
            description="A trend following strategy",
            version="1.0.0",
        )

        assert strategy is not None
        assert strategy.strategy_id == "trend_following_v1"
        assert strategy.account_id == "test_account_001"
        assert strategy.strategy_type == "TREND"
        assert strategy.is_active is True

    def test_register_strategy_no_account(self, registry: RegistrationRegistry) -> None:
        """测试无账户时注册策略."""
        with pytest.raises(ValueError, match="不存在备案记录"):
            registry.register_strategy(
                account_id="nonexistent_account",
                strategy_id="test_strategy",
                strategy_type="TREND",
            )

    def test_update_registration_status(self, registry: RegistrationRegistry) -> None:
        """测试更新备案状态."""
        registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        updated = registry.update_registration_status(
            account_id="test_account_001",
            new_status=RegistrationStatus.APPROVED,
            reason="审核通过",
            changed_by="Admin",
        )

        assert updated.status == RegistrationStatus.APPROVED
        assert updated.status_reason == "审核通过"
        assert updated.approved_at != ""

    def test_get_account_strategies(self, registry: RegistrationRegistry) -> None:
        """测试获取账户策略列表."""
        registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        registry.register_strategy(
            account_id="test_account_001",
            strategy_id="strategy_1",
            strategy_type="TREND",
        )
        registry.register_strategy(
            account_id="test_account_001",
            strategy_id="strategy_2",
            strategy_type="ARBITRAGE",
        )

        strategies = registry.get_account_strategies("test_account_001")
        assert len(strategies) == 2

    def test_audit_callback_called(
        self,
        registry: RegistrationRegistry,
        audit_events: list[dict[str, Any]],
    ) -> None:
        """测试审计回调被调用 (M3军规验证)."""
        registry.register_account(
            account_id="test_account_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        assert len(audit_events) >= 1
        event = audit_events[0]
        assert event["event_type"] == "REGISTRATION_CREATED"
        assert event["account_id"] == "test_account_001"
        assert "M3" in event["military_rules"]


# ============================================================
# OrderFrequencyMonitor Tests
# ============================================================


class TestOrderFrequencyMonitor:
    """订单频率监控器测试."""

    def test_record_order(self) -> None:
        """测试记录订单."""
        monitor = OrderFrequencyMonitor()

        monitor.record_order(
            event_type="submit",
            account_id="acc_001",
            strategy_id="strat_001",
            order_id="order_001",
        )

        assert monitor.total_orders == 1
        assert monitor.total_cancels == 0

    def test_cancel_ratio_calculation(self) -> None:
        """测试报撤单比例计算."""
        monitor = OrderFrequencyMonitor(window_seconds=5)
        now = datetime.now()  # noqa: DTZ005

        # 记录10个报单
        for i in range(10):
            monitor.record_order(
                event_type="submit",
                account_id="acc_001",
                strategy_id="strat_001",
                order_id=f"order_{i}",
                timestamp=now + timedelta(milliseconds=i * 100),
            )

        # 记录5个撤单
        for i in range(5):
            monitor.record_order(
                event_type="cancel",
                account_id="acc_001",
                strategy_id="strat_001",
                order_id=f"cancel_{i}",
                timestamp=now + timedelta(milliseconds=1000 + i * 100),
            )

        metrics = monitor.get_metrics(now + timedelta(seconds=2))
        # 撤单比例 = 5 / 15 = 33.3%
        assert 0.3 < metrics.cancel_ratio < 0.4

    def test_hft_detection(self) -> None:
        """测试高频交易检测."""
        monitor = OrderFrequencyMonitor(window_seconds=1)
        now = datetime.now()  # noqa: DTZ005

        # 记录300+个订单在1秒内 (超过300笔/秒阈值)
        for i in range(350):
            monitor.record_order(
                event_type="submit",
                account_id="acc_001",
                strategy_id="strat_001",
                order_id=f"order_{i}",
                timestamp=now + timedelta(milliseconds=i * 2),  # 每2ms一个订单
            )

        metrics = monitor.get_metrics(now + timedelta(milliseconds=700))
        assert metrics.is_hft is True


# ============================================================
# ComplianceValidator Tests
# ============================================================


class TestComplianceValidator:
    """合规验证器测试."""

    def test_validate_cancel_ratio_pass(self, validator: ComplianceValidator) -> None:
        """测试报撤单比例合规 (<=50%)."""
        metrics = ComplianceMetrics(
            cancel_ratio=0.4,  # 40% < 50%
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        assert result.is_valid is True
        # 应该没有报撤单比例违规
        cancel_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.CANCEL_RATIO_EXCEEDED
        ]
        assert len(cancel_violations) == 0

    def test_validate_cancel_ratio_fail(self, validator: ComplianceValidator) -> None:
        """测试报撤单比例超限 (>50%)."""
        metrics = ComplianceMetrics(
            cancel_ratio=0.6,  # 60% > 50%
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        cancel_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.CANCEL_RATIO_EXCEEDED
        ]
        assert len(cancel_violations) > 0

    def test_validate_cancel_freq_pass(self, validator: ComplianceValidator) -> None:
        """测试撤单频率合规 (<=500次/秒)."""
        metrics = ComplianceMetrics(
            cancel_freq_per_sec=300,  # 300次/秒 < 500次/秒
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        freq_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.CANCEL_FREQ_EXCEEDED
        ]
        assert len(freq_violations) == 0

    def test_validate_cancel_freq_fail(self, validator: ComplianceValidator) -> None:
        """测试撤单频率超限 (>500次/秒)."""
        metrics = ComplianceMetrics(
            cancel_freq_per_sec=600,  # 600次/秒 > 500次/秒
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        freq_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.CANCEL_FREQ_EXCEEDED
        ]
        assert len(freq_violations) > 0
        assert freq_violations[0].violation_level == ViolationLevel.CRITICAL

    def test_validate_order_interval_pass(self, validator: ComplianceValidator) -> None:
        """测试订单间隔合规 (>=100ms)."""
        metrics = ComplianceMetrics(
            avg_order_interval_ms=150,  # 150ms > 100ms
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        interval_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.ORDER_INTERVAL_TOO_SHORT
        ]
        assert len(interval_violations) == 0

    def test_validate_order_interval_fail(self, validator: ComplianceValidator) -> None:
        """测试订单间隔过短 (<100ms)."""
        metrics = ComplianceMetrics(
            avg_order_interval_ms=50,  # 50ms < 100ms
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        interval_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.ORDER_INTERVAL_TOO_SHORT
        ]
        assert len(interval_violations) > 0

    def test_validate_audit_delay_pass(self, validator: ComplianceValidator) -> None:
        """测试审计延迟合规 (<=1s)."""
        metrics = ComplianceMetrics(
            max_audit_delay_sec=0.5,  # 0.5s < 1s
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        delay_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.AUDIT_DELAY_EXCEEDED
        ]
        assert len(delay_violations) == 0

    def test_validate_audit_delay_fail(self, validator: ComplianceValidator) -> None:
        """测试审计延迟超限 (>1s)."""
        metrics = ComplianceMetrics(
            max_audit_delay_sec=1.5,  # 1.5s > 1s
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        delay_violations = [
            v
            for v in result.violations
            if v.violation_type == ViolationType.AUDIT_DELAY_EXCEEDED
        ]
        assert len(delay_violations) > 0

    def test_hft_detection_warning(self, validator: ComplianceValidator) -> None:
        """测试高频交易检测预警."""
        metrics = ComplianceMetrics(
            orders_per_sec=350,  # 350笔/秒 > 300笔/秒
            is_hft=True,
        )

        result = validator.validate_metrics(metrics, "acc_001", "strat_001")
        hft_warnings = [
            w for w in result.warnings if w.violation_type == ViolationType.HFT_DETECTED
        ]
        assert len(hft_warnings) > 0

    def test_record_and_validate(self, validator: ComplianceValidator) -> None:
        """测试记录订单并验证."""
        result = validator.record_order(
            event_type="submit",
            account_id="acc_001",
            strategy_id="strat_001",
            order_id="order_001",
        )

        assert result is not None
        assert "cancel_ratio" in result.metrics


# ============================================================
# RegulatoryReporter Tests
# ============================================================


class TestRegulatoryReporter:
    """监管报送器测试."""

    def test_generate_daily_report(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试生成日报送."""
        # 先注册账户
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        report = reporter.generate_daily_report("acc_001")

        assert report is not None
        assert report.report_type == ReportType.DAILY
        assert report.account_id == "acc_001"
        assert report.status == ReportStatus.PENDING
        assert report.report_id.startswith("RPT-")

    def test_generate_exception_report(self, reporter: RegulatoryReporter) -> None:
        """测试生成异常报送."""
        report = reporter.generate_exception_report(
            account_id="acc_001",
            exception_type="SYSTEM_ERROR",
            description="系统发生异常",
            strategy_id="strat_001",
            impact="暂停交易",
            action_taken="重启系统",
        )

        assert report is not None
        assert report.report_type == ReportType.EXCEPTION
        assert "exception_type" in report.content
        assert report.content["exception_type"] == "SYSTEM_ERROR"

    def test_generate_change_report(self, reporter: RegulatoryReporter) -> None:
        """测试生成变更报送."""
        report = reporter.generate_change_report(
            account_id="acc_001",
            change_type="STRATEGY_UPDATE",
            old_value="v1.0.0",
            new_value="v1.1.0",
            reason="Bug fix",
        )

        assert report is not None
        assert report.report_type == ReportType.CHANGE
        assert report.content["old_value"] == "v1.0.0"
        assert report.content["new_value"] == "v1.1.0"

    def test_submit_report(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试提交报送."""
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        report = reporter.generate_daily_report("acc_001")
        success = reporter.submit_report(report)

        assert success is True
        assert report.status == ReportStatus.SUBMITTED
        assert report.submitted_at != ""

    def test_export_json(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试导出JSON格式."""
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        report = reporter.generate_daily_report("acc_001")
        json_output = reporter.export_report(report, ReportFormat.JSON)

        assert json_output is not None
        assert "report_id" in json_output
        assert "acc_001" in json_output

    def test_export_xml(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试导出XML格式."""
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        report = reporter.generate_daily_report("acc_001")
        xml_output = reporter.export_report(report, ReportFormat.XML)

        assert xml_output is not None
        assert "<?xml version" in xml_output
        assert "<report>" in xml_output

    def test_get_pending_reports(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试获取待提交报送."""
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        reporter.generate_daily_report("acc_001")
        reporter.generate_exception_report(
            account_id="acc_001",
            exception_type="TEST",
            description="Test exception",
        )

        pending = reporter.get_pending_reports()
        assert len(pending) == 2

    def test_statistics(
        self, reporter: RegulatoryReporter, registry: RegistrationRegistry
    ) -> None:
        """测试统计信息."""
        registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )

        report = reporter.generate_daily_report("acc_001")
        reporter.submit_report(report)

        stats = reporter.get_statistics()
        assert stats["total_reports"] == 1
        assert stats["submit_count"] == 1
        assert stats["success_count"] == 1


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """集成测试."""

    def test_full_workflow(
        self,
        registry: RegistrationRegistry,
        validator: ComplianceValidator,
        reporter: RegulatoryReporter,
        audit_events: list[dict[str, Any]],
    ) -> None:
        """测试完整工作流程."""
        # 1. 注册账户
        reg_info = registry.register_account(
            account_id="acc_001",
            account_type="programmatic",
            responsible_person="Zhang San",
        )
        assert reg_info.status == RegistrationStatus.PENDING

        # 2. 审核通过
        registry.update_registration_status(
            account_id="acc_001",
            new_status=RegistrationStatus.APPROVED,
        )

        # 3. 注册策略
        registry.register_strategy(
            account_id="acc_001",
            strategy_id="trend_v1",
            strategy_type="TREND",
        )

        # 4. 模拟交易并验证
        for i in range(10):
            validator.record_order(
                event_type="submit",
                account_id="acc_001",
                strategy_id="trend_v1",
                order_id=f"order_{i}",
            )

        # 5. 生成日报送
        report = reporter.generate_daily_report("acc_001")
        assert report.content["strategy_count"] == 1

        # 6. 提交报送
        success = reporter.submit_report(report)
        assert success is True

        # 7. 验证审计日志
        assert len(audit_events) >= 3  # 至少有注册、状态更新、策略注册等事件

    def test_compliance_thresholds(self, validator: ComplianceValidator) -> None:
        """测试D7-P1合规阈值."""
        # 测试所有阈值边界条件
        config = validator.config

        # 验证配置值符合D7-P1要求
        assert config.max_cancel_ratio == 0.50  # <=50%
        assert config.max_cancel_freq_per_sec == 500  # <=500次/秒
        assert config.min_order_interval_ms == 100  # >=100ms
        assert config.max_audit_delay_sec == 1.0  # <=1s


# ============================================================
# Convenience Function Tests
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_registration_registry(self) -> None:
        """测试创建备案登记中心."""
        registry = create_registration_registry()
        assert registry is not None
        assert isinstance(registry, RegistrationRegistry)

    def test_create_compliance_validator(self) -> None:
        """测试创建合规验证器."""
        validator = create_compliance_validator()
        assert validator is not None
        assert isinstance(validator, ComplianceValidator)

    def test_create_regulatory_reporter(self) -> None:
        """测试创建监管报送器."""
        reporter = create_regulatory_reporter()
        assert reporter is not None
        assert isinstance(reporter, RegulatoryReporter)
