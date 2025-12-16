"""
保证金监控模块测试 - MarginMonitor (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §19 保证金制度
V4 Scenarios: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL

军规 M16: 保证金实时监控测试覆盖
"""

from datetime import datetime, timedelta

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


# ============================================================
# 枚举类测试
# ============================================================


class TestMarginLevelEnum:
    """MarginLevel 枚举测试."""

    def test_all_levels_exist(self) -> None:
        """测试所有等级存在."""
        assert MarginLevel.SAFE.value == "安全"
        assert MarginLevel.NORMAL.value == "正常"
        assert MarginLevel.WARNING.value == "预警"
        assert MarginLevel.DANGER.value == "危险"
        assert MarginLevel.CRITICAL.value == "临界"

    def test_level_count(self) -> None:
        """测试等级数量."""
        assert len(MarginLevel) == 5


class TestMarginStatusEnum:
    """MarginStatus 枚举测试."""

    def test_all_statuses_exist(self) -> None:
        """测试所有状态存在."""
        assert MarginStatus.HEALTHY.value == "HEALTHY"
        assert MarginStatus.RESTRICTED.value == "RESTRICTED"
        assert MarginStatus.FROZEN.value == "FROZEN"
        assert MarginStatus.MARGIN_CALL.value == "MARGIN_CALL"
        assert MarginStatus.FORCE_LIQUIDATION.value == "FORCE_LIQUIDATION"

    def test_status_count(self) -> None:
        """测试状态数量."""
        assert len(MarginStatus) == 5


# ============================================================
# 配置类测试
# ============================================================


class TestMarginConfig:
    """MarginConfig 配置测试."""

    def test_default_values(self) -> None:
        """测试默认配置值."""
        config = MarginConfig()
        assert config.safe_threshold == 0.5
        assert config.normal_threshold == 0.7
        assert config.warning_threshold == 0.85
        assert config.danger_threshold == 1.0
        assert config.min_available_margin == 10000.0
        assert config.max_snapshot_history == 1000
        assert config.margin_buffer_pct == 0.1

    def test_custom_values(self) -> None:
        """测试自定义配置值."""
        config = MarginConfig(
            safe_threshold=0.4,
            normal_threshold=0.6,
            warning_threshold=0.8,
            danger_threshold=0.95,
            min_available_margin=5000.0,
            max_snapshot_history=500,
            margin_buffer_pct=0.05,
        )
        assert config.safe_threshold == 0.4
        assert config.normal_threshold == 0.6
        assert config.min_available_margin == 5000.0

    def test_config_is_frozen(self) -> None:
        """测试配置不可变."""
        config = MarginConfig()
        with pytest.raises(Exception):  # frozen dataclass
            config.safe_threshold = 0.6  # type: ignore


# ============================================================
# 快照和告警测试
# ============================================================


class TestMarginSnapshot:
    """MarginSnapshot 快照测试."""

    def test_snapshot_creation(self) -> None:
        """测试快照创建."""
        now = datetime.now()
        snapshot = MarginSnapshot(
            timestamp=now,
            equity=100000.0,
            margin_used=60000.0,
            margin_available=40000.0,
            usage_ratio=0.6,
            level=MarginLevel.NORMAL,
            status=MarginStatus.HEALTHY,
        )
        assert snapshot.equity == 100000.0
        assert snapshot.margin_used == 60000.0
        assert snapshot.level == MarginLevel.NORMAL

    def test_snapshot_to_dict(self) -> None:
        """测试快照转字典."""
        now = datetime.now()
        snapshot = MarginSnapshot(
            timestamp=now,
            equity=100000.0,
            margin_used=60000.0,
            margin_available=40000.0,
            usage_ratio=0.6,
            level=MarginLevel.NORMAL,
            status=MarginStatus.HEALTHY,
        )
        d = snapshot.to_dict()
        assert d["equity"] == 100000.0
        assert d["level"] == "正常"
        assert d["status"] == "HEALTHY"
        assert "timestamp" in d


class TestMarginAlert:
    """MarginAlert 告警测试."""

    def test_alert_creation(self) -> None:
        """测试告警创建."""
        now = datetime.now()
        alert = MarginAlert(
            timestamp=now,
            level=MarginLevel.WARNING,
            previous_level=MarginLevel.NORMAL,
            message="保证金等级升级",
            usage_ratio=0.75,
            equity=100000.0,
            margin_used=75000.0,
            action_required="建议减仓",
        )
        assert alert.level == MarginLevel.WARNING
        assert alert.previous_level == MarginLevel.NORMAL

    def test_alert_to_dict(self) -> None:
        """测试告警转字典."""
        now = datetime.now()
        alert = MarginAlert(
            timestamp=now,
            level=MarginLevel.WARNING,
            previous_level=MarginLevel.NORMAL,
            message="保证金等级升级",
            usage_ratio=0.75,
            equity=100000.0,
            margin_used=75000.0,
            action_required="建议减仓",
        )
        d = alert.to_dict()
        assert d["level"] == "预警"
        assert d["previous_level"] == "正常"
        assert "timestamp" in d


# ============================================================
# CHINA.MARGIN.RATIO_CHECK: 保证金率检查
# ============================================================


class TestMarginRatioCheck:
    """RULE_ID: CHINA.MARGIN.RATIO_CHECK 保证金率检查测试."""

    def test_safe_level_below_50_percent(self) -> None:
        """测试安全等级: 使用率 < 50%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=40000.0)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.4
        assert monitor.status == MarginStatus.HEALTHY

    def test_normal_level_50_to_70_percent(self) -> None:
        """测试正常等级: 50% <= 使用率 < 70%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=60000.0)
        assert level == MarginLevel.NORMAL
        assert monitor.usage_ratio == 0.6
        assert monitor.status == MarginStatus.HEALTHY

    def test_warning_level_70_to_85_percent(self) -> None:
        """测试预警等级: 70% <= 使用率 < 85%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=80000.0)
        assert level == MarginLevel.WARNING
        assert monitor.usage_ratio == 0.8
        assert monitor.status == MarginStatus.RESTRICTED

    def test_danger_level_85_to_100_percent(self) -> None:
        """测试危险等级: 85% <= 使用率 < 100%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=95000.0)
        assert level == MarginLevel.DANGER
        assert monitor.usage_ratio == 0.95
        assert monitor.status == MarginStatus.MARGIN_CALL

    def test_critical_level_above_100_percent(self) -> None:
        """测试临界等级: 使用率 >= 100%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=110000.0)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 1.1
        assert monitor.status == MarginStatus.FORCE_LIQUIDATION

    def test_boundary_50_percent(self) -> None:
        """测试边界值: 正好50%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=50000.0)
        assert level == MarginLevel.NORMAL  # 50%属于NORMAL

    def test_boundary_70_percent(self) -> None:
        """测试边界值: 正好70%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=70000.0)
        assert level == MarginLevel.WARNING  # 70%属于WARNING

    def test_boundary_85_percent(self) -> None:
        """测试边界值: 正好85%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=85000.0)
        assert level == MarginLevel.DANGER  # 85%属于DANGER

    def test_boundary_100_percent(self) -> None:
        """测试边界值: 正好100%."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=100000.0)
        assert level == MarginLevel.CRITICAL  # 100%属于CRITICAL


# ============================================================
# CHINA.MARGIN.USAGE_MONITOR: 保证金使用监控
# ============================================================


class TestMarginUsageMonitor:
    """RULE_ID: CHINA.MARGIN.USAGE_MONITOR 保证金使用监控测试."""

    def test_update_basic(self) -> None:
        """测试基础更新功能."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert monitor.equity == 100000.0
        assert monitor.margin_used == 60000.0
        assert monitor.margin_available == 40000.0

    def test_update_with_timestamp(self) -> None:
        """测试带时间戳的更新."""
        monitor = MarginMonitor()
        ts = datetime(2025, 12, 16, 10, 0, 0)
        monitor.update(equity=100000.0, margin_used=60000.0, timestamp=ts)
        assert monitor.last_update == ts

    def test_multiple_updates(self) -> None:
        """测试多次更新."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)
        assert monitor.level == MarginLevel.SAFE

        monitor.update(equity=100000.0, margin_used=60000.0)
        assert monitor.level == MarginLevel.NORMAL

        monitor.update(equity=100000.0, margin_used=80000.0)
        assert monitor.level == MarginLevel.WARNING

    def test_snapshot_recorded(self) -> None:
        """测试快照记录."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert len(monitor.snapshots) == 1

        monitor.update(equity=100000.0, margin_used=70000.0)
        assert len(monitor.snapshots) == 2

    def test_snapshot_max_history(self) -> None:
        """测试快照历史上限."""
        config = MarginConfig(max_snapshot_history=5)
        monitor = MarginMonitor(config=config)

        for i in range(10):
            monitor.update(equity=100000.0, margin_used=float(i * 10000))

        assert len(monitor.snapshots) == 5  # 最多保留5条

    def test_zero_equity_handling(self) -> None:
        """测试零权益处理."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0.0, margin_used=10000.0)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 1.0

    def test_zero_margin_handling(self) -> None:
        """测试零保证金处理."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=0.0)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.0

    def test_negative_values_handled(self) -> None:
        """测试负值处理."""
        monitor = MarginMonitor()
        monitor.update(equity=-10000.0, margin_used=-5000.0)
        # 负值应被处理为0
        assert monitor.equity == 0.0
        assert monitor.margin_used == 0.0

    def test_get_available_margin(self) -> None:
        """测试获取可用保证金."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert monitor.get_available_margin() == 40000.0

    def test_get_margin_summary(self) -> None:
        """测试获取保证金摘要."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)
        summary = monitor.get_margin_summary()

        assert summary["equity"] == 100000.0
        assert summary["margin_used"] == 60000.0
        assert summary["margin_available"] == 40000.0
        assert summary["level"] == "正常"
        assert summary["status"] == "HEALTHY"
        assert "action_required" in summary

    def test_get_risk_indicator(self) -> None:
        """测试风险指标计算."""
        monitor = MarginMonitor()

        monitor.update(equity=100000.0, margin_used=50000.0)
        assert monitor.get_risk_indicator() == 0.5

        monitor.update(equity=100000.0, margin_used=120000.0)
        assert monitor.get_risk_indicator() == 1.0  # 超过100%时截断为1


# ============================================================
# CHINA.MARGIN.WARNING_LEVEL: 保证金预警等级
# ============================================================


class TestMarginWarningLevel:
    """RULE_ID: CHINA.MARGIN.WARNING_LEVEL 保证金预警等级测试."""

    def test_alert_generated_on_level_change(self) -> None:
        """测试等级变化时生成告警."""
        monitor = MarginMonitor()

        # 初始状态是SAFE
        monitor.update(equity=100000.0, margin_used=30000.0)
        assert len(monitor.alerts) == 0  # 初始无告警

        # 升级到NORMAL
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert len(monitor.alerts) == 1
        assert monitor.alerts[0].level == MarginLevel.NORMAL
        assert monitor.alerts[0].previous_level == MarginLevel.SAFE

    def test_alert_direction_upgrade(self) -> None:
        """测试告警方向: 风险升级."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)
        monitor.update(equity=100000.0, margin_used=80000.0)

        alert = monitor.alerts[0]
        assert "升级" in alert.message

    def test_alert_direction_downgrade(self) -> None:
        """测试告警方向: 风险降级."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=80000.0)  # WARNING
        monitor.update(equity=100000.0, margin_used=30000.0)  # SAFE

        # 第一个告警是从SAFE到WARNING (因为初始是SAFE)
        # 第二个告警是从WARNING到SAFE
        assert len(monitor.alerts) == 2
        assert "降级" in monitor.alerts[1].message

    def test_no_alert_when_level_unchanged(self) -> None:
        """测试等级不变时不生成告警."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)  # NORMAL
        monitor.update(equity=100000.0, margin_used=65000.0)  # 仍然是NORMAL

        # 只有第一次从SAFE到NORMAL的告警
        assert len(monitor.alerts) == 1

    def test_previous_level_tracking(self) -> None:
        """测试之前等级追踪."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)  # SAFE
        assert monitor.previous_level == MarginLevel.SAFE

        monitor.update(equity=100000.0, margin_used=60000.0)  # NORMAL
        assert monitor.previous_level == MarginLevel.SAFE

        monitor.update(equity=100000.0, margin_used=80000.0)  # WARNING
        assert monitor.previous_level == MarginLevel.NORMAL

    def test_clear_alerts(self) -> None:
        """测试清除告警."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)
        monitor.update(equity=100000.0, margin_used=60000.0)
        monitor.update(equity=100000.0, margin_used=80000.0)

        count = monitor.clear_alerts()
        assert count == 2
        assert len(monitor.alerts) == 0


# ============================================================
# 开仓检查测试
# ============================================================


class TestCanOpenPosition:
    """开仓检查测试."""

    def test_can_open_when_safe(self) -> None:
        """测试安全状态下可以开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)

        result = monitor.can_open_position(required_margin=10000.0)
        assert result.can_open is True
        assert "通过" in result.reason

    def test_cannot_open_when_critical(self) -> None:
        """测试临界状态下不能开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=110000.0)

        result = monitor.can_open_position(required_margin=5000.0)
        assert result.can_open is False
        assert "FORCE_LIQUIDATION" in result.reason

    def test_cannot_open_when_margin_call(self) -> None:
        """测试追保状态下不能开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=90000.0)  # DANGER

        result = monitor.can_open_position(required_margin=5000.0)
        assert result.can_open is False
        assert "追保" in result.reason

    def test_cannot_open_when_restricted(self) -> None:
        """测试受限状态下不能开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=80000.0)  # WARNING

        result = monitor.can_open_position(required_margin=5000.0)
        assert result.can_open is False
        assert "受限" in result.reason

    def test_cannot_open_when_insufficient_margin(self) -> None:
        """测试保证金不足时不能开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=60000.0)

        # 可用保证金40000, 需要含缓冲55000
        result = monitor.can_open_position(required_margin=50000.0)
        assert result.can_open is False
        assert "可用保证金不足" in result.reason

    def test_cannot_open_when_projected_danger(self) -> None:
        """测试开仓后会进入危险等级时不能开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=40000.0)

        # 开仓后使用率会超过85%
        result = monitor.can_open_position(required_margin=50000.0)
        assert result.can_open is False
        assert "危险" in result.reason or "DANGER" in str(result.projected_level)

    def test_can_open_with_warning(self) -> None:
        """测试开仓后会进入预警等级时可以开仓但有警告."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=40000.0)

        # 开仓后使用率70%~85%
        result = monitor.can_open_position(required_margin=25000.0)
        assert result.can_open is True
        assert "警告" in result.reason
        assert result.projected_level == MarginLevel.WARNING

    def test_min_available_margin_check(self) -> None:
        """测试最小可用保证金检查."""
        config = MarginConfig(min_available_margin=20000.0)
        monitor = MarginMonitor(config=config)
        monitor.update(equity=100000.0, margin_used=50000.0)

        # 开仓后可用保证金低于20000
        result = monitor.can_open_position(required_margin=35000.0)
        assert result.can_open is False
        assert "低于最小要求" in result.reason

    def test_open_position_check_result_fields(self) -> None:
        """测试开仓检查结果字段."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)

        result = monitor.can_open_position(required_margin=10000.0)
        assert result.required_margin == 10000.0
        assert result.available_margin == 70000.0
        assert result.projected_usage_ratio == pytest.approx(0.4)
        assert result.projected_level == MarginLevel.SAFE


# ============================================================
# 减仓建议测试
# ============================================================


class TestReducePositionAdvice:
    """减仓建议测试."""

    def test_should_reduce_when_critical(self) -> None:
        """测试临界状态下应减仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=110000.0)

        should_reduce, reason = monitor.should_reduce_position()
        assert should_reduce is True
        assert "必须立即减仓" in reason

    def test_should_reduce_when_danger(self) -> None:
        """测试危险状态下应减仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=90000.0)

        should_reduce, reason = monitor.should_reduce_position()
        assert should_reduce is True
        assert "强烈建议减仓" in reason

    def test_should_reduce_when_warning(self) -> None:
        """测试预警状态下应减仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=80000.0)

        should_reduce, reason = monitor.should_reduce_position()
        assert should_reduce is True
        assert "建议适当减仓" in reason

    def test_no_reduce_when_safe(self) -> None:
        """测试安全状态下无需减仓."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)

        should_reduce, reason = monitor.should_reduce_position()
        assert should_reduce is False
        assert "无需减仓" in reason

    def test_recommended_reduce_pct_critical(self) -> None:
        """测试临界状态下建议减仓比例."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=120000.0)

        pct = monitor.get_recommended_reduce_pct()
        assert pct > 0.5  # 需要减仓超过50%

    def test_recommended_reduce_pct_danger(self) -> None:
        """测试危险状态下建议减仓比例."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=90000.0)

        pct = monitor.get_recommended_reduce_pct()
        assert 0 < pct <= 0.5

    def test_recommended_reduce_pct_safe(self) -> None:
        """测试安全状态下建议减仓比例."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=30000.0)

        pct = monitor.get_recommended_reduce_pct()
        assert pct == 0.0


# ============================================================
# 监控器状态管理测试
# ============================================================


class TestMonitorStateManagement:
    """监控器状态管理测试."""

    def test_reset(self) -> None:
        """测试重置监控器."""
        monitor = MarginMonitor()
        monitor.update(equity=100000.0, margin_used=80000.0)
        monitor.update(equity=100000.0, margin_used=60000.0)

        monitor.reset()

        assert monitor.equity == 0.0
        assert monitor.margin_used == 0.0
        assert monitor.margin_available == 0.0
        assert monitor.usage_ratio == 0.0
        assert monitor.level == MarginLevel.SAFE
        assert monitor.status == MarginStatus.HEALTHY
        assert len(monitor.snapshots) == 0
        assert len(monitor.alerts) == 0
        assert monitor.last_update is None

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = MarginConfig(
            safe_threshold=0.4,
            normal_threshold=0.6,
            warning_threshold=0.8,
        )
        monitor = MarginMonitor(config=config)

        # 45%应该是NORMAL (因为safe_threshold=0.4)
        level = monitor.update(equity=100000.0, margin_used=45000.0)
        assert level == MarginLevel.NORMAL


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_monitor_singleton(self) -> None:
        """测试默认监控器单例."""
        m1 = get_default_monitor()
        m2 = get_default_monitor()
        assert m1 is m2

    def test_check_margin_function(self) -> None:
        """测试 check_margin 便捷函数."""
        # 重置单例状态
        monitor = get_default_monitor()
        monitor.reset()

        level, action = check_margin(equity=100000.0, margin_used=60000.0)
        assert level == MarginLevel.NORMAL
        assert "注意仓位控制" in action

    def test_can_open_function_with_update(self) -> None:
        """测试 can_open 便捷函数 (带更新)."""
        # 重置单例状态
        monitor = get_default_monitor()
        monitor.reset()

        result, reason = can_open(
            required_margin=10000.0,
            equity=100000.0,
            margin_used=30000.0,
        )
        assert result is True
        assert "通过" in reason

    def test_can_open_function_without_update(self) -> None:
        """测试 can_open 便捷函数 (不更新)."""
        # 先更新
        monitor = get_default_monitor()
        monitor.update(equity=100000.0, margin_used=80000.0)

        # 不带更新参数调用
        result, reason = can_open(required_margin=5000.0)
        assert result is False  # WARNING状态不能开仓


# ============================================================
# 军规 M16 测试
# ============================================================


class TestMilitaryRuleM16:
    """军规 M16: 保证金实时监控测试.

    RULE_ID: CHINA.MARGIN.*
    军规 M16: 保证金使用率必须实时计算
    """

    def test_realtime_update(self) -> None:
        """测试实时更新."""
        monitor = MarginMonitor()

        # 模拟实时更新
        for i in range(10):
            margin_used = float(i * 10000)
            monitor.update(equity=100000.0, margin_used=margin_used)
            # 每次更新后状态应该立即反映
            expected_ratio = margin_used / 100000.0
            assert monitor.usage_ratio == pytest.approx(expected_ratio)

    def test_level_actions_defined(self) -> None:
        """测试所有等级都有建议行动."""
        for level in MarginLevel:
            assert level in MarginMonitor.LEVEL_ACTIONS
            assert MarginMonitor.LEVEL_ACTIONS[level]

    def test_status_mapping(self) -> None:
        """测试等级到状态的映射."""
        monitor = MarginMonitor()

        # SAFE -> HEALTHY
        monitor.update(equity=100000.0, margin_used=30000.0)
        assert monitor.status == MarginStatus.HEALTHY

        # NORMAL -> HEALTHY
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert monitor.status == MarginStatus.HEALTHY

        # WARNING -> RESTRICTED
        monitor.update(equity=100000.0, margin_used=80000.0)
        assert monitor.status == MarginStatus.RESTRICTED

        # DANGER -> MARGIN_CALL
        monitor.update(equity=100000.0, margin_used=90000.0)
        assert monitor.status == MarginStatus.MARGIN_CALL

        # CRITICAL -> FORCE_LIQUIDATION
        monitor.update(equity=100000.0, margin_used=110000.0)
        assert monitor.status == MarginStatus.FORCE_LIQUIDATION

    def test_integration_full_cycle(self) -> None:
        """测试完整周期: 安全->危险->安全."""
        monitor = MarginMonitor()

        # 1. 安全状态
        level = monitor.update(equity=100000.0, margin_used=30000.0)
        assert level == MarginLevel.SAFE
        result = monitor.can_open_position(10000.0)
        assert result.can_open is True

        # 2. 逐步增加风险
        monitor.update(equity=100000.0, margin_used=60000.0)
        assert monitor.level == MarginLevel.NORMAL

        monitor.update(equity=100000.0, margin_used=80000.0)
        assert monitor.level == MarginLevel.WARNING
        result = monitor.can_open_position(5000.0)
        assert result.can_open is False

        # 3. 进入危险
        monitor.update(equity=100000.0, margin_used=90000.0)
        assert monitor.level == MarginLevel.DANGER
        should_reduce, _ = monitor.should_reduce_position()
        assert should_reduce is True

        # 4. 恢复到安全
        monitor.update(equity=100000.0, margin_used=30000.0)
        assert monitor.level == MarginLevel.SAFE

        # 5. 检查告警历史
        assert len(monitor.alerts) >= 2


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_very_small_equity(self) -> None:
        """测试极小权益."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0.01, margin_used=0.005)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.5  # NORMAL边界

    def test_very_large_values(self) -> None:
        """测试极大值."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1e12, margin_used=5e11)
        assert level == MarginLevel.NORMAL
        assert monitor.usage_ratio == pytest.approx(0.5)

    def test_floating_point_precision(self) -> None:
        """测试浮点精度."""
        monitor = MarginMonitor()
        # 精确的边界值
        level = monitor.update(equity=100000.0, margin_used=49999.99)
        assert level == MarginLevel.SAFE

        level = monitor.update(equity=100000.0, margin_used=50000.0)
        assert level == MarginLevel.NORMAL

    def test_zero_both_values(self) -> None:
        """测试两个值都为零."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0.0, margin_used=0.0)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.0

    def test_margin_exceeds_equity_significantly(self) -> None:
        """测试保证金大幅超过权益."""
        monitor = MarginMonitor()
        level = monitor.update(equity=100000.0, margin_used=200000.0)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 2.0
        assert monitor.get_risk_indicator() == 1.0  # 截断为1
