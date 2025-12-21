"""
LiquidityGate - 流动性门控.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.9.1
V2 Scenario: EXEC.PROTECTION.LIQUIDITY

军规级要求:
- 检查买卖价差
- 检查盘口深度
- 阻止流动性不足时下单
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LiquidityCheckResult(Enum):
    """流动性检查结果."""

    PASS = "PASS"  # 通过
    SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"  # 价差过大
    DEPTH_TOO_THIN = "DEPTH_TOO_THIN"  # 深度不足
    NO_QUOTE = "NO_QUOTE"  # 无行情


@dataclass
class LiquidityConfig:
    """流动性配置.

    Attributes:
        max_spread_ticks: 最大价差（tick 数）
        min_bid_volume: 最小买一量
        min_ask_volume: 最小卖一量
        min_depth_volume: 最小盘口总深度
    """

    max_spread_ticks: int = 5
    min_bid_volume: int = 10
    min_ask_volume: int = 10
    min_depth_volume: int = 20


@dataclass
class Quote:
    """行情数据.

    Attributes:
        symbol: 合约代码
        bid: 买一价
        ask: 卖一价
        bid_volume: 买一量
        ask_volume: 卖一量
        tick_size: 最小变动价位
    """

    symbol: str
    bid: float
    ask: float
    bid_volume: int
    ask_volume: int
    tick_size: float

    def spread_ticks(self) -> int:
        """价差（tick 数）."""
        if self.tick_size <= 0:
            return 0
        return int(round((self.ask - self.bid) / self.tick_size))

    def total_depth(self) -> int:
        """盘口总深度."""
        return self.bid_volume + self.ask_volume


@dataclass
class LiquidityCheckOutput:
    """流动性检查输出.

    Attributes:
        result: 检查结果
        symbol: 合约代码
        spread_ticks: 价差（tick 数）
        bid_volume: 买一量
        ask_volume: 卖一量
        message: 详细信息
    """

    result: LiquidityCheckResult
    symbol: str = ""
    spread_ticks: int = 0
    bid_volume: int = 0
    ask_volume: int = 0
    message: str = ""

    def passed(self) -> bool:
        """是否通过."""
        return self.result == LiquidityCheckResult.PASS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "symbol": self.symbol,
            "spread_ticks": self.spread_ticks,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "message": self.message,
        }


class LiquidityGate:
    """流动性门控.

    V2 Scenario: EXEC.PROTECTION.LIQUIDITY

    检查:
    - 买卖价差不超过阈值
    - 盘口深度满足最小要求
    """

    def __init__(self, config: LiquidityConfig | None = None) -> None:
        """初始化流动性门控.

        Args:
            config: 流动性配置
        """
        self._config = config or LiquidityConfig()
        self._check_count = 0
        self._reject_count = 0

    @property
    def config(self) -> LiquidityConfig:
        """配置."""
        return self._config

    @property
    def check_count(self) -> int:
        """检查次数."""
        return self._check_count

    @property
    def reject_count(self) -> int:
        """拒绝次数."""
        return self._reject_count

    def check(self, quote: Quote | None) -> LiquidityCheckOutput:
        """检查流动性.

        V2 Scenario: EXEC.PROTECTION.LIQUIDITY

        Args:
            quote: 行情数据

        Returns:
            检查输出
        """
        self._check_count += 1

        # 无行情
        if quote is None:
            self._reject_count += 1
            return LiquidityCheckOutput(
                result=LiquidityCheckResult.NO_QUOTE,
                message="No quote available",
            )

        symbol = quote.symbol
        spread_ticks = quote.spread_ticks()
        bid_volume = quote.bid_volume
        ask_volume = quote.ask_volume

        # 检查价差
        if spread_ticks > self._config.max_spread_ticks:
            self._reject_count += 1
            return LiquidityCheckOutput(
                result=LiquidityCheckResult.SPREAD_TOO_WIDE,
                symbol=symbol,
                spread_ticks=spread_ticks,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                message=f"Spread {spread_ticks} > {self._config.max_spread_ticks} ticks",
            )

        # 检查深度
        if bid_volume < self._config.min_bid_volume:
            self._reject_count += 1
            return LiquidityCheckOutput(
                result=LiquidityCheckResult.DEPTH_TOO_THIN,
                symbol=symbol,
                spread_ticks=spread_ticks,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                message=f"Bid volume {bid_volume} < {self._config.min_bid_volume}",
            )

        if ask_volume < self._config.min_ask_volume:
            self._reject_count += 1
            return LiquidityCheckOutput(
                result=LiquidityCheckResult.DEPTH_TOO_THIN,
                symbol=symbol,
                spread_ticks=spread_ticks,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                message=f"Ask volume {ask_volume} < {self._config.min_ask_volume}",
            )

        total_depth = quote.total_depth()
        if total_depth < self._config.min_depth_volume:
            self._reject_count += 1
            return LiquidityCheckOutput(
                result=LiquidityCheckResult.DEPTH_TOO_THIN,
                symbol=symbol,
                spread_ticks=spread_ticks,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                message=f"Total depth {total_depth} < {self._config.min_depth_volume}",
            )

        # 通过
        return LiquidityCheckOutput(
            result=LiquidityCheckResult.PASS,
            symbol=symbol,
            spread_ticks=spread_ticks,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            message="Liquidity check passed",
        )

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计字典
        """
        return {
            "check_count": self._check_count,
            "reject_count": self._reject_count,
            "pass_rate": (
                (self._check_count - self._reject_count) / self._check_count
                if self._check_count > 0
                else 0.0
            ),
        }
