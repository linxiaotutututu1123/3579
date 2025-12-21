"""
OrderSplitter - 智能订单拆分模块.

V4PRO Platform Component - Mode 2 Trading Pipeline
SPEC: 5.3.2 Order Splitting Algorithms

军规级要求:
- M12: 双重确认 - 大额订单确认机制
- M5: 成本先行 - 滑点最小化

执行质量指标:
- 滑点控制: 目标<=0.1%
- 成交率: >=95%
- 执行延迟: <=100ms

四种拆单算法:
- TWAP: 时间加权平均价格
- VWAP: 成交量加权平均价格
- ICEBERG: 冰山订单
- BEHAVIORAL: 行为伪装拆单
"""

from __future__ import annotations

import asyncio
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from src.execution.order_types import Offset, OrderIntent, Side


# ============================================================================
# 枚举定义
# ============================================================================
class SplitAlgorithm(str, Enum):
    """拆单算法类型.

    属性:
        TWAP: 时间加权平均价格 - 等时间间隔均匀拆分
        VWAP: 成交量加权平均价格 - 按历史成交量分布拆分
        ICEBERG: 冰山订单 - 只显示部分订单量
        BEHAVIORAL: 行为伪装 - 模拟散户行为模式
    """

    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    BEHAVIORAL = "BEHAVIORAL"


class SplitOrderStatus(str, Enum):
    """拆单订单状态.

    属性:
        PENDING: 待执行
        EXECUTING: 执行中
        FILLED: 已成交
        PARTIAL_FILLED: 部分成交
        CANCELLED: 已取消
        FAILED: 执行失败
    """

    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    FILLED = "FILLED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class MarketCondition(str, Enum):
    """市场状态.

    属性:
        NORMAL: 正常流动性
        HIGH_VOLATILITY: 高波动
        LOW_LIQUIDITY: 低流动性
        TRENDING: 趋势行情
    """

    NORMAL = "NORMAL"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    TRENDING = "TRENDING"


# ============================================================================
# 数据类定义
# ============================================================================
@dataclass
class MarketSnapshot:
    """市场快照数据.

    Attributes:
        symbol: 合约代码
        bid: 买一价
        ask: 卖一价
        last_price: 最新价
        bid_volume: 买一量
        ask_volume: 卖一量
        volume: 当前成交量
        avg_volume: 平均成交量(分钟级)
        volatility: 波动率
        tick_size: 最小变动价位
        timestamp: 时间戳
    """

    symbol: str
    bid: float
    ask: float
    last_price: float
    bid_volume: int
    ask_volume: int
    volume: int
    avg_volume: float
    volatility: float
    tick_size: float
    timestamp: float = field(default_factory=time.time)

    def spread(self) -> float:
        """计算买卖价差."""
        return self.ask - self.bid

    def spread_bps(self) -> float:
        """计算价差(基点)."""
        if self.last_price <= 0:
            return 0.0
        return (self.spread() / self.last_price) * 10000

    def mid_price(self) -> float:
        """计算中间价."""
        return (self.bid + self.ask) / 2


@dataclass
class SplitOrder:
    """拆分后的子订单.

    Attributes:
        order_id: 订单ID
        parent_id: 父订单ID
        sequence: 序号
        symbol: 合约代码
        side: 买卖方向
        offset: 开平仓
        price: 价格
        qty: 数量
        scheduled_time: 计划执行时间
        status: 订单状态
        filled_qty: 已成交数量
        filled_price: 成交均价
        slippage: 滑点
        latency_ms: 执行延迟(毫秒)
        created_at: 创建时间
        executed_at: 执行时间
    """

    order_id: str
    parent_id: str
    sequence: int
    symbol: str
    side: Side
    offset: Offset
    price: float
    qty: int
    scheduled_time: float
    status: SplitOrderStatus = SplitOrderStatus.PENDING
    filled_qty: int = 0
    filled_price: float = 0.0
    slippage: float = 0.0
    latency_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    executed_at: float = 0.0

    def to_intent(self) -> OrderIntent:
        """转换为OrderIntent."""
        return OrderIntent(
            symbol=self.symbol,
            side=self.side,
            offset=self.offset,
            price=self.price,
            qty=self.qty,
            reason=f"split_order_{self.parent_id}_{self.sequence}",
        )

    def fill_rate(self) -> float:
        """计算成交率."""
        if self.qty <= 0:
            return 0.0
        return self.filled_qty / self.qty


@dataclass
class SplitPlan:
    """拆单计划.

    Attributes:
        plan_id: 计划ID
        parent_order: 原始订单
        algorithm: 使用的算法
        orders: 拆分后的子订单列表
        total_qty: 总数量
        filled_qty: 已成交数量
        start_time: 开始时间
        end_time: 预计结束时间
        status: 执行状态
        execution_metrics: 执行指标
    """

    plan_id: str
    parent_order: OrderIntent
    algorithm: SplitAlgorithm
    orders: list[SplitOrder] = field(default_factory=list)
    total_qty: int = 0
    filled_qty: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    status: SplitOrderStatus = SplitOrderStatus.PENDING
    execution_metrics: dict[str, Any] = field(default_factory=dict)

    def progress(self) -> float:
        """计算执行进度."""
        if self.total_qty <= 0:
            return 0.0
        return self.filled_qty / self.total_qty

    def avg_slippage(self) -> float:
        """计算平均滑点."""
        filled_orders = [o for o in self.orders if o.filled_qty > 0]
        if not filled_orders:
            return 0.0
        total_slippage = sum(o.slippage * o.filled_qty for o in filled_orders)
        total_filled = sum(o.filled_qty for o in filled_orders)
        return total_slippage / total_filled if total_filled > 0 else 0.0

    def fill_rate(self) -> float:
        """计算整体成交率."""
        return self.progress()

    def avg_latency_ms(self) -> float:
        """计算平均延迟."""
        executed_orders = [o for o in self.orders if o.executed_at > 0]
        if not executed_orders:
            return 0.0
        return sum(o.latency_ms for o in executed_orders) / len(executed_orders)


@dataclass
class SplitterConfig:
    """拆单器配置.

    Attributes:
        min_order_qty: 最小拆单量
        max_slices: 最大拆分数量
        twap_interval_seconds: TWAP时间间隔(秒)
        vwap_lookback_minutes: VWAP回溯时长(分钟)
        iceberg_show_ratio: 冰山显示比例
        iceberg_random_factor: 冰山随机因子
        behavioral_min_interval_ms: 行为伪装最小间隔(毫秒)
        behavioral_max_interval_ms: 行为伪装最大间隔(毫秒)
        large_order_threshold: 大额订单阈值
        target_slippage_bps: 目标滑点(基点)
        target_fill_rate: 目标成交率
        target_latency_ms: 目标延迟(毫秒)
        confirmation_required: 是否需要确认(M12军规)
    """

    min_order_qty: int = 1
    max_slices: int = 100
    twap_interval_seconds: float = 60.0
    vwap_lookback_minutes: int = 30
    iceberg_show_ratio: float = 0.1
    iceberg_random_factor: float = 0.3
    behavioral_min_interval_ms: float = 500
    behavioral_max_interval_ms: float = 3000
    large_order_threshold: int = 100
    target_slippage_bps: float = 10.0  # 0.1% = 10 bps
    target_fill_rate: float = 0.95
    target_latency_ms: float = 100.0
    confirmation_required: bool = True


@dataclass
class VolumeProfile:
    """成交量分布.

    Attributes:
        intervals: 时间区间列表(分钟)
        volumes: 各区间成交量
        total_volume: 总成交量
    """

    intervals: list[int] = field(default_factory=list)
    volumes: list[float] = field(default_factory=list)
    total_volume: float = 0.0

    def get_weight(self, interval_idx: int) -> float:
        """获取指定区间的权重."""
        if self.total_volume <= 0 or interval_idx >= len(self.volumes):
            return 0.0
        return self.volumes[interval_idx] / self.total_volume


@dataclass
class ExecutionQuality:
    """执行质量指标.

    军规覆盖:
    - M5: 成本先行 - 滑点监控

    Attributes:
        slippage_bps: 实际滑点(基点)
        fill_rate: 成交率
        latency_ms: 执行延迟(毫秒)
        target_slippage_bps: 目标滑点
        target_fill_rate: 目标成交率
        target_latency_ms: 目标延迟
    """

    slippage_bps: float = 0.0
    fill_rate: float = 0.0
    latency_ms: float = 0.0
    target_slippage_bps: float = 10.0  # 0.1%
    target_fill_rate: float = 0.95
    target_latency_ms: float = 100.0

    def slippage_ok(self) -> bool:
        """滑点是否达标."""
        return self.slippage_bps <= self.target_slippage_bps

    def fill_rate_ok(self) -> bool:
        """成交率是否达标."""
        return self.fill_rate >= self.target_fill_rate

    def latency_ok(self) -> bool:
        """延迟是否达标."""
        return self.latency_ms <= self.target_latency_ms

    def all_targets_met(self) -> bool:
        """所有指标是否达标."""
        return self.slippage_ok() and self.fill_rate_ok() and self.latency_ok()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "slippage_bps": round(self.slippage_bps, 2),
            "fill_rate": round(self.fill_rate, 4),
            "latency_ms": round(self.latency_ms, 2),
            "slippage_ok": self.slippage_ok(),
            "fill_rate_ok": self.fill_rate_ok(),
            "latency_ok": self.latency_ok(),
            "all_targets_met": self.all_targets_met(),
        }


# ============================================================================
# 拆单算法基类
# ============================================================================
class SplitAlgorithmBase(ABC):
    """拆单算法基类.

    所有拆单算法必须继承此类并实现generate_plan方法。
    """

    def __init__(self, config: SplitterConfig) -> None:
        """初始化算法.

        Args:
            config: 拆单器配置
        """
        self._config = config

    @property
    def config(self) -> SplitterConfig:
        """获取配置."""
        return self._config

    @abstractmethod
    def generate_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """生成拆单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)
            volume_profile: 成交量分布(VWAP使用)

        Returns:
            拆单计划
        """
        raise NotImplementedError

    def _calculate_slices(self, total_qty: int) -> int:
        """计算拆分数量.

        Args:
            total_qty: 总数量

        Returns:
            拆分数量
        """
        min_qty = max(self._config.min_order_qty, 1)
        slices = math.ceil(total_qty / min_qty)
        return min(slices, self._config.max_slices)

    def _generate_order_id(self) -> str:
        """生成订单ID."""
        return str(uuid.uuid4())[:8]

    def _generate_plan_id(self) -> str:
        """生成计划ID."""
        return f"plan_{uuid.uuid4().hex[:12]}"


# ============================================================================
# TWAP算法 - 时间加权平均价格
# ============================================================================
class TWAPAlgorithm(SplitAlgorithmBase):
    """TWAP拆单算法.

    时间加权平均价格算法，将订单按等时间间隔均匀拆分。
    适用于流动性充足、波动率较低的市场。

    特点:
    - 等时间间隔执行
    - 等量拆分
    - 简单易于实现
    - 执行可预测性强
    """

    def generate_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """生成TWAP拆单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)
            volume_profile: 成交量分布(TWAP不使用)

        Returns:
            TWAP拆单计划
        """
        plan_id = self._generate_plan_id()
        current_time = time.time()

        # 计算拆分数量
        num_slices = max(
            1,
            min(
                int(duration_seconds / self._config.twap_interval_seconds),
                self._calculate_slices(order.qty),
            ),
        )

        # 计算每片数量
        base_qty = order.qty // num_slices
        remainder = order.qty % num_slices

        # 计算时间间隔
        interval = duration_seconds / num_slices

        # 生成子订单
        orders: list[SplitOrder] = []
        for i in range(num_slices):
            qty = base_qty + (1 if i < remainder else 0)
            if qty <= 0:
                continue

            scheduled_time = current_time + (i * interval)

            split_order = SplitOrder(
                order_id=self._generate_order_id(),
                parent_id=plan_id,
                sequence=i + 1,
                symbol=order.symbol,
                side=order.side,
                offset=order.offset,
                price=order.price,
                qty=qty,
                scheduled_time=scheduled_time,
            )
            orders.append(split_order)

        return SplitPlan(
            plan_id=plan_id,
            parent_order=order,
            algorithm=SplitAlgorithm.TWAP,
            orders=orders,
            total_qty=order.qty,
            start_time=current_time,
            end_time=current_time + duration_seconds,
            execution_metrics={
                "algorithm": "TWAP",
                "num_slices": num_slices,
                "interval_seconds": interval,
                "base_qty": base_qty,
            },
        )


# ============================================================================
# VWAP算法 - 成交量加权平均价格
# ============================================================================
class VWAPAlgorithm(SplitAlgorithmBase):
    """VWAP拆单算法.

    成交量加权平均价格算法，按历史成交量分布拆分订单。
    适用于需要减小市场冲击的大额订单。

    特点:
    - 按成交量分布执行
    - 高成交量时段多执行
    - 减小对市场价格的冲击
    - 更接近市场真实成交均价
    """

    def generate_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """生成VWAP拆单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)
            volume_profile: 成交量分布

        Returns:
            VWAP拆单计划
        """
        plan_id = self._generate_plan_id()
        current_time = time.time()

        # 如果没有成交量分布，使用默认分布
        if volume_profile is None or not volume_profile.intervals:
            volume_profile = self._generate_default_profile(duration_seconds)

        num_intervals = len(volume_profile.intervals)

        # 按成交量权重分配数量
        orders: list[SplitOrder] = []
        allocated_qty = 0
        interval_duration = duration_seconds / num_intervals if num_intervals > 0 else duration_seconds

        for i, interval in enumerate(volume_profile.intervals):
            weight = volume_profile.get_weight(i)
            qty = int(order.qty * weight)

            # 最后一个区间分配剩余数量
            if i == num_intervals - 1:
                qty = order.qty - allocated_qty
            else:
                allocated_qty += qty

            if qty <= 0:
                continue

            scheduled_time = current_time + (i * interval_duration)

            split_order = SplitOrder(
                order_id=self._generate_order_id(),
                parent_id=plan_id,
                sequence=i + 1,
                symbol=order.symbol,
                side=order.side,
                offset=order.offset,
                price=order.price,
                qty=qty,
                scheduled_time=scheduled_time,
            )
            orders.append(split_order)

        return SplitPlan(
            plan_id=plan_id,
            parent_order=order,
            algorithm=SplitAlgorithm.VWAP,
            orders=orders,
            total_qty=order.qty,
            start_time=current_time,
            end_time=current_time + duration_seconds,
            execution_metrics={
                "algorithm": "VWAP",
                "num_intervals": num_intervals,
                "volume_profile": {
                    "intervals": volume_profile.intervals,
                    "weights": [
                        volume_profile.get_weight(i)
                        for i in range(len(volume_profile.intervals))
                    ],
                },
            },
        )

    def _generate_default_profile(self, duration_seconds: float) -> VolumeProfile:
        """生成默认成交量分布.

        采用典型的U型分布：开盘和收盘成交量较高。

        Args:
            duration_seconds: 执行时长(秒)

        Returns:
            默认成交量分布
        """
        # 默认分成10个区间
        num_intervals = 10
        intervals = list(range(num_intervals))

        # U型分布：两端高，中间低
        volumes = []
        for i in range(num_intervals):
            # 使用抛物线模型
            x = i / (num_intervals - 1)  # 0 to 1
            volume = 1.5 - (x - 0.5) ** 2 * 4  # U型曲线
            volumes.append(max(0.5, volume))

        total_volume = sum(volumes)

        return VolumeProfile(
            intervals=intervals,
            volumes=volumes,
            total_volume=total_volume,
        )


# ============================================================================
# ICEBERG算法 - 冰山订单
# ============================================================================
class IcebergAlgorithm(SplitAlgorithmBase):
    """冰山订单算法.

    只显示部分订单量，隐藏真实交易意图。
    适用于大额订单防止被市场识别。

    特点:
    - 只显示小部分订单量
    - 随机变化显示量
    - 成交后自动续挂
    - 降低市场冲击
    """

    def generate_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """生成冰山订单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)
            volume_profile: 成交量分布(冰山不使用)

        Returns:
            冰山订单计划
        """
        plan_id = self._generate_plan_id()
        current_time = time.time()

        # 计算显示量
        show_qty = max(
            self._config.min_order_qty,
            int(order.qty * self._config.iceberg_show_ratio),
        )

        # 计算拆分数量
        num_slices = math.ceil(order.qty / show_qty)
        num_slices = min(num_slices, self._config.max_slices)

        # 计算时间间隔（略微随机化）
        base_interval = duration_seconds / num_slices

        # 生成子订单
        orders: list[SplitOrder] = []
        remaining_qty = order.qty
        accumulated_time = 0.0

        for i in range(num_slices):
            # 随机化显示量
            random_factor = 1.0 + random.uniform(
                -self._config.iceberg_random_factor,
                self._config.iceberg_random_factor,
            )
            qty = min(int(show_qty * random_factor), remaining_qty)
            qty = max(qty, self._config.min_order_qty)

            if qty <= 0:
                break

            # 随机化时间间隔
            time_factor = 1.0 + random.uniform(-0.2, 0.2)
            interval = base_interval * time_factor
            scheduled_time = current_time + accumulated_time

            split_order = SplitOrder(
                order_id=self._generate_order_id(),
                parent_id=plan_id,
                sequence=i + 1,
                symbol=order.symbol,
                side=order.side,
                offset=order.offset,
                price=order.price,
                qty=qty,
                scheduled_time=scheduled_time,
            )
            orders.append(split_order)

            remaining_qty -= qty
            accumulated_time += interval

            if remaining_qty <= 0:
                break

        return SplitPlan(
            plan_id=plan_id,
            parent_order=order,
            algorithm=SplitAlgorithm.ICEBERG,
            orders=orders,
            total_qty=order.qty,
            start_time=current_time,
            end_time=current_time + duration_seconds,
            execution_metrics={
                "algorithm": "ICEBERG",
                "show_qty": show_qty,
                "num_slices": len(orders),
                "random_factor": self._config.iceberg_random_factor,
            },
        )


# ============================================================================
# BEHAVIORAL算法 - 行为伪装拆单
# ============================================================================
class BehavioralAlgorithm(SplitAlgorithmBase):
    """行为伪装拆单算法.

    模拟散户交易行为，避免被识别为算法交易。
    适用于对手方有检测算法交易能力的市场。

    特点:
    - 随机化订单大小
    - 随机化时间间隔
    - 模拟人类交易模式
    - 混合不同价格策略
    """

    # 行为模式权重
    BEHAVIOR_PATTERNS: dict[str, float] = {
        "aggressive": 0.3,  # 激进：吃单
        "passive": 0.4,  # 被动：挂单
        "neutral": 0.3,  # 中性：中间价
    }

    def generate_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """生成行为伪装拆单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)
            volume_profile: 成交量分布(可选使用)

        Returns:
            行为伪装拆单计划
        """
        plan_id = self._generate_plan_id()
        current_time = time.time()

        # 计算拆分数量（使用随机因子）
        avg_interval_ms = (
            self._config.behavioral_min_interval_ms
            + self._config.behavioral_max_interval_ms
        ) / 2
        num_slices = int(duration_seconds * 1000 / avg_interval_ms)
        num_slices = max(1, min(num_slices, self._calculate_slices(order.qty)))

        # 生成随机数量分布（模拟人类行为）
        qty_ratios = self._generate_human_like_distribution(num_slices)

        # 生成子订单
        orders: list[SplitOrder] = []
        remaining_qty = order.qty
        accumulated_time = 0.0

        for i in range(num_slices):
            # 计算数量（基于随机分布）
            qty = int(order.qty * qty_ratios[i])
            qty = max(self._config.min_order_qty, min(qty, remaining_qty))

            if qty <= 0:
                break

            # 随机化时间间隔
            interval_ms = random.uniform(
                self._config.behavioral_min_interval_ms,
                self._config.behavioral_max_interval_ms,
            )
            interval_seconds = interval_ms / 1000.0

            # 选择价格策略
            price = self._select_price(order, market)

            scheduled_time = current_time + accumulated_time

            split_order = SplitOrder(
                order_id=self._generate_order_id(),
                parent_id=plan_id,
                sequence=i + 1,
                symbol=order.symbol,
                side=order.side,
                offset=order.offset,
                price=price,
                qty=qty,
                scheduled_time=scheduled_time,
            )
            orders.append(split_order)

            remaining_qty -= qty
            accumulated_time += interval_seconds

            if remaining_qty <= 0:
                break

        # 处理剩余数量
        if remaining_qty > 0 and orders:
            orders[-1].qty += remaining_qty

        return SplitPlan(
            plan_id=plan_id,
            parent_order=order,
            algorithm=SplitAlgorithm.BEHAVIORAL,
            orders=orders,
            total_qty=order.qty,
            start_time=current_time,
            end_time=current_time + accumulated_time,
            execution_metrics={
                "algorithm": "BEHAVIORAL",
                "num_slices": len(orders),
                "behavior_patterns": self.BEHAVIOR_PATTERNS,
                "avg_interval_ms": avg_interval_ms,
            },
        )

    def _generate_human_like_distribution(self, num_slices: int) -> list[float]:
        """生成类人类的数量分布.

        人类交易通常不是完全均匀的，会有一定的随机性和偏好。

        Args:
            num_slices: 拆分数量

        Returns:
            各片数量占比列表
        """
        if num_slices <= 0:
            return []

        # 生成基础随机分布
        raw_ratios = [random.gauss(1.0, 0.3) for _ in range(num_slices)]
        raw_ratios = [max(0.2, r) for r in raw_ratios]  # 确保最小值

        # 归一化
        total = sum(raw_ratios)
        return [r / total for r in raw_ratios]

    def _select_price(self, order: OrderIntent, market: MarketSnapshot) -> float:
        """根据行为模式选择价格.

        Args:
            order: 订单
            market: 市场快照

        Returns:
            选择的价格
        """
        # 随机选择行为模式
        r = random.random()
        cumulative = 0.0

        for pattern, weight in self.BEHAVIOR_PATTERNS.items():
            cumulative += weight
            if r <= cumulative:
                return self._get_price_for_pattern(pattern, order, market)

        return order.price

    def _get_price_for_pattern(
        self, pattern: str, order: OrderIntent, market: MarketSnapshot
    ) -> float:
        """根据行为模式获取价格.

        Args:
            pattern: 行为模式
            order: 订单
            market: 市场快照

        Returns:
            价格
        """
        if pattern == "aggressive":
            # 激进：吃对手价
            if order.side == Side.BUY:
                return market.ask
            else:
                return market.bid
        elif pattern == "passive":
            # 被动：挂己方价
            if order.side == Side.BUY:
                return market.bid
            else:
                return market.ask
        else:  # neutral
            # 中性：中间价
            return market.mid_price()


# ============================================================================
# 策略选择器
# ============================================================================
class AlgorithmSelector:
    """拆单算法选择器.

    根据订单规模、市场流动性、时段选择最优算法。

    选择逻辑:
    - 小订单: TWAP（简单高效）
    - 中等订单 + 正常流动性: VWAP（减小冲击）
    - 大订单 + 低流动性: ICEBERG（隐藏意图）
    - 敏感环境: BEHAVIORAL（伪装交易）
    """

    def __init__(self, config: SplitterConfig) -> None:
        """初始化选择器.

        Args:
            config: 拆单器配置
        """
        self._config = config
        self._algorithms: dict[SplitAlgorithm, SplitAlgorithmBase] = {
            SplitAlgorithm.TWAP: TWAPAlgorithm(config),
            SplitAlgorithm.VWAP: VWAPAlgorithm(config),
            SplitAlgorithm.ICEBERG: IcebergAlgorithm(config),
            SplitAlgorithm.BEHAVIORAL: BehavioralAlgorithm(config),
        }

    def select_algorithm(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        condition: MarketCondition = MarketCondition.NORMAL,
        force_algorithm: SplitAlgorithm | None = None,
    ) -> SplitAlgorithm:
        """选择最优算法.

        Args:
            order: 订单
            market: 市场快照
            condition: 市场状态
            force_algorithm: 强制使用的算法（可选）

        Returns:
            选择的算法类型
        """
        if force_algorithm is not None:
            return force_algorithm

        qty = order.qty
        avg_volume = market.avg_volume
        volatility = market.volatility

        # 计算订单相对市场的规模
        volume_ratio = qty / avg_volume if avg_volume > 0 else 1.0

        # 判断逻辑
        if condition == MarketCondition.HIGH_VOLATILITY:
            # 高波动性：使用冰山订单减小暴露
            return SplitAlgorithm.ICEBERG

        if condition == MarketCondition.LOW_LIQUIDITY:
            # 低流动性：使用行为伪装避免被检测
            return SplitAlgorithm.BEHAVIORAL

        if volume_ratio > 0.1:  # 订单量超过平均成交量10%
            # 大订单：使用VWAP减小市场冲击
            if volatility > 0.02:  # 波动率超过2%
                return SplitAlgorithm.ICEBERG
            return SplitAlgorithm.VWAP

        if volume_ratio > 0.05:  # 订单量超过平均成交量5%
            # 中等订单：使用VWAP
            return SplitAlgorithm.VWAP

        # 小订单：使用TWAP
        return SplitAlgorithm.TWAP

    def get_algorithm(self, algo_type: SplitAlgorithm) -> SplitAlgorithmBase:
        """获取算法实例.

        Args:
            algo_type: 算法类型

        Returns:
            算法实例
        """
        return self._algorithms[algo_type]


# ============================================================================
# 订单拆分器主类
# ============================================================================
class OrderSplitter:
    """智能订单拆分器.

    V4PRO Platform Component - Mode 2 Trading Pipeline

    军规覆盖:
    - M12: 双重确认 - 大额订单确认机制
    - M5: 成本先行 - 滑点最小化

    功能:
    - 自动选择最优拆单算法
    - 支持手动指定算法
    - 执行质量监控
    - 大额订单确认机制
    """

    def __init__(
        self,
        config: SplitterConfig | None = None,
        on_confirmation: Callable[[OrderIntent, SplitPlan], bool] | None = None,
    ) -> None:
        """初始化订单拆分器.

        Args:
            config: 拆单器配置
            on_confirmation: 大额订单确认回调(M12军规)
        """
        self._config = config or SplitterConfig()
        self._selector = AlgorithmSelector(self._config)
        self._on_confirmation = on_confirmation
        self._active_plans: dict[str, SplitPlan] = {}
        self._completed_plans: dict[str, SplitPlan] = {}
        self._stats = {
            "total_orders": 0,
            "total_qty": 0,
            "total_filled": 0,
            "avg_slippage_bps": 0.0,
            "avg_fill_rate": 0.0,
            "avg_latency_ms": 0.0,
        }

    @property
    def config(self) -> SplitterConfig:
        """获取配置."""
        return self._config

    @property
    def active_plans(self) -> dict[str, SplitPlan]:
        """获取活跃计划."""
        return self._active_plans.copy()

    def create_plan(
        self,
        order: OrderIntent,
        market: MarketSnapshot,
        duration_seconds: float = 300.0,
        condition: MarketCondition = MarketCondition.NORMAL,
        force_algorithm: SplitAlgorithm | None = None,
        volume_profile: VolumeProfile | None = None,
    ) -> SplitPlan:
        """创建拆单计划.

        Args:
            order: 原始订单
            market: 市场快照
            duration_seconds: 执行时长(秒)，默认5分钟
            condition: 市场状态
            force_algorithm: 强制使用的算法（可选）
            volume_profile: 成交量分布（VWAP使用）

        Returns:
            拆单计划
        """
        # 选择算法
        algo_type = self._selector.select_algorithm(
            order, market, condition, force_algorithm
        )
        algorithm = self._selector.get_algorithm(algo_type)

        # 生成计划
        plan = algorithm.generate_plan(order, market, duration_seconds, volume_profile)

        # M12军规：大额订单确认
        if self._requires_confirmation(order):
            if not self._confirm_order(order, plan):
                plan.status = SplitOrderStatus.CANCELLED
                return plan

        # 保存计划
        self._active_plans[plan.plan_id] = plan
        self._stats["total_orders"] += 1
        self._stats["total_qty"] += plan.total_qty

        return plan

    def _requires_confirmation(self, order: OrderIntent) -> bool:
        """判断是否需要确认.

        M12军规：大额订单双重确认

        Args:
            order: 订单

        Returns:
            是否需要确认
        """
        if not self._config.confirmation_required:
            return False
        return order.qty >= self._config.large_order_threshold

    def _confirm_order(self, order: OrderIntent, plan: SplitPlan) -> bool:
        """确认大额订单.

        M12军规：双重确认机制

        Args:
            order: 订单
            plan: 拆单计划

        Returns:
            是否确认执行
        """
        if self._on_confirmation is None:
            return True
        return self._on_confirmation(order, plan)

    def update_order_status(
        self,
        plan_id: str,
        order_id: str,
        status: SplitOrderStatus,
        filled_qty: int = 0,
        filled_price: float = 0.0,
        latency_ms: float = 0.0,
    ) -> bool:
        """更新子订单状态.

        Args:
            plan_id: 计划ID
            order_id: 订单ID
            status: 新状态
            filled_qty: 成交数量
            filled_price: 成交价格
            latency_ms: 执行延迟

        Returns:
            是否更新成功
        """
        plan = self._active_plans.get(plan_id)
        if plan is None:
            return False

        for order in plan.orders:
            if order.order_id == order_id:
                order.status = status
                order.filled_qty = filled_qty
                order.filled_price = filled_price
                order.latency_ms = latency_ms
                order.executed_at = time.time()

                # 计算滑点
                if filled_price > 0 and order.price > 0:
                    slippage = abs(filled_price - order.price) / order.price * 10000
                    order.slippage = slippage

                # 更新计划统计
                plan.filled_qty = sum(o.filled_qty for o in plan.orders)

                # 检查计划是否完成
                self._check_plan_completion(plan)
                return True

        return False

    def _check_plan_completion(self, plan: SplitPlan) -> None:
        """检查计划是否完成.

        Args:
            plan: 拆单计划
        """
        all_done = all(
            o.status
            in (
                SplitOrderStatus.FILLED,
                SplitOrderStatus.CANCELLED,
                SplitOrderStatus.FAILED,
            )
            for o in plan.orders
        )

        if all_done:
            if plan.filled_qty >= plan.total_qty * 0.95:
                plan.status = SplitOrderStatus.FILLED
            elif plan.filled_qty > 0:
                plan.status = SplitOrderStatus.PARTIAL_FILLED
            else:
                plan.status = SplitOrderStatus.FAILED

            # 移动到已完成
            self._completed_plans[plan.plan_id] = plan
            self._active_plans.pop(plan.plan_id, None)

            # 更新统计
            self._update_stats(plan)

    def _update_stats(self, plan: SplitPlan) -> None:
        """更新统计信息.

        Args:
            plan: 已完成的计划
        """
        self._stats["total_filled"] += plan.filled_qty

        # 更新平均值（滚动平均）
        n = len(self._completed_plans)
        if n > 0:
            old_slippage = self._stats["avg_slippage_bps"]
            old_fill_rate = self._stats["avg_fill_rate"]
            old_latency = self._stats["avg_latency_ms"]

            new_slippage = plan.avg_slippage()
            new_fill_rate = plan.fill_rate()
            new_latency = plan.avg_latency_ms()

            self._stats["avg_slippage_bps"] = (
                old_slippage * (n - 1) + new_slippage
            ) / n
            self._stats["avg_fill_rate"] = (old_fill_rate * (n - 1) + new_fill_rate) / n
            self._stats["avg_latency_ms"] = (old_latency * (n - 1) + new_latency) / n

    def get_execution_quality(self, plan_id: str | None = None) -> ExecutionQuality:
        """获取执行质量指标.

        M5军规：成本先行 - 监控滑点

        Args:
            plan_id: 计划ID（可选，为空返回整体指标）

        Returns:
            执行质量指标
        """
        if plan_id is not None:
            plan = self._active_plans.get(plan_id) or self._completed_plans.get(
                plan_id
            )
            if plan is None:
                return ExecutionQuality()

            return ExecutionQuality(
                slippage_bps=plan.avg_slippage(),
                fill_rate=plan.fill_rate(),
                latency_ms=plan.avg_latency_ms(),
                target_slippage_bps=self._config.target_slippage_bps,
                target_fill_rate=self._config.target_fill_rate,
                target_latency_ms=self._config.target_latency_ms,
            )

        # 返回整体指标
        return ExecutionQuality(
            slippage_bps=self._stats["avg_slippage_bps"],
            fill_rate=self._stats["avg_fill_rate"],
            latency_ms=self._stats["avg_latency_ms"],
            target_slippage_bps=self._config.target_slippage_bps,
            target_fill_rate=self._config.target_fill_rate,
            target_latency_ms=self._config.target_latency_ms,
        )

    def get_pending_orders(self, plan_id: str) -> list[SplitOrder]:
        """获取待执行订单.

        Args:
            plan_id: 计划ID

        Returns:
            待执行订单列表
        """
        plan = self._active_plans.get(plan_id)
        if plan is None:
            return []

        current_time = time.time()
        return [
            o
            for o in plan.orders
            if o.status == SplitOrderStatus.PENDING and o.scheduled_time <= current_time
        ]

    def get_next_order(self, plan_id: str) -> SplitOrder | None:
        """获取下一个待执行订单.

        Args:
            plan_id: 计划ID

        Returns:
            下一个待执行订单，没有则返回None
        """
        pending = self.get_pending_orders(plan_id)
        if not pending:
            return None
        return min(pending, key=lambda o: o.scheduled_time)

    def cancel_plan(self, plan_id: str) -> bool:
        """取消拆单计划.

        Args:
            plan_id: 计划ID

        Returns:
            是否取消成功
        """
        plan = self._active_plans.get(plan_id)
        if plan is None:
            return False

        for order in plan.orders:
            if order.status == SplitOrderStatus.PENDING:
                order.status = SplitOrderStatus.CANCELLED

        plan.status = SplitOrderStatus.CANCELLED
        self._completed_plans[plan_id] = plan
        self._active_plans.pop(plan_id, None)
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计字典
        """
        return {
            **self._stats,
            "active_plans": len(self._active_plans),
            "completed_plans": len(self._completed_plans),
            "execution_quality": self.get_execution_quality().to_dict(),
        }


# ============================================================================
# 异步执行器
# ============================================================================
class AsyncOrderExecutor:
    """异步订单执行器.

    提供异步执行拆单计划的能力。

    使用示例:
        >>> executor = AsyncOrderExecutor(splitter, broker)
        >>> await executor.execute_plan(plan_id)
    """

    def __init__(
        self,
        splitter: OrderSplitter,
        broker: Any,  # Broker protocol
        max_concurrent: int = 5,
    ) -> None:
        """初始化执行器.

        Args:
            splitter: 订单拆分器
            broker: 经纪商接口
            max_concurrent: 最大并发订单数
        """
        self._splitter = splitter
        self._broker = broker
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_plan(self, plan_id: str) -> ExecutionQuality:
        """异步执行拆单计划.

        Args:
            plan_id: 计划ID

        Returns:
            执行质量指标
        """
        plan = self._splitter.active_plans.get(plan_id)
        if plan is None:
            return ExecutionQuality()

        plan.status = SplitOrderStatus.EXECUTING

        # 按计划时间执行各子订单
        for order in plan.orders:
            if order.status != SplitOrderStatus.PENDING:
                continue

            # 等待到计划时间
            wait_time = order.scheduled_time - time.time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # 执行订单
            await self._execute_order(plan_id, order)

        return self._splitter.get_execution_quality(plan_id)

    async def _execute_order(self, plan_id: str, order: SplitOrder) -> None:
        """执行单个子订单.

        Args:
            plan_id: 计划ID
            order: 子订单
        """
        async with self._semaphore:
            start_time = time.time()
            order.status = SplitOrderStatus.EXECUTING

            try:
                # 调用经纪商接口
                intent = order.to_intent()
                ack = self._broker.place_order(intent)

                latency_ms = (time.time() - start_time) * 1000

                # 更新状态（假设立即成交）
                self._splitter.update_order_status(
                    plan_id=plan_id,
                    order_id=order.order_id,
                    status=SplitOrderStatus.FILLED,
                    filled_qty=order.qty,
                    filled_price=order.price,
                    latency_ms=latency_ms,
                )

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                self._splitter.update_order_status(
                    plan_id=plan_id,
                    order_id=order.order_id,
                    status=SplitOrderStatus.FAILED,
                    filled_qty=0,
                    filled_price=0.0,
                    latency_ms=latency_ms,
                )
