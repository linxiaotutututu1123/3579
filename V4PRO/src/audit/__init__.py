"""
Audit - 审计事件模块

V3PRO+ Platform Component - Phase 1/8
V2 SPEC: 第 7 章

军规级要求:
- 所有事件必须有 run_id, exec_id 追溯
- JSONL 格式原子化写入
- DecisionEvent 必须包含 strategy_id, version, feature_hash
- M3: 审计日志完整 - 链式追踪, 时序保证, 校验和防篡改
- 合规存储: 交易5年, 系统3年, 审计10年
"""

from __future__ import annotations

from src.audit.audit_tracker import (
    AuditEventCategory,
    AuditEventType,
    AuditTracker,
    RETENTION_DAYS,
    TraceContext,
    TracedAuditEvent,
    create_audit_tracker,
    read_audit_trail,
    verify_audit_integrity,
)
from src.audit.decision_log import DecisionEvent
from src.audit.guardian_log import GuardianEvent
from src.audit.order_trail import ExecEvent, OrderStateEvent, TradeEvent
from src.audit.pnl_attribution import PnLAttribution, PnLRecord
from src.audit.replay_verifier import ReplayVerifier
from src.audit.writer import AuditEvent, AuditWriter


__all__ = [
    # Phase 8: 审计追踪机制
    "AuditEventCategory",
    "AuditEventType",
    "AuditTracker",
    "RETENTION_DAYS",
    "TraceContext",
    "TracedAuditEvent",
    "create_audit_tracker",
    "read_audit_trail",
    "verify_audit_integrity",
    # 原有导出
    "AuditEvent",
    "AuditWriter",
    "DecisionEvent",
    "ExecEvent",
    "GuardianEvent",
    "OrderStateEvent",
    "PnLAttribution",
    "PnLRecord",
    "ReplayVerifier",
    "TradeEvent",
]
