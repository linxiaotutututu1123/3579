"""
BarBuilder - 连续主力 bars 聚合

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.4
V2 Scenarios: MKT.CONTINUITY.BARS

军规级要求:
- bars_1m_product 从 dominant tick 聚合
- roll 切换点有审计事件
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.market.quote_cache import BookTop


@dataclass
class Bar:
    """K 线数据.

    Attributes:
        symbol: 合约代码（品种级连续主力使用品种代码）
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        open_interest: 持仓量
        ts_start: 开始时间戳
        ts_end: 结束时间戳
    """

    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int
    ts_start: float
    ts_end: float


@dataclass
class BarBuildState:
    """Bar 构建状态."""

    current_bar: Bar | None = None
    last_volume: int = 0
    last_oi: int = 0


class BarBuilder:
    """连续主力 bars 聚合器.

    V2 Scenario: MKT.CONTINUITY.BARS

    军规级要求:
    - bars_1m_product 从 dominant tick 聚合
    - roll 切换点有审计事件
    - 支持 1 分钟 bar 聚合
    """

    def __init__(
        self,
        bar_interval_s: int = 60,
        on_bar_complete: Callable[[Bar], None] | None = None,
        on_roll_event: Callable[[str, str, str, float], None] | None = None,
    ) -> None:
        """初始化聚合器.

        Args:
            bar_interval_s: Bar 周期（秒），默认 60 秒
            on_bar_complete: Bar 完成回调
            on_roll_event: 主力切换回调 (product, old_symbol, new_symbol, ts)
        """
        self._bar_interval_s = bar_interval_s
        self._on_bar_complete = on_bar_complete
        self._on_roll_event = on_roll_event

        # product -> build state
        self._states: dict[str, BarBuildState] = {}
        # product -> current dominant symbol
        self._dominant_map: dict[str, str] = {}
        # product -> completed bars
        self._bars: dict[str, list[Bar]] = {}

    def update_dominant(self, product: str, symbol: str, ts: float) -> None:
        """更新品种的主力合约.

        Args:
            product: 品种代码
            symbol: 新主力合约代码
            ts: 时间戳
        """
        old_symbol = self._dominant_map.get(product)
        if old_symbol and old_symbol != symbol:
            # 主力切换，触发审计事件
            if self._on_roll_event:
                self._on_roll_event(product, old_symbol, symbol, ts)

            # 强制完成当前 bar
            self._force_complete_bar(product, ts)

        self._dominant_map[product] = symbol

    def on_tick(self, product: str, book: BookTop) -> Bar | None:
        """处理 tick 数据.

        V2 Scenario: MKT.CONTINUITY.BARS

        Args:
            product: 品种代码
            book: L1 盘口数据

        Returns:
            如果 bar 完成，返回完成的 bar；否则返回 None
        """
        # 只处理当前主力的 tick
        dominant = self._dominant_map.get(product)
        if dominant and book.symbol != dominant:
            return None

        if product not in self._states:
            self._states[product] = BarBuildState()
        if product not in self._bars:
            self._bars[product] = []

        state = self._states[product]

        # 计算 bar 边界
        bar_start = (int(book.ts) // self._bar_interval_s) * self._bar_interval_s
        bar_end = bar_start + self._bar_interval_s

        # 检查是否需要完成当前 bar
        completed_bar: Bar | None = None
        if state.current_bar and state.current_bar.ts_start < bar_start:
            # 当前 bar 已过期，完成它
            completed_bar = self._complete_bar(product, state.current_bar)

        # 更新或创建 bar
        if state.current_bar is None or state.current_bar.ts_start < bar_start:
            # 创建新 bar
            state.current_bar = Bar(
                symbol=product,  # 使用品种代码作为连续主力标识
                open=book.last,
                high=book.last,
                low=book.last,
                close=book.last,
                volume=0,
                open_interest=book.open_interest,
                ts_start=float(bar_start),
                ts_end=float(bar_end),
            )
            state.last_volume = book.volume
            state.last_oi = book.open_interest
        else:
            # 更新现有 bar
            bar = state.current_bar
            bar.high = max(bar.high, book.last)
            bar.low = min(bar.low, book.last)
            bar.close = book.last
            bar.volume += max(0, book.volume - state.last_volume)
            bar.open_interest = book.open_interest
            state.last_volume = book.volume
            state.last_oi = book.open_interest

        return completed_bar

    def _complete_bar(self, product: str, bar: Bar) -> Bar:
        """完成一个 bar."""
        self._bars[product].append(bar)
        if self._on_bar_complete:
            self._on_bar_complete(bar)
        return bar

    def _force_complete_bar(self, product: str, ts: float) -> None:
        """强制完成当前 bar（用于主力切换）."""
        state = self._states.get(product)
        if state and state.current_bar:
            state.current_bar.ts_end = ts
            self._complete_bar(product, state.current_bar)
            state.current_bar = None

    def get_bars(self, product: str, count: int = 0) -> list[Bar]:
        """获取已完成的 bars.

        Args:
            product: 品种代码
            count: 返回数量，0 表示全部

        Returns:
            Bar 列表（时间正序）
        """
        bars = self._bars.get(product, [])
        if count > 0:
            return bars[-count:]
        return bars

    def clear(self, product: str | None = None) -> None:
        """清空 bars.

        Args:
            product: 品种代码，None 表示清空全部
        """
        if product:
            self._states.pop(product, None)
            self._bars.pop(product, None)
        else:
            self._states.clear()
            self._bars.clear()
