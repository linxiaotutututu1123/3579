"""
保证金监控模块测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 Scenarios: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL

军规 M16: 保证金实时监控 - 保证金使用率必须实时计算
"""

from __future__ import annotations

import pytest

from src.execution.protection.margin_monitor import (
    MarginAlert,
    MarginConfig,
    MarginLevel,
    MarginMonitor,
    MarginSnapshot,
    MarginStatus,
    OpenPositionCheckResult,
    can_open,
    check_margin,
    get_default_monitor,
)


class TestMarginLevelEnum:
    """保证金等级枚举测试."""

    def test_all_values(self) -> None:
        """测试所有枚举值."""
        assert MarginLevel.SAFE.value == "安全"
        assert MarginLevel.NORMAL.value == "正常"
        assert MarginLevel.WARNING.value == "预警"
        assert MarginLevel.DANGER.value == "危险"
        assert MarginLevel.CRITICAL.value == "临界"

    def test_enum_count(self) -> None:
        """测试枚举数量."""
        assert len(MarginLevel) == 5


class TestMarginConfig:
    """保证金配置测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = MarginConfig()
        assert config.safe_threshold == 0.50
        assert config.normal_threshold == 0.70
        assert config.warning_threshold == 0.85
        assert config.danger_threshold == 1.00
        assert config.min_available_margin == 10000.0
        assert config.enable_alerts is True
        assert config.history_size == 1000

    def test_custom_values(self) -> None:
        """测试自定义值."""
        config = MarginConfig(
            safe_threshold=0.40,
            normal_threshold=0.60,
            warning_threshold=0.80,
            danger_threshold=0.95,
            min_available_margin=50000.0,
            enable_alerts=False,
            history_size=500,
        )
        assert config.safe_threshold == 0.40
        assert config.normal_threshold == 0.60
        assert config.warning_threshold == 0.80
        assert config.danger_threshold == 0.95
        assert config.min_available_margin == 50000.0
        assert config.enable_alerts is False
        assert config.history_size == 500

    def test_frozen_dataclass(self) -> None:
        """测试frozen配置不可变."""
        config = MarginConfig()
        with pytest.raises(AttributeError):
            config.safe_threshold = 0.30  # type: ignore[misc]


class TestMarginSnapshot:
    """保证金快照测试."""

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        from datetime import datetime

        snapshot = MarginSnapshot(
            timestamp=datetime(2025, 12, 16, 10, 0, 0),
            equity=1000000.0,
            margin_used=600000.0,
            margin_available=400000.0,
            usage_ratio=0.60,
            level=MarginLevel.NORMAL,
        )
        result = snapshot.to_dict()
        assert result["equity"] == 1000000.0
        assert result["margin_used"] == 600000.0
        assert result["margin_available"] == 400000.0
        assert result["usage_ratio"] == 0.60
        assert result["level"] == "正常"
        assert "2025-12-16" in result["timestamp"]


class TestMarginAlert:
    """保证金告警测试."""

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        from datetime import datetime

        alert = MarginAlert(
            timestamp=datetime(2025, 12, 16, 10, 0, 0),
            alert_type="LEVEL_UP",
            level=MarginLevel.WARNING,
            previous_level=MarginLevel.NORMAL,
            usage_ratio=0.75,
            message="保证金风险上升",
        )
        result = alert.to_dict()
        assert result["alert_type"] == "LEVEL_UP"
        assert result["level"] == "预警"
        assert result["previous_level"] == "正常"
        assert result["usage_ratio"] == 0.75


class TestOpenPositionCheckResult:
    """开仓检查结果测试."""

    def test_allowed_result(self) -> None:
        """测试允许开仓结果."""
        result = OpenPositionCheckResult(
            allowed=True,
            reason="保证金检查通过",
            available_margin=500000.0,
            required_margin=100000.0,
            projected_usage=0.70,
            projected_level=MarginLevel.WARNING,
        )
        assert result.allowed is True
        assert result.reason == "保证金检查通过"

    def test_rejected_result(self) -> None:
        """测试拒绝开仓结果."""
        result = OpenPositionCheckResult(
            allowed=False,
            reason="可用保证金不足",
            available_margin=50000.0,
            required_margin=100000.0,
        )
        assert result.allowed is False
        assert "不足" in result.reason

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        result = OpenPositionCheckResult(
            allowed=True,
            reason="保证金检查通过",
            projected_level=MarginLevel.NORMAL,
        )
        d = result.to_dict()
        assert d["allowed"] is True
        assert d["projected_level"] == "正常"


class TestMarginStatus:
    """保证金状态测试."""

    def test_default_status(self) -> None:
        """测试默认状态."""
        status = MarginStatus()
        assert status.equity == 0.0
        assert status.margin_used == 0.0
        assert status.margin_available == 0.0
        assert status.usage_ratio == 0.0
        assert status.level == MarginLevel.SAFE
        assert status.last_update is None

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        from datetime import datetime

        status = MarginStatus(
            equity=1000000.0,
            margin_used=600000.0,
            margin_available=400000.0,
            usage_ratio=0.60,
            level=MarginLevel.NORMAL,
            last_update=datetime(2025, 12, 16, 10, 0, 0),
        )
        result = status.to_dict()
        assert result["equity"] == 1000000.0
        assert result["level"] == "正常"


class TestMarginMonitorInit:
    """MarginMonitor初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        monitor = MarginMonitor()
        assert monitor.config.safe_threshold == 0.50
        assert monitor.status.level == MarginLevel.SAFE
        assert monitor.update_count == 0
        assert monitor.level_change_count == 0

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = MarginConfig(safe_threshold=0.40)
        monitor = MarginMonitor(config=config)
        assert monitor.config.safe_threshold == 0.40


class TestMarginMonitorUpdate:
    """保证金更新测试 (军规 M16).

    RULE_ID: CHINA.MARGIN.USAGE_MONITOR
    """

    def test_update_safe_level(self) -> None:
        """测试更新到安全等级.

        RULE_ID: CHINA.MARGIN.RATIO_CHECK
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=400000.0)
        assert level == MarginLevel.SAFE
        assert monitor.get_usage_ratio() == pytest.approx(0.40)

    def test_update_normal_level(self) -> None:
        """测试更新到正常等级.

        RULE_ID: CHINA.MARGIN.RATIO_CHECK
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=600000.0)
        assert level == MarginLevel.NORMAL
        assert monitor.get_usage_ratio() == pytest.approx(0.60)

    def test_update_warning_level(self) -> None:
        """测试更新到预警等级.

        RULE_ID: CHINA.MARGIN.WARNING_LEVEL
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=750000.0)
        assert level == MarginLevel.WARNING
        assert monitor.get_usage_ratio() == pytest.approx(0.75)

    def test_update_danger_level(self) -> None:
        """测试更新到危险等级.

        RULE_ID: CHINA.MARGIN.WARNING_LEVEL
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=900000.0)
        assert level == MarginLevel.DANGER
        assert monitor.get_usage_ratio() == pytest.approx(0.90)

    def test_update_critical_level(self) -> None:
        """测试更新到临界等级.

        RULE_ID: CHINA.MARGIN.WARNING_LEVEL
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=1000000.0)
        assert level == MarginLevel.CRITICAL
        assert monitor.get_usage_ratio() == pytest.approx(1.00)

    def test_update_over_100_percent(self) -> None:
        """测试超过100%使用率.

        RULE_ID: CHINA.MARGIN.WARNING_LEVEL
        """
        monitor = MarginMonitor()
        level = monitor.update(equity=1000000.0, margin_used=1200000.0)
        assert level == MarginLevel.CRITICAL
        assert monitor.get_usage_ratio() == pytest.approx(1.20)

    def test_update_zero_equity(self) -> None:
        """测试零权益."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0.0, margin_used=100000.0)
        assert level == MarginLevel.CRITICAL  # 使用率100%

    def test_update_count(self) -> None:
        """测试更新次数计数."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)
        monitor.update(1000000.0, 500000.0)
        monitor.update(1000000.0, 600000.0)
        assert monitor.update_count == 3


class TestMarginMonitorLevelChange:
    """等级变化测试."""

    def test_level_change_count(self) -> None:
        """测试等级变化计数."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # SAFE
        monitor.update(1000000.0, 600000.0)  # NORMAL (变化)
        monitor.update(1000000.0, 650000.0)  # NORMAL (无变化)
        monitor.update(1000000.0, 750000.0)  # WARNING (变化)
        assert monitor.level_change_count == 2

    def test_alert_generation_on_level_up(self) -> None:
        """测试风险上升时生成告警."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # SAFE
        monitor.update(1000000.0, 750000.0)  # WARNING (风险上升)

        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_type == "LEVEL_UP"
        assert alerts[0].level == MarginLevel.WARNING
        assert alerts[0].previous_level == MarginLevel.SAFE

    def test_alert_generation_on_level_down(self) -> None:
        """测试风险下降时生成告警."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 750000.0)  # WARNING
        monitor.update(1000000.0, 400000.0)  # SAFE (风险下降)

        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_type == "LEVEL_DOWN"
        assert alerts[0].level == MarginLevel.SAFE

    def test_no_alert_when_disabled(self) -> None:
        """测试禁用告警时不生成."""
        config = MarginConfig(enable_alerts=False)
        monitor = MarginMonitor(config=config)
        monitor.update(1000000.0, 400000.0)  # SAFE
        monitor.update(1000000.0, 750000.0)  # WARNING

        alerts = monitor.get_alerts()
        assert len(alerts) == 0


class TestMarginMonitorCanOpenPosition:
    """开仓检查测试 (军规 M16).

    RULE_ID: CHINA.MARGIN.RATIO_CHECK
    """

    def test_can_open_with_sufficient_margin(self) -> None:
        """测试有足够保证金时允许开仓.

        RULE_ID: CHINA.MARGIN.RATIO_CHECK
        """
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # 可用600000

        can, reason = monitor.can_open_position(100000.0)
        assert can is True
        assert "通过" in reason

    def test_cannot_open_insufficient_margin(self) -> None:
        """测试保证金不足时拒绝开仓.

        RULE_ID: CHINA.MARGIN.RATIO_CHECK
        """
        monitor = MarginMonitor()
        monitor.update(1000000.0, 900000.0)  # 可用100000

        can, reason = monitor.can_open_position(200000.0)
        assert can is False
        assert "不足" in reason

    def test_cannot_open_below_min_available(self) -> None:
        """测试低于最低可用保证金时拒绝开仓."""
        config = MarginConfig(min_available_margin=50000.0)
        monitor = MarginMonitor(config=config)
        monitor.update(1000000.0, 900000.0)  # 可用100000

        # 开仓后可用60000, 高于min
        can, reason = monitor.can_open_position(40000.0)
        assert can is True

        # 开仓后可用30000, 低于min
        can, reason = monitor.can_open_position(70000.0)
        assert can is False
        assert "低于最低要求" in reason

    def test_cannot_open_would_reach_critical(self) -> None:
        """测试开仓后会达到临界状态时拒绝."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 850000.0)  # 可用150000, DANGER

        # 开仓后使用率100%
        can, reason = monitor.can_open_position(150000.0)
        assert can is False
        assert "临界" in reason

    def test_check_open_position_detailed(self) -> None:
        """测试详细的开仓检查结果."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # 可用600000

        result = monitor.check_open_position(200000.0)
        assert result.allowed is True
        assert result.available_margin == 600000.0
        assert result.required_margin == 200000.0
        assert result.projected_usage == pytest.approx(0.60)
        assert result.projected_level == MarginLevel.NORMAL


class TestMarginMonitorHelpers:
    """辅助方法测试."""

    def test_is_safe(self) -> None:
        """测试is_safe方法."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # SAFE
        assert monitor.is_safe() is True

        monitor.update(1000000.0, 600000.0)  # NORMAL
        assert monitor.is_safe() is True

        monitor.update(1000000.0, 750000.0)  # WARNING
        assert monitor.is_safe() is False

    def test_is_warning(self) -> None:
        """测试is_warning方法."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # SAFE
        assert monitor.is_warning() is False

        monitor.update(1000000.0, 750000.0)  # WARNING
        assert monitor.is_warning() is True

        monitor.update(1000000.0, 900000.0)  # DANGER
        assert monitor.is_warning() is True

    def test_is_critical(self) -> None:
        """测试is_critical方法."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 900000.0)  # DANGER
        assert monitor.is_critical() is False

        monitor.update(1000000.0, 1000000.0)  # CRITICAL
        assert monitor.is_critical() is True

    def test_get_available_margin(self) -> None:
        """测试获取可用保证金."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 600000.0)
        assert monitor.get_available_margin() == 400000.0


class TestMarginMonitorHistory:
    """历史记录测试."""

    def test_history_tracking(self) -> None:
        """测试历史记录追踪."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)
        monitor.update(1000000.0, 500000.0)
        monitor.update(1000000.0, 600000.0)

        history = monitor.get_history()
        assert len(history) == 3
        assert history[0].usage_ratio == pytest.approx(0.40)
        assert history[2].usage_ratio == pytest.approx(0.60)

    def test_history_limit(self) -> None:
        """测试获取有限历史."""
        monitor = MarginMonitor()
        for i in range(10):
            monitor.update(1000000.0, float(i * 100000))

        history = monitor.get_history(limit=3)
        assert len(history) == 3

    def test_history_size_limit(self) -> None:
        """测试历史记录大小限制."""
        config = MarginConfig(history_size=5)
        monitor = MarginMonitor(config=config)
        for i in range(10):
            monitor.update(1000000.0, float(i * 100000))

        history = monitor.get_history()
        assert len(history) == 5


class TestMarginMonitorStats:
    """统计信息测试."""

    def test_get_stats(self) -> None:
        """测试获取统计信息."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)  # SAFE
        monitor.update(1000000.0, 750000.0)  # WARNING

        stats = monitor.get_stats()
        assert stats["update_count"] == 2
        assert stats["level_change_count"] == 1
        assert stats["current_level"] == "预警"
        assert stats["current_usage"] == pytest.approx(0.75)
        assert stats["alert_count"] == 1
        assert stats["history_size"] == 2

    def test_reset(self) -> None:
        """测试重置."""
        monitor = MarginMonitor()
        monitor.update(1000000.0, 400000.0)
        monitor.update(1000000.0, 750000.0)
        monitor.reset()

        assert monitor.update_count == 0
        assert monitor.level_change_count == 0
        assert len(monitor.get_history()) == 0
        assert len(monitor.get_alerts()) == 0
        assert monitor.status.level == MarginLevel.SAFE


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_monitor_singleton(self) -> None:
        """测试默认监控器单例."""
        monitor1 = get_default_monitor()
        monitor2 = get_default_monitor()
        assert monitor1 is monitor2

    def test_check_margin_function(self) -> None:
        """测试check_margin便捷函数."""
        # 重置默认监控器状态
        monitor = get_default_monitor()
        monitor.reset()

        level = check_margin(1000000.0, 600000.0)
        assert level == MarginLevel.NORMAL

    def test_can_open_function(self) -> None:
        """测试can_open便捷函数."""
        monitor = get_default_monitor()
        monitor.reset()
        monitor.update(1000000.0, 400000.0)

        can, reason = can_open(100000.0)
        assert can is True


class TestMilitaryRuleM16:
    """军规 M16 保证金实时监控测试.

    RULE_ID: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL
    军规: M16 - 保证金使用率必须实时计算
    """

    def test_m16_realtime_calculation(self) -> None:
        """M16: 实时计算测试.

        RULE_ID: CHINA.MARGIN.USAGE_MONITOR
        """
        monitor = MarginMonitor()

        # 模拟实时更新
        monitor.update(1000000.0, 400000.0)  # 40%
        assert monitor.get_usage_ratio() == pytest.approx(0.40)

        monitor.update(1000000.0, 600000.0)  # 60%
        assert monitor.get_usage_ratio() == pytest.approx(0.60)

        monitor.update(1000000.0, 800000.0)  # 80%
        assert monitor.get_usage_ratio() == pytest.approx(0.80)

    def test_m16_warning_levels(self) -> None:
        """M16: 预警等级测试.

        RULE_ID: CHINA.MARGIN.WARNING_LEVEL
        """
        monitor = MarginMonitor()

        # 测试所有等级边界
        test_cases = [
            (0.40, MarginLevel.SAFE),       # < 50%
            (0.50, MarginLevel.NORMAL),     # 50% (边界)
            (0.60, MarginLevel.NORMAL),     # 50-70%
            (0.70, MarginLevel.WARNING),    # 70% (边界)
            (0.80, MarginLevel.WARNING),    # 70-85%
            (0.85, MarginLevel.DANGER),     # 85% (边界)
            (0.95, MarginLevel.DANGER),     # 85-100%
            (1.00, MarginLevel.CRITICAL),   # 100% (边界)
            (1.20, MarginLevel.CRITICAL),   # > 100%
        ]

        for usage, expected_level in test_cases:
            margin_used = 1000000.0 * usage
            level = monitor.update(1000000.0, margin_used)
            assert level == expected_level, f"使用率 {usage} 应为 {expected_level.value}"

    def test_m16_open_position_check(self) -> None:
        """M16: 开仓前检查测试.

        RULE_ID: CHINA.MARGIN.RATIO_CHECK
        """
        monitor = MarginMonitor()
        monitor.update(1000000.0, 700000.0)  # 70% WARNING, 可用300000

        # 允许开仓 (不会超过临界)
        result = monitor.check_open_position(100000.0)
        assert result.allowed is True
        assert result.projected_usage == pytest.approx(0.80)

        # 拒绝开仓 (会达到临界)
        result = monitor.check_open_position(300000.0)
        assert result.allowed is False

    def test_m16_audit_trail(self) -> None:
        """M16: 审计追踪测试.

        RULE_ID: CHINA.MARGIN.USAGE_MONITOR
        """
        monitor = MarginMonitor()

        # 更新并验证历史记录
        monitor.update(1000000.0, 400000.0)
        monitor.update(1000000.0, 600000.0)
        monitor.update(1000000.0, 800000.0)

        history = monitor.get_history()
        assert len(history) == 3

        # 验证可审计信息完整
        for snapshot in history:
            d = snapshot.to_dict()
            assert "timestamp" in d
            assert "equity" in d
            assert "margin_used" in d
            assert "usage_ratio" in d
            assert "level" in d


class TestEdgeCases:
    """边界条件测试."""

    def test_very_small_equity(self) -> None:
        """测试极小权益."""
        monitor = MarginMonitor()
        level = monitor.update(1.0, 0.5)
        assert level == MarginLevel.SAFE

    def test_negative_margin_used(self) -> None:
        """测试负保证金使用."""
        monitor = MarginMonitor()
        level = monitor.update(1000000.0, -100000.0)
        assert level == MarginLevel.SAFE  # 使用率为负数, 仍视为安全

    def test_exact_threshold_boundaries(self) -> None:
        """测试精确阈值边界."""
        monitor = MarginMonitor()

        # 恰好在边界值
        monitor.update(100.0, 50.0)  # 恰好50%
        assert monitor.get_level() == MarginLevel.NORMAL

        monitor.update(100.0, 70.0)  # 恰好70%
        assert monitor.get_level() == MarginLevel.WARNING

        monitor.update(100.0, 85.0)  # 恰好85%
        assert monitor.get_level() == MarginLevel.DANGER

        monitor.update(100.0, 100.0)  # 恰好100%
        assert monitor.get_level() == MarginLevel.CRITICAL

    def test_floating_point_precision(self) -> None:
        """测试浮点精度."""
        monitor = MarginMonitor()

        # 使用可能产生精度问题的值
        level = monitor.update(3.0, 1.5)  # 应该是50%
        assert monitor.get_usage_ratio() == pytest.approx(0.5)
        assert level == MarginLevel.NORMAL
