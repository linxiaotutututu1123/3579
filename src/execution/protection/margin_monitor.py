"""
保证金监控模块 - MarginMonitor (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §19 保证金制度
V4 Scenarios: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL

军规 M16: 保证金实时监控 - 保证金使用率必须实时计算

功能特性:
- 实时监控保证金使用率
- 五级预警机制 (SAFE/NORMAL/WARNING/DANGER/CRITICAL)
- 开仓前保证金检查
- 追加保证金告警生成
- 强平风险预警
- 历史快照记录

保证金使用率等级 (2025年):
- SAFE: < 50% (安全)
- NORMAL: 50% - 70% (正常)
- WARNING: 70% - 85% (预警)
- DANGER: 85% - 100% (危险)
- CRITICAL: >= 100% (临界, 触发强平)

示例:
    >>> monitor = MarginMonitor()
    >>> level = monitor.update(equity=100000.0, margin_used=60000.0)
    >>> print(f"保证金使用率: {monitor.usage_ratio:.1%}, 等级: {level.value}")
    保证金使用率: 60.0%, 等级: 正常

    >>> can_open, msg = monitor.can_open_position(required_margin=30000.0)
    >>> if not can_open:
    ...     print(f"无法开仓: {msg}")
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import ClassVar


class MarginLevel(Enum):
    """保证金使用率等级枚举.

    根据最高指示文件§19保证金制度定义的五级预警机制。
    """

    SAFE = "安全"  # < 50%
    NORMAL = "正常"  # 50% - 70%
    WARNING = "预警"  # 70% - 85%
    DANGER = "危险"  # 85% - 100%
    CRITICAL = "临界"  # >= 100% (触发强平)


class MarginStatus(Enum):
    """保证金状态枚举."""

    HEALTHY = "HEALTHY"  # 健康状态, 可正常交易
    RESTRICTED = "RESTRICTED"  # 受限状态, 只能减仓
    FROZEN = "FROZEN"  # 冻结状态, 禁止交易
    MARGIN_CALL = "MARGIN_CALL"  # 追保状态, 需追加保证金
    FORCE_LIQUIDATION = "FORCE_LIQUIDATION"  # 强平状态


@dataclass(frozen=True)
class MarginConfig:
    """保证金监控配置.

    属性:
        safe_threshold: 安全阈值 (默认 0.5, 即 50%)
        normal_threshold: 正常阈值 (默认 0.7, 即 70%)
        warning_threshold: 预警阈值 (默认 0.85, 即 85%)
        danger_threshold: 危险阈值 (默认 1.0, 即 100%)
        min_available_margin: 最小可用保证金 (默认 10000)
        max_snapshot_history: 最大历史快照数量 (默认 1000)
        margin_buffer_pct: 保证金缓冲比例 (默认 0.1, 即 10%)
    """

    safe_threshold: float = 0.5
    normal_threshold: float = 0.7
    warning_threshold: float = 0.85
    danger_threshold: float = 1.0
    min_available_margin: float = 10000.0
    max_snapshot_history: int = 1000
    margin_buffer_pct: float = 0.1


@dataclass
class MarginSnapshot:
    """保证金快照.

    属性:
        timestamp: 快照时间戳
        equity: 账户权益
        margin_used: 已用保证金
        margin_available: 可用保证金
        usage_ratio: 保证金使用率
        level: 保证金等级
        status: 保证金状态
    """

    timestamp: datetime
    equity: float
    margin_used: float
    margin_available: float
    usage_ratio: float
    level: MarginLevel
    status: MarginStatus

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "margin_used": self.margin_used,
            "margin_available": self.margin_available,
            "usage_ratio": self.usage_ratio,
            "level": self.level.value,
            "status": self.status.value,
        }


@dataclass
class MarginAlert:
    """保证金告警.

    属性:
        timestamp: 告警时间戳
        level: 告警等级
        previous_level: 之前等级
        message: 告警消息
        usage_ratio: 当前使用率
        equity: 当前权益
        margin_used: 当前已用保证金
        action_required: 需要采取的行动
    """

    timestamp: datetime
    level: MarginLevel
    previous_level: MarginLevel
    message: str
    usage_ratio: float
    equity: float
    margin_used: float
    action_required: str

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "previous_level": self.previous_level.value,
            "message": self.message,
            "usage_ratio": self.usage_ratio,
            "equity": self.equity,
            "margin_used": self.margin_used,
            "action_required": self.action_required,
        }


@dataclass
class OpenPositionCheckResult:
    """开仓检查结果.

    属性:
        can_open: 是否可以开仓
        reason: 原因说明
        required_margin: 所需保证金
        available_margin: 可用保证金
        projected_usage_ratio: 预计使用率 (开仓后)
        projected_level: 预计等级 (开仓后)
    """

    can_open: bool
    reason: str
    required_margin: float
    available_margin: float
    projected_usage_ratio: float
    projected_level: MarginLevel


class MarginMonitor:
    """保证金监控器 (军规 M16).

    实时监控保证金使用情况, 提供五级预警机制, 支持开仓检查和告警生成。

    属性:
        config: 保证金配置
        usage_ratio: 当前保证金使用率
        level: 当前保证金等级
        status: 当前保证金状态
        equity: 当前账户权益
        margin_used: 当前已用保证金
        margin_available: 当前可用保证金

    示例:
        >>> monitor = MarginMonitor()
        >>> level = monitor.update(equity=100000.0, margin_used=60000.0)
        >>> print(level)  # MarginLevel.NORMAL
    """

    # 类级别常量
    LEVEL_THRESHOLDS: ClassVar[list[tuple[float, MarginLevel]]] = [
        (0.5, MarginLevel.SAFE),
        (0.7, MarginLevel.NORMAL),
        (0.85, MarginLevel.WARNING),
        (1.0, MarginLevel.DANGER),
    ]

    LEVEL_ACTIONS: ClassVar[dict[MarginLevel, str]] = {
        MarginLevel.SAFE: "正常交易",
        MarginLevel.NORMAL: "正常交易, 注意仓位控制",
        MarginLevel.WARNING: "建议减仓, 避免新开仓",
        MarginLevel.DANGER: "立即减仓, 禁止开仓",
        MarginLevel.CRITICAL: "触发强平, 紧急平仓",
    }

    def __init__(self, config: MarginConfig | None = None) -> None:
        """初始化保证金监控器.

        参数:
            config: 保证金配置, 默认使用 MarginConfig()
        """
        self.config = config or MarginConfig()
        self._equity: float = 0.0
        self._margin_used: float = 0.0
        self._margin_available: float = 0.0
        self._usage_ratio: float = 0.0
        self._level: MarginLevel = MarginLevel.SAFE
        self._status: MarginStatus = MarginStatus.HEALTHY
        self._previous_level: MarginLevel = MarginLevel.SAFE
        self._snapshots: deque[MarginSnapshot] = deque(maxlen=self.config.max_snapshot_history)
        self._alerts: deque[MarginAlert] = deque(maxlen=100)
        self._last_update: datetime | None = None

    @property
    def usage_ratio(self) -> float:
        """获取当前保证金使用率."""
        return self._usage_ratio

    @property
    def level(self) -> MarginLevel:
        """获取当前保证金等级."""
        return self._level

    @property
    def status(self) -> MarginStatus:
        """获取当前保证金状态."""
        return self._status

    @property
    def equity(self) -> float:
        """获取当前账户权益."""
        return self._equity

    @property
    def margin_used(self) -> float:
        """获取当前已用保证金."""
        return self._margin_used

    @property
    def margin_available(self) -> float:
        """获取当前可用保证金."""
        return self._margin_available

    @property
    def previous_level(self) -> MarginLevel:
        """获取之前的保证金等级."""
        return self._previous_level

    @property
    def snapshots(self) -> list[MarginSnapshot]:
        """获取历史快照列表."""
        return list(self._snapshots)

    @property
    def alerts(self) -> list[MarginAlert]:
        """获取告警列表."""
        return list(self._alerts)

    @property
    def last_update(self) -> datetime | None:
        """获取最后更新时间."""
        return self._last_update

    def update(
        self,
        equity: float,
        margin_used: float,
        timestamp: datetime | None = None,
    ) -> MarginLevel:
        """更新保证金使用率.

        参数:
            equity: 账户权益
            margin_used: 已用保证金
            timestamp: 时间戳, 默认当前时间

        返回:
            当前保证金等级
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 保存之前的等级
        self._previous_level = self._level

        # 更新基础数据
        self._equity = max(0.0, equity)
        self._margin_used = max(0.0, margin_used)
        self._margin_available = max(0.0, self._equity - self._margin_used)

        # 计算使用率
        if self._equity > 0:
            self._usage_ratio = self._margin_used / self._equity
        else:
            # 权益为0或负数, 视为临界状态
            self._usage_ratio = 1.0 if self._margin_used > 0 else 0.0

        # 计算等级
        self._level = self._calculate_level()

        # 计算状态
        self._status = self._calculate_status()

        # 记录快照
        snapshot = MarginSnapshot(
            timestamp=timestamp,
            equity=self._equity,
            margin_used=self._margin_used,
            margin_available=self._margin_available,
            usage_ratio=self._usage_ratio,
            level=self._level,
            status=self._status,
        )
        self._snapshots.append(snapshot)

        # 检查是否需要生成告警
        if self._level != self._previous_level:
            self._generate_alert(timestamp)

        self._last_update = timestamp
        return self._level

    def _calculate_level(self) -> MarginLevel:
        """计算保证金等级.

        根据最高指示文件§19定义的阈值计算等级。
        """
        if self._usage_ratio < self.config.safe_threshold:
            return MarginLevel.SAFE
        if self._usage_ratio < self.config.normal_threshold:
            return MarginLevel.NORMAL
        if self._usage_ratio < self.config.warning_threshold:
            return MarginLevel.WARNING
        if self._usage_ratio < self.config.danger_threshold:
            return MarginLevel.DANGER
        return MarginLevel.CRITICAL

    def _calculate_status(self) -> MarginStatus:
        """计算保证金状态."""
        if self._level == MarginLevel.CRITICAL:
            return MarginStatus.FORCE_LIQUIDATION
        if self._level == MarginLevel.DANGER:
            return MarginStatus.MARGIN_CALL
        if self._level == MarginLevel.WARNING:
            return MarginStatus.RESTRICTED
        return MarginStatus.HEALTHY

    def _generate_alert(self, timestamp: datetime) -> None:
        """生成保证金告警.

        参数:
            timestamp: 告警时间戳
        """
        # 判断等级变化方向
        level_order = [
            MarginLevel.SAFE,
            MarginLevel.NORMAL,
            MarginLevel.WARNING,
            MarginLevel.DANGER,
            MarginLevel.CRITICAL,
        ]
        current_idx = level_order.index(self._level)
        previous_idx = level_order.index(self._previous_level)

        if current_idx > previous_idx:
            direction = "升级"  # 风险上升
        else:
            direction = "降级"  # 风险下降

        message = (
            f"保证金等级{direction}: {self._previous_level.value} → {self._level.value}, "
            f"使用率: {self._usage_ratio:.1%}"
        )

        alert = MarginAlert(
            timestamp=timestamp,
            level=self._level,
            previous_level=self._previous_level,
            message=message,
            usage_ratio=self._usage_ratio,
            equity=self._equity,
            margin_used=self._margin_used,
            action_required=self.LEVEL_ACTIONS[self._level],
        )
        self._alerts.append(alert)

    def can_open_position(
        self,
        required_margin: float,
    ) -> OpenPositionCheckResult:
        """检查是否可以开仓.

        参数:
            required_margin: 开仓所需保证金

        返回:
            OpenPositionCheckResult 包含检查结果和详细信息
        """
        # 检查是否处于可交易状态
        if self._status in (
            MarginStatus.FROZEN,
            MarginStatus.FORCE_LIQUIDATION,
        ):
            return OpenPositionCheckResult(
                can_open=False,
                reason=f"当前状态 {self._status.value} 禁止开仓",
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=self._usage_ratio,
                projected_level=self._level,
            )

        # 检查是否处于受限状态
        if self._status == MarginStatus.MARGIN_CALL:
            return OpenPositionCheckResult(
                can_open=False,
                reason="当前处于追保状态, 禁止开仓, 请追加保证金",
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=self._usage_ratio,
                projected_level=self._level,
            )

        if self._status == MarginStatus.RESTRICTED:
            return OpenPositionCheckResult(
                can_open=False,
                reason="当前处于受限状态, 建议减仓而非开仓",
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=self._usage_ratio,
                projected_level=self._level,
            )

        # 计算开仓后的保证金使用率
        projected_margin_used = self._margin_used + required_margin
        projected_usage_ratio = projected_margin_used / self._equity if self._equity > 0 else 1.0

        # 计算开仓后的等级
        projected_level = self._calculate_projected_level(projected_usage_ratio)

        # 添加缓冲区检查 - 确保有足够的保证金缓冲
        buffer_margin = required_margin * self.config.margin_buffer_pct
        required_with_buffer = required_margin + buffer_margin

        # 检查可用保证金是否足够
        if self._margin_available < required_with_buffer:
            return OpenPositionCheckResult(
                can_open=False,
                reason=(
                    f"可用保证金不足, 需要 {required_with_buffer:.2f} "
                    f"(含 {self.config.margin_buffer_pct:.0%} 缓冲), "
                    f"当前可用 {self._margin_available:.2f}"
                ),
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=projected_usage_ratio,
                projected_level=projected_level,
            )

        # 检查最小可用保证金
        remaining = self._margin_available - required_margin
        if remaining < self.config.min_available_margin:
            return OpenPositionCheckResult(
                can_open=False,
                reason=(
                    f"开仓后可用保证金 {remaining:.2f} "
                    f"低于最小要求 {self.config.min_available_margin:.2f}"
                ),
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=projected_usage_ratio,
                projected_level=projected_level,
            )

        # 检查开仓后是否会进入危险等级
        if projected_level in (MarginLevel.DANGER, MarginLevel.CRITICAL):
            return OpenPositionCheckResult(
                can_open=False,
                reason=(
                    f"开仓后保证金使用率 {projected_usage_ratio:.1%} "
                    f"将进入 {projected_level.value} 等级"
                ),
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=projected_usage_ratio,
                projected_level=projected_level,
            )

        # 检查开仓后是否会进入预警等级 (允许但警告)
        if projected_level == MarginLevel.WARNING:
            return OpenPositionCheckResult(
                can_open=True,
                reason=(
                    f"警告: 开仓后保证金使用率 {projected_usage_ratio:.1%} "
                    f"将进入 {projected_level.value} 等级, 请谨慎操作"
                ),
                required_margin=required_margin,
                available_margin=self._margin_available,
                projected_usage_ratio=projected_usage_ratio,
                projected_level=projected_level,
            )

        # 正常情况 - 可以开仓
        return OpenPositionCheckResult(
            can_open=True,
            reason="保证金检查通过",
            required_margin=required_margin,
            available_margin=self._margin_available,
            projected_usage_ratio=projected_usage_ratio,
            projected_level=projected_level,
        )

    def _calculate_projected_level(self, usage_ratio: float) -> MarginLevel:
        """计算预计的保证金等级.

        参数:
            usage_ratio: 预计使用率

        返回:
            预计的保证金等级
        """
        if usage_ratio < self.config.safe_threshold:
            return MarginLevel.SAFE
        if usage_ratio < self.config.normal_threshold:
            return MarginLevel.NORMAL
        if usage_ratio < self.config.warning_threshold:
            return MarginLevel.WARNING
        if usage_ratio < self.config.danger_threshold:
            return MarginLevel.DANGER
        return MarginLevel.CRITICAL

    def get_available_margin(self) -> float:
        """获取可用保证金.

        返回:
            可用保证金金额
        """
        return self._margin_available

    def get_margin_summary(self) -> dict[str, object]:
        """获取保证金摘要信息.

        返回:
            包含保证金详细信息的字典
        """
        return {
            "equity": self._equity,
            "margin_used": self._margin_used,
            "margin_available": self._margin_available,
            "usage_ratio": self._usage_ratio,
            "usage_ratio_pct": f"{self._usage_ratio:.1%}",
            "level": self._level.value,
            "status": self._status.value,
            "action_required": self.LEVEL_ACTIONS[self._level],
            "last_update": (self._last_update.isoformat() if self._last_update else None),
            "alert_count": len(self._alerts),
        }

    def get_risk_indicator(self) -> float:
        """获取风险指标 (0-1).

        将保证金使用率映射到 0-1 的风险指标。

        返回:
            风险指标, 0表示最安全, 1表示最危险
        """
        # 将使用率映射到 0-1, 超过100%时截断为1
        return min(1.0, self._usage_ratio)

    def should_reduce_position(self) -> tuple[bool, str]:
        """判断是否应该减仓.

        返回:
            (是否应该减仓, 原因说明)
        """
        if self._level == MarginLevel.CRITICAL:
            return True, "保证金已临界, 必须立即减仓"
        if self._level == MarginLevel.DANGER:
            return True, "保证金危险, 强烈建议减仓"
        if self._level == MarginLevel.WARNING:
            return True, "保证金预警, 建议适当减仓"
        return False, "保证金充足, 无需减仓"

    def get_recommended_reduce_pct(self) -> float:
        """获取建议减仓比例.

        根据当前保证金等级计算建议减仓比例。

        返回:
            建议减仓比例 (0-1)
        """
        if self._level == MarginLevel.CRITICAL:
            # 紧急情况, 减仓到安全水平
            target_ratio = self.config.safe_threshold
            excess = self._usage_ratio - target_ratio
            return min(1.0, excess / self._usage_ratio) if self._usage_ratio > 0 else 0.5
        if self._level == MarginLevel.DANGER:
            # 危险等级, 减仓到正常水平
            target_ratio = self.config.normal_threshold
            excess = self._usage_ratio - target_ratio
            return min(0.5, excess / self._usage_ratio) if self._usage_ratio > 0 else 0.3
        if self._level == MarginLevel.WARNING:
            # 预警等级, 减仓到安全水平
            target_ratio = self.config.safe_threshold
            excess = self._usage_ratio - target_ratio
            return min(0.3, excess / self._usage_ratio) if self._usage_ratio > 0 else 0.2
        return 0.0

    def reset(self) -> None:
        """重置监控器状态."""
        self._equity = 0.0
        self._margin_used = 0.0
        self._margin_available = 0.0
        self._usage_ratio = 0.0
        self._level = MarginLevel.SAFE
        self._status = MarginStatus.HEALTHY
        self._previous_level = MarginLevel.SAFE
        self._snapshots.clear()
        self._alerts.clear()
        self._last_update = None

    def clear_alerts(self) -> int:
        """清除所有告警.

        返回:
            清除的告警数量
        """
        count = len(self._alerts)
        self._alerts.clear()
        return count


# ============================================================
# 模块级便捷函数
# ============================================================

# 默认监控器单例
_default_monitor: MarginMonitor | None = None


def get_default_monitor() -> MarginMonitor:
    """获取默认保证金监控器 (单例模式).

    返回:
        默认的 MarginMonitor 实例
    """
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = MarginMonitor()
    return _default_monitor


def check_margin(
    equity: float,
    margin_used: float,
) -> tuple[MarginLevel, str]:
    """检查保证金使用情况 (便捷函数).

    参数:
        equity: 账户权益
        margin_used: 已用保证金

    返回:
        (保证金等级, 建议行动)
    """
    monitor = get_default_monitor()
    level = monitor.update(equity=equity, margin_used=margin_used)
    action = MarginMonitor.LEVEL_ACTIONS[level]
    return level, action


def can_open(
    required_margin: float,
    equity: float | None = None,
    margin_used: float | None = None,
) -> tuple[bool, str]:
    """检查是否可以开仓 (便捷函数).

    参数:
        required_margin: 开仓所需保证金
        equity: 账户权益 (可选, 若提供则先更新)
        margin_used: 已用保证金 (可选, 若提供则先更新)

    返回:
        (是否可以开仓, 原因说明)
    """
    monitor = get_default_monitor()

    # 如果提供了权益和保证金, 先更新
    if equity is not None and margin_used is not None:
        monitor.update(equity=equity, margin_used=margin_used)

    result = monitor.can_open_position(required_margin=required_margin)
    return result.can_open, result.reason
