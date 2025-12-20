"""
CostEstimator - 成本估计器

V3PRO+ Platform Component - Phase 1
V2 SPEC: 第 6 章 成本模型
V2 Scenarios:
- COST.MODEL.FEE_ESTIMATE: 手续费估计
- COST.MODEL.SLIPPAGE_ESTIMATE: 滑点估计
- COST.MODEL.IMPACT_ESTIMATE: 市场冲击估计
- COST.GATE.EDGE_CHECK: edge gate 检查

军规级要求:
- 精确的手续费计算（按比例/按手）
- 滑点估计基于订单簿深度
- 市场冲击基于成交量占比
- edge gate: signal_edge > total_cost 才交易
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.market.instrument_cache import InstrumentCache


@dataclass
class CostBreakdown:
    """成本分解.

    Attributes:
        fee: 手续费
        slippage: 滑点成本
        impact: 市场冲击成本
        total: 总成本
    """

    fee: float
    slippage: float
    impact: float
    total: float

    @property
    def per_unit(self) -> float:
        """每单位成本（用于与 edge 比较）."""
        return self.total


class CostEstimator:
    """成本估计器.

    V2 Scenarios:
    - COST.MODEL.FEE_ESTIMATE: 手续费估计
    - COST.MODEL.SLIPPAGE_ESTIMATE: 滑点估计
    - COST.MODEL.IMPACT_ESTIMATE: 市场冲击估计
    - COST.GATE.EDGE_CHECK: edge gate 检查

    基于合约信息和市场状态计算交易成本。
    """

    # 默认手续费率（万分之一）
    DEFAULT_FEE_RATE: float = 0.0001
    # 平今加收倍数
    CLOSE_TODAY_MULTIPLIER: float = 3.0
    # 滑点基准（tick 数）
    SLIPPAGE_BASE_TICKS: float = 0.5
    # 冲击系数（sqrt(qty/adv)）
    IMPACT_COEFFICIENT: float = 0.1

    def __init__(
        self,
        instrument_cache: InstrumentCache | None = None,
        fee_rates: dict[str, float] | None = None,
    ) -> None:
        """初始化估计器.

        Args:
            instrument_cache: 合约缓存（可选，用于获取 tick_size/multiplier）
            fee_rates: 品种手续费率映射 {product: rate}（可选）
        """
        self._instrument_cache = instrument_cache
        self._fee_rates = fee_rates or {}

    def fee_estimate(
        self,
        symbol: str,
        notional: float,
        is_close_today: bool = False,
    ) -> float:
        """估计手续费.

        V2 Scenario: COST.MODEL.FEE_ESTIMATE

        Args:
            symbol: 合约代码
            notional: 名义金额（price * qty * multiplier）
            is_close_today: 是否平今仓

        Returns:
            估计的手续费
        """
        # 获取品种手续费率
        product = self._extract_product(symbol)
        rate = self._fee_rates.get(product, self.DEFAULT_FEE_RATE)

        fee = notional * rate

        # 平今加收
        if is_close_today:
            fee *= self.CLOSE_TODAY_MULTIPLIER

        return fee

    def slippage_estimate(
        self,
        symbol: str,
        qty: int,
        depth: int,
    ) -> float:
        """估计滑点.

        V2 Scenario: COST.MODEL.SLIPPAGE_ESTIMATE

        基于订单簿深度估计滑点。深度越浅，滑点越大。

        Args:
            symbol: 合约代码
            qty: 委托数量
            depth: 订单簿深度（单边总挂单量）

        Returns:
            估计的滑点成本（以价值计）
        """
        if depth <= 0:
            # 无深度数据，使用保守估计
            depth = 1

        # 获取合约信息
        tick_size = self._get_tick_size(symbol)
        multiplier = self._get_multiplier(symbol)

        # 滑点 = 基准 ticks * (1 + qty/depth) * tick_size * multiplier * qty
        slippage_ticks = self.SLIPPAGE_BASE_TICKS * (1.0 + qty / depth)
        slippage = slippage_ticks * tick_size * multiplier * qty

        return slippage

    def impact_estimate(
        self,
        symbol: str,
        qty: int,
        adv: float,
    ) -> float:
        """估计市场冲击.

        V2 Scenario: COST.MODEL.IMPACT_ESTIMATE

        基于成交量占比估计市场冲击。使用 sqrt(qty/adv) 模型。

        Args:
            symbol: 合约代码
            qty: 委托数量
            adv: 日均成交量（Average Daily Volume）

        Returns:
            估计的市场冲击成本（以价值计）
        """
        if adv <= 0:
            # 无 ADV 数据，使用保守估计
            adv = 1000.0

        # 获取合约信息
        tick_size = self._get_tick_size(symbol)
        multiplier = self._get_multiplier(symbol)

        # 冲击 = coefficient * sqrt(qty/adv) * tick_size * multiplier * qty
        participation = qty / adv
        impact_ticks = self.IMPACT_COEFFICIENT * (participation ** 0.5) * 100  # 放大为 tick 数
        impact = impact_ticks * tick_size * multiplier * qty

        return impact

    def total_cost(
        self,
        symbol: str,
        qty: int,
        notional: float,
        depth: int,
        adv: float,
        is_close_today: bool = False,
    ) -> CostBreakdown:
        """计算总成本.

        Args:
            symbol: 合约代码
            qty: 委托数量
            notional: 名义金额
            depth: 订单簿深度
            adv: 日均成交量
            is_close_today: 是否平今仓

        Returns:
            成本分解
        """
        fee = self.fee_estimate(symbol, notional, is_close_today)
        slippage = self.slippage_estimate(symbol, qty, depth)
        impact = self.impact_estimate(symbol, qty, adv)

        return CostBreakdown(
            fee=fee,
            slippage=slippage,
            impact=impact,
            total=fee + slippage + impact,
        )

    def edge_gate(
        self,
        signal_edge: float,
        total_cost: float,
    ) -> bool:
        """检查是否通过 edge gate.

        V2 Scenario: COST.GATE.EDGE_CHECK

        只有当信号 edge 大于总成本时才允许交易。

        Args:
            signal_edge: 信号预期收益（edge）
            total_cost: 总成本

        Returns:
            True 表示通过 gate，允许交易
        """
        return signal_edge > total_cost

    def edge_gate_with_breakdown(
        self,
        signal_edge: float,
        cost: CostBreakdown,
    ) -> tuple[bool, float]:
        """带分解的 edge gate 检查.

        Args:
            signal_edge: 信号预期收益
            cost: 成本分解

        Returns:
            (是否通过, 净 edge)
        """
        net_edge = signal_edge - cost.total
        passed = net_edge > 0
        return passed, net_edge

    def _extract_product(self, symbol: str) -> str:
        """从合约代码提取品种.

        Args:
            symbol: 合约代码（如 AO2501）

        Returns:
            品种代码（如 AO）
        """
        if self._instrument_cache:
            info = self._instrument_cache.get(symbol)
            if info:
                return info.product

        # 回退：提取字母部分
        product = ""
        for char in symbol:
            if char.isalpha():
                product += char
            else:
                break
        return product or symbol

    def _get_tick_size(self, symbol: str) -> float:
        """获取合约最小变动价位.

        Args:
            symbol: 合约代码

        Returns:
            tick_size，默认 1.0
        """
        if self._instrument_cache:
            info = self._instrument_cache.get(symbol)
            if info:
                return info.tick_size
        return 1.0

    def _get_multiplier(self, symbol: str) -> int:
        """获取合约乘数.

        Args:
            symbol: 合约代码

        Returns:
            multiplier，默认 10
        """
        if self._instrument_cache:
            info = self._instrument_cache.get(symbol)
            if info:
                return info.multiplier
        return 10

    def set_fee_rate(self, product: str, rate: float) -> None:
        """设置品种手续费率.

        Args:
            product: 品种代码
            rate: 手续费率（如 0.0001 表示万分之一）
        """
        self._fee_rates[product] = rate

    def get_fee_rate(self, product: str) -> float:
        """获取品种手续费率.

        Args:
            product: 品种代码

        Returns:
            手续费率
        """
        return self._fee_rates.get(product, self.DEFAULT_FEE_RATE)
