"""
高频交易检测器模块 - HFT Detector (军规级 v4.0).

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测
- CHINA.COMPLIANCE.THROTTLE: 限速控制
- CHINA.COMPLIANCE.AUDIT_LOG: 审计日志记录

军规覆盖:
- M3: 审计日志完整 - 必记字段/保留期限/存储要求
- M6: 熔断保护机制完整 - 与熔断系统联动
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能模块:
- HFTDetector: 高频交易检测器 (主类)
- OrderFlow: 订单流数据结构
- HFTDetectionResult: 检测结果
- ThrottleLevel: 限速级别枚举
- ThrottleController: 限速控制器
- ThrottleStatus: 限速状态
- ThrottleConfig: 限速配置

高频交易阈值 (设计规格):
- 订单频率: warning=200, critical=300, block=500 (笔/秒)
- 撤单比例: warning=40%, critical=50%
- 往返时间: <10ms 视为HFT行为指标

示例:
    >>> from src.compliance.hft_detector import (
    ...     HFTDetector,
    ...     OrderFlow,
    ...     ThrottleLevel,
    ...     HFTDetectionResult,
    ... )
    >>> detector = HFTDetector()
    >>> order_flow = OrderFlow(
    ...     account_id="acc_001",
    ...     order_id="order_001",
    ...     event_type="submit",
    ...     timestamp=time.time(),
    ... )
    >>> result = detector.detect_hft_pattern(order_flow)
    >>> if result.is_hft:
    ...     print(f"检测到HFT: {result.detection_reason}")
"""

from __future__ import annotations

from src.compliance.hft_detector.throttle import (
    ThrottleConfig,
    ThrottleController,
    ThrottleLevel,
    ThrottleStatus,
)

from src.compliance.hft_detector.detector import (
    # Constants
    HFT_THRESHOLDS,
    DEFAULT_WINDOW_SECONDS,
    MAX_RECORDS,
    THROTTLE_LEVEL_PRIORITY,
    # Enums
    HFTIndicatorType,
    AuditEventType,
    # Data Classes
    OrderFlow,
    HFTIndicator,
    HFTDetectionResult,
    HFTDetectorConfig,
    ThrottleState,
    AuditLogEntry,
    # Main Class
    HFTDetector,
    # Factory Functions
    create_hft_detector,
    get_default_hft_config,
    get_hft_thresholds,
)

__all__ = [
    # Throttle module (existing)
    "ThrottleConfig",
    "ThrottleController",
    "ThrottleLevel",
    "ThrottleStatus",
    # Detector module (new)
    # Constants
    "HFT_THRESHOLDS",
    "DEFAULT_WINDOW_SECONDS",
    "MAX_RECORDS",
    "THROTTLE_LEVEL_PRIORITY",
    # Enums
    "HFTIndicatorType",
    "AuditEventType",
    # Data Classes
    "OrderFlow",
    "HFTIndicator",
    "HFTDetectionResult",
    "HFTDetectorConfig",
    "ThrottleState",
    "AuditLogEntry",
    # Main Class
    "HFTDetector",
    # Factory Functions
    "create_hft_detector",
    "get_default_hft_config",
    "get_hft_thresholds",
]
