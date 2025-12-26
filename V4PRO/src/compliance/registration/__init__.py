"""
程序化交易备案模块 - Registration (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.REGISTRATION: 程序化交易备案登记
- CHINA.COMPLIANCE.VALIDATION: 合规阈值验证
- CHINA.COMPLIANCE.REPORT: 监管报送

军规覆盖:
- M3: 审计日志完整 - 所有操作必须记录审计日志
- M7: 场景回放 - 支持合规检查场景回放
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 程序化交易备案登记 (Registry)
- 合规阈值验证 (Validator)
- 监管报送接口 (Reporter)
- 高频交易检测 (HFT Detection)
- 审计日志集成 (Audit Integration)

合规阈值 (D7-P1):
- 报撤单比例: <=50%
- 撤单频率: <=500次/秒
- 订单间隔: >=100ms
- 审计延迟: <=1s

监管规则 (2025年《期货市场程序化交易管理规定》):
- 程序化交易账户需完成备案登记
- 交易策略变更需及时报送
- 异常交易行为需自动监控

示例:
    >>> from src.compliance.registration import (
    ...     RegistrationRegistry,
    ...     ComplianceValidator,
    ...     RegulatoryReporter,
    ... )
    >>> registry = RegistrationRegistry()
    >>> validator = ComplianceValidator()
    >>> reporter = RegulatoryReporter(registry, validator)
"""

from __future__ import annotations

from src.compliance.registration.registry import (
    RegistrationInfo,
    RegistrationRegistry,
    RegistrationStatus,
    StrategyRegistration,
    create_registration_registry,
)
from src.compliance.registration.reporter import (
    ReportFormat,
    ReportRecord,
    ReportType,
    RegulatoryReporter,
    create_regulatory_reporter,
)
from src.compliance.registration.validator import (
    ComplianceMetrics,
    ComplianceValidator,
    ComplianceValidatorConfig,
    OrderFrequencyMonitor,
    ValidationResult,
    ViolationDetail,
    create_compliance_validator,
)

__all__ = [
    # Registry
    "RegistrationInfo",
    "RegistrationRegistry",
    "RegistrationStatus",
    "StrategyRegistration",
    "create_registration_registry",
    # Validator
    "ComplianceMetrics",
    "ComplianceValidator",
    "ComplianceValidatorConfig",
    "OrderFrequencyMonitor",
    "ValidationResult",
    "ViolationDetail",
    "create_compliance_validator",
    # Reporter
    "ReportFormat",
    "ReportRecord",
    "ReportType",
    "RegulatoryReporter",
    "create_regulatory_reporter",
]
