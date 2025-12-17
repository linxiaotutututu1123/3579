"""
执行引擎 (ExecutionEngine).

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M1(单一信号源), M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- MODE2.ENGINE.SUBMIT: 意图提交与幂等检查
- MODE2.ENGINE.DISPATCH: 执行器分发
- MODE2.ENGINE.LIFECYCLE: 生命周期管理
- MODE2.ENGINE.AUDIT: 审计日志集成

执行引擎核心职责:
1. 接收策略层的 OrderIntent
2. 幂等检查(拒绝重复意图)
3. 选择合适的执行器
4. 管理执行生命周期
5. 记录完整审计日志

军规级要求:
- 每个 intent_id 只能执行一次 (M2)
- 所有执行步骤必须审计 (M3)
- 执行前必须通过成本检查 (M5)
- 执行结果必须可回放验证 (M7)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.execution.mode2.audit_events import (
    Mode2AuditEvent,
    create_intent_completed_event,
    create_intent_created_event,
    create_intent_failed_event,
    create_intent_rejected_event,
    create_plan_cancelled_event,
    create_plan_created_event,
    create_plan_paused_event,
    create_plan_resumed_event,
    create_slice_ack_event,
    create_slice_cancelled_event,
    create_slice_filled_event,
    create_slice_rejected_event,
    create_slice_sent_event,
)
from src.execution.mode2.executor_base import (
    ExecutionProgress,
    ExecutorAction,
    ExecutorActionType,
    ExecutorBase,
    ExecutorStatus,
    OrderEvent,
)
from src.execution.mode2.executor_iceberg import IcebergConfig, IcebergExecutor
from src.execution.mode2.executor_immediate import ImmediateExecutor
from src.execution.mode2.executor_twap import TWAPConfig, TWAPExecutor
from src.execution.mode2.executor_vwap import VWAPConfig, VWAPExecutor
from src.execution.mode2.intent import (
    AlgoType,
    IntentRegistry,
    OrderIntent,
    Urgency,
)


logger = logging.getLogger(__name__)


class ExecutionPlanStatus(str, Enum):
    """执行计划状态.

    Attributes:
        PENDING: 等待执行
        ACTIVE: 执行中
        PAUSED: 已暂停
        COMPLETED: 已完成
        CANCELLED: 已取消
        FAILED: 已失败
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class ExecutionPlan:
    """执行计划.

    V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

    Attributes:
        plan_id: 计划ID(等于 intent_id)
        intent: 交易意图
        algo: 执行算法
        executor_type: 执行器类型名称
        status: 计划状态
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        filled_qty: 成交数量
        avg_price: 平均价格
        error: 错误信息
        metadata: 扩展元数据
    """

    plan_id: str
    intent: OrderIntent
    algo: AlgoType
    executor_type: str
    status: ExecutionPlanStatus = ExecutionPlanStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    filled_qty: int = 0
    avg_price: float = 0.0
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            包含所有字段的字典
        """
        return {
            "plan_id": self.plan_id,
            "intent": self.intent.to_dict(),
            "algo": self.algo.value,
            "executor_type": self.executor_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "filled_qty": self.filled_qty,
            "avg_price": self.avg_price,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionEngineConfig:
    """执行引擎配置.

    Attributes:
        enable_audit: 是否启用审计
        enable_cost_check: 是否启用成本检查
        default_timeout_seconds: 默认订单超时时间
        max_concurrent_plans: 最大并发计划数
        twap_config: TWAP 执行器配置
        vwap_config: VWAP 执行器配置
        iceberg_config: 冰山单执行器配置
    """

    enable_audit: bool = True
    enable_cost_check: bool = True
    default_timeout_seconds: float = 30.0
    max_concurrent_plans: int = 100
    twap_config: TWAPConfig = field(default_factory=TWAPConfig)
    vwap_config: VWAPConfig = field(default_factory=VWAPConfig)
    iceberg_config: IcebergConfig = field(default_factory=IcebergConfig)


# 审计回调类型
AuditCallback = Callable[[Mode2AuditEvent], None]

# 成本检查回调类型
CostCheckCallback = Callable[[OrderIntent], tuple[bool, str]]


class ExecutionEngine:
    """执行引擎.

    V4PRO Scenarios:
    - MODE2.ENGINE.SUBMIT: 意图提交与幂等检查
    - MODE2.ENGINE.DISPATCH: 执行器分发
    - MODE2.ENGINE.LIFECYCLE: 生命周期管理
    - MODE2.ENGINE.AUDIT: 审计日志集成

    核心职责:
    1. 管理意图注册表(幂等检查)
    2. 创建和分发执行器
    3. 协调执行生命周期
    4. 集成审计日志

    军规级要求:
    - 每个 intent_id 只能执行一次 (M2)
    - 所有执行步骤必须审计 (M3)
    - 执行结果必须可回放验证 (M7)
    """

    def __init__(
        self,
        config: ExecutionEngineConfig | None = None,
        audit_callback: AuditCallback | None = None,
        cost_check_callback: CostCheckCallback | None = None,
    ) -> None:
        """初始化执行引擎.

        Args:
            config: 引擎配置
            audit_callback: 审计回调函数
            cost_check_callback: 成本检查回调函数
        """
        self._config = config or ExecutionEngineConfig()
        self._audit_callback = audit_callback
        self._cost_check_callback = cost_check_callback

        # 意图注册表(幂等检查)
        self._registry = IntentRegistry()

        # 执行计划映射
        self._plans: dict[str, ExecutionPlan] = {}

        # 执行器映射
        self._executors: dict[str, ExecutorBase] = {}

        # 初始化执行器实例
        self._immediate_executor = ImmediateExecutor()
        self._twap_executor = TWAPExecutor(self._config.twap_config)
        self._vwap_executor = VWAPExecutor(self._config.vwap_config)
        self._iceberg_executor = IcebergExecutor(self._config.iceberg_config)

    def submit_intent(self, intent: OrderIntent) -> tuple[bool, str]:
        """提交交易意图.

        V4PRO Scenario: MODE2.ENGINE.SUBMIT

        幂等检查后创建执行计划。

        Args:
            intent: 交易意图

        Returns:
            (是否成功, 计划ID或错误信息)
        """
        intent_id = intent.intent_id

        # 幂等检查
        if self._registry.is_registered(intent_id):
            error_msg = f"意图已存在: {intent_id} (M2 幂等检查)"
            self._emit_audit(create_intent_rejected_event(intent, "DUPLICATE_INTENT", error_msg))
            logger.warning(error_msg)
            return False, error_msg

        # 检查意图是否过期
        if intent.is_expired():
            error_msg = f"意图已过期: {intent_id}"
            self._emit_audit(create_intent_rejected_event(intent, "INTENT_EXPIRED", error_msg))
            logger.warning(error_msg)
            return False, error_msg

        # 成本检查 (M5)
        if self._config.enable_cost_check and self._cost_check_callback:
            passed, reason = self._cost_check_callback(intent)
            if not passed:
                error_msg = f"成本检查失败: {reason} (M5)"
                self._emit_audit(
                    create_intent_rejected_event(intent, "COST_CHECK_FAILED", error_msg)
                )
                logger.warning(error_msg)
                return False, error_msg

        # 检查并发计划数
        active_count = sum(
            1
            for p in self._plans.values()
            if p.status in (ExecutionPlanStatus.PENDING, ExecutionPlanStatus.ACTIVE)
        )
        if active_count >= self._config.max_concurrent_plans:
            error_msg = f"并发计划数超限: {active_count} >= {self._config.max_concurrent_plans}"
            self._emit_audit(
                create_intent_rejected_event(intent, "MAX_CONCURRENT_EXCEEDED", error_msg)
            )
            logger.warning(error_msg)
            return False, error_msg

        # 注册意图
        self._registry.register(intent)

        # 审计: 意图创建
        self._emit_audit(create_intent_created_event(intent))

        # 选择执行器
        executor = self._select_executor(intent)
        executor_type = type(executor).__name__

        # 创建执行计划
        plan_id = executor.make_plan(intent)

        # 审计: 计划创建
        progress = executor.get_progress(plan_id)
        slice_count = progress.slice_count if progress else 1
        self._emit_audit(create_plan_created_event(intent, plan_id, slice_count, intent.algo.value))

        # 记录计划
        plan = ExecutionPlan(
            plan_id=plan_id,
            intent=intent,
            algo=intent.algo,
            executor_type=executor_type,
            status=ExecutionPlanStatus.PENDING,
        )
        self._plans[plan_id] = plan
        self._executors[plan_id] = executor

        logger.info(f"意图提交成功: {intent_id}, 执行器: {executor_type}")

        return True, plan_id

    def _select_executor(self, intent: OrderIntent) -> ExecutorBase:
        """选择执行器.

        V4PRO Scenario: MODE2.ENGINE.DISPATCH

        根据算法类型和紧急程度选择合适的执行器。

        Args:
            intent: 交易意图

        Returns:
            执行器实例
        """
        # CRITICAL 紧急度强制使用立即执行
        if intent.urgency == Urgency.CRITICAL:
            return self._immediate_executor

        # 根据算法类型选择
        algo_executor_map = {
            AlgoType.IMMEDIATE: self._immediate_executor,
            AlgoType.TWAP: self._twap_executor,
            AlgoType.VWAP: self._vwap_executor,
            AlgoType.ICEBERG: self._iceberg_executor,
            AlgoType.POV: self._vwap_executor,  # POV 暂用 VWAP
            AlgoType.ADAPTIVE: self._twap_executor,  # ADAPTIVE 暂用 TWAP
        }

        return algo_executor_map.get(intent.algo, self._immediate_executor)

    def get_next_action(
        self, plan_id: str, current_time: float | None = None
    ) -> ExecutorAction | None:
        """获取下一个执行动作.

        V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

        Args:
            plan_id: 计划ID
            current_time: 当前时间戳

        Returns:
            下一个动作,None 表示无动作
        """
        executor = self._executors.get(plan_id)
        plan = self._plans.get(plan_id)

        if executor is None or plan is None:
            return None

        action = executor.next_action(plan_id, current_time)

        if action is None:
            return None

        # 更新计划状态
        if action.action_type == ExecutorActionType.PLACE_ORDER:
            if plan.status == ExecutionPlanStatus.PENDING:
                plan.status = ExecutionPlanStatus.ACTIVE
                plan.started_at = time.time()

            # 审计: 分片发送
            if action.client_order_id:
                self._emit_audit(
                    create_slice_sent_event(
                        intent_id=plan.intent.intent_id,
                        plan_id=plan_id,
                        client_order_id=action.client_order_id,
                        slice_index=action.metadata.get("slice_index", 0),
                        instrument=action.instrument or "",
                        side=action.side.value if action.side else "",
                        offset=action.offset.value if action.offset else "",
                        qty=action.qty or 0,
                        price=action.price or 0.0,
                    )
                )

        elif action.action_type == ExecutorActionType.COMPLETE:
            plan.status = ExecutionPlanStatus.COMPLETED
            plan.completed_at = time.time()

            # 更新成交信息
            progress = executor.get_progress(plan_id)
            if progress:
                plan.filled_qty = progress.filled_qty
                plan.avg_price = progress.avg_price

            # 标记意图完成
            self._registry.mark_completed(plan.intent.intent_id)

            # 审计: 意图完成
            self._emit_audit(
                create_intent_completed_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    filled_qty=plan.filled_qty,
                    avg_price=plan.avg_price,
                    total_cost=progress.total_cost if progress else 0.0,
                    slice_count=progress.slice_count if progress else 0,
                    elapsed_seconds=plan.completed_at - plan.started_at
                    if plan.started_at > 0
                    else 0.0,
                )
            )

            logger.info(
                f"计划执行完成: {plan_id}, 成交={plan.filled_qty}, 均价={plan.avg_price:.4f}"
            )

        elif action.action_type == ExecutorActionType.ABORT:
            plan.status = ExecutionPlanStatus.FAILED
            plan.completed_at = time.time()
            plan.error = action.reason

            # 标记意图失败
            self._registry.mark_failed(plan.intent.intent_id)

            # 更新成交信息
            progress = executor.get_progress(plan_id)
            if progress:
                plan.filled_qty = progress.filled_qty
                plan.avg_price = progress.avg_price

            # 审计: 意图失败
            self._emit_audit(
                create_intent_failed_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    filled_qty=plan.filled_qty,
                    remaining_qty=plan.intent.target_qty - plan.filled_qty,
                    error_code="EXECUTION_FAILED",
                    error_msg=action.reason,
                )
            )

            logger.warning(f"计划执行失败: {plan_id}, 原因: {action.reason}")

        elif action.action_type == ExecutorActionType.CANCEL_ORDER:
            # 审计: 分片取消(撤单请求)
            if action.client_order_id:
                self._emit_audit(
                    create_slice_cancelled_event(
                        intent_id=plan.intent.intent_id,
                        plan_id=plan_id,
                        client_order_id=action.client_order_id,
                        slice_index=action.metadata.get("slice_index", -1),
                        reason=action.reason,
                    )
                )

        return action

    def on_order_event(self, plan_id: str, event: OrderEvent) -> None:
        """处理订单事件.

        V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

        Args:
            plan_id: 计划ID
            event: 订单事件
        """
        executor = self._executors.get(plan_id)
        plan = self._plans.get(plan_id)

        if executor is None or plan is None:
            logger.warning(f"未找到计划: {plan_id}")
            return

        # 分发事件给执行器
        executor.on_event(plan_id, event)

        # 审计
        if event.event_type == "ACK":
            self._emit_audit(
                create_slice_ack_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    client_order_id=event.client_order_id,
                    slice_index=self._parse_slice_index(event.client_order_id),
                    exchange_order_id=event.exchange_order_id,
                )
            )

        elif event.event_type in ("PARTIAL_FILL", "FILL"):
            self._emit_audit(
                create_slice_filled_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    client_order_id=event.client_order_id,
                    slice_index=self._parse_slice_index(event.client_order_id),
                    filled_qty=event.filled_qty,
                    filled_price=event.filled_price,
                    remaining_qty=event.remaining_qty,
                    is_partial=event.event_type == "PARTIAL_FILL",
                )
            )

        elif event.event_type == "REJECT":
            self._emit_audit(
                create_slice_rejected_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    client_order_id=event.client_order_id,
                    slice_index=self._parse_slice_index(event.client_order_id),
                    error_code=event.error_code,
                    error_msg=event.error_msg,
                )
            )

        elif event.event_type == "CANCEL_ACK":
            self._emit_audit(
                create_slice_cancelled_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    client_order_id=event.client_order_id,
                    slice_index=self._parse_slice_index(event.client_order_id),
                    reason="撤单确认",
                )
            )

        # 同步更新计划状态
        status = executor.get_status(plan_id)
        if status == ExecutorStatus.COMPLETED:
            plan.status = ExecutionPlanStatus.COMPLETED
            plan.completed_at = time.time()
            progress = executor.get_progress(plan_id)
            if progress:
                plan.filled_qty = progress.filled_qty
                plan.avg_price = progress.avg_price

    def pause_plan(self, plan_id: str) -> bool:
        """暂停计划.

        V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

        Args:
            plan_id: 计划ID

        Returns:
            是否成功暂停
        """
        executor = self._executors.get(plan_id)
        plan = self._plans.get(plan_id)

        if executor is None or plan is None:
            return False

        success = executor.pause(plan_id)
        if success:
            plan.status = ExecutionPlanStatus.PAUSED
            self._emit_audit(
                create_plan_paused_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    reason="用户暂停",
                )
            )
            logger.info(f"计划已暂停: {plan_id}")

        return success

    def resume_plan(self, plan_id: str) -> bool:
        """恢复计划.

        V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

        Args:
            plan_id: 计划ID

        Returns:
            是否成功恢复
        """
        executor = self._executors.get(plan_id)
        plan = self._plans.get(plan_id)

        if executor is None or plan is None:
            return False

        success = executor.resume(plan_id)
        if success:
            plan.status = ExecutionPlanStatus.ACTIVE
            self._emit_audit(
                create_plan_resumed_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    reason="用户恢复",
                )
            )
            logger.info(f"计划已恢复: {plan_id}")

        return success

    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消计划.

        V4PRO Scenario: MODE2.ENGINE.LIFECYCLE

        Args:
            plan_id: 计划ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        executor = self._executors.get(plan_id)
        plan = self._plans.get(plan_id)

        if executor is None or plan is None:
            return False

        success = executor.cancel_plan(plan_id, reason)
        if success:
            plan.status = ExecutionPlanStatus.CANCELLED
            plan.completed_at = time.time()
            plan.error = reason or "用户取消"

            # 更新成交信息
            progress = executor.get_progress(plan_id)
            if progress:
                plan.filled_qty = progress.filled_qty
                plan.avg_price = progress.avg_price

            # 标记意图失败
            self._registry.mark_failed(plan.intent.intent_id)

            self._emit_audit(
                create_plan_cancelled_event(
                    intent_id=plan.intent.intent_id,
                    plan_id=plan_id,
                    filled_qty=plan.filled_qty,
                    remaining_qty=plan.intent.target_qty - plan.filled_qty,
                    reason=plan.error,
                )
            )
            logger.info(f"计划已取消: {plan_id}, 原因: {plan.error}")

        return success

    def get_plan(self, plan_id: str) -> ExecutionPlan | None:
        """获取执行计划.

        Args:
            plan_id: 计划ID

        Returns:
            执行计划或 None
        """
        return self._plans.get(plan_id)

    def get_progress(self, plan_id: str) -> ExecutionProgress | None:
        """获取执行进度.

        Args:
            plan_id: 计划ID

        Returns:
            执行进度或 None
        """
        executor = self._executors.get(plan_id)
        if executor is None:
            return None
        return executor.get_progress(plan_id)

    def get_active_plans(self) -> list[str]:
        """获取活动计划列表.

        Returns:
            活动计划ID列表
        """
        return [
            plan_id
            for plan_id, plan in self._plans.items()
            if plan.status in (ExecutionPlanStatus.PENDING, ExecutionPlanStatus.ACTIVE)
        ]

    def get_pending_cancel_orders(self, plan_id: str) -> list[str]:
        """获取需要撤销的挂单列表.

        Args:
            plan_id: 计划ID

        Returns:
            需要撤销的 client_order_id 列表
        """
        executor = self._executors.get(plan_id)
        if executor is None:
            return []

        # 检查执行器是否有此方法
        if hasattr(executor, "get_pending_cancel_orders"):
            return executor.get_pending_cancel_orders(plan_id)
        return []

    def is_intent_registered(self, intent_id: str) -> bool:
        """检查意图是否已注册.

        V4PRO Scenario: MODE2.ENGINE.SUBMIT

        Args:
            intent_id: 意图ID

        Returns:
            是否已注册
        """
        return self._registry.is_registered(intent_id)

    def get_statistics(self) -> dict[str, Any]:
        """获取引擎统计信息.

        Returns:
            统计信息字典
        """
        total_plans = len(self._plans)
        active_plans = sum(
            1
            for p in self._plans.values()
            if p.status in (ExecutionPlanStatus.PENDING, ExecutionPlanStatus.ACTIVE)
        )
        completed_plans = sum(
            1 for p in self._plans.values() if p.status == ExecutionPlanStatus.COMPLETED
        )
        failed_plans = sum(
            1 for p in self._plans.values() if p.status == ExecutionPlanStatus.FAILED
        )
        cancelled_plans = sum(
            1 for p in self._plans.values() if p.status == ExecutionPlanStatus.CANCELLED
        )

        return {
            "total_plans": total_plans,
            "active_plans": active_plans,
            "completed_plans": completed_plans,
            "failed_plans": failed_plans,
            "cancelled_plans": cancelled_plans,
            "registered_intents": len(self._registry),
        }

    def _emit_audit(self, event: Mode2AuditEvent) -> None:
        """发送审计事件.

        Args:
            event: 审计事件
        """
        if self._config.enable_audit and self._audit_callback:
            try:
                self._audit_callback(event)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")

    def _parse_slice_index(self, client_order_id: str) -> int:
        """解析分片索引.

        Args:
            client_order_id: 客户订单ID

        Returns:
            分片索引,解析失败返回 -1
        """
        try:
            from src.execution.mode2.intent import IntentIdGenerator

            _, slice_index, _ = IntentIdGenerator.parse_client_order_id(client_order_id)
            return slice_index
        except ValueError:
            return -1

    def set_audit_callback(self, callback: AuditCallback) -> None:
        """设置审计回调.

        Args:
            callback: 审计回调函数
        """
        self._audit_callback = callback

    def set_cost_check_callback(self, callback: CostCheckCallback) -> None:
        """设置成本检查回调.

        Args:
            callback: 成本检查回调函数
        """
        self._cost_check_callback = callback
