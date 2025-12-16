"""
Audit - 审计事件模块

V3PRO+ Platform Component - Phase 1
V2 SPEC: 第 7 章

军规级要求:
- 所有事件必须有 run_id, exec_id 追溯
- JSONL 格式原子化写入
- DecisionEvent 必须包含 strategy_id, version, feature_hash
"""

from __future__ import annotations

from src.audit.decision_log import DecisionEvent
from src.audit.guardian_log import GuardianEvent
from src.audit.order_trail import ExecEvent, OrderStateEvent, TradeEvent
from src.audit.pnl_attribution import PnLAttribution, PnLRecord
from src.audit.replay_verifier import ReplayVerifier
from src.audit.writer import AuditEvent, AuditWriter


__all__ = [
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
