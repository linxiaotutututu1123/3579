"""强化学习基础模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致), M18(实验性门禁)

V4PRO Scenarios:
- K28: RL.BASE.DETERMINISTIC - RL推理确定性
- K29: RL.BASE.AUDIT_LOG - RL决策审计
- K30: RL.BASE.STATE_HASH - 状态哈希一致性
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict

import numpy as np
import torch
from numpy.typing import NDArray


class RLState(TypedDict):
    """RL状态字典."""

    features: NDArray[np.float32]  # 特征向量
    position: float  # 当前持仓
    pnl: float  # 当前盈亏
    step: int  # 当前步数


class RLAction(Enum):
    """RL动作枚举."""

    HOLD = 0  # 持有
    BUY = 1  # 买入
    SELL = 2  # 卖出


@dataclass
class RLReward:
    """RL奖励结构."""

    total: float  # 总奖励
    pnl_reward: float = 0.0  # 盈亏奖励
    risk_penalty: float = 0.0  # 风险惩罚
    cost_penalty: float = 0.0  # 成本惩罚
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证奖励结构."""
        # M3: 记录奖励分解审计
        self.metadata["reward_breakdown"] = {
            "pnl": self.pnl_reward,
            "risk": self.risk_penalty,
            "cost": self.cost_penalty,
        }


@dataclass
class RLTransition:
    """RL状态转移记录 (M3 审计)."""

    state: NDArray[np.float32]
    action: int
    reward: float
    next_state: NDArray[np.float32]
    done: bool
    info: dict[str, Any] = field(default_factory=dict)

    # M7: 状态哈希用于回放一致性验证
    state_hash: str = ""
    next_state_hash: str = ""

    def __post_init__(self) -> None:
        """计算状态哈希."""
        if not self.state_hash:
            self.state_hash = self._compute_hash(self.state)
        if not self.next_state_hash:
            self.next_state_hash = self._compute_hash(self.next_state)

    @staticmethod
    def _compute_hash(arr: NDArray[np.float32]) -> str:
        """计算数组哈希 (K30)."""
        return hashlib.sha256(arr.tobytes()).hexdigest()[:16]


@dataclass
class RLConfig:
    """RL配置 (带军规约束)."""

    # 模型配置
    state_dim: int = 180
    action_dim: int = 3
    hidden_dim: int = 64

    # 训练配置
    learning_rate: float = 3e-4
    gamma: float = 0.99
    batch_size: int = 64

    # M7: 确定性配置
    seed: int = 42
    deterministic: bool = True

    # M18: 实验性门禁
    min_training_steps: int = 100_000
    maturity_threshold: float = 0.80

    # M3: 审计配置
    log_frequency: int = 100
    checkpoint_frequency: int = 1000


class RLAgent(ABC):
    """RL代理基类 (军规级).

    所有RL代理必须继承此类，确保符合军规要求:
    - M7: 确定性推理 (相同输入相同输出)
    - M3: 完整审计日志
    - M18: 实验性门禁验证
    """

    # M18: 禁止绕过成熟度门禁
    BYPASS_FORBIDDEN: bool = True

    def __init__(self, config: RLConfig) -> None:
        """初始化RL代理.

        Args:
            config: RL配置
        """
        self.config = config
        self._training_steps = 0
        self._eval_mode = False

        # M7: 设置确定性种子
        if config.deterministic:
            self._set_deterministic_seed(config.seed)

        # M3: 初始化审计日志
        self._decision_log: list[dict[str, Any]] = []

    def _set_deterministic_seed(self, seed: int) -> None:
        """设置确定性种子 (K28)."""
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

    @abstractmethod
    def select_action(
        self, state: NDArray[np.float32], deterministic: bool = False
    ) -> tuple[int, dict[str, Any]]:
        """选择动作 (K28 确定性, K29 审计).

        Args:
            state: 当前状态
            deterministic: 是否使用确定性策略

        Returns:
            (动作索引, 元数据字典)
        """
        ...

    @abstractmethod
    def update(
        self, transitions: list[RLTransition]
    ) -> dict[str, float]:
        """更新策略 (K29 审计).

        Args:
            transitions: 状态转移列表

        Returns:
            训练指标字典
        """
        ...

    @abstractmethod
    def get_value(self, state: NDArray[np.float32]) -> float:
        """获取状态价值.

        Args:
            state: 当前状态

        Returns:
            状态价值估计
        """
        ...

    def eval(self) -> None:
        """切换到评估模式."""
        self._eval_mode = True

    def train(self) -> None:
        """切换到训练模式."""
        self._eval_mode = False

    def is_mature(self) -> bool:
        """检查是否达到成熟度门槛 (M18).

        Returns:
            是否成熟
        """
        return self._training_steps >= self.config.min_training_steps

    def get_maturity_score(self) -> float:
        """获取成熟度分数 (M18).

        Returns:
            成熟度分数 [0, 1]
        """
        if self.config.min_training_steps == 0:
            return 1.0
        return min(
            1.0,
            self._training_steps / self.config.min_training_steps,
        )

    def log_decision(
        self,
        state: NDArray[np.float32],
        action: int,
        metadata: dict[str, Any],
    ) -> None:
        """记录决策日志 (K29 审计).

        Args:
            state: 状态
            action: 动作
            metadata: 元数据
        """
        log_entry = {
            "step": self._training_steps,
            "state_hash": hashlib.sha256(state.tobytes()).hexdigest()[:16],
            "action": action,
            "metadata": metadata,
        }
        self._decision_log.append(log_entry)

        # 限制日志大小
        if len(self._decision_log) > 10000:
            self._decision_log = self._decision_log[-5000:]

    def get_decision_log(self) -> list[dict[str, Any]]:
        """获取决策日志 (M3).

        Returns:
            决策日志列表
        """
        return self._decision_log.copy()

    def compute_state_hash(self, state: NDArray[np.float32]) -> str:
        """计算状态哈希 (K30).

        Args:
            state: 状态数组

        Returns:
            状态哈希值
        """
        return hashlib.sha256(state.tobytes()).hexdigest()[:16]

    @abstractmethod
    def save(self, path: str) -> None:
        """保存模型.

        Args:
            path: 保存路径
        """
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """加载模型.

        Args:
            path: 加载路径
        """
        ...
