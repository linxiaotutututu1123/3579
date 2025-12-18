"""经验回放缓冲区模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致)

V4PRO Scenarios:
- K31: RL.BUFFER.DETERMINISTIC - 缓冲区采样确定性
- K32: RL.BUFFER.PRIORITY - 优先级回放
- K33: RL.BUFFER.ROLLOUT - Rollout缓冲区
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.strategy.rl.base import RLTransition


@dataclass
class BufferConfig:
    """缓冲区配置."""

    capacity: int = 100_000
    batch_size: int = 64
    seed: int = 42
    # M7: 确定性采样
    deterministic: bool = True


class ReplayBuffer:
    """经验回放缓冲区 (K31 确定性).

    基础的均匀采样回放缓冲区，支持确定性采样。
    """

    def __init__(self, config: BufferConfig) -> None:
        """初始化缓冲区.

        Args:
            config: 缓冲区配置
        """
        self.config = config
        self._buffer: list[RLTransition] = []
        self._position = 0

        # M7: 确定性随机数生成器
        if config.deterministic:
            self._rng = np.random.RandomState(config.seed)
        else:
            self._rng = np.random.RandomState()

    def push(self, transition: RLTransition) -> None:
        """添加转移记录.

        Args:
            transition: 状态转移
        """
        if len(self._buffer) < self.config.capacity:
            self._buffer.append(transition)
        else:
            self._buffer[self._position] = transition
        self._position = (self._position + 1) % self.config.capacity

    def sample(
        self, batch_size: int | None = None
    ) -> list[RLTransition]:
        """采样批次 (K31 确定性).

        Args:
            batch_size: 批次大小

        Returns:
            转移记录列表
        """
        batch_size = batch_size or self.config.batch_size
        indices = self._rng.choice(
            len(self._buffer), batch_size, replace=False
        )
        return [self._buffer[i] for i in indices]

    def __len__(self) -> int:
        """获取缓冲区大小."""
        return len(self._buffer)

    def is_ready(self) -> bool:
        """检查是否有足够样本."""
        return len(self._buffer) >= self.config.batch_size

    def clear(self) -> None:
        """清空缓冲区."""
        self._buffer.clear()
        self._position = 0

    def get_buffer_hash(self) -> str:
        """获取缓冲区哈希 (M7).

        Returns:
            缓冲区内容哈希
        """
        if not self._buffer:
            return "empty"
        # 只哈希最近的100个转移
        recent = self._buffer[-100:]
        hashes = [t.state_hash for t in recent]
        return hashlib.sha256("".join(hashes).encode()).hexdigest()[:16]


@dataclass
class PriorityConfig(BufferConfig):
    """优先级缓冲区配置."""

    alpha: float = 0.6  # 优先级指数
    beta: float = 0.4  # 重要性采样指数
    beta_increment: float = 0.001  # beta递增


class PrioritizedReplayBuffer:
    """优先级经验回放缓冲区 (K32).

    基于TD误差的优先级采样。
    """

    def __init__(self, config: PriorityConfig) -> None:
        """初始化优先级缓冲区.

        Args:
            config: 缓冲区配置
        """
        self.config = config
        self._buffer: list[RLTransition] = []
        self._priorities: list[float] = []
        self._position = 0
        self._beta = config.beta

        # M7: 确定性随机数生成器
        if config.deterministic:
            self._rng = np.random.RandomState(config.seed)
        else:
            self._rng = np.random.RandomState()

    def push(
        self, transition: RLTransition, priority: float | None = None
    ) -> None:
        """添加转移记录.

        Args:
            transition: 状态转移
            priority: 初始优先级
        """
        max_priority = max(self._priorities) if self._priorities else 1.0
        priority = priority or max_priority

        if len(self._buffer) < self.config.capacity:
            self._buffer.append(transition)
            self._priorities.append(priority)
        else:
            self._buffer[self._position] = transition
            self._priorities[self._position] = priority

        self._position = (self._position + 1) % self.config.capacity

    def sample(
        self, batch_size: int | None = None
    ) -> tuple[list[RLTransition], NDArray[np.float32], list[int]]:
        """优先级采样 (K32).

        Args:
            batch_size: 批次大小

        Returns:
            (转移列表, 重要性权重, 索引列表)
        """
        batch_size = batch_size or self.config.batch_size

        # 计算采样概率
        priorities = np.array(self._priorities, dtype=np.float32)
        probs = priorities ** self.config.alpha
        probs /= probs.sum()

        # 采样
        indices = self._rng.choice(
            len(self._buffer), batch_size, replace=False, p=probs
        )

        # 计算重要性采样权重
        n = len(self._buffer)
        weights = (n * probs[indices]) ** (-self._beta)
        weights /= weights.max()
        weights = weights.astype(np.float32)

        # 更新beta
        self._beta = min(1.0, self._beta + self.config.beta_increment)

        return (
            [self._buffer[i] for i in indices],
            weights,
            indices.tolist(),
        )

    def update_priorities(
        self, indices: list[int], priorities: list[float]
    ) -> None:
        """更新优先级.

        Args:
            indices: 索引列表
            priorities: 新优先级列表
        """
        for idx, priority in zip(indices, priorities, strict=True):
            self._priorities[idx] = priority + 1e-6  # 避免零优先级

    def __len__(self) -> int:
        """获取缓冲区大小."""
        return len(self._buffer)

    def is_ready(self) -> bool:
        """检查是否有足够样本."""
        return len(self._buffer) >= self.config.batch_size


@dataclass
class RolloutConfig:
    """Rollout缓冲区配置."""

    buffer_size: int = 2048
    gamma: float = 0.99
    gae_lambda: float = 0.95
    seed: int = 42


class RolloutBuffer:
    """Rollout缓冲区 (K33).

    用于PPO等on-policy算法的轨迹存储。
    """

    def __init__(self, config: RolloutConfig) -> None:
        """初始化Rollout缓冲区.

        Args:
            config: 缓冲区配置
        """
        self.config = config
        self._states: list[NDArray[np.float32]] = []
        self._actions: list[int] = []
        self._rewards: list[float] = []
        self._values: list[float] = []
        self._log_probs: list[float] = []
        self._dones: list[bool] = []

        # 计算后的优势和回报
        self._advantages: NDArray[np.float32] | None = None
        self._returns: NDArray[np.float32] | None = None

        # M7: 确定性
        self._rng = np.random.RandomState(config.seed)

    def push(
        self,
        state: NDArray[np.float32],
        action: int,
        reward: float,
        value: float,
        log_prob: float,
        done: bool,
    ) -> None:
        """添加一步数据.

        Args:
            state: 状态
            action: 动作
            reward: 奖励
            value: 状态价值
            log_prob: 动作对数概率
            done: 是否结束
        """
        self._states.append(state)
        self._actions.append(action)
        self._rewards.append(reward)
        self._values.append(value)
        self._log_probs.append(log_prob)
        self._dones.append(done)

    def compute_returns_and_advantages(
        self, last_value: float
    ) -> None:
        """计算回报和GAE优势 (K33).

        Args:
            last_value: 最后状态的价值估计
        """
        n = len(self._rewards)
        self._advantages = np.zeros(n, dtype=np.float32)
        self._returns = np.zeros(n, dtype=np.float32)

        gae = 0.0
        for t in reversed(range(n)):
            if t == n - 1:
                next_value = last_value
                next_non_terminal = 1.0 - float(self._dones[t])
            else:
                next_value = self._values[t + 1]
                next_non_terminal = 1.0 - float(self._dones[t])

            delta = (
                self._rewards[t]
                + self.config.gamma * next_value * next_non_terminal
                - self._values[t]
            )
            gae = (
                delta
                + self.config.gamma
                * self.config.gae_lambda
                * next_non_terminal
                * gae
            )
            self._advantages[t] = gae
            self._returns[t] = gae + self._values[t]

    def get_batches(
        self, batch_size: int
    ) -> list[dict[str, NDArray[np.float32] | NDArray[np.int64]]]:
        """获取小批次数据 (K33 确定性).

        Args:
            batch_size: 批次大小

        Returns:
            批次数据列表
        """
        if self._advantages is None or self._returns is None:
            raise ValueError("必须先调用 compute_returns_and_advantages")

        n = len(self._states)
        indices = np.arange(n)
        self._rng.shuffle(indices)

        batches = []
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_indices = indices[start:end]

            batch = {
                "states": np.array(
                    [self._states[i] for i in batch_indices],
                    dtype=np.float32,
                ),
                "actions": np.array(
                    [self._actions[i] for i in batch_indices],
                    dtype=np.int64,
                ),
                "old_log_probs": np.array(
                    [self._log_probs[i] for i in batch_indices],
                    dtype=np.float32,
                ),
                "advantages": self._advantages[batch_indices],
                "returns": self._returns[batch_indices],
            }
            batches.append(batch)

        return batches

    def clear(self) -> None:
        """清空缓冲区."""
        self._states.clear()
        self._actions.clear()
        self._rewards.clear()
        self._values.clear()
        self._log_probs.clear()
        self._dones.clear()
        self._advantages = None
        self._returns = None

    def __len__(self) -> int:
        """获取缓冲区大小."""
        return len(self._states)

    def is_full(self) -> bool:
        """检查是否已满."""
        return len(self._states) >= self.config.buffer_size
