"""
PnLAttribution - PnL 归因

V3PRO+ Platform Component - Phase 1
V2 Scenarios: AUDIT.PNL.ATTRIBUTION

军规级要求:
- 按策略/品种/时段归因
- 支持实时和批量计算
- 可审计追溯
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PnLRecord:
    """PnL 记录.

    Attributes:
        ts: 时间戳
        run_id: 运行 ID
        exec_id: 执行 ID
        strategy_id: 策略 ID
        symbol: 合约代码
        realized_pnl: 已实现盈亏
        unrealized_pnl: 未实现盈亏
        commission: 手续费
        slippage: 滑点成本
        net_pnl: 净盈亏
        position_qty: 持仓数量
        avg_cost: 平均成本
    """

    ts: float
    run_id: str
    exec_id: str
    strategy_id: str
    symbol: str
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0
    position_qty: int = 0
    avg_cost: float = 0.0

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "PNL"

    @property
    def total_pnl(self) -> float:
        """总盈亏."""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def gross_pnl(self) -> float:
        """毛盈亏（不含成本）."""
        return self.net_pnl + self.commission + self.slippage

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        data["total_pnl"] = self.total_pnl
        data["gross_pnl"] = self.gross_pnl
        return data


class PnLAttribution:
    """PnL 归因计算器.

    V2 Scenario: AUDIT.PNL.ATTRIBUTION

    按策略/品种/时段进行 PnL 归因。
    """

    def __init__(self, run_id: str, exec_id: str) -> None:
        """初始化归因器.

        Args:
            run_id: 运行 ID
            exec_id: 执行 ID
        """
        self._run_id = run_id
        self._exec_id = exec_id
        self._records: dict[tuple[str, str], PnLRecord] = {}  # (strategy_id, symbol) -> PnLRecord

    @property
    def run_id(self) -> str:
        """运行 ID."""
        return self._run_id

    @property
    def exec_id(self) -> str:
        """执行 ID."""
        return self._exec_id

    def update_realized(
        self,
        ts: float,
        strategy_id: str,
        symbol: str,
        realized_pnl: float,
        commission: float = 0.0,
        slippage: float = 0.0,
    ) -> PnLRecord:
        """更新已实现盈亏.

        Args:
            ts: 时间戳
            strategy_id: 策略 ID
            symbol: 合约代码
            realized_pnl: 已实现盈亏
            commission: 手续费
            slippage: 滑点成本

        Returns:
            更新后的 PnLRecord
        """
        key = (strategy_id, symbol)
        if key not in self._records:
            self._records[key] = PnLRecord(
                ts=ts,
                run_id=self._run_id,
                exec_id=self._exec_id,
                strategy_id=strategy_id,
                symbol=symbol,
            )

        record = self._records[key]
        record.ts = ts
        record.realized_pnl += realized_pnl
        record.commission += commission
        record.slippage += slippage
        record.net_pnl = record.realized_pnl - record.commission - record.slippage

        return record

    def update_unrealized(
        self,
        ts: float,
        strategy_id: str,
        symbol: str,
        unrealized_pnl: float,
        position_qty: int,
        avg_cost: float,
    ) -> PnLRecord:
        """更新未实现盈亏.

        Args:
            ts: 时间戳
            strategy_id: 策略 ID
            symbol: 合约代码
            unrealized_pnl: 未实现盈亏
            position_qty: 持仓数量
            avg_cost: 平均成本

        Returns:
            更新后的 PnLRecord
        """
        key = (strategy_id, symbol)
        if key not in self._records:
            self._records[key] = PnLRecord(
                ts=ts,
                run_id=self._run_id,
                exec_id=self._exec_id,
                strategy_id=strategy_id,
                symbol=symbol,
            )

        record = self._records[key]
        record.ts = ts
        record.unrealized_pnl = unrealized_pnl
        record.position_qty = position_qty
        record.avg_cost = avg_cost

        return record

    def get_record(self, strategy_id: str, symbol: str) -> PnLRecord | None:
        """获取 PnL 记录.

        Args:
            strategy_id: 策略 ID
            symbol: 合约代码

        Returns:
            PnLRecord 或 None
        """
        return self._records.get((strategy_id, symbol))

    def get_all_records(self) -> list[PnLRecord]:
        """获取所有 PnL 记录.

        Returns:
            所有 PnLRecord 列表
        """
        return list(self._records.values())

    def get_by_strategy(self, strategy_id: str) -> list[PnLRecord]:
        """按策略获取 PnL 记录.

        Args:
            strategy_id: 策略 ID

        Returns:
            该策略的所有 PnLRecord
        """
        return [r for r in self._records.values() if r.strategy_id == strategy_id]

    def get_by_symbol(self, symbol: str) -> list[PnLRecord]:
        """按合约获取 PnL 记录.

        Args:
            symbol: 合约代码

        Returns:
            该合约的所有 PnLRecord
        """
        return [r for r in self._records.values() if r.symbol == symbol]

    def get_total_pnl(self) -> float:
        """获取总 PnL.

        Returns:
            所有记录的总 PnL
        """
        return sum(r.total_pnl for r in self._records.values())

    def get_strategy_pnl(self, strategy_id: str) -> float:
        """获取策略 PnL.

        Args:
            strategy_id: 策略 ID

        Returns:
            该策略的总 PnL
        """
        return sum(r.total_pnl for r in self.get_by_strategy(strategy_id))

    def clear(self) -> None:
        """清空所有记录."""
        self._records.clear()
