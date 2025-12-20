"""冰山单执行器测试.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- H07: ALGO.ICEBERG.DISPLAY_SIZE - 冰山单显示量
- H08: ALGO.ICEBERG.REFRESH - 冰山单刷新逻辑
- H09: ALGO.ICEBERG.RANDOM_SIZE - 冰山单确定性(M7)
"""

from __future__ import annotations

import time

import pytest

from src.execution.mode2.executor_base import (
    ExecutorActionType,
    ExecutorStatus,
    OrderEvent,
)
from src.execution.mode2.executor_iceberg import IcebergConfig, IcebergExecutor
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
        decision_hash="test_decision_hash_iceberg",
        instrument=instrument,
        side=Side.BUY,
        offset=Offset.OPEN,
        target_qty=target_qty,
        algo=AlgoType.ICEBERG,
        limit_price=limit_price,
        signal_ts=signal_ts or int(time.time() * 1000),
    )


class TestIcebergDisplaySize:
    """H07: ALGO.ICEBERG.DISPLAY_SIZE - 冰山单显示量测试."""

    def test_fixed_display_qty(self) -> None:
        """测试固定显示量配置."""
        config = IcebergConfig(
            display_qty=10,  # 固定显示10手
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        # 获取冰山单状态
        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["display_qty"] == 10
        assert status["total_qty"] == 100

        # 验证第一个订单量为显示量
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER
        assert action.qty == 10

    def test_display_qty_ratio(self) -> None:
        """测试按比例计算显示量."""
        config = IcebergConfig(
            display_qty=0,  # 0 表示按比例
            display_qty_ratio=0.2,  # 20%
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["display_qty"] == 20  # 100 * 0.2

    def test_display_qty_bounds(self) -> None:
        """测试显示量边界约束."""
        config = IcebergConfig(
            display_qty=0,
            display_qty_ratio=0.5,  # 50%
            min_slice_qty=5,
            max_slice_qty=30,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        # 50 超过 max_slice_qty, 应该被限制为 30
        assert status["display_qty"] == 30

    def test_display_qty_min_bound(self) -> None:
        """测试显示量最小边界."""
        config = IcebergConfig(
            display_qty=0,
            display_qty_ratio=0.01,  # 1%
            min_slice_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        # 1% = 1, 但 min_slice_qty = 10
        assert status["display_qty"] == 10

    def test_display_qty_not_exceed_total(self) -> None:
        """测试显示量不超过总量."""
        config = IcebergConfig(
            display_qty=50,  # 显示量大于总量
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        # 显示量不能超过总量
        assert status["display_qty"] == 30

    def test_display_qty_in_metadata(self) -> None:
        """测试显示量记录在元数据中 (M3)."""
        config = IcebergConfig(display_qty=15)
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=60)

        plan_id = executor.make_plan(intent)

        # 获取第一个动作
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER

        # 验证元数据包含显示量和隐藏量
        assert "display_qty" in action.metadata
        assert action.metadata["display_qty"] == 15
        assert "hidden_qty" in action.metadata
        assert action.metadata["hidden_qty"] == 45  # 60 - 15 = 45


class TestIcebergRefresh:
    """H08: ALGO.ICEBERG.REFRESH - 冰山单刷新逻辑测试."""

    def test_refresh_after_fill(self) -> None:
        """测试成交后自动补单."""
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 第一个显示量
        action1 = executor.next_action(plan_id, time.time())
        assert action1 is not None
        assert action1.qty == 10

        # 成交
        event = OrderEvent(
            client_order_id=action1.client_order_id or "",
            event_type="FILL",
            filled_qty=10,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event)

        # 应自动补单(第二个显示量)
        action2 = executor.next_action(plan_id, time.time())
        assert action2 is not None
        assert action2.action_type == ExecutorActionType.PLACE_ORDER
        assert action2.qty == 10

    def test_no_refresh_while_pending(self) -> None:
        """测试有挂单时不补单."""
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 下第一个单
        action1 = executor.next_action(plan_id, time.time())
        assert action1 is not None
        assert action1.action_type == ExecutorActionType.PLACE_ORDER

        # 再次查询,应返回 WAIT
        action2 = executor.next_action(plan_id, time.time())
        assert action2 is not None
        assert action2.action_type == ExecutorActionType.WAIT
        assert "等待" in action2.reason

    def test_partial_fill_handling(self) -> None:
        """测试部分成交处理."""
        config = IcebergConfig(
            display_qty=10,
            refresh_on_partial=True,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)

        # 下单
        action = executor.next_action(plan_id, time.time())
        assert action is not None

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

    def test_full_refresh_cycle(self) -> None:
        """测试完整的补单周期."""
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 执行三轮补单
        for i in range(3):
            action = executor.next_action(plan_id, time.time())
            assert action is not None
            assert action.action_type == ExecutorActionType.PLACE_ORDER
            assert action.qty == 10

            # 成交
            event = OrderEvent(
                client_order_id=action.client_order_id or "",
                event_type="FILL",
                filled_qty=10,
                filled_price=4000.0,
            )
            executor.on_event(plan_id, event)

        # 验证完成
        assert executor.get_status(plan_id) == ExecutorStatus.COMPLETED

        # 验证进度
        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 30

    def test_refresh_with_remainder(self) -> None:
        """测试余量补单(最后一单小于显示量)."""
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=25)  # 不能被10整除

        plan_id = executor.make_plan(intent)

        # 前两轮各10手
        for _ in range(2):
            action = executor.next_action(plan_id, time.time())
            assert action is not None
            event = OrderEvent(
                client_order_id=action.client_order_id or "",
                event_type="FILL",
                filled_qty=action.qty or 0,
                filled_price=4000.0,
            )
            executor.on_event(plan_id, event)

        # 第三轮应该是5手(余量)
        action = executor.next_action(plan_id, time.time())
        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER
        assert action.qty == 5  # 25 - 20 = 5


class TestIcebergDeterministic:
    """H09: ALGO.ICEBERG.RANDOM_SIZE - 冰山单确定性测试 (M7)."""

    def test_deterministic_display_qty(self) -> None:
        """测试显示量计算确定性."""
        config = IcebergConfig(
            display_qty=0,
            display_qty_ratio=0.15,
            timeout_seconds=10.0,
        )

        # 创建两个执行器
        executor1 = IcebergExecutor(config)
        executor2 = IcebergExecutor(config)

        intent = create_test_intent(target_qty=100)

        plan_id_1 = executor1.make_plan(intent)
        plan_id_2 = executor2.make_plan(intent)

        status1 = executor1.get_iceberg_status(plan_id_1)
        status2 = executor2.get_iceberg_status(plan_id_2)

        # 相同配置和意图应产生相同的显示量
        assert status1 is not None
        assert status2 is not None
        assert status1["display_qty"] == status2["display_qty"]

    def test_idempotent_make_plan(self) -> None:
        """测试幂等性 (M2)."""
        config = IcebergConfig(display_qty=10)
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id_1 = executor.make_plan(intent)
        plan_id_2 = executor.make_plan(intent)

        # 同一意图返回相同计划ID
        assert plan_id_1 == plan_id_2

    def test_slice_allocation_deterministic(self) -> None:
        """测试分片分配确定性 (M7)."""
        config = IcebergConfig(display_qty=10)

        executor1 = IcebergExecutor(config)
        executor2 = IcebergExecutor(config)

        intent = create_test_intent(target_qty=35)

        plan_id_1 = executor1.make_plan(intent)
        plan_id_2 = executor2.make_plan(intent)

        status1 = executor1.get_iceberg_status(plan_id_1)
        status2 = executor2.get_iceberg_status(plan_id_2)

        assert status1 is not None
        assert status2 is not None
        assert status1["slice_count"] == status2["slice_count"]


class TestIcebergExecutorIntegration:
    """冰山单执行器集成测试."""

    def test_full_execution_cycle(self) -> None:
        """测试完整执行周期."""
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)

        # 验证初始状态
        assert executor.get_status(plan_id) == ExecutorStatus.PENDING

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["hidden_qty"] == 30  # 初始全部隐藏

        # 执行所有分片
        for _ in range(3):
            action = executor.next_action(plan_id, time.time())
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

    def test_cancel_plan(self) -> None:
        """测试取消计划."""
        config = IcebergConfig(display_qty=10)
        executor = IcebergExecutor(config)
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

        # 取消
        success = executor.cancel_plan(plan_id, "测试取消")
        assert success
        assert executor.get_status(plan_id) == ExecutorStatus.CANCELLED

    def test_hidden_qty_tracking(self) -> None:
        """测试隐藏量追踪."""
        config = IcebergConfig(display_qty=10)
        executor = IcebergExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id = executor.make_plan(intent)

        # 初始状态
        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["hidden_qty"] == 50
        assert status["visible_qty"] == 0

        # 下第一单后
        action = executor.next_action(plan_id, time.time())
        assert action is not None

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["visible_qty"] == 10
        assert status["hidden_qty"] == 40

        # 成交后
        event = OrderEvent(
            client_order_id=action.client_order_id or "",
            event_type="FILL",
            filled_qty=10,
            filled_price=4000.0,
        )
        executor.on_event(plan_id, event)

        status = executor.get_iceberg_status(plan_id)
        assert status is not None
        assert status["filled_qty"] == 10
        assert status["remaining_qty"] == 40
        assert status["visible_qty"] == 0  # 成交后无挂单

    def test_progress_with_avg_price(self) -> None:
        """测试进度包含平均价格."""
        config = IcebergConfig(display_qty=10)
        executor = IcebergExecutor(config)
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

    def test_order_reject_retry(self) -> None:
        """测试订单拒绝后重试."""
        config = IcebergConfig(
            display_qty=10,
            retry_count=3,
            timeout_seconds=10.0,
        )
        executor = IcebergExecutor(config)
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
        config = IcebergConfig(
            display_qty=10,
            timeout_seconds=1.0,  # 1秒超时
        )
        executor = IcebergExecutor(config)
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
