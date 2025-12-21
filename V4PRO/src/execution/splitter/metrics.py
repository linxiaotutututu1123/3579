"""
执行质量指标模块.

V4PRO Platform Component - Order Splitting Metrics
军规覆盖: M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- SPLITTER.METRICS.SLIPPAGE: 滑点计算与监控
- SPLITTER.METRICS.FILL_RATE: 成交率统计
- SPLITTER.METRICS.LATENCY: 执行延迟监控

执行质量目标 (D7-P1):
- 滑点: <=0.1%
- 成交率: >=95%
- 执行延迟: <=100ms
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MetricStatus(str, Enum):
    """指标状态枚举.

    Attributes:
        EXCELLENT: 优秀 (超越目标)
        GOOD: 良好 (达到目标)
        WARNING: 警告 (接近阈值)
        CRITICAL: 危险 (超出阈值)
    """

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ExecutionTargets:
    """执行质量目标.

    V4PRO D7-P1 设计规范定义的目标值。

    Attributes:
        slippage_pct: 滑点目标 (<=0.1%)
        fill_rate_pct: 成交率目标 (>=95%)
        latency_ms: 执行延迟目标 (<=100ms)
    """

    slippage_pct: float = 0.001  # <=0.1%
    fill_rate_pct: float = 0.95  # >=95%
    latency_ms: float = 100.0  # <=100ms


# 默认执行质量目标
DEFAULT_TARGETS = ExecutionTargets()


@dataclass
class SlippageMetric:
    """滑点指标.

    V4PRO Scenario: SPLITTER.METRICS.SLIPPAGE

    滑点计算: (实际成交价 - 目标价) / 目标价 * 100%
    - 买入时: 正滑点表示多付
    - 卖出时: 正滑点表示少收

    Attributes:
        target_price: 目标价格
        executed_price: 实际成交价格
        qty: 成交数量
        side: 交易方向 (BUY/SELL)
        slippage_pct: 滑点百分比
        slippage_cost: 滑点成本(绝对值)
    """

    target_price: float
    executed_price: float
    qty: int
    side: str
    slippage_pct: float = field(init=False)
    slippage_cost: float = field(init=False)

    def __post_init__(self) -> None:
        """计算滑点指标."""
        if self.target_price <= 0:
            self.slippage_pct = 0.0
            self.slippage_cost = 0.0
            return

        # 计算价格差异
        price_diff = self.executed_price - self.target_price

        # 买入时正滑点(多付)为负向, 卖出时负滑点(少收)为负向
        if self.side.upper() == "BUY":
            self.slippage_pct = price_diff / self.target_price
        else:
            self.slippage_pct = -price_diff / self.target_price

        # 滑点成本 = 价格差 * 数量
        self.slippage_cost = abs(price_diff) * self.qty

    def get_status(self, targets: ExecutionTargets = DEFAULT_TARGETS) -> MetricStatus:
        """获取滑点状态.

        Args:
            targets: 执行质量目标

        Returns:
            指标状态
        """
        abs_slippage = abs(self.slippage_pct)
        if abs_slippage <= targets.slippage_pct * 0.5:
            return MetricStatus.EXCELLENT
        if abs_slippage <= targets.slippage_pct:
            return MetricStatus.GOOD
        if abs_slippage <= targets.slippage_pct * 2:
            return MetricStatus.WARNING
        return MetricStatus.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "target_price": self.target_price,
            "executed_price": self.executed_price,
            "qty": self.qty,
            "side": self.side,
            "slippage_pct": self.slippage_pct,
            "slippage_cost": self.slippage_cost,
            "status": self.get_status().value,
        }


@dataclass
class FillRateMetric:
    """成交率指标.

    V4PRO Scenario: SPLITTER.METRICS.FILL_RATE

    成交率计算: 已成交数量 / 目标数量 * 100%

    Attributes:
        target_qty: 目标数量
        filled_qty: 已成交数量
        pending_qty: 挂单中数量
        cancelled_qty: 已取消数量
        fill_rate: 成交率 (0.0-1.0)
    """

    target_qty: int
    filled_qty: int = 0
    pending_qty: int = 0
    cancelled_qty: int = 0
    fill_rate: float = field(init=False)

    def __post_init__(self) -> None:
        """计算成交率."""
        if self.target_qty <= 0:
            self.fill_rate = 0.0
            return
        self.fill_rate = self.filled_qty / self.target_qty

    def get_status(self, targets: ExecutionTargets = DEFAULT_TARGETS) -> MetricStatus:
        """获取成交率状态.

        Args:
            targets: 执行质量目标

        Returns:
            指标状态
        """
        if self.fill_rate >= 1.0:
            return MetricStatus.EXCELLENT
        if self.fill_rate >= targets.fill_rate_pct:
            return MetricStatus.GOOD
        if self.fill_rate >= targets.fill_rate_pct * 0.8:
            return MetricStatus.WARNING
        return MetricStatus.CRITICAL

    @property
    def remaining_qty(self) -> int:
        """剩余未成交数量."""
        return max(0, self.target_qty - self.filled_qty)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "target_qty": self.target_qty,
            "filled_qty": self.filled_qty,
            "pending_qty": self.pending_qty,
            "cancelled_qty": self.cancelled_qty,
            "remaining_qty": self.remaining_qty,
            "fill_rate": self.fill_rate,
            "status": self.get_status().value,
        }


@dataclass
class LatencyMetric:
    """执行延迟指标.

    V4PRO Scenario: SPLITTER.METRICS.LATENCY

    延迟计算: 订单提交到确认/成交的时间差

    Attributes:
        submit_time_ms: 订单提交时间(毫秒时间戳)
        ack_time_ms: 订单确认时间(毫秒时间戳)
        fill_time_ms: 订单成交时间(毫秒时间戳)
        ack_latency_ms: 确认延迟(毫秒)
        fill_latency_ms: 成交延迟(毫秒)
    """

    submit_time_ms: float
    ack_time_ms: float | None = None
    fill_time_ms: float | None = None
    ack_latency_ms: float = field(init=False)
    fill_latency_ms: float = field(init=False)

    def __post_init__(self) -> None:
        """计算延迟指标."""
        if self.ack_time_ms is not None:
            self.ack_latency_ms = self.ack_time_ms - self.submit_time_ms
        else:
            self.ack_latency_ms = 0.0

        if self.fill_time_ms is not None:
            self.fill_latency_ms = self.fill_time_ms - self.submit_time_ms
        else:
            self.fill_latency_ms = 0.0

    def get_status(self, targets: ExecutionTargets = DEFAULT_TARGETS) -> MetricStatus:
        """获取延迟状态.

        Args:
            targets: 执行质量目标

        Returns:
            指标状态
        """
        # 使用确认延迟作为主要指标
        latency = self.ack_latency_ms if self.ack_latency_ms > 0 else self.fill_latency_ms
        if latency <= 0:
            return MetricStatus.GOOD

        if latency <= targets.latency_ms * 0.5:
            return MetricStatus.EXCELLENT
        if latency <= targets.latency_ms:
            return MetricStatus.GOOD
        if latency <= targets.latency_ms * 2:
            return MetricStatus.WARNING
        return MetricStatus.CRITICAL

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "submit_time_ms": self.submit_time_ms,
            "ack_time_ms": self.ack_time_ms,
            "fill_time_ms": self.fill_time_ms,
            "ack_latency_ms": self.ack_latency_ms,
            "fill_latency_ms": self.fill_latency_ms,
            "status": self.get_status().value,
        }


@dataclass
class ExecutionMetrics:
    """执行综合指标.

    汇总滑点、成交率、延迟等指标。

    Attributes:
        plan_id: 执行计划ID
        algo: 执行算法
        start_time: 开始时间
        end_time: 结束时间
        slippage_metrics: 滑点指标列表
        fill_rate: 成交率指标
        latency_metrics: 延迟指标列表
    """

    plan_id: str
    algo: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    slippage_metrics: list[SlippageMetric] = field(default_factory=list)
    fill_rate: FillRateMetric | None = None
    latency_metrics: list[LatencyMetric] = field(default_factory=list)

    @property
    def avg_slippage_pct(self) -> float:
        """平均滑点百分比."""
        if not self.slippage_metrics:
            return 0.0
        total_cost = sum(m.slippage_cost for m in self.slippage_metrics)
        total_value = sum(m.target_price * m.qty for m in self.slippage_metrics)
        if total_value <= 0:
            return 0.0
        return total_cost / total_value

    @property
    def total_slippage_cost(self) -> float:
        """总滑点成本."""
        return sum(m.slippage_cost for m in self.slippage_metrics)

    @property
    def avg_latency_ms(self) -> float:
        """平均执行延迟(毫秒)."""
        if not self.latency_metrics:
            return 0.0
        latencies = [
            m.ack_latency_ms
            for m in self.latency_metrics
            if m.ack_latency_ms > 0
        ]
        if not latencies:
            return 0.0
        return sum(latencies) / len(latencies)

    @property
    def max_latency_ms(self) -> float:
        """最大执行延迟(毫秒)."""
        if not self.latency_metrics:
            return 0.0
        latencies = [
            m.ack_latency_ms
            for m in self.latency_metrics
            if m.ack_latency_ms > 0
        ]
        if not latencies:
            return 0.0
        return max(latencies)

    @property
    def execution_duration(self) -> float:
        """执行总时长(秒)."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def add_slippage(
        self,
        target_price: float,
        executed_price: float,
        qty: int,
        side: str,
    ) -> SlippageMetric:
        """添加滑点记录.

        Args:
            target_price: 目标价格
            executed_price: 实际成交价格
            qty: 成交数量
            side: 交易方向

        Returns:
            滑点指标
        """
        metric = SlippageMetric(
            target_price=target_price,
            executed_price=executed_price,
            qty=qty,
            side=side,
        )
        self.slippage_metrics.append(metric)
        return metric

    def add_latency(
        self,
        submit_time_ms: float,
        ack_time_ms: float | None = None,
        fill_time_ms: float | None = None,
    ) -> LatencyMetric:
        """添加延迟记录.

        Args:
            submit_time_ms: 提交时间
            ack_time_ms: 确认时间
            fill_time_ms: 成交时间

        Returns:
            延迟指标
        """
        metric = LatencyMetric(
            submit_time_ms=submit_time_ms,
            ack_time_ms=ack_time_ms,
            fill_time_ms=fill_time_ms,
        )
        self.latency_metrics.append(metric)
        return metric

    def update_fill_rate(
        self,
        target_qty: int,
        filled_qty: int,
        pending_qty: int = 0,
        cancelled_qty: int = 0,
    ) -> FillRateMetric:
        """更新成交率.

        Args:
            target_qty: 目标数量
            filled_qty: 已成交数量
            pending_qty: 挂单中数量
            cancelled_qty: 已取消数量

        Returns:
            成交率指标
        """
        self.fill_rate = FillRateMetric(
            target_qty=target_qty,
            filled_qty=filled_qty,
            pending_qty=pending_qty,
            cancelled_qty=cancelled_qty,
        )
        return self.fill_rate

    def get_overall_status(
        self, targets: ExecutionTargets = DEFAULT_TARGETS
    ) -> MetricStatus:
        """获取综合状态.

        综合评估所有指标,取最差状态。

        Args:
            targets: 执行质量目标

        Returns:
            综合状态
        """
        statuses: list[MetricStatus] = []

        # 滑点状态
        if self.slippage_metrics:
            avg_slippage = abs(self.avg_slippage_pct)
            if avg_slippage <= targets.slippage_pct * 0.5:
                statuses.append(MetricStatus.EXCELLENT)
            elif avg_slippage <= targets.slippage_pct:
                statuses.append(MetricStatus.GOOD)
            elif avg_slippage <= targets.slippage_pct * 2:
                statuses.append(MetricStatus.WARNING)
            else:
                statuses.append(MetricStatus.CRITICAL)

        # 成交率状态
        if self.fill_rate:
            statuses.append(self.fill_rate.get_status(targets))

        # 延迟状态
        if self.latency_metrics:
            avg_latency = self.avg_latency_ms
            if avg_latency <= targets.latency_ms * 0.5:
                statuses.append(MetricStatus.EXCELLENT)
            elif avg_latency <= targets.latency_ms:
                statuses.append(MetricStatus.GOOD)
            elif avg_latency <= targets.latency_ms * 2:
                statuses.append(MetricStatus.WARNING)
            else:
                statuses.append(MetricStatus.CRITICAL)

        if not statuses:
            return MetricStatus.GOOD

        # 返回最差状态
        priority = {
            MetricStatus.EXCELLENT: 0,
            MetricStatus.GOOD: 1,
            MetricStatus.WARNING: 2,
            MetricStatus.CRITICAL: 3,
        }
        return max(statuses, key=lambda s: priority[s])

    def finalize(self) -> None:
        """结束指标收集."""
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典(用于审计日志).

        Returns:
            包含所有指标的字典
        """
        return {
            "plan_id": self.plan_id,
            "algo": self.algo,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "execution_duration": self.execution_duration,
            "slippage": {
                "avg_pct": self.avg_slippage_pct,
                "total_cost": self.total_slippage_cost,
                "details": [m.to_dict() for m in self.slippage_metrics],
            },
            "fill_rate": self.fill_rate.to_dict() if self.fill_rate else None,
            "latency": {
                "avg_ms": self.avg_latency_ms,
                "max_ms": self.max_latency_ms,
                "details": [m.to_dict() for m in self.latency_metrics],
            },
            "overall_status": self.get_overall_status().value,
        }


class MetricsCollector:
    """指标收集器.

    管理多个执行计划的指标收集。

    军规覆盖: M3(完整审计)
    """

    def __init__(self, targets: ExecutionTargets | None = None) -> None:
        """初始化指标收集器.

        Args:
            targets: 执行质量目标
        """
        self._targets = targets or DEFAULT_TARGETS
        self._metrics: dict[str, ExecutionMetrics] = {}

    @property
    def targets(self) -> ExecutionTargets:
        """获取执行质量目标."""
        return self._targets

    def create_metrics(self, plan_id: str, algo: str) -> ExecutionMetrics:
        """创建执行指标.

        Args:
            plan_id: 执行计划ID
            algo: 执行算法

        Returns:
            执行指标对象
        """
        metrics = ExecutionMetrics(plan_id=plan_id, algo=algo)
        self._metrics[plan_id] = metrics
        return metrics

    def get_metrics(self, plan_id: str) -> ExecutionMetrics | None:
        """获取执行指标.

        Args:
            plan_id: 执行计划ID

        Returns:
            执行指标对象或None
        """
        return self._metrics.get(plan_id)

    def remove_metrics(self, plan_id: str) -> bool:
        """移除执行指标.

        Args:
            plan_id: 执行计划ID

        Returns:
            是否成功移除
        """
        if plan_id in self._metrics:
            del self._metrics[plan_id]
            return True
        return False

    def get_all_metrics(self) -> list[ExecutionMetrics]:
        """获取所有执行指标.

        Returns:
            执行指标列表
        """
        return list(self._metrics.values())

    def get_summary(self) -> dict[str, Any]:
        """获取指标汇总.

        Returns:
            汇总信息字典
        """
        if not self._metrics:
            return {
                "total_plans": 0,
                "avg_slippage_pct": 0.0,
                "avg_fill_rate": 0.0,
                "avg_latency_ms": 0.0,
                "status_distribution": {},
            }

        slippages = [m.avg_slippage_pct for m in self._metrics.values()]
        fill_rates = [
            m.fill_rate.fill_rate
            for m in self._metrics.values()
            if m.fill_rate
        ]
        latencies = [
            m.avg_latency_ms
            for m in self._metrics.values()
            if m.avg_latency_ms > 0
        ]

        status_counts: dict[str, int] = {}
        for m in self._metrics.values():
            status = m.get_overall_status(self._targets).value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_plans": len(self._metrics),
            "avg_slippage_pct": sum(slippages) / len(slippages) if slippages else 0.0,
            "avg_fill_rate": sum(fill_rates) / len(fill_rates) if fill_rates else 0.0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "status_distribution": status_counts,
        }

    def clear(self) -> None:
        """清空所有指标."""
        self._metrics.clear()
