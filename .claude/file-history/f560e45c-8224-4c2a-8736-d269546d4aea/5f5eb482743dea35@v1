"""
Subscriber - 行情订阅管理器

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.3
V2 Scenarios: MKT.SUBSCRIBER.DIFF_UPDATE

军规级要求:
- 订阅集差分更新（add = new - old, remove = old - new）
- 支持动态增减订阅
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    pass


class QuoteCallback(Protocol):
    """行情回调协议."""

    def __call__(self, symbol: str, data: dict) -> None:
        """处理行情数据."""
        ...


@dataclass
class SubscriptionDiff:
    """订阅差分.

    Attributes:
        add: 需要新增订阅的合约
        remove: 需要取消订阅的合约
    """

    add: set[str]
    remove: set[str]


class Subscriber:
    """行情订阅管理器.

    V2 Scenario: MKT.SUBSCRIBER.DIFF_UPDATE

    军规级要求:
    - 订阅集差分更新
    - add = new - old
    - remove = old - new
    """

    def __init__(
        self,
        on_subscribe: Callable[[set[str]], None] | None = None,
        on_unsubscribe: Callable[[set[str]], None] | None = None,
    ) -> None:
        """初始化订阅管理器.

        Args:
            on_subscribe: 订阅回调（接收新增的合约集合）
            on_unsubscribe: 取消订阅回调（接收移除的合约集合）
        """
        self._current_set: set[str] = set()
        self._on_subscribe = on_subscribe
        self._on_unsubscribe = on_unsubscribe
        self._callbacks: dict[str, list[QuoteCallback]] = {}

    @property
    def current_subscriptions(self) -> set[str]:
        """当前订阅集合."""
        return self._current_set.copy()

    def update(self, new_set: set[str]) -> SubscriptionDiff:
        """更新订阅集合.

        V2 Scenario: MKT.SUBSCRIBER.DIFF_UPDATE

        Args:
            new_set: 新的订阅集合

        Returns:
            订阅差分
        """
        add = new_set - self._current_set
        remove = self._current_set - new_set

        diff = SubscriptionDiff(add=add, remove=remove)

        # 执行订阅操作
        if add and self._on_subscribe:
            self._on_subscribe(add)

        if remove and self._on_unsubscribe:
            self._on_unsubscribe(remove)
            # 清理移除合约的回调
            for symbol in remove:
                self._callbacks.pop(symbol, None)

        self._current_set = new_set.copy()
        return diff

    def subscribe(self, symbols: set[str]) -> SubscriptionDiff:
        """增量订阅.

        Args:
            symbols: 需要订阅的合约集合

        Returns:
            订阅差分
        """
        new_set = self._current_set | symbols
        return self.update(new_set)

    def unsubscribe(self, symbols: set[str]) -> SubscriptionDiff:
        """增量取消订阅.

        Args:
            symbols: 需要取消订阅的合约集合

        Returns:
            订阅差分
        """
        new_set = self._current_set - symbols
        return self.update(new_set)

    def register_callback(self, symbol: str, callback: QuoteCallback) -> None:
        """注册行情回调.

        Args:
            symbol: 合约代码
            callback: 回调函数
        """
        if symbol not in self._callbacks:
            self._callbacks[symbol] = []
        self._callbacks[symbol].append(callback)

    def dispatch(self, symbol: str, data: dict) -> None:
        """分发行情数据.

        Args:
            symbol: 合约代码
            data: 行情数据
        """
        for callback in self._callbacks.get(symbol, []):
            callback(symbol, data)

    def clear(self) -> None:
        """清空所有订阅."""
        if self._current_set and self._on_unsubscribe:
            self._on_unsubscribe(self._current_set)
        self._current_set.clear()
        self._callbacks.clear()

    def __len__(self) -> int:
        """返回当前订阅数量."""
        return len(self._current_set)
