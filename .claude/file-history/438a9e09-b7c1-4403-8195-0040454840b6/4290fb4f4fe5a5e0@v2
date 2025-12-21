"""
Guardian Triggers - 异常检测器

V3PRO+ Platform Component - Phase 1
V2 SPEC: 6.2
V2 Scenarios:
- GUARD.DETECT.QUOTE_STALE: 行情 stale 检测
- GUARD.DETECT.ORDER_STUCK: 订单卡住检测
- GUARD.DETECT.POSITION_DRIFT: 持仓漂移检测
- GUARD.DETECT.LEG_IMBALANCE: 腿不平衡检测

军规级要求:
- 检测必须有明确阈值
- 触发必须产生事件
- 可配置参数
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    pass


@dataclass
class TriggerResult:
    """触发器检测结果.

    Attributes:
        triggered: 是否触发
        trigger_name: 触发器名称
        event_name: 事件名称（用于 FSM 转移）
        details: 详细信息
    """

    triggered: bool
    trigger_name: str
    event_name: str
    details: dict[str, Any] = field(default_factory=dict)


class BaseTrigger(ABC):
    """触发器基类."""

    @property
    @abstractmethod
    def name(self) -> str:
        """触发器名称."""
        ...

    @abstractmethod
    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查是否触发.

        Args:
            state: 当前状态字典

        Returns:
            检测结果
        """
        ...

    def reset(self) -> None:  # noqa: B027
        """重置触发器状态（可选覆盖）."""


class QuoteStaleTrigger(BaseTrigger):
    """行情 stale 检测器.

    V2 Scenario: GUARD.DETECT.QUOTE_STALE

    检测行情是否过期。
    """

    def __init__(
        self,
        hard_stale_ms: float = 10000.0,
        symbols: list[str] | None = None,
    ) -> None:
        """初始化检测器.

        Args:
            hard_stale_ms: 硬 stale 阈值（毫秒）
            symbols: 需监控的合约列表（None 表示全部）
        """
        self._hard_stale_ms = hard_stale_ms
        self._symbols = symbols

    @property
    def name(self) -> str:
        """触发器名称."""
        return "quote_stale"

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查行情是否 stale.

        Args:
            state: 状态字典，需包含:
                - quote_timestamps: dict[str, float] 合约最后更新时间戳
                - now_ts: float 当前时间戳

        Returns:
            检测结果
        """
        quote_timestamps = state.get("quote_timestamps", {})
        now_ts = state.get("now_ts", time.time())

        stale_symbols: list[str] = []
        symbols_to_check = self._symbols or list(quote_timestamps.keys())

        for symbol in symbols_to_check:
            last_ts = quote_timestamps.get(symbol)
            if last_ts is None:
                stale_symbols.append(symbol)
                continue

            elapsed_ms = (now_ts - last_ts) * 1000
            if elapsed_ms > self._hard_stale_ms:
                stale_symbols.append(symbol)

        triggered = len(stale_symbols) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="quote_stale",
            details={
                "stale_symbols": stale_symbols,
                "threshold_ms": self._hard_stale_ms,
            },
        )


class OrderStuckTrigger(BaseTrigger):
    """订单卡住检测器.

    V2 Scenario: GUARD.DETECT.ORDER_STUCK

    检测订单是否长时间未推进。
    """

    def __init__(
        self,
        stuck_timeout_s: float = 120.0,
    ) -> None:
        """初始化检测器.

        Args:
            stuck_timeout_s: 卡单超时（秒）
        """
        self._stuck_timeout_s = stuck_timeout_s

    @property
    def name(self) -> str:
        """触发器名称."""
        return "order_stuck"

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查订单是否卡住.

        Args:
            state: 状态字典，需包含:
                - active_orders: list[dict] 活动订单列表
                - now_ts: float 当前时间戳

        Returns:
            检测结果
        """
        active_orders = state.get("active_orders", [])
        now_ts = state.get("now_ts", time.time())

        stuck_orders: list[str] = []

        for order in active_orders:
            last_update_ts = order.get("last_update_ts", order.get("created_ts", 0))
            elapsed_s = now_ts - last_update_ts

            if elapsed_s > self._stuck_timeout_s:
                stuck_orders.append(order.get("order_id", "unknown"))

        triggered = len(stuck_orders) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="order_stuck",
            details={
                "stuck_orders": stuck_orders,
                "threshold_s": self._stuck_timeout_s,
            },
        )


class PositionDriftTrigger(BaseTrigger):
    """持仓漂移检测器.

    V2 Scenario: GUARD.DETECT.POSITION_DRIFT

    检测本地持仓与柜台持仓是否一致。
    """

    def __init__(self, tolerance: int = 0) -> None:
        """初始化检测器.

        Args:
            tolerance: 允许的差异容忍度
        """
        self._tolerance = tolerance

    @property
    def name(self) -> str:
        """触发器名称."""
        return "position_drift"

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查持仓是否漂移.

        Args:
            state: 状态字典，需包含:
                - local_positions: dict[str, int] 本地持仓
                - broker_positions: dict[str, int] 柜台持仓

        Returns:
            检测结果
        """
        local_positions = state.get("local_positions", {})
        broker_positions = state.get("broker_positions", {})

        all_symbols = set(local_positions.keys()) | set(broker_positions.keys())
        drifted_symbols: list[dict[str, Any]] = []

        for symbol in all_symbols:
            local_qty = local_positions.get(symbol, 0)
            broker_qty = broker_positions.get(symbol, 0)
            diff = abs(local_qty - broker_qty)

            if diff > self._tolerance:
                drifted_symbols.append(
                    {
                        "symbol": symbol,
                        "local": local_qty,
                        "broker": broker_qty,
                        "diff": diff,
                    }
                )

        triggered = len(drifted_symbols) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="position_drift",
            details={
                "drifted_positions": drifted_symbols,
                "tolerance": self._tolerance,
            },
        )


class LegImbalanceTrigger(BaseTrigger):
    """腿不平衡检测器.

    V2 Scenario: GUARD.DETECT.LEG_IMBALANCE

    检测套利策略的腿是否不平衡。
    """

    def __init__(self, threshold: int = 10) -> None:
        """初始化检测器.

        Args:
            threshold: 不平衡阈值（手数）
        """
        self._threshold = threshold

    @property
    def name(self) -> str:
        """触发器名称."""
        return "leg_imbalance"

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查腿是否不平衡.

        Args:
            state: 状态字典，需包含:
                - pair_positions: list[dict] 配对持仓列表
                  每个配对包含 {near_symbol, far_symbol, near_qty, far_qty}

        Returns:
            检测结果
        """
        pair_positions = state.get("pair_positions", [])

        imbalanced_pairs: list[dict[str, Any]] = []

        for pair in pair_positions:
            near_qty = pair.get("near_qty", 0)
            far_qty = pair.get("far_qty", 0)
            imbalance = abs(near_qty) - abs(far_qty)

            if abs(imbalance) > self._threshold:
                imbalanced_pairs.append(
                    {
                        "near_symbol": pair.get("near_symbol"),
                        "far_symbol": pair.get("far_symbol"),
                        "near_qty": near_qty,
                        "far_qty": far_qty,
                        "imbalance": imbalance,
                    }
                )

        triggered = len(imbalanced_pairs) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="leg_imbalance",
            details={
                "imbalanced_pairs": imbalanced_pairs,
                "threshold": self._threshold,
            },
        )


class TriggerManager:
    """触发器管理器.

    管理多个触发器的检测。
    """

    def __init__(self, triggers: list[BaseTrigger] | None = None) -> None:
        """初始化管理器.

        Args:
            triggers: 触发器列表
        """
        self._triggers = triggers or []

    def add_trigger(self, trigger: BaseTrigger) -> None:
        """添加触发器.

        Args:
            trigger: 触发器实例
        """
        self._triggers.append(trigger)

    def remove_trigger(self, name: str) -> bool:
        """移除触发器.

        Args:
            name: 触发器名称

        Returns:
            是否成功移除
        """
        for i, trigger in enumerate(self._triggers):
            if trigger.name == name:
                self._triggers.pop(i)
                return True
        return False

    def check_all(self, state: dict[str, Any]) -> list[TriggerResult]:
        """检查所有触发器.

        Args:
            state: 当前状态

        Returns:
            所有触发的结果列表
        """
        results: list[TriggerResult] = []
        for trigger in self._triggers:
            result = trigger.check(state)
            if result.triggered:
                results.append(result)
        return results

    def reset_all(self) -> None:
        """重置所有触发器."""
        for trigger in self._triggers:
            trigger.reset()
