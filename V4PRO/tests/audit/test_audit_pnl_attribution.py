"""
PnLAttribution 测试.

V2 Scenarios:
- AUDIT.PNL.ATTRIBUTION: PnL 归因
"""

from src.audit.pnl_attribution import PnLAttribution, PnLRecord


class TestPnLRecord:
    """PnLRecord 测试类."""

    def test_pnl_record_basic(self) -> None:
        """测试 PnLRecord 基本属性."""
        record = PnLRecord(
            ts=1234567890.123,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=1000.0,
            unrealized_pnl=500.0,
            commission=10.0,
            slippage=5.0,
            net_pnl=985.0,
            position_qty=10,
            avg_cost=5000.0,
        )

        assert record.ts == 1234567890.123
        assert record.run_id == "run-001"
        assert record.exec_id == "exec-001"
        assert record.strategy_id == "simple_ai"
        assert record.symbol == "AO2501"

    def test_pnl_record_event_type(self) -> None:
        """测试事件类型属性."""
        record = PnLRecord(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            symbol="AO2501",
        )

        assert record.event_type == "PNL"

    def test_pnl_record_total_pnl(self) -> None:
        """测试总盈亏计算."""
        record = PnLRecord(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=1000.0,
            unrealized_pnl=500.0,
        )

        assert record.total_pnl == 1500.0

    def test_pnl_record_gross_pnl(self) -> None:
        """测试毛盈亏计算."""
        record = PnLRecord(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            symbol="AO2501",
            net_pnl=985.0,
            commission=10.0,
            slippage=5.0,
        )

        # gross_pnl = net_pnl + commission + slippage
        assert record.gross_pnl == 1000.0

    def test_pnl_record_to_dict(self) -> None:
        """测试转换为字典."""
        record = PnLRecord(
            ts=1234567890.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=1000.0,
            unrealized_pnl=500.0,
            commission=10.0,
            slippage=5.0,
            net_pnl=985.0,
        )

        data = record.to_dict()

        assert data["event_type"] == "PNL"
        assert data["ts"] == 1234567890.0
        assert data["run_id"] == "run-001"
        assert data["strategy_id"] == "simple_ai"
        assert data["total_pnl"] == 1500.0
        assert data["gross_pnl"] == 1000.0


class TestPnLAttribution:
    """PnLAttribution 测试类."""

    def test_audit_pnl_attribution_basic(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 基本 PnL 归因."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        record = attribution.update_realized(
            ts=1.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=1000.0,
            commission=10.0,
            slippage=5.0,
        )

        assert record.realized_pnl == 1000.0
        assert record.commission == 10.0
        assert record.slippage == 5.0
        assert record.net_pnl == 985.0  # 1000 - 10 - 5

    def test_audit_pnl_attribution_by_strategy(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 按策略归因."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        # 策略 1 的盈亏
        attribution.update_realized(
            ts=1.0,
            strategy_id="strategy_1",
            symbol="AO2501",
            realized_pnl=1000.0,
        )
        attribution.update_realized(
            ts=2.0,
            strategy_id="strategy_1",
            symbol="SA2501",
            realized_pnl=500.0,
        )

        # 策略 2 的盈亏
        attribution.update_realized(
            ts=3.0,
            strategy_id="strategy_2",
            symbol="AO2501",
            realized_pnl=200.0,
        )

        # 按策略获取
        strategy_1_records = attribution.get_by_strategy("strategy_1")
        strategy_2_records = attribution.get_by_strategy("strategy_2")

        assert len(strategy_1_records) == 2
        assert len(strategy_2_records) == 1

        # 策略 PnL
        assert attribution.get_strategy_pnl("strategy_1") == 1500.0
        assert attribution.get_strategy_pnl("strategy_2") == 200.0

    def test_audit_pnl_attribution_by_symbol(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 按品种归因."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        attribution.update_realized(
            ts=1.0,
            strategy_id="strategy_1",
            symbol="AO2501",
            realized_pnl=1000.0,
        )
        attribution.update_realized(
            ts=2.0,
            strategy_id="strategy_2",
            symbol="AO2501",
            realized_pnl=500.0,
        )
        attribution.update_realized(
            ts=3.0,
            strategy_id="strategy_1",
            symbol="SA2501",
            realized_pnl=200.0,
        )

        ao_records = attribution.get_by_symbol("AO2501")
        sa_records = attribution.get_by_symbol("SA2501")

        assert len(ao_records) == 2
        assert len(sa_records) == 1

    def test_audit_pnl_attribution_update_unrealized(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 更新未实现盈亏."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        record = attribution.update_unrealized(
            ts=1.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            unrealized_pnl=500.0,
            position_qty=10,
            avg_cost=5000.0,
        )

        assert record.unrealized_pnl == 500.0
        assert record.position_qty == 10
        assert record.avg_cost == 5000.0

    def test_audit_pnl_attribution_combined(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 同时更新已实现和未实现."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        # 更新已实现
        attribution.update_realized(
            ts=1.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=1000.0,
            commission=10.0,
        )

        # 更新未实现
        attribution.update_unrealized(
            ts=2.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            unrealized_pnl=500.0,
            position_qty=10,
            avg_cost=5000.0,
        )

        record = attribution.get_record("simple_ai", "AO2501")
        assert record is not None
        assert record.realized_pnl == 1000.0
        assert record.unrealized_pnl == 500.0
        assert record.total_pnl == 1500.0

    def test_audit_pnl_attribution_cumulative(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 累计已实现盈亏."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        # 多次平仓累计
        attribution.update_realized(
            ts=1.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=100.0,
            commission=1.0,
        )
        attribution.update_realized(
            ts=2.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=200.0,
            commission=2.0,
        )
        attribution.update_realized(
            ts=3.0,
            strategy_id="simple_ai",
            symbol="AO2501",
            realized_pnl=300.0,
            commission=3.0,
        )

        record = attribution.get_record("simple_ai", "AO2501")
        assert record is not None
        assert record.realized_pnl == 600.0  # 100 + 200 + 300
        assert record.commission == 6.0  # 1 + 2 + 3
        assert record.net_pnl == 594.0  # 600 - 6

    def test_audit_pnl_attribution_get_total_pnl(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 获取总 PnL."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        attribution.update_realized(
            ts=1.0,
            strategy_id="strategy_1",
            symbol="AO2501",
            realized_pnl=1000.0,
        )
        attribution.update_unrealized(
            ts=2.0,
            strategy_id="strategy_1",
            symbol="AO2501",
            unrealized_pnl=500.0,
            position_qty=10,
            avg_cost=5000.0,
        )
        attribution.update_realized(
            ts=3.0,
            strategy_id="strategy_2",
            symbol="SA2501",
            realized_pnl=200.0,
        )

        total = attribution.get_total_pnl()
        assert total == 1700.0  # 1000 + 500 + 200

    def test_audit_pnl_attribution_get_all_records(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 获取所有记录."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        attribution.update_realized(
            ts=1.0, strategy_id="s1", symbol="AO2501", realized_pnl=100.0
        )
        attribution.update_realized(
            ts=2.0, strategy_id="s2", symbol="SA2501", realized_pnl=200.0
        )
        attribution.update_realized(
            ts=3.0, strategy_id="s1", symbol="SA2501", realized_pnl=300.0
        )

        records = attribution.get_all_records()
        assert len(records) == 3

    def test_audit_pnl_attribution_clear(self) -> None:
        """AUDIT.PNL.ATTRIBUTION: 清空记录."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        attribution.update_realized(
            ts=1.0, strategy_id="s1", symbol="AO2501", realized_pnl=100.0
        )

        assert len(attribution.get_all_records()) == 1

        attribution.clear()

        assert len(attribution.get_all_records()) == 0

    def test_audit_pnl_attribution_properties(self) -> None:
        """测试归因器属性."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        assert attribution.run_id == "run-001"
        assert attribution.exec_id == "exec-001"

    def test_audit_pnl_attribution_get_record_not_found(self) -> None:
        """测试获取不存在的记录."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        record = attribution.get_record("nonexistent", "AO2501")
        assert record is None

    def test_audit_pnl_attribution_timestamp_update(self) -> None:
        """测试时间戳更新."""
        attribution = PnLAttribution(run_id="run-001", exec_id="exec-001")

        attribution.update_realized(
            ts=1.0, strategy_id="s1", symbol="AO2501", realized_pnl=100.0
        )
        attribution.update_realized(
            ts=5.0, strategy_id="s1", symbol="AO2501", realized_pnl=200.0
        )

        record = attribution.get_record("s1", "AO2501")
        assert record is not None
        assert record.ts == 5.0  # 更新为最新时间戳
