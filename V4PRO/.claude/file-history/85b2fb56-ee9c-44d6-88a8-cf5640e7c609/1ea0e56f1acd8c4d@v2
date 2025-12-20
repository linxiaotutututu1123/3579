"""TWAP执行器测试.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- H01: ALGO.TWAP.SLICE_CALC - TWAP切片计算
- H02: ALGO.TWAP.TIME_DISTRIBUTE - TWAP时间分布
- H03: ALGO.TWAP.PARTIAL_FILL - TWAP部分成交处理
"""

from __future__ import annotations

import time

import pytest

from src.execution.mode2.executor_base import (
    ExecutorActionType,
    ExecutorStatus,
    OrderEvent,
)
from src.execution.mode2.executor_twap import TWAPConfig, TWAPExecutor
from src.execution.mode2.intent import AlgoType, Offset, OrderIntent, Side


def create_test_intent(
    target_qty: int = 100,
    instrument: str = "rb2501",
    limit_price: float | None = 4000.0,
    signal_ts: int | None = None,
) -> OrderIntent:
    """创建测试用交易意图."""
    return OrderIntent(
        strategy_id="test_strategy",
        decision_hash="test_decision_hash_12345",
        instrument=instrument,
        side=Side.BUY,
        offset=Offset.OPEN,
        target_qty=target_qty,
        algo=AlgoType.TWAP,
        limit_price=limit_price,
        signal_ts=signal_ts or int(time.time() * 1000),
    )


class TestTWAPSliceCalculation:
    """H01: ALGO.TWAP.SLICE_CALC - TWAP切片计算测试."""

    def test_slice_calc_basic(self) -> None:
        """测试基本分片计算."""
        config = TWAPConfig(
            max_slice_qty=20,
            duration_seconds=100.0,
            min_interval_seconds=10.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        # 验证计划创建成功
        assert plan_id == intent.intent_id
        status = executor.get_status(plan_id)
        assert status == ExecutorStatus.PENDING

        # 验证分片数量
        schedule = executor.get_schedule(plan_id)
        assert len(schedule) >= 5  # 100/20 = 5个分片

        # 验证总数量正确
        total_qty = sum(s["qty"] for s in schedule)
        assert total_qty == 100

    def test_slice_calc_with_fixed_count(self) -> None:
        """测试指定分片数量的计算."""
        config = TWAPConfig(
            slice_count=10,
            duration_seconds=100.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证分片数量为配置值
        assert len(schedule) == 10

        # 验证数量均匀分配
        for s in schedule:
            assert s["qty"] == 10

    def test_slice_calc_uneven_distribution(self) -> None:
        """测试不均匀分配(有余数)."""
        config = TWAPConfig(
            slice_count=3,
            duration_seconds=60.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=10)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 10 / 3 = 3余1,前1个分片多1个
        assert len(schedule) == 3
        total_qty = sum(s["qty"] for s in schedule)
        assert total_qty == 10

        # 验证分配: 4, 3, 3 或类似
        qtys = [s["qty"] for s in schedule]
        assert max(qtys) - min(qtys) <= 1

    def test_slice_calc_idempotent(self) -> None:
        """测试分片计算幂等性 (M2)."""
        config = TWAPConfig(slice_count=5)
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id_1 = executor.make_plan(intent)
        plan_id_2 = executor.make_plan(intent)

        # 同一意图返回相同计划ID
        assert plan_id_1 == plan_id_2


class TestTWAPTimeDistribution:
    """H02: ALGO.TWAP.TIME_DISTRIBUTE - TWAP时间分布测试."""

    def test_time_distribute_uniform(self) -> None:
        """测试均匀时间分布."""
        config = TWAPConfig(
            slice_count=5,
            duration_seconds=100.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证时间间隔均匀 (100s / 4 = 25s)
        times = [s["scheduled_time"] for s in schedule]
        intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]

        # 所有间隔应相等
        for interval in intervals:
            assert abs(interval - 25.0) < 0.1

    def test_time_distribute_wait_action(self) -> None:
        """测试时间未到时返回WAIT动作."""
        config = TWAPConfig(
            slice_count=3,
            duration_seconds=60.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 第一个分片应该立即执行
        action = executor.next_action(plan_id, schedule[0]["scheduled_time"])
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER

        # 模拟成交第一个分片
        event = OrderEvent(
            client_order_id=action.client_order_id or "",
            event_type="FILL",
            filled_qty=action.qty or 0,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event)

        # 在第二个分片时间之前查询,应返回WAIT
        early_time = schedule[0]["scheduled_time"] + 1.0
        if early_time < schedule[1]["scheduled_time"]:
            action = executor.next_action(plan_id, early_time)
            assert action is not None
            assert action.action_type == ExecutorActionType.WAIT

    def test_time_distribute_deterministic(self) -> None:
        """测试时间分布确定性 (M7)."""
        config = TWAPConfig(
            slice_count=4,
            duration_seconds=80.0,
            randomize_interval=False,  # 禁用随机化
        )

        # 创建两个执行器,使用相同配置
        executor1 = TWAPExecutor(config)
        executor2 = TWAPExecutor(config)

        intent = create_test_intent(target_qty=40)

        plan_id_1 = executor1.make_plan(intent)
        plan_id_2 = executor2.make_plan(intent)

        schedule1 = executor1.get_schedule(plan_id_1)
        schedule2 = executor2.get_schedule(plan_id_2)

        # 验证分片数量和数量相同
        assert len(schedule1) == len(schedule2)
        for s1, s2 in zip(schedule1, schedule2, strict=False):
            assert s1["qty"] == s2["qty"]
            assert s1["index"] == s2["index"]


class TestTWAPPartialFill:
    """H03: ALGO.TWAP.PARTIAL_FILL - TWAP部分成交处理测试."""

    def test_partial_fill_continue(self) -> None:
        """测试部分成交后继续执行."""
        config = TWAPConfig(slice_count=2, duration_seconds=10.0)
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)

        # 获取第一个下单动作
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER
        assert action.qty == 10

        # 部分成交
        event = OrderEvent(
            client_order_id=action.client_order_id or "",
            event_type="PARTIAL_FILL",
            filled_qty=5,
            filled_price=4000.0,
            remaining_qty=5,
        )
        executor.on_event(plan_id, event)

        # 验证进度更新
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 5

        # 完全成交
        event = OrderEvent(
            client_order_id=action.client_order_id or "",
            event_type="FILL",
            filled_qty=5,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event)

        # 验证进度
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 10

    def test_partial_fill_progress_tracking(self) -> None:
        """测试部分成交进度追踪."""
        config = TWAPConfig(slice_count=4, duration_seconds=0.1)
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=40)

        plan_id = executor.make_plan(intent)

        filled_total = 0
        start_time = time.time()

        # 执行所有分片
        for i in range(4):
            action = executor.next_action(plan_id, start_time + i * 0.025)
            if action is None or action.action_type != ExecutorActionType.PLACE_ORDER:
                continue

            # 模拟成交
            event = OrderEvent(
                client_order_id=action.client_order_id or "",
                event_type="FILL",
                filled_qty=action.qty or 0,
                filled_price=4000.0,
            )
            executor.on_event(plan_id, event)
            filled_total += action.qty or 0

        # 验证全部成交
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 40
        assert progress.is_complete

    def test_order_reject_retry(self) -> None:
        """测试订单拒绝后重试."""
        config = TWAPConfig(
            slice_count=2,
            duration_seconds=10.0,
            retry_count=3,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)

        # 第一次下单
        action1 = executor.next_action(plan_id, time.time())
        assert action1 is not None
        assert action1.action_type == ExecutorActionType.PLACE_ORDER

        # 订单被拒绝
        event = OrderEvent(
            client_order_id=action1.client_order_id or "",
            event_type="REJECT",
            error_code="LIMIT_PRICE",
            error_msg="价格超限",
        )
        executor.on_event(plan_id, event)

        # 应该重试
        action2 = executor.next_action(plan_id, time.time())
        assert action2 is not None
        assert action2.action_type == ExecutorActionType.PLACE_ORDER

        # 验证client_order_id不同(包含重试次数)
        assert action2.client_order_id != action1.client_order_id

    def test_order_timeout_cancel(self) -> None:
        """测试订单超时撤单."""
        config = TWAPConfig(
            slice_count=2,
            duration_seconds=10.0,
            timeout_seconds=1.0,  # 1秒超时
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)
        now = time.time()

        # 下单
        action = executor.next_action(plan_id, now)
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER

        # 2秒后检查,应该返回撤单动作
        action_timeout = executor.next_action(plan_id, now + 2.0)
        assert action_timeout is not None
        assert action_timeout.action_type == ExecutorActionType.CANCEL_ORDER


class TestTWAPExecutorIntegration:
    """TWAP执行器集成测试."""

    def test_full_execution_cycle(self) -> None:
        """测试完整执行周期."""
        config = TWAPConfig(
            slice_count=3,
            duration_seconds=0.1,
            timeout_seconds=10.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 验证初始状态
        assert executor.get_status(plan_id) == ExecutorStatus.PENDING

        # 执行所有分片
        start_time = time.time()
        for i in range(3):
            action = executor.next_action(plan_id, start_time + i * 0.05)
            if action is None:
                continue

            if action.action_type == ExecutorActionType.PLACE_ORDER:
                # 模拟成交
                event = OrderEvent(
                    client_order_id=action.client_order_id or "",
                    event_type="FILL",
                    filled_qty=action.qty or 0,
                    filled_price=4000.0,
                )
                executor.on_event(plan_id, event)
            elif action.action_type == ExecutorActionType.COMPLETE:
                break

        # 验证完成状态
        assert executor.get_status(plan_id) == ExecutorStatus.COMPLETED

        # 验证最终进度
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 30
        assert progress.avg_price == 4000.0

    def test_cancel_plan(self) -> None:
        """测试取消计划."""
        config = TWAPConfig(slice_count=5, duration_seconds=100.0)
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id = executor.make_plan(intent)

        # 执行一个分片
        action = executor.next_action(plan_id, time.time())
        if action and action.action_type == ExecutorActionType.PLACE_ORDER:
            event = OrderEvent(
                client_order_id=action.client_order_id or "",
                event_type="FILL",
                filled_qty=action.qty or 0,
                filled_price=4000.0,
            )
            executor.on_event(plan_id, event)

        # 取消计划
        success = executor.cancel_plan(plan_id, "用户取消")
        assert success

        # 验证状态
        assert executor.get_status(plan_id) == ExecutorStatus.CANCELLED

        # 取消后的动作应该是ABORT
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.ABORT

    def test_pause_resume(self) -> None:
        """测试暂停恢复."""
        config = TWAPConfig(slice_count=3, duration_seconds=60.0)
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 开始执行
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER

        # 模拟成交
        event = OrderEvent(
            client_order_id=action.client_order_id or "",
            event_type="FILL",
            filled_qty=10,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event)

        # 暂停
        success = executor.pause(plan_id)
        assert success
        assert executor.get_status(plan_id) == ExecutorStatus.PAUSED

        # 暂停时应返回WAIT
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.WAIT

        # 恢复
        success = executor.resume(plan_id)
        assert success
        assert executor.get_status(plan_id) == ExecutorStatus.RUNNING

    def test_metadata_tracking(self) -> None:
        """测试元数据追踪 (M3)."""
        config = TWAPConfig(
            slice_count=4,
            duration_seconds=80.0,
        )
        executor = TWAPExecutor(config)
        intent = create_test_intent(target_qty=40)

        plan_id = executor.make_plan(intent)

        # 获取第一个动作
        action = executor.next_action(plan_id, time.time())
        assert action is not None

        # 验证元数据包含审计信息
        assert "intent_id" in action.metadata
        assert "slice_index" in action.metadata
        assert action.metadata["intent_id"] == intent.intent_id
