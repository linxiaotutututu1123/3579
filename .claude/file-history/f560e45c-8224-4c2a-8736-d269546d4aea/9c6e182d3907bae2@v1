"""
QualityChecker - 数据质量检测

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.6
V2 Scenarios: MKT.QUALITY.OUTLIER, MKT.QUALITY.GAP, MKT.QUALITY.DISORDER

军规级要求:
- 异常值检测（价格跳变多倍 tick_size → 标记异常）
- 行情间隙检测（长时间无 tick → stale）
- 时间乱序检测（时间倒退 → drop + 审计）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.market.quote_cache import BookTop
    from src.market.instrument_cache import InstrumentInfo


class QualityIssue(Enum):
    """数据质量问题类型."""

    OUTLIER = "outlier"  # 价格异常跳变
    GAP = "gap"  # 行情间隙
    DISORDER = "disorder"  # 时间乱序


@dataclass
class QualityEvent:
    """数据质量事件.

    Attributes:
        issue: 问题类型
        symbol: 合约代码
        ts: 时间戳
        details: 详细信息
    """

    issue: QualityIssue
    symbol: str
    ts: float
    details: dict


class QualityChecker:
    """数据质量检测器.

    V2 Scenarios:
    - MKT.QUALITY.OUTLIER: 异常值检测
    - MKT.QUALITY.GAP: 行情间隙检测
    - MKT.QUALITY.DISORDER: 时间乱序检测

    军规级要求:
    - 价格跳变多倍 tick_size → 标记异常
    - 长时间无 tick → stale
    - 时间倒退 → drop + 审计
    """

    def __init__(
        self,
        outlier_ticks_threshold: int = 50,
        gap_threshold_ms: float = 5000.0,
        on_quality_event: Callable[[QualityEvent], None] | None = None,
    ) -> None:
        """初始化检测器.

        Args:
            outlier_ticks_threshold: 异常值阈值（tick_size 倍数）
            gap_threshold_ms: 间隙阈值（毫秒）
            on_quality_event: 质量事件回调
        """
        self._outlier_ticks_threshold = outlier_ticks_threshold
        self._gap_threshold_ms = gap_threshold_ms
        self._on_quality_event = on_quality_event

        # symbol -> last book
        self._last_books: dict[str, BookTop] = {}
        # symbol -> instrument info (for tick_size)
        self._instruments: dict[str, InstrumentInfo] = {}

    def register_instrument(self, info: InstrumentInfo) -> None:
        """注册合约信息.

        Args:
            info: 合约信息（用于获取 tick_size）
        """
        self._instruments[info.symbol] = info

    def check(self, book: BookTop) -> list[QualityEvent]:
        """检查行情数据质量.

        Args:
            book: L1 盘口数据

        Returns:
            质量事件列表
        """
        events: list[QualityEvent] = []
        symbol = book.symbol
        last_book = self._last_books.get(symbol)

        if last_book:
            # 检查时间乱序
            disorder_event = self._check_disorder(book, last_book)
            if disorder_event:
                events.append(disorder_event)
                # 乱序数据不更新缓存，直接返回
                return events

            # 检查价格异常
            outlier_event = self._check_outlier(book, last_book)
            if outlier_event:
                events.append(outlier_event)

            # 检查行情间隙
            gap_event = self._check_gap(book, last_book)
            if gap_event:
                events.append(gap_event)

        # 更新缓存
        self._last_books[symbol] = book

        # 触发回调
        for event in events:
            if self._on_quality_event:
                self._on_quality_event(event)

        return events

    def _check_outlier(self, book: BookTop, last_book: BookTop) -> QualityEvent | None:
        """检查价格异常.

        V2 Scenario: MKT.QUALITY.OUTLIER
        """
        symbol = book.symbol
        instrument = self._instruments.get(symbol)

        if not instrument or last_book.last <= 0:
            return None

        tick_size = instrument.tick_size
        if tick_size <= 0:
            return None

        price_change = abs(book.last - last_book.last)
        ticks_change = price_change / tick_size

        if ticks_change > self._outlier_ticks_threshold:
            return QualityEvent(
                issue=QualityIssue.OUTLIER,
                symbol=symbol,
                ts=book.ts,
                details={
                    "last_price": last_book.last,
                    "new_price": book.last,
                    "price_change": price_change,
                    "ticks_change": ticks_change,
                    "threshold": self._outlier_ticks_threshold,
                },
            )
        return None

    def _check_gap(self, book: BookTop, last_book: BookTop) -> QualityEvent | None:
        """检查行情间隙.

        V2 Scenario: MKT.QUALITY.GAP
        """
        # 计算时间差（自动检测单位）
        if book.ts > 1e12:
            gap_ms = book.ts - last_book.ts
        else:
            gap_ms = (book.ts - last_book.ts) * 1000

        if gap_ms > self._gap_threshold_ms:
            return QualityEvent(
                issue=QualityIssue.GAP,
                symbol=book.symbol,
                ts=book.ts,
                details={
                    "last_ts": last_book.ts,
                    "new_ts": book.ts,
                    "gap_ms": gap_ms,
                    "threshold_ms": self._gap_threshold_ms,
                },
            )
        return None

    def _check_disorder(self, book: BookTop, last_book: BookTop) -> QualityEvent | None:
        """检查时间乱序.

        V2 Scenario: MKT.QUALITY.DISORDER
        """
        if book.ts < last_book.ts:
            return QualityEvent(
                issue=QualityIssue.DISORDER,
                symbol=book.symbol,
                ts=book.ts,
                details={
                    "last_ts": last_book.ts,
                    "new_ts": book.ts,
                    "message": "timestamp went backwards, data dropped",
                },
            )
        return None

    def clear(self, symbol: str | None = None) -> None:
        """清空状态.

        Args:
            symbol: 合约代码，None 表示清空全部
        """
        if symbol:
            self._last_books.pop(symbol, None)
        else:
            self._last_books.clear()
