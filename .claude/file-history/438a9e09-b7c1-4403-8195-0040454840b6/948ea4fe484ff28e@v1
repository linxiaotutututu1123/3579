"""Position Aggregator (Military-Grade v3.0).

Provides multi-strategy position aggregation functionality.

Features:
- Strategy-level aggregation
- Symbol-level aggregation
- Time-series aggregation
- Snapshot creation

Example:
    aggregator = PositionAggregator()
    aggregator.add_snapshot(portfolio_manager.get_snapshot())
    history = aggregator.get_history()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AggregatedPosition:
    """Aggregated position across strategies.

    Attributes:
        symbol: Contract symbol
        net_quantity: Net position quantity
        gross_quantity: Gross position (sum of absolute values)
        strategies: List of strategies holding this position
        avg_price: Weighted average price
        total_pnl: Total P&L
    """

    symbol: str
    net_quantity: int
    gross_quantity: int
    strategies: list[str]
    avg_price: float
    total_pnl: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "net_quantity": self.net_quantity,
            "gross_quantity": self.gross_quantity,
            "strategies": self.strategies,
            "avg_price": self.avg_price,
            "total_pnl": self.total_pnl,
        }


@dataclass
class PositionSnapshot:
    """Point-in-time position snapshot.

    Attributes:
        ts: Timestamp
        positions: Aggregated positions
        total_pnl: Total P&L at snapshot time
        metadata: Additional metadata
    """

    ts: float
    positions: list[AggregatedPosition]
    total_pnl: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ts": self.ts,
            "positions": [p.to_dict() for p in self.positions],
            "total_pnl": self.total_pnl,
            "metadata": self.metadata,
        }


class PositionAggregator:
    """Aggregates positions across strategies and time."""

    def __init__(self, max_history: int = 1000) -> None:
        """Initialize aggregator.

        Args:
            max_history: Maximum number of snapshots to keep
        """
        self._max_history = max_history
        self._snapshots: list[PositionSnapshot] = []

    def add_snapshot(
        self, portfolio_data: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> PositionSnapshot:
        """Add a position snapshot.

        Args:
            portfolio_data: Portfolio snapshot data
            metadata: Additional metadata

        Returns:
            Created snapshot
        """
        positions = self._aggregate_positions(portfolio_data)
        total_pnl = portfolio_data.get("total_realized_pnl", 0.0) + portfolio_data.get(
            "total_unrealized_pnl", 0.0
        )

        snapshot = PositionSnapshot(
            ts=time.time(),
            positions=positions,
            total_pnl=total_pnl,
            metadata=metadata or {},
        )

        self._snapshots.append(snapshot)

        # Trim history
        if len(self._snapshots) > self._max_history:
            self._snapshots = self._snapshots[-self._max_history :]

        return snapshot

    def _aggregate_positions(
        self, portfolio_data: dict[str, Any]
    ) -> list[AggregatedPosition]:
        """Aggregate positions by symbol.

        Args:
            portfolio_data: Portfolio snapshot data

        Returns:
            List of aggregated positions
        """
        positions_data = portfolio_data.get("positions", [])

        # Group by symbol
        by_symbol: dict[str, list[dict[str, Any]]] = {}
        for pos in positions_data:
            symbol = pos.get("symbol", "")
            if symbol not in by_symbol:
                by_symbol[symbol] = []
            by_symbol[symbol].append(pos)

        # Aggregate
        aggregated: list[AggregatedPosition] = []
        for symbol, pos_list in by_symbol.items():
            net_qty = sum(p.get("quantity", 0) for p in pos_list)
            gross_qty = sum(abs(p.get("quantity", 0)) for p in pos_list)
            strategies = list({p.get("strategy", "") for p in pos_list})

            # Weighted average price
            total_value = sum(
                abs(p.get("quantity", 0)) * p.get("avg_price", 0.0) for p in pos_list
            )
            avg_price = total_value / gross_qty if gross_qty > 0 else 0.0

            # Total P&L
            total_pnl = sum(
                p.get("realized_pnl", 0.0) + p.get("unrealized_pnl", 0.0)
                for p in pos_list
            )

            aggregated.append(
                AggregatedPosition(
                    symbol=symbol,
                    net_quantity=net_qty,
                    gross_quantity=gross_qty,
                    strategies=strategies,
                    avg_price=avg_price,
                    total_pnl=total_pnl,
                )
            )

        return aggregated

    def get_history(self, limit: int | None = None) -> list[PositionSnapshot]:
        """Get snapshot history.

        Args:
            limit: Maximum number of snapshots to return (None = all)

        Returns:
            List of snapshots (newest last)
        """
        if limit is None:
            return list(self._snapshots)
        return self._snapshots[-limit:]

    def get_latest(self) -> PositionSnapshot | None:
        """Get latest snapshot.

        Returns:
            Latest snapshot or None
        """
        return self._snapshots[-1] if self._snapshots else None

    def get_pnl_series(self) -> list[tuple[float, float]]:
        """Get P&L time series.

        Returns:
            List of (timestamp, pnl) tuples
        """
        return [(s.ts, s.total_pnl) for s in self._snapshots]

    def clear(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()

    @property
    def snapshot_count(self) -> int:
        """Number of snapshots stored."""
        return len(self._snapshots)
