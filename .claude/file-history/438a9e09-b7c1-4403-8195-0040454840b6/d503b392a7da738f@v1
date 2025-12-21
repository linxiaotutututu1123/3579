"""
RetryPolicy - 重试策略.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.5
V2 Scenario: EXEC.RETRY.BACKOFF

军规级要求:
- 指数退避
- 最大重试次数限制
- 重试间隔可配置
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RetryReason(Enum):
    """重试原因."""

    ACK_TIMEOUT = "ACK_TIMEOUT"  # Ack 超时
    FILL_TIMEOUT = "FILL_TIMEOUT"  # Fill 超时
    REJECTED = "REJECTED"  # 被拒绝
    NETWORK_ERROR = "NETWORK_ERROR"  # 网络错误
    MANUAL = "MANUAL"  # 手动重试


class RepriceMode(Enum):
    """追价模式."""

    TO_BEST = "TO_BEST"  # 追到对手价
    TO_BEST_PLUS_TICK = "TO_BEST_PLUS_TICK"  # 追到对手价+1tick
    TO_CROSS = "TO_CROSS"  # 越过对手价


@dataclass
class RetryConfig:
    """重试配置.

    Attributes:
        max_retries: 最大重试次数
        base_delay_s: 基础延迟（秒）
        max_delay_s: 最大延迟（秒）
        backoff_factor: 退避因子
        reprice_mode: 追价模式
    """

    max_retries: int = 3
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    backoff_factor: float = 2.0
    reprice_mode: RepriceMode = RepriceMode.TO_BEST


@dataclass
class RetryState:
    """重试状态.

    Attributes:
        local_id: 本地订单 ID
        retry_count: 已重试次数
        last_retry_at: 上次重试时间
        next_retry_at: 下次重试时间
        reason: 重试原因
        original_price: 原始价格
        new_price: 新价格
    """

    local_id: str
    retry_count: int = 0
    last_retry_at: float = 0.0
    next_retry_at: float = 0.0
    reason: RetryReason | None = None
    original_price: float = 0.0
    new_price: float = 0.0

    def can_retry(self, max_retries: int) -> bool:
        """是否可以重试.

        Args:
            max_retries: 最大重试次数

        Returns:
            是否可以重试
        """
        return self.retry_count < max_retries

    def is_ready(self, now: float | None = None) -> bool:
        """是否可以执行重试.

        Args:
            now: 当前时间戳

        Returns:
            是否可以执行
        """
        if now is None:
            now = time.time()
        return now >= self.next_retry_at


class RetryPolicy:
    """重试策略.

    V2 Scenario: EXEC.RETRY.BACKOFF

    支持:
    - 指数退避
    - 最大重试次数
    - 追价模式
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """初始化重试策略.

        Args:
            config: 重试配置
        """
        self._config = config or RetryConfig()
        self._states: dict[str, RetryState] = {}

    @property
    def config(self) -> RetryConfig:
        """重试配置."""
        return self._config

    def calculate_delay(self, retry_count: int) -> float:
        """计算重试延迟（指数退避）.

        V2 Scenario: EXEC.RETRY.BACKOFF

        delay = min(base * factor^retry_count, max_delay)

        Args:
            retry_count: 当前重试次数

        Returns:
            延迟秒数
        """
        delay = self._config.base_delay_s * (self._config.backoff_factor ** retry_count)
        return min(delay, self._config.max_delay_s)

    def should_retry(self, local_id: str, reason: RetryReason) -> bool:
        """是否应该重试.

        Args:
            local_id: 本地订单 ID
            reason: 重试原因

        Returns:
            是否应该重试
        """
        state = self._states.get(local_id)
        if state is None:
            return True  # 首次重试

        return state.can_retry(self._config.max_retries)

    def register_retry(
        self,
        local_id: str,
        reason: RetryReason,
        original_price: float = 0.0,
        new_price: float = 0.0,
        now: float | None = None,
    ) -> RetryState:
        """注册重试.

        Args:
            local_id: 本地订单 ID
            reason: 重试原因
            original_price: 原始价格
            new_price: 新价格
            now: 当前时间戳

        Returns:
            重试状态
        """
        if now is None:
            now = time.time()

        state = self._states.get(local_id)
        if state is None:
            state = RetryState(local_id=local_id)
            self._states[local_id] = state

        state.retry_count += 1
        state.last_retry_at = now
        state.reason = reason
        state.original_price = original_price
        state.new_price = new_price

        delay = self.calculate_delay(state.retry_count - 1)
        state.next_retry_at = now + delay

        return state

    def get_state(self, local_id: str) -> RetryState | None:
        """获取重试状态.

        Args:
            local_id: 本地订单 ID

        Returns:
            重试状态或 None
        """
        return self._states.get(local_id)

    def get_retry_count(self, local_id: str) -> int:
        """获取重试次数.

        Args:
            local_id: 本地订单 ID

        Returns:
            重试次数
        """
        state = self._states.get(local_id)
        return state.retry_count if state else 0

    def clear_state(self, local_id: str) -> bool:
        """清除重试状态.

        Args:
            local_id: 本地订单 ID

        Returns:
            是否清除成功
        """
        return self._states.pop(local_id, None) is not None

    def get_ready_retries(self, now: float | None = None) -> list[RetryState]:
        """获取可执行的重试.

        Args:
            now: 当前时间戳

        Returns:
            可执行的重试状态列表
        """
        if now is None:
            now = time.time()

        ready = []
        for state in self._states.values():
            if state.is_ready(now) and state.can_retry(self._config.max_retries):
                ready.append(state)

        return ready

    def calculate_reprice(
        self,
        direction: str,
        original_price: float,
        bid: float,
        ask: float,
        tick_size: float,
    ) -> float:
        """计算追价价格.

        Args:
            direction: 方向 (BUY/SELL)
            original_price: 原始价格
            bid: 买一价
            ask: 卖一价
            tick_size: 最小变动价位

        Returns:
            新价格
        """
        mode = self._config.reprice_mode

        if direction == "BUY":
            if mode == RepriceMode.TO_BEST:
                return ask
            elif mode == RepriceMode.TO_BEST_PLUS_TICK:
                return ask + tick_size
            else:  # TO_CROSS
                return ask + tick_size * 2
        else:  # SELL
            if mode == RepriceMode.TO_BEST:
                return bid
            elif mode == RepriceMode.TO_BEST_PLUS_TICK:
                return bid - tick_size
            else:  # TO_CROSS
                return bid - tick_size * 2

    def __len__(self) -> int:
        """返回重试状态数量."""
        return len(self._states)

    def clear(self) -> None:
        """清空所有重试状态."""
        self._states.clear()
