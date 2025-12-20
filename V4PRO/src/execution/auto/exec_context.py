"""
ExecContext - 执行上下文.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.6
V2 Scenario: EXEC.CONTEXT.TRACKING

军规级要求:
- 一次调仓意图的完整追踪
- 关联所有订单
- 支持审计追溯
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecStatus(Enum):
    """执行状态."""

    PENDING = "PENDING"  # 待执行
    RUNNING = "RUNNING"  # 执行中
    COMPLETED = "COMPLETED"  # 完成
    PARTIAL = "PARTIAL"  # 部分完成
    FAILED = "FAILED"  # 失败
    CANCELLED = "CANCELLED"  # 取消


@dataclass
class ExecOrder:
    """执行中的订单.

    Attributes:
        local_id: 本地订单 ID
        symbol: 合约代码
        direction: 方向
        target_qty: 目标数量
        filled_qty: 已成交数量
        status: 状态
    """

    local_id: str
    symbol: str
    direction: str
    target_qty: int
    filled_qty: int = 0
    status: str = "PENDING"

    def is_complete(self) -> bool:
        """是否完成."""
        return self.filled_qty >= self.target_qty

    def remaining_qty(self) -> int:
        """剩余数量."""
        return max(0, self.target_qty - self.filled_qty)


@dataclass
class ExecContext:
    """执行上下文.

    V2 Scenario: EXEC.CONTEXT.TRACKING

    追踪一次调仓意图的完整执行过程。

    Attributes:
        exec_id: 执行 ID（UUID）
        run_id: 运行 ID
        strategy_id: 策略 ID
        target_portfolio: 目标组合 {symbol: qty}
        current_portfolio: 当前组合 {symbol: qty}
        orders: 关联订单列表
        status: 执行状态
        created_at: 创建时间戳
        started_at: 开始时间戳
        completed_at: 完成时间戳
        error: 错误信息
    """

    run_id: str
    strategy_id: str
    target_portfolio: dict[str, int]
    current_portfolio: dict[str, int]
    exec_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    orders: list[ExecOrder] = field(default_factory=list)
    status: ExecStatus = ExecStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_order(self, order: ExecOrder) -> None:
        """添加订单.

        Args:
            order: 执行订单
        """
        self.orders.append(order)

    def get_order(self, local_id: str) -> ExecOrder | None:
        """获取订单.

        Args:
            local_id: 本地订单 ID

        Returns:
            执行订单或 None
        """
        for order in self.orders:
            if order.local_id == local_id:
                return order
        return None

    def update_order(self, local_id: str, filled_qty: int, status: str) -> bool:
        """更新订单.

        Args:
            local_id: 本地订单 ID
            filled_qty: 已成交数量
            status: 状态

        Returns:
            是否更新成功
        """
        order = self.get_order(local_id)
        if order is None:
            return False

        order.filled_qty = filled_qty
        order.status = status
        return True

    def start(self) -> None:
        """开始执行."""
        self.status = ExecStatus.RUNNING
        self.started_at = time.time()

    def complete(self) -> None:
        """完成执行."""
        self.status = ExecStatus.COMPLETED
        self.completed_at = time.time()

    def partial_complete(self) -> None:
        """部分完成."""
        self.status = ExecStatus.PARTIAL
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        """执行失败.

        Args:
            error: 错误信息
        """
        self.status = ExecStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def cancel(self) -> None:
        """取消执行."""
        self.status = ExecStatus.CANCELLED
        self.completed_at = time.time()

    def get_delta(self) -> dict[str, int]:
        """获取调仓差异.

        Returns:
            {symbol: delta_qty}
        """
        delta: dict[str, int] = {}
        all_symbols = set(self.target_portfolio.keys()) | set(
            self.current_portfolio.keys()
        )

        for symbol in all_symbols:
            target = self.target_portfolio.get(symbol, 0)
            current = self.current_portfolio.get(symbol, 0)
            if target != current:
                delta[symbol] = target - current

        return delta

    def get_progress(self) -> tuple[int, int]:
        """获取执行进度.

        Returns:
            (completed_orders, total_orders)
        """
        completed = sum(1 for o in self.orders if o.is_complete())
        return completed, len(self.orders)

    def get_fill_rate(self) -> float:
        """获取成交率.

        Returns:
            成交率 (0-1)
        """
        if not self.orders:
            return 0.0

        total_target = sum(o.target_qty for o in self.orders)
        total_filled = sum(o.filled_qty for o in self.orders)

        if total_target == 0:
            return 1.0

        return total_filled / total_target

    def is_complete(self) -> bool:
        """是否完成."""
        return self.status in (ExecStatus.COMPLETED, ExecStatus.PARTIAL)

    def is_running(self) -> bool:
        """是否运行中."""
        return self.status == ExecStatus.RUNNING

    def duration_s(self) -> float:
        """执行时长（秒）.

        Returns:
            执行时长
        """
        if self.started_at == 0:
            return 0.0

        end = self.completed_at if self.completed_at > 0 else time.time()
        return end - self.started_at

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "exec_id": self.exec_id,
            "run_id": self.run_id,
            "strategy_id": self.strategy_id,
            "target_portfolio": self.target_portfolio,
            "current_portfolio": self.current_portfolio,
            "status": self.status.value,
            "order_count": len(self.orders),
            "progress": self.get_progress(),
            "fill_rate": self.get_fill_rate(),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_s": self.duration_s(),
            "error": self.error,
        }


class ExecContextManager:
    """执行上下文管理器.

    管理多个执行上下文，支持:
    - 创建新上下文
    - 查询上下文
    - 历史记录
    """

    def __init__(self, max_history: int = 100) -> None:
        """初始化管理器.

        Args:
            max_history: 最大历史记录数
        """
        self._contexts: dict[str, ExecContext] = {}
        self._history: list[ExecContext] = []
        self._max_history = max_history

    def create(
        self,
        run_id: str,
        strategy_id: str,
        target_portfolio: dict[str, int],
        current_portfolio: dict[str, int],
    ) -> ExecContext:
        """创建执行上下文.

        Args:
            run_id: 运行 ID
            strategy_id: 策略 ID
            target_portfolio: 目标组合
            current_portfolio: 当前组合

        Returns:
            执行上下文
        """
        ctx = ExecContext(
            run_id=run_id,
            strategy_id=strategy_id,
            target_portfolio=target_portfolio,
            current_portfolio=current_portfolio,
        )
        self._contexts[ctx.exec_id] = ctx
        return ctx

    def get(self, exec_id: str) -> ExecContext | None:
        """获取执行上下文.

        Args:
            exec_id: 执行 ID

        Returns:
            执行上下文或 None
        """
        return self._contexts.get(exec_id)

    def get_active(self) -> list[ExecContext]:
        """获取活动的执行上下文.

        Returns:
            活动上下文列表
        """
        return [c for c in self._contexts.values() if c.is_running()]

    def complete(self, exec_id: str) -> bool:
        """完成执行上下文.

        Args:
            exec_id: 执行 ID

        Returns:
            是否成功
        """
        ctx = self._contexts.pop(exec_id, None)
        if ctx is None:
            return False

        self._history.append(ctx)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return True

    def get_history(self, limit: int = 10) -> list[ExecContext]:
        """获取历史记录.

        Args:
            limit: 数量限制

        Returns:
            历史上下文列表
        """
        return self._history[-limit:]

    def __len__(self) -> int:
        """返回活动上下文数量."""
        return len(self._contexts)
