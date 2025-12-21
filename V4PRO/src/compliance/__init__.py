"""
合规模块 (军规级 v4.0).

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: §12 Phase 7, §21 程序化交易合规, D7-P1 程序化交易备案

功能特性:
- 程序化交易合规检查 (ProgrammaticTradingCompliance)
- 报撤单频率节流 (ComplianceThrottle)
- 合规报告生成 (ComplianceReport)
- 中国期货合规规则 (ChinaFuturesComplianceChecker)
- 程序化交易备案登记 (RegistrationRegistry) [Phase 9]
- 合规阈值验证 (ComplianceValidator) [Phase 9]
- 监管报送接口 (RegulatoryReporter) [Phase 9]

军规覆盖:
- M3: 审计日志完整 - 所有操作必须记录审计日志
- M7: 场景回放 - 支持合规检查场景回放
- M12: 双重确认 - 大额订单需人工或二次确认
- M13: 涨跌停感知 - 订单价格必须检查涨跌停板
- M15: 夜盘跨日处理 - 夜盘交易日归属必须正确
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

监管规则 (2025年《期货市场程序化交易管理规定》):
- 5秒内报撤单预警阈值: 50笔
- 单秒高频交易判定: >=300笔
- 单日高频交易判定: >=20000笔

合规阈值 (D7-P1):
- 报撤单比例: <=50%
- 撤单频率: <=500次/秒
- 订单间隔: >=100ms
- 审计延迟: <=1s

示例:
    >>> from src.compliance import (
    ...     ChinaFuturesComplianceChecker,
    ...     ComplianceThrottle,
    ...     ProgrammaticTradingCompliance,
    ...     ThrottleLevel,
    ...     RegistrationRegistry,
    ...     ComplianceValidator,
    ...     RegulatoryReporter,
    ... )
    >>> compliance = ProgrammaticTradingCompliance()
    >>> can, msg = compliance.can_submit("rb2501")
    >>> checker = ChinaFuturesComplianceChecker()
    >>> result = checker.check_order(order_info)
    >>> registry = RegistrationRegistry()
    >>> validator = ComplianceValidator()
    >>> reporter = RegulatoryReporter(registry, validator)
"""

from __future__ import annotations

from src.compliance.china_futures_rules import (
    ChinaFuturesComplianceChecker,
    ComplianceCheckResult,
    ComplianceConfig,
    ComplianceViolation,
    MarketContext,
    OrderInfo,
    SeverityLevel,
    ViolationType,
    check_order_compliance,
    create_compliance_checker,
    get_default_compliance_config,
)
from src.compliance.programmatic_trading import (
    ComplianceReport,
    ComplianceThrottle,
    OrderAction,
    OrderRecord,
    ProgrammaticTradingCompliance,
    ThrottleConfig,
    ThrottleLevel,
    ThrottleStatus,
    create_compliance_manager,
    create_compliance_throttle,
    get_default_throttle_config,
)
from src.compliance.registration import (
    ComplianceMetrics,
    ComplianceValidator,
    ComplianceValidatorConfig,
    OrderFrequencyMonitor,
    RegistrationInfo,
    RegistrationRegistry,
    RegistrationStatus,
    ReportFormat,
    ReportRecord,
    ReportType,
    RegulatoryReporter,
    StrategyRegistration,
    ValidationResult,
    ViolationDetail,
    create_compliance_validator,
    create_registration_registry,
    create_regulatory_reporter,
)


__all__ = [
    # China Futures Rules
    "ChinaFuturesComplianceChecker",
    "ComplianceCheckResult",
    "ComplianceConfig",
    "ComplianceViolation",
    "MarketContext",
    "OrderInfo",
    "SeverityLevel",
    "ViolationType",
    "check_order_compliance",
    "create_compliance_checker",
    "get_default_compliance_config",
    # Programmatic Trading
    "ComplianceReport",
    "ComplianceThrottle",
    "OrderAction",
    "OrderRecord",
    "ProgrammaticTradingCompliance",
    "ThrottleConfig",
    "ThrottleLevel",
    "ThrottleStatus",
    "create_compliance_manager",
    "create_compliance_throttle",
    "get_default_throttle_config",
    # Registration (Phase 9)
    "ComplianceMetrics",
    "ComplianceValidator",
    "ComplianceValidatorConfig",
    "OrderFrequencyMonitor",
    "RegistrationInfo",
    "RegistrationRegistry",
    "RegistrationStatus",
    "ReportFormat",
    "ReportRecord",
    "ReportType",
    "RegulatoryReporter",
    "StrategyRegistration",
    "ValidationResult",
    "ViolationDetail",
    "create_compliance_validator",
    "create_registration_registry",
    "create_regulatory_reporter",
]
