"""
OrderContext - 订单标识映射.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.1
V2 Scenario: EXEC.ID.MAPPING

军规级要求:
- local_id 系统内唯一
- order_ref/order_sys_id 映射完整
- front_id/session_id 会话标识
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderContext:
    """订单上下文 - 订单标识映射.

    V2 Scenario: EXEC.ID.MAPPING

    Attributes:
        local_id: 本地订单 ID（系统生成，UUID）
        symbol: 合约代码
        direction: 方向 (BUY/SELL)
        offset: 开平 (OPEN/CLOSE/CLOSE_TODAY)
        qty: 数量
        price: 价格
        order_ref: CTP 订单引用（place_order 返回）
        order_sys_id: 交易所系统号（OnRtnOrder 返回）
        front_id: CTP 前置 ID
        session_id: CTP 会话 ID
        created_at: 创建时间戳
        extra: 额外信息
    """

    symbol: str
    direction: str
    offset: str
    qty: int
    price: float
    local_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_ref: str | None = None
    order_sys_id: str | None = None
    front_id: int | None = None
    session_id: int | None = None
    created_at: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def set_order_ref(self, order_ref: str) -> None:
        """设置订单引用.

        Args:
            order_ref: CTP 订单引用
        """
        self.order_ref = order_ref

    def set_order_sys_id(self, order_sys_id: str) -> None:
        """设置交易所系统号.

        Args:
            order_sys_id: 交易所系统号
        """
        self.order_sys_id = order_sys_id

    def set_session_info(self, front_id: int, session_id: int) -> None:
        """设置会话信息.

        Args:
            front_id: CTP 前置 ID
            session_id: CTP 会话 ID
        """
        self.front_id = front_id
        self.session_id = session_id

    def has_order_ref(self) -> bool:
        """是否有订单引用."""
        return self.order_ref is not None

    def has_order_sys_id(self) -> bool:
        """是否有交易所系统号."""
        return self.order_sys_id is not None

    def can_cancel_by_sys_id(self) -> bool:
        """是否可通过系统号撤单（优先级 1）."""
        return self.order_sys_id is not None

    def can_cancel_by_ref(self) -> bool:
        """是否可通过订单引用撤单（优先级 2）."""
        return self.order_ref is not None and self.front_id is not None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "local_id": self.local_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "offset": self.offset,
            "qty": self.qty,
            "price": self.price,
            "order_ref": self.order_ref,
            "order_sys_id": self.order_sys_id,
            "front_id": self.front_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
        }


class OrderContextRegistry:
    """订单上下文注册表.

    维护 local_id → OrderContext 的映射，
    以及 order_ref/order_sys_id → local_id 的反向映射。
    """

    def __init__(self) -> None:
        """初始化注册表."""
        self._contexts: dict[str, OrderContext] = {}
        self._ref_to_local: dict[str, str] = {}
        self._sys_id_to_local: dict[str, str] = {}

    def register(self, ctx: OrderContext) -> None:
        """注册订单上下文.

        Args:
            ctx: 订单上下文
        """
        self._contexts[ctx.local_id] = ctx

    def update_order_ref(self, local_id: str, order_ref: str) -> bool:
        """更新订单引用映射.

        Args:
            local_id: 本地订单 ID
            order_ref: CTP 订单引用

        Returns:
            是否更新成功
        """
        if local_id not in self._contexts:
            return False

        ctx = self._contexts[local_id]
        ctx.set_order_ref(order_ref)
        self._ref_to_local[order_ref] = local_id
        return True

    def update_order_sys_id(self, local_id: str, order_sys_id: str) -> bool:
        """更新交易所系统号映射.

        Args:
            local_id: 本地订单 ID
            order_sys_id: 交易所系统号

        Returns:
            是否更新成功
        """
        if local_id not in self._contexts:
            return False

        ctx = self._contexts[local_id]
        ctx.set_order_sys_id(order_sys_id)
        self._sys_id_to_local[order_sys_id] = local_id
        return True

    def get_by_local_id(self, local_id: str) -> OrderContext | None:
        """通过本地 ID 获取上下文.

        Args:
            local_id: 本地订单 ID

        Returns:
            订单上下文或 None
        """
        return self._contexts.get(local_id)

    def get_by_order_ref(self, order_ref: str) -> OrderContext | None:
        """通过订单引用获取上下文.

        Args:
            order_ref: CTP 订单引用

        Returns:
            订单上下文或 None
        """
        local_id = self._ref_to_local.get(order_ref)
        if local_id is None:
            return None
        return self._contexts.get(local_id)

    def get_by_order_sys_id(self, order_sys_id: str) -> OrderContext | None:
        """通过交易所系统号获取上下文.

        Args:
            order_sys_id: 交易所系统号

        Returns:
            订单上下文或 None
        """
        local_id = self._sys_id_to_local.get(order_sys_id)
        if local_id is None:
            return None
        return self._contexts.get(local_id)

    def remove(self, local_id: str) -> bool:
        """移除订单上下文.

        Args:
            local_id: 本地订单 ID

        Returns:
            是否移除成功
        """
        ctx = self._contexts.pop(local_id, None)
        if ctx is None:
            return False

        if ctx.order_ref:
            self._ref_to_local.pop(ctx.order_ref, None)
        if ctx.order_sys_id:
            self._sys_id_to_local.pop(ctx.order_sys_id, None)
        return True

    def __len__(self) -> int:
        """返回注册的订单数量."""
        return len(self._contexts)

    def get_all(self) -> list[OrderContext]:
        """获取所有订单上下文."""
        return list(self._contexts.values())
