"""投资组合管理器 (军规级 v3.0).

提供多策略持仓管理功能。

功能特性:
- 按合约和策略追踪持仓
- 净持仓聚合
- 盈亏追踪
- 持仓限额控制

示例:
    manager = PortfolioManager(max_position_per_symbol=100)
    manager.update_position("AO2501", 10, "calendar_arb")
    net_position = manager.get_net_position("AO2501")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PositionEntry:
    """单个持仓条目.

    属性:
        symbol: 合约代码
        quantity: 持仓数量 (正数=多头, 负数=空头)
        strategy: 持有该持仓的策略
        avg_price: 平均入场价格
        realized_pnl: 已实现盈亏
        unrealized_pnl: 未实现盈亏
        updated_at: 最后更新时间戳
    """

    symbol: str
    quantity: int
    strategy: str
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "strategy": self.strategy,
            "avg_price": self.avg_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "updated_at": self.updated_at,
        }


@dataclass
class PortfolioConfig:
    """投资组合配置.

    属性:
        max_position_per_symbol: 每个合约最大持仓
        max_total_position: 总持仓最大值
        max_strategies: 最大策略数量
        enable_position_limits: 是否启用持仓限额控制
    """

    max_position_per_symbol: int = 100
    max_total_position: int = 1000
    max_strategies: int = 10
    enable_position_limits: bool = True


class PortfolioManager:
    """Portfolio-level position manager.

    Manages positions across multiple strategies and symbols,
    providing aggregation and limit enforcement.
    """

    def __init__(self, config: PortfolioConfig | None = None) -> None:
        """Initialize portfolio manager.

        Args:
            config: Portfolio configuration
        """
        self._config = config or PortfolioConfig()

        # Positions by (symbol, strategy)
        self._positions: dict[tuple[str, str], PositionEntry] = {}

        # Net positions by symbol
        self._net_positions: dict[str, int] = {}

        # P&L tracking
        self._total_realized_pnl: float = 0.0
        self._total_unrealized_pnl: float = 0.0

    def update_position(
        self,
        symbol: str,
        quantity: int,
        strategy: str,
        avg_price: float = 0.0,
    ) -> bool:
        """Update position for a symbol and strategy.

        Args:
            symbol: Contract symbol
            quantity: New position quantity
            strategy: Strategy name
            avg_price: Average entry price

        Returns:
            True if update successful, False if limit exceeded
        """
        # Check position limits
        if self._config.enable_position_limits:
            new_net = self._calculate_new_net(symbol, quantity, strategy)
            if abs(new_net) > self._config.max_position_per_symbol:
                return False

        # Update or create position entry
        key = (symbol, strategy)
        if key in self._positions:
            entry = self._positions[key]
            entry.quantity = quantity
            entry.avg_price = avg_price
            entry.updated_at = time.time()
        else:
            self._positions[key] = PositionEntry(
                symbol=symbol,
                quantity=quantity,
                strategy=strategy,
                avg_price=avg_price,
            )

        # Update net position
        self._recalculate_net_position(symbol)

        return True

    def _calculate_new_net(self, symbol: str, quantity: int, strategy: str) -> int:
        """Calculate new net position if update is applied.

        Args:
            symbol: Contract symbol
            quantity: New quantity
            strategy: Strategy name

        Returns:
            New net position
        """
        current_net = self._net_positions.get(symbol, 0)
        key = (symbol, strategy)
        current_qty = self._positions[key].quantity if key in self._positions else 0
        delta = quantity - current_qty
        return current_net + delta

    def _recalculate_net_position(self, symbol: str) -> None:
        """Recalculate net position for a symbol.

        Args:
            symbol: Contract symbol
        """
        net = 0
        for key, entry in self._positions.items():
            if key[0] == symbol:
                net += entry.quantity
        self._net_positions[symbol] = net

    def get_position(self, symbol: str, strategy: str) -> PositionEntry | None:
        """Get position for a symbol and strategy.

        Args:
            symbol: Contract symbol
            strategy: Strategy name

        Returns:
            Position entry or None
        """
        return self._positions.get((symbol, strategy))

    def get_net_position(self, symbol: str) -> int:
        """Get net position for a symbol across all strategies.

        Args:
            symbol: Contract symbol

        Returns:
            Net position quantity
        """
        return self._net_positions.get(symbol, 0)

    def get_all_positions(self) -> list[PositionEntry]:
        """Get all position entries.

        Returns:
            List of all positions
        """
        return list(self._positions.values())

    def get_positions_by_strategy(self, strategy: str) -> list[PositionEntry]:
        """Get all positions for a strategy.

        Args:
            strategy: Strategy name

        Returns:
            List of positions
        """
        return [entry for key, entry in self._positions.items() if key[1] == strategy]

    def get_positions_by_symbol(self, symbol: str) -> list[PositionEntry]:
        """Get all positions for a symbol.

        Args:
            symbol: Contract symbol

        Returns:
            List of positions
        """
        return [entry for key, entry in self._positions.items() if key[0] == symbol]

    def clear_position(self, symbol: str, strategy: str) -> None:
        """Clear position for a symbol and strategy.

        Args:
            symbol: Contract symbol
            strategy: Strategy name
        """
        key = (symbol, strategy)
        if key in self._positions:
            del self._positions[key]
            self._recalculate_net_position(symbol)

    def clear_all(self) -> None:
        """Clear all positions."""
        self._positions.clear()
        self._net_positions.clear()
        self._total_realized_pnl = 0.0
        self._total_unrealized_pnl = 0.0

    def update_pnl(
        self,
        symbol: str,
        strategy: str,
        realized: float = 0.0,
        unrealized: float = 0.0,
    ) -> None:
        """Update P&L for a position.

        Args:
            symbol: Contract symbol
            strategy: Strategy name
            realized: Realized P&L
            unrealized: Unrealized P&L
        """
        key = (symbol, strategy)
        if key in self._positions:
            entry = self._positions[key]
            self._total_realized_pnl += realized - entry.realized_pnl
            self._total_unrealized_pnl += unrealized - entry.unrealized_pnl
            entry.realized_pnl = realized
            entry.unrealized_pnl = unrealized

    @property
    def total_realized_pnl(self) -> float:
        """Total realized P&L."""
        return sum(e.realized_pnl for e in self._positions.values())

    @property
    def total_unrealized_pnl(self) -> float:
        """Total unrealized P&L."""
        return sum(e.unrealized_pnl for e in self._positions.values())

    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)."""
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def symbols(self) -> list[str]:
        """List of all symbols with positions."""
        return list(self._net_positions.keys())

    @property
    def strategies(self) -> list[str]:
        """List of all strategies with positions."""
        return list({key[1] for key in self._positions})

    def get_snapshot(self) -> dict[str, Any]:
        """Get portfolio snapshot for audit.

        Returns:
            Portfolio snapshot dictionary
        """
        return {
            "positions": [e.to_dict() for e in self._positions.values()],
            "net_positions": dict(self._net_positions),
            "total_realized_pnl": self.total_realized_pnl,
            "total_unrealized_pnl": self.total_unrealized_pnl,
            "symbols": self.symbols,
            "strategies": self.strategies,
        }
