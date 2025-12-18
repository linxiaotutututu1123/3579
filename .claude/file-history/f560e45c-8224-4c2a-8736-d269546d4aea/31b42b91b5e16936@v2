"""
QuoteCache - L1 行情缓存 + stale 检测

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.3
V2 Scenarios: MKT.STALE.SOFT, MKT.STALE.HARD

军规级要求:
- 软 stale 检测（QUOTE_STALE_MS 超时后标记）
- 硬 stale 检测（QUOTE_HARD_STALE_MS 超时后执行禁止开仓）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass

# 配置常量（来自 V3PRO_UPGRADE_PLAN 第 18 章）
QUOTE_STALE_MS: float = 3000.0
QUOTE_HARD_STALE_MS: float = 10000.0


@dataclass
class BookTop:
    """L1 盘口数据.

    Attributes:
        symbol: 合约代码
        bid: 买一价
        ask: 卖一价
        bid_vol: 买一量
        ask_vol: 卖一量
        last: 最新价
        volume: 成交量
        open_interest: 持仓量
        ts: 时间戳（Unix epoch 毫秒或秒）
    """

    symbol: str
    bid: float
    ask: float
    bid_vol: int
    ask_vol: int
    last: float
    volume: int
    open_interest: int
    ts: float

    @property
    def mid(self) -> float:
        """中间价."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last

    @property
    def spread(self) -> float:
        """买卖价差."""
        if self.bid > 0 and self.ask > 0:
            return self.ask - self.bid
        return 0.0

    @property
    def spread_bps(self) -> float:
        """买卖价差（基点）."""
        mid = self.mid
        if mid > 0:
            return self.spread / mid * 10000
        return 0.0


class QuoteCache:
    """L1 行情缓存.

    V2 Scenarios:
    - MKT.STALE.SOFT: 软 stale 检测
    - MKT.STALE.HARD: 硬 stale 检测

    军规级要求:
    - QUOTE_STALE_MS 超时后标记 soft stale，策略可继续使用
    - QUOTE_HARD_STALE_MS 超时后标记 hard stale，执行禁止开仓
    """

    def __init__(
        self,
        stale_ms: float = QUOTE_STALE_MS,
        hard_stale_ms: float = QUOTE_HARD_STALE_MS,
    ) -> None:
        """初始化缓存.

        Args:
            stale_ms: 软 stale 阈值（毫秒）
            hard_stale_ms: 硬 stale 阈值（毫秒）
        """
        self._stale_ms = stale_ms
        self._hard_stale_ms = hard_stale_ms
        self._cache: dict[str, BookTop] = {}

    def update(self, book: BookTop) -> None:
        """更新行情.

        Args:
            book: L1 盘口数据
        """
        self._cache[book.symbol] = book

    def get(self, symbol: str) -> BookTop | None:
        """获取行情.

        Args:
            symbol: 合约代码

        Returns:
            L1 盘口数据，不存在返回 None
        """
        return self._cache.get(symbol)

    def is_stale(self, symbol: str, now_ts: float) -> bool:
        """软 stale 检测.

        V2 Scenario: MKT.STALE.SOFT

        Args:
            symbol: 合约代码
            now_ts: 当前时间戳（秒或毫秒，与 BookTop.ts 单位一致）

        Returns:
            True 表示 stale
        """
        book = self._cache.get(symbol)
        if book is None:
            return True

        # 自动检测单位（如果 now_ts > 1e12，认为是毫秒）
        age_ms = now_ts - book.ts if now_ts > 1e12 else (now_ts - book.ts) * 1000
        return age_ms > self._stale_ms

    def is_hard_stale(self, symbol: str, now_ts: float) -> bool:
        """硬 stale 检测.

        V2 Scenario: MKT.STALE.HARD

        Args:
            symbol: 合约代码
            now_ts: 当前时间戳

        Returns:
            True 表示 hard stale，应禁止开仓
        """
        book = self._cache.get(symbol)
        if book is None:
            return True

        # 自动检测单位
        age_ms = now_ts - book.ts if now_ts > 1e12 else (now_ts - book.ts) * 1000
        return age_ms > self._hard_stale_ms

    def get_stale_age_ms(self, symbol: str, now_ts: float) -> float:
        """获取行情过期时长.

        Args:
            symbol: 合约代码
            now_ts: 当前时间戳

        Returns:
            过期时长（毫秒），无数据返回 inf
        """
        book = self._cache.get(symbol)
        if book is None:
            return float("inf")

        if now_ts > 1e12:
            return now_ts - book.ts
        return (now_ts - book.ts) * 1000

    def all_symbols(self) -> list[str]:
        """获取所有缓存的合约代码."""
        return list(self._cache.keys())

    def get_stale_symbols(self, now_ts: float) -> list[str]:
        """获取所有 stale 的合约代码."""
        return [s for s in self._cache if self.is_stale(s, now_ts)]

    def get_hard_stale_symbols(self, now_ts: float) -> list[str]:
        """获取所有 hard stale 的合约代码."""
        return [s for s in self._cache if self.is_hard_stale(s, now_ts)]

    def clear(self) -> None:
        """清空缓存."""
        self._cache.clear()

    def __len__(self) -> int:
        """返回缓存的行情数量."""
        return len(self._cache)
