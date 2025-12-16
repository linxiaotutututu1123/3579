"""
中国期货触发器测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 测试
V4 Scenarios:
- CHINA.TRIGGER.LIMIT_PRICE: 涨跌停触发器
- CHINA.TRIGGER.MARGIN_CALL: 保证金追缴触发
- CHINA.TRIGGER.DELIVERY: 交割月接近触发

军规覆盖:
- M6: 熔断保护
- M13: 涨跌停感知
- M15: 夜盘跨日处理
- M16: 保证金实时监控
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from src.guardian.triggers import TriggerManager, TriggerResult
from src.guardian.triggers_china import (
    DeliveryApproachingTrigger,
    DeliveryInfo,
    LimitPriceInfo,
    LimitPriceStatus,
    LimitPriceTrigger,
    MarginInfo,
    MarginLevel,
    MarginTrigger,
    create_default_china_triggers,
    register_china_triggers,
)


# ============================================================
# 枚举测试
# ============================================================


class TestLimitPriceStatusEnum:
    """涨跌停状态枚举测试."""

    def test_all_statuses_exist(self) -> None:
        """测试所有状态存在."""
        assert LimitPriceStatus.NORMAL.value == "NORMAL"
        assert LimitPriceStatus.NEAR_LIMIT_UP.value == "NEAR_LIMIT_UP"
        assert LimitPriceStatus.NEAR_LIMIT_DOWN.value == "NEAR_LIMIT_DOWN"
        assert LimitPriceStatus.AT_LIMIT_UP.value == "AT_LIMIT_UP"
        assert LimitPriceStatus.AT_LIMIT_DOWN.value == "AT_LIMIT_DOWN"

    def test_status_count(self) -> None:
        """测试状态数量."""
        assert len(LimitPriceStatus) == 5


class TestMarginLevelEnum:
    """保证金等级枚举测试."""

    def test_all_levels_exist(self) -> None:
        """测试所有等级存在."""
        assert MarginLevel.SAFE.value == "SAFE"
        assert MarginLevel.NORMAL.value == "NORMAL"
        assert MarginLevel.WARNING.value == "WARNING"
        assert MarginLevel.DANGER.value == "DANGER"
        assert MarginLevel.CRITICAL.value == "CRITICAL"

    def test_level_count(self) -> None:
        """测试等级数量."""
        assert len(MarginLevel) == 5


# ============================================================
# 数据类测试
# ============================================================


class TestLimitPriceInfo:
    """涨跌停信息数据类测试."""

    def test_create_info(self) -> None:
        """测试创建信息."""
        info = LimitPriceInfo(
            symbol="rb2501",
            current_price=4200.0,
            limit_up=4410.0,
            limit_down=3990.0,
            status=LimitPriceStatus.NORMAL,
            distance_to_limit_pct=0.05,
        )
        assert info.symbol == "rb2501"
        assert info.current_price == 4200.0
        assert info.limit_up == 4410.0
        assert info.limit_down == 3990.0
        assert info.status == LimitPriceStatus.NORMAL
        assert info.distance_to_limit_pct == 0.05


class TestMarginInfo:
    """保证金信息数据类测试."""

    def test_create_info(self) -> None:
        """测试创建信息."""
        info = MarginInfo(
            equity=100000.0,
            margin_used=50000.0,
            margin_available=50000.0,
            usage_ratio=0.5,
            level=MarginLevel.SAFE,
        )
        assert info.equity == 100000.0
        assert info.margin_used == 50000.0
        assert info.margin_available == 50000.0
        assert info.usage_ratio == 0.5
        assert info.level == MarginLevel.SAFE


class TestDeliveryInfo:
    """交割信息数据类测试."""

    def test_create_info(self) -> None:
        """测试创建信息."""
        info = DeliveryInfo(
            symbol="rb2501",
            delivery_date=date(2025, 1, 15),
            days_to_delivery=5,
            position=10,
            should_close=False,
        )
        assert info.symbol == "rb2501"
        assert info.delivery_date == date(2025, 1, 15)
        assert info.days_to_delivery == 5
        assert info.position == 10
        assert info.should_close is False


# ============================================================
# 涨跌停触发器测试 - CHINA.TRIGGER.LIMIT_PRICE
# ============================================================


class TestLimitPriceTrigger:
    """涨跌停触发器测试.

    V4 Scenario: CHINA.TRIGGER.LIMIT_PRICE
    军规: M6 熔断保护, M13 涨跌停感知
    """

    RULE_ID = "CHINA.TRIGGER.LIMIT_PRICE"

    def test_name(self) -> None:
        """测试触发器名称."""
        trigger = LimitPriceTrigger()
        assert trigger.name == "limit_price_china"

    def test_no_trigger_normal_price(self) -> None:
        """测试正常价格不触发."""
        trigger = LimitPriceTrigger(near_limit_threshold=0.01)
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4200.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is False
        assert result.trigger_name == "limit_price_china"

    def test_trigger_at_limit_up(self) -> None:
        """测试涨停触发."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["at_limit_count"] == 1
        assert "rb2501" in result.details["at_limit_symbols"]

    def test_trigger_at_limit_down(self) -> None:
        """测试跌停触发."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 3990.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["at_limit_count"] == 1
        assert "rb2501" in result.details["at_limit_symbols"]

    def test_trigger_near_limit_up(self) -> None:
        """测试接近涨停触发."""
        trigger = LimitPriceTrigger(near_limit_threshold=0.02)
        # 涨跌停范围420, 2%阈值=8.4, 4410-8=4402
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4405.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["near_limit_count"] == 1
        assert "rb2501" in result.details["near_limit_symbols"]

    def test_trigger_near_limit_down(self) -> None:
        """测试接近跌停触发."""
        trigger = LimitPriceTrigger(near_limit_threshold=0.02)
        # 跌停+8=3998
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 3995.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["near_limit_count"] == 1

    def test_multiple_symbols(self) -> None:
        """测试多合约检测."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,  # 涨停
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                },
                "hc2501": {
                    "current": 4000.0,  # 正常
                    "limit_up": 4200.0,
                    "limit_down": 3800.0,
                },
                "i2501": {
                    "current": 800.0,  # 跌停
                    "limit_up": 900.0,
                    "limit_down": 800.0,
                },
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["at_limit_count"] == 2
        assert len(result.details["triggered_symbols"]) == 2

    def test_triggered_symbols_property(self) -> None:
        """测试触发合约属性."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        trigger.check(state)
        symbols = trigger.triggered_symbols
        assert "rb2501" in symbols
        assert symbols["rb2501"].status == LimitPriceStatus.AT_LIMIT_UP

    def test_reset(self) -> None:
        """测试重置."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        trigger.check(state)
        assert len(trigger.triggered_symbols) > 0
        trigger.reset()
        assert len(trigger.triggered_symbols) == 0

    def test_empty_state(self) -> None:
        """测试空状态."""
        trigger = LimitPriceTrigger()
        result = trigger.check({})
        assert result.triggered is False

    def test_invalid_prices(self) -> None:
        """测试无效价格."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 0,
                    "limit_up": 0,
                    "limit_down": 0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is False


# ============================================================
# 保证金触发器测试 - CHINA.TRIGGER.MARGIN_CALL
# ============================================================


class TestMarginTrigger:
    """保证金触发器测试.

    V4 Scenario: CHINA.TRIGGER.MARGIN_CALL
    军规: M6 熔断保护, M16 保证金实时监控
    """

    RULE_ID = "CHINA.TRIGGER.MARGIN_CALL"

    def test_name(self) -> None:
        """测试触发器名称."""
        trigger = MarginTrigger()
        assert trigger.name == "margin_china"

    def test_safe_level(self) -> None:
        """测试安全等级 (<50%)."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 40000.0}
        result = trigger.check(state)
        assert result.triggered is False
        assert result.details["level"] == "SAFE"
        assert trigger.last_level == MarginLevel.SAFE

    def test_normal_level(self) -> None:
        """测试正常等级 (50%-70%)."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 60000.0}
        result = trigger.check(state)
        assert result.triggered is False
        assert result.details["level"] == "NORMAL"

    def test_warning_level(self) -> None:
        """测试预警等级 (70%-85%)."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 75000.0}
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["level"] == "WARNING"
        assert result.event_name == "margin_warning"

    def test_danger_level(self) -> None:
        """测试危险等级 (85%-100%)."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 90000.0}
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["level"] == "DANGER"
        assert result.event_name == "margin_danger"

    def test_critical_level(self) -> None:
        """测试临界等级 (>=100%)."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 110000.0}
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["level"] == "CRITICAL"
        assert result.event_name == "margin_critical"

    def test_zero_equity(self) -> None:
        """测试零权益."""
        trigger = MarginTrigger()
        state = {"equity": 0.0, "margin_used": 10000.0}
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["level"] == "CRITICAL"

    def test_zero_margin(self) -> None:
        """测试零保证金."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 0.0}
        result = trigger.check(state)
        assert result.triggered is False
        assert result.details["level"] == "SAFE"

    def test_last_info_property(self) -> None:
        """测试最后信息属性."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 50000.0}
        trigger.check(state)
        info = trigger.last_info
        assert info is not None
        assert info.equity == 100000.0
        assert info.margin_used == 50000.0
        assert info.margin_available == 50000.0
        assert info.usage_ratio == 0.5

    def test_level_changed(self) -> None:
        """测试等级变化检测."""
        trigger = MarginTrigger()
        # 第一次检查
        state1 = {"equity": 100000.0, "margin_used": 40000.0}
        result1 = trigger.check(state1)
        assert result1.details["level_changed"] is True  # 从初始SAFE变化

        # 等级变化
        state2 = {"equity": 100000.0, "margin_used": 75000.0}
        result2 = trigger.check(state2)
        assert result2.details["level_changed"] is True  # SAFE -> WARNING

        # 等级不变
        state3 = {"equity": 100000.0, "margin_used": 80000.0}
        result3 = trigger.check(state3)
        assert result3.details["level_changed"] is False  # 还是WARNING

    def test_action_required(self) -> None:
        """测试建议行动."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 90000.0}
        result = trigger.check(state)
        assert "立即减仓" in result.details["action_required"]

    def test_reset(self) -> None:
        """测试重置."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 90000.0}
        trigger.check(state)
        assert trigger.last_level == MarginLevel.DANGER
        trigger.reset()
        assert trigger.last_level == MarginLevel.SAFE
        assert trigger.last_info is None

    def test_empty_state(self) -> None:
        """测试空状态."""
        trigger = MarginTrigger()
        result = trigger.check({})
        assert result.triggered is False  # 0/0 = 0


# ============================================================
# 交割临近触发器测试 - CHINA.TRIGGER.DELIVERY
# ============================================================


class TestDeliveryApproachingTrigger:
    """交割临近触发器测试.

    V4 Scenario: CHINA.TRIGGER.DELIVERY
    军规: M6 熔断保护, M15 夜盘跨日处理
    """

    RULE_ID = "CHINA.TRIGGER.DELIVERY"

    def test_name(self) -> None:
        """测试触发器名称."""
        trigger = DeliveryApproachingTrigger()
        assert trigger.name == "delivery_approaching_china"

    def test_no_trigger_far_delivery(self) -> None:
        """测试远期交割不触发."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 1)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_trigger_warning(self) -> None:
        """测试预警触发."""
        trigger = DeliveryApproachingTrigger(warning_days=5, critical_days=2)
        current = date(2025, 1, 12)  # 距交割3天
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "delivery_warning"
        assert result.details["warning_count"] == 1
        assert result.details["critical_count"] == 0

    def test_trigger_critical(self) -> None:
        """测试紧急触发."""
        trigger = DeliveryApproachingTrigger(warning_days=5, critical_days=2)
        current = date(2025, 1, 14)  # 距交割1天
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.event_name == "delivery_critical"
        assert result.details["critical_count"] == 1

    def test_skip_zero_position(self) -> None:
        """测试跳过零持仓."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 12)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 0,  # 无持仓
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_skip_expired_contract(self) -> None:
        """测试跳过已过期合约."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 20)  # 已过交割日
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_multiple_positions(self) -> None:
        """测试多持仓检测."""
        trigger = DeliveryApproachingTrigger(warning_days=5, critical_days=2)
        current = date(2025, 1, 12)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),  # 3天 - warning
                    "qty": 10,
                },
                {
                    "symbol": "hc2501",
                    "delivery_date": date(2025, 1, 13),  # 1天 - critical
                    "qty": 5,
                },
                {
                    "symbol": "i2501",
                    "delivery_date": date(2025, 2, 15),  # 远期 - 不触发
                    "qty": 20,
                },
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["warning_count"] == 1
        assert result.details["critical_count"] == 1

    def test_datetime_delivery_date(self) -> None:
        """测试datetime类型交割日期."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 12)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": datetime(2025, 1, 15, 15, 0, 0),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is True

    def test_string_delivery_date(self) -> None:
        """测试字符串类型交割日期."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 12)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": "2025-01-15",
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        result = trigger.check(state)
        assert result.triggered is True

    def test_invalid_string_delivery_date(self) -> None:
        """测试无效字符串日期."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": "invalid-date",
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 12),
        }
        result = trigger.check(state)
        assert result.triggered is False  # 跳过无效日期

    def test_approaching_positions_property(self) -> None:
        """测试接近交割持仓属性."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        current = date(2025, 1, 12)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": current,
        }
        trigger.check(state)
        positions = trigger.approaching_positions
        assert len(positions) == 1
        assert positions[0].symbol == "rb2501"
        assert positions[0].days_to_delivery == 3

    def test_reset(self) -> None:
        """测试重置."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 12),
        }
        trigger.check(state)
        assert len(trigger.approaching_positions) > 0
        trigger.reset()
        assert len(trigger.approaching_positions) == 0

    def test_empty_state(self) -> None:
        """测试空状态."""
        trigger = DeliveryApproachingTrigger()
        result = trigger.check({})
        assert result.triggered is False

    def test_no_delivery_date(self) -> None:
        """测试缺少交割日期."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 12),
        }
        result = trigger.check(state)
        assert result.triggered is False

    def test_default_current_date(self) -> None:
        """测试默认当前日期."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        tomorrow = date.today() + timedelta(days=3)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": tomorrow,
                    "qty": 10,
                }
            ]
        }
        result = trigger.check(state)
        assert result.triggered is True


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_default_china_triggers(self) -> None:
        """测试创建默认触发器."""
        triggers = create_default_china_triggers()
        assert len(triggers) == 3
        names = [t.name for t in triggers]
        assert "limit_price_china" in names
        assert "margin_china" in names
        assert "delivery_approaching_china" in names

    def test_register_china_triggers(self) -> None:
        """测试注册触发器."""
        manager = TriggerManager()
        names = register_china_triggers(manager)
        assert len(names) == 3
        assert "limit_price_china" in names
        assert "margin_china" in names
        assert "delivery_approaching_china" in names


# ============================================================
# TriggerManager 集成测试
# ============================================================


class TestTriggerManagerIntegration:
    """触发器管理器集成测试."""

    def test_check_all_triggers(self) -> None:
        """测试检查所有触发器."""
        manager = TriggerManager()
        register_china_triggers(manager)

        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,  # 涨停
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            },
            "equity": 100000.0,
            "margin_used": 90000.0,  # DANGER
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 12),
        }

        results = manager.check_all(state)
        assert len(results) >= 2  # 至少涨跌停和保证金触发

    def test_no_triggers(self) -> None:
        """测试无触发."""
        manager = TriggerManager()
        register_china_triggers(manager)

        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4200.0,  # 正常
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            },
            "equity": 100000.0,
            "margin_used": 40000.0,  # SAFE
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 2, 15),  # 远期
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 1),
        }

        results = manager.check_all(state)
        assert len(results) == 0


# ============================================================
# 军规覆盖测试
# ============================================================


class TestMilitaryRuleM6:
    """军规 M6 熔断保护测试.

    军规: 触发风控阈值必须立即停止
    """

    RULE_ID = "M6.CIRCUIT_BREAKER"

    def test_margin_critical_circuit_breaker(self) -> None:
        """测试保证金临界触发熔断."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 110000.0}
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["level"] == "CRITICAL"
        assert "紧急平仓" in result.details["action_required"]

    def test_limit_price_circuit_breaker(self) -> None:
        """测试涨跌停触发熔断."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["at_limit_count"] == 1


class TestMilitaryRuleM13:
    """军规 M13 涨跌停感知测试.

    军规: 订单价格必须检查涨跌停板
    """

    RULE_ID = "M13.LIMIT_PRICE_AWARENESS"

    def test_detect_near_limit(self) -> None:
        """测试检测接近涨跌停."""
        trigger = LimitPriceTrigger(near_limit_threshold=0.02)
        # 价格距离涨停仅1%
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4402.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert result.triggered is True
        symbols = trigger.triggered_symbols
        assert symbols["rb2501"].status == LimitPriceStatus.NEAR_LIMIT_UP


class TestMilitaryRuleM16:
    """军规 M16 保证金实时监控测试.

    军规: 保证金使用率必须实时计算
    """

    RULE_ID = "M16.MARGIN_REALTIME_MONITOR"

    def test_realtime_margin_level(self) -> None:
        """测试实时保证金等级."""
        trigger = MarginTrigger()

        # 模拟连续更新
        levels = []
        for margin_used in [30000, 55000, 75000, 90000, 110000]:
            state = {"equity": 100000.0, "margin_used": float(margin_used)}
            result = trigger.check(state)
            levels.append(result.details["level"])

        assert levels == ["SAFE", "NORMAL", "WARNING", "DANGER", "CRITICAL"]

    def test_margin_info_update(self) -> None:
        """测试保证金信息更新."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 70000.0}
        trigger.check(state)

        info = trigger.last_info
        assert info is not None
        assert info.usage_ratio == 0.7
        assert info.margin_available == 30000.0


class TestMilitaryRuleM15:
    """军规 M15 夜盘跨日处理测试.

    军规: 交易日归属必须正确
    """

    RULE_ID = "M15.NIGHT_SESSION_DAY"

    def test_delivery_date_calculation(self) -> None:
        """测试交割日期计算."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        # 模拟夜盘时间检查 (实际夜盘在trading_calendar处理)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 10),  # 假设夜盘后归属1.10
        }
        result = trigger.check(state)
        assert result.triggered is True
        # 1.10 -> 1.15 = 5天 = warning阈值
        assert result.details["warning_count"] == 1


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_limit_price_exact_threshold(self) -> None:
        """测试涨跌停精确阈值."""
        trigger = LimitPriceTrigger(near_limit_threshold=0.01)
        # 范围420, 1%=4.2, 4410-4.2=4405.8
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4405.8,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        # 距离/范围 = 4.2/420 = 0.01 = 阈值边界
        assert result.triggered is True

    def test_margin_exact_threshold(self) -> None:
        """测试保证金精确阈值."""
        trigger = MarginTrigger()
        # 测试50%边界 (SAFE/NORMAL)
        state = {"equity": 100000.0, "margin_used": 50000.0}
        result = trigger.check(state)
        assert result.details["level"] == "NORMAL"  # >=50% is NORMAL

    def test_delivery_exact_warning_days(self) -> None:
        """测试交割精确预警天数."""
        trigger = DeliveryApproachingTrigger(warning_days=5, critical_days=2)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 10),  # 正好5天
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["warning_count"] == 1

    def test_delivery_exact_critical_days(self) -> None:
        """测试交割精确紧急天数."""
        trigger = DeliveryApproachingTrigger(warning_days=5, critical_days=2)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 13),  # 正好2天
        }
        result = trigger.check(state)
        assert result.triggered is True
        assert result.details["critical_count"] == 1

    def test_very_small_margin(self) -> None:
        """测试极小保证金."""
        trigger = MarginTrigger()
        state = {"equity": 100.0, "margin_used": 99.0}
        result = trigger.check(state)
        assert result.details["level"] == "DANGER"  # 99%

    def test_very_large_equity(self) -> None:
        """测试极大权益."""
        trigger = MarginTrigger()
        state = {"equity": 1e12, "margin_used": 1e11}
        result = trigger.check(state)
        assert result.details["level"] == "SAFE"  # 10%

    def test_negative_position(self) -> None:
        """测试负持仓(空头)."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": -10,  # 空头
                }
            ],
            "current_date": date(2025, 1, 12),
        }
        result = trigger.check(state)
        assert result.triggered is True  # 空头也需要移仓


# ============================================================
# TriggerResult 测试
# ============================================================


class TestTriggerResultFormat:
    """触发结果格式测试."""

    def test_limit_price_result_format(self) -> None:
        """测试涨跌停结果格式."""
        trigger = LimitPriceTrigger()
        state = {
            "limit_prices": {
                "rb2501": {
                    "current": 4410.0,
                    "limit_up": 4410.0,
                    "limit_down": 3990.0,
                }
            }
        }
        result = trigger.check(state)
        assert isinstance(result, TriggerResult)
        assert "triggered_symbols" in result.details
        assert "at_limit_count" in result.details
        assert "near_limit_count" in result.details

    def test_margin_result_format(self) -> None:
        """测试保证金结果格式."""
        trigger = MarginTrigger()
        state = {"equity": 100000.0, "margin_used": 80000.0}
        result = trigger.check(state)
        assert isinstance(result, TriggerResult)
        assert "equity" in result.details
        assert "margin_used" in result.details
        assert "usage_ratio" in result.details
        assert "usage_ratio_pct" in result.details
        assert "level" in result.details
        assert "action_required" in result.details

    def test_delivery_result_format(self) -> None:
        """测试交割结果格式."""
        trigger = DeliveryApproachingTrigger(warning_days=5)
        state = {
            "positions": [
                {
                    "symbol": "rb2501",
                    "delivery_date": date(2025, 1, 15),
                    "qty": 10,
                }
            ],
            "current_date": date(2025, 1, 12),
        }
        result = trigger.check(state)
        assert isinstance(result, TriggerResult)
        assert "warning_positions" in result.details
        assert "critical_positions" in result.details
        assert "warning_days_threshold" in result.details
        assert "critical_days_threshold" in result.details
