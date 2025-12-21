"""
合规模块 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §21 程序化交易合规

功能特性:
- 程序化交易合规检查 (ProgrammaticTradingCompliance)
- 报撤单频率节流 (ComplianceThrottle)
- 合规报告生成 (ComplianceReport)

军规覆盖:
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

监管规则 (2025年《期货市场程序化交易管理规定》):
- 5秒内报撤单预警阈值: 50笔
- 单秒高频交易判定: ≥300笔
- 单日高频交易判定: ≥20000笔

示例:
    >>> from src.compliance import (
    ...     ComplianceThrottle,
    ...     ProgrammaticTradingCompliance,
    ...     ThrottleLevel,
    ... )
    >>> compliance = ProgrammaticTradingCompliance()
    >>> can, msg = compliance.can_submit("rb2501")
"""

from __future__ import annotations

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


__all__ = [
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
]
