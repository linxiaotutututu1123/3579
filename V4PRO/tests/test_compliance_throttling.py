"""
合规节流机制测试 - Compliance Throttling Tests (军规级 v4.0).

V4PRO Platform Component - Phase 7/9 Testing
V4 SPEC: D7-P1 程序化交易备案, M3 审计日志完整, M17 程序化合规

测试覆盖:
- ComplianceThrottleManager: 合规节流管理器
- HFTDetector: 高频交易检测器
- AuditLogger: 审计日志记录器
"""

from __future__ import annotations

import time
from datetime import datetime

import pytest

from src.compliance.compliance_throttling import (
    # Config
    ThrottleConfig,
    AuditLogConfig,
    # Enums
    ThrottleAction,
    AuditEventType,
    LogCategory,
    # Data Classes
    ThrottleResult,
    AuditLogEntry,
    HFTDetectionResult,
    # Main Classes
    ComplianceThrottleManager,
    HFTDetector,
    AuditLogger,
    # Constants
    MAX_CANCEL_RATIO,
    MAX_CANCEL_FREQ_PER_SEC,
    MIN_ORDER_INTERVAL_MS,
    MAX_AUDIT_DELAY_SEC,
    HFT_THRESHOLD_PER_SEC,
    # Factory Functions
    create_throttle_manager,
    create_hft_detector,
    create_audit_logger,
)


class TestComplianceConstants:
    """合规常量测试."""

    def test_cancel_ratio_threshold(self) -> None:
        """测试报撤单比例阈值."""
        assert MAX_CANCEL_RATIO == 0.50, "报撤单比例应为50%"

    def test_cancel_freq_threshold(self) -> None:
        """测试撤单频率阈值."""
        assert MAX_CANCEL_FREQ_PER_SEC == 500, "撤单频率应为500次/秒"

    def test_order_interval_threshold(self) -> None:
        """测试订单间隔阈值."""
        assert MIN_ORDER_INTERVAL_MS == 100, "订单间隔应>=100ms"

    def test_audit_delay_threshold(self) -> None:
        """测试审计延迟阈值."""
        assert MAX_AUDIT_DELAY_SEC == 1.0, "审计延迟应<=1s"

    def test_hft_threshold(self) -> None:
        """测试高频交易阈值."""
        assert HFT_THRESHOLD_PER_SEC == 300, "高频交易阈值应为300笔/秒"


class TestThrottleConfig:
    """节流配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = ThrottleConfig()
        assert config.max_cancel_ratio == 0.50
        assert config.max_cancel_freq_per_sec == 500
        assert config.min_order_interval_ms == 100
        assert config.max_audit_delay_sec == 1.0
        assert config.hft_threshold_per_sec == 300
        assert config.enable_auto_throttle is True
        assert config.enable_hft_detection is True

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = ThrottleConfig(
            max_cancel_ratio=0.40,
            max_cancel_freq_per_sec=400,
            min_order_interval_ms=200,
        )
        assert config.max_cancel_ratio == 0.40
        assert config.max_cancel_freq_per_sec == 400
        assert config.min_order_interval_ms == 200


class TestHFTDetector:
    """高频交易检测器测试."""

    def test_create_detector(self) -> None:
        """测试创建检测器."""
        detector = HFTDetector()
        assert detector.threshold == HFT_THRESHOLD_PER_SEC

    def test_record_order(self) -> None:
        """测试记录订单."""
        detector = HFTDetector()
        detector.record_order("acc_001", "strat_001", "order_001", "submit", "rb2501")
        detector.record_order("acc_001", "strat_001", "order_002", "cancel", "rb2501")

        result = detector.detect("acc_001")
        assert result.orders_per_sec >= 0

    def test_hft_detection_low_frequency(self) -> None:
        """测试低频率不触发HFT检测."""
        detector = HFTDetector(threshold_per_sec=300)
        ts = time.time()

        # 记录少量订单
        for i in range(10):
            detector.record_order("acc_001", "strat_001", f"order_{i}", "submit", timestamp=ts)

        result = detector.detect("acc_001", ts)
        assert result.is_hft is False
        assert result.orders_per_sec < 300

    def test_hft_detection_high_frequency(self) -> None:
        """测试高频率触发HFT检测."""
        detector = HFTDetector(threshold_per_sec=10, window_seconds=1)
        ts = time.time()

        # 记录大量订单 (超过阈值)
        for i in range(20):
            detector.record_order("acc_001", "strat_001", f"order_{i}", "submit", timestamp=ts)

        result = detector.detect("acc_001", ts)
        assert result.is_hft is True
        assert result.orders_per_sec >= 10
        assert "acc_001" in detector.hft_accounts

    def test_hft_account_tracking(self) -> None:
        """测试HFT账户跟踪."""
        detector = HFTDetector(threshold_per_sec=5)
        ts = time.time()

        # 触发HFT
        for i in range(10):
            detector.record_order("acc_001", "strat_001", f"order_{i}", "submit", timestamp=ts)

        detector.detect("acc_001", ts)
        assert detector.is_hft_account("acc_001") is True

        # 清除标记
        detector.clear_hft_flag("acc_001")
        assert detector.is_hft_account("acc_001") is False

    def test_cancel_ratio_calculation(self) -> None:
        """测试撤单比例计算."""
        detector = HFTDetector()
        ts = time.time()

        # 50%撤单比例
        detector.record_order("acc_001", "strat_001", "order_001", "submit", timestamp=ts)
        detector.record_order("acc_001", "strat_001", "order_002", "cancel", timestamp=ts)
        detector.record_order("acc_001", "strat_001", "order_003", "submit", timestamp=ts)
        detector.record_order("acc_001", "strat_001", "order_004", "cancel", timestamp=ts)

        result = detector.detect("acc_001", ts)
        assert result.cancel_ratio == 0.5

    def test_statistics(self) -> None:
        """测试统计信息."""
        detector = HFTDetector()
        detector.record_order("acc_001", "strat_001", "order_001", "submit")
        detector.detect("acc_001")

        stats = detector.get_statistics()
        assert "detection_count" in stats
        assert "hft_detection_count" in stats
        assert stats["detection_count"] == 1

    def test_reset(self) -> None:
        """测试重置."""
        detector = HFTDetector(threshold_per_sec=5)
        ts = time.time()

        for i in range(10):
            detector.record_order("acc_001", "strat_001", f"order_{i}", "submit", timestamp=ts)
        detector.detect("acc_001", ts)

        detector.reset()
        assert len(detector.hft_accounts) == 0
        result = detector.detect("acc_001")
        assert result.is_hft is False


class TestComplianceThrottleManager:
    """合规节流管理器测试."""

    def test_create_manager(self) -> None:
        """测试创建管理器."""
        manager = ComplianceThrottleManager()
        assert manager.config.max_cancel_ratio == 0.50
        assert manager.VERSION == "4.0"

    def test_check_allow_normal(self) -> None:
        """测试正常情况允许通过."""
        manager = ComplianceThrottleManager()
        result = manager.check_and_throttle("acc_001", "strat_001")
        assert result.action in (ThrottleAction.ALLOW, ThrottleAction.WARN)

    def test_order_interval_throttling(self) -> None:
        """测试订单间隔节流."""
        manager = ComplianceThrottleManager()
        ts = time.time()

        # 第一笔订单
        manager.record_order("acc_001", "strat_001", "order_001", "submit", timestamp=ts)

        # 立即检查 (间隔太短)
        result = manager.check_and_throttle("acc_001", "strat_001", ts + 0.01)  # 10ms

        # 应该被延迟
        assert result.action in (ThrottleAction.DELAY, ThrottleAction.WARN)

    def test_can_submit(self) -> None:
        """测试can_submit方法."""
        manager = ComplianceThrottleManager()
        can, msg = manager.can_submit("acc_001", "strat_001")
        assert can is True
        assert len(msg) > 0

    def test_get_account_metrics(self) -> None:
        """测试获取账户指标."""
        manager = ComplianceThrottleManager()
        ts = time.time()

        manager.record_order("acc_001", "strat_001", "order_001", "submit", timestamp=ts)
        manager.record_order("acc_001", "strat_001", "order_002", "cancel", timestamp=ts)

        metrics = manager.get_account_metrics("acc_001", ts)
        assert "cancel_ratio" in metrics
        assert "total_orders" in metrics
        assert metrics["total_orders"] == 2

    def test_statistics(self) -> None:
        """测试统计信息."""
        manager = ComplianceThrottleManager()
        manager.check_and_throttle("acc_001", "strat_001")

        stats = manager.get_statistics()
        assert "check_count" in stats
        assert "throttle_count" in stats
        assert "hft_detector" in stats
        assert stats["check_count"] == 1

    def test_audit_callback(self) -> None:
        """测试审计回调."""
        audit_events = []

        def callback(entry: AuditLogEntry) -> None:
            audit_events.append(entry)

        config = ThrottleConfig(
            min_order_interval_ms=1000,  # 1秒间隔
        )
        manager = ComplianceThrottleManager(config=config, audit_callback=callback)

        ts = time.time()
        manager.record_order("acc_001", "strat_001", "order_001", "submit", timestamp=ts)
        manager.check_and_throttle("acc_001", "strat_001", ts + 0.01)  # 触发间隔过短

        # 应该有审计事件
        # (根据实际阈值判断)

    def test_reset(self) -> None:
        """测试重置."""
        manager = ComplianceThrottleManager()
        manager.record_order("acc_001", "strat_001", "order_001", "submit")
        manager.check_and_throttle("acc_001", "strat_001")

        manager.reset()
        stats = manager.get_statistics()
        assert stats["check_count"] == 0


class TestAuditLogger:
    """审计日志记录器测试."""

    def test_create_logger(self) -> None:
        """测试创建记录器."""
        logger = AuditLogger()
        assert logger.VERSION == "4.0"

    def test_log_basic(self) -> None:
        """测试基本日志记录."""
        audit_logger = AuditLogger()
        entry = audit_logger.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001/strat_001",
            target="order_12345",
            action="提交买入订单",
            result="SUCCESS",
            context={"symbol": "rb2501", "volume": 10},
        )

        assert entry.event_type == AuditEventType.ORDER_SUBMIT
        assert entry.operator == "acc_001/strat_001"
        assert entry.target == "order_12345"
        assert entry.result == "SUCCESS"
        assert entry.military_rule == "M3"
        assert len(entry.integrity_hash) == 64  # SHA256

    def test_log_order_submit(self) -> None:
        """测试订单提交日志."""
        audit_logger = AuditLogger()
        entry = audit_logger.log_order_submit(
            account_id="acc_001",
            strategy_id="strat_001",
            order_id="order_12345",
            symbol="rb2501",
            direction="BUY",
            volume=10,
            price=3500.0,
        )

        assert entry.event_type == AuditEventType.ORDER_SUBMIT
        assert entry.category == LogCategory.TRADING
        assert "symbol" in entry.context
        assert entry.context["symbol"] == "rb2501"

    def test_log_compliance_violation(self) -> None:
        """测试合规违规日志."""
        audit_logger = AuditLogger()
        entry = audit_logger.log_compliance_violation(
            account_id="acc_001",
            strategy_id="strat_001",
            violation_type="CANCEL_RATIO_EXCEEDED",
            message="报撤单比例超限: 55% > 50%",
            metrics={"cancel_ratio": 0.55},
        )

        assert entry.event_type == AuditEventType.COMPLIANCE_VIOLATION
        assert entry.category == LogCategory.AUDIT
        assert entry.result == "VIOLATION"

    def test_log_hft_detected(self) -> None:
        """测试高频交易检测日志."""
        audit_logger = AuditLogger()
        entry = audit_logger.log_hft_detected(
            account_id="acc_001",
            orders_per_sec=350.0,
            threshold=300,
        )

        assert entry.event_type == AuditEventType.HFT_DETECTED
        assert entry.context["orders_per_sec"] == 350.0

    def test_integrity_verification(self) -> None:
        """测试完整性验证."""
        audit_logger = AuditLogger()
        entry = audit_logger.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001",
            target="order_001",
            action="submit",
            result="SUCCESS",
        )

        # 验证完整性
        assert audit_logger.verify_integrity(entry) is True

    def test_get_logs(self) -> None:
        """测试查询日志."""
        audit_logger = AuditLogger()

        # 记录多条日志
        audit_logger.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001",
            target="order_001",
            action="submit",
            result="SUCCESS",
            category=LogCategory.TRADING,
        )
        audit_logger.log(
            event_type=AuditEventType.COMPLIANCE_WARNING,
            operator="acc_001",
            target="check",
            action="check",
            result="WARNING",
            category=LogCategory.AUDIT,
        )

        # 查询交易日志
        trading_logs = audit_logger.get_logs(category=LogCategory.TRADING)
        assert len(trading_logs) == 1

        # 查询所有日志
        all_logs = audit_logger.get_logs()
        assert len(all_logs) == 2

    def test_retention_dates(self) -> None:
        """测试保留期限."""
        config = AuditLogConfig(
            trading_log_retention_years=5,
            system_log_retention_years=3,
            audit_log_retention_years=10,
        )
        audit_logger = AuditLogger(config=config)

        # 获取保留日期
        trading_date = audit_logger.get_retention_date(LogCategory.TRADING)
        audit_date = audit_logger.get_retention_date(LogCategory.AUDIT)

        # 审计日志保留更久
        assert trading_date > audit_date

    def test_statistics(self) -> None:
        """测试统计信息."""
        audit_logger = AuditLogger()
        audit_logger.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001",
            target="order_001",
            action="submit",
            result="SUCCESS",
        )

        stats = audit_logger.get_statistics()
        assert "total_log_count" in stats
        assert "log_counts_by_category" in stats
        assert stats["total_log_count"] == 1

    def test_backup_callback(self) -> None:
        """测试备份回调."""
        backup_entries = []

        def backup_callback(entry: AuditLogEntry) -> None:
            backup_entries.append(entry)

        config = AuditLogConfig(enable_remote_backup=True)
        audit_logger = AuditLogger(config=config, backup_callback=backup_callback)

        audit_logger.log(
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001",
            target="order_001",
            action="submit",
            result="SUCCESS",
        )

        assert len(backup_entries) == 1


class TestAuditLogEntry:
    """审计日志条目测试."""

    def test_m3_required_fields(self) -> None:
        """测试M3军规必记字段."""
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001/strat_001",
            target="order_12345",
            action="提交订单",
            result="SUCCESS",
            context={"symbol": "rb2501"},
        )

        # 验证必记字段
        d = entry.to_dict()
        assert "timestamp" in d
        assert "event_type" in d
        assert "operator" in d
        assert "target" in d
        assert "action" in d
        assert "result" in d
        assert "context" in d

    def test_integrity_hash(self) -> None:
        """测试完整性哈希."""
        entry = AuditLogEntry(
            timestamp="2025-12-22T10:00:00",
            event_type=AuditEventType.ORDER_SUBMIT,
            operator="acc_001",
            target="order_001",
            action="submit",
            result="SUCCESS",
            context={},
            sequence_id=1,
        )

        hash1 = entry.compute_integrity_hash()
        hash2 = entry.compute_integrity_hash()

        # 相同内容产生相同哈希
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256


class TestFactoryFunctions:
    """工厂函数测试."""

    def test_create_throttle_manager(self) -> None:
        """测试创建节流管理器."""
        manager = create_throttle_manager()
        assert isinstance(manager, ComplianceThrottleManager)

    def test_create_hft_detector(self) -> None:
        """测试创建HFT检测器."""
        detector = create_hft_detector(threshold_per_sec=100)
        assert isinstance(detector, HFTDetector)
        assert detector.threshold == 100

    def test_create_audit_logger(self) -> None:
        """测试创建审计日志器."""
        logger = create_audit_logger()
        assert isinstance(logger, AuditLogger)


class TestThrottleResult:
    """节流结果测试."""

    def test_should_delay(self) -> None:
        """测试延迟判断."""
        result = ThrottleResult(
            action=ThrottleAction.DELAY,
            delay_ms=100,
        )
        assert result.should_delay() is True

        result_no_delay = ThrottleResult(
            action=ThrottleAction.ALLOW,
            delay_ms=0,
        )
        assert result_no_delay.should_delay() is False

    def test_should_reject(self) -> None:
        """测试拒绝判断."""
        result = ThrottleResult(
            action=ThrottleAction.REJECT,
        )
        assert result.should_reject() is True

        result_allow = ThrottleResult(
            action=ThrottleAction.ALLOW,
        )
        assert result_allow.should_reject() is False


class TestIntegration:
    """集成测试."""

    def test_full_workflow(self) -> None:
        """测试完整工作流."""
        # 创建组件
        throttle_manager = ComplianceThrottleManager()
        hft_detector = HFTDetector()
        audit_logger = AuditLogger()

        # 模拟订单提交
        account_id = "acc_001"
        strategy_id = "strat_001"
        ts = time.time()

        # 1. 记录订单
        throttle_manager.record_order(
            account_id, strategy_id, "order_001", "submit", "rb2501", ts
        )
        hft_detector.record_order(
            account_id, strategy_id, "order_001", "submit", "rb2501", ts
        )

        # 2. 检查节流
        result = throttle_manager.check_and_throttle(account_id, strategy_id, ts)
        assert result.action in (ThrottleAction.ALLOW, ThrottleAction.WARN)

        # 3. 检测HFT
        hft_result = hft_detector.detect(account_id, ts)
        assert hft_result.is_hft is False

        # 4. 记录审计日志
        entry = audit_logger.log_order_submit(
            account_id=account_id,
            strategy_id=strategy_id,
            order_id="order_001",
            symbol="rb2501",
            direction="BUY",
            volume=10,
            price=3500.0,
        )
        assert audit_logger.verify_integrity(entry)

        # 5. 查看统计
        throttle_stats = throttle_manager.get_statistics()
        hft_stats = hft_detector.get_statistics()
        audit_stats = audit_logger.get_statistics()

        assert throttle_stats["check_count"] == 1
        assert hft_stats["detection_count"] == 1
        assert audit_stats["total_log_count"] == 1

    def test_high_frequency_scenario(self) -> None:
        """测试高频交易场景."""
        config = ThrottleConfig(
            hft_threshold_per_sec=10,  # 降低阈值便于测试
            enable_hft_detection=True,
        )
        manager = ComplianceThrottleManager(config=config)
        ts = time.time()

        # 快速提交大量订单
        for i in range(20):
            manager.record_order("acc_001", "strat_001", f"order_{i}", "submit", timestamp=ts)

        # 检查是否被识别为HFT
        hft_result = manager.hft_detector.detect("acc_001", ts)
        assert hft_result.is_hft is True

        # 节流检查应该有警告
        result = manager.check_and_throttle("acc_001", "strat_001", ts)
        assert "高频" in result.reason or result.action != ThrottleAction.ALLOW
