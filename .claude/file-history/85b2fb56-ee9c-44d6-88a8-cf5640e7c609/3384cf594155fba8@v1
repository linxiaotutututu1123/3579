"""强化学习策略模块 (军规级 v4.2).

V4PRO Platform Component - Phase K B类模型层
V4 SPEC: §25 强化学习策略

本模块包含强化学习策略实现，符合军规要求:
- M7: 回放一致性 - 确定性推理
- M3: 完整审计 - 决策日志
- M18: 实验性门禁 - 训练成熟度验证

功能特性:
    - 基础RL代理接口
    - 经验回放缓冲区
    - PPO/A2C/DQN算法框架
    - 交易环境封装
    - 训练与评估工具
"""

from src.strategy.rl.base import (
    RLAgent,
    RLConfig,
    RLState,
    RLAction,
    RLReward,
    RLTransition,
)
from src.strategy.rl.buffer import (
    ReplayBuffer,
    PrioritizedReplayBuffer,
    RolloutBuffer,
)
from src.strategy.rl.env import (
    TradingEnv,
    TradingEnvConfig,
    TradingState,
    TradingAction,
)

__all__ = [
    # 基础类
    "RLAgent",
    "RLConfig",
    "RLState",
    "RLAction",
    "RLReward",
    "RLTransition",
    # 缓冲区
    "ReplayBuffer",
    "PrioritizedReplayBuffer",
    "RolloutBuffer",
    # 环境
    "TradingEnv",
    "TradingEnvConfig",
    "TradingState",
    "TradingAction",
]
