"""
Guardian Triggers 测试.

V2 Scenarios:
- GUARD.DETECT.QUOTE_STALE: 行情 stale 检测
- GUARD.DETECT.ORDER_STUCK: 订单卡住检测
- GUARD.DETECT.POSITION_DRIFT: 持仓漂移检测
- GUARD.DETECT.LEG_IMBALANCE: 腿不平衡检测
"""

import time

from src.guardian.triggers import (
    LegImbalanceTrigger,
    OrderStuckTrigger,
    PositionDriftTrigger,
    QuoteStaleTrigger,
    TriggerManager,
)


class TestQuoteStaleTrigger:
    """QuoteStaleTrigger 测试类."""

    def test_guard_detect_quote_stale_triggered(self) -> None:
        """GUARD.DETECT.QUOTE_STALE: 行情过期触发."""
        trigger = QuoteStaleTrigger(hard_stale_ms=5000.0)
        now = time.time()
        state = {
            "quote_timestamps": {"AO2501": now - 10.0},  # 10秒前
            "now_ts": now,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "quote_stale"
        assert "AO2501" in result.details["stale_symbols"]

    def test_guard_detect_quote_stale_not_triggered(self) -> None:
        """GUARD.DETECT.QUOTE_STALE: 行情正常不触发."""
        trigger = QuoteStaleTrigger(hard_stale_ms=5000.0)
        now = time.time()
        state = {
            "quote_timestamps": {"AO2501": now - 1.0},  # 1秒前
            "now_ts": now,
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_quote_stale_missing_symbol(self) -> None:
        """测试缺少行情的合约."""
        trigger = QuoteStaleTrigger(hard_stale_ms=5000.0, symbols=["AO2501", "SA2501"])
        now = time.time()
        state = {
            "quote_timestamps": {"AO2501": now},  # 只有 AO2501
            "now_ts": now,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert "SA2501" in result.details["stale_symbols"]

    def test_quote_stale_name(self) -> None:
        """测试触发器名称."""
        trigger = QuoteStaleTrigger()
        assert trigger.name == "quote_stale"


class TestOrderStuckTrigger:
    """OrderStuckTrigger 测试类."""

    def test_guard_detect_order_stuck_triggered(self) -> None:
        """GUARD.DETECT.ORDER_STUCK: 订单卡住触发."""
        trigger = OrderStuckTrigger(stuck_timeout_s=60.0)
        now = time.time()
        state = {
            "active_orders": [
                {"order_id": "ord1", "last_update_ts": now - 120.0},  # 120秒前
            ],
            "now_ts": now,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "order_stuck"
        assert "ord1" in result.details["stuck_orders"]

    def test_guard_detect_order_stuck_not_triggered(self) -> None:
        """GUARD.DETECT.ORDER_STUCK: 订单正常不触发."""
        trigger = OrderStuckTrigger(stuck_timeout_s=60.0)
        now = time.time()
        state = {
            "active_orders": [
                {"order_id": "ord1", "last_update_ts": now - 30.0},  # 30秒前
            ],
            "now_ts": now,
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_order_stuck_empty_orders(self) -> None:
        """测试空订单列表."""
        trigger = OrderStuckTrigger()
        state = {"active_orders": [], "now_ts": time.time()}
        result = trigger.check(state)
        assert result.triggered is False

    def test_order_stuck_name(self) -> None:
        """测试触发器名称."""
        trigger = OrderStuckTrigger()
        assert trigger.name == "order_stuck"


class TestPositionDriftTrigger:
    """PositionDriftTrigger 测试类."""

    def test_guard_detect_position_drift_triggered(self) -> None:
        """GUARD.DETECT.POSITION_DRIFT: 持仓漂移触发."""
        trigger = PositionDriftTrigger(tolerance=0)
        state = {
            "local_positions": {"AO2501": 10},
            "broker_positions": {"AO2501": 8},
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "position_drift"
        assert len(result.details["drifted_positions"]) == 1

    def test_guard_detect_position_drift_not_triggered(self) -> None:
        """GUARD.DETECT.POSITION_DRIFT: 持仓一致不触发."""
        trigger = PositionDriftTrigger(tolerance=0)
        state = {
            "local_positions": {"AO2501": 10},
            "broker_positions": {"AO2501": 10},
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_position_drift_with_tolerance(self) -> None:
        """测试带容忍度的持仓漂移."""
        trigger = PositionDriftTrigger(tolerance=2)
        state = {
            "local_positions": {"AO2501": 10},
            "broker_positions": {"AO2501": 8},  # 差2，在容忍范围内
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_position_drift_name(self) -> None:
        """测试触发器名称."""
        trigger = PositionDriftTrigger()
        assert trigger.name == "position_drift"


class TestLegImbalanceTrigger:
    """LegImbalanceTrigger 测试类."""

    def test_guard_detect_leg_imbalance_triggered(self) -> None:
        """GUARD.DETECT.LEG_IMBALANCE: 腿不平衡触发."""
        trigger = LegImbalanceTrigger(threshold=5)
        state = {
            "pair_positions": [
                {
                    "near_symbol": "AO2501",
                    "far_symbol": "AO2505",
                    "near_qty": 20,
                    "far_qty": 5,  # 不平衡 15
                }
            ]
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "leg_imbalance"

    def test_guard_detect_leg_imbalance_not_triggered(self) -> None:
        """GUARD.DETECT.LEG_IMBALANCE: 腿平衡不触发."""
        trigger = LegImbalanceTrigger(threshold=5)
        state = {
            "pair_positions": [
                {
                    "near_symbol": "AO2501",
                    "far_symbol": "AO2505",
                    "near_qty": 10,
                    "far_qty": 10,
                }
            ]
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_leg_imbalance_empty(self) -> None:
        """测试空配对列表."""
        trigger = LegImbalanceTrigger()
        state = {"pair_positions": []}
        result = trigger.check(state)
        assert result.triggered is False

    def test_leg_imbalance_name(self) -> None:
        """测试触发器名称."""
        trigger = LegImbalanceTrigger()
        assert trigger.name == "leg_imbalance"


class TestTriggerManager:
    """TriggerManager 测试类."""

    def test_add_trigger(self) -> None:
        """测试添加触发器."""
        manager = TriggerManager()
        trigger = QuoteStaleTrigger()
        manager.add_trigger(trigger)
        # 验证通过 check_all 能工作
        results = manager.check_all({"quote_timestamps": {}, "now_ts": time.time()})
        assert isinstance(results, list)

    def test_remove_trigger(self) -> None:
        """测试移除触发器."""
        trigger = QuoteStaleTrigger()
        manager = TriggerManager(triggers=[trigger])
        assert manager.remove_trigger("quote_stale") is True
        assert manager.remove_trigger("nonexistent") is False

    def test_check_all(self) -> None:
        """测试检查所有触发器."""
        now = time.time()
        manager = TriggerManager(
            triggers=[
                QuoteStaleTrigger(hard_stale_ms=5000.0),
                OrderStuckTrigger(stuck_timeout_s=60.0),
            ]
        )
        state = {
            "quote_timestamps": {"AO2501": now - 10.0},  # stale
            "active_orders": [],
            "now_ts": now,
        }
        results = manager.check_all(state)
        assert len(results) == 1
        assert results[0].trigger_name == "quote_stale"

    def test_reset_all(self) -> None:
        """测试重置所有触发器."""
        manager = TriggerManager(triggers=[QuoteStaleTrigger()])
        manager.reset_all()  # 应该不抛异常
