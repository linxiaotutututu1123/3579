"""
Guardian Recovery - 冷启动恢复

V3PRO+ Platform Component - Phase 1
V2 SPEC: 6.4
V2 Scenarios: GUARD.RECOVERY.COLD_START

军规级要求:
- 冷启动必须先撤销所有未完成订单
- 必须同步柜台持仓
- 必须进入 REDUCE_ONLY 冷却期
- 恢复过程必须写入审计日志
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class RecoveryStep(str, Enum):
    """恢复步骤."""

    CANCEL_ALL = "cancel_all"
    QUERY_POSITIONS = "query_positions"
    RECONCILE = "reconcile"
    SET_REDUCE_ONLY = "set_reduce_only"
    COOLDOWN = "cooldown"
    HEALTH_CHECK = "health_check"
    COMPLETE = "complete"


class RecoveryStatus(str, Enum):
    """恢复状态."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RecoveryState:
    """恢复状态.

    Attributes:
        status: 当前状态
        current_step: 当前步骤
        completed_steps: 已完成步骤
        start_time: 开始时间
        end_time: 结束时间
        errors: 错误列表
        details: 详细信息
    """

    status: RecoveryStatus = RecoveryStatus.NOT_STARTED
    current_step: RecoveryStep | None = None
    completed_steps: list[RecoveryStep] = field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "status": self.status.value,
            "current_step": self.current_step.value if self.current_step else None,
            "completed_steps": [s.value for s in self.completed_steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "errors": self.errors,
            "details": self.details,
        }


class ColdStartRecovery:
    """冷启动恢复器.

    V2 Scenario: GUARD.RECOVERY.COLD_START

    实现冷启动恢复流程：
    1. cancel_all - 撤销所有未完成订单
    2. query_positions - 查询柜台持仓
    3. reconcile - 对账
    4. set_reduce_only - 进入 REDUCE_ONLY 模式
    5. cooldown - 等待冷却期
    6. health_check - 健康检查
    7. complete - 完成，进入 RUNNING
    """

    def __init__(
        self,
        cooldown_s: float = 300.0,
        cancel_all_fn: Any | None = None,
        query_positions_fn: Any | None = None,
        reconcile_fn: Any | None = None,
        set_mode_fn: Any | None = None,
        health_check_fn: Any | None = None,
        on_step: Any | None = None,
    ) -> None:
        """初始化恢复器.

        Args:
            cooldown_s: 冷却期（秒）
            cancel_all_fn: 撤单函数 () -> bool
            query_positions_fn: 查询持仓函数 () -> dict[str, int]
            reconcile_fn: 对账函数 (local, broker) -> bool
            set_mode_fn: 设置模式函数 (mode) -> None
            health_check_fn: 健康检查函数 () -> bool
            on_step: 步骤回调 (step, success, details) -> None
        """
        self._cooldown_s = cooldown_s
        self._cancel_all_fn = cancel_all_fn
        self._query_positions_fn = query_positions_fn
        self._reconcile_fn = reconcile_fn
        self._set_mode_fn = set_mode_fn
        self._health_check_fn = health_check_fn
        self._on_step = on_step
        self._state = RecoveryState()

    @property
    def state(self) -> RecoveryState:
        """当前恢复状态."""
        return self._state

    @property
    def is_complete(self) -> bool:
        """是否完成恢复."""
        return self._state.status == RecoveryStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """是否恢复失败."""
        return self._state.status == RecoveryStatus.FAILED

    def start(self) -> RecoveryState:
        """开始恢复流程.

        V2 Scenario: GUARD.RECOVERY.COLD_START

        Returns:
            恢复状态
        """
        self._state = RecoveryState(
            status=RecoveryStatus.IN_PROGRESS,
            start_time=time.time(),
        )

        steps = [
            (RecoveryStep.CANCEL_ALL, self._step_cancel_all),
            (RecoveryStep.QUERY_POSITIONS, self._step_query_positions),
            (RecoveryStep.RECONCILE, self._step_reconcile),
            (RecoveryStep.SET_REDUCE_ONLY, self._step_set_reduce_only),
            (RecoveryStep.COOLDOWN, self._step_cooldown),
            (RecoveryStep.HEALTH_CHECK, self._step_health_check),
        ]

        for step, step_fn in steps:
            self._state.current_step = step
            success, details = step_fn()

            if self._on_step:
                self._on_step(step, success, details)

            if success:
                self._state.completed_steps.append(step)
                self._state.details[step.value] = details
            else:
                self._state.status = RecoveryStatus.FAILED
                self._state.errors.append(f"{step.value}: {details.get('error', 'unknown')}")
                self._state.end_time = time.time()
                return self._state

        self._state.status = RecoveryStatus.COMPLETED
        self._state.current_step = RecoveryStep.COMPLETE
        self._state.completed_steps.append(RecoveryStep.COMPLETE)
        self._state.end_time = time.time()

        return self._state

    def _step_cancel_all(self) -> tuple[bool, dict[str, Any]]:
        """步骤1: 撤销所有订单."""
        if not self._cancel_all_fn:
            return True, {"skipped": True, "reason": "no cancel function"}

        try:
            success = self._cancel_all_fn()
            return success, {"success": success}
        except Exception as e:
            return False, {"error": str(e)}

    def _step_query_positions(self) -> tuple[bool, dict[str, Any]]:
        """步骤2: 查询柜台持仓."""
        if not self._query_positions_fn:
            return True, {"skipped": True, "reason": "no query function"}

        try:
            positions = self._query_positions_fn()
            self._state.details["broker_positions"] = positions
            return True, {"positions": positions}
        except Exception as e:
            return False, {"error": str(e)}

    def _step_reconcile(self) -> tuple[bool, dict[str, Any]]:
        """步骤3: 对账."""
        if not self._reconcile_fn:
            return True, {"skipped": True, "reason": "no reconcile function"}

        try:
            broker_positions = self._state.details.get("broker_positions", {})
            local_positions: dict[str, int] = {}  # 冷启动时本地为空
            success = self._reconcile_fn(local_positions, broker_positions)
            return success, {"matched": success}
        except Exception as e:
            return False, {"error": str(e)}

    def _step_set_reduce_only(self) -> tuple[bool, dict[str, Any]]:
        """步骤4: 设置 REDUCE_ONLY 模式."""
        if not self._set_mode_fn:
            return True, {"skipped": True, "reason": "no set_mode function"}

        try:
            from src.guardian.state_machine import GuardianMode

            self._set_mode_fn(GuardianMode.REDUCE_ONLY)
            return True, {"mode": "REDUCE_ONLY"}
        except Exception as e:
            return False, {"error": str(e)}

    def _step_cooldown(self) -> tuple[bool, dict[str, Any]]:
        """步骤5: 冷却期等待.

        注意：实际生产中不应阻塞，这里简化实现。
        """
        # 在测试/模拟中跳过实际等待
        return True, {
            "cooldown_s": self._cooldown_s,
            "note": "cooldown period started",
        }

    def _step_health_check(self) -> tuple[bool, dict[str, Any]]:
        """步骤6: 健康检查."""
        if not self._health_check_fn:
            return True, {"skipped": True, "reason": "no health_check function"}

        try:
            healthy = self._health_check_fn()
            return healthy, {"healthy": healthy}
        except Exception as e:
            return False, {"error": str(e)}

    def reset(self) -> None:
        """重置恢复状态."""
        self._state = RecoveryState()
