"""
TimeoutManager - 超时管理.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.5
V2 Scenarios:
- EXEC.TIMEOUT.ACK: Ack 超时处理
- EXEC.TIMEOUT.FILL: Fill 超时处理

军规级要求:
- 超时检测必须精准
- 超时事件必须触发 FSM 转移
- 超时配置可调
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class TimeoutType(Enum):
    """超时类型."""

    ACK = "ACK"  # Ack 超时
    FILL = "FILL"  # Fill 超时
    CANCEL = "CANCEL"  # Cancel 超时


@dataclass
class TimeoutConfig:
    """超时配置.

    Attributes:
        ack_timeout_s: Ack 超时（秒）
        fill_timeout_s: Fill 超时（秒）
        cancel_timeout_s: Cancel 超时（秒）
    """

    ack_timeout_s: float = 5.0
    fill_timeout_s: float = 30.0
    cancel_timeout_s: float = 10.0


@dataclass
class TimeoutEntry:
    """超时条目.

    Attributes:
        local_id: 本地订单 ID
        timeout_type: 超时类型
        deadline: 截止时间戳
        created_at: 创建时间戳
    """

    local_id: str
    timeout_type: TimeoutType
    deadline: float
    created_at: float = field(default_factory=time.time)

    def is_expired(self, now: float | None = None) -> bool:
        """是否已超时.

        Args:
            now: 当前时间戳（默认使用 time.time()）

        Returns:
            是否已超时
        """
        if now is None:
            now = time.time()
        return now >= self.deadline

    def remaining_s(self, now: float | None = None) -> float:
        """剩余时间（秒）.

        Args:
            now: 当前时间戳

        Returns:
            剩余秒数（可能为负）
        """
        if now is None:
            now = time.time()
        return self.deadline - now


class TimeoutManager:
    """超时管理器.

    V2 Scenarios:
    - EXEC.TIMEOUT.ACK: Ack 超时处理
    - EXEC.TIMEOUT.FILL: Fill 超时处理

    管理订单的各类超时，支持:
    - 注册超时
    - 取消超时
    - 检查已超时的订单
    """

    def __init__(
        self,
        config: TimeoutConfig | None = None,
        on_timeout: Callable[[str, TimeoutType], None] | None = None,
    ) -> None:
        """初始化超时管理器.

        Args:
            config: 超时配置
            on_timeout: 超时回调 (local_id, timeout_type)
        """
        self._config = config or TimeoutConfig()
        self._on_timeout = on_timeout
        self._entries: dict[tuple[str, TimeoutType], TimeoutEntry] = {}

    @property
    def config(self) -> TimeoutConfig:
        """超时配置."""
        return self._config

    def register_ack_timeout(self, local_id: str, now: float | None = None) -> TimeoutEntry:
        """注册 Ack 超时.

        V2 Scenario: EXEC.TIMEOUT.ACK

        Args:
            local_id: 本地订单 ID
            now: 当前时间戳

        Returns:
            超时条目
        """
        if now is None:
            now = time.time()

        entry = TimeoutEntry(
            local_id=local_id,
            timeout_type=TimeoutType.ACK,
            deadline=now + self._config.ack_timeout_s,
            created_at=now,
        )
        self._entries[(local_id, TimeoutType.ACK)] = entry
        return entry

    def register_fill_timeout(self, local_id: str, now: float | None = None) -> TimeoutEntry:
        """注册 Fill 超时.

        V2 Scenario: EXEC.TIMEOUT.FILL

        Args:
            local_id: 本地订单 ID
            now: 当前时间戳

        Returns:
            超时条目
        """
        if now is None:
            now = time.time()

        entry = TimeoutEntry(
            local_id=local_id,
            timeout_type=TimeoutType.FILL,
            deadline=now + self._config.fill_timeout_s,
            created_at=now,
        )
        self._entries[(local_id, TimeoutType.FILL)] = entry
        return entry

    def register_cancel_timeout(self, local_id: str, now: float | None = None) -> TimeoutEntry:
        """注册 Cancel 超时.

        Args:
            local_id: 本地订单 ID
            now: 当前时间戳

        Returns:
            超时条目
        """
        if now is None:
            now = time.time()

        entry = TimeoutEntry(
            local_id=local_id,
            timeout_type=TimeoutType.CANCEL,
            deadline=now + self._config.cancel_timeout_s,
            created_at=now,
        )
        self._entries[(local_id, TimeoutType.CANCEL)] = entry
        return entry

    def cancel_timeout(self, local_id: str, timeout_type: TimeoutType) -> bool:
        """取消超时.

        Args:
            local_id: 本地订单 ID
            timeout_type: 超时类型

        Returns:
            是否取消成功
        """
        key = (local_id, timeout_type)
        return self._entries.pop(key, None) is not None

    def cancel_all_for_order(self, local_id: str) -> int:
        """取消订单的所有超时.

        Args:
            local_id: 本地订单 ID

        Returns:
            取消的超时数量
        """
        count = 0
        for tt in TimeoutType:
            if self.cancel_timeout(local_id, tt):
                count += 1
        return count

    def check_expired(self, now: float | None = None) -> list[TimeoutEntry]:
        """检查已超时的条目.

        Args:
            now: 当前时间戳

        Returns:
            已超时的条目列表
        """
        if now is None:
            now = time.time()

        expired = []
        for entry in list(self._entries.values()):
            if entry.is_expired(now):
                expired.append(entry)
                self._entries.pop((entry.local_id, entry.timeout_type), None)

                if self._on_timeout:
                    self._on_timeout(entry.local_id, entry.timeout_type)

        return expired

    def get_entry(self, local_id: str, timeout_type: TimeoutType) -> TimeoutEntry | None:
        """获取超时条目.

        Args:
            local_id: 本地订单 ID
            timeout_type: 超时类型

        Returns:
            超时条目或 None
        """
        return self._entries.get((local_id, timeout_type))

    def has_timeout(self, local_id: str, timeout_type: TimeoutType) -> bool:
        """是否有超时条目.

        Args:
            local_id: 本地订单 ID
            timeout_type: 超时类型

        Returns:
            是否存在
        """
        return (local_id, timeout_type) in self._entries

    def __len__(self) -> int:
        """返回超时条目数量."""
        return len(self._entries)

    def clear(self) -> None:
        """清空所有超时条目."""
        self._entries.clear()
