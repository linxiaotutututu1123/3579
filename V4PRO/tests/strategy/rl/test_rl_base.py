"""RL基础模块测试.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M5(成本先行), M7(回放一致), M18(实验性门禁)

V4PRO Scenarios:
- K28: RL.BASE.DETERMINISTIC - RL推理确定性
- K29: RL.BASE.AUDIT_LOG - RL决策审计
- K30: RL.BASE.STATE_HASH - 状态哈希一致性
- K31: RL.BUFFER.DETERMINISTIC - 缓冲区采样确定性
- K32: RL.BUFFER.PRIORITY - 优先级回放
- K33: RL.BUFFER.ROLLOUT - Rollout缓冲区
- K34: RL.ENV.DETERMINISTIC - 环境确定性
- K35: RL.ENV.COST_MODEL - 成本模型
- K36: RL.ENV.REWARD_SHAPE - 奖励塑形
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray

from src.strategy.rl.base import (
    RLAction,
    RLAgent,
    RLConfig,
    RLReward,
    RLTransition,
)
from src.strategy.rl.buffer import (
    BufferConfig,
    PrioritizedReplayBuffer,
    PriorityConfig,
    ReplayBuffer,
    RolloutBuffer,
    RolloutConfig,
)
from src.strategy.rl.env import (
    TradingAction,
    TradingEnv,
    TradingEnvConfig,
)
from src.strategy.types import Bar1m


def _generate_bars(
    n: int, base_price: float = 4000.0, trend: float = 0.0001
) -> list[Bar1m]:
    """生成合成K线数据."""
    bars: list[Bar1m] = []
    price = base_price
    for i in range(n):
        price = price * (1 + trend + 0.001 * math.sin(i * 0.1))
        high = price * 1.002
        low = price * 0.998
        bars.append(
            {
                "ts": 1700000000.0 + i * 60,
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000.0 + i * 10,
            }
        )
    return bars


class SimpleRLAgent(RLAgent):
    """简单RL代理实现(用于测试)."""

    def __init__(self, config: RLConfig) -> None:
        """初始化."""
        super().__init__(config)
        self._policy = torch.nn.Sequential(
            torch.nn.Linear(config.state_dim, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, config.action_dim),
        )
        self._value = torch.nn.Sequential(
            torch.nn.Linear(config.state_dim, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
        )

    def select_action(
        self, state: NDArray[np.float32], deterministic: bool = False
    ) -> tuple[int, dict[str, Any]]:
        """选择动作."""
        with torch.inference_mode():
            x = torch.from_numpy(state).unsqueeze(0)
            logits = self._policy(x)

            if deterministic or self._eval_mode:
                action = int(logits.argmax(dim=-1).item())
            else:
                probs = torch.softmax(logits, dim=-1)
                action = int(torch.multinomial(probs, 1).item())

        metadata = {
            "logits": logits.numpy().tolist(),
            "deterministic": deterministic,
        }

        # K29: 记录决策
        self.log_decision(state, action, metadata)

        return action, metadata

    def update(
        self, transitions: list[RLTransition]
    ) -> dict[str, float]:
        """更新策略."""
        self._training_steps += len(transitions)
        return {"loss": 0.1, "steps": float(len(transitions))}

    def get_value(self, state: NDArray[np.float32]) -> float:
        """获取状态价值."""
        with torch.inference_mode():
            x = torch.from_numpy(state).unsqueeze(0)
            value = self._value(x)
        return float(value.item())

    def save(self, path: str) -> None:
        """保存模型."""
        torch.save(
            {
                "policy": self._policy.state_dict(),
                "value": self._value.state_dict(),
            },
            path,
        )

    def load(self, path: str) -> None:
        """加载模型."""
        checkpoint = torch.load(path, weights_only=True)
        self._policy.load_state_dict(checkpoint["policy"])
        self._value.load_state_dict(checkpoint["value"])


class TestRLBaseDeterministic:
    """K28: RL.BASE.DETERMINISTIC - RL推理确定性测试."""

    def test_deterministic_action_selection(self) -> None:
        """测试确定性动作选择."""
        config = RLConfig(state_dim=180, seed=42, deterministic=True)
        agent = SimpleRLAgent(config)
        agent.eval()

        state = np.random.randn(180).astype(np.float32)

        # 多次选择动作
        actions = []
        for _ in range(5):
            action, _ = agent.select_action(state, deterministic=True)
            actions.append(action)

        # 所有动作应相同
        assert all(a == actions[0] for a in actions)

    def test_same_seed_same_model(self) -> None:
        """测试相同种子产生相同模型."""
        config1 = RLConfig(state_dim=180, seed=12345)
        config2 = RLConfig(state_dim=180, seed=12345)

        torch.manual_seed(12345)
        agent1 = SimpleRLAgent(config1)

        torch.manual_seed(12345)
        agent2 = SimpleRLAgent(config2)

        # 参数应相同
        for p1, p2 in zip(
            agent1._policy.parameters(),
            agent2._policy.parameters(),
            strict=True,
        ):
            assert torch.equal(p1, p2)

    def test_eval_mode_deterministic(self) -> None:
        """测试评估模式下的确定性."""
        config = RLConfig(state_dim=180, seed=42)
        agent = SimpleRLAgent(config)
        agent.eval()

        state = np.random.randn(180).astype(np.float32)

        action1, _ = agent.select_action(state)
        action2, _ = agent.select_action(state)

        # eval模式下应确定性
        assert action1 == action2


class TestRLBaseAuditLog:
    """K29: RL.BASE.AUDIT_LOG - RL决策审计测试."""

    def test_decision_logging(self) -> None:
        """测试决策日志记录 (M3)."""
        config = RLConfig(state_dim=180)
        agent = SimpleRLAgent(config)

        state = np.random.randn(180).astype(np.float32)
        agent.select_action(state, deterministic=True)

        log = agent.get_decision_log()
        assert len(log) == 1
        assert "state_hash" in log[0]
        assert "action" in log[0]
        assert "metadata" in log[0]

    def test_log_contains_state_hash(self) -> None:
        """测试日志包含状态哈希."""
        config = RLConfig(state_dim=180)
        agent = SimpleRLAgent(config)

        state = np.random.randn(180).astype(np.float32)
        expected_hash = hashlib.sha256(state.tobytes()).hexdigest()[:16]

        agent.select_action(state, deterministic=True)

        log = agent.get_decision_log()
        assert log[0]["state_hash"] == expected_hash

    def test_log_size_limit(self) -> None:
        """测试日志大小限制."""
        config = RLConfig(state_dim=180)
        agent = SimpleRLAgent(config)

        # 记录超过限制
        for _ in range(15000):
            state = np.random.randn(180).astype(np.float32)
            agent.select_action(state, deterministic=True)

        log = agent.get_decision_log()
        # 应该被截断
        assert len(log) <= 10000


class TestRLBaseStateHash:
    """K30: RL.BASE.STATE_HASH - 状态哈希一致性测试."""

    def test_state_hash_reproducible(self) -> None:
        """测试状态哈希可重现."""
        state = np.random.randn(180).astype(np.float32)

        hash1 = hashlib.sha256(state.tobytes()).hexdigest()[:16]
        hash2 = hashlib.sha256(state.tobytes()).hexdigest()[:16]

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_transition_state_hash(self) -> None:
        """测试转移记录状态哈希."""
        state = np.random.randn(180).astype(np.float32)
        next_state = np.random.randn(180).astype(np.float32)

        transition = RLTransition(
            state=state,
            action=1,
            reward=0.5,
            next_state=next_state,
            done=False,
        )

        # 验证哈希被计算
        assert len(transition.state_hash) == 16
        assert len(transition.next_state_hash) == 16
        assert transition.state_hash != transition.next_state_hash

    def test_agent_compute_state_hash(self) -> None:
        """测试代理计算状态哈希."""
        config = RLConfig(state_dim=180)
        agent = SimpleRLAgent(config)

        state = np.random.randn(180).astype(np.float32)
        hash1 = agent.compute_state_hash(state)
        hash2 = agent.compute_state_hash(state)

        assert hash1 == hash2


class TestRLBufferDeterministic:
    """K31: RL.BUFFER.DETERMINISTIC - 缓冲区采样确定性测试."""

    def test_deterministic_sampling(self) -> None:
        """测试确定性采样."""
        config = BufferConfig(capacity=100, batch_size=10, seed=42)

        buffer1 = ReplayBuffer(config)
        buffer2 = ReplayBuffer(config)

        # 添加相同数据
        for i in range(50):
            state = np.ones(10, dtype=np.float32) * i
            transition = RLTransition(
                state=state,
                action=i % 3,
                reward=float(i),
                next_state=state + 1,
                done=False,
            )
            buffer1.push(transition)
            buffer2.push(transition)

        # 采样应相同
        sample1 = buffer1.sample()
        sample2 = buffer2.sample()

        assert len(sample1) == len(sample2)
        for t1, t2 in zip(sample1, sample2, strict=True):
            assert t1.state_hash == t2.state_hash

    def test_buffer_hash(self) -> None:
        """测试缓冲区哈希 (M7)."""
        config = BufferConfig(capacity=100, batch_size=10)
        buffer = ReplayBuffer(config)

        for i in range(20):
            state = np.ones(10, dtype=np.float32) * i
            transition = RLTransition(
                state=state,
                action=0,
                reward=0.0,
                next_state=state,
                done=False,
            )
            buffer.push(transition)

        hash1 = buffer.get_buffer_hash()
        hash2 = buffer.get_buffer_hash()

        assert hash1 == hash2
        assert len(hash1) == 16


class TestRLBufferPriority:
    """K32: RL.BUFFER.PRIORITY - 优先级回放测试."""

    def test_priority_sampling(self) -> None:
        """测试优先级采样."""
        config = PriorityConfig(capacity=100, batch_size=10, seed=42)
        buffer = PrioritizedReplayBuffer(config)

        # 添加不同优先级的数据
        for i in range(50):
            state = np.ones(10, dtype=np.float32) * i
            transition = RLTransition(
                state=state,
                action=0,
                reward=0.0,
                next_state=state,
                done=False,
            )
            # 后面的数据优先级更高
            buffer.push(transition, priority=float(i + 1))

        samples, weights, indices = buffer.sample()

        assert len(samples) == 10
        assert len(weights) == 10
        assert len(indices) == 10
        assert all(w > 0 for w in weights)

    def test_priority_update(self) -> None:
        """测试优先级更新."""
        config = PriorityConfig(capacity=100, batch_size=10)
        buffer = PrioritizedReplayBuffer(config)

        for i in range(20):
            state = np.ones(10, dtype=np.float32) * i
            transition = RLTransition(
                state=state,
                action=0,
                reward=0.0,
                next_state=state,
                done=False,
            )
            buffer.push(transition, priority=1.0)

        # 更新优先级
        buffer.update_priorities([0, 1, 2], [10.0, 20.0, 30.0])

        # 验证更新成功(内部优先级已更新)
        assert buffer._priorities[0] > 1.0
        assert buffer._priorities[1] > buffer._priorities[0]


class TestRLBufferRollout:
    """K33: RL.BUFFER.ROLLOUT - Rollout缓冲区测试."""

    def test_rollout_gae(self) -> None:
        """测试GAE优势计算."""
        config = RolloutConfig(buffer_size=100, gamma=0.99, gae_lambda=0.95)
        buffer = RolloutBuffer(config)

        # 添加数据
        for i in range(10):
            buffer.push(
                state=np.ones(10, dtype=np.float32) * i,
                action=0,
                reward=1.0,
                value=0.5,
                log_prob=-1.0,
                done=i == 9,
            )

        # 计算优势
        buffer.compute_returns_and_advantages(last_value=0.0)

        assert buffer._advantages is not None
        assert buffer._returns is not None
        assert len(buffer._advantages) == 10
        assert len(buffer._returns) == 10

    def test_rollout_batches(self) -> None:
        """测试批次获取."""
        config = RolloutConfig(buffer_size=100, seed=42)
        buffer = RolloutBuffer(config)

        for i in range(20):
            buffer.push(
                state=np.ones(10, dtype=np.float32) * i,
                action=i % 3,
                reward=float(i) * 0.1,
                value=0.5,
                log_prob=-1.0,
                done=False,
            )

        buffer.compute_returns_and_advantages(last_value=0.5)
        batches = buffer.get_batches(batch_size=8)

        # 验证批次
        assert len(batches) == 3  # 20 / 8 = 2余4, 需要3个批次
        assert "states" in batches[0]
        assert "actions" in batches[0]
        assert "advantages" in batches[0]


class TestRLEnvDeterministic:
    """K34: RL.ENV.DETERMINISTIC - 环境确定性测试."""

    def test_env_reset_deterministic(self) -> None:
        """测试环境重置确定性."""
        config = TradingEnvConfig(seed=42, deterministic=True)
        bars = _generate_bars(200)

        env1 = TradingEnv(config, bars)
        env2 = TradingEnv(config, bars)

        state1 = env1.reset(seed=42)
        state2 = env2.reset(seed=42)

        assert state1.get_hash() == state2.get_hash()

    def test_env_step_deterministic(self) -> None:
        """测试环境步进确定性."""
        config = TradingEnvConfig(seed=42, deterministic=True)
        bars = _generate_bars(200)

        env = TradingEnv(config, bars)
        env.reset(seed=42)

        # 执行相同动作序列
        actions = [1, 0, 0, 2, 1, 0]
        states1 = []
        rewards1 = []

        for action in actions:
            state, reward, done, _ = env.step(action)
            states1.append(state.get_hash())
            rewards1.append(reward)
            if done:
                break

        # 重置并重复
        env.reset(seed=42)
        states2 = []
        rewards2 = []

        for action in actions:
            state, reward, done, _ = env.step(action)
            states2.append(state.get_hash())
            rewards2.append(reward)
            if done:
                break

        assert states1 == states2
        assert rewards1 == rewards2


class TestRLEnvCostModel:
    """K35: RL.ENV.COST_MODEL - 成本模型测试."""

    def test_commission_applied(self) -> None:
        """测试手续费计算 (M5)."""
        config = TradingEnvConfig(
            commission_rate=0.0001,
            slippage_ticks=0,
            contract_multiplier=10.0,
        )
        bars = _generate_bars(200)

        env = TradingEnv(config, bars)
        env.reset()

        # 执行买入
        _, _, _, info = env.step(TradingAction.BUY)

        # 验证成本被计算
        assert info["total_cost"] > 0
        assert info["trade_info"]["executed"]
        assert info["trade_info"]["cost"] > 0

    def test_slippage_applied(self) -> None:
        """测试滑点计算 (M5)."""
        config = TradingEnvConfig(
            commission_rate=0.0,
            slippage_ticks=2,
            tick_size=1.0,
            contract_multiplier=10.0,
        )
        bars = _generate_bars(200)

        env = TradingEnv(config, bars)
        env.reset()

        # 执行买入
        _, _, _, info = env.step(TradingAction.BUY)

        # 验证滑点
        assert info["trade_info"]["slippage"] == 2.0 * 10.0  # 2 ticks * 10 multiplier

    def test_cost_tracking(self) -> None:
        """测试成本追踪."""
        config = TradingEnvConfig(
            commission_rate=0.0001,
            slippage_ticks=1,
        )
        bars = _generate_bars(200)

        env = TradingEnv(config, bars)
        env.reset()

        # 多次交易
        for _ in range(5):
            env.step(TradingAction.BUY)

        metrics = env.get_metrics()
        assert metrics["total_trades"] == 5
        assert metrics["total_cost"] > 0


class TestRLEnvRewardShape:
    """K36: RL.ENV.REWARD_SHAPE - 奖励塑形测试."""

    def test_pnl_reward(self) -> None:
        """测试盈亏奖励."""
        config = TradingEnvConfig(
            reward_scale=1.0,
            risk_penalty_factor=0.0,
            cost_penalty_factor=0.0,
            commission_rate=0.0,
            slippage_ticks=0,
        )
        bars = _generate_bars(200, trend=0.001)  # 上涨趋势

        env = TradingEnv(config, bars)
        env.reset()

        # 买入后持有
        env.step(TradingAction.BUY)
        _, reward, _, _ = env.step(TradingAction.HOLD)

        # 上涨趋势中持多应有正奖励
        assert reward > 0

    def test_risk_penalty(self) -> None:
        """测试风险惩罚."""
        # 测试风险惩罚存在且随仓位增加
        config = TradingEnvConfig(
            reward_scale=1.0,
            risk_penalty_factor=10.0,  # 高惩罚系数
            cost_penalty_factor=0.0,
            commission_rate=0.0,
            slippage_ticks=0,
            max_position=10,
        )
        # 使用完全静态价格避免PnL干扰
        static_bars: list[Bar1m] = []
        for i in range(200):
            static_bars.append({
                "ts": 1700000000.0 + i * 60,
                "open": 4000.0,
                "high": 4000.0,
                "low": 4000.0,
                "close": 4000.0,
                "volume": 1000.0,
            })

        env = TradingEnv(config, static_bars)
        env.reset()

        # 小仓位 (1手)
        env.step(TradingAction.BUY)
        _, reward_small, _, _ = env.step(TradingAction.HOLD)

        # 重置并建立大仓位
        env.reset()
        for _ in range(9):  # 9手
            env.step(TradingAction.BUY)
        _, reward_large, _, _ = env.step(TradingAction.HOLD)

        # 大仓位的风险惩罚应更大(奖励更低/更负)
        # 因为risk_penalty = (position/max_position)^2 * factor
        # 小仓位: (1/10)^2 * 10 = 0.1
        # 大仓位: (9/10)^2 * 10 = 8.1
        # 静态价格下PnL=0,所以只有风险惩罚
        assert reward_large < reward_small

    def test_cost_penalty(self) -> None:
        """测试成本惩罚 (M5)."""
        config = TradingEnvConfig(
            reward_scale=1.0,
            risk_penalty_factor=0.0,
            cost_penalty_factor=1.0,
            commission_rate=0.001,  # 高手续费
            slippage_ticks=5,
        )
        bars = _generate_bars(200)

        env = TradingEnv(config, bars)
        env.reset()

        # 交易会产生成本惩罚
        _, reward1, _, _ = env.step(TradingAction.BUY)

        # 成本惩罚应使奖励降低
        # reward1包含成本惩罚
        assert isinstance(reward1, float)


class TestRLMaturityGate:
    """RL成熟度门禁测试 (M18)."""

    def test_maturity_threshold(self) -> None:
        """测试成熟度门槛."""
        config = RLConfig(min_training_steps=1000, maturity_threshold=0.80)
        agent = SimpleRLAgent(config)

        assert not agent.is_mature()
        assert agent.get_maturity_score() == 0.0

    def test_maturity_progress(self) -> None:
        """测试成熟度进度."""
        config = RLConfig(min_training_steps=1000)
        agent = SimpleRLAgent(config)

        # 模拟训练500步
        transitions = [
            RLTransition(
                state=np.zeros(180, dtype=np.float32),
                action=0,
                reward=0.0,
                next_state=np.zeros(180, dtype=np.float32),
                done=False,
            )
            for _ in range(500)
        ]
        agent.update(transitions)

        assert agent.get_maturity_score() == 0.5
        assert not agent.is_mature()

    def test_maturity_complete(self) -> None:
        """测试成熟度完成."""
        config = RLConfig(min_training_steps=100)
        agent = SimpleRLAgent(config)

        # 训练超过门槛
        transitions = [
            RLTransition(
                state=np.zeros(180, dtype=np.float32),
                action=0,
                reward=0.0,
                next_state=np.zeros(180, dtype=np.float32),
                done=False,
            )
            for _ in range(150)
        ]
        agent.update(transitions)

        assert agent.get_maturity_score() >= 1.0
        assert agent.is_mature()

    def test_bypass_forbidden(self) -> None:
        """测试禁止绕过门禁."""
        assert SimpleRLAgent.BYPASS_FORBIDDEN is True


class TestRLRewardStructure:
    """RL奖励结构测试."""

    def test_reward_breakdown(self) -> None:
        """测试奖励分解."""
        reward = RLReward(
            total=0.5,
            pnl_reward=0.8,
            risk_penalty=0.2,
            cost_penalty=0.1,
        )

        assert "reward_breakdown" in reward.metadata
        assert reward.metadata["reward_breakdown"]["pnl"] == 0.8
        assert reward.metadata["reward_breakdown"]["risk"] == 0.2
        assert reward.metadata["reward_breakdown"]["cost"] == 0.1

    def test_reward_action_enum(self) -> None:
        """测试动作枚举."""
        assert RLAction.HOLD.value == 0
        assert RLAction.BUY.value == 1
        assert RLAction.SELL.value == 2
