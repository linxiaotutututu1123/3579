"""
GuardianFSM - 守护状态机

V3PRO+ Platform Component - Phase 1
V2 SPEC: 6.1
V2 Scenarios: GUARD.FSM.TRANSITIONS

军规级要求:
- 状态转移必须严格按照转移表
- 每次转移必须写入审计日志
- 状态不可逆向跳转（除 MANUAL→RUNNING）
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class GuardianMode(IntEnum):
    """守护模式枚举.

    V2 SPEC 6.1 定义的状态：
    - INIT: 初始化中
    - RUNNING: 正常运行，允许开仓
    - REDUCE_ONLY: 仅允许减仓/平仓
    - HALTED: 停止交易，等待人工
    - MANUAL: 人工接管
    """

    INIT = 0
    RUNNING = 1
    REDUCE_ONLY = 2
    HALTED = 3
    MANUAL = 4


# 合法的状态转移表
# (from_state, event) -> to_state
VALID_TRANSITIONS: dict[tuple[GuardianMode, str], GuardianMode] = {
    # INIT 状态转移
    (GuardianMode.INIT, "init_success"): GuardianMode.RUNNING,
    (GuardianMode.INIT, "init_failed"): GuardianMode.HALTED,
    # RUNNING 状态转移
    (GuardianMode.RUNNING, "quote_stale"): GuardianMode.REDUCE_ONLY,
    (GuardianMode.RUNNING, "order_stuck"): GuardianMode.REDUCE_ONLY,
    (GuardianMode.RUNNING, "leg_imbalance"): GuardianMode.REDUCE_ONLY,
    (GuardianMode.RUNNING, "position_drift"): GuardianMode.HALTED,
    (GuardianMode.RUNNING, "manual_halt"): GuardianMode.HALTED,
    (GuardianMode.RUNNING, "manual_takeover"): GuardianMode.MANUAL,
    # REDUCE_ONLY 状态转移
    (GuardianMode.REDUCE_ONLY, "recovered"): GuardianMode.RUNNING,
    (GuardianMode.REDUCE_ONLY, "degraded"): GuardianMode.HALTED,
    (GuardianMode.REDUCE_ONLY, "manual_halt"): GuardianMode.HALTED,
    (GuardianMode.REDUCE_ONLY, "manual_takeover"): GuardianMode.MANUAL,
    # HALTED 状态转移
    (GuardianMode.HALTED, "manual_takeover"): GuardianMode.MANUAL,
    # MANUAL 状态转移
    (GuardianMode.MANUAL, "manual_release"): GuardianMode.RUNNING,
    (GuardianMode.MANUAL, "manual_halt"): GuardianMode.HALTED,
}


class TransitionError(Exception):
    """状态转移错误."""

    pass


class GuardianFSM:
    """守护状态机.

    V2 Scenario: GUARD.FSM.TRANSITIONS

    实现 Guardian 的状态转移逻辑。
    """

    def __init__(
        self,
        initial_mode: GuardianMode = GuardianMode.INIT,
        on_transition: Callable[[GuardianMode, GuardianMode, str], None] | None = None,
    ) -> None:
        """初始化状态机.

        Args:
            initial_mode: 初始状态
            on_transition: 状态转移回调 (from, to, event)
        """
        self._mode = initial_mode
        self._on_transition = on_transition
        self._transition_count = 0

    @property
    def mode(self) -> GuardianMode:
        """当前模式."""
        return self._mode

    @property
    def transition_count(self) -> int:
        """状态转移次数."""
        return self._transition_count

    def can_transition(self, event: str) -> bool:
        """检查是否可以转移.

        Args:
            event: 触发事件

        Returns:
            是否可以转移
        """
        return (self._mode, event) in VALID_TRANSITIONS

    def get_next_mode(self, event: str) -> GuardianMode | None:
        """获取下一个状态（不执行转移）.

        Args:
            event: 触发事件

        Returns:
            下一个状态，或 None 如果不可转移
        """
        return VALID_TRANSITIONS.get((self._mode, event))

    def transition(self, event: str) -> GuardianMode:
        """执行状态转移.

        V2 Scenario: GUARD.FSM.TRANSITIONS

        Args:
            event: 触发事件

        Returns:
            新状态

        Raises:
            TransitionError: 非法转移
        """
        key = (self._mode, event)
        if key not in VALID_TRANSITIONS:
            raise TransitionError(
                f"Invalid transition: {self._mode.name} + {event}"
            )

        from_mode = self._mode
        to_mode = VALID_TRANSITIONS[key]
        self._mode = to_mode
        self._transition_count += 1

        if self._on_transition:
            self._on_transition(from_mode, to_mode, event)

        return to_mode

    def force_mode(self, mode: GuardianMode, reason: str = "forced") -> None:
        """强制设置模式（仅用于恢复/测试）.

        Args:
            mode: 目标模式
            reason: 原因
        """
        from_mode = self._mode
        self._mode = mode
        self._transition_count += 1

        if self._on_transition:
            self._on_transition(from_mode, mode, f"force:{reason}")

    def is_trading_allowed(self) -> bool:
        """是否允许交易.

        Returns:
            RUNNING 或 REDUCE_ONLY 时返回 True
        """
        return self._mode in (GuardianMode.RUNNING, GuardianMode.REDUCE_ONLY)

    def is_open_allowed(self) -> bool:
        """是否允许开仓.

        V2 Scenario: GUARD.MODE.REDUCE_ONLY_EFFECT

        Returns:
            仅 RUNNING 时返回 True
        """
        return self._mode == GuardianMode.RUNNING

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            状态信息字典
        """
        return {
            "mode": self._mode.name,
            "mode_value": self._mode.value,
            "transition_count": self._transition_count,
            "trading_allowed": self.is_trading_allowed(),
            "open_allowed": self.is_open_allowed(),
        }
