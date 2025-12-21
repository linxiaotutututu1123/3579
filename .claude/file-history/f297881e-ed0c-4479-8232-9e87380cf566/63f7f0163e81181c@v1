"""
Trading Module - CI门禁与模式控制 (军规级 v4.0).

V4PRO Platform Component - Phase 0
V2 SPEC: 第 8 章 CI/CD 门禁

模块职责:
- CI门禁检查 (CIGate)
- 退出码体系 (ExitCode: 0-13)
- CHECK_MODE 模式控制
- JSON报告生成 (Schema v3)
- 策略验证 (PolicyReport)

Required Scenarios:
- INFRA.CI.GATE_PASS
- INFRA.CI.LINT_PASS
- INFRA.CI.TYPE_PASS
- INFRA.CI.TEST_PASS
- INFRA.CI.COVERAGE_MIN
- INFRA.CHECK.MODE_ENABLED
- INFRA.CHECK.BROKER_BLOCKED
- INFRA.EXIT.CODE.*
"""

from __future__ import annotations

from src.trading.ci_gate import (
    CI_REPORT_REQUIRED_FIELDS,
    FIXED_PATHS,
    CIGate,
    CIJsonReport,
    CIJsonReportV3,
    CIStep,
    CIStepFailure,
    CIStepStatus,
    ExitCode,
    GateCheck,
    GateCheckStatus,
    GateReport,
    PolicyReport,
    PolicyViolation,
    assert_not_check_mode,
    check_artifact_paths,
    check_command_whitelist,
    disable_check_mode,
    enable_check_mode,
    get_exit_code,
    is_check_mode,
    log_gate_report,
    validate_report_schema,
)


__all__ = [
    # 常量
    "CI_REPORT_REQUIRED_FIELDS",
    "FIXED_PATHS",
    # 门禁类
    "CIGate",
    "CIJsonReport",
    "CIJsonReportV3",
    "CIStep",
    "CIStepFailure",
    "CIStepStatus",
    # 退出码
    "ExitCode",
    # Gate检查
    "GateCheck",
    "GateCheckStatus",
    "GateReport",
    # 策略验证
    "PolicyReport",
    "PolicyViolation",
    # CHECK_MODE函数
    "assert_not_check_mode",
    "check_artifact_paths",
    "check_command_whitelist",
    "disable_check_mode",
    "enable_check_mode",
    "get_exit_code",
    "is_check_mode",
    "log_gate_report",
    "validate_report_schema",
]
