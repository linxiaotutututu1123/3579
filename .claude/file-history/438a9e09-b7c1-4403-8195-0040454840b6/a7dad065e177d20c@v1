"""
FatFingerGate - 胖手指检查.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.9.2
V2 Scenario: EXEC.PROTECTION.FATFINGER

军规级要求:
- 检查订单数量上限
- 检查订单金额上限
- 检查价格偏离度
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FatFingerCheckResult(Enum):
    """胖手指检查结果."""

    PASS = "PASS"  # 通过
    QTY_TOO_LARGE = "QTY_TOO_LARGE"  # 数量过大
    NOTIONAL_TOO_LARGE = "NOTIONAL_TOO_LARGE"  # 金额过大
    PRICE_DEVIATION = "PRICE_DEVIATION"  # 价格偏离
    INVALID_ORDER = "INVALID_ORDER"  # 无效订单


@dataclass
class FatFingerConfig:
    """胖手指配置.

    Attributes:
        max_qty: 最大数量
        max_notional: 最大金额
        max_price_deviation: 最大价格偏离（比例，如 0.05 表示 5%）
    """

    max_qty: int = 100
    max_notional: float = 1_000_000.0
    max_price_deviation: float = 0.05


@dataclass
class OrderInput:
    """订单输入.

    Attributes:
        symbol: 合约代码
        direction: 方向 (BUY/SELL)
        qty: 数量
        price: 价格
        multiplier: 合约乘数
        reference_price: 参考价格（如最新价）
    """

    symbol: str
    direction: str
    qty: int
    price: float
    multiplier: float = 1.0
    reference_price: float = 0.0

    def notional(self) -> float:
        """名义金额."""
        return self.qty * self.price * self.multiplier

    def price_deviation(self) -> float:
        """价格偏离度.

        Returns:
            偏离比例（可正可负）
        """
        if self.reference_price <= 0:
            return 0.0
        return (self.price - self.reference_price) / self.reference_price


@dataclass
class FatFingerCheckOutput:
    """胖手指检查输出.

    Attributes:
        result: 检查结果
        symbol: 合约代码
        qty: 数量
        notional: 名义金额
        price_deviation: 价格偏离度
        message: 详细信息
    """

    result: FatFingerCheckResult
    symbol: str = ""
    qty: int = 0
    notional: float = 0.0
    price_deviation: float = 0.0
    message: str = ""

    def passed(self) -> bool:
        """是否通过."""
        return self.result == FatFingerCheckResult.PASS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "symbol": self.symbol,
            "qty": self.qty,
            "notional": self.notional,
            "price_deviation": self.price_deviation,
            "message": self.message,
        }


class FatFingerGate:
    """胖手指门控.

    V2 Scenario: EXEC.PROTECTION.FATFINGER

    检查:
    - 订单数量不超过阈值
    - 订单金额不超过阈值
    - 价格偏离度在合理范围
    """

    def __init__(self, config: FatFingerConfig | None = None) -> None:
        """初始化胖手指门控.

        Args:
            config: 胖手指配置
        """
        self._config = config or FatFingerConfig()
        self._check_count = 0
        self._reject_count = 0

    @property
    def config(self) -> FatFingerConfig:
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

    def check(self, order: OrderInput) -> FatFingerCheckOutput:
        """检查订单.

        V2 Scenario: EXEC.PROTECTION.FATFINGER

        Args:
            order: 订单输入

        Returns:
            检查输出
        """
        self._check_count += 1

        symbol = order.symbol
        qty = order.qty
        notional = order.notional()
        price_deviation = order.price_deviation()

        # 检查数量
        if qty > self._config.max_qty:
            self._reject_count += 1
            return FatFingerCheckOutput(
                result=FatFingerCheckResult.QTY_TOO_LARGE,
                symbol=symbol,
                qty=qty,
                notional=notional,
                price_deviation=price_deviation,
                message=f"Qty {qty} > {self._config.max_qty}",
            )

        # 检查金额
        if notional > self._config.max_notional:
            self._reject_count += 1
            return FatFingerCheckOutput(
                result=FatFingerCheckResult.NOTIONAL_TOO_LARGE,
                symbol=symbol,
                qty=qty,
                notional=notional,
                price_deviation=price_deviation,
                message=f"Notional {notional:.2f} > {self._config.max_notional:.2f}",
            )

        # 检查价格偏离
        abs_deviation = abs(price_deviation)
        if abs_deviation > self._config.max_price_deviation:
            self._reject_count += 1
            return FatFingerCheckOutput(
                result=FatFingerCheckResult.PRICE_DEVIATION,
                symbol=symbol,
                qty=qty,
                notional=notional,
                price_deviation=price_deviation,
                message=f"Price deviation {abs_deviation:.2%} > {self._config.max_price_deviation:.2%}",
            )

        # 通过
        return FatFingerCheckOutput(
            result=FatFingerCheckResult.PASS,
            symbol=symbol,
            qty=qty,
            notional=notional,
            price_deviation=price_deviation,
            message="Fat finger check passed",
        )

    def check_batch(self, orders: list[OrderInput]) -> list[FatFingerCheckOutput]:
        """批量检查订单.

        Args:
            orders: 订单列表

        Returns:
            检查输出列表
        """
        return [self.check(order) for order in orders]

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
