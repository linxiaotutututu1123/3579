"""
高频交易检测器模块 - HFT Detector.

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测
- CHINA.COMPLIANCE.THROTTLE: 限速控制

军规覆盖:
- M3: 审计日志完整 - 必记字段/保留期限/存储要求
- M6: 熔断保护机制完整 - 与熔断系统联动
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能模块:
- ThrottleController: 限速控制器
- ThrottleLevel: 限速级别枚举
- ThrottleStatus: 限速状态
- ThrottleConfig: 限速配置
"""

from __future__ import annotations

from src.compliance.hft_detector.throttle import (
    ThrottleConfig,
    ThrottleController,
    ThrottleLevel,
    ThrottleStatus,
)

__all__ = [
    "ThrottleConfig",
    "ThrottleController",
    "ThrottleLevel",
    "ThrottleStatus",
]
