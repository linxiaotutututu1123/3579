"""
保证金监控模块测试 (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §19 保证金制度

军规覆盖:
- M6: 熔断保护
- M16: 保证金实时监控

场景覆盖:
- CHINA.MARGIN.RATIO_CHECK: 保证金率检查
- CHINA.MARGIN.USAGE_MONITOR: 保证金使用监控
- CHINA.MARGIN.WARNING_LEVEL: 保证金预警等级
"""

from datetime import datetime

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


# =============================================================================
# MarginLevel枚举测试
# =============================================================================


class TestMarginLevel:
    """MarginLevel枚举测试."""

    RULE_ID = "CHINA.MARGIN.WARNING_LEVEL"

    def test_level_values(self) -> None:
        """测试等级值."""
        assert MarginLevel.SAFE.value == "安全"
        assert MarginLevel.NORMAL.value == "正常"
        assert MarginLevel.WARNING.value == "预警"
        assert MarginLevel.DANGER.value == "危险"
        assert MarginLevel.CRITICAL.value == "临界"

    def test_is_safe(self) -> None:
        """测试安全判断."""
        assert MarginLevel.SAFE.is_safe() is True
        assert MarginLevel.NORMAL.is_safe() is False
        assert MarginLevel.WARNING.is_safe() is False
        assert MarginLevel.DANGER.is_safe() is False
        assert MarginLevel.CRITICAL.is_safe() is False

    def test_is_tradeable(self) -> None:
        """测试可交易判断."""
        assert MarginLevel.SAFE.is_tradeable() is True
        assert MarginLevel.NORMAL.is_tradeable() is True
        assert MarginLevel.WARNING.is_tradeable() is True
        assert MarginLevel.DANGER.is_tradeable() is False
        assert MarginLevel.CRITICAL.is_tradeable() is False

    def test_requires_action(self) -> None:
        """测试需要行动判断."""
        assert MarginLevel.SAFE.requires_action() is False
        assert MarginLevel.NORMAL.requires_action() is False
        assert MarginLevel.WARNING.requires_action() is False
        assert MarginLevel.DANGER.requires_action() is True
        assert MarginLevel.CRITICAL.requires_action() is True

    def test_to_emoji(self) -> None:
        """测试表情符号转换."""
        assert MarginLevel.SAFE.to_emoji() == "🟢"
        assert MarginLevel.NORMAL.to_emoji() == "🔵"
        assert MarginLevel.WARNING.to_emoji() == "🟡"
        assert MarginLevel.DANGER.to_emoji() == "🟠"
        assert MarginLevel.CRITICAL.to_emoji() == "🔴"


class TestMarginStatus:
    """MarginStatus枚举测试."""

    def test_status_values(self) -> None:
        """测试状态值."""
        assert MarginStatus.ACTIVE.value == "监控中"
        assert MarginStatus.PAUSED.value == "暂停"
        assert MarginStatus.ERROR.value == "异常"


# =============================================================================
# MarginConfig配置测试
# =============================================================================


class TestMarginConfig:
    """MarginConfig配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = MarginConfig()
        assert config.safe_threshold == 0.50
        assert config.warning_threshold == 0.70
        assert config.danger_threshold == 0.85
        assert config.critical_threshold == 1.00
        assert config.min_available_margin == 0.0
        assert config.alert_cooldown_seconds == 300
        assert config.history_max_size == 1000

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = MarginConfig(
            safe_threshold=0.40,
            warning_threshold=0.60,
            danger_threshold=0.80,
            critical_threshold=0.95,
            min_available_margin=10000.0,
            alert_cooldown_seconds=60,
            history_max_size=500,
        )
        assert config.safe_threshold == 0.40
        assert config.warning_threshold == 0.60
        assert config.danger_threshold == 0.80
        assert config.critical_threshold == 0.95
        assert config.min_available_margin == 10000.0

    def test_invalid_safe_warning_threshold(self) -> None:
        """测试无效阈值 - 安全>=预警."""
        with pytest.raises(ValueError, match="安全阈值.*必须小于预警阈值"):
            MarginConfig(safe_threshold=0.70, warning_threshold=0.60)

    def test_invalid_warning_danger_threshold(self) -> None:
        """测试无效阈值 - 预警>=危险."""
        with pytest.raises(ValueError, match="预警阈值.*必须小于危险阈值"):
            MarginConfig(warning_threshold=0.85, danger_threshold=0.80)

    def test_invalid_danger_critical_threshold(self) -> None:
        """测试无效阈值 - 危险>=临界."""
        with pytest.raises(ValueError, match="危险阈值.*必须小于临界阈值"):
            MarginConfig(danger_threshold=1.00, critical_threshold=0.95)

    def test_negative_min_available_margin(self) -> None:
        """测试负数最低可用保证金."""
        with pytest.raises(ValueError, match="最低可用保证金不能为负数"):
            MarginConfig(min_available_margin=-1000.0)

    def test_config_frozen(self) -> None:
        """测试配置不可变."""
        config = MarginConfig()
        with pytest.raises(AttributeError):  # frozen dataclass raises AttributeError
            config.safe_threshold = 0.60  # type: ignore[misc]


# =============================================================================
# MarginSnapshot快照测试
# =============================================================================


class TestMarginSnapshot:
    """MarginSnapshot快照测试."""

    def test_snapshot_creation(self) -> None:
        """测试快照创建."""
        ts = datetime.now()
        snapshot = MarginSnapshot(
            timestamp=ts,
            equity=1_000_000.0,
            margin_used=600_000.0,
            margin_available=400_000.0,
            usage_ratio=0.60,
            level=MarginLevel.NORMAL,
        )
        assert snapshot.equity == 1_000_000.0
        assert snapshot.margin_used == 600_000.0
        assert snapshot.margin_available == 400_000.0
        assert snapshot.usage_ratio == 0.60
        assert snapshot.level == MarginLevel.NORMAL

    def test_snapshot_to_dict(self) -> None:
        """测试快照转字典."""
        ts = datetime(2025, 12, 16, 10, 30, 0)
        snapshot = MarginSnapshot(
            timestamp=ts,
            equity=1_000_000.0,
            margin_used=600_000.0,
            margin_available=400_000.0,
            usage_ratio=0.60,
            level=MarginLevel.NORMAL,
        )
        d = snapshot.to_dict()
        assert d["timestamp"] == "2025-12-16T10:30:00"
        assert d["equity"] == 1_000_000.0
        assert d["level"] == "正常"


# =============================================================================
# MarginAlert告警测试
# =============================================================================


class TestMarginAlert:
    """MarginAlert告警测试."""

    def test_alert_creation(self) -> None:
        """测试告警创建."""
        ts = datetime.now()
        alert = MarginAlert(
            timestamp=ts,
            level=MarginLevel.WARNING,
            previous_level=MarginLevel.NORMAL,
            usage_ratio=0.75,
            equity=1_000_000.0,
            margin_used=750_000.0,
            message="保证金等级升级: 正常 → 预警",
            requires_action=False,
        )
        assert alert.level == MarginLevel.WARNING
        assert alert.previous_level == MarginLevel.NORMAL
        assert alert.requires_action is False

    def test_alert_requires_action(self) -> None:
        """测试告警需要行动."""
        ts = datetime.now()
        alert = MarginAlert(
            timestamp=ts,
            level=MarginLevel.DANGER,
            previous_level=MarginLevel.WARNING,
            usage_ratio=0.90,
            equity=1_000_000.0,
            margin_used=900_000.0,
            message="保证金等级升级: 预警 → 危险",
            requires_action=True,
        )
        assert alert.requires_action is True

    def test_alert_to_dict(self) -> None:
        """测试告警转字典."""
        ts = datetime(2025, 12, 16, 10, 30, 0)
        alert = MarginAlert(
            timestamp=ts,
            level=MarginLevel.WARNING,
            previous_level=MarginLevel.NORMAL,
            usage_ratio=0.75,
            equity=1_000_000.0,
            margin_used=750_000.0,
            message="test",
            requires_action=False,
        )
        d = alert.to_dict()
        assert d["level"] == "预警"
        assert d["previous_level"] == "正常"


# =============================================================================
# OpenPositionCheckResult测试
# =============================================================================


class TestOpenPositionCheckResult:
    """OpenPositionCheckResult测试."""

    def test_result_can_open(self) -> None:
        """测试可开仓结果."""
        result = OpenPositionCheckResult(
            can_open=True,
            reason="保证金充足, 可以开仓",
            current_level=MarginLevel.SAFE,
            usage_ratio=0.30,
            available_margin=700_000.0,
            required_margin=50_000.0,
            margin_after=0.35,
        )
        assert result.can_open is True
        assert result.margin_after == 0.35

    def test_result_cannot_open(self) -> None:
        """测试不可开仓结果."""
        result = OpenPositionCheckResult(
            can_open=False,
            reason="保证金处于危险等级, 禁止开仓",
            current_level=MarginLevel.DANGER,
            usage_ratio=0.90,
            available_margin=100_000.0,
            required_margin=50_000.0,
        )
        assert result.can_open is False

    def test_result_to_dict(self) -> None:
        """测试结果转字典."""
        result = OpenPositionCheckResult(
            can_open=True,
            reason="test",
            current_level=MarginLevel.SAFE,
            usage_ratio=0.30,
            available_margin=700_000.0,
            required_margin=50_000.0,
        )
        d = result.to_dict()
        assert d["can_open"] is True
        assert d["current_level"] == "安全"


# =============================================================================
# MarginMonitor监控器测试 - 核心场景
# =============================================================================


class TestMarginMonitorRatioCheck:
    """CHINA.MARGIN.RATIO_CHECK 保证金率检查测试."""

    RULE_ID = "CHINA.MARGIN.RATIO_CHECK"

    def test_usage_ratio_safe(self) -> None:
        """测试安全使用率 (< 50%)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=400_000)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.40

    def test_usage_ratio_normal(self) -> None:
        """测试正常使用率 (50% - 70%)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=600_000)
        assert level == MarginLevel.NORMAL
        assert monitor.usage_ratio == 0.60

    def test_usage_ratio_warning(self) -> None:
        """测试预警使用率 (70% - 85%)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=750_000)
        assert level == MarginLevel.WARNING
        assert monitor.usage_ratio == 0.75

    def test_usage_ratio_danger(self) -> None:
        """测试危险使用率 (85% - 100%)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=900_000)
        assert level == MarginLevel.DANGER
        assert monitor.usage_ratio == 0.90

    def test_usage_ratio_critical(self) -> None:
        """测试临界使用率 (>= 100%)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=1_000_000)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 1.00

    def test_usage_ratio_over_100_percent(self) -> None:
        """测试超过100%使用率."""
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=1_200_000)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 1.20

    def test_zero_equity_with_margin(self) -> None:
        """测试零权益有保证金 (无穷大使用率)."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0, margin_used=100_000)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == float("inf")

    def test_zero_equity_zero_margin(self) -> None:
        """测试零权益零保证金."""
        monitor = MarginMonitor()
        level = monitor.update(equity=0, margin_used=0)
        assert level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.0

    def test_available_margin_calculation(self) -> None:
        """测试可用保证金计算."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)
        assert monitor.margin_available == 400_000.0
        assert monitor.get_available_margin() == 400_000.0

    def test_available_margin_negative_protection(self) -> None:
        """测试可用保证金负数保护."""
        monitor = MarginMonitor()
        monitor.update(equity=500_000, margin_used=600_000)
        assert monitor.margin_available == 0.0  # 不返回负数


class TestMarginMonitorUsageMonitor:
    """CHINA.MARGIN.USAGE_MONITOR 保证金使用监控测试."""

    RULE_ID = "CHINA.MARGIN.USAGE_MONITOR"

    def test_update_with_timestamp(self) -> None:
        """测试带时间戳更新."""
        monitor = MarginMonitor()
        ts = datetime(2025, 12, 16, 10, 30, 0)
        level = monitor.update(equity=1_000_000, margin_used=400_000, timestamp=ts)
        assert level == MarginLevel.SAFE
        assert monitor.last_update == ts

    def test_update_count(self) -> None:
        """测试更新计数."""
        monitor = MarginMonitor()
        assert monitor.update_count == 0
        monitor.update(equity=1_000_000, margin_used=400_000)
        assert monitor.update_count == 1
        monitor.update(equity=1_000_000, margin_used=500_000)
        assert monitor.update_count == 2

    def test_history_recording(self) -> None:
        """测试历史记录."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        monitor.update(equity=1_000_000, margin_used=600_000)
        monitor.update(equity=1_000_000, margin_used=800_000)

        history = monitor.get_history()
        assert len(history) == 3
        # 从新到旧
        assert history[0].margin_used == 800_000.0
        assert history[1].margin_used == 600_000.0
        assert history[2].margin_used == 400_000.0

    def test_history_limit(self) -> None:
        """测试历史记录限制."""
        monitor = MarginMonitor()
        for i in range(5):
            monitor.update(equity=1_000_000, margin_used=i * 100_000)

        history = monitor.get_history(limit=3)
        assert len(history) == 3

    def test_history_max_size(self) -> None:
        """测试历史记录最大数量."""
        config = MarginConfig(history_max_size=5)
        monitor = MarginMonitor(config=config)
        for i in range(10):
            monitor.update(equity=1_000_000, margin_used=i * 100_000)

        history = monitor.get_history()
        assert len(history) == 5  # 最多保留5条

    def test_get_snapshot(self) -> None:
        """测试获取当前快照."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)
        snapshot = monitor.get_snapshot()
        assert snapshot.equity == 1_000_000.0
        assert snapshot.margin_used == 600_000.0
        assert snapshot.level == MarginLevel.NORMAL

    def test_invalid_equity(self) -> None:
        """测试无效权益."""
        monitor = MarginMonitor()
        with pytest.raises(ValueError, match="权益不能为负数"):
            monitor.update(equity=-100, margin_used=0)

    def test_invalid_margin_used(self) -> None:
        """测试无效已用保证金."""
        monitor = MarginMonitor()
        with pytest.raises(ValueError, match="已用保证金不能为负数"):
            monitor.update(equity=1_000_000, margin_used=-100)


class TestMarginMonitorWarningLevel:
    """CHINA.MARGIN.WARNING_LEVEL 保证金预警等级测试."""

    RULE_ID = "CHINA.MARGIN.WARNING_LEVEL"

    def test_level_transition_safe_to_normal(self) -> None:
        """测试等级变化: 安全 → 正常."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        assert monitor.level == MarginLevel.SAFE

        monitor.update(equity=1_000_000, margin_used=550_000)
        assert monitor.level == MarginLevel.NORMAL

    def test_level_transition_normal_to_warning(self) -> None:
        """测试等级变化: 正常 → 预警."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)
        assert monitor.level == MarginLevel.NORMAL

        monitor.update(equity=1_000_000, margin_used=750_000)
        assert monitor.level == MarginLevel.WARNING

    def test_level_transition_warning_to_danger(self) -> None:
        """测试等级变化: 预警 → 危险."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=750_000)
        assert monitor.level == MarginLevel.WARNING

        monitor.update(equity=1_000_000, margin_used=900_000)
        assert monitor.level == MarginLevel.DANGER

    def test_level_transition_danger_to_critical(self) -> None:
        """测试等级变化: 危险 → 临界."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=900_000)
        assert monitor.level == MarginLevel.DANGER

        monitor.update(equity=1_000_000, margin_used=1_000_000)
        assert monitor.level == MarginLevel.CRITICAL

    def test_level_transition_down(self) -> None:
        """测试等级下降: 危险 → 预警 → 正常."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=900_000)
        assert monitor.level == MarginLevel.DANGER

        monitor.update(equity=1_000_000, margin_used=750_000)
        assert monitor.level == MarginLevel.WARNING

        monitor.update(equity=1_000_000, margin_used=600_000)
        assert monitor.level == MarginLevel.NORMAL

    def test_alert_generation_on_level_change(self) -> None:
        """测试等级变化时生成告警."""
        config = MarginConfig(alert_cooldown_seconds=0)  # 禁用冷却
        monitor = MarginMonitor(config=config)

        # 初始安全
        monitor.update(equity=1_000_000, margin_used=400_000)
        assert len(monitor.get_alerts()) == 0  # 首次不告警

        # 变为正常
        monitor.update(equity=1_000_000, margin_used=550_000)
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].level == MarginLevel.NORMAL
        assert alerts[0].previous_level == MarginLevel.SAFE

    def test_no_alert_on_same_level(self) -> None:
        """测试同等级不告警."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        monitor.update(equity=1_000_000, margin_used=450_000)  # 仍然安全
        assert len(monitor.get_alerts()) == 0

    def test_custom_thresholds(self) -> None:
        """测试自定义阈值."""
        config = MarginConfig(
            safe_threshold=0.40,
            warning_threshold=0.60,
            danger_threshold=0.80,
            critical_threshold=0.95,
        )
        monitor = MarginMonitor(config=config)

        # 45% 应该是正常 (不是安全)
        monitor.update(equity=1_000_000, margin_used=450_000)
        assert monitor.level == MarginLevel.NORMAL

        # 65% 应该是预警 (不是正常)
        monitor.update(equity=1_000_000, margin_used=650_000)
        assert monitor.level == MarginLevel.WARNING


# =============================================================================
# can_open_position 开仓检查测试
# =============================================================================


class TestCanOpenPosition:
    """can_open_position 开仓检查测试."""

    RULE_ID = "CHINA.MARGIN.RATIO_CHECK"

    def test_can_open_safe_level(self) -> None:
        """测试安全等级可开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=300_000)
        result = monitor.can_open_position(50_000)
        assert result.can_open is True
        assert "保证金充足" in result.reason

    def test_can_open_normal_level(self) -> None:
        """测试正常等级可开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=550_000)
        result = monitor.can_open_position(50_000)
        assert result.can_open is True

    def test_can_open_warning_level_allowed(self) -> None:
        """测试预警等级允许开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=750_000)
        result = monitor.can_open_position(50_000, allow_warning=True)
        assert result.can_open is True

    def test_cannot_open_warning_level_disallowed(self) -> None:
        """测试预警等级不允许开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=750_000)
        result = monitor.can_open_position(50_000, allow_warning=False)
        assert result.can_open is False
        assert "预警等级" in result.reason

    def test_cannot_open_danger_level(self) -> None:
        """测试危险等级禁止开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=900_000)
        result = monitor.can_open_position(50_000)
        assert result.can_open is False
        assert "危险等级" in result.reason

    def test_cannot_open_critical_level(self) -> None:
        """测试临界等级禁止开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=1_000_000)
        result = monitor.can_open_position(50_000)
        assert result.can_open is False
        assert "临界等级" in result.reason

    def test_cannot_open_insufficient_margin(self) -> None:
        """测试保证金不足禁止开仓."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        # 可用保证金 600_000，需要 700_000
        result = monitor.can_open_position(700_000)
        assert result.can_open is False
        assert "可用保证金不足" in result.reason

    def test_cannot_open_would_exceed_danger(self) -> None:
        """测试开仓后超过危险等级."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)
        # 开仓后 600000 + 250000 = 850000，使用率85%，达到危险等级
        result = monitor.can_open_position(250_000)
        assert result.can_open is False
        assert "危险" in result.reason

    def test_cannot_open_negative_margin(self) -> None:
        """测试负数保证金."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        result = monitor.can_open_position(-10_000)
        assert result.can_open is False
        assert "不能为负数" in result.reason

    def test_cannot_open_min_available_margin(self) -> None:
        """测试开仓后低于最低可用保证金."""
        config = MarginConfig(min_available_margin=100_000)
        monitor = MarginMonitor(config=config)
        monitor.update(equity=1_000_000, margin_used=400_000)
        # 可用 600_000，开仓 550_000，剩余 50_000 < 100_000
        result = monitor.can_open_position(550_000)
        assert result.can_open is False
        assert "低于最低要求" in result.reason

    def test_margin_after_calculation(self) -> None:
        """测试开仓后使用率计算."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=400_000)
        result = monitor.can_open_position(100_000)
        assert result.can_open is True
        # (400_000 + 100_000) / 1_000_000 = 0.50
        assert result.margin_after == pytest.approx(0.50)


# =============================================================================
# 监控器状态管理测试
# =============================================================================


class TestMarginMonitorStateManagement:
    """监控器状态管理测试."""

    def test_initial_state(self) -> None:
        """测试初始状态."""
        monitor = MarginMonitor()
        assert monitor.equity == 0.0
        assert monitor.margin_used == 0.0
        assert monitor.usage_ratio == 0.0
        assert monitor.level == MarginLevel.SAFE
        assert monitor.status == MarginStatus.ACTIVE
        assert monitor.update_count == 0
        assert monitor.last_update is None

    def test_reset(self) -> None:
        """测试重置状态."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)
        monitor.update(equity=1_000_000, margin_used=800_000)

        monitor.reset()
        assert monitor.equity == 0.0
        assert monitor.margin_used == 0.0
        assert monitor.update_count == 0
        assert len(monitor.get_history()) == 0
        assert len(monitor.get_alerts()) == 0

    def test_pause_resume(self) -> None:
        """测试暂停恢复."""
        monitor = MarginMonitor()
        assert monitor.status == MarginStatus.ACTIVE

        monitor.pause()
        assert monitor.status == MarginStatus.PAUSED

        monitor.resume()
        assert monitor.status == MarginStatus.ACTIVE

    def test_get_stats(self) -> None:
        """测试获取统计信息."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)

        stats = monitor.get_stats()
        assert stats["status"] == "监控中"
        assert stats["level"] == "正常"
        assert stats["equity"] == 1_000_000.0
        assert stats["margin_used"] == 600_000.0
        assert stats["margin_available"] == 400_000.0
        assert stats["usage_ratio"] == 0.60
        assert stats["update_count"] == 1

    def test_properties(self) -> None:
        """测试属性访问."""
        monitor = MarginMonitor()
        monitor.update(equity=1_000_000, margin_used=600_000)

        assert monitor.equity == 1_000_000.0
        assert monitor.margin_used == 600_000.0
        assert monitor.margin_available == 400_000.0
        assert monitor.usage_ratio == 0.60
        assert monitor.level == MarginLevel.NORMAL
        assert monitor.update_count == 1
        assert monitor.last_update is not None


# =============================================================================
# 告警系统测试
# =============================================================================


class TestMarginAlertSystem:
    """告警系统测试."""

    def test_alert_on_level_upgrade(self) -> None:
        """测试等级升高告警."""
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        monitor.update(equity=1_000_000, margin_used=400_000)
        monitor.update(equity=1_000_000, margin_used=900_000)

        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].level == MarginLevel.DANGER
        assert "升级" in alerts[0].message

    def test_alert_on_level_downgrade(self) -> None:
        """测试等级降低告警."""
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        monitor.update(equity=1_000_000, margin_used=900_000)
        monitor.update(equity=1_000_000, margin_used=400_000)

        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].level == MarginLevel.SAFE
        assert "降级" in alerts[0].message

    def test_alert_cooldown(self) -> None:
        """测试告警冷却."""
        config = MarginConfig(alert_cooldown_seconds=300)
        monitor = MarginMonitor(config=config)

        # 第一次告警
        monitor.update(equity=1_000_000, margin_used=400_000)
        monitor.update(equity=1_000_000, margin_used=550_000)
        assert len(monitor.get_alerts()) == 1

        # 冷却期内不告警
        monitor.update(equity=1_000_000, margin_used=750_000)
        assert len(monitor.get_alerts()) == 1  # 仍然是1

    def test_alert_requires_action(self) -> None:
        """测试告警需要行动标记."""
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        monitor.update(equity=1_000_000, margin_used=400_000)
        monitor.update(equity=1_000_000, margin_used=900_000)

        alerts = monitor.get_alerts()
        assert alerts[0].requires_action is True

    def test_alert_limit(self) -> None:
        """测试告警数量限制."""
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        monitor.update(equity=1_000_000, margin_used=400_000)

        # 连续多次等级变化
        values = [600_000, 750_000, 900_000, 600_000, 400_000]
        for v in values:
            monitor.update(equity=1_000_000, margin_used=v)

        alerts = monitor.get_alerts(limit=3)
        assert len(alerts) == 3


# =============================================================================
# 边界条件测试
# =============================================================================


class TestMarginMonitorEdgeCases:
    """边界条件测试."""

    def test_threshold_boundary_50_percent(self) -> None:
        """测试50%边界 (安全/正常)."""
        monitor = MarginMonitor()

        # 刚好50%是正常
        monitor.update(equity=1_000_000, margin_used=500_000)
        assert monitor.level == MarginLevel.NORMAL

        # 49.9%是安全
        monitor.update(equity=1_000_000, margin_used=499_000)
        assert monitor.level == MarginLevel.SAFE

    def test_threshold_boundary_70_percent(self) -> None:
        """测试70%边界 (正常/预警)."""
        monitor = MarginMonitor()

        # 刚好70%是预警
        monitor.update(equity=1_000_000, margin_used=700_000)
        assert monitor.level == MarginLevel.WARNING

        # 69.9%是正常
        monitor.update(equity=1_000_000, margin_used=699_000)
        assert monitor.level == MarginLevel.NORMAL

    def test_threshold_boundary_85_percent(self) -> None:
        """测试85%边界 (预警/危险)."""
        monitor = MarginMonitor()

        # 刚好85%是危险
        monitor.update(equity=1_000_000, margin_used=850_000)
        assert monitor.level == MarginLevel.DANGER

        # 84.9%是预警
        monitor.update(equity=1_000_000, margin_used=849_000)
        assert monitor.level == MarginLevel.WARNING

    def test_threshold_boundary_100_percent(self) -> None:
        """测试100%边界 (危险/临界)."""
        monitor = MarginMonitor()

        # 刚好100%是临界
        monitor.update(equity=1_000_000, margin_used=1_000_000)
        assert monitor.level == MarginLevel.CRITICAL

        # 99.9%是危险
        monitor.update(equity=1_000_000, margin_used=999_000)
        assert monitor.level == MarginLevel.DANGER

    def test_very_small_equity(self) -> None:
        """测试极小权益."""
        monitor = MarginMonitor()
        monitor.update(equity=100, margin_used=50)
        assert monitor.level == MarginLevel.NORMAL
        assert monitor.usage_ratio == 0.50

    def test_very_large_equity(self) -> None:
        """测试极大权益."""
        monitor = MarginMonitor()
        monitor.update(equity=100_000_000_000, margin_used=40_000_000_000)
        assert monitor.level == MarginLevel.SAFE
        assert monitor.usage_ratio == 0.40


# =============================================================================
# 便捷函数测试
# =============================================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_get_default_monitor(self) -> None:
        """测试获取默认监控器."""
        monitor1 = get_default_monitor()
        monitor2 = get_default_monitor()
        assert monitor1 is monitor2  # 单例

    def test_check_margin(self) -> None:
        """测试快捷检查保证金等级."""
        level = check_margin(equity=1_000_000, margin_used=400_000)
        assert level == MarginLevel.SAFE

    def test_can_open(self) -> None:
        """测试快捷检查开仓."""
        # 先更新状态
        check_margin(equity=1_000_000, margin_used=400_000)
        can, reason = can_open(required_margin=50_000)
        assert can is True
        assert "保证金充足" in reason


# =============================================================================
# 军规M16综合测试
# =============================================================================


class TestMilitaryRuleM16:
    """军规M16: 保证金实时监控综合测试."""

    RULE_ID = "M16.MARGIN.REALTIME_MONITOR"

    def test_realtime_monitoring_scenario(self) -> None:
        """测试实时监控场景.

        模拟一个交易日的保证金变化过程:
        1. 开盘: 安全状态
        2. 开仓: 正常状态
        3. 加仓: 预警状态
        4. 浮亏: 危险状态
        5. 减仓: 正常状态
        """
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        # 1. 开盘 - 安全
        level = monitor.update(equity=1_000_000, margin_used=200_000)
        assert level == MarginLevel.SAFE
        assert monitor.level.is_tradeable()

        # 2. 开仓 - 正常
        level = monitor.update(equity=1_000_000, margin_used=550_000)
        assert level == MarginLevel.NORMAL
        result = monitor.can_open_position(100_000)
        assert result.can_open is True

        # 3. 加仓 - 预警
        level = monitor.update(equity=1_000_000, margin_used=750_000)
        assert level == MarginLevel.WARNING
        result = monitor.can_open_position(100_000, allow_warning=False)
        assert result.can_open is False

        # 4. 浮亏 - 危险 (权益下降)
        level = monitor.update(equity=900_000, margin_used=800_000)
        assert level == MarginLevel.DANGER
        assert level.requires_action()
        result = monitor.can_open_position(50_000)
        assert result.can_open is False

        # 5. 减仓 - 正常
        level = monitor.update(equity=900_000, margin_used=500_000)
        assert level == MarginLevel.NORMAL
        assert level.is_tradeable()

        # 验证告警记录
        alerts = monitor.get_alerts()
        assert len(alerts) >= 3  # 多次等级变化

    def test_forced_liquidation_warning(self) -> None:
        """测试强平风险预警.

        军规M16: 保证金使用率≥100%时必须发出强平预警
        """
        config = MarginConfig(alert_cooldown_seconds=0)
        monitor = MarginMonitor(config=config)

        # 初始正常
        monitor.update(equity=1_000_000, margin_used=600_000)

        # 进入临界状态
        level = monitor.update(equity=1_000_000, margin_used=1_000_000)
        assert level == MarginLevel.CRITICAL
        assert level.requires_action()

        # 检查告警
        alerts = monitor.get_alerts()
        critical_alerts = [a for a in alerts if a.level == MarginLevel.CRITICAL]
        assert len(critical_alerts) >= 1
        assert critical_alerts[0].requires_action is True

    def test_margin_call_scenario(self) -> None:
        """测试追保场景.

        模拟权益下降导致保证金率上升
        """
        monitor = MarginMonitor()

        # 初始正常
        level = monitor.update(equity=1_000_000, margin_used=600_000)
        assert level == MarginLevel.NORMAL

        # 权益下降50%，保证金率翻倍
        level = monitor.update(equity=500_000, margin_used=600_000)
        assert level == MarginLevel.CRITICAL
        assert monitor.usage_ratio == 1.20
