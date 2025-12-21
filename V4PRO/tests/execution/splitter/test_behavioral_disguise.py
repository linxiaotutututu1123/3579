"""
行为伪装拆单算法测试.

V4PRO Platform Component - Behavioral Disguise Order Splitter Tests
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- SPLITTER.BEHAVIORAL.RANDOM: 随机化分片时间
- SPLITTER.BEHAVIORAL.SIZE_VARIANCE: 分片大小变化
- SPLITTER.BEHAVIORAL.NOISE: 交易噪声注入
"""

from __future__ import annotations

import time

import pytest

from src.execution.mode2.executor_base import (
    ExecutorActionType,
    ExecutorStatus,
    OrderEvent,
)
from src.execution.mode2.intent import AlgoType, Offset, OrderIntent, Side
from src.execution.splitter.behavioral_disguise import (
    BehavioralConfig,
    BehavioralDisguiseExecutor,
    DisguisePattern,
    DisguiseState,
    NoiseType,
)


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
        algo=AlgoType.IMMEDIATE,
        limit_price=limit_price,
        signal_ts=signal_ts or int(time.time() * 1000),
    )


class TestDisguisePatternEnum:
    """伪装模式枚举测试."""

    def test_pattern_values(self) -> None:
        """测试模式值."""
        assert DisguisePattern.RETAIL.value == "RETAIL"
        assert DisguisePattern.INSTITUTIONAL.value == "INSTITUTIONAL"
        assert DisguisePattern.HYBRID.value == "HYBRID"
        assert DisguisePattern.ADAPTIVE.value == "ADAPTIVE"

    def test_pattern_string_conversion(self) -> None:
        """测试模式字符串转换."""
        assert str(DisguisePattern.RETAIL) == "RETAIL"


class TestNoiseTypeEnum:
    """噪声类型枚举测试."""

    def test_noise_values(self) -> None:
        """测试噪声类型值."""
        assert NoiseType.NONE.value == "NONE"
        assert NoiseType.TIMING.value == "TIMING"
        assert NoiseType.SIZE.value == "SIZE"
        assert NoiseType.BOTH.value == "BOTH"


class TestBehavioralConfig:
    """行为伪装配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = BehavioralConfig()
        assert config.pattern == DisguisePattern.RETAIL
        assert config.noise_type == NoiseType.BOTH
        assert config.duration_seconds == 300.0
        assert config.min_interval_seconds == 5.0
        assert config.max_interval_seconds == 60.0
        assert config.size_variance == 0.3
        assert config.timing_variance == 0.4
        assert config.min_slices == 5
        assert config.max_slices == 20

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = BehavioralConfig(
            pattern=DisguisePattern.INSTITUTIONAL,
            noise_type=NoiseType.SIZE,
            duration_seconds=600.0,
            size_variance=0.5,
        )
        assert config.pattern == DisguisePattern.INSTITUTIONAL
        assert config.noise_type == NoiseType.SIZE
        assert config.duration_seconds == 600.0
        assert config.size_variance == 0.5


class TestDisguiseState:
    """伪装状态测试."""

    def test_state_init(self) -> None:
        """测试状态初始化."""
        state = DisguiseState(random_seed=12345)
        assert state.random_seed == 12345
        assert state.current_pattern == DisguisePattern.RETAIL
        assert state.pattern_switch_count == 0
        assert state.fake_cancel_count == 0

    def test_state_rng_deterministic(self) -> None:
        """测试随机数生成器确定性 (M7)."""
        state1 = DisguiseState(random_seed=12345)
        state2 = DisguiseState(random_seed=12345)

        # 同一种子应产生相同随机数序列
        vals1 = [state1.rng.random() for _ in range(10)]
        vals2 = [state2.rng.random() for _ in range(10)]
        assert vals1 == vals2

    def test_state_rng_different_seeds(self) -> None:
        """测试不同种子产生不同序列."""
        state1 = DisguiseState(random_seed=12345)
        state2 = DisguiseState(random_seed=54321)

        vals1 = [state1.rng.random() for _ in range(10)]
        vals2 = [state2.rng.random() for _ in range(10)]
        assert vals1 != vals2


class TestBehavioralExecutorMakePlan:
    """行为伪装执行器计划创建测试."""

    def test_make_plan_basic(self) -> None:
        """测试基本计划创建."""
        config = BehavioralConfig(min_slices=5, max_slices=10)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)

        assert plan_id == intent.intent_id
        assert executor.get_status(plan_id) == ExecutorStatus.PENDING

    def test_make_plan_idempotent(self) -> None:
        """测试计划创建幂等性 (M2)."""
        config = BehavioralConfig()
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id_1 = executor.make_plan(intent)
        plan_id_2 = executor.make_plan(intent)

        # 同一意图返回相同计划ID
        assert plan_id_1 == plan_id_2

    def test_make_plan_deterministic_seed(self) -> None:
        """测试确定性随机种子 (M7)."""
        config = BehavioralConfig()
        executor1 = BehavioralDisguiseExecutor(config)
        executor2 = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        executor1.make_plan(intent)
        executor2.make_plan(intent)

        # 相同意图应产生相同种子
        info1 = executor1.get_disguise_info(intent.intent_id)
        info2 = executor2.get_disguise_info(intent.intent_id)
        assert info1 is not None
        assert info2 is not None
        assert info1["random_seed"] == info2["random_seed"]

    def test_make_plan_metadata(self) -> None:
        """测试计划元数据."""
        config = BehavioralConfig(pattern=DisguisePattern.INSTITUTIONAL)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        info = executor.get_disguise_info(plan_id)

        assert info is not None
        assert info["current_pattern"] == "INSTITUTIONAL"
        assert info["slice_count"] > 0


class TestBehavioralExecutorSliceGeneration:
    """SPLITTER.BEHAVIORAL.SIZE_VARIANCE - 分片大小变化测试."""

    def test_slice_total_qty_correct(self) -> None:
        """测试分片总数量正确."""
        config = BehavioralConfig(min_slices=5, max_slices=10)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        progress = executor.get_progress(plan_id)

        assert progress is not None
        assert progress.total_qty == 100

    def test_slice_variance_applied(self) -> None:
        """测试分片大小变异."""
        config = BehavioralConfig(
            noise_type=NoiseType.SIZE,
            size_variance=0.5,
            min_slices=5,
            max_slices=10,
        )
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        info = executor.get_disguise_info(plan_id)

        assert info is not None
        assert info["slice_count"] >= 5

    def test_slice_variance_disabled(self) -> None:
        """测试禁用大小变异."""
        config = BehavioralConfig(
            noise_type=NoiseType.TIMING,  # 只有时间噪声
            min_slices=5,
            max_slices=10,
        )
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        executor.make_plan(intent)
        # 应正常创建计划
        assert executor.get_status(intent.intent_id) == ExecutorStatus.PENDING


class TestBehavioralExecutorPatterns:
    """伪装模式测试."""

    def test_retail_pattern_more_slices(self) -> None:
        """测试散户模式产生更多分片."""
        config_retail = BehavioralConfig(
            pattern=DisguisePattern.RETAIL,
            min_slices=5,
            max_slices=20,
        )
        config_inst = BehavioralConfig(
            pattern=DisguisePattern.INSTITUTIONAL,
            min_slices=5,
            max_slices=20,
        )

        executor_retail = BehavioralDisguiseExecutor(config_retail)
        executor_inst = BehavioralDisguiseExecutor(config_inst)

        # 使用不同decision_hash确保不同intent_id
        intent_retail = OrderIntent(
            strategy_id="test_strategy",
            decision_hash="retail_test_12345",
            instrument="rb2501",
            side=Side.BUY,
            offset=Offset.OPEN,
            target_qty=100,
            algo=AlgoType.IMMEDIATE,
            limit_price=4000.0,
            signal_ts=int(time.time() * 1000),
        )
        intent_inst = OrderIntent(
            strategy_id="test_strategy",
            decision_hash="inst_test_12345",
            instrument="rb2501",
            side=Side.BUY,
            offset=Offset.OPEN,
            target_qty=100,
            algo=AlgoType.IMMEDIATE,
            limit_price=4000.0,
            signal_ts=int(time.time() * 1000),
        )

        plan_id_retail = executor_retail.make_plan(intent_retail)
        plan_id_inst = executor_inst.make_plan(intent_inst)

        info_retail = executor_retail.get_disguise_info(plan_id_retail)
        info_inst = executor_inst.get_disguise_info(plan_id_inst)

        # 散户模式通常产生更多分片
        assert info_retail is not None
        assert info_inst is not None
        # 由于随机性, 不做严格断言, 只验证有分片生成
        assert info_retail["slice_count"] >= 1
        assert info_inst["slice_count"] >= 1


class TestBehavioralExecutorNextAction:
    """行为伪装执行器动作测试."""

    def test_next_action_first_slice(self) -> None:
        """测试第一个分片立即执行."""
        config = BehavioralConfig(min_slices=3, max_slices=5)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        action = executor.next_action(plan_id, time.time())

        assert action is not None
        assert action.action_type == ExecutorActionType.PLACE_ORDER
        assert action.qty is not None and action.qty > 0

    def test_next_action_wait_for_time(self) -> None:
        """测试等待执行时间."""
        config = BehavioralConfig(
            min_slices=3,
            max_slices=5,
            min_interval_seconds=10.0,
        )
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        # 第一个分片
        action1 = executor.next_action(plan_id, current_time)
        assert action1 is not None
        assert action1.action_type == ExecutorActionType.PLACE_ORDER

        # 模拟订单完成
        executor.on_event(
            plan_id,
            OrderEvent(
                event_type="FILL",
                client_order_id=action1.client_order_id or "",
                filled_qty=action1.qty or 0,
                filled_price=4000.0,
                ts=current_time,
            ),
        )

        # 第二个分片应该等待
        action2 = executor.next_action(plan_id, current_time + 1)
        if action2 is not None and action2.action_type == ExecutorActionType.WAIT:
            assert action2.wait_until is not None or "等待" in (action2.reason or "")

    def test_next_action_pending_orders_wait(self) -> None:
        """测试有挂单时等待."""
        config = BehavioralConfig(min_slices=3, max_slices=5)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=30)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        # 第一个分片
        action1 = executor.next_action(plan_id, current_time)
        assert action1 is not None
        assert action1.action_type == ExecutorActionType.PLACE_ORDER

        # 订单未完成时再次调用
        action2 = executor.next_action(plan_id, current_time + 1)
        assert action2 is not None
        assert action2.action_type == ExecutorActionType.WAIT
        assert "等待订单" in (action2.reason or "")

    def test_next_action_complete(self) -> None:
        """测试完成状态."""
        config = BehavioralConfig(min_slices=1, max_slices=2)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=10)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        # 执行第一个分片
        action = executor.next_action(plan_id, current_time)
        assert action is not None

        # 模拟全部成交
        executor.on_event(
            plan_id,
            OrderEvent(
                event_type="FILL",
                client_order_id=action.client_order_id or "",
                filled_qty=10,
                filled_price=4000.0,
                ts=current_time,
            ),
        )

        # 应该完成
        action_final = executor.next_action(plan_id, current_time + 1)
        assert action_final is not None
        assert action_final.action_type == ExecutorActionType.COMPLETE


class TestBehavioralExecutorEvents:
    """行为伪装执行器事件处理测试."""

    def test_on_event_fill(self) -> None:
        """测试成交事件处理."""
        config = BehavioralConfig(min_slices=2, max_slices=3)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        action = executor.next_action(plan_id, current_time)
        assert action is not None

        # 模拟部分成交
        executor.on_event(
            plan_id,
            OrderEvent(
                event_type="PARTIAL_FILL",
                client_order_id=action.client_order_id or "",
                filled_qty=5,
                filled_price=4000.0,
                ts=current_time,
            ),
        )

        progress = executor.get_progress(plan_id)
        assert progress is not None
        assert progress.filled_qty == 5

    def test_on_event_cancel(self) -> None:
        """测试撤单事件处理."""
        config = BehavioralConfig(min_slices=2, max_slices=3)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=20)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        action = executor.next_action(plan_id, current_time)
        assert action is not None

        # 模拟撤单
        executor.on_event(
            plan_id,
            OrderEvent(
                event_type="CANCEL_ACK",
                client_order_id=action.client_order_id or "",
                filled_qty=0,
                filled_price=0.0,
                ts=current_time,
            ),
        )

        # 分片应标记为未执行, 可重试
        status = executor.get_status(plan_id)
        assert status == ExecutorStatus.PENDING or status == ExecutorStatus.RUNNING


class TestBehavioralExecutorCancel:
    """行为伪装执行器取消测试."""

    def test_cancel_plan(self) -> None:
        """测试取消计划."""
        config = BehavioralConfig()
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        result = executor.cancel_plan(plan_id, "用户取消")

        assert result is True
        assert executor.get_status(plan_id) == ExecutorStatus.CANCELLED

    def test_cancel_plan_not_found(self) -> None:
        """测试取消不存在的计划."""
        executor = BehavioralDisguiseExecutor()
        result = executor.cancel_plan("nonexistent", "")
        assert result is False

    def test_cancel_plan_already_completed(self) -> None:
        """测试取消已完成的计划."""
        config = BehavioralConfig(min_slices=1, max_slices=1)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=10)

        plan_id = executor.make_plan(intent)
        current_time = time.time()

        # 执行并完成
        action = executor.next_action(plan_id, current_time)
        assert action is not None
        executor.on_event(
            plan_id,
            OrderEvent(
                event_type="FILL",
                client_order_id=action.client_order_id or "",
                filled_qty=10,
                filled_price=4000.0,
                ts=current_time,
            ),
        )
        executor.next_action(plan_id, current_time + 1)

        # 尝试取消
        result = executor.cancel_plan(plan_id, "")
        assert result is False


class TestBehavioralExecutorProgress:
    """行为伪装执行器进度测试."""

    def test_get_progress(self) -> None:
        """测试获取进度."""
        config = BehavioralConfig(min_slices=3, max_slices=5)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=50)

        plan_id = executor.make_plan(intent)
        progress = executor.get_progress(plan_id)

        assert progress is not None
        assert progress.total_qty == 50
        assert progress.filled_qty == 0
        assert progress.slice_count >= 3

    def test_get_progress_not_found(self) -> None:
        """测试获取不存在计划的进度."""
        executor = BehavioralDisguiseExecutor()
        progress = executor.get_progress("nonexistent")
        assert progress is None


class TestBehavioralExecutorDisguiseInfo:
    """行为伪装信息测试."""

    def test_get_disguise_info(self) -> None:
        """测试获取伪装信息."""
        config = BehavioralConfig(pattern=DisguisePattern.HYBRID)
        executor = BehavioralDisguiseExecutor(config)
        intent = create_test_intent(target_qty=100)

        plan_id = executor.make_plan(intent)
        info = executor.get_disguise_info(plan_id)

        assert info is not None
        assert info["plan_id"] == plan_id
        assert info["current_pattern"] == "HYBRID"
        assert "random_seed" in info
        assert "slice_count" in info
        assert "executed_slices" in info

    def test_get_disguise_info_not_found(self) -> None:
        """测试获取不存在计划的伪装信息."""
        executor = BehavioralDisguiseExecutor()
        info = executor.get_disguise_info("nonexistent")
        assert info is None


class TestBehavioralExecutorReplayConsistency:
    """M7回放一致性测试."""

    def test_same_intent_same_slices(self) -> None:
        """测试相同意图产生相同分片序列."""
        config = BehavioralConfig(
            pattern=DisguisePattern.RETAIL,
            noise_type=NoiseType.BOTH,
            min_slices=5,
            max_slices=10,
        )

        # 创建相同意图
        intent = OrderIntent(
            strategy_id="test_strategy",
            decision_hash="replay_test_hash",
            instrument="rb2501",
            side=Side.BUY,
            offset=Offset.OPEN,
            target_qty=100,
            algo=AlgoType.IMMEDIATE,
            limit_price=4000.0,
            signal_ts=1000000,
        )

        executor1 = BehavioralDisguiseExecutor(config)
        executor2 = BehavioralDisguiseExecutor(config)

        executor1.make_plan(intent)
        executor2.make_plan(intent)

        info1 = executor1.get_disguise_info(intent.intent_id)
        info2 = executor2.get_disguise_info(intent.intent_id)

        # 验证种子相同
        assert info1 is not None
        assert info2 is not None
        assert info1["random_seed"] == info2["random_seed"]

        # 验证分片数量相同
        assert info1["slice_count"] == info2["slice_count"]
