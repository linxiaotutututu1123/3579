"""
GuardianMonitor - 守护主循环

V3PRO+ Platform Component - Phase 1
V2 SPEC: 6.2
V2 Scenarios:
- GUARD.MODE.REDUCE_ONLY_EFFECT: reduce_only 禁开仓
- STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 禁开仓
- STRAT.DEGRADE.HALTED_OUTPUT_ZERO: HALTED 输出零

军规级要求:
- 整合 FSM + Triggers + Actions
- REDUCE_ONLY 模式下禁止开仓
- HALTED 模式下输出零仓位
- 所有状态变更必须审计
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.guardian.actions import GuardianActions
from src.guardian.recovery import ColdStartRecovery
from src.guardian.state_machine import GuardianFSM, GuardianMode
from src.guardian.triggers import BaseTrigger, TriggerManager, TriggerResult

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class GuardianCheckResult:
    """检查结果.

    Attributes:
        mode: 当前模式
        triggered: 是否有触发
        triggers: 触发的触发器列表
        actions_taken: 执行的动作列表
        timestamp: 检查时间戳
    """

    mode: GuardianMode
    triggered: bool
    triggers: list[TriggerResult] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class GuardianMonitor:
    """守护主循环.

    V2 Scenarios:
    - GUARD.MODE.REDUCE_ONLY_EFFECT
    - STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN
    - STRAT.DEGRADE.HALTED_OUTPUT_ZERO

    整合 FSM、Triggers、Actions，实现守护主循环。
    """

    def __init__(
        self,
        fsm: GuardianFSM | None = None,
        trigger_manager: TriggerManager | None = None,
        actions: GuardianActions | None = None,
        recovery: ColdStartRecovery | None = None,
        on_mode_change: Callable[[GuardianMode, GuardianMode, str], None] | None = None,
    ) -> None:
        """初始化守护监控器.

        Args:
            fsm: 状态机（可选，默认创建新的）
            trigger_manager: 触发器管理器（可选）
            actions: 动作执行器（可选）
            recovery: 恢复器（可选）
            on_mode_change: 模式变更回调 (from, to, trigger)
        """
        self._on_mode_change = on_mode_change
        self._fsm = fsm or GuardianFSM(
            initial_mode=GuardianMode.INIT,
            on_transition=self._handle_transition,
        )
        self._trigger_manager = trigger_manager or TriggerManager()
        self._actions = actions or GuardianActions()
        self._recovery = recovery
        self._last_check_time: float = 0.0

    def _handle_transition(
        self, from_mode: GuardianMode, to_mode: GuardianMode, event: str
    ) -> None:
        """处理状态转移."""
        if self._on_mode_change:
            self._on_mode_change(from_mode, to_mode, event)

    @property
    def mode(self) -> GuardianMode:
        """当前模式."""
        return self._fsm.mode

    @property
    def fsm(self) -> GuardianFSM:
        """状态机实例."""
        return self._fsm

    @property
    def trigger_manager(self) -> TriggerManager:
        """触发器管理器."""
        return self._trigger_manager

    @property
    def actions(self) -> GuardianActions:
        """动作执行器."""
        return self._actions

    def add_trigger(self, trigger: BaseTrigger) -> None:
        """添加触发器.

        Args:
            trigger: 触发器实例
        """
        self._trigger_manager.add_trigger(trigger)

    def can_open_position(self) -> bool:
        """是否允许开仓.

        V2 Scenarios:
        - GUARD.MODE.REDUCE_ONLY_EFFECT
        - STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN

        Returns:
            仅 RUNNING 模式返回 True
        """
        return self._fsm.is_open_allowed()

    def filter_target_portfolio(
        self,
        target: dict[str, int],
        current: dict[str, int],
    ) -> dict[str, int]:
        """根据当前模式过滤目标仓位.

        V2 Scenarios:
        - STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN: REDUCE_ONLY 禁开仓
        - STRAT.DEGRADE.HALTED_OUTPUT_ZERO: HALTED 输出零

        Args:
            target: 策略输出的目标仓位
            current: 当前持仓

        Returns:
            过滤后的目标仓位
        """
        mode = self._fsm.mode

        # HALTED 或 MANUAL 模式：输出零仓位变化
        if mode in (GuardianMode.HALTED, GuardianMode.MANUAL):
            return dict(current)  # 保持当前仓位不变

        # INIT 模式：不允许任何交易
        if mode == GuardianMode.INIT:
            return dict(current)

        # RUNNING 模式：允许任何交易
        if mode == GuardianMode.RUNNING:
            return dict(target)

        # REDUCE_ONLY 模式：只允许减仓
        if mode == GuardianMode.REDUCE_ONLY:
            filtered: dict[str, int] = {}
            all_symbols = set(target.keys()) | set(current.keys())

            for symbol in all_symbols:
                target_qty = target.get(symbol, 0)
                current_qty = current.get(symbol, 0)

                # 判断是开仓还是平仓
                if current_qty == 0:
                    # 当前无仓位，不允许开仓
                    filtered[symbol] = 0
                elif current_qty > 0:
                    # 多头：只允许减仓（target <= current）
                    filtered[symbol] = min(target_qty, current_qty)
                    if filtered[symbol] < 0:
                        filtered[symbol] = 0  # 不允许翻空
                else:
                    # 空头：只允许减仓（target >= current）
                    filtered[symbol] = max(target_qty, current_qty)
                    if filtered[symbol] > 0:
                        filtered[symbol] = 0  # 不允许翻多

            return filtered

        return dict(current)

    def check(self, state: dict[str, Any]) -> GuardianCheckResult:
        """执行一次检查循环.

        Args:
            state: 当前状态字典，应包含:
                - quote_timestamps: 行情时间戳
                - active_orders: 活动订单
                - local_positions: 本地持仓
                - broker_positions: 柜台持仓
                - pair_positions: 配对持仓
                - now_ts: 当前时间戳

        Returns:
            检查结果
        """
        now_ts = state.get("now_ts", time.time())
        state["now_ts"] = now_ts
        self._last_check_time = now_ts

        # 检查所有触发器
        triggered_results = self._trigger_manager.check_all(state)

        actions_taken: list[str] = []

        # 处理触发的事件
        for result in triggered_results:
            event_name = result.event_name

            # 检查是否可以转移
            if self._fsm.can_transition(event_name):
                old_mode = self._fsm.mode
                new_mode = self._fsm.transition(event_name)

                # 记录模式变更动作
                self._actions.set_mode(new_mode, event_name)
                actions_taken.append(f"set_mode:{new_mode.name}")

                # 根据新模式执行额外动作
                if new_mode == GuardianMode.HALTED:
                    # HALTED 时撤销所有订单
                    self._actions.cancel_all()
                    actions_taken.append("cancel_all")

        return GuardianCheckResult(
            mode=self._fsm.mode,
            triggered=len(triggered_results) > 0,
            triggers=triggered_results,
            actions_taken=actions_taken,
            timestamp=now_ts,
        )

    def initialize(self) -> bool:
        """初始化守护监控器.

        执行初始化流程，成功后进入 RUNNING 状态。

        Returns:
            是否初始化成功
        """
        if self._fsm.mode != GuardianMode.INIT:
            return False

        try:
            # 如果有恢复器，执行恢复流程
            if self._recovery:
                state = self._recovery.start()
                if state.status.value == "completed":
                    self._fsm.transition("init_success")
                    return True
                else:
                    self._fsm.transition("init_failed")
                    return False

            # 无恢复器，直接进入 RUNNING
            self._fsm.transition("init_success")
            return True

        except Exception:
            if self._fsm.can_transition("init_failed"):
                self._fsm.transition("init_failed")
            return False

    def manual_set_mode(self, mode: GuardianMode, reason: str = "") -> bool:
        """手动设置模式.

        Args:
            mode: 目标模式
            reason: 原因

        Returns:
            是否成功
        """
        current = self._fsm.mode

        # 确定事件名
        event_map = {
            GuardianMode.HALTED: "manual_halt",
            GuardianMode.MANUAL: "manual_takeover",
            GuardianMode.RUNNING: "manual_release",
        }

        event = event_map.get(mode)
        if not event or not self._fsm.can_transition(event):
            # 使用强制模式
            self._fsm.force_mode(mode, reason or "manual_override")
            return True

        self._fsm.transition(event)
        return True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            状态信息字典
        """
        return {
            "mode": self._fsm.mode.name,
            "mode_value": self._fsm.mode.value,
            "can_open_position": self.can_open_position(),
            "transition_count": self._fsm.transition_count,
            "last_check_time": self._last_check_time,
        }
