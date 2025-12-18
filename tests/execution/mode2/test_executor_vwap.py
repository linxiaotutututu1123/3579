"""VWAP执行器测试.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- H04: ALGO.VWAP.VOLUME_PROFILE - VWAP成交量分布
- H05: ALGO.VWAP.PARTICIPATION - VWAP参与率控制
- H06: ALGO.VWAP.CATCH_UP - VWAP追赶逻辑
"""

from __future__ import annotations

import time

import pytest

from src.execution.mode2.executor_base import (
    ExecutorActionType,
    ExecutorStatus,
    OrderEvent,
)
from src.execution.mode2.executor_vwap import (
    DEFAULT_VOLUME_PROFILE,
    VWAPConfig,
    VWAPExecutor,
)
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
        decision_hash="test_decision_hash_vwap",
        instrument=instrument,
        side=Side.BUY,
        offset=Offset.OPEN,
        target_qty=target_qty,
        algo=AlgoType.VWAP,
        limit_price=limit_price,
        signal_ts=signal_ts or int(time.time() * 1000),
    )


class TestVWAPVolumeProfile:
    """H04: ALGO.VWAP.VOLUME_PROFILE - VWAP成交量分布测试."""

    def test_volume_profile_weighted_allocation(self) -> None:
        """测试按成交量分布加权分配."""
        # 自定义成交量分布: 20%, 30%, 50%
        profile = [0.2, 0.3, 0.5]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=60.0,
            min_slice_qty_ratio=0.01,  # 1%最小分片
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证分片数量
        assert len(schedule) == 3

        # 验证按权重分配
        qtys = [s["qty"] for s in schedule]
        total = sum(qtys)
        assert total == 100

        # 第三个分片应该最大(50%)
        assert qtys[2] >= qtys[0]
        assert qtys[2] >= qtys[1]

    def test_volume_profile_normalization(self) -> None:
        """测试成交量分布自动归一化."""
        # 非归一化分布
        profile = [1, 2, 3, 4]  # 总和=10
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=80.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证总量正确
        total = sum(s["qty"] for s in schedule)
        assert total == 100

        # 验证比例大致正确 (10%, 20%, 30%, 40%)
        qtys = [s["qty"] for s in schedule]
        # 允许舍入误差
        assert qtys[3] > qtys[0]  # 最后一个应该最大

    def test_default_volume_profile(self) -> None:
        """测试默认中国期货市场成交量分布."""
        config = VWAPConfig(duration_seconds=100.0)
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证使用默认分布
        assert len(schedule) == len(DEFAULT_VOLUME_PROFILE)

        # 验证总量
        total = sum(s["qty"] for s in schedule)
        assert total == 100

    def test_volume_weight_in_metadata(self) -> None:
        """测试成交量权重记录在元数据中 (M3)."""
        profile = [0.3, 0.4, 0.3]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=30.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 获取第一个动作
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER

        # 验证元数据包含成交量权重
        assert "volume_weight" in action.metadata
        assert action.metadata["volume_weight"] == 0.3


class TestVWAPParticipation:
    """H05: ALGO.VWAP.PARTICIPATION - VWAP参与率控制测试."""

    def test_participation_rate_config(self) -> None:
        """测试参与率配置."""
        config = VWAPConfig(
            participation_rate=0.05,  # 5%参与率
            volume_profile=[0.5, 0.5],
            duration_seconds=20.0,
        )
        executor = VWAPExecutor(config)

        # 验证配置
        assert executor._vwap_config.participation_rate == 0.05

    def test_min_slice_qty_ratio(self) -> None:
        """测试最小分片比例."""
        config = VWAPConfig(
            min_slice_qty_ratio=0.1,  # 10%最小分片
            volume_profile=[0.05, 0.95],  # 第一个只占5%
            duration_seconds=20.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 即使权重只有5%,分片数量不应低于10
        qtys = [s["qty"] for s in schedule]
        # 第一个分片应该>=10(最小分片比例)
        assert qtys[0] >= 10


class TestVWAPCatchUp:
    """H06: ALGO.VWAP.CATCH_UP - VWAP追赶逻辑测试."""

    def test_sequential_execution(self) -> None:
        """测试顺序执行(基本追赶)."""
        profile = [0.25, 0.25, 0.25, 0.25]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=40.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=40)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 模拟执行所有分片(使用时间表中的时间)
        filled = 0
        for s in schedule:
            action = executor.next_action(plan_id, s["scheduled_time"])
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
            filled += action.qty or 0

        # 验证全部完成
        assert filled == 40
        assert executor.get_status(plan_id) == ExecutorStatus.COMPLETED

    def test_execution_after_delay(self) -> None:
        """测试延迟后的执行."""
        profile = [0.5, 0.5]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=20.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 在第二个分片时间后查询,应该仍能执行第一个分片
        late_time = schedule[1]["scheduled_time"] + 10.0

        action = executor.next_action(plan_id, late_time)
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER


class TestVWAPExecutorIntegration:
    """VWAP执行器集成测试."""

    def test_full_execution_cycle(self) -> None:
        """测试完整执行周期."""
        profile = [0.3, 0.4, 0.3]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=0.1,
            timeout_seconds=10.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证初始状态
        assert executor.get_status(plan_id) == ExecutorStatus.PENDING

        # 执行所有分片(使用时间表中的时间)
        for s in schedule:
            action = executor.next_action(plan_id, s["scheduled_time"])
            if action is None:
                continue

            if action.action_type == ExecutorActionType.PLACE_ORDER:
                event = OrderEvent(
                    client_order_id=action.client_order_id or "",
                    event_type="FILL",
                    filled_qty=action.qty or 0,
                    filled_price=4000.0,
                )
                executor.on_event(plan_id, event)
            elif action.action_type == ExecutorActionType.COMPLETE:
                break

        # 验证完成
        assert executor.get_status(plan_id) == ExecutorStatus.COMPLETED

    def test_idempotent_make_plan(self) -> None:
        """测试幂等性 (M2)."""
        config = VWAPConfig(volume_profile=[0.5, 0.5])
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id_1 = executor.make_plan(intent)
        plan_id_2 = executor.make_plan(intent)

        assert plan_id_1 == plan_id_2

    def test_dynamic_volume_profile(self) -> None:
        """测试动态设置成交量分布."""
        config = VWAPConfig(volume_profile=[0.5, 0.5])
        executor = VWAPExecutor(config)

        # 动态修改分布
        executor.set_volume_profile([0.3, 0.3, 0.4])

        # 验证新分布生效
        assert executor._vwap_config.volume_profile == [0.3, 0.3, 0.4]

    def test_schedule_with_volume_weight(self) -> None:
        """测试时间表包含成交量权重."""
        profile = [0.2, 0.3, 0.5]
        config = VWAPConfig(
            volume_profile=profile,
            duration_seconds=30.0,
        )
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        schedule = executor.get_schedule(plan_id)

        # 验证每个分片都有volume_weight
        for i, s in enumerate(schedule):
            assert "volume_weight" in s
            assert s["volume_weight"] == profile[i]

    def test_cancel_plan(self) -> None:
        """测试取消计划."""
        config = VWAPConfig(volume_profile=[0.5, 0.5])
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

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

        # 取消
        success = executor.cancel_plan(plan_id, "测试取消")
        assert success
        assert executor.get_status(plan_id) == ExecutorStatus.CANCELLED

    def test_progress_with_avg_price(self) -> None:
        """测试进度包含平均价格."""
        config = VWAPConfig(volume_profile=[0.5, 0.5])
        executor = VWAPExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)

        # 第一个分片成交价4000
        action1 = executor.next_action(plan_id, time.time())
        assert action1 is not None
        event1 = OrderEvent(
            client_order_id=action1.client_order_id or "",
            event_type="FILL",
            filled_qty=10,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event1)

        # 第二个分片成交价4100
        action2 = executor.next_action(plan_id, time.time())
        assert action2 is not None
        event2 = OrderEvent(
            client_order_id=action2.client_order_id or "",
            event_type="FILL",
            filled_qty=10,
            filled_price=4100.0,
        )
        executor.on_event(plan_id, event2)

        # 验证平均价格
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 20
        assert progress.avg_price == 4050.0  # (10*4000 + 10*4100) / 20
