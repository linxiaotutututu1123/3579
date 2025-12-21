"""
信号仲裁器模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: Section 29 信号融合

军规覆盖:
- M1: 单一信号源 - 确保每个信号源唯一，去重合并
- M3: 审计日志 - 所有操作记录完整可追溯
- M6: 熔断保护 - 异常时触发熔断保护机制

功能特性:
- 信号去重 (相同方向合并)
- 冲突检测 (LONG vs SHORT)
- 优先级排序 (权重+置信度)
- 相关性惩罚 (降低高相关策略权重)
- 生成唯一联邦信号

示例:
    >>> from src.strategy.federation.arbiter import SignalArbiter
    >>> arbiter = SignalArbiter(registry=registry)
    >>> result = arbiter.arbitrate(signals)
    >>> if result.success:
    ...     print(f"Federation signal: {result.signal}")
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from src.strategy.federation.central_coordinator import (
    FederationSignal,
    SignalDirection,
    StrategySignal,
)
from src.strategy.federation.models import (
    AuditEntry,
    AuditEventType,
    ConflictRecord,
    ConflictType,
    ResolutionAction,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from src.strategy.federation.registry import StrategyRegistry


class ArbiterStatus(Enum):
    """仲裁器状态枚举."""

    NORMAL = "NORMAL"  # 正常运行
    DEGRADED = "DEGRADED"  # 降级模式
    CIRCUIT_BREAK = "CIRCUIT_BREAK"  # 熔断状态


class ArbiterDecision(Enum):
    """仲裁决策类型."""

    ACCEPT = "ACCEPT"  # 接受信号
    REJECT = "REJECT"  # 拒绝信号
    MERGE = "MERGE"  # 合并信号
    FLAT = "FLAT"  # 强制平仓


@dataclass
class ArbiterConfig:
    """仲裁器配置.

    属性:
        correlation_threshold: 相关性惩罚阈值 (默认0.3)
        min_confidence: 最小置信度门槛 (默认0.5)
        conflict_threshold: 冲突数触发熔断阈值 (默认5)
        circuit_break_duration: 熔断持续时间(秒) (默认60)
        max_signals_per_symbol: 每个品种最大信号数 (默认10)
        dedup_window: 去重时间窗口(秒) (默认1.0)
    """

    correlation_threshold: float = 0.3
    min_confidence: float = 0.5
    conflict_threshold: int = 5
    circuit_break_duration: float = 60.0
    max_signals_per_symbol: int = 10
    dedup_window: float = 1.0


@dataclass
class ArbitrationResult:
    """仲裁结果.

    属性:
        success: 是否成功生成信号
        signal: 联邦融合信号
        conflicts: 检测到的冲突列表
        decisions: 决策记录
        audit_entries: 审计记录
        timestamp: 仲裁时间戳
    """

    success: bool
    signal: FederationSignal | None = None
    conflicts: list[ConflictRecord] = field(default_factory=list)
    decisions: dict[str, ArbiterDecision] = field(default_factory=dict)
    audit_entries: list[AuditEntry] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "success": self.success,
            "signal": self.signal.to_audit_dict() if self.signal else None,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "decisions": {k: v.value for k, v in self.decisions.items()},
            "audit_entries": [e.to_dict() for e in self.audit_entries],
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SignalKey:
    """信号唯一键 (用于去重).

    属性:
        strategy_id: 策略ID
        symbol: 合约代码
        direction: 信号方向
    """

    strategy_id: str
    symbol: str
    direction: SignalDirection


class SignalArbiter:
    """信号仲裁器 - 解决多策略信号冲突 (M1/M3/M6 合规).

    核心职责:
    - 信号去重: 确保每个策略每个方向仅一个有效信号 (M1)
    - 冲突检测: 识别 LONG vs SHORT 等冲突类型
    - 优先级排序: 基于权重和置信度排序
    - 相关性惩罚: 降低高相关策略的权重
    - 审计日志: 记录所有操作 (M3)
    - 熔断保护: 异常时触发熔断 (M6)

    仲裁流程:
        1. 信号去重 (相同方向合并)
        2. 冲突检测 (LONG vs SHORT)
        3. 优先级排序 (权重+置信度)
        4. 相关性惩罚 (降低高相关策略权重)
        5. 生成唯一联邦信号

    示例:
        >>> registry = StrategyRegistry()
        >>> registry.register("kalman_arb", weight=0.3)
        >>> arbiter = SignalArbiter(registry=registry)
        >>> result = arbiter.arbitrate(signals)
        >>> print(f"Success: {result.success}")
    """

    # 类级常量
    DEFAULT_CONFIG: ClassVar[ArbiterConfig] = ArbiterConfig()

    def __init__(
        self,
        registry: StrategyRegistry | None = None,
        config: ArbiterConfig | None = None,
        audit_logger: Callable[[AuditEntry], None] | None = None,
        circuit_break_callback: Callable[[], None] | None = None,
    ) -> None:
        """初始化信号仲裁器.

        参数:
            registry: 策略注册中心 (可选)
            config: 仲裁器配置 (可选，使用默认值)
            audit_logger: 审计日志回调 (M3)
            circuit_break_callback: 熔断触发回调 (M6)
        """
        self._lock = threading.RLock()
        self._registry = registry
        self._config = config or ArbiterConfig()
        self._audit_logger = audit_logger
        self._circuit_break_callback = circuit_break_callback

        # 状态管理
        self._status = ArbiterStatus.NORMAL
        self._circuit_break_until: float = 0.0

        # 统计数据
        self._arbitration_count: int = 0
        self._conflict_count: int = 0
        self._signal_count: int = 0
        self._reject_count: int = 0

        # 最近冲突记录 (用于熔断判断)
        self._recent_conflicts: list[float] = []

        # 信号缓存 (用于去重)
        self._signal_cache: dict[SignalKey, tuple[StrategySignal, float]] = {}

    @property
    def status(self) -> ArbiterStatus:
        """获取仲裁器状态."""
        with self._lock:
            # 检查熔断是否已过期
            if (
                self._status == ArbiterStatus.CIRCUIT_BREAK
                and time.time() > self._circuit_break_until
            ):
                self._status = ArbiterStatus.NORMAL
                self._log_audit(
                    AuditEventType.CIRCUIT_BREAK_RECOVERED,
                    action="circuit_break_expired",
                    result="recovered",
                )
            return self._status

    @property
    def statistics(self) -> dict[str, Any]:
        """获取统计数据."""
        with self._lock:
            return {
                "status": self._status.value,
                "arbitration_count": self._arbitration_count,
                "conflict_count": self._conflict_count,
                "signal_count": self._signal_count,
                "reject_count": self._reject_count,
                "conflict_rate": (
                    self._conflict_count / self._arbitration_count
                    if self._arbitration_count > 0
                    else 0.0
                ),
                "reject_rate": (
                    self._reject_count / self._signal_count
                    if self._signal_count > 0
                    else 0.0
                ),
            }

    def arbitrate(
        self,
        signals: list[StrategySignal],
        symbol: str | None = None,
    ) -> ArbitrationResult:
        """主仲裁方法 - 解决多策略信号冲突.

        仲裁流程:
            1. 检查熔断状态
            2. 信号预处理和去重 (M1)
            3. 冲突检测
            4. 冲突解决
            5. 信号融合
            6. 记录审计日志 (M3)
            7. 检查熔断条件 (M6)

        参数:
            signals: 策略信号列表
            symbol: 合约代码 (可选，用于过滤)

        返回:
            ArbitrationResult: 仲裁结果
        """
        with self._lock:
            self._arbitration_count += 1
            timestamp = time.time()
            audit_entries: list[AuditEntry] = []
            conflicts: list[ConflictRecord] = []
            decisions: dict[str, ArbiterDecision] = {}

            # 1. 检查熔断状态
            if self.status == ArbiterStatus.CIRCUIT_BREAK:
                entry = self._create_audit_entry(
                    AuditEventType.SIGNAL_REJECTED,
                    action="arbitrate",
                    result="rejected_circuit_break",
                    details={"reason": "circuit_breaker_active"},
                )
                audit_entries.append(entry)
                self._log_audit_entry(entry)

                return ArbitrationResult(
                    success=False,
                    signal=None,
                    conflicts=[],
                    decisions={s.strategy_id: ArbiterDecision.REJECT for s in signals},
                    audit_entries=audit_entries,
                    timestamp=timestamp,
                )

            # 2. 信号预处理
            if not signals:
                return ArbitrationResult(
                    success=False,
                    signal=None,
                    audit_entries=audit_entries,
                    timestamp=timestamp,
                )

            # 过滤和去重
            filtered_signals = self._filter_signals(signals, symbol)
            deduplicated_signals = self._deduplicate_signals(filtered_signals)

            self._signal_count += len(deduplicated_signals)

            if not deduplicated_signals:
                return ArbitrationResult(
                    success=False,
                    signal=None,
                    audit_entries=audit_entries,
                    timestamp=timestamp,
                )

            # 记录信号提交审计
            for signal in deduplicated_signals:
                entry = self._create_audit_entry(
                    AuditEventType.SIGNAL_SUBMITTED,
                    strategy_id=signal.strategy_id,
                    action="submit_signal",
                    result="accepted",
                    details=signal.to_dict(),
                )
                audit_entries.append(entry)
                self._log_audit_entry(entry)

            # 3. 冲突检测
            conflict = self.detect_conflict(deduplicated_signals)
            if conflict is not None:
                conflicts.append(conflict)
                self._conflict_count += 1
                self._recent_conflicts.append(timestamp)

                # 记录冲突审计
                entry = self._create_audit_entry(
                    AuditEventType.CONFLICT_DETECTED,
                    action="detect_conflict",
                    result=conflict.conflict_type.value,
                    details=conflict.to_dict(),
                )
                audit_entries.append(entry)
                self._log_audit_entry(entry)

            # 4. 冲突解决
            resolved_signals = deduplicated_signals
            if conflict is not None:
                resolution = self.resolve_conflict(conflict, deduplicated_signals)
                resolved_signals, decisions = resolution

                # 记录解决审计
                entry = self._create_audit_entry(
                    AuditEventType.CONFLICT_RESOLVED,
                    action="resolve_conflict",
                    result=conflict.resolution.value,
                    details={
                        "conflict_id": conflict.conflict_id,
                        "winner_signal_id": conflict.winner_signal_id,
                        "decisions": {k: v.value for k, v in decisions.items()},
                    },
                )
                audit_entries.append(entry)
                self._log_audit_entry(entry)

            # 5. 信号融合
            if not resolved_signals:
                return ArbitrationResult(
                    success=False,
                    signal=None,
                    conflicts=conflicts,
                    decisions=decisions,
                    audit_entries=audit_entries,
                    timestamp=timestamp,
                )

            fused_signal = self._fuse_signals(resolved_signals)

            # 记录融合信号审计
            entry = self._create_audit_entry(
                AuditEventType.SIGNAL_VALIDATED,
                action="fuse_signals",
                result="success",
                details=fused_signal.to_audit_dict() if fused_signal else {},
            )
            audit_entries.append(entry)
            self._log_audit_entry(entry)

            # 6. 检查熔断条件
            self._check_circuit_break(timestamp)

            return ArbitrationResult(
                success=fused_signal is not None,
                signal=fused_signal,
                conflicts=conflicts,
                decisions=decisions,
                audit_entries=audit_entries,
                timestamp=timestamp,
            )

    def detect_conflict(
        self,
        signals: list[StrategySignal],
    ) -> ConflictRecord | None:
        """检测信号冲突.

        冲突类型:
        - DIRECTION: LONG vs SHORT 方向冲突
        - DUPLICATE: 同一策略重复信号
        - RATE_LIMIT: 信号频率超限

        参数:
            signals: 策略信号列表

        返回:
            ConflictRecord 或 None (无冲突)
        """
        if len(signals) < 2:
            return None

        # 按方向分组
        long_signals = [s for s in signals if s.direction == SignalDirection.LONG]
        short_signals = [s for s in signals if s.direction == SignalDirection.SHORT]

        # 检测方向冲突
        if long_signals and short_signals:
            conflict_id = str(uuid.uuid4())[:8]
            all_signal_ids = [
                f"{s.strategy_id}:{s.symbol}" for s in long_signals + short_signals
            ]
            all_strategy_ids = list(
                {s.strategy_id for s in long_signals + short_signals}
            )
            symbol = signals[0].symbol if signals else ""

            return ConflictRecord(
                conflict_id=conflict_id,
                conflict_type=ConflictType.DIRECTION,
                signal_ids=tuple(all_signal_ids),
                strategy_ids=tuple(all_strategy_ids),
                symbol=symbol,
                resolution=ResolutionAction.DEFER,  # 待解决
                timestamp=time.time(),
                details={
                    "long_count": len(long_signals),
                    "short_count": len(short_signals),
                    "long_strategies": [s.strategy_id for s in long_signals],
                    "short_strategies": [s.strategy_id for s in short_signals],
                },
            )

        # 检测重复信号 (同一策略多个信号)
        strategy_counts: dict[str, int] = {}
        for signal in signals:
            strategy_counts[signal.strategy_id] = (
                strategy_counts.get(signal.strategy_id, 0) + 1
            )

        duplicates = {sid: cnt for sid, cnt in strategy_counts.items() if cnt > 1}
        if duplicates:
            conflict_id = str(uuid.uuid4())[:8]
            symbol = signals[0].symbol if signals else ""

            return ConflictRecord(
                conflict_id=conflict_id,
                conflict_type=ConflictType.DUPLICATE,
                signal_ids=tuple(f"{s.strategy_id}:{s.symbol}" for s in signals),
                strategy_ids=tuple(duplicates.keys()),
                symbol=symbol,
                resolution=ResolutionAction.DEFER,
                timestamp=time.time(),
                details={"duplicate_counts": duplicates},
            )

        return None

    def resolve_conflict(
        self,
        conflict: ConflictRecord,
        signals: list[StrategySignal],
    ) -> tuple[list[StrategySignal], dict[str, ArbiterDecision]]:
        """解决信号冲突.

        解决策略:
        - DIRECTION 冲突: 基于优先级分数选择胜者
        - DUPLICATE 冲突: 保留最高置信度信号
        - 其他: 默认接受最高优先级

        参数:
            conflict: 冲突记录
            signals: 原始信号列表

        返回:
            (解决后的信号列表, 决策记录)
        """
        decisions: dict[str, ArbiterDecision] = {}

        if conflict.conflict_type == ConflictType.DIRECTION:
            # 方向冲突: 计算综合优先级分数
            long_signals = [s for s in signals if s.direction == SignalDirection.LONG]
            short_signals = [s for s in signals if s.direction == SignalDirection.SHORT]

            long_score = self._calculate_group_score(long_signals)
            short_score = self._calculate_group_score(short_signals)

            if long_score > short_score:
                winner_signals = long_signals
                loser_signals = short_signals
            elif short_score > long_score:
                winner_signals = short_signals
                loser_signals = long_signals
            else:
                # 相等时强制平仓
                for signal in signals:
                    decisions[signal.strategy_id] = ArbiterDecision.FLAT
                return [], decisions

            # 记录决策
            for signal in winner_signals:
                decisions[signal.strategy_id] = ArbiterDecision.ACCEPT
            for signal in loser_signals:
                decisions[signal.strategy_id] = ArbiterDecision.REJECT
                self._reject_count += 1

            return winner_signals, decisions

        elif conflict.conflict_type == ConflictType.DUPLICATE:
            # 重复信号: 每个策略保留最高置信度
            best_by_strategy: dict[str, StrategySignal] = {}
            for signal in signals:
                existing = best_by_strategy.get(signal.strategy_id)
                if existing is None or signal.confidence > existing.confidence:
                    best_by_strategy[signal.strategy_id] = signal

            for signal in signals:
                if best_by_strategy.get(signal.strategy_id) == signal:
                    decisions[signal.strategy_id] = ArbiterDecision.ACCEPT
                else:
                    decisions[signal.strategy_id] = ArbiterDecision.REJECT
                    self._reject_count += 1

            return list(best_by_strategy.values()), decisions

        else:
            # 默认: 接受最高优先级信号
            if signals:
                best_signal = max(signals, key=lambda s: self._get_priority_score(s))
                decisions[best_signal.strategy_id] = ArbiterDecision.ACCEPT
                for signal in signals:
                    if signal != best_signal:
                        decisions[signal.strategy_id] = ArbiterDecision.REJECT
                        self._reject_count += 1
                return [best_signal], decisions

            return [], decisions

    def trigger_circuit_break(self, reason: str = "manual") -> None:
        """触发熔断保护 (M6).

        参数:
            reason: 熔断原因
        """
        with self._lock:
            self._status = ArbiterStatus.CIRCUIT_BREAK
            self._circuit_break_until = time.time() + self._config.circuit_break_duration

            # 记录审计日志
            self._log_audit(
                AuditEventType.CIRCUIT_BREAK_TRIGGERED,
                action="trigger_circuit_break",
                result="triggered",
                details={
                    "reason": reason,
                    "duration": self._config.circuit_break_duration,
                    "until": self._circuit_break_until,
                },
            )

            # 触发回调
            if self._circuit_break_callback:
                try:
                    self._circuit_break_callback()
                except Exception:
                    pass  # 忽略回调异常

    def reset_circuit_break(self) -> None:
        """重置熔断状态."""
        with self._lock:
            self._status = ArbiterStatus.NORMAL
            self._circuit_break_until = 0.0
            self._recent_conflicts.clear()

            self._log_audit(
                AuditEventType.CIRCUIT_BREAK_RECOVERED,
                action="reset_circuit_break",
                result="reset",
            )

    def _filter_signals(
        self,
        signals: list[StrategySignal],
        symbol: str | None = None,
    ) -> list[StrategySignal]:
        """过滤信号.

        过滤条件:
        - 置信度 >= 最小置信度
        - 策略已注册且启用 (如有注册中心)
        - 符号匹配 (如指定)

        参数:
            signals: 原始信号列表
            symbol: 合约代码 (可选)

        返回:
            过滤后的信号列表
        """
        filtered = []

        for signal in signals:
            # 置信度检查
            if signal.confidence < self._config.min_confidence:
                continue

            # 符号匹配
            if symbol and signal.symbol != symbol:
                continue

            # 注册中心检查
            if self._registry is not None:
                if not self._registry.is_registered(signal.strategy_id):
                    continue
                if not self._registry.is_active(signal.strategy_id):
                    continue

            filtered.append(signal)

        return filtered

    def _deduplicate_signals(
        self,
        signals: list[StrategySignal],
    ) -> list[StrategySignal]:
        """信号去重 (M1: 单一信号源).

        去重策略:
        - 同一策略、同一品种、同一方向: 保留最新/最高置信度
        - 使用时间窗口避免短时间重复

        参数:
            signals: 原始信号列表

        返回:
            去重后的信号列表
        """
        current_time = time.time()

        # 清理过期缓存
        expired_keys = [
            key
            for key, (_, ts) in self._signal_cache.items()
            if current_time - ts > self._config.dedup_window
        ]
        for key in expired_keys:
            del self._signal_cache[key]

        deduplicated: dict[SignalKey, StrategySignal] = {}

        for signal in signals:
            key = SignalKey(
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                direction=signal.direction,
            )

            # 检查缓存 (时间窗口内的重复信号)
            if key in self._signal_cache:
                cached_signal, cached_time = self._signal_cache[key]
                if current_time - cached_time < self._config.dedup_window:
                    # 保留更高置信度的信号
                    if signal.confidence <= cached_signal.confidence:
                        continue

            # 更新或添加
            existing = deduplicated.get(key)
            if existing is None or signal.confidence > existing.confidence:
                deduplicated[key] = signal
                self._signal_cache[key] = (signal, current_time)

        return list(deduplicated.values())

    def _calculate_group_score(self, signals: list[StrategySignal]) -> float:
        """计算信号组的综合分数.

        分数 = sum(权重 * 置信度 * 强度)

        参数:
            signals: 信号列表

        返回:
            综合分数
        """
        total_score = 0.0

        for signal in signals:
            weight = self._get_strategy_weight(signal.strategy_id)
            score = weight * signal.confidence * signal.strength
            total_score += score

        return total_score

    def _get_priority_score(self, signal: StrategySignal) -> float:
        """获取信号优先级分数.

        分数 = 权重 * 置信度 * 强度

        参数:
            signal: 策略信号

        返回:
            优先级分数
        """
        weight = self._get_strategy_weight(signal.strategy_id)
        return weight * signal.confidence * signal.strength

    def _get_strategy_weight(self, strategy_id: str) -> float:
        """获取策略权重.

        参数:
            strategy_id: 策略ID

        返回:
            权重值 (默认0.1)
        """
        if self._registry is not None:
            # 优先使用动态权重
            dynamic_weight = self._registry.get_dynamic_weight(strategy_id)
            if dynamic_weight > 0:
                return dynamic_weight
            return self._registry.get_weight(strategy_id)
        return 0.1

    def _fuse_signals(
        self,
        signals: list[StrategySignal],
    ) -> FederationSignal | None:
        """融合信号生成联邦信号.

        融合算法:
        1. 计算各策略权重 (含相关性惩罚)
        2. 加权平均计算方向和强度
        3. 生成联邦信号

        参数:
            signals: 策略信号列表

        返回:
            联邦融合信号
        """
        if not signals:
            return None

        # 获取权重
        weights: dict[str, float] = {}
        for signal in signals:
            weights[signal.strategy_id] = self._get_strategy_weight(signal.strategy_id)

        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        # 计算相关性惩罚
        correlation_penalty = self._calculate_correlation_penalty(signals)

        # 计算加权方向和强度
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

        # 获取品种
        symbol = signals[0].symbol if signals else ""
        contributing = tuple(s.strategy_id for s in signals)
        timestamp = datetime.now(tz=timezone.utc).isoformat()

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

    def _calculate_correlation_penalty(
        self,
        signals: list[StrategySignal],
    ) -> float:
        """计算相关性惩罚 (M20).

        惩罚策略:
        - 从注册中心获取策略相关性
        - 高相关性策略权重被降低
        - 惩罚系数 = 平均超阈值相关性 * 0.5

        参数:
            signals: 策略信号列表

        返回:
            惩罚系数 (0-0.5)
        """
        if len(signals) < 2 or self._registry is None:
            return 0.0

        total_correlation = 0.0
        pair_count = 0

        for i, signal_a in enumerate(signals):
            for signal_b in signals[i + 1 :]:
                # 从注册中心获取相关性 (如果有方法)
                # 这里使用简化逻辑：同类策略惩罚
                if signal_a.strategy_id.split("_")[0] == signal_b.strategy_id.split("_")[0]:
                    correlation = 0.5  # 同类策略默认相关性
                else:
                    correlation = 0.1  # 不同类策略默认相关性

                if correlation > self._config.correlation_threshold:
                    total_correlation += correlation
                    pair_count += 1

        if pair_count == 0:
            return 0.0

        avg_correlation = total_correlation / pair_count
        return min(0.5, avg_correlation * 0.5)

    def _check_circuit_break(self, current_time: float) -> None:
        """检查熔断条件 (M6).

        触发条件:
        - 短时间内冲突数超过阈值

        参数:
            current_time: 当前时间戳
        """
        # 清理过期冲突记录 (60秒窗口)
        window_start = current_time - 60.0
        self._recent_conflicts = [
            t for t in self._recent_conflicts if t > window_start
        ]

        # 检查是否超过阈值
        if len(self._recent_conflicts) >= self._config.conflict_threshold:
            self.trigger_circuit_break(
                reason=f"conflict_count_exceeded:{len(self._recent_conflicts)}"
            )

    def _create_audit_entry(
        self,
        event_type: AuditEventType,
        strategy_id: str = "",
        signal_id: str = "",
        action: str = "",
        result: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """创建审计日志条目.

        参数:
            event_type: 事件类型
            strategy_id: 策略ID
            signal_id: 信号ID
            action: 操作
            result: 结果
            details: 详细信息

        返回:
            审计日志条目
        """
        return AuditEntry(
            entry_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            timestamp=time.time(),
            strategy_id=strategy_id,
            signal_id=signal_id,
            action=action,
            result=result,
            details=details or {},
            operator="signal_arbiter",
        )

    def _log_audit_entry(self, entry: AuditEntry) -> None:
        """记录审计日志条目.

        参数:
            entry: 审计日志条目
        """
        if self._audit_logger:
            try:
                self._audit_logger(entry)
            except Exception:
                pass  # 忽略日志异常

    def _log_audit(
        self,
        event_type: AuditEventType,
        strategy_id: str = "",
        signal_id: str = "",
        action: str = "",
        result: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录审计日志 (M3).

        参数:
            event_type: 事件类型
            strategy_id: 策略ID
            signal_id: 信号ID
            action: 操作
            result: 结果
            details: 详细信息
        """
        entry = self._create_audit_entry(
            event_type, strategy_id, signal_id, action, result, details
        )
        self._log_audit_entry(entry)

    def reset(self) -> None:
        """重置仲裁器状态 (用于测试)."""
        with self._lock:
            self._status = ArbiterStatus.NORMAL
            self._circuit_break_until = 0.0
            self._arbitration_count = 0
            self._conflict_count = 0
            self._signal_count = 0
            self._reject_count = 0
            self._recent_conflicts.clear()
            self._signal_cache.clear()


# ============================================================
# 便捷函数
# ============================================================


def create_arbiter(
    registry: StrategyRegistry | None = None,
    config: ArbiterConfig | None = None,
    audit_logger: Callable[[AuditEntry], None] | None = None,
) -> SignalArbiter:
    """创建信号仲裁器.

    参数:
        registry: 策略注册中心
        config: 仲裁器配置
        audit_logger: 审计日志回调

    返回:
        SignalArbiter 实例
    """
    return SignalArbiter(
        registry=registry,
        config=config,
        audit_logger=audit_logger,
    )


def create_config(
    correlation_threshold: float = 0.3,
    min_confidence: float = 0.5,
    conflict_threshold: int = 5,
    circuit_break_duration: float = 60.0,
) -> ArbiterConfig:
    """创建仲裁器配置.

    参数:
        correlation_threshold: 相关性惩罚阈值
        min_confidence: 最小置信度门槛
        conflict_threshold: 冲突数触发熔断阈值
        circuit_break_duration: 熔断持续时间(秒)

    返回:
        ArbiterConfig 实例
    """
    return ArbiterConfig(
        correlation_threshold=correlation_threshold,
        min_confidence=min_confidence,
        conflict_threshold=conflict_threshold,
        circuit_break_duration=circuit_break_duration,
    )


__all__ = [
    # 枚举
    "ArbiterStatus",
    "ArbiterDecision",
    # 配置和结果
    "ArbiterConfig",
    "ArbitrationResult",
    "SignalKey",
    # 核心类
    "SignalArbiter",
    # 便捷函数
    "create_arbiter",
    "create_config",
]
