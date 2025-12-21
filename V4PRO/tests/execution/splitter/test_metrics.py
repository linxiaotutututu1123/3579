"""
执行质量指标测试.

V4PRO Platform Component - Order Splitting Metrics Tests
军规覆盖: M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- SPLITTER.METRICS.SLIPPAGE: 滑点计算与监控
- SPLITTER.METRICS.FILL_RATE: 成交率统计
- SPLITTER.METRICS.LATENCY: 执行延迟监控
"""

from __future__ import annotations

import time

import pytest

from src.execution.splitter.metrics import (
    DEFAULT_TARGETS,
    ExecutionMetrics,
    ExecutionTargets,
    FillRateMetric,
    LatencyMetric,
    MetricStatus,
    MetricsCollector,
    SlippageMetric,
)


class TestSlippageMetric:
    """SPLITTER.METRICS.SLIPPAGE - 滑点指标测试."""

    def test_slippage_buy_positive(self) -> None:
        """测试买入正滑点(多付)."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.1,
            qty=100,
            side="BUY",
        )
        # 多付0.1%, 滑点为正
        assert metric.slippage_pct == pytest.approx(0.001, rel=0.01)
        assert metric.slippage_cost == pytest.approx(10.0, rel=0.01)

    def test_slippage_buy_negative(self) -> None:
        """测试买入负滑点(少付)."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=99.9,
            qty=100,
            side="BUY",
        )
        # 少付0.1%, 滑点为负
        assert metric.slippage_pct == pytest.approx(-0.001, rel=0.01)
        assert metric.slippage_cost == pytest.approx(10.0, rel=0.01)

    def test_slippage_sell_positive(self) -> None:
        """测试卖出正滑点(多收)."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.1,
            qty=100,
            side="SELL",
        )
        # 多收0.1%, 对卖方有利, 滑点为负(实际是好的)
        assert metric.slippage_pct == pytest.approx(-0.001, rel=0.01)

    def test_slippage_sell_negative(self) -> None:
        """测试卖出负滑点(少收)."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=99.9,
            qty=100,
            side="SELL",
        )
        # 少收0.1%, 对卖方不利, 滑点为正
        assert metric.slippage_pct == pytest.approx(0.001, rel=0.01)

    def test_slippage_zero(self) -> None:
        """测试零滑点."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.0,
            qty=100,
            side="BUY",
        )
        assert metric.slippage_pct == 0.0
        assert metric.slippage_cost == 0.0

    def test_slippage_zero_target_price(self) -> None:
        """测试目标价格为零."""
        metric = SlippageMetric(
            target_price=0.0,
            executed_price=100.0,
            qty=100,
            side="BUY",
        )
        assert metric.slippage_pct == 0.0
        assert metric.slippage_cost == 0.0

    def test_slippage_status_excellent(self) -> None:
        """测试滑点状态-优秀."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.04,  # 0.04% < 0.05% (目标的一半)
            qty=100,
            side="BUY",
        )
        assert metric.get_status() == MetricStatus.EXCELLENT

    def test_slippage_status_good(self) -> None:
        """测试滑点状态-良好."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.08,  # 0.08% < 0.1% (目标)
            qty=100,
            side="BUY",
        )
        assert metric.get_status() == MetricStatus.GOOD

    def test_slippage_status_warning(self) -> None:
        """测试滑点状态-警告."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.15,  # 0.15% < 0.2% (目标的2倍)
            qty=100,
            side="BUY",
        )
        assert metric.get_status() == MetricStatus.WARNING

    def test_slippage_status_critical(self) -> None:
        """测试滑点状态-危险."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.25,  # 0.25% > 0.2% (目标的2倍)
            qty=100,
            side="BUY",
        )
        assert metric.get_status() == MetricStatus.CRITICAL

    def test_slippage_to_dict(self) -> None:
        """测试滑点指标转字典."""
        metric = SlippageMetric(
            target_price=100.0,
            executed_price=100.1,
            qty=100,
            side="BUY",
        )
        d = metric.to_dict()
        assert "target_price" in d
        assert "executed_price" in d
        assert "slippage_pct" in d
        assert "slippage_cost" in d
        assert "status" in d


class TestFillRateMetric:
    """SPLITTER.METRICS.FILL_RATE - 成交率指标测试."""

    def test_fill_rate_full(self) -> None:
        """测试100%成交率."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=100,
        )
        assert metric.fill_rate == 1.0
        assert metric.remaining_qty == 0

    def test_fill_rate_partial(self) -> None:
        """测试部分成交率."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=80,
        )
        assert metric.fill_rate == 0.8
        assert metric.remaining_qty == 20

    def test_fill_rate_zero(self) -> None:
        """测试0%成交率."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=0,
        )
        assert metric.fill_rate == 0.0
        assert metric.remaining_qty == 100

    def test_fill_rate_zero_target(self) -> None:
        """测试目标数量为零."""
        metric = FillRateMetric(
            target_qty=0,
            filled_qty=0,
        )
        assert metric.fill_rate == 0.0

    def test_fill_rate_status_excellent(self) -> None:
        """测试成交率状态-优秀."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=100,
        )
        assert metric.get_status() == MetricStatus.EXCELLENT

    def test_fill_rate_status_good(self) -> None:
        """测试成交率状态-良好."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=96,  # 96% >= 95%
        )
        assert metric.get_status() == MetricStatus.GOOD

    def test_fill_rate_status_warning(self) -> None:
        """测试成交率状态-警告."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=80,  # 80% >= 76% (95%*0.8)
        )
        assert metric.get_status() == MetricStatus.WARNING

    def test_fill_rate_status_critical(self) -> None:
        """测试成交率状态-危险."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=70,  # 70% < 76%
        )
        assert metric.get_status() == MetricStatus.CRITICAL

    def test_fill_rate_to_dict(self) -> None:
        """测试成交率指标转字典."""
        metric = FillRateMetric(
            target_qty=100,
            filled_qty=80,
            pending_qty=10,
            cancelled_qty=10,
        )
        d = metric.to_dict()
        assert d["target_qty"] == 100
        assert d["filled_qty"] == 80
        assert d["pending_qty"] == 10
        assert d["cancelled_qty"] == 10
        assert d["remaining_qty"] == 20
        assert d["fill_rate"] == 0.8


class TestLatencyMetric:
    """SPLITTER.METRICS.LATENCY - 延迟指标测试."""

    def test_latency_ack(self) -> None:
        """测试确认延迟."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1050.0,
        )
        assert metric.ack_latency_ms == 50.0
        assert metric.fill_latency_ms == 0.0

    def test_latency_fill(self) -> None:
        """测试成交延迟."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            fill_time_ms=1100.0,
        )
        assert metric.ack_latency_ms == 0.0
        assert metric.fill_latency_ms == 100.0

    def test_latency_both(self) -> None:
        """测试确认和成交延迟."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1050.0,
            fill_time_ms=1100.0,
        )
        assert metric.ack_latency_ms == 50.0
        assert metric.fill_latency_ms == 100.0

    def test_latency_status_excellent(self) -> None:
        """测试延迟状态-优秀."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1040.0,  # 40ms < 50ms (目标的一半)
        )
        assert metric.get_status() == MetricStatus.EXCELLENT

    def test_latency_status_good(self) -> None:
        """测试延迟状态-良好."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1080.0,  # 80ms < 100ms (目标)
        )
        assert metric.get_status() == MetricStatus.GOOD

    def test_latency_status_warning(self) -> None:
        """测试延迟状态-警告."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1150.0,  # 150ms < 200ms (目标的2倍)
        )
        assert metric.get_status() == MetricStatus.WARNING

    def test_latency_status_critical(self) -> None:
        """测试延迟状态-危险."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1250.0,  # 250ms > 200ms (目标的2倍)
        )
        assert metric.get_status() == MetricStatus.CRITICAL

    def test_latency_to_dict(self) -> None:
        """测试延迟指标转字典."""
        metric = LatencyMetric(
            submit_time_ms=1000.0,
            ack_time_ms=1050.0,
            fill_time_ms=1100.0,
        )
        d = metric.to_dict()
        assert d["submit_time_ms"] == 1000.0
        assert d["ack_time_ms"] == 1050.0
        assert d["fill_time_ms"] == 1100.0
        assert d["ack_latency_ms"] == 50.0
        assert d["fill_latency_ms"] == 100.0


class TestExecutionMetrics:
    """执行综合指标测试."""

    def test_metrics_init(self) -> None:
        """测试指标初始化."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        assert metrics.plan_id == "test_plan"
        assert metrics.algo == "TWAP"
        assert metrics.slippage_metrics == []
        assert metrics.fill_rate is None
        assert metrics.latency_metrics == []

    def test_add_slippage(self) -> None:
        """测试添加滑点记录."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        slip = metrics.add_slippage(
            target_price=100.0,
            executed_price=100.1,
            qty=100,
            side="BUY",
        )
        assert len(metrics.slippage_metrics) == 1
        assert slip.slippage_pct == pytest.approx(0.001, rel=0.01)

    def test_add_latency(self) -> None:
        """测试添加延迟记录."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        lat = metrics.add_latency(
            submit_time_ms=1000.0,
            ack_time_ms=1050.0,
        )
        assert len(metrics.latency_metrics) == 1
        assert lat.ack_latency_ms == 50.0

    def test_update_fill_rate(self) -> None:
        """测试更新成交率."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        fr = metrics.update_fill_rate(
            target_qty=100,
            filled_qty=80,
        )
        assert metrics.fill_rate is not None
        assert fr.fill_rate == 0.8

    def test_avg_slippage_pct(self) -> None:
        """测试平均滑点百分比."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.add_slippage(100.0, 100.1, 50, "BUY")  # 0.1滑点成本
        metrics.add_slippage(100.0, 100.2, 50, "BUY")  # 0.2滑点成本
        # 总滑点成本 = 5 + 10 = 15
        # 总价值 = 100*50 + 100*50 = 10000
        # 平均滑点 = 15/10000 = 0.0015
        assert metrics.avg_slippage_pct == pytest.approx(0.0015, rel=0.01)

    def test_total_slippage_cost(self) -> None:
        """测试总滑点成本."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.add_slippage(100.0, 100.1, 100, "BUY")
        metrics.add_slippage(100.0, 100.2, 100, "BUY")
        # 总滑点成本 = 10 + 20 = 30
        assert metrics.total_slippage_cost == pytest.approx(30.0, rel=0.01)

    def test_avg_latency_ms(self) -> None:
        """测试平均延迟."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.add_latency(1000.0, 1050.0)  # 50ms
        metrics.add_latency(1000.0, 1100.0)  # 100ms
        assert metrics.avg_latency_ms == pytest.approx(75.0, rel=0.01)

    def test_max_latency_ms(self) -> None:
        """测试最大延迟."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.add_latency(1000.0, 1050.0)  # 50ms
        metrics.add_latency(1000.0, 1100.0)  # 100ms
        assert metrics.max_latency_ms == 100.0

    def test_execution_duration(self) -> None:
        """测试执行时长."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.start_time = 1000.0
        metrics.end_time = 1100.0
        assert metrics.execution_duration == 100.0

    def test_get_overall_status(self) -> None:
        """测试综合状态."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        # 无指标时返回GOOD
        assert metrics.get_overall_status() == MetricStatus.GOOD

        # 添加良好指标
        metrics.add_slippage(100.0, 100.05, 100, "BUY")  # 0.05% - GOOD
        metrics.update_fill_rate(100, 100)  # 100% - EXCELLENT
        metrics.add_latency(1000.0, 1050.0)  # 50ms - EXCELLENT
        # 综合取最差: GOOD
        assert metrics.get_overall_status() == MetricStatus.GOOD

    def test_finalize(self) -> None:
        """测试结束指标收集."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        assert metrics.end_time is None
        metrics.finalize()
        assert metrics.end_time is not None

    def test_to_dict(self) -> None:
        """测试转字典."""
        metrics = ExecutionMetrics(plan_id="test_plan", algo="TWAP")
        metrics.add_slippage(100.0, 100.1, 100, "BUY")
        metrics.update_fill_rate(100, 80)
        metrics.add_latency(1000.0, 1050.0)
        d = metrics.to_dict()
        assert d["plan_id"] == "test_plan"
        assert d["algo"] == "TWAP"
        assert "slippage" in d
        assert "fill_rate" in d
        assert "latency" in d
        assert "overall_status" in d


class TestMetricsCollector:
    """指标收集器测试."""

    def test_collector_init(self) -> None:
        """测试收集器初始化."""
        collector = MetricsCollector()
        assert collector.targets == DEFAULT_TARGETS
        assert len(collector.get_all_metrics()) == 0

    def test_collector_custom_targets(self) -> None:
        """测试自定义目标."""
        targets = ExecutionTargets(
            slippage_pct=0.002,
            fill_rate_pct=0.90,
            latency_ms=200.0,
        )
        collector = MetricsCollector(targets)
        assert collector.targets == targets

    def test_create_metrics(self) -> None:
        """测试创建指标."""
        collector = MetricsCollector()
        metrics = collector.create_metrics("plan_1", "TWAP")
        assert metrics.plan_id == "plan_1"
        assert metrics.algo == "TWAP"
        assert collector.get_metrics("plan_1") is metrics

    def test_get_metrics_not_found(self) -> None:
        """测试获取不存在的指标."""
        collector = MetricsCollector()
        assert collector.get_metrics("nonexistent") is None

    def test_remove_metrics(self) -> None:
        """测试移除指标."""
        collector = MetricsCollector()
        collector.create_metrics("plan_1", "TWAP")
        assert collector.remove_metrics("plan_1") is True
        assert collector.get_metrics("plan_1") is None
        assert collector.remove_metrics("plan_1") is False

    def test_get_all_metrics(self) -> None:
        """测试获取所有指标."""
        collector = MetricsCollector()
        collector.create_metrics("plan_1", "TWAP")
        collector.create_metrics("plan_2", "VWAP")
        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 2

    def test_get_summary(self) -> None:
        """测试获取汇总."""
        collector = MetricsCollector()
        m1 = collector.create_metrics("plan_1", "TWAP")
        m1.add_slippage(100.0, 100.05, 100, "BUY")
        m1.update_fill_rate(100, 100)
        m1.add_latency(1000.0, 1050.0)

        m2 = collector.create_metrics("plan_2", "VWAP")
        m2.add_slippage(100.0, 100.1, 100, "BUY")
        m2.update_fill_rate(100, 95)
        m2.add_latency(1000.0, 1080.0)

        summary = collector.get_summary()
        assert summary["total_plans"] == 2
        assert "avg_slippage_pct" in summary
        assert "avg_fill_rate" in summary
        assert "avg_latency_ms" in summary
        assert "status_distribution" in summary

    def test_get_summary_empty(self) -> None:
        """测试空收集器汇总."""
        collector = MetricsCollector()
        summary = collector.get_summary()
        assert summary["total_plans"] == 0
        assert summary["avg_slippage_pct"] == 0.0
        assert summary["avg_fill_rate"] == 0.0
        assert summary["avg_latency_ms"] == 0.0

    def test_clear(self) -> None:
        """测试清空指标."""
        collector = MetricsCollector()
        collector.create_metrics("plan_1", "TWAP")
        collector.create_metrics("plan_2", "VWAP")
        collector.clear()
        assert len(collector.get_all_metrics()) == 0


class TestExecutionTargets:
    """执行质量目标测试."""

    def test_default_targets(self) -> None:
        """测试默认目标值."""
        targets = DEFAULT_TARGETS
        assert targets.slippage_pct == 0.001  # 0.1%
        assert targets.fill_rate_pct == 0.95  # 95%
        assert targets.latency_ms == 100.0  # 100ms

    def test_custom_targets(self) -> None:
        """测试自定义目标值."""
        targets = ExecutionTargets(
            slippage_pct=0.002,
            fill_rate_pct=0.90,
            latency_ms=200.0,
        )
        assert targets.slippage_pct == 0.002
        assert targets.fill_rate_pct == 0.90
        assert targets.latency_ms == 200.0

    def test_targets_immutable(self) -> None:
        """测试目标值不可变."""
        targets = ExecutionTargets()
        with pytest.raises(AttributeError):
            targets.slippage_pct = 0.002  # type: ignore
