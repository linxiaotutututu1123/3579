"""
信号冲突解决模块 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制
V4 SPEC: M1军规 - 防止信号冲突

军规覆盖:
- M1: 单一信号源 - 信号冲突检测与解决
- M3: 审计日志 - 冲突记录追踪
- M7: 场景回放 - 冲突场景可回放

功能特性:
- 同一合约多信号冲突检测
- 多种冲突解决策略
- 信号优先级仲裁
- 审计日志支持

示例:
    >>> from src.strategy.signal import SignalConflictResolver, ResolutionStrategy
    >>> resolver = SignalConflictResolver(strategy=ResolutionStrategy.PRIORITY_FIRST)
    >>> resolved_signal = resolver.resolve(conflicting_signals)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    pass

from src.strategy.signal.source import (
    SignalDirection,
    SignalPriority,
    TradingSignal,
)


class ResolutionStrategy(Enum):
    """冲突解决策略枚举."""

    PRIORITY_FIRST = "PRIORITY_FIRST"  # 优先级最高者胜出
    CONFIDENCE_WEIGHTED = "CONFIDENCE_WEIGHTED"  # 置信度加权
    STRENGTH_WEIGHTED = "STRENGTH_WEIGHTED"  # 强度加权
    NEWEST_FIRST = "NEWEST_FIRST"  # 最新信号优先
    OLDEST_FIRST = "OLDEST_FIRST"  # 最早信号优先
    REJECT_ALL = "REJECT_ALL"  # 全部拒绝
    FLAT_ON_CONFLICT = "FLAT_ON_CONFLICT"  # 冲突时平仓


class ConflictType(Enum):
    """冲突类型枚举."""

    DIRECTION_CONFLICT = "DIRECTION_CONFLICT"  # 方向冲突 (多空对立)
    SOURCE_DUPLICATE = "SOURCE_DUPLICATE"  # 同源重复信号
    TIMING_CONFLICT = "TIMING_CONFLICT"  # 时序冲突 (信号时间重叠)
    SYMBOL_CONFLICT = "SYMBOL_CONFLICT"  # 多合约冲突
    PRIORITY_TIE = "PRIORITY_TIE"  # 优先级相同


class ConflictSeverity(Enum):
    """冲突严重程度枚举."""

    LOW = "LOW"  # 低严重性
    MEDIUM = "MEDIUM"  # 中等严重性
    HIGH = "HIGH"  # 高严重性
    CRITICAL = "CRITICAL"  # 严重


@dataclass(frozen=True, slots=True)
class ConflictInfo:
    """冲突信息 (不可变).

    属性:
        conflict_type: 冲突类型
        severity: 严重程度
        signals: 冲突信号列表
        symbol: 合约代码
        timestamp: 检测时间戳
        details: 详细信息
    """

    conflict_type: ConflictType
    severity: ConflictSeverity
    signals: tuple[str, ...]  # signal_ids
    symbol: str
    timestamp: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "conflict_type": self.conflict_type.value,
            "severity": self.severity.value,
            "signals": list(self.signals),
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "details": self.details,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "SIGNAL_CONFLICT_DETECTED",
            "event_time": datetime.now(tz=timezone.utc).isoformat(),
            **self.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """冲突解决结果 (不可变).

    属性:
        resolved: 是否解决成功
        winner_signal: 胜出信号
        conflict_info: 冲突信息
        resolution_strategy: 使用的解决策略
        rejected_signals: 被拒绝的信号列表
        timestamp: 解决时间戳
        details: 详细信息
    """

    resolved: bool
    winner_signal: TradingSignal | None
    conflict_info: ConflictInfo
    resolution_strategy: ResolutionStrategy
    rejected_signals: tuple[str, ...] = ()  # signal_ids
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "resolved": self.resolved,
            "winner_signal_id": (
                self.winner_signal.signal_id if self.winner_signal else None
            ),
            "conflict_info": self.conflict_info.to_dict(),
            "resolution_strategy": self.resolution_strategy.value,
            "rejected_signals": list(self.rejected_signals),
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "details": self.details,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "SIGNAL_CONFLICT_RESOLVED",
            "event_time": datetime.now(tz=timezone.utc).isoformat(),
            **self.to_dict(),
        }


@dataclass
class SignalConflictResolver:
    """信号冲突解决器 (M1军规核心组件).

    负责:
    - 检测信号冲突
    - 应用冲突解决策略
    - 选择最优信号
    - 记录冲突和解决过程

    属性:
        strategy: 解决策略
        conflict_history: 冲突历史
        resolution_history: 解决历史
    """

    # 默认配置
    DEFAULT_HISTORY_SIZE: ClassVar[int] = 1000  # 历史记录大小
    DEFAULT_CONFLICT_WINDOW: ClassVar[float] = 5.0  # 冲突检测窗口 (秒)

    # 解决策略
    strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY_FIRST

    # 配置
    conflict_window: float = field(default=5.0)

    # 内部状态
    _conflict_history: list[ConflictInfo] = field(
        default_factory=list, init=False, repr=False
    )
    _resolution_history: list[ResolutionResult] = field(
        default_factory=list, init=False, repr=False
    )
    _signal_cache: dict[str, list[TradingSignal]] = field(
        default_factory=lambda: defaultdict(list), init=False, repr=False
    )

    @property
    def conflict_count(self) -> int:
        """获取冲突总数."""
        return len(self._conflict_history)

    @property
    def resolution_count(self) -> int:
        """获取解决总数."""
        return len(self._resolution_history)

    def detect_conflicts(
        self,
        signals: list[TradingSignal],
    ) -> list[ConflictInfo]:
        """检测信号冲突.

        参数:
            signals: 信号列表

        返回:
            冲突信息列表
        """
        if len(signals) < 2:
            return []

        conflicts: list[ConflictInfo] = []

        # 按合约分组
        by_symbol: dict[str, list[TradingSignal]] = defaultdict(list)
        for signal in signals:
            by_symbol[signal.symbol].append(signal)

        for symbol, symbol_signals in by_symbol.items():
            if len(symbol_signals) < 2:
                continue

            # 检测方向冲突
            direction_conflict = self._detect_direction_conflict(symbol, symbol_signals)
            if direction_conflict:
                conflicts.append(direction_conflict)

            # 检测同源重复
            source_duplicates = self._detect_source_duplicates(symbol, symbol_signals)
            conflicts.extend(source_duplicates)

            # 检测时序冲突
            timing_conflicts = self._detect_timing_conflicts(symbol, symbol_signals)
            conflicts.extend(timing_conflicts)

        # 记录冲突历史
        self._conflict_history.extend(conflicts)
        self._trim_history()

        return conflicts

    def _detect_direction_conflict(
        self,
        symbol: str,
        signals: list[TradingSignal],
    ) -> ConflictInfo | None:
        """检测方向冲突."""
        long_signals = [s for s in signals if s.direction == SignalDirection.LONG]
        short_signals = [s for s in signals if s.direction == SignalDirection.SHORT]

        if long_signals and short_signals:
            all_signal_ids = tuple(
                s.signal_id for s in long_signals + short_signals
            )
            return ConflictInfo(
                conflict_type=ConflictType.DIRECTION_CONFLICT,
                severity=ConflictSeverity.HIGH,
                signals=all_signal_ids,
                symbol=symbol,
                timestamp=time.time(),
                details={
                    "long_count": len(long_signals),
                    "short_count": len(short_signals),
                    "long_sources": [s.source_id for s in long_signals],
                    "short_sources": [s.source_id for s in short_signals],
                },
            )
        return None

    def _detect_source_duplicates(
        self,
        symbol: str,
        signals: list[TradingSignal],
    ) -> list[ConflictInfo]:
        """检测同源重复信号."""
        conflicts = []
        by_source: dict[str, list[TradingSignal]] = defaultdict(list)

        for signal in signals:
            by_source[signal.source_id].append(signal)

        for source_id, source_signals in by_source.items():
            if len(source_signals) > 1:
                signal_ids = tuple(s.signal_id for s in source_signals)
                conflicts.append(
                    ConflictInfo(
                        conflict_type=ConflictType.SOURCE_DUPLICATE,
                        severity=ConflictSeverity.MEDIUM,
                        signals=signal_ids,
                        symbol=symbol,
                        timestamp=time.time(),
                        details={
                            "source_id": source_id,
                            "duplicate_count": len(source_signals),
                        },
                    )
                )

        return conflicts

    def _detect_timing_conflicts(
        self,
        symbol: str,
        signals: list[TradingSignal],
    ) -> list[ConflictInfo]:
        """检测时序冲突."""
        conflicts = []

        # 按时间排序
        sorted_signals = sorted(signals, key=lambda s: s.timestamp)

        for i in range(len(sorted_signals) - 1):
            current = sorted_signals[i]
            next_signal = sorted_signals[i + 1]

            time_diff = next_signal.timestamp - current.timestamp
            if time_diff < self.conflict_window:
                # 时间窗口内的信号视为潜在冲突
                if current.direction != next_signal.direction:
                    conflicts.append(
                        ConflictInfo(
                            conflict_type=ConflictType.TIMING_CONFLICT,
                            severity=ConflictSeverity.LOW,
                            signals=(current.signal_id, next_signal.signal_id),
                            symbol=symbol,
                            timestamp=time.time(),
                            details={
                                "time_diff": time_diff,
                                "window": self.conflict_window,
                            },
                        )
                    )

        return conflicts

    def resolve(
        self,
        signals: list[TradingSignal],
        strategy: ResolutionStrategy | None = None,
    ) -> ResolutionResult:
        """解决信号冲突.

        参数:
            signals: 冲突信号列表
            strategy: 解决策略 (可选, 使用默认策略)

        返回:
            ResolutionResult解决结果
        """
        if not signals:
            return ResolutionResult(
                resolved=False,
                winner_signal=None,
                conflict_info=ConflictInfo(
                    conflict_type=ConflictType.DIRECTION_CONFLICT,
                    severity=ConflictSeverity.LOW,
                    signals=(),
                    symbol="",
                    timestamp=time.time(),
                ),
                resolution_strategy=strategy or self.strategy,
                details={"error": "No signals to resolve"},
            )

        if len(signals) == 1:
            return ResolutionResult(
                resolved=True,
                winner_signal=signals[0],
                conflict_info=ConflictInfo(
                    conflict_type=ConflictType.DIRECTION_CONFLICT,
                    severity=ConflictSeverity.LOW,
                    signals=(signals[0].signal_id,),
                    symbol=signals[0].symbol,
                    timestamp=time.time(),
                ),
                resolution_strategy=strategy or self.strategy,
                details={"note": "Single signal, no conflict"},
            )

        # 检测冲突
        conflicts = self.detect_conflicts(signals)
        if not conflicts:
            # 无冲突, 选择第一个
            return ResolutionResult(
                resolved=True,
                winner_signal=signals[0],
                conflict_info=ConflictInfo(
                    conflict_type=ConflictType.DIRECTION_CONFLICT,
                    severity=ConflictSeverity.LOW,
                    signals=tuple(s.signal_id for s in signals),
                    symbol=signals[0].symbol,
                    timestamp=time.time(),
                ),
                resolution_strategy=strategy or self.strategy,
                details={"note": "No conflict detected"},
            )

        # 使用指定策略解决
        resolution_strategy = strategy or self.strategy
        primary_conflict = conflicts[0]

        # 根据策略解决冲突
        winner = self._apply_resolution_strategy(signals, resolution_strategy)

        # 构建结果
        rejected = tuple(
            s.signal_id for s in signals
            if winner is None or s.signal_id != winner.signal_id
        )

        result = ResolutionResult(
            resolved=winner is not None,
            winner_signal=winner,
            conflict_info=primary_conflict,
            resolution_strategy=resolution_strategy,
            rejected_signals=rejected,
            details={
                "conflict_count": len(conflicts),
                "signal_count": len(signals),
            },
        )

        # 记录解决历史
        self._resolution_history.append(result)
        self._trim_history()

        return result

    def _apply_resolution_strategy(
        self,
        signals: list[TradingSignal],
        strategy: ResolutionStrategy,
    ) -> TradingSignal | None:
        """应用解决策略.

        参数:
            signals: 信号列表
            strategy: 解决策略

        返回:
            胜出信号或None
        """
        if not signals:
            return None

        if strategy == ResolutionStrategy.PRIORITY_FIRST:
            # 选择优先级最高的信号
            return min(signals, key=lambda s: s.priority.value)

        elif strategy == ResolutionStrategy.CONFIDENCE_WEIGHTED:
            # 选择置信度最高的信号
            return max(signals, key=lambda s: s.confidence)

        elif strategy == ResolutionStrategy.STRENGTH_WEIGHTED:
            # 选择强度最高的信号
            return max(signals, key=lambda s: s.strength)

        elif strategy == ResolutionStrategy.NEWEST_FIRST:
            # 选择最新的信号
            return max(signals, key=lambda s: s.timestamp)

        elif strategy == ResolutionStrategy.OLDEST_FIRST:
            # 选择最早的信号
            return min(signals, key=lambda s: s.timestamp)

        elif strategy == ResolutionStrategy.REJECT_ALL:
            # 全部拒绝
            return None

        elif strategy == ResolutionStrategy.FLAT_ON_CONFLICT:
            # 创建平仓信号 (返回None让调用者处理)
            return None

        return None

    def resolve_by_priority(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """按优先级解决冲突.

        参数:
            signals: 信号列表

        返回:
            优先级最高的信号
        """
        result = self.resolve(signals, ResolutionStrategy.PRIORITY_FIRST)
        return result.winner_signal

    def resolve_by_confidence(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """按置信度解决冲突.

        参数:
            signals: 信号列表

        返回:
            置信度最高的信号
        """
        result = self.resolve(signals, ResolutionStrategy.CONFIDENCE_WEIGHTED)
        return result.winner_signal

    def resolve_by_strength(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """按强度解决冲突.

        参数:
            signals: 信号列表

        返回:
            强度最高的信号
        """
        result = self.resolve(signals, ResolutionStrategy.STRENGTH_WEIGHTED)
        return result.winner_signal

    def _trim_history(self) -> None:
        """修剪历史记录."""
        max_size = self.DEFAULT_HISTORY_SIZE
        if len(self._conflict_history) > max_size:
            self._conflict_history = self._conflict_history[-max_size:]
        if len(self._resolution_history) > max_size:
            self._resolution_history = self._resolution_history[-max_size:]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        conflict_type_counts: dict[str, int] = {}
        for conflict in self._conflict_history:
            ctype = conflict.conflict_type.value
            conflict_type_counts[ctype] = conflict_type_counts.get(ctype, 0) + 1

        resolution_success = sum(
            1 for r in self._resolution_history if r.resolved
        )

        return {
            "total_conflicts": len(self._conflict_history),
            "total_resolutions": len(self._resolution_history),
            "resolution_success_rate": (
                resolution_success / len(self._resolution_history)
                if self._resolution_history else 0.0
            ),
            "conflict_type_breakdown": conflict_type_counts,
            "current_strategy": self.strategy.value,
            "conflict_window": self.conflict_window,
        }

    def get_recent_conflicts(self, count: int = 10) -> list[ConflictInfo]:
        """获取最近的冲突."""
        return self._conflict_history[-count:]

    def get_recent_resolutions(self, count: int = 10) -> list[ResolutionResult]:
        """获取最近的解决结果."""
        return self._resolution_history[-count:]

    def clear_history(self) -> None:
        """清空历史记录."""
        self._conflict_history.clear()
        self._resolution_history.clear()

    def set_strategy(self, strategy: ResolutionStrategy) -> None:
        """设置解决策略.

        参数:
            strategy: 新的解决策略
        """
        self.strategy = strategy


# ============================================================
# 便捷函数
# ============================================================


def create_conflict_resolver(
    strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY_FIRST,
    conflict_window: float = 5.0,
) -> SignalConflictResolver:
    """创建冲突解决器.

    参数:
        strategy: 解决策略
        conflict_window: 冲突检测窗口

    返回:
        SignalConflictResolver实例
    """
    return SignalConflictResolver(
        strategy=strategy,
        conflict_window=conflict_window,
    )


def resolve_conflicts(
    signals: list[TradingSignal],
    strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY_FIRST,
) -> TradingSignal | None:
    """解决信号冲突 (便捷函数).

    参数:
        signals: 信号列表
        strategy: 解决策略

    返回:
        胜出信号或None
    """
    resolver = SignalConflictResolver(strategy=strategy)
    result = resolver.resolve(signals)
    return result.winner_signal
