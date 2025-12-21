"""
策略联邦中枢模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: §28 策略联邦, §29 信号融合, §30 风险对冲

军规覆盖:
- M1: 单一信号源 - 联邦输出为唯一信号源
- M19: 风险归因 - 策略贡献度追踪
- M20: 跨所一致 - 策略间相关性抑制

功能特性:
- 策略注册与管理
- 信号去重与融合
- 动态权重分配
- 相关性抑制
- 审计日志支持

示例:
    >>> from src.strategy.federation import (
    ...     StrategyFederation,
    ...     FederationSignal,
    ... )
    >>> federation = StrategyFederation()
    >>> federation.register_strategy("kalman_arb", weight=0.3)
    >>> signal = federation.generate_signal(market_state)
"""

from __future__ import annotations

import contextlib
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np


if TYPE_CHECKING:
    from collections.abc import Callable


class SignalDirection(Enum):
    """信号方向枚举."""

    LONG = "LONG"  # 多头
    SHORT = "SHORT"  # 空头
    FLAT = "FLAT"  # 平仓/观望


class SignalStrength(Enum):
    """信号强度枚举."""

    STRONG = "STRONG"  # 强信号 (>0.7)
    MODERATE = "MODERATE"  # 中等信号 (0.4-0.7)
    WEAK = "WEAK"  # 弱信号 (<0.4)


@dataclass(frozen=True)
class StrategySignal:
    """策略信号 (不可变).

    属性:
        strategy_id: 策略ID
        symbol: 合约代码
        direction: 信号方向
        strength: 信号强度 (0-1)
        confidence: 置信度 (0-1)
        timestamp: 时间戳
        metadata: 元数据
    """

    strategy_id: str
    symbol: str
    direction: SignalDirection
    strength: float
    confidence: float
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class FederationSignal:
    """联邦融合信号 (不可变) - 唯一信号出口.

    属性:
        symbol: 合约代码
        direction: 最终信号方向
        strength: 融合后强度
        confidence: 融合后置信度
        contributing_strategies: 贡献策略列表
        weights: 策略权重
        correlation_penalty: 相关性惩罚
        timestamp: 时间戳
    """

    symbol: str
    direction: SignalDirection
    strength: float
    confidence: float
    contributing_strategies: tuple[str, ...] = ()
    weights: dict[str, float] = field(default_factory=dict)
    correlation_penalty: float = 0.0
    timestamp: str = ""

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "FEDERATION_SIGNAL",
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "contributing_strategies": list(self.contributing_strategies),
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "correlation_penalty": round(self.correlation_penalty, 4),
            "timestamp": self.timestamp,
        }

    def get_strength_level(self) -> SignalStrength:
        """获取信号强度等级."""
        if self.strength > 0.7:
            return SignalStrength.STRONG
        if self.strength > 0.4:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK


@dataclass
class StrategyMember:
    """联邦成员策略.

    属性:
        strategy_id: 策略ID
        name: 策略名称
        weight: 基础权重 (0-1)
        dynamic_weight: 动态权重 (基于表现调整)
        enabled: 是否启用
        signal_count: 信号计数
        hit_count: 命中计数
        last_signal: 最后信号
    """

    strategy_id: str
    name: str
    weight: float = 0.1
    dynamic_weight: float = 0.1
    enabled: bool = True
    signal_count: int = 0
    hit_count: int = 0
    last_signal: StrategySignal | None = None

    @property
    def hit_rate(self) -> float:
        """获取命中率."""
        if self.signal_count == 0:
            return 0.0
        return self.hit_count / self.signal_count


@dataclass
class CorrelationMatrix:
    """策略相关性矩阵.

    属性:
        strategy_ids: 策略ID列表
        matrix: 相关性矩阵
        last_update: 最后更新时间
    """

    strategy_ids: list[str] = field(default_factory=list)
    matrix: np.ndarray | None = None
    last_update: str = ""

    def get_correlation(self, strategy_a: str, strategy_b: str) -> float:
        """获取两个策略的相关性."""
        if self.matrix is None or not self.strategy_ids:
            return 0.0

        try:
            idx_a = self.strategy_ids.index(strategy_a)
            idx_b = self.strategy_ids.index(strategy_b)
            return float(self.matrix[idx_a, idx_b])
        except (ValueError, IndexError):
            return 0.0


class StrategyFederation:
    """策略联邦中枢 (军规 M1/M19/M20).

    功能:
    - 策略注册与管理
    - 信号去重 (M1)
    - 信号融合
    - 动态权重分配
    - 相关性抑制 (M20)
    - 贡献度追踪 (M19)

    示例:
        >>> federation = StrategyFederation()
        >>> federation.register_strategy("kalman_arb", weight=0.3)
        >>> federation.register_strategy("lstm_trend", weight=0.25)
        >>> signal = federation.generate_signal("rb2501", signals)
    """

    # 默认参数
    DEFAULT_CORRELATION_THRESHOLD: ClassVar[float] = 0.3  # 相关性抑制阈值
    DEFAULT_MIN_CONFIDENCE: ClassVar[float] = 0.5  # 最小置信度
    DEFAULT_SIGNAL_DECAY: ClassVar[float] = 0.95  # 信号衰减系数

    def __init__(
        self,
        correlation_threshold: float = 0.3,
        min_confidence: float = 0.5,
        enable_dynamic_weights: bool = True,
    ) -> None:
        """初始化策略联邦.

        参数:
            correlation_threshold: 相关性抑制阈值
            min_confidence: 最小置信度门槛
            enable_dynamic_weights: 是否启用动态权重
        """
        self._correlation_threshold = correlation_threshold
        self._min_confidence = min_confidence
        self._enable_dynamic_weights = enable_dynamic_weights

        # 成员策略
        self._members: dict[str, StrategyMember] = {}

        # 相关性矩阵
        self._correlation_matrix = CorrelationMatrix()

        # 信号历史 (用于计算相关性) - 使用 deque 优化
        self._signal_history: dict[str, deque[float]] = {}
        self._history_window: int = 100

        # 相关性矩阵更新节流
        self._last_correlation_update: float = 0.0
        self._correlation_update_interval: float = 1.0  # 最小更新间隔（秒）

        # 回调函数
        self._on_signal_callbacks: list[Callable[[FederationSignal], None]] = []

        # 统计
        self._signal_count: int = 0
        self._conflict_count: int = 0

    @property
    def member_count(self) -> int:
        """获取成员数量."""
        return len(self._members)

    @property
    def signal_count(self) -> int:
        """获取信号总数."""
        return self._signal_count

    @property
    def conflict_count(self) -> int:
        """获取冲突计数."""
        return self._conflict_count

    def register_strategy(
        self,
        strategy_id: str,
        name: str | None = None,
        weight: float = 0.1,
    ) -> None:
        """注册策略.

        参数:
            strategy_id: 策略ID
            name: 策略名称
            weight: 基础权重
        """
        if strategy_id in self._members:
            return

        self._members[strategy_id] = StrategyMember(
            strategy_id=strategy_id,
            name=name or strategy_id,
            weight=weight,
            dynamic_weight=weight,
        )

        # 初始化信号历史
        self._signal_history[strategy_id] = []

    def unregister_strategy(self, strategy_id: str) -> None:
        """注销策略.

        参数:
            strategy_id: 策略ID
        """
        if strategy_id in self._members:
            del self._members[strategy_id]
        if strategy_id in self._signal_history:
            del self._signal_history[strategy_id]

    def enable_strategy(self, strategy_id: str) -> None:
        """启用策略."""
        if strategy_id in self._members:
            self._members[strategy_id].enabled = True

    def disable_strategy(self, strategy_id: str) -> None:
        """禁用策略."""
        if strategy_id in self._members:
            self._members[strategy_id].enabled = False

    def set_weight(self, strategy_id: str, weight: float) -> None:
        """设置策略权重.

        参数:
            strategy_id: 策略ID
            weight: 权重值 (0-1)
        """
        if strategy_id in self._members:
            self._members[strategy_id].weight = max(0.0, min(1.0, weight))

    def submit_signal(self, signal: StrategySignal) -> None:
        """提交策略信号.

        参数:
            signal: 策略信号
        """
        if signal.strategy_id not in self._members:
            return

        member = self._members[signal.strategy_id]
        if not member.enabled:
            return

        member.signal_count += 1
        member.last_signal = signal

        # 记录信号历史 (用于相关性计算)
        direction_value = (
            1.0
            if signal.direction == SignalDirection.LONG
            else (-1.0 if signal.direction == SignalDirection.SHORT else 0.0)
        )
        history = self._signal_history[signal.strategy_id]
        history.append(direction_value * signal.strength)
        if len(history) > self._history_window:
            history.pop(0)

    def generate_signal(
        self,
        symbol: str,
        signals: list[StrategySignal],
    ) -> FederationSignal | None:
        """生成联邦融合信号 (M1: 唯一信号出口).

        参数:
            symbol: 合约代码
            signals: 策略信号列表

        返回:
            融合信号或None
        """
        self._signal_count += 1
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        # 过滤有效信号
        valid_signals = [
            s
            for s in signals
            if s.strategy_id in self._members
            and self._members[s.strategy_id].enabled
            and s.confidence >= self._min_confidence
            and s.symbol == symbol
        ]

        if not valid_signals:
            return None

        # 提交信号
        for signal in valid_signals:
            self.submit_signal(signal)

        # 检测信号冲突
        directions = {s.direction for s in valid_signals}
        if SignalDirection.LONG in directions and SignalDirection.SHORT in directions:
            self._conflict_count += 1

        # 更新相关性矩阵
        self._update_correlation_matrix()

        # 计算融合信号
        fused_signal = self._fuse_signals(symbol, valid_signals, timestamp)

        # 通知回调
        if fused_signal is not None:
            self._notify_signal(fused_signal)

        return fused_signal

    def _fuse_signals(
        self,
        symbol: str,
        signals: list[StrategySignal],
        timestamp: str,
    ) -> FederationSignal | None:
        """融合策略信号.

        参数:
            symbol: 合约代码
            signals: 策略信号列表
            timestamp: 时间戳

        返回:
            融合信号
        """
        if not signals:
            return None

        # 获取策略权重
        weights: dict[str, float] = {}
        for signal in signals:
            member = self._members[signal.strategy_id]
            weight = (
                member.dynamic_weight if self._enable_dynamic_weights else member.weight
            )
            weights[signal.strategy_id] = weight

        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # 计算相关性惩罚
        correlation_penalty = self._calculate_correlation_penalty(signals)

        # 计算加权方向
        long_score = 0.0
        short_score = 0.0

        for signal in signals:
            w = weights.get(signal.strategy_id, 0.0)
            if signal.direction == SignalDirection.LONG:
                long_score += w * signal.strength * signal.confidence
            elif signal.direction == SignalDirection.SHORT:
                short_score += w * signal.strength * signal.confidence

        # 应用相关性惩罚
        long_score *= 1 - correlation_penalty
        short_score *= 1 - correlation_penalty

        # 确定最终方向
        if long_score > short_score and long_score > 0.1:
            direction = SignalDirection.LONG
            strength = long_score
        elif short_score > long_score and short_score > 0.1:
            direction = SignalDirection.SHORT
            strength = short_score
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        # 计算融合置信度
        confidence = sum(
            weights.get(s.strategy_id, 0.0) * s.confidence for s in signals
        )

        contributing = tuple(s.strategy_id for s in signals)

        return FederationSignal(
            symbol=symbol,
            direction=direction,
            strength=min(1.0, strength),
            confidence=min(1.0, confidence),
            contributing_strategies=contributing,
            weights=weights,
            correlation_penalty=correlation_penalty,
            timestamp=timestamp,
        )

    def _calculate_correlation_penalty(self, signals: list[StrategySignal]) -> float:
        """计算相关性惩罚 (M20).

        参数:
            signals: 策略信号列表

        返回:
            惩罚系数 (0-1)
        """
        if len(signals) < 2:
            return 0.0

        total_correlation = 0.0
        pair_count = 0

        for i, signal_a in enumerate(signals):
            for signal_b in signals[i + 1 :]:
                correlation = self._correlation_matrix.get_correlation(
                    signal_a.strategy_id, signal_b.strategy_id
                )
                if correlation > self._correlation_threshold:
                    total_correlation += correlation
                    pair_count += 1

        if pair_count == 0:
            return 0.0

        # 惩罚系数 = 平均超阈值相关性 * 0.5
        avg_correlation = total_correlation / pair_count
        return min(0.5, avg_correlation * 0.5)

    def _update_correlation_matrix(self) -> None:
        """更新相关性矩阵."""
        strategy_ids = list(self._signal_history.keys())
        n = len(strategy_ids)

        if n < 2:
            return

        # 检查是否有足够的历史数据
        min_history = min(len(self._signal_history[sid]) for sid in strategy_ids)
        if min_history < 10:
            return

        # 构建相关性矩阵
        matrix = np.eye(n)

        for i in range(n):
            for j in range(i + 1, n):
                hist_i = np.array(self._signal_history[strategy_ids[i]][-min_history:])
                hist_j = np.array(self._signal_history[strategy_ids[j]][-min_history:])

                if len(hist_i) > 1 and len(hist_j) > 1:
                    # 计算皮尔逊相关系数
                    std_i = np.std(hist_i)
                    std_j = np.std(hist_j)
                    if std_i > 0 and std_j > 0:
                        correlation = np.corrcoef(hist_i, hist_j)[0, 1]
                        if not np.isnan(correlation):
                            matrix[i, j] = correlation
                            matrix[j, i] = correlation

        self._correlation_matrix = CorrelationMatrix(
            strategy_ids=strategy_ids,
            matrix=matrix,
            last_update=datetime.now().isoformat(),  # noqa: DTZ005
        )

    def update_dynamic_weights(self, performance: dict[str, float]) -> None:
        """更新动态权重 (基于策略表现).

        参数:
            performance: 策略ID -> 表现分数 (如夏普比率)
        """
        if not self._enable_dynamic_weights:
            return

        # 归一化表现分数
        total_perf = sum(max(0, p) for p in performance.values())
        if total_perf == 0:
            return

        for strategy_id, perf in performance.items():
            if strategy_id in self._members:
                # 动态权重 = 基础权重 * (1 + 表现因子)
                base_weight = self._members[strategy_id].weight
                perf_factor = max(0, perf) / total_perf
                self._members[strategy_id].dynamic_weight = base_weight * (
                    0.5 + perf_factor
                )

    def record_hit(self, strategy_id: str) -> None:
        """记录策略命中."""
        if strategy_id in self._members:
            self._members[strategy_id].hit_count += 1

    def register_callback(self, callback: Callable[[FederationSignal], None]) -> None:
        """注册信号回调."""
        self._on_signal_callbacks.append(callback)

    def _notify_signal(self, signal: FederationSignal) -> None:
        """通知信号."""
        for callback in self._on_signal_callbacks:
            with contextlib.suppress(Exception):
                callback(signal)

    def get_member(self, strategy_id: str) -> StrategyMember | None:
        """获取成员策略."""
        return self._members.get(strategy_id)

    def get_all_members(self) -> list[StrategyMember]:
        """获取所有成员策略."""
        return list(self._members.values())

    def get_correlation(self, strategy_a: str, strategy_b: str) -> float:
        """获取策略相关性."""
        return self._correlation_matrix.get_correlation(strategy_a, strategy_b)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        return {
            "member_count": len(self._members),
            "signal_count": self._signal_count,
            "conflict_count": self._conflict_count,
            "conflict_rate": (
                self._conflict_count / self._signal_count
                if self._signal_count > 0
                else 0.0
            ),
            "correlation_threshold": self._correlation_threshold,
            "members": {
                sid: {
                    "name": m.name,
                    "weight": m.weight,
                    "dynamic_weight": m.dynamic_weight,
                    "enabled": m.enabled,
                    "hit_rate": m.hit_rate,
                }
                for sid, m in self._members.items()
            },
        }

    def reset(self) -> None:
        """重置联邦状态."""
        self._signal_count = 0
        self._conflict_count = 0
        for member in self._members.values():
            member.signal_count = 0
            member.hit_count = 0
            member.last_signal = None
        self._signal_history = {sid: [] for sid in self._members}
        self._correlation_matrix = CorrelationMatrix()


# ============================================================
# 便捷函数
# ============================================================


def create_federation(
    correlation_threshold: float = 0.3,
    min_confidence: float = 0.5,
) -> StrategyFederation:
    """创建策略联邦.

    参数:
        correlation_threshold: 相关性阈值
        min_confidence: 最小置信度

    返回:
        策略联邦实例
    """
    return StrategyFederation(
        correlation_threshold=correlation_threshold,
        min_confidence=min_confidence,
    )


def create_signal(
    strategy_id: str,
    symbol: str,
    direction: SignalDirection,
    strength: float,
    confidence: float,
) -> StrategySignal:
    """创建策略信号.

    参数:
        strategy_id: 策略ID
        symbol: 合约代码
        direction: 信号方向
        strength: 信号强度
        confidence: 置信度

    返回:
        策略信号
    """
    return StrategySignal(
        strategy_id=strategy_id,
        symbol=symbol,
        direction=direction,
        strength=strength,
        confidence=confidence,
        timestamp=datetime.now().isoformat(),  # noqa: DTZ005
    )
