"""
GuardianLog - 守护事件

V3PRO+ Platform Component - Phase 1
V2 SPEC: 7.1
V2 Scenarios: STRAT.DEGRADE.MODE_TRANSITION_AUDIT

军规级要求:
- 模式切换必须写入审计
- 包含 mode_from, mode_to, trigger
- 可追溯到 run_id 和 exec_id
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class GuardianEventType(str, Enum):
    """守护事件类型."""

    MODE_CHANGE = "MODE_CHANGE"
    TRIGGER_DETECTED = "TRIGGER_DETECTED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    RECOVERY_STARTED = "RECOVERY_STARTED"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    HEALTH_CHECK = "HEALTH_CHECK"


@dataclass
class GuardianEvent:
    """守护事件.

    V2 Scenario: STRAT.DEGRADE.MODE_TRANSITION_AUDIT

    记录 Guardian 状态机的模式切换和动作执行。

    Attributes:
        ts: 时间戳
        run_id: 运行 ID
        exec_id: 执行 ID
        guardian_event_type: 守护事件类型
        mode_from: 原模式
        mode_to: 目标模式
        trigger: 触发原因
        action: 执行的动作
        details: 详细信息
    """

    ts: float
    run_id: str
    exec_id: str
    guardian_event_type: str
    mode_from: str | None = None
    mode_to: str | None = None
    trigger: str | None = None
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "GUARDIAN"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        return data

    @classmethod
    def mode_change(
        cls,
        ts: float,
        run_id: str,
        exec_id: str,
        mode_from: str,
        mode_to: str,
        trigger: str,
        details: dict[str, Any] | None = None,
    ) -> GuardianEvent:
        """创建模式切换事件.

        V2 Scenario: STRAT.DEGRADE.MODE_TRANSITION_AUDIT

        Args:
            ts: 时间戳
            run_id: 运行 ID
            exec_id: 执行 ID
            mode_from: 原模式
            mode_to: 目标模式
            trigger: 触发原因
            details: 详细信息

        Returns:
            GuardianEvent 实例
        """
        return cls(
            ts=ts,
            run_id=run_id,
            exec_id=exec_id,
            guardian_event_type=GuardianEventType.MODE_CHANGE.value,
            mode_from=mode_from,
            mode_to=mode_to,
            trigger=trigger,
            details=details or {},
        )

    @classmethod
    def trigger_detected(
        cls,
        ts: float,
        run_id: str,
        exec_id: str,
        trigger: str,
        details: dict[str, Any] | None = None,
    ) -> GuardianEvent:
        """创建触发器检测事件.

        Args:
            ts: 时间戳
            run_id: 运行 ID
            exec_id: 执行 ID
            trigger: 触发器名称
            details: 详细信息

        Returns:
            GuardianEvent 实例
        """
        return cls(
            ts=ts,
            run_id=run_id,
            exec_id=exec_id,
            guardian_event_type=GuardianEventType.TRIGGER_DETECTED.value,
            trigger=trigger,
            details=details or {},
        )

    @classmethod
    def action_executed(
        cls,
        ts: float,
        run_id: str,
        exec_id: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> GuardianEvent:
        """创建动作执行事件.

        Args:
            ts: 时间戳
            run_id: 运行 ID
            exec_id: 执行 ID
            action: 动作名称
            details: 详细信息

        Returns:
            GuardianEvent 实例
        """
        return cls(
            ts=ts,
            run_id=run_id,
            exec_id=exec_id,
            guardian_event_type=GuardianEventType.ACTION_EXECUTED.value,
            action=action,
            details=details or {},
        )
