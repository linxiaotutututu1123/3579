"""交易环境模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M5(成本先行), M7(回放一致)

V4PRO Scenarios:
- K34: RL.ENV.DETERMINISTIC - 环境确定性
- K35: RL.ENV.COST_MODEL - 成本模型
- K36: RL.ENV.REWARD_SHAPE - 奖励塑形
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.strategy.types import Bar1m


class TradingAction(IntEnum):
    """交易动作枚举."""

    HOLD = 0
    BUY = 1
    SELL = 2


@dataclass
class TradingEnvConfig:
    """交易环境配置.

    军规约束:
    - M5: 成本先行 - 必须配置交易成本
    - M7: 回放一致 - 确定性配置
    """

    # 基础配置
    initial_capital: float = 1_000_000.0
    max_position: int = 100  # 最大持仓手数
    contract_multiplier: float = 10.0  # 合约乘数

    # M5: 成本配置 (成本先行)
    commission_rate: float = 0.0001  # 手续费率
    slippage_ticks: int = 1  # 滑点tick数
    tick_size: float = 1.0  # 最小变动价位

    # 奖励配置
    reward_scale: float = 1e-4  # 奖励缩放因子
    risk_penalty_factor: float = 0.1  # 风险惩罚系数
    cost_penalty_factor: float = 1.0  # 成本惩罚系数 (M5)

    # M7: 确定性配置
    seed: int = 42
    deterministic: bool = True

    # 特征配置
    lookback_window: int = 60
    feature_dim: int = 180


@dataclass
class TradingState:
    """交易状态."""

    step: int
    features: NDArray[np.float32]
    position: int
    capital: float
    pnl: float
    unrealized_pnl: float
    total_cost: float
    done: bool
    info: dict[str, Any] = field(default_factory=dict)

    def to_array(self) -> NDArray[np.float32]:
        """转换为特征数组."""
        # 拼接特征和状态信息
        state_info = np.array(
            [
                self.position / 100.0,  # 归一化持仓
                self.pnl / 1_000_000.0,  # 归一化盈亏
                self.unrealized_pnl / 100_000.0,
            ],
            dtype=np.float32,
        )
        return np.concatenate([self.features, state_info])

    def get_hash(self) -> str:
        """获取状态哈希 (M7)."""
        return hashlib.sha256(self.to_array().tobytes()).hexdigest()[:16]


class TradingEnv:
    """交易环境 (K34 确定性).

    符合军规的交易仿真环境:
    - M5: 成本先行 - 所有交易计入成本
    - M7: 回放一致 - 确定性仿真
    - M3: 完整审计 - 交易日志
    """

    def __init__(
        self,
        config: TradingEnvConfig,
        bars: list[Bar1m] | None = None,
    ) -> None:
        """初始化交易环境.

        Args:
            config: 环境配置
            bars: K线数据
        """
        self.config = config
        self._bars = bars or []

        # 状态变量
        self._step = 0
        self._position = 0
        self._capital = config.initial_capital
        self._entry_price = 0.0
        self._total_cost = 0.0
        self._total_trades = 0

        # M3: 交易日志
        self._trade_log: list[dict[str, Any]] = []

        # M7: 确定性随机数
        if config.deterministic:
            self._rng = np.random.RandomState(config.seed)
        else:
            self._rng = np.random.RandomState()

    def set_data(self, bars: list[Bar1m]) -> None:
        """设置K线数据.

        Args:
            bars: K线数据列表
        """
        self._bars = bars

    def reset(self, seed: int | None = None) -> TradingState:
        """重置环境 (K34 确定性).

        Args:
            seed: 随机种子

        Returns:
            初始状态
        """
        if seed is not None and self.config.deterministic:
            self._rng = np.random.RandomState(seed)

        self._step = self.config.lookback_window
        self._position = 0
        self._capital = self.config.initial_capital
        self._entry_price = 0.0
        self._total_cost = 0.0
        self._total_trades = 0
        self._trade_log.clear()

        return self._get_state()

    def step(
        self, action: int
    ) -> tuple[TradingState, float, bool, dict[str, Any]]:
        """执行一步 (K35 成本模型, K36 奖励塑形).

        Args:
            action: 动作 (0=持有, 1=买入, 2=卖出)

        Returns:
            (下一状态, 奖励, 是否结束, 信息)
        """
        if self._step >= len(self._bars) - 1:
            state = self._get_state()
            state.done = True
            return state, 0.0, True, {"reason": "数据结束"}

        current_bar = self._bars[self._step]
        next_bar = self._bars[self._step + 1]
        current_price = current_bar["close"]
        next_price = next_bar["close"]

        # 执行交易
        trade_info = self._execute_trade(action, current_price)

        # 计算奖励 (K36)
        reward = self._compute_reward(
            action, current_price, next_price, trade_info
        )

        # 更新步数
        self._step += 1

        # 获取下一状态
        next_state = self._get_state()
        done = self._step >= len(self._bars) - 1

        info = {
            "trade_info": trade_info,
            "position": self._position,
            "capital": self._capital,
            "total_cost": self._total_cost,
        }

        return next_state, reward, done, info

    def _execute_trade(
        self, action: int, price: float
    ) -> dict[str, Any]:
        """执行交易 (K35 成本模型).

        Args:
            action: 动作
            price: 当前价格

        Returns:
            交易信息
        """
        trade_info: dict[str, Any] = {
            "action": action,
            "executed": False,
            "cost": 0.0,
            "slippage": 0.0,
        }

        if action == TradingAction.HOLD:
            return trade_info

        # M5: 计算滑点成本
        slippage = (
            self.config.slippage_ticks * self.config.tick_size
        )

        if action == TradingAction.BUY and self._position < self.config.max_position:
            # 买入
            exec_price = price + slippage  # 买入滑点向上
            trade_qty = 1  # 每次交易1手

            # M5: 计算手续费
            commission = (
                exec_price
                * self.config.contract_multiplier
                * self.config.commission_rate
            )

            # 更新状态
            self._position += trade_qty
            self._entry_price = exec_price
            self._total_cost += commission + slippage * self.config.contract_multiplier
            self._total_trades += 1

            trade_info.update({
                "executed": True,
                "side": "BUY",
                "qty": trade_qty,
                "price": exec_price,
                "cost": commission,
                "slippage": slippage * self.config.contract_multiplier,
            })

            # M3: 记录交易
            self._log_trade(trade_info)

        elif action == TradingAction.SELL and self._position > -self.config.max_position:
            # 卖出
            exec_price = price - slippage  # 卖出滑点向下
            trade_qty = 1

            # M5: 计算手续费
            commission = (
                exec_price
                * self.config.contract_multiplier
                * self.config.commission_rate
            )

            # 更新状态
            self._position -= trade_qty
            self._entry_price = exec_price
            self._total_cost += commission + slippage * self.config.contract_multiplier
            self._total_trades += 1

            trade_info.update({
                "executed": True,
                "side": "SELL",
                "qty": trade_qty,
                "price": exec_price,
                "cost": commission,
                "slippage": slippage * self.config.contract_multiplier,
            })

            # M3: 记录交易
            self._log_trade(trade_info)

        return trade_info

    def _compute_reward(
        self,
        action: int,
        current_price: float,
        next_price: float,
        trade_info: dict[str, Any],
    ) -> float:
        """计算奖励 (K36 奖励塑形).

        Args:
            action: 动作
            current_price: 当前价格
            next_price: 下一价格
            trade_info: 交易信息

        Returns:
            奖励值
        """
        # PnL奖励 (持仓盈亏)
        price_change = next_price - current_price
        pnl = (
            self._position
            * price_change
            * self.config.contract_multiplier
        )
        pnl_reward = pnl * self.config.reward_scale

        # M5: 成本惩罚 (成本先行)
        cost = trade_info.get("cost", 0.0) + trade_info.get("slippage", 0.0)
        cost_penalty = cost * self.config.cost_penalty_factor * self.config.reward_scale

        # 风险惩罚 (大仓位惩罚)
        risk_penalty = (
            abs(self._position) / self.config.max_position
        ) ** 2 * self.config.risk_penalty_factor

        # 总奖励
        reward = pnl_reward - cost_penalty - risk_penalty

        return float(reward)

    def _get_state(self) -> TradingState:
        """获取当前状态.

        Returns:
            当前交易状态
        """
        features = self._extract_features()

        # 计算未实现盈亏
        if self._position != 0 and self._step < len(self._bars):
            current_price = self._bars[self._step]["close"]
            unrealized_pnl = (
                self._position
                * (current_price - self._entry_price)
                * self.config.contract_multiplier
            )
        else:
            unrealized_pnl = 0.0

        return TradingState(
            step=self._step,
            features=features,
            position=self._position,
            capital=self._capital,
            pnl=self._capital - self.config.initial_capital,
            unrealized_pnl=unrealized_pnl,
            total_cost=self._total_cost,
            done=self._step >= len(self._bars) - 1,
        )

    def _extract_features(self) -> NDArray[np.float32]:
        """提取特征.

        Returns:
            特征数组
        """
        if self._step < self.config.lookback_window:
            return np.zeros(self.config.feature_dim, dtype=np.float32)

        # 获取回看窗口内的K线
        start = self._step - self.config.lookback_window
        window_bars = self._bars[start : self._step]

        # 提取特征
        closes = np.array([b["close"] for b in window_bars], dtype=np.float32)
        volumes = np.array([b["volume"] for b in window_bars], dtype=np.float32)
        highs = np.array([b["high"] for b in window_bars], dtype=np.float32)
        lows = np.array([b["low"] for b in window_bars], dtype=np.float32)

        # 收益率
        returns = np.diff(closes) / closes[:-1]
        returns = np.concatenate([[0], returns])

        # 归一化
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        volumes = (volumes - volumes.mean()) / (volumes.std() + 1e-8)
        ranges = (highs - lows) / closes
        ranges = (ranges - ranges.mean()) / (ranges.std() + 1e-8)

        # 拼接特征
        features = np.concatenate([returns, volumes, ranges])

        result: NDArray[np.float32] = features.astype(np.float32)
        return result

    def _log_trade(self, trade_info: dict[str, Any]) -> None:
        """记录交易 (M3 审计).

        Args:
            trade_info: 交易信息
        """
        log_entry = {
            "step": self._step,
            "ts": self._bars[self._step]["ts"] if self._step < len(self._bars) else 0,
            **trade_info,
            "position_after": self._position,
            "capital_after": self._capital,
        }
        self._trade_log.append(log_entry)

    def get_trade_log(self) -> list[dict[str, Any]]:
        """获取交易日志 (M3).

        Returns:
            交易日志列表
        """
        return self._trade_log.copy()

    def get_metrics(self) -> dict[str, float]:
        """获取环境指标.

        Returns:
            指标字典
        """
        return {
            "total_trades": float(self._total_trades),
            "total_cost": self._total_cost,
            "final_capital": self._capital,
            "final_pnl": self._capital - self.config.initial_capital,
            "final_position": float(self._position),
        }
