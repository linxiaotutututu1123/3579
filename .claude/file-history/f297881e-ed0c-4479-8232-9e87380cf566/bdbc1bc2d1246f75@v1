"""
主力合约追踪器测试 (军规级 v4.1).

测试覆盖:
- M20: 主力合约追踪 - 基于成交量+持仓量自动识别

场景覆盖:
- MAIN.CONTRACT.DETECT: 主力合约检测
- MAIN.CONTRACT.SWITCH: 合约切换事件
- MAIN.CONTRACT.HISTORY: 切换历史记录
"""

from __future__ import annotations

import pytest

from src.market.main_contract_tracker import (
    ContractMetrics,
    ContractSwitchEvent,
    MainContractTracker,
    ProductState,
    SwitchReason,
    create_tracker,
    extract_product,
    is_main_month,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tracker() -> MainContractTracker:
    """创建默认追踪器."""
    return MainContractTracker()


@pytest.fixture
def tracker_low_threshold() -> MainContractTracker:
    """创建低阈值追踪器 (更容易切换)."""
    return MainContractTracker(
        volume_threshold=1.2,
        oi_threshold=1.1,
        combined_threshold=1.1,
    )


# ============================================================
# 基础功能测试
# ============================================================


class TestMainContractTrackerInit:
    """追踪器初始化测试."""

    def test_default_init(self) -> None:
        """测试默认初始化."""
        tracker = MainContractTracker()
        assert tracker.volume_threshold == 1.5
        assert tracker.oi_threshold == 1.2
        assert tracker.update_count == 0
        assert tracker.switch_count == 0

    def test_custom_thresholds(self) -> None:
        """测试自定义阈值."""
        tracker = MainContractTracker(
            volume_threshold=2.0,
            oi_threshold=1.5,
            combined_threshold=1.5,
        )
        assert tracker.volume_threshold == 2.0
        assert tracker.oi_threshold == 1.5

    def test_custom_weights(self) -> None:
        """测试自定义权重."""
        tracker = MainContractTracker(
            volume_weight=0.7,
            oi_weight=0.3,
        )
        stats = tracker.get_statistics()
        assert stats["volume_threshold"] == 1.5


# ============================================================
# 更新测试
# ============================================================


class TestUpdate:
    """更新测试."""

    def test_first_update_sets_main(self, tracker: MainContractTracker) -> None:
        """测试首次更新设置主力合约."""
        event = tracker.update("rb2501", "rb", 100000, 50000)

        assert event is not None
        assert event.reason == SwitchReason.INITIAL
        assert event.new_contract == "rb2501"
        assert event.old_contract is None
        assert tracker.get_main_contract("rb") == "rb2501"

    def test_update_increments_count(self, tracker: MainContractTracker) -> None:
        """测试更新计数递增."""
        assert tracker.update_count == 0

        tracker.update("rb2501", "rb", 100000, 50000)
        assert tracker.update_count == 1

        tracker.update("rb2505", "rb", 80000, 40000)
        assert tracker.update_count == 2

    def test_update_same_contract(self, tracker: MainContractTracker) -> None:
        """测试更新同一合约不切换."""
        tracker.update("rb2501", "rb", 100000, 50000)
        event = tracker.update("rb2501", "rb", 120000, 60000)

        assert event is None
        assert tracker.switch_count == 1  # 只有初始设置

    def test_update_smaller_contract_no_switch(self, tracker: MainContractTracker) -> None:
        """测试更新较小合约不切换."""
        tracker.update("rb2501", "rb", 100000, 50000)
        event = tracker.update("rb2505", "rb", 80000, 40000)

        assert event is None
        assert tracker.get_main_contract("rb") == "rb2501"


# ============================================================
# 切换测试
# ============================================================


class TestSwitch:
    """切换测试."""

    def test_volume_dominance_switch(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试成交量主导切换."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        event = tracker_low_threshold.update("rb2505", "rb", 150000, 50000)

        assert event is not None
        assert event.reason == SwitchReason.VOLUME_DOMINANCE
        assert event.old_contract == "rb2501"
        assert event.new_contract == "rb2505"

    def test_oi_dominance_switch(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试持仓量主导切换."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        event = tracker_low_threshold.update("rb2505", "rb", 100000, 60000)

        assert event is not None
        assert event.reason == SwitchReason.OI_DOMINANCE
        assert event.new_contract == "rb2505"

    def test_combined_dominance_switch(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试综合指标切换."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        # 成交量和持仓量都略高,但单独不够阈值
        event = tracker_low_threshold.update("rb2505", "rb", 115000, 55000)

        assert event is not None
        assert event.reason == SwitchReason.COMBINED_DOMINANCE

    def test_switch_increments_count(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试切换计数递增."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        assert tracker_low_threshold.switch_count == 1  # 初始设置

        tracker_low_threshold.update("rb2505", "rb", 150000, 60000)
        assert tracker_low_threshold.switch_count == 2

    def test_manual_switch(self, tracker: MainContractTracker) -> None:
        """测试手动切换."""
        tracker.update("rb2501", "rb", 100000, 50000)
        event = tracker.set_main_contract("rb", "rb2505")

        assert event.reason == SwitchReason.MANUAL
        assert event.new_contract == "rb2505"
        assert tracker.get_main_contract("rb") == "rb2505"


# ============================================================
# 查询测试
# ============================================================


class TestQuery:
    """查询测试."""

    def test_get_main_contract(self, tracker: MainContractTracker) -> None:
        """测试获取主力合约."""
        assert tracker.get_main_contract("rb") is None

        tracker.update("rb2501", "rb", 100000, 50000)
        assert tracker.get_main_contract("rb") == "rb2501"

    def test_is_main_contract(self, tracker: MainContractTracker) -> None:
        """测试检查是否为主力合约."""
        tracker.update("rb2501", "rb", 100000, 50000)
        tracker.update("rb2505", "rb", 80000, 40000)

        assert tracker.is_main_contract("rb2501", "rb") is True
        assert tracker.is_main_contract("rb2505", "rb") is False

    def test_get_all_contracts(self, tracker: MainContractTracker) -> None:
        """测试获取所有合约."""
        tracker.update("rb2501", "rb", 100000, 50000)
        tracker.update("rb2505", "rb", 80000, 40000)

        contracts = tracker.get_all_contracts("rb")
        assert len(contracts) == 2
        assert "rb2501" in contracts
        assert "rb2505" in contracts

    def test_get_contract_metrics(self, tracker: MainContractTracker) -> None:
        """测试获取合约指标."""
        tracker.update("rb2501", "rb", 100000, 50000)

        metrics = tracker.get_contract_metrics("rb2501", "rb")
        assert metrics is not None
        assert metrics.volume == 100000
        assert metrics.open_interest == 50000

    def test_get_nonexistent_contract_metrics(self, tracker: MainContractTracker) -> None:
        """测试获取不存在合约指标."""
        metrics = tracker.get_contract_metrics("rb9999", "rb")
        assert metrics is None


# ============================================================
# 历史测试
# ============================================================


class TestHistory:
    """历史测试."""

    def test_switch_history_empty(self, tracker: MainContractTracker) -> None:
        """测试空历史."""
        history = tracker.get_switch_history("rb")
        assert len(history) == 0

    def test_switch_history_records(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试历史记录."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        tracker_low_threshold.update("rb2505", "rb", 150000, 60000)

        history = tracker_low_threshold.get_switch_history("rb")
        assert len(history) == 2

        # 第一条是初始设置
        assert history[0].reason == SwitchReason.INITIAL
        assert history[0].new_contract == "rb2501"

        # 第二条是切换
        assert history[1].old_contract == "rb2501"
        assert history[1].new_contract == "rb2505"


# ============================================================
# 回调测试
# ============================================================


class TestCallback:
    """回调测试."""

    def test_register_callback(self, tracker: MainContractTracker) -> None:
        """测试注册回调."""
        events: list[ContractSwitchEvent] = []

        def callback(event: ContractSwitchEvent) -> None:
            events.append(event)

        tracker.register_callback(callback)
        tracker.update("rb2501", "rb", 100000, 50000)

        assert len(events) == 1
        assert events[0].new_contract == "rb2501"

    def test_unregister_callback(self, tracker: MainContractTracker) -> None:
        """测试注销回调."""
        events: list[ContractSwitchEvent] = []

        def callback(event: ContractSwitchEvent) -> None:
            events.append(event)

        tracker.register_callback(callback)
        tracker.update("rb2501", "rb", 100000, 50000)
        assert len(events) == 1

        tracker.unregister_callback(callback)
        tracker.set_main_contract("rb", "rb2505")
        assert len(events) == 1  # 不再增加

    def test_callback_error_ignored(self, tracker: MainContractTracker) -> None:
        """测试回调错误被忽略."""

        def bad_callback(event: ContractSwitchEvent) -> None:
            raise ValueError("Test error")

        tracker.register_callback(bad_callback)
        # 不应该抛出异常
        tracker.update("rb2501", "rb", 100000, 50000)
        assert tracker.get_main_contract("rb") == "rb2501"


# ============================================================
# 统计测试
# ============================================================


class TestStatistics:
    """统计测试."""

    def test_get_statistics(self, tracker: MainContractTracker) -> None:
        """测试获取统计信息."""
        tracker.update("rb2501", "rb", 100000, 50000)
        tracker.update("hc2501", "hc", 80000, 40000)

        stats = tracker.get_statistics()
        assert stats["update_count"] == 2
        assert stats["switch_count"] == 2  # 两个初始设置
        assert stats["product_count"] == 2
        assert "rb" in stats["products"]
        assert "hc" in stats["products"]

    def test_reset(self, tracker: MainContractTracker) -> None:
        """测试重置."""
        tracker.update("rb2501", "rb", 100000, 50000)
        tracker.reset()

        assert tracker.update_count == 0
        assert tracker.switch_count == 0
        assert tracker.get_main_contract("rb") is None


# ============================================================
# ContractSwitchEvent 测试
# ============================================================


class TestContractSwitchEvent:
    """切换事件测试."""

    def test_event_frozen(self) -> None:
        """测试事件不可变."""
        event = ContractSwitchEvent(
            product="rb",
            old_contract="rb2501",
            new_contract="rb2505",
            reason=SwitchReason.VOLUME_DOMINANCE,
        )

        with pytest.raises(AttributeError):
            event.new_contract = "rb2509"  # type: ignore[misc]

    def test_to_audit_dict(self) -> None:
        """测试转换为审计字典."""
        event = ContractSwitchEvent(
            product="rb",
            old_contract="rb2501",
            new_contract="rb2505",
            reason=SwitchReason.VOLUME_DOMINANCE,
            volume_ratio=1.6,
            oi_ratio=1.3,
            timestamp="2025-01-15T10:00:00",
        )

        audit = event.to_audit_dict()
        assert audit["event_type"] == "CONTRACT_SWITCH"
        assert audit["product"] == "rb"
        assert audit["old_contract"] == "rb2501"
        assert audit["new_contract"] == "rb2505"
        assert audit["reason"] == "VOLUME_DOMINANCE"
        assert audit["volume_ratio"] == 1.6
        assert audit["oi_ratio"] == 1.3


# ============================================================
# ContractMetrics 测试
# ============================================================


class TestContractMetrics:
    """合约指标测试."""

    def test_create_metrics(self) -> None:
        """测试创建指标."""
        metrics = ContractMetrics(
            symbol="rb2501",
            volume=100000,
            open_interest=50000,
        )

        assert metrics.symbol == "rb2501"
        assert metrics.volume == 100000
        assert metrics.open_interest == 50000


# ============================================================
# ProductState 测试
# ============================================================


class TestProductState:
    """品种状态测试."""

    def test_create_state(self) -> None:
        """测试创建状态."""
        state = ProductState(product="rb")

        assert state.product == "rb"
        assert state.main_contract is None
        assert len(state.contracts) == 0
        assert len(state.switch_history) == 0


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_tracker(self) -> None:
        """测试创建追踪器."""
        tracker = create_tracker(volume_threshold=2.0)
        assert tracker.volume_threshold == 2.0

    def test_extract_product(self) -> None:
        """测试提取品种代码."""
        assert extract_product("rb2501") == "rb"
        assert extract_product("IF2501") == "IF"
        assert extract_product("hc2505") == "hc"
        assert extract_product("au2506") == "au"

    def test_extract_product_no_digits(self) -> None:
        """测试无数字的合约代码."""
        assert extract_product("rb") == "rb"

    def test_is_main_month(self) -> None:
        """测试主力月份判断."""
        assert is_main_month("rb2501") is True
        assert is_main_month("rb2505") is True
        assert is_main_month("rb2509") is True
        assert is_main_month("rb2510") is True
        assert is_main_month("rb2503") is False
        assert is_main_month("rb2507") is False


# ============================================================
# 多品种测试
# ============================================================


class TestMultipleProducts:
    """多品种测试."""

    def test_multiple_products_independent(self, tracker: MainContractTracker) -> None:
        """测试多品种独立追踪."""
        tracker.update("rb2501", "rb", 100000, 50000)
        tracker.update("hc2501", "hc", 80000, 40000)
        tracker.update("i2501", "i", 60000, 30000)

        assert tracker.get_main_contract("rb") == "rb2501"
        assert tracker.get_main_contract("hc") == "hc2501"
        assert tracker.get_main_contract("i") == "i2501"

    def test_switch_one_product_not_affect_other(
        self, tracker_low_threshold: MainContractTracker
    ) -> None:
        """测试一个品种切换不影响其他品种."""
        tracker_low_threshold.update("rb2501", "rb", 100000, 50000)
        tracker_low_threshold.update("hc2501", "hc", 80000, 40000)

        # rb 切换
        tracker_low_threshold.update("rb2505", "rb", 150000, 60000)

        assert tracker_low_threshold.get_main_contract("rb") == "rb2505"
        assert tracker_low_threshold.get_main_contract("hc") == "hc2501"


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_zero_volume(self, tracker: MainContractTracker) -> None:
        """测试零成交量."""
        tracker.update("rb2501", "rb", 0, 50000)
        assert tracker.get_main_contract("rb") == "rb2501"

    def test_zero_oi(self, tracker: MainContractTracker) -> None:
        """测试零持仓量."""
        tracker.update("rb2501", "rb", 100000, 0)
        assert tracker.get_main_contract("rb") == "rb2501"

    def test_very_large_values(self, tracker: MainContractTracker) -> None:
        """测试极大值."""
        tracker.update("rb2501", "rb", 100000000, 50000000)
        assert tracker.get_main_contract("rb") == "rb2501"

    def test_nonexistent_product(self, tracker: MainContractTracker) -> None:
        """测试不存在的品种."""
        assert tracker.get_main_contract("xxx") is None
        assert tracker.get_all_contracts("xxx") == []
        assert tracker.get_switch_history("xxx") == []


# ============================================================
# 时间戳测试
# ============================================================


class TestTimestamp:
    """时间戳测试."""

    def test_event_has_timestamp(self, tracker: MainContractTracker) -> None:
        """测试事件有时间戳."""
        event = tracker.update("rb2501", "rb", 100000, 50000)

        assert event is not None
        assert event.timestamp != ""
        assert "T" in event.timestamp  # ISO格式

    def test_metrics_has_timestamp(self, tracker: MainContractTracker) -> None:
        """测试指标有时间戳."""
        tracker.update("rb2501", "rb", 100000, 50000)
        metrics = tracker.get_contract_metrics("rb2501", "rb")

        assert metrics is not None
        assert metrics.last_update != ""
