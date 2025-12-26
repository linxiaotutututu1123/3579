"""
动态保证金监控器 (军规级 v4.3).

V4PRO Platform Component - Phase 9 保证金监控动态化
V4 SPEC: D9 动态保证金监控, M16 保证金实时监控

功能特性:
- 实时保证金使用率计算
- 多级告警机制 (70%/80%/90%/95%)
- 追保预警生成
- 强平风险评估
- 与 AdaptiveVaRScheduler 集成
- 动态阈值调整

军规覆盖:
- M6: 熔断保护 - 极端保证金告警触发熔断
- M16: 保证金监控 - 实时使用率计算和多级告警
- M19: 风险归因 - 保证金不足原因分析

中国期货交易所保证金规则:
- 交易保证金 = 合约价值 * 保证金比例
- 维持保证金 = 交易保证金 * 维持比例 (通常75%-80%)
- 追保线: 风险度 >= 100%
- 强平线: 风险度 >= 强平阈值 (交易所规定)

示例:
    >>> from src.risk.margin_monitor import DynamicMarginMonitor, MarginAlertLevel
    >>> monitor = DynamicMarginMonitor()
    >>> result = monitor.update_margin_status(
    ...     equity=1000000.0,
    ...     margin_used=750000.0,
    ...     margin_frozen=50000.0,
    ... )
    >>> print(f"告警级别: {result.alert_level.value}, 使用率: {result.usage_ratio:.1%}")
    告警级别: WARNING, 使用率: 75.0%

    # 与 AdaptiveVaRScheduler 集成
    >>> from src.risk.adaptive_var import AdaptiveVaRScheduler, EventType
    >>> scheduler = AdaptiveVaRScheduler()
    >>> monitor.integrate_var_scheduler(scheduler)
    >>> # 保证金告警自动触发VaR重算
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.risk.adaptive_var import AdaptiveVaRScheduler


class MarginAlertLevel(Enum):
    """保证金告警级别枚举.

    根据 D9 设计规范定义的五级告警机制。

    属性:
        SAFE: 安全 - 使用率 < 70%
        WARNING: 预警 - 使用率 70%-80%
        DANGER: 危险 - 使用率 80%-90%
        CRITICAL: 临界 - 使用率 90%-95%
        FORCE_CLOSE: 强平 - 使用率 > 95%
    """

    SAFE = "安全"  # < 70%
    WARNING = "预警"  # 70% - 80%
    DANGER = "危险"  # 80% - 90%
    CRITICAL = "临界"  # 90% - 95%
    FORCE_CLOSE = "强平"  # > 95%


class MarginRiskAction(Enum):
    """保证金风险处置动作枚举."""

    NONE = "无需处置"  # 安全状态
    MONITOR = "加强监控"  # 预警状态
    REDUCE_POSITION = "减仓"  # 危险状态
    MARGIN_CALL = "追加保证金"  # 临界状态
    FORCE_LIQUIDATE = "强制平仓"  # 强平状态


class MarginCallReason(Enum):
    """追保原因枚举."""

    HIGH_USAGE = "使用率过高"
    PRICE_VOLATILITY = "价格波动加剧"
    LIMIT_HIT = "触及涨跌停"
    VAR_SPIKE = "VaR急剧上升"
    EXCHANGE_ADJUSTMENT = "交易所调整保证金"


@dataclass(frozen=True)
class DynamicMarginConfig:
    """动态保证金监控配置.

    D9设计规范: 动态保证金监控阈值

    属性:
        safe_threshold: 安全阈值 (默认 0.70, 即 70%)
        warning_threshold: 预警阈值 (默认 0.80, 即 80%)
        danger_threshold: 危险阈值 (默认 0.90, 即 90%)
        critical_threshold: 临界阈值 (默认 0.95, 即 95%)
        force_close_threshold: 强平阈值 (默认 1.00, 即 100%)
        margin_call_buffer: 追保缓冲比例 (默认 0.05, 即 5%)
        update_interval_ms: 更新间隔毫秒 (默认 500ms)
        history_size: 历史记录大小 (默认 1000)
        var_trigger_threshold: 触发VaR重算的使用率变化阈值 (默认 0.05)
    """

    # 告警阈值
    safe_threshold: float = 0.70
    warning_threshold: float = 0.80
    danger_threshold: float = 0.90
    critical_threshold: float = 0.95
    force_close_threshold: float = 1.00

    # 追保配置
    margin_call_buffer: float = 0.05  # 追保缓冲

    # 监控配置
    update_interval_ms: int = 500  # 更新间隔
    history_size: int = 1000  # 历史记录大小

    # VaR集成配置
    var_trigger_threshold: float = 0.05  # 触发VaR重算的阈值


@dataclass
class MarginSnapshot:
    """保证金快照.

    属性:
        timestamp: 快照时间戳
        equity: 账户权益
        margin_used: 已用保证金
        margin_frozen: 冻结保证金
        margin_available: 可用保证金
        usage_ratio: 使用率
        alert_level: 告警级别
        risk_action: 风险处置动作
    """

    timestamp: datetime
    equity: float
    margin_used: float
    margin_frozen: float
    margin_available: float
    usage_ratio: float
    alert_level: MarginAlertLevel
    risk_action: MarginRiskAction

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": round(self.equity, 2),
            "margin_used": round(self.margin_used, 2),
            "margin_frozen": round(self.margin_frozen, 2),
            "margin_available": round(self.margin_available, 2),
            "usage_ratio": round(self.usage_ratio, 4),
            "usage_ratio_pct": f"{self.usage_ratio:.2%}",
            "alert_level": self.alert_level.value,
            "risk_action": self.risk_action.value,
        }


@dataclass
class MarginCallAlert:
    """追保告警.

    属性:
        timestamp: 告警时间
        alert_level: 告警级别
        previous_level: 之前级别
        usage_ratio: 当前使用率
        required_margin: 需追加保证金金额
        reason: 追保原因
        message: 告警消息
        urgency_score: 紧急程度 (0-1)
    """

    timestamp: datetime
    alert_level: MarginAlertLevel
    previous_level: MarginAlertLevel
    usage_ratio: float
    required_margin: float
    reason: MarginCallReason
    message: str
    urgency_score: float = 0.0

    def __post_init__(self) -> None:
        """计算紧急程度."""
        level_urgency = {
            MarginAlertLevel.SAFE: 0.0,
            MarginAlertLevel.WARNING: 0.3,
            MarginAlertLevel.DANGER: 0.6,
            MarginAlertLevel.CRITICAL: 0.85,
            MarginAlertLevel.FORCE_CLOSE: 1.0,
        }
        self.urgency_score = level_urgency.get(self.alert_level, 0.5)

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "alert_level": self.alert_level.value,
            "previous_level": self.previous_level.value,
            "usage_ratio": round(self.usage_ratio, 4),
            "usage_ratio_pct": f"{self.usage_ratio:.2%}",
            "required_margin": round(self.required_margin, 2),
            "reason": self.reason.value,
            "message": self.message,
            "urgency_score": round(self.urgency_score, 2),
        }


@dataclass
class ForceCloseRisk:
    """强平风险评估结果.

    属性:
        risk_score: 强平风险评分 (0-1)
        probability: 强平概率估计
        time_to_force_close_hours: 预计距强平时间 (小时)
        suggested_reduce_ratio: 建议减仓比例
        affected_positions: 受影响持仓列表
        escape_actions: 脱困措施建议
    """

    risk_score: float
    probability: float
    time_to_force_close_hours: float | None
    suggested_reduce_ratio: float
    affected_positions: list[str] = field(default_factory=list)
    escape_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "risk_score": round(self.risk_score, 4),
            "probability": round(self.probability, 4),
            "probability_pct": f"{self.probability:.2%}",
            "time_to_force_close_hours": (
                round(self.time_to_force_close_hours, 1)
                if self.time_to_force_close_hours is not None
                else None
            ),
            "suggested_reduce_ratio": round(self.suggested_reduce_ratio, 4),
            "suggested_reduce_pct": f"{self.suggested_reduce_ratio:.1%}",
            "affected_positions": self.affected_positions,
            "escape_actions": self.escape_actions,
        }


@dataclass
class MarginUpdateResult:
    """保证金更新结果.

    属性:
        success: 是否更新成功
        alert_level: 当前告警级别
        previous_level: 之前告警级别
        usage_ratio: 当前使用率
        level_changed: 级别是否变化
        alert_generated: 是否生成了告警
        var_trigger_needed: 是否需要触发VaR重算
        force_close_risk: 强平风险评估 (如果有)
    """

    success: bool
    alert_level: MarginAlertLevel
    previous_level: MarginAlertLevel
    usage_ratio: float
    level_changed: bool
    alert_generated: bool
    var_trigger_needed: bool
    force_close_risk: ForceCloseRisk | None = None

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "success": self.success,
            "alert_level": self.alert_level.value,
            "previous_level": self.previous_level.value,
            "usage_ratio": round(self.usage_ratio, 4),
            "usage_ratio_pct": f"{self.usage_ratio:.2%}",
            "level_changed": self.level_changed,
            "alert_generated": self.alert_generated,
            "var_trigger_needed": self.var_trigger_needed,
            "force_close_risk": (
                self.force_close_risk.to_dict() if self.force_close_risk else None
            ),
        }


class DynamicMarginMonitor:
    """动态保证金监控器 (军规 M16/M6/M19).

    实时监控保证金使用情况，提供多级告警机制，支持追保预警和强平风险评估。
    可与 AdaptiveVaRScheduler 集成，在保证金告警时触发VaR重算。

    功能:
    - 实时保证金使用率计算
    - 多级告警 (70%/80%/90%/95%)
    - 追保预警生成
    - 强平风险评估
    - 与 AdaptiveVaRScheduler 集成

    示例:
        >>> monitor = DynamicMarginMonitor()
        >>> result = monitor.update_margin_status(
        ...     equity=1000000.0,
        ...     margin_used=750000.0,
        ... )
        >>> print(f"级别: {result.alert_level.value}")
        级别: 预警
    """

    # 类级别常量
    LEVEL_THRESHOLDS: ClassVar[list[tuple[float, MarginAlertLevel]]] = [
        (0.70, MarginAlertLevel.SAFE),
        (0.80, MarginAlertLevel.WARNING),
        (0.90, MarginAlertLevel.DANGER),
        (0.95, MarginAlertLevel.CRITICAL),
    ]

    LEVEL_ACTIONS: ClassVar[dict[MarginAlertLevel, MarginRiskAction]] = {
        MarginAlertLevel.SAFE: MarginRiskAction.NONE,
        MarginAlertLevel.WARNING: MarginRiskAction.MONITOR,
        MarginAlertLevel.DANGER: MarginRiskAction.REDUCE_POSITION,
        MarginAlertLevel.CRITICAL: MarginRiskAction.MARGIN_CALL,
        MarginAlertLevel.FORCE_CLOSE: MarginRiskAction.FORCE_LIQUIDATE,
    }

    LEVEL_DESCRIPTIONS: ClassVar[dict[MarginAlertLevel, str]] = {
        MarginAlertLevel.SAFE: "保证金充足，正常交易",
        MarginAlertLevel.WARNING: "保证金使用率偏高，加强监控",
        MarginAlertLevel.DANGER: "保证金使用率危险，建议减仓",
        MarginAlertLevel.CRITICAL: "保证金使用率临界，需追加保证金",
        MarginAlertLevel.FORCE_CLOSE: "保证金不足，触发强制平仓",
    }

    def __init__(
        self,
        config: DynamicMarginConfig | None = None,
        var_scheduler: AdaptiveVaRScheduler | None = None,
    ) -> None:
        """初始化动态保证金监控器.

        参数:
            config: 监控配置
            var_scheduler: 自适应VaR调度器 (可选集成)
        """
        self._config = config or DynamicMarginConfig()
        self._var_scheduler = var_scheduler

        # 当前状态
        self._equity: float = 0.0
        self._margin_used: float = 0.0
        self._margin_frozen: float = 0.0
        self._margin_available: float = 0.0
        self._usage_ratio: float = 0.0
        self._alert_level: MarginAlertLevel = MarginAlertLevel.SAFE
        self._previous_level: MarginAlertLevel = MarginAlertLevel.SAFE
        self._previous_usage_ratio: float = 0.0

        # 历史记录
        self._snapshots: deque[MarginSnapshot] = deque(
            maxlen=self._config.history_size
        )
        self._alerts: deque[MarginCallAlert] = deque(maxlen=100)

        # 时间追踪
        self._last_update_time: float = 0.0
        self._last_update_timestamp: datetime | None = None

        # 回调
        self._alert_callbacks: list[Callable[[MarginCallAlert], None]] = []
        self._level_change_callbacks: list[
            Callable[[MarginAlertLevel, MarginAlertLevel], None]
        ] = []

        # 统计
        self._update_count: int = 0
        self._alert_count: int = 0
        self._force_close_warning_count: int = 0

        # 线程安全
        self._lock = threading.Lock()

    @property
    def config(self) -> DynamicMarginConfig:
        """获取配置."""
        return self._config

    @property
    def equity(self) -> float:
        """获取当前权益."""
        return self._equity

    @property
    def margin_used(self) -> float:
        """获取已用保证金."""
        return self._margin_used

    @property
    def margin_frozen(self) -> float:
        """获取冻结保证金."""
        return self._margin_frozen

    @property
    def margin_available(self) -> float:
        """获取可用保证金."""
        return self._margin_available

    @property
    def usage_ratio(self) -> float:
        """获取使用率."""
        return self._usage_ratio

    @property
    def alert_level(self) -> MarginAlertLevel:
        """获取当前告警级别."""
        return self._alert_level

    @property
    def previous_level(self) -> MarginAlertLevel:
        """获取之前告警级别."""
        return self._previous_level

    @property
    def snapshots(self) -> list[MarginSnapshot]:
        """获取历史快照."""
        return list(self._snapshots)

    @property
    def alerts(self) -> list[MarginCallAlert]:
        """获取告警列表."""
        return list(self._alerts)

    @property
    def last_update_timestamp(self) -> datetime | None:
        """获取最后更新时间."""
        return self._last_update_timestamp

    def integrate_var_scheduler(self, scheduler: AdaptiveVaRScheduler) -> None:
        """集成自适应VaR调度器.

        参数:
            scheduler: AdaptiveVaRScheduler 实例
        """
        self._var_scheduler = scheduler

    def update_margin_status(
        self,
        equity: float,
        margin_used: float,
        margin_frozen: float = 0.0,
        timestamp: datetime | None = None,
        returns: list[float] | None = None,
    ) -> MarginUpdateResult:
        """更新保证金状态.

        参数:
            equity: 账户权益
            margin_used: 已用保证金
            margin_frozen: 冻结保证金 (可选)
            timestamp: 时间戳 (可选)
            returns: 收益率序列 (用于VaR触发)

        返回:
            MarginUpdateResult 更新结果
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        with self._lock:
            # 保存之前状态
            self._previous_level = self._alert_level
            self._previous_usage_ratio = self._usage_ratio

            # 更新基础数据
            self._equity = max(0.0, equity)
            self._margin_used = max(0.0, margin_used)
            self._margin_frozen = max(0.0, margin_frozen)
            self._margin_available = max(
                0.0, self._equity - self._margin_used - self._margin_frozen
            )

            # 计算使用率
            self._usage_ratio = self._calculate_usage_ratio()

            # 计算告警级别
            self._alert_level = self._calculate_alert_level()

            # 获取风险处置动作
            risk_action = self.LEVEL_ACTIONS[self._alert_level]

            # 记录快照
            snapshot = MarginSnapshot(
                timestamp=timestamp,
                equity=self._equity,
                margin_used=self._margin_used,
                margin_frozen=self._margin_frozen,
                margin_available=self._margin_available,
                usage_ratio=self._usage_ratio,
                alert_level=self._alert_level,
                risk_action=risk_action,
            )
            self._snapshots.append(snapshot)

            # 检查级别变化
            level_changed = self._alert_level != self._previous_level
            alert_generated = False

            if level_changed:
                alert = self._generate_margin_call_alert(timestamp)
                if alert:
                    self._alerts.append(alert)
                    self._alert_count += 1
                    alert_generated = True
                    self._notify_alert(alert)
                self._notify_level_change(self._previous_level, self._alert_level)

            # 检查是否需要触发VaR重算
            var_trigger_needed = self._should_trigger_var()

            # 如果需要且有调度器，触发VaR重算
            if var_trigger_needed and self._var_scheduler and returns:
                self._trigger_var_recalculation(returns)

            # 评估强平风险 (危险及以上级别)
            force_close_risk = None
            if self._alert_level in (
                MarginAlertLevel.DANGER,
                MarginAlertLevel.CRITICAL,
                MarginAlertLevel.FORCE_CLOSE,
            ):
                force_close_risk = self._assess_force_close_risk()
                if self._alert_level == MarginAlertLevel.FORCE_CLOSE:
                    self._force_close_warning_count += 1

            # 更新时间
            self._last_update_time = time.time() * 1000
            self._last_update_timestamp = timestamp
            self._update_count += 1

            return MarginUpdateResult(
                success=True,
                alert_level=self._alert_level,
                previous_level=self._previous_level,
                usage_ratio=self._usage_ratio,
                level_changed=level_changed,
                alert_generated=alert_generated,
                var_trigger_needed=var_trigger_needed,
                force_close_risk=force_close_risk,
            )

    def _calculate_usage_ratio(self) -> float:
        """计算保证金使用率.

        使用率 = (已用保证金 + 冻结保证金) / 权益

        返回:
            使用率 (0-1+)
        """
        total_margin = self._margin_used + self._margin_frozen
        if self._equity > 0:
            return total_margin / self._equity
        # 权益为0或负数时
        return 1.0 if total_margin > 0 else 0.0

    def _calculate_alert_level(self) -> MarginAlertLevel:
        """计算告警级别.

        根据 D9 设计规范的阈值计算。

        返回:
            告警级别
        """
        if self._usage_ratio < self._config.safe_threshold:
            return MarginAlertLevel.SAFE
        if self._usage_ratio < self._config.warning_threshold:
            return MarginAlertLevel.WARNING
        if self._usage_ratio < self._config.danger_threshold:
            return MarginAlertLevel.DANGER
        if self._usage_ratio < self._config.critical_threshold:
            return MarginAlertLevel.CRITICAL
        return MarginAlertLevel.FORCE_CLOSE

    def _generate_margin_call_alert(self, timestamp: datetime) -> MarginCallAlert | None:
        """生成追保告警.

        参数:
            timestamp: 告警时间

        返回:
            追保告警对象 (如果需要)
        """
        # 判断级别变化方向
        level_order = [
            MarginAlertLevel.SAFE,
            MarginAlertLevel.WARNING,
            MarginAlertLevel.DANGER,
            MarginAlertLevel.CRITICAL,
            MarginAlertLevel.FORCE_CLOSE,
        ]
        current_idx = level_order.index(self._alert_level)
        previous_idx = level_order.index(self._previous_level)

        # 只在级别升高时生成追保告警
        if current_idx <= previous_idx:
            return None

        # 计算需追加保证金
        required_margin = self._calculate_required_margin()

        # 确定追保原因
        reason = self._determine_margin_call_reason()

        # 生成消息
        direction = "升级"
        message = (
            f"保证金告警{direction}: {self._previous_level.value} → {self._alert_level.value}, "
            f"使用率: {self._usage_ratio:.1%}, "
            f"需追加: {required_margin:.2f}"
        )

        return MarginCallAlert(
            timestamp=timestamp,
            alert_level=self._alert_level,
            previous_level=self._previous_level,
            usage_ratio=self._usage_ratio,
            required_margin=required_margin,
            reason=reason,
            message=message,
        )

    def _calculate_required_margin(self) -> float:
        """计算需追加的保证金金额.

        计算回到安全水平所需的追加金额。

        返回:
            需追加保证金金额
        """
        if self._usage_ratio <= self._config.safe_threshold:
            return 0.0

        # 目标使用率 = 安全阈值 - 缓冲
        target_ratio = self._config.safe_threshold - self._config.margin_call_buffer
        target_ratio = max(0.1, target_ratio)  # 最低10%

        # 当前总保证金
        total_margin = self._margin_used + self._margin_frozen

        # 计算目标权益 (使得 total_margin / target_equity = target_ratio)
        target_equity = total_margin / target_ratio

        # 需追加金额 = 目标权益 - 当前权益
        required = target_equity - self._equity

        return max(0.0, required)

    def _determine_margin_call_reason(self) -> MarginCallReason:
        """确定追保原因.

        返回:
            追保原因
        """
        # 根据使用率变化速度判断
        usage_change = self._usage_ratio - self._previous_usage_ratio

        if usage_change > 0.10:
            return MarginCallReason.PRICE_VOLATILITY
        if self._usage_ratio >= 0.95:
            return MarginCallReason.HIGH_USAGE

        return MarginCallReason.HIGH_USAGE

    def _should_trigger_var(self) -> bool:
        """判断是否应该触发VaR重算.

        触发条件:
        - 使用率变化超过阈值
        - 进入危险或更高级别
        - 从低级别跳升到高级别

        返回:
            是否应该触发
        """
        # 使用率变化超过阈值
        usage_change = abs(self._usage_ratio - self._previous_usage_ratio)
        if usage_change >= self._config.var_trigger_threshold:
            return True

        # 进入危险级别
        if self._alert_level in (
            MarginAlertLevel.DANGER,
            MarginAlertLevel.CRITICAL,
            MarginAlertLevel.FORCE_CLOSE,
        ):
            # 如果之前不在危险级别，触发
            if self._previous_level in (
                MarginAlertLevel.SAFE,
                MarginAlertLevel.WARNING,
            ):
                return True

        return False

    def _trigger_var_recalculation(self, returns: list[float]) -> None:
        """触发VaR重算.

        参数:
            returns: 收益率序列
        """
        if self._var_scheduler is None:
            return

        # 导入在这里避免循环依赖
        from src.risk.adaptive_var import EventType

        self._var_scheduler.trigger_event(
            EventType.MARGIN_WARNING,
            returns,
            margin_usage_ratio=self._usage_ratio,
            alert_level=self._alert_level.value,
        )

    def _assess_force_close_risk(self) -> ForceCloseRisk:
        """评估强平风险.

        返回:
            强平风险评估结果
        """
        # 计算风险评分 (基于使用率)
        if self._usage_ratio < self._config.safe_threshold:
            risk_score = 0.0
        elif self._usage_ratio < self._config.warning_threshold:
            risk_score = 0.2
        elif self._usage_ratio < self._config.danger_threshold:
            risk_score = 0.4
        elif self._usage_ratio < self._config.critical_threshold:
            risk_score = 0.7
        else:
            risk_score = min(1.0, self._usage_ratio)

        # 估算强平概率
        probability = self._estimate_force_close_probability()

        # 估算距强平时间
        time_to_force_close = self._estimate_time_to_force_close()

        # 计算建议减仓比例
        suggested_reduce = self._calculate_suggested_reduce_ratio()

        # 生成脱困措施
        escape_actions = self._generate_escape_actions()

        return ForceCloseRisk(
            risk_score=risk_score,
            probability=probability,
            time_to_force_close_hours=time_to_force_close,
            suggested_reduce_ratio=suggested_reduce,
            affected_positions=[],  # 需要外部提供持仓信息
            escape_actions=escape_actions,
        )

    def _estimate_force_close_probability(self) -> float:
        """估算强平概率.

        基于当前使用率和历史趋势估算。

        返回:
            强平概率 (0-1)
        """
        if self._usage_ratio >= self._config.force_close_threshold:
            return 1.0

        # 计算距强平阈值的距离
        distance = self._config.force_close_threshold - self._usage_ratio

        # 基于历史趋势调整
        if len(self._snapshots) >= 2:
            recent_snapshots = list(self._snapshots)[-10:]
            if len(recent_snapshots) >= 2:
                first_ratio = recent_snapshots[0].usage_ratio
                last_ratio = recent_snapshots[-1].usage_ratio
                trend = last_ratio - first_ratio

                if trend > 0:
                    # 上升趋势，增加概率
                    trend_factor = min(0.5, trend * 2)
                else:
                    # 下降趋势，降低概率
                    trend_factor = max(-0.3, trend)
            else:
                trend_factor = 0.0
        else:
            trend_factor = 0.0

        # 基础概率 = 1 - distance (距离越近概率越高)
        base_probability = max(0.0, 1.0 - distance * 2)

        # 调整后概率
        adjusted = base_probability + trend_factor
        return max(0.0, min(1.0, adjusted))

    def _estimate_time_to_force_close(self) -> float | None:
        """估算距强平时间.

        返回:
            预计时间 (小时) 或 None (无法估算)
        """
        if self._usage_ratio >= self._config.force_close_threshold:
            return 0.0

        if len(self._snapshots) < 3:
            return None

        # 计算使用率变化速度
        recent_snapshots = list(self._snapshots)[-10:]
        if len(recent_snapshots) < 2:
            return None

        first = recent_snapshots[0]
        last = recent_snapshots[-1]

        time_diff = (last.timestamp - first.timestamp).total_seconds()
        if time_diff <= 0:
            return None

        ratio_diff = last.usage_ratio - first.usage_ratio

        if ratio_diff <= 0:
            # 使用率在下降，不会触发强平
            return None

        # 计算速度 (每秒变化率)
        speed = ratio_diff / time_diff

        # 计算距强平的距离
        distance = self._config.force_close_threshold - self._usage_ratio

        # 预计时间 (秒 -> 小时)
        time_seconds = distance / speed
        time_hours = time_seconds / 3600

        return max(0.0, time_hours)

    def _calculate_suggested_reduce_ratio(self) -> float:
        """计算建议减仓比例.

        返回:
            建议减仓比例 (0-1)
        """
        if self._usage_ratio < self._config.warning_threshold:
            return 0.0

        # 目标使用率
        target_ratio = self._config.safe_threshold - self._config.margin_call_buffer

        if self._usage_ratio <= target_ratio:
            return 0.0

        # 需要减少的保证金比例
        excess_ratio = self._usage_ratio - target_ratio
        reduce_ratio = excess_ratio / self._usage_ratio

        return min(1.0, max(0.0, reduce_ratio))

    def _generate_escape_actions(self) -> list[str]:
        """生成脱困措施建议.

        返回:
            脱困措施列表
        """
        actions = []

        if self._alert_level == MarginAlertLevel.FORCE_CLOSE:
            actions.append("立即平掉亏损最大的持仓")
            actions.append("平掉保证金占用最高的持仓")
            actions.append("联系期货公司追加保证金")
        elif self._alert_level == MarginAlertLevel.CRITICAL:
            actions.append("追加保证金至安全水平")
            actions.append("减仓高风险持仓")
            actions.append("关注市场波动，准备应对")
        elif self._alert_level == MarginAlertLevel.DANGER:
            actions.append("考虑追加保证金")
            actions.append("评估持仓风险，适当减仓")
            actions.append("设置止损单保护")
        elif self._alert_level == MarginAlertLevel.WARNING:
            actions.append("加强监控保证金使用情况")
            actions.append("避免新开仓位")
            actions.append("准备追加保证金资金")

        return actions

    def register_alert_callback(
        self, callback: Callable[[MarginCallAlert], None]
    ) -> None:
        """注册告警回调.

        参数:
            callback: 回调函数
        """
        self._alert_callbacks.append(callback)

    def register_level_change_callback(
        self, callback: Callable[[MarginAlertLevel, MarginAlertLevel], None]
    ) -> None:
        """注册级别变化回调.

        参数:
            callback: 回调函数 (old_level, new_level)
        """
        self._level_change_callbacks.append(callback)

    def _notify_alert(self, alert: MarginCallAlert) -> None:
        """通知告警."""
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass  # 回调错误不影响主流程

    def _notify_level_change(
        self, old_level: MarginAlertLevel, new_level: MarginAlertLevel
    ) -> None:
        """通知级别变化."""
        for callback in self._level_change_callbacks:
            try:
                callback(old_level, new_level)
            except Exception:
                pass  # 回调错误不影响主流程

    def get_current_status(self) -> dict[str, Any]:
        """获取当前状态.

        返回:
            状态字典
        """
        return {
            "equity": round(self._equity, 2),
            "margin_used": round(self._margin_used, 2),
            "margin_frozen": round(self._margin_frozen, 2),
            "margin_available": round(self._margin_available, 2),
            "usage_ratio": round(self._usage_ratio, 4),
            "usage_ratio_pct": f"{self._usage_ratio:.2%}",
            "alert_level": self._alert_level.value,
            "risk_action": self.LEVEL_ACTIONS[self._alert_level].value,
            "description": self.LEVEL_DESCRIPTIONS[self._alert_level],
            "last_update": (
                self._last_update_timestamp.isoformat()
                if self._last_update_timestamp
                else None
            ),
        }

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "update_count": self._update_count,
            "alert_count": self._alert_count,
            "force_close_warning_count": self._force_close_warning_count,
            "snapshot_count": len(self._snapshots),
            "current_level": self._alert_level.value,
            "config": {
                "safe_threshold": self._config.safe_threshold,
                "warning_threshold": self._config.warning_threshold,
                "danger_threshold": self._config.danger_threshold,
                "critical_threshold": self._config.critical_threshold,
                "force_close_threshold": self._config.force_close_threshold,
            },
        }

    def get_trend_analysis(self, lookback: int = 20) -> dict[str, Any]:
        """获取趋势分析.

        参数:
            lookback: 回看记录数

        返回:
            趋势分析结果
        """
        if len(self._snapshots) < 2:
            return {
                "trend": "unknown",
                "change_rate": 0.0,
                "samples": 0,
            }

        recent = list(self._snapshots)[-lookback:]
        if len(recent) < 2:
            return {
                "trend": "unknown",
                "change_rate": 0.0,
                "samples": len(recent),
            }

        first_ratio = recent[0].usage_ratio
        last_ratio = recent[-1].usage_ratio
        change = last_ratio - first_ratio

        # 计算时间跨度
        time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
        if time_span > 0:
            change_rate_per_hour = (change / time_span) * 3600
        else:
            change_rate_per_hour = 0.0

        # 判断趋势
        if abs(change) < 0.01:
            trend = "stable"
        elif change > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # 计算波动
        ratios = [s.usage_ratio for s in recent]
        if len(ratios) >= 2:
            mean = sum(ratios) / len(ratios)
            variance = sum((r - mean) ** 2 for r in ratios) / (len(ratios) - 1)
            volatility = variance ** 0.5
        else:
            volatility = 0.0

        return {
            "trend": trend,
            "change": round(change, 4),
            "change_pct": f"{change:.2%}",
            "change_rate_per_hour": round(change_rate_per_hour, 4),
            "volatility": round(volatility, 4),
            "min_ratio": round(min(ratios), 4),
            "max_ratio": round(max(ratios), 4),
            "samples": len(recent),
        }

    def clear_alerts(self) -> int:
        """清除告警.

        返回:
            清除的告警数
        """
        with self._lock:
            count = len(self._alerts)
            self._alerts.clear()
            return count

    def reset(self) -> None:
        """重置监控器."""
        with self._lock:
            self._equity = 0.0
            self._margin_used = 0.0
            self._margin_frozen = 0.0
            self._margin_available = 0.0
            self._usage_ratio = 0.0
            self._alert_level = MarginAlertLevel.SAFE
            self._previous_level = MarginAlertLevel.SAFE
            self._previous_usage_ratio = 0.0
            self._snapshots.clear()
            self._alerts.clear()
            self._last_update_time = 0.0
            self._last_update_timestamp = None
            self._update_count = 0
            self._alert_count = 0
            self._force_close_warning_count = 0

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式.

        返回:
            审计日志字典
        """
        return {
            "event_type": "DYNAMIC_MARGIN_MONITOR",
            "timestamp": (
                self._last_update_timestamp.isoformat()
                if self._last_update_timestamp
                else datetime.now().isoformat()  # noqa: DTZ005
            ),
            "equity": round(self._equity, 2),
            "margin_used": round(self._margin_used, 2),
            "margin_frozen": round(self._margin_frozen, 2),
            "usage_ratio": round(self._usage_ratio, 4),
            "alert_level": self._alert_level.value,
            "update_count": self._update_count,
            "alert_count": self._alert_count,
            "force_close_warnings": self._force_close_warning_count,
        }


# ============================================================
# 便捷函数
# ============================================================

# 默认监控器单例
_default_dynamic_monitor: DynamicMarginMonitor | None = None


def get_default_dynamic_monitor() -> DynamicMarginMonitor:
    """获取默认动态保证金监控器.

    返回:
        DynamicMarginMonitor 单例
    """
    global _default_dynamic_monitor
    if _default_dynamic_monitor is None:
        _default_dynamic_monitor = DynamicMarginMonitor()
    return _default_dynamic_monitor


def create_dynamic_margin_monitor(
    safe_threshold: float = 0.70,
    warning_threshold: float = 0.80,
    danger_threshold: float = 0.90,
    critical_threshold: float = 0.95,
    var_scheduler: AdaptiveVaRScheduler | None = None,
) -> DynamicMarginMonitor:
    """创建动态保证金监控器.

    参数:
        safe_threshold: 安全阈值
        warning_threshold: 预警阈值
        danger_threshold: 危险阈值
        critical_threshold: 临界阈值
        var_scheduler: 可选的VaR调度器

    返回:
        DynamicMarginMonitor 实例
    """
    config = DynamicMarginConfig(
        safe_threshold=safe_threshold,
        warning_threshold=warning_threshold,
        danger_threshold=danger_threshold,
        critical_threshold=critical_threshold,
    )
    return DynamicMarginMonitor(config=config, var_scheduler=var_scheduler)


def quick_margin_check(
    equity: float,
    margin_used: float,
    margin_frozen: float = 0.0,
) -> tuple[MarginAlertLevel, str]:
    """快速保证金检查.

    参数:
        equity: 账户权益
        margin_used: 已用保证金
        margin_frozen: 冻结保证金

    返回:
        (告警级别, 建议)
    """
    monitor = get_default_dynamic_monitor()
    result = monitor.update_margin_status(
        equity=equity,
        margin_used=margin_used,
        margin_frozen=margin_frozen,
    )
    description = DynamicMarginMonitor.LEVEL_DESCRIPTIONS[result.alert_level]
    return result.alert_level, description


def assess_force_close_risk(
    equity: float,
    margin_used: float,
    margin_frozen: float = 0.0,
) -> ForceCloseRisk:
    """评估强平风险.

    参数:
        equity: 账户权益
        margin_used: 已用保证金
        margin_frozen: 冻结保证金

    返回:
        ForceCloseRisk 评估结果
    """
    monitor = get_default_dynamic_monitor()
    result = monitor.update_margin_status(
        equity=equity,
        margin_used=margin_used,
        margin_frozen=margin_frozen,
    )
    if result.force_close_risk:
        return result.force_close_risk
    return ForceCloseRisk(
        risk_score=0.0,
        probability=0.0,
        time_to_force_close_hours=None,
        suggested_reduce_ratio=0.0,
    )
