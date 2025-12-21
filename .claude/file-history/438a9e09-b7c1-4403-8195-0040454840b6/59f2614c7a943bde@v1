"""
ThrottleGate - 节流控制.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.9.3
V2 Scenario: EXEC.PROTECTION.THROTTLE

军规级要求:
- 限制每分钟订单数
- 限制订单最小间隔
- 防止过度交易
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThrottleCheckResult(Enum):
    """节流检查结果."""

    PASS = "PASS"  # 通过
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"  # 频率限制
    MIN_INTERVAL_VIOLATED = "MIN_INTERVAL_VIOLATED"  # 最小间隔违规


@dataclass
class ThrottleConfig:
    """节流配置.

    Attributes:
        max_orders_per_minute: 每分钟最大订单数
        min_interval_s: 最小订单间隔（秒）
        window_s: 统计窗口（秒）
    """

    max_orders_per_minute: int = 60
    min_interval_s: float = 1.0
    window_s: float = 60.0


@dataclass
class ThrottleCheckOutput:
    """节流检查输出.

    Attributes:
        result: 检查结果
        orders_in_window: 窗口内订单数
        time_since_last: 距上次订单时间（秒）
        wait_time_s: 需要等待的时间（秒）
        message: 详细信息
    """

    result: ThrottleCheckResult
    orders_in_window: int = 0
    time_since_last: float = 0.0
    wait_time_s: float = 0.0
    message: str = ""

    def passed(self) -> bool:
        """是否通过."""
        return self.result == ThrottleCheckResult.PASS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "orders_in_window": self.orders_in_window,
            "time_since_last": self.time_since_last,
            "wait_time_s": self.wait_time_s,
            "message": self.message,
        }


class ThrottleGate:
    """节流门控.

    V2 Scenario: EXEC.PROTECTION.THROTTLE

    检查:
    - 每分钟订单数不超过限制
    - 订单间隔不小于最小值
    """

    def __init__(self, config: ThrottleConfig | None = None) -> None:
        """初始化节流门控.

        Args:
            config: 节流配置
        """
        self._config = config or ThrottleConfig()
        self._order_times: deque[float] = deque()
        self._last_order_time: float = 0.0
        self._check_count = 0
        self._reject_count = 0

    @property
    def config(self) -> ThrottleConfig:
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

    def check(self, now: float | None = None) -> ThrottleCheckOutput:
        """检查节流.

        V2 Scenario: EXEC.PROTECTION.THROTTLE

        Args:
            now: 当前时间戳

        Returns:
            检查输出
        """
        if now is None:
            now = time.time()

        self._check_count += 1

        # 清理过期记录
        self._cleanup(now)

        # 计算窗口内订单数
        orders_in_window = len(self._order_times)

        # 计算距上次订单时间
        time_since_last = 0.0
        if self._last_order_time > 0:
            time_since_last = now - self._last_order_time

        # 检查频率限制
        if orders_in_window >= self._config.max_orders_per_minute:
            self._reject_count += 1
            wait_time = self._order_times[0] + self._config.window_s - now
            return ThrottleCheckOutput(
                result=ThrottleCheckResult.RATE_LIMIT_EXCEEDED,
                orders_in_window=orders_in_window,
                time_since_last=time_since_last,
                wait_time_s=max(0, wait_time),
                message=f"Rate limit: {orders_in_window} >= {self._config.max_orders_per_minute}/min",
            )

        # 检查最小间隔
        if self._last_order_time > 0 and time_since_last < self._config.min_interval_s:
            self._reject_count += 1
            wait_time = self._config.min_interval_s - time_since_last
            return ThrottleCheckOutput(
                result=ThrottleCheckResult.MIN_INTERVAL_VIOLATED,
                orders_in_window=orders_in_window,
                time_since_last=time_since_last,
                wait_time_s=max(0, wait_time),
                message=f"Min interval: {time_since_last:.2f}s < {self._config.min_interval_s}s",
            )

        # 通过
        return ThrottleCheckOutput(
            result=ThrottleCheckResult.PASS,
            orders_in_window=orders_in_window,
            time_since_last=time_since_last,
            wait_time_s=0.0,
            message="Throttle check passed",
        )

    def record_order(self, now: float | None = None) -> None:
        """记录订单.

        在订单成功提交后调用。

        Args:
            now: 当前时间戳
        """
        if now is None:
            now = time.time()

        self._order_times.append(now)
        self._last_order_time = now

    def check_and_record(self, now: float | None = None) -> ThrottleCheckOutput:
        """检查并记录.

        如果检查通过，自动记录订单。

        Args:
            now: 当前时间戳

        Returns:
            检查输出
        """
        if now is None:
            now = time.time()

        result = self.check(now)
        if result.passed():
            self.record_order(now)

        return result

    def _cleanup(self, now: float) -> None:
        """清理过期记录.

        Args:
            now: 当前时间戳
        """
        cutoff = now - self._config.window_s
        while self._order_times and self._order_times[0] < cutoff:
            self._order_times.popleft()

    def get_remaining_capacity(self, now: float | None = None) -> int:
        """获取剩余容量.

        Args:
            now: 当前时间戳

        Returns:
            剩余可下订单数
        """
        if now is None:
            now = time.time()

        self._cleanup(now)
        return max(0, self._config.max_orders_per_minute - len(self._order_times))

    def get_next_available_time(self, now: float | None = None) -> float:
        """获取下一个可用时间.

        Args:
            now: 当前时间戳

        Returns:
            下一个可下单的时间戳
        """
        if now is None:
            now = time.time()

        # 检查频率限制
        self._cleanup(now)
        if len(self._order_times) >= self._config.max_orders_per_minute:
            return self._order_times[0] + self._config.window_s

        # 检查最小间隔
        if self._last_order_time > 0:
            next_by_interval = self._last_order_time + self._config.min_interval_s
            if next_by_interval > now:
                return next_by_interval

        return now

    def reset(self) -> None:
        """重置节流器."""
        self._order_times.clear()
        self._last_order_time = 0.0

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
            "orders_in_window": len(self._order_times),
            "remaining_capacity": self.get_remaining_capacity(),
        }
