"""
PositionTracker - 持仓追踪.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.8
V2 Scenarios:
- POS.TRACKER.TRADE_DRIVEN: trade-driven 更新
- POS.RECONCILE.PERIODIC: 定期对账
- POS.RECONCILE.AFTER_DISCONNECT: 断连后对账
- POS.RECONCILE.FAIL_ACTION: 对账失败动作

军规级要求:
- 持仓由 PositionTracker 唯一维护（军规 M6）
- 成交驱动更新
- 定期与柜台对账
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReconcileStatus(Enum):
    """对账状态."""

    MATCH = "MATCH"  # 匹配
    MISMATCH = "MISMATCH"  # 不匹配
    ERROR = "ERROR"  # 错误


@dataclass
class Position:
    """持仓.

    Attributes:
        symbol: 合约代码
        long_qty: 多头数量
        short_qty: 空头数量
        long_avg_cost: 多头均价
        short_avg_cost: 空头均价
        last_update: 最后更新时间
    """

    symbol: str
    long_qty: int = 0
    short_qty: int = 0
    long_avg_cost: float = 0.0
    short_avg_cost: float = 0.0
    last_update: float = field(default_factory=time.time)

    @property
    def net_qty(self) -> int:
        """净持仓."""
        return self.long_qty - self.short_qty

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "symbol": self.symbol,
            "long_qty": self.long_qty,
            "short_qty": self.short_qty,
            "net_qty": self.net_qty,
            "long_avg_cost": self.long_avg_cost,
            "short_avg_cost": self.short_avg_cost,
            "last_update": self.last_update,
        }


@dataclass
class Trade:
    """成交.

    Attributes:
        trade_id: 成交 ID
        order_local_id: 订单本地 ID
        symbol: 合约代码
        direction: 方向 (BUY/SELL)
        offset: 开平 (OPEN/CLOSE/CLOSE_TODAY)
        volume: 成交量
        price: 成交价
        ts: 时间戳
    """

    trade_id: str
    order_local_id: str
    symbol: str
    direction: str
    offset: str
    volume: int
    price: float
    ts: float = field(default_factory=time.time)


@dataclass
class ReconcileResult:
    """对账结果.

    Attributes:
        status: 对账状态
        timestamp: 对账时间
        local_positions: 本地持仓
        broker_positions: 柜台持仓
        mismatches: 不匹配列表 [(symbol, local_qty, broker_qty)]
        error: 错误信息
    """

    status: ReconcileStatus
    timestamp: float = field(default_factory=time.time)
    local_positions: dict[str, int] = field(default_factory=dict)
    broker_positions: dict[str, int] = field(default_factory=dict)
    mismatches: list[tuple[str, int, int]] = field(default_factory=list)
    error: str | None = None

    def is_match(self) -> bool:
        """是否匹配."""
        return self.status == ReconcileStatus.MATCH


class PositionTracker:
    """持仓追踪器.

    V2 Scenarios:
    - POS.TRACKER.TRADE_DRIVEN: trade-driven 更新
    - POS.RECONCILE.PERIODIC: 定期对账
    - POS.RECONCILE.AFTER_DISCONNECT: 断连后对账
    - POS.RECONCILE.FAIL_ACTION: 对账失败动作

    军规 M6: 持仓由 PositionTracker 唯一维护
    """

    def __init__(
        self,
        on_mismatch: Callable[[ReconcileResult], None] | None = None,
    ) -> None:
        """初始化持仓追踪器.

        Args:
            on_mismatch: 对账不匹配回调
        """
        self._positions: dict[str, Position] = {}
        self._on_mismatch = on_mismatch
        self._last_reconcile: float = 0.0
        self._trade_count: int = 0

    def on_trade(self, trade: Trade) -> None:
        """处理成交.

        V2 Scenario: POS.TRACKER.TRADE_DRIVEN

        成交驱动持仓更新：
        - BUY + OPEN: 增加多头
        - BUY + CLOSE: 减少空头
        - SELL + OPEN: 增加空头
        - SELL + CLOSE: 减少多头

        Args:
            trade: 成交
        """
        symbol = trade.symbol
        if symbol not in self._positions:
            self._positions[symbol] = Position(symbol=symbol)

        pos = self._positions[symbol]

        if trade.direction == "BUY":
            if trade.offset == "OPEN":
                # 买开：增加多头
                total_cost = (
                    pos.long_avg_cost * pos.long_qty + trade.price * trade.volume
                )
                pos.long_qty += trade.volume
                if pos.long_qty > 0:
                    pos.long_avg_cost = total_cost / pos.long_qty
            else:
                # 买平（平空）：减少空头
                pos.short_qty = max(0, pos.short_qty - trade.volume)
        elif trade.offset == "OPEN":
            # 卖开：增加空头
            total_cost = pos.short_avg_cost * pos.short_qty + trade.price * trade.volume
            pos.short_qty += trade.volume
            if pos.short_qty > 0:
                pos.short_avg_cost = total_cost / pos.short_qty
        else:
            # 卖平（平多）：减少多头
            pos.long_qty = max(0, pos.long_qty - trade.volume)

        pos.last_update = trade.ts
        self._trade_count += 1

    def get_position(self, symbol: str) -> Position | None:
        """获取持仓.

        Args:
            symbol: 合约代码

        Returns:
            持仓或 None
        """
        return self._positions.get(symbol)

    def get_net_position(self, symbol: str) -> int:
        """获取净持仓.

        Args:
            symbol: 合约代码

        Returns:
            净持仓（多为正，空为负）
        """
        pos = self._positions.get(symbol)
        return pos.net_qty if pos else 0

    def get_all_positions(self) -> dict[str, Position]:
        """获取所有持仓.

        Returns:
            {symbol: Position}
        """
        return dict(self._positions)

    def get_net_positions(self) -> dict[str, int]:
        """获取所有净持仓.

        Returns:
            {symbol: net_qty}
        """
        return {s: p.net_qty for s, p in self._positions.items() if p.net_qty != 0}

    def reconcile(self, broker_positions: dict[str, int]) -> ReconcileResult:
        """对账.

        V2 Scenarios:
        - POS.RECONCILE.PERIODIC: 定期对账
        - POS.RECONCILE.AFTER_DISCONNECT: 断连后对账

        比较本地持仓与柜台持仓。

        Args:
            broker_positions: 柜台持仓 {symbol: net_qty}

        Returns:
            对账结果
        """
        local_positions = self.get_net_positions()
        mismatches: list[tuple[str, int, int]] = []

        # 检查所有 symbol
        all_symbols = set(local_positions.keys()) | set(broker_positions.keys())
        for symbol in all_symbols:
            local_qty = local_positions.get(symbol, 0)
            broker_qty = broker_positions.get(symbol, 0)

            if local_qty != broker_qty:
                mismatches.append((symbol, local_qty, broker_qty))

        status = ReconcileStatus.MATCH if not mismatches else ReconcileStatus.MISMATCH
        result = ReconcileResult(
            status=status,
            local_positions=local_positions,
            broker_positions=broker_positions,
            mismatches=mismatches,
        )

        self._last_reconcile = result.timestamp

        # 对账失败回调
        if status == ReconcileStatus.MISMATCH and self._on_mismatch:
            self._on_mismatch(result)

        return result

    def sync_from_broker(self, broker_positions: dict[str, int]) -> None:
        """从柜台同步持仓.

        V2 Scenario: POS.RECONCILE.FAIL_ACTION

        用于冷启动恢复或对账失败后同步。

        Args:
            broker_positions: 柜台持仓 {symbol: net_qty}
        """
        self._positions.clear()

        for symbol, net_qty in broker_positions.items():
            if net_qty == 0:
                continue

            pos = Position(symbol=symbol)
            if net_qty > 0:
                pos.long_qty = net_qty
            else:
                pos.short_qty = abs(net_qty)

            self._positions[symbol] = pos

    def clear(self) -> None:
        """清空持仓."""
        self._positions.clear()

    @property
    def last_reconcile(self) -> float:
        """上次对账时间."""
        return self._last_reconcile

    @property
    def trade_count(self) -> int:
        """成交数量."""
        return self._trade_count

    def should_reconcile(self, interval_s: float, now: float | None = None) -> bool:
        """是否应该对账.

        V2 Scenario: POS.RECONCILE.PERIODIC

        Args:
            interval_s: 对账间隔（秒）
            now: 当前时间戳

        Returns:
            是否应该对账
        """
        if now is None:
            now = time.time()

        return (now - self._last_reconcile) >= interval_s

    def __len__(self) -> int:
        """返回有持仓的合约数量."""
        return len([p for p in self._positions.values() if p.net_qty != 0])

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "positions": {s: p.to_dict() for s, p in self._positions.items()},
            "net_positions": self.get_net_positions(),
            "last_reconcile": self._last_reconcile,
            "trade_count": self._trade_count,
        }
