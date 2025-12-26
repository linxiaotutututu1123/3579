"""
执行器基类与接口定义.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.EXECUTOR.INTERFACE: 统一执行器接口
- MODE2.EXECUTOR.PAUSE_RESUME: 暂停恢复机制
- MODE2.EXECUTOR.CANCEL: 取消执行计划

执行器接口 (军规级要求):
    make_plan(intent) -> plan_id: 生成执行计划
    next_action(plan_id) -> action | None: 获取下一个动作
    on_event(plan_id, event): 处理订单事件
    cancel_plan(plan_id): 取消计划
    pause(plan_id): 暂停执行
    resume(plan_id): 恢复执行
    get_status(plan_id) -> status: 获取状态
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.execution.mode2.intent import Offset, OrderIntent, Side


class ExecutorActionType(str, Enum):
    """执行器动作类型.

    Attributes:
        PLACE_ORDER: 下单
        CANCEL_ORDER: 撤单
        MODIFY_ORDER: 改单
        WAIT: 等待
        COMPLETE: 完成
        ABORT: 中止
    """

    PLACE_ORDER = "PLACE_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    MODIFY_ORDER = "MODIFY_ORDER"
    WAIT = "WAIT"
    COMPLETE = "COMPLETE"
    ABORT = "ABORT"


class ExecutorStatus(str, Enum):
    """执行器状态.

    Attributes:
        PENDING: 等待开始
        RUNNING: 执行中
        PAUSED: 已暂停
        COMPLETED: 已完成
        CANCELLED: 已取消
        FAILED: 已失败
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# 终态集合
TERMINAL_STATUSES = frozenset(
    [
        ExecutorStatus.COMPLETED,
        ExecutorStatus.CANCELLED,
        ExecutorStatus.FAILED,
    ]
)


@dataclass
class ExecutorAction:
    """执行器动作.

    表示执行器在某一时刻应该执行的操作。

    Attributes:
        action_type: 动作类型
        client_order_id: 客户订单ID(PLACE_ORDER/CANCEL_ORDER/MODIFY_ORDER 必填)
        instrument: 合约代码
        side: 交易方向
        offset: 开平方向
        price: 价格
        qty: 数量
        wait_until: 等待到指定时间戳(WAIT 动作)
        reason: 动作原因
        metadata: 扩展元数据
    """

    action_type: ExecutorActionType
    client_order_id: str | None = None
    instrument: str | None = None
    side: Side | None = None
    offset: Offset | None = None
    price: float | None = None
    qty: int | None = None
    wait_until: float | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        """是否是终态动作."""
        return self.action_type in (ExecutorActionType.COMPLETE, ExecutorActionType.ABORT)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "action_type": self.action_type.value,
            "client_order_id": self.client_order_id,
            "instrument": self.instrument,
            "side": self.side.value if self.side else None,
            "offset": self.offset.value if self.offset else None,
            "price": self.price,
            "qty": self.qty,
            "wait_until": self.wait_until,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class OrderEvent:
    """订单事件.

    用于通知执行器订单状态变化。

    Attributes:
        client_order_id: 客户订单ID
        event_type: 事件类型
        filled_qty: 成交数量
        filled_price: 成交价格
        remaining_qty: 剩余数量
        error_code: 错误码
        error_msg: 错误信息
        exchange_order_id: 交易所订单ID
        ts: 事件时间戳
    """

    client_order_id: str
    event_type: str  # ACK, PARTIAL_FILL, FILL, REJECT, CANCEL_ACK, CANCEL_REJECT
    filled_qty: int = 0
    filled_price: float = 0.0
    remaining_qty: int = 0
    error_code: str = ""
    error_msg: str = ""
    exchange_order_id: str = ""
    ts: float = field(default_factory=time.time)

    def is_fill(self) -> bool:
        """是否是成交事件."""
        return self.event_type in ("PARTIAL_FILL", "FILL")

    def is_terminal(self) -> bool:
        """是否是终态事件."""
        return self.event_type in ("FILL", "REJECT", "CANCEL_ACK")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "client_order_id": self.client_order_id,
            "event_type": self.event_type,
            "filled_qty": self.filled_qty,
            "filled_price": self.filled_price,
            "remaining_qty": self.remaining_qty,
            "error_code": self.error_code,
            "error_msg": self.error_msg,
            "exchange_order_id": self.exchange_order_id,
            "ts": self.ts,
        }


@dataclass
class ExecutionProgress:
    """执行进度.

    Attributes:
        total_qty: 总目标数量
        filled_qty: 已成交数量
        pending_qty: 挂单中数量
        remaining_qty: 剩余未执行数量
        slice_count: 总分片数
        completed_slices: 已完成分片数
        avg_price: 平均成交价格
        total_cost: 总成本
        start_time: 开始时间
        elapsed_time: 已用时间(秒)
    """

    total_qty: int = 0
    filled_qty: int = 0
    pending_qty: int = 0
    remaining_qty: int = 0
    slice_count: int = 0
    completed_slices: int = 0
    avg_price: float = 0.0
    total_cost: float = 0.0
    start_time: float = 0.0
    elapsed_time: float = 0.0

    @property
    def fill_ratio(self) -> float:
        """成交比例."""
        if self.total_qty == 0:
            return 0.0
        return self.filled_qty / self.total_qty

    @property
    def is_complete(self) -> bool:
        """是否已完成."""
        return self.filled_qty >= self.total_qty

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "total_qty": self.total_qty,
            "filled_qty": self.filled_qty,
            "pending_qty": self.pending_qty,
            "remaining_qty": self.remaining_qty,
            "slice_count": self.slice_count,
            "completed_slices": self.completed_slices,
            "avg_price": self.avg_price,
            "total_cost": self.total_cost,
            "start_time": self.start_time,
            "elapsed_time": self.elapsed_time,
            "fill_ratio": self.fill_ratio,
            "is_complete": self.is_complete,
        }


@dataclass
class ExecutorConfig:
    """执行器配置基类.

    Attributes:
        max_slice_qty: 单个分片最大数量
        min_slice_qty: 单个分片最小数量
        price_tolerance: 价格容忍度(滑点)
        timeout_seconds: 单个订单超时时间(秒)
        retry_count: 重试次数
        audit_enabled: 是否启用审计
    """

    max_slice_qty: int = 100
    min_slice_qty: int = 1
    price_tolerance: float = 0.0
    timeout_seconds: float = 30.0
    retry_count: int = 3
    audit_enabled: bool = True


class ExecutorBase(ABC):
    """执行器基类.

    V4PRO Scenarios:
    - MODE2.EXECUTOR.INTERFACE: 统一执行器接口
    - MODE2.EXECUTOR.PAUSE_RESUME: 暂停恢复机制
    - MODE2.EXECUTOR.CANCEL: 取消执行计划

    所有执行器必须实现此接口。
    """

    def __init__(self, config: ExecutorConfig | None = None) -> None:
        """初始化执行器.

        Args:
            config: 执行器配置
        """
        self._config = config or ExecutorConfig()
        self._plans: dict[str, ExecutionPlanContext] = {}

    @property
    def config(self) -> ExecutorConfig:
        """获取配置."""
        return self._config

    @abstractmethod
    def make_plan(self, intent: OrderIntent) -> str:
        """生成执行计划.

        V4PRO Scenario: MODE2.EXECUTOR.INTERFACE

        Args:
            intent: 交易意图

        Returns:
            计划ID (通常等于 intent_id)

        Raises:
            ValueError: 意图参数无效
        """

    @abstractmethod
    def next_action(self, plan_id: str, current_time: float | None = None) -> ExecutorAction | None:
        """获取下一个动作.

        V4PRO Scenario: MODE2.EXECUTOR.INTERFACE

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳

        Returns:
            下一个动作,None 表示当前无动作
        """

    @abstractmethod
    def on_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

        V4PRO Scenario: MODE2.EXECUTOR.INTERFACE

        Args:
            plan_id: 计划ID
            event: 订单事件
        """

    @abstractmethod
    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消计划.

        V4PRO Scenario: MODE2.EXECUTOR.CANCEL

        Args:
            plan_id: 计划ID
            reason: 取消原因

        Returns:
            是否成功取消
        """

    def pause(self, plan_id: str) -> bool:
        """暂停执行.

        V4PRO Scenario: MODE2.EXECUTOR.PAUSE_RESUME

        Args:
            plan_id: 计划ID

        Returns:
            是否成功暂停
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return False
        if ctx.status in TERMINAL_STATUSES:
            return False
        ctx.status = ExecutorStatus.PAUSED
        return True

    def resume(self, plan_id: str) -> bool:
        """恢复执行.

        V4PRO Scenario: MODE2.EXECUTOR.PAUSE_RESUME

        Args:
            plan_id: 计划ID

        Returns:
            是否成功恢复
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return False
        if ctx.status != ExecutorStatus.PAUSED:
            return False
        ctx.status = ExecutorStatus.RUNNING
        return True

    @abstractmethod
    def get_status(self, plan_id: str) -> ExecutorStatus | None:
        """获取计划状态.

        Args:
            plan_id: 计划ID

        Returns:
            状态或 None
        """

    @abstractmethod
    def get_progress(self, plan_id: str) -> ExecutionProgress | None:
        """获取执行进度.

        Args:
            plan_id: 计划ID

        Returns:
            进度或 None
        """

    def get_pending_cancel_orders(self, plan_id: str) -> list[str]:
        """获取需要撤销的挂单列表.

        V4PRO Scenario: MODE2.EXECUTOR.CANCEL

        Args:
            plan_id: 计划ID

        Returns:
            需要撤销的 client_order_id 列表
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return []
        return list(ctx.pending_orders.keys())

    def get_active_plans(self) -> list[str]:
        """获取活动计划列表.

        Returns:
            活动计划ID列表
        """
        return [
            plan_id for plan_id, ctx in self._plans.items() if ctx.status not in TERMINAL_STATUSES
        ]

    def is_plan_active(self, plan_id: str) -> bool:
        """检查计划是否活动.

        Args:
            plan_id: 计划ID

        Returns:
            是否活动
        """
        ctx = self._plans.get(plan_id)
        if ctx is None:
            return False
        return ctx.status not in TERMINAL_STATUSES


@dataclass
class ExecutionPlanContext:
    """执行计划上下文.

    存储计划的执行状态和进度信息。

    Attributes:
        plan_id: 计划ID
        intent: 交易意图
        status: 状态
        progress: 进度
        slices: 分片列表
        current_slice_index: 当前分片索引
        pending_orders: 挂单中的订单
        filled_orders: 已成交的订单
        cancelled_orders: 已撤销的订单
        error: 错误信息
        start_time: 开始时间
        end_time: 结束时间
        metadata: 扩展元数据
    """

    plan_id: str
    intent: OrderIntent
    status: ExecutorStatus = ExecutorStatus.PENDING
    progress: ExecutionProgress = field(default_factory=ExecutionProgress)
    slices: list[SliceInfo] = field(default_factory=list)
    current_slice_index: int = 0
    pending_orders: dict[str, PendingOrder] = field(default_factory=dict)
    filled_orders: list[FilledOrder] = field(default_factory=list)
    cancelled_orders: list[str] = field(default_factory=list)
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化进度."""
        self.progress.total_qty = self.intent.target_qty

    def is_terminal(self) -> bool:
        """是否终态."""
        return self.status in TERMINAL_STATUSES

    def update_progress(self) -> None:
        """更新进度."""
        self.progress.filled_qty = sum(o.filled_qty for o in self.filled_orders)
        self.progress.pending_qty = sum(o.qty for o in self.pending_orders.values())
        self.progress.remaining_qty = self.intent.target_qty - self.progress.filled_qty
        self.progress.completed_slices = self.current_slice_index
        self.progress.slice_count = len(self.slices)

        # 计算平均价格
        if self.progress.filled_qty > 0:
            total_value = sum(o.filled_qty * o.avg_price for o in self.filled_orders)
            self.progress.avg_price = total_value / self.progress.filled_qty
            self.progress.total_cost = total_value

        # 计算已用时间
        if self.start_time > 0:
            self.progress.start_time = self.start_time
            self.progress.elapsed_time = time.time() - self.start_time


@dataclass
class SliceInfo:
    """分片信息.

    Attributes:
        index: 分片索引
        qty: 分片数量
        target_price: 目标价格
        scheduled_time: 计划执行时间
        executed: 是否已执行
    """

    index: int
    qty: int
    target_price: float | None = None
    scheduled_time: float | None = None
    executed: bool = False


@dataclass
class PendingOrder:
    """挂单中的订单.

    Attributes:
        client_order_id: 客户订单ID
        qty: 数量
        price: 价格
        submit_time: 提交时间
        retry_count: 重试次数
    """

    client_order_id: str
    qty: int
    price: float
    submit_time: float
    retry_count: int = 0


@dataclass
class FilledOrder:
    """已成交的订单.

    Attributes:
        client_order_id: 客户订单ID
        filled_qty: 成交数量
        avg_price: 平均成交价格
        fill_time: 成交时间
    """

    client_order_id: str
    filled_qty: int
    avg_price: float
    fill_time: float
