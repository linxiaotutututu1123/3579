"""
LegManager - 腿管理器.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.10.2
V2 Scenarios:
- PAIR.IMBALANCE.DETECT: 腿不平衡检测
- PAIR.AUTOHEDGE.DELTA_NEUTRAL: 自动对冲

军规级要求:
- 跟踪每条腿的状态
- 检测腿不平衡
- 支持自动对冲
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LegStatus(Enum):
    """腿状态."""

    PENDING = "PENDING"  # 待执行
    SUBMITTED = "SUBMITTED"  # 已提交
    PARTIAL = "PARTIAL"  # 部分成交
    FILLED = "FILLED"  # 全部成交
    CANCELLED = "CANCELLED"  # 已撤销
    FAILED = "FAILED"  # 失败


@dataclass
class Leg:
    """配对交易的腿.

    Attributes:
        leg_id: 腿 ID
        pair_id: 配对 ID
        symbol: 合约代码
        direction: 方向 (BUY/SELL)
        target_qty: 目标数量
        filled_qty: 已成交数量
        avg_price: 平均价格
        status: 状态
        order_local_id: 订单本地 ID
        created_at: 创建时间
        filled_at: 成交时间
    """

    leg_id: str
    pair_id: str
    symbol: str
    direction: str
    target_qty: int
    filled_qty: int = 0
    avg_price: float = 0.0
    status: LegStatus = LegStatus.PENDING
    order_local_id: str | None = None
    created_at: float = field(default_factory=time.time)
    filled_at: float = 0.0

    def is_complete(self) -> bool:
        """是否完成."""
        return self.status in (LegStatus.FILLED, LegStatus.CANCELLED, LegStatus.FAILED)

    def is_filled(self) -> bool:
        """是否全部成交."""
        return self.status == LegStatus.FILLED

    def remaining_qty(self) -> int:
        """剩余数量."""
        return max(0, self.target_qty - self.filled_qty)

    def fill_ratio(self) -> float:
        """成交比例."""
        if self.target_qty == 0:
            return 0.0
        return self.filled_qty / self.target_qty

    def update_fill(self, qty: int, price: float) -> None:
        """更新成交.

        Args:
            qty: 成交数量
            price: 成交价格
        """
        if qty <= 0:
            return

        total_value = self.avg_price * self.filled_qty + price * qty
        self.filled_qty += qty

        if self.filled_qty > 0:
            self.avg_price = total_value / self.filled_qty

        if self.filled_qty >= self.target_qty:
            self.status = LegStatus.FILLED
            self.filled_at = time.time()
        else:
            self.status = LegStatus.PARTIAL

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "leg_id": self.leg_id,
            "pair_id": self.pair_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "target_qty": self.target_qty,
            "filled_qty": self.filled_qty,
            "remaining_qty": self.remaining_qty(),
            "avg_price": self.avg_price,
            "status": self.status.value,
            "fill_ratio": self.fill_ratio(),
        }


@dataclass
class ImbalanceInfo:
    """不平衡信息.

    Attributes:
        pair_id: 配对 ID
        near_leg: 近腿
        far_leg: 远腿
        imbalance_qty: 不平衡数量
        is_imbalanced: 是否不平衡
        threshold: 阈值
    """

    pair_id: str
    near_leg: Leg
    far_leg: Leg
    imbalance_qty: int
    is_imbalanced: bool
    threshold: int


class LegManager:
    """腿管理器.

    V2 Scenarios:
    - PAIR.IMBALANCE.DETECT: 腿不平衡检测
    - PAIR.AUTOHEDGE.DELTA_NEUTRAL: 自动对冲

    管理配对交易的两条腿，检测不平衡并触发对冲。
    """

    def __init__(self, imbalance_threshold: int = 10) -> None:
        """初始化腿管理器.

        Args:
            imbalance_threshold: 不平衡阈值（手数）
        """
        self._legs: dict[str, Leg] = {}
        self._pairs: dict[str, tuple[str, str]] = {}  # pair_id -> (near_leg_id, far_leg_id)
        self._imbalance_threshold = imbalance_threshold

    @property
    def imbalance_threshold(self) -> int:
        """不平衡阈值."""
        return self._imbalance_threshold

    def create_pair(
        self,
        pair_id: str,
        near_symbol: str,
        far_symbol: str,
        near_direction: str,
        far_direction: str,
        qty: int,
    ) -> tuple[Leg, Leg]:
        """创建配对.

        Args:
            pair_id: 配对 ID
            near_symbol: 近腿合约
            far_symbol: 远腿合约
            near_direction: 近腿方向
            far_direction: 远腿方向
            qty: 数量

        Returns:
            (近腿, 远腿)
        """
        near_leg = Leg(
            leg_id=f"{pair_id}_near",
            pair_id=pair_id,
            symbol=near_symbol,
            direction=near_direction,
            target_qty=qty,
        )

        far_leg = Leg(
            leg_id=f"{pair_id}_far",
            pair_id=pair_id,
            symbol=far_symbol,
            direction=far_direction,
            target_qty=qty,
        )

        self._legs[near_leg.leg_id] = near_leg
        self._legs[far_leg.leg_id] = far_leg
        self._pairs[pair_id] = (near_leg.leg_id, far_leg.leg_id)

        return near_leg, far_leg

    def get_leg(self, leg_id: str) -> Leg | None:
        """获取腿.

        Args:
            leg_id: 腿 ID

        Returns:
            腿或 None
        """
        return self._legs.get(leg_id)

    def get_pair_legs(self, pair_id: str) -> tuple[Leg | None, Leg | None]:
        """获取配对的两条腿.

        Args:
            pair_id: 配对 ID

        Returns:
            (近腿, 远腿) 或 (None, None)
        """
        leg_ids = self._pairs.get(pair_id)
        if leg_ids is None:
            return None, None

        near_leg_id, far_leg_id = leg_ids
        return self._legs.get(near_leg_id), self._legs.get(far_leg_id)

    def update_leg(self, leg_id: str, qty: int, price: float) -> bool:
        """更新腿成交.

        Args:
            leg_id: 腿 ID
            qty: 成交数量
            price: 成交价格

        Returns:
            是否更新成功
        """
        leg = self._legs.get(leg_id)
        if leg is None:
            return False

        leg.update_fill(qty, price)
        return True

    def set_leg_status(self, leg_id: str, status: LegStatus) -> bool:
        """设置腿状态.

        Args:
            leg_id: 腿 ID
            status: 状态

        Returns:
            是否设置成功
        """
        leg = self._legs.get(leg_id)
        if leg is None:
            return False

        leg.status = status
        return True

    def check_imbalance(self, pair_id: str) -> ImbalanceInfo | None:
        """检查不平衡.

        V2 Scenario: PAIR.IMBALANCE.DETECT

        Args:
            pair_id: 配对 ID

        Returns:
            不平衡信息或 None
        """
        near_leg, far_leg = self.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return None

        # 计算不平衡：近腿成交 - 远腿成交
        imbalance_qty = near_leg.filled_qty - far_leg.filled_qty
        is_imbalanced = abs(imbalance_qty) > self._imbalance_threshold

        return ImbalanceInfo(
            pair_id=pair_id,
            near_leg=near_leg,
            far_leg=far_leg,
            imbalance_qty=imbalance_qty,
            is_imbalanced=is_imbalanced,
            threshold=self._imbalance_threshold,
        )

    def get_hedge_order(self, pair_id: str) -> dict[str, Any] | None:
        """获取对冲订单.

        V2 Scenario: PAIR.AUTOHEDGE.DELTA_NEUTRAL

        当检测到不平衡时，生成对冲订单。

        Args:
            pair_id: 配对 ID

        Returns:
            对冲订单信息或 None
        """
        info = self.check_imbalance(pair_id)
        if info is None or not info.is_imbalanced:
            return None

        imbalance = info.imbalance_qty

        if imbalance > 0:
            # 近腿多了，需要补远腿
            return {
                "symbol": info.far_leg.symbol,
                "direction": info.far_leg.direction,
                "qty": abs(imbalance),
                "reason": "auto_hedge",
            }
        # 远腿多了，需要补近腿
        return {
            "symbol": info.near_leg.symbol,
            "direction": info.near_leg.direction,
            "qty": abs(imbalance),
            "reason": "auto_hedge",
        }

    def is_pair_complete(self, pair_id: str) -> bool:
        """配对是否完成.

        Args:
            pair_id: 配对 ID

        Returns:
            是否完成
        """
        near_leg, far_leg = self.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return False

        return near_leg.is_complete() and far_leg.is_complete()

    def is_pair_filled(self, pair_id: str) -> bool:
        """配对是否全部成交.

        Args:
            pair_id: 配对 ID

        Returns:
            是否全部成交
        """
        near_leg, far_leg = self.get_pair_legs(pair_id)
        if near_leg is None or far_leg is None:
            return False

        return near_leg.is_filled() and far_leg.is_filled()

    def get_all_imbalances(self) -> list[ImbalanceInfo]:
        """获取所有不平衡.

        Returns:
            不平衡信息列表
        """
        imbalances = []
        for pair_id in self._pairs:
            info = self.check_imbalance(pair_id)
            if info and info.is_imbalanced:
                imbalances.append(info)
        return imbalances

    def __len__(self) -> int:
        """返回配对数量."""
        return len(self._pairs)
