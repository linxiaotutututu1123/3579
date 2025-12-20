"""
PairExecutor - 配对执行器.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.10.1
V2 Scenarios:
- PAIR.EXECUTOR.ATOMIC: 原子执行
- PAIR.ROLLBACK.ON_LEG_FAIL: 腿失败回滚
- PAIR.BREAKER.STOP_Z: Z 值熔断

军规级要求:
- 配对交易原子性
- 失败自动回滚
- 熔断保护
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.execution.pair.leg_manager import LegManager, LegStatus


if TYPE_CHECKING:
    from src.execution.auto.engine import AutoOrderEngine


class PairStatus(Enum):
    """配对状态."""

    PENDING = "PENDING"  # 待执行
    EXECUTING = "EXECUTING"  # 执行中
    COMPLETED = "COMPLETED"  # 完成
    PARTIAL = "PARTIAL"  # 部分完成
    ROLLING_BACK = "ROLLING_BACK"  # 回滚中
    ROLLED_BACK = "ROLLED_BACK"  # 已回滚
    FAILED = "FAILED"  # 失败
    BREAKER_STOPPED = "BREAKER_STOPPED"  # 熔断


@dataclass
class PairOrder:
    """配对订单.

    Attributes:
        near_symbol: 近腿合约
        far_symbol: 远腿合约
        near_direction: 近腿方向
        far_direction: 远腿方向
        qty: 数量
        near_price: 近腿价格
        far_price: 远腿价格
    """

    near_symbol: str
    far_symbol: str
    near_direction: str
    far_direction: str
    qty: int
    near_price: float = 0.0
    far_price: float = 0.0

    def spread(self) -> float:
        """价差."""
        return self.near_price - self.far_price


@dataclass
class PairResult:
    """配对结果.

    Attributes:
        pair_id: 配对 ID
        status: 状态
        near_filled: 近腿成交量
        far_filled: 远腿成交量
        near_avg_price: 近腿均价
        far_avg_price: 远腿均价
        realized_spread: 实际价差
        error: 错误信息
        created_at: 创建时间
        completed_at: 完成时间
    """

    pair_id: str
    status: PairStatus
    near_filled: int = 0
    far_filled: int = 0
    near_avg_price: float = 0.0
    far_avg_price: float = 0.0
    realized_spread: float = 0.0
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def is_complete(self) -> bool:
        """是否完成."""
        return self.status in (
            PairStatus.COMPLETED,
            PairStatus.ROLLED_BACK,
            PairStatus.FAILED,
            PairStatus.BREAKER_STOPPED,
        )

    def is_success(self) -> bool:
        """是否成功."""
        return self.status == PairStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "pair_id": self.pair_id,
            "status": self.status.value,
            "near_filled": self.near_filled,
            "far_filled": self.far_filled,
            "near_avg_price": self.near_avg_price,
            "far_avg_price": self.far_avg_price,
            "realized_spread": self.realized_spread,
            "error": self.error,
        }


@dataclass
class BreakerConfig:
    """熔断配置.

    Attributes:
        max_z_score: 最大 Z 值
        lookback_periods: 回看周期
        enabled: 是否启用
    """

    max_z_score: float = 3.0
    lookback_periods: int = 20
    enabled: bool = True


class PairExecutor:
    """配对执行器.

    V2 Scenarios:
    - PAIR.EXECUTOR.ATOMIC: 原子执行
    - PAIR.ROLLBACK.ON_LEG_FAIL: 腿失败回滚
    - PAIR.BREAKER.STOP_Z: Z 值熔断

    执行配对交易，保证原子性。
    """

    def __init__(
        self,
        engine: AutoOrderEngine | None = None,
        leg_manager: LegManager | None = None,
        breaker_config: BreakerConfig | None = None,
        on_rollback: Callable[[str, str], None] | None = None,
    ) -> None:
        """初始化配对执行器.

        Args:
            engine: 自动下单引擎
            leg_manager: 腿管理器
            breaker_config: 熔断配置
            on_rollback: 回滚回调 (pair_id, reason)
        """
        self._engine = engine
        self._leg_manager = leg_manager or LegManager()
        self._breaker_config = breaker_config or BreakerConfig()
        self._on_rollback = on_rollback

        self._results: dict[str, PairResult] = {}
        self._spread_history: list[float] = []

    @property
    def leg_manager(self) -> LegManager:
        """腿管理器."""
        return self._leg_manager

    @property
    def breaker_config(self) -> BreakerConfig:
        """熔断配置."""
        return self._breaker_config

    def execute(self, order: PairOrder) -> str:
        """执行配对交易.

        V2 Scenario: PAIR.EXECUTOR.ATOMIC

        Args:
            order: 配对订单

        Returns:
            配对 ID
        """
        pair_id = str(uuid.uuid4())

        # 检查熔断
        if self._check_breaker(order.spread()):
            result = PairResult(
                pair_id=pair_id,
                status=PairStatus.BREAKER_STOPPED,
                error="Z-score breaker triggered",
            )
            self._results[pair_id] = result
            return pair_id

        # 创建腿
        near_leg, far_leg = self._leg_manager.create_pair(
            pair_id=pair_id,
            near_symbol=order.near_symbol,
            far_symbol=order.far_symbol,
            near_direction=order.near_direction,
            far_direction=order.far_direction,
            qty=order.qty,
        )

        # 创建结果
        result = PairResult(
            pair_id=pair_id,
            status=PairStatus.EXECUTING,
        )
        self._results[pair_id] = result

        # 提交近腿
        if self._engine:
            from src.execution.auto.order_context import OrderContext

            near_ctx = OrderContext(
                symbol=order.near_symbol,
                direction=order.near_direction,
                offset="OPEN",
                qty=order.qty,
                price=order.near_price,
            )
            near_local_id = self._engine.submit(near_ctx)
            near_leg.order_local_id = near_local_id
            near_leg.status = LegStatus.SUBMITTED

            # 提交远腿
            far_ctx = OrderContext(
                symbol=order.far_symbol,
                direction=order.far_direction,
                offset="OPEN",
                qty=order.qty,
                price=order.far_price,
            )
            far_local_id = self._engine.submit(far_ctx)
            far_leg.order_local_id = far_local_id
            far_leg.status = LegStatus.SUBMITTED

        return pair_id

    def on_leg_fill(
        self, pair_id: str, leg_id: str, qty: int, price: float
    ) -> None:
        """处理腿成交.

        Args:
            pair_id: 配对 ID
            leg_id: 腿 ID
            qty: 成交数量
            price: 成交价格
        """
        self._leg_manager.update_leg(leg_id, qty, price)
        self._update_result(pair_id)

    def on_leg_fail(self, pair_id: str, leg_id: str, reason: str) -> None:
        """处理腿失败.

        V2 Scenario: PAIR.ROLLBACK.ON_LEG_FAIL

        Args:
            pair_id: 配对 ID
            leg_id: 腿 ID
            reason: 失败原因
        """
        self._leg_manager.set_leg_status(leg_id, LegStatus.FAILED)

        result = self._results.get(pair_id)
        if result is None:
            return

        # 检查是否需要回滚
        near_leg, far_leg = self._leg_manager.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return

        # 如果一腿成交另一腿失败，需要回滚
        if (near_leg.filled_qty > 0 and far_leg.status == LegStatus.FAILED) or (
            far_leg.filled_qty > 0 and near_leg.status == LegStatus.FAILED
        ):
            self._rollback(pair_id, reason)
        else:
            result.status = PairStatus.FAILED
            result.error = reason
            result.completed_at = time.time()

    def _rollback(self, pair_id: str, reason: str) -> None:
        """回滚配对交易.

        V2 Scenario: PAIR.ROLLBACK.ON_LEG_FAIL

        Args:
            pair_id: 配对 ID
            reason: 回滚原因
        """
        result = self._results.get(pair_id)
        if result is None:
            return

        result.status = PairStatus.ROLLING_BACK

        near_leg, far_leg = self._leg_manager.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return

        # 平掉已成交的腿
        if self._engine:
            from src.execution.auto.order_context import OrderContext

            if near_leg.filled_qty > 0:
                # 平近腿：反向操作
                close_direction = "SELL" if near_leg.direction == "BUY" else "BUY"
                close_ctx = OrderContext(
                    symbol=near_leg.symbol,
                    direction=close_direction,
                    offset="CLOSE",
                    qty=near_leg.filled_qty,
                    price=0.0,  # 市价
                )
                self._engine.submit(close_ctx)

            if far_leg.filled_qty > 0:
                # 平远腿：反向操作
                close_direction = "SELL" if far_leg.direction == "BUY" else "BUY"
                close_ctx = OrderContext(
                    symbol=far_leg.symbol,
                    direction=close_direction,
                    offset="CLOSE",
                    qty=far_leg.filled_qty,
                    price=0.0,  # 市价
                )
                self._engine.submit(close_ctx)

        result.status = PairStatus.ROLLED_BACK
        result.error = f"Rolled back: {reason}"
        result.completed_at = time.time()

        if self._on_rollback:
            self._on_rollback(pair_id, reason)

    def _update_result(self, pair_id: str) -> None:
        """更新配对结果.

        Args:
            pair_id: 配对 ID
        """
        result = self._results.get(pair_id)
        if result is None:
            return

        near_leg, far_leg = self._leg_manager.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return

        result.near_filled = near_leg.filled_qty
        result.far_filled = far_leg.filled_qty
        result.near_avg_price = near_leg.avg_price
        result.far_avg_price = far_leg.avg_price

        if near_leg.avg_price > 0 and far_leg.avg_price > 0:
            result.realized_spread = near_leg.avg_price - far_leg.avg_price
            self._spread_history.append(result.realized_spread)

        # 检查是否完成
        if self._leg_manager.is_pair_filled(pair_id):
            result.status = PairStatus.COMPLETED
            result.completed_at = time.time()
        elif self._leg_manager.is_pair_complete(pair_id):
            result.status = PairStatus.PARTIAL
            result.completed_at = time.time()

    def _check_breaker(self, current_spread: float) -> bool:
        """检查熔断.

        V2 Scenario: PAIR.BREAKER.STOP_Z

        Args:
            current_spread: 当前价差

        Returns:
            是否触发熔断
        """
        if not self._breaker_config.enabled:
            return False

        if len(self._spread_history) < self._breaker_config.lookback_periods:
            return False

        # 计算 Z 值
        recent = self._spread_history[-self._breaker_config.lookback_periods :]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)

        if variance <= 0:
            return False

        std: float = variance ** 0.5
        z_score: float = abs(current_spread - mean) / std

        return bool(z_score > self._breaker_config.max_z_score)

    def get_result(self, pair_id: str) -> PairResult | None:
        """获取配对结果.

        Args:
            pair_id: 配对 ID

        Returns:
            配对结果或 None
        """
        return self._results.get(pair_id)

    def get_active_pairs(self) -> list[str]:
        """获取活动配对.

        Returns:
            活动配对 ID 列表
        """
        return [
            pair_id
            for pair_id, result in self._results.items()
            if not result.is_complete()
        ]

    def check_imbalances(self) -> list[str]:
        """检查所有不平衡.

        V2 Scenario: PAIR.IMBALANCE.DETECT

        Returns:
            不平衡的配对 ID 列表
        """
        imbalances = self._leg_manager.get_all_imbalances()
        return [info.pair_id for info in imbalances]

    def auto_hedge(self, pair_id: str) -> str | None:
        """自动对冲.

        V2 Scenario: PAIR.AUTOHEDGE.DELTA_NEUTRAL

        Args:
            pair_id: 配对 ID

        Returns:
            对冲订单本地 ID 或 None
        """
        hedge_order = self._leg_manager.get_hedge_order(pair_id)
        if hedge_order is None:
            return None

        if self._engine is None:
            return None

        from src.execution.auto.order_context import OrderContext

        ctx = OrderContext(
            symbol=hedge_order["symbol"],
            direction=hedge_order["direction"],
            offset="OPEN",
            qty=hedge_order["qty"],
            price=0.0,  # 市价
        )

        return self._engine.submit(ctx)

    def __len__(self) -> int:
        """返回配对数量."""
        return len(self._results)
