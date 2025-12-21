"""
保证金监控模块 - MarginMonitor (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §19 保证金制度
V4 Scenarios: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL

军规 M16: 保证金实时监控 - 保证金使用率必须实时计算

功能特性:
- 实时计算保证金使用率
- 五级预警等级 (SAFE/NORMAL/WARNING/DANGER/CRITICAL)
- 开仓前保证金检查
- 可用保证金计算
- 历史记录追踪
- 预警事件生成

保证金等级阈值:
- SAFE: < 50% (安全)
- NORMAL: 50% - 70% (正常)
- WARNING: 70% - 85% (预警)
- DANGER: 85% - 100% (危险)
- CRITICAL: >= 100% (临界, 触发强平)

示例:
    >>> monitor = MarginMonitor()
    >>> level = monitor.update(equity=1000000.0, margin_used=600000.0)
    >>> print(level)  # MarginLevel.NORMAL (60%)
    >>> can_open, msg = monitor.can_open_position(required_margin=200000.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MarginLevel(Enum):
    """保证金使用率等级 (军规级 v4.0).

    等级定义:
    - SAFE: 使用率 < 50% (安全)
    - NORMAL: 使用率 50% - 70% (正常)
    - WARNING: 使用率 70% - 85% (预警)
    - DANGER: 使用率 85% - 100% (危险)
    - CRITICAL: 使用率 >= 100% (临界, 触发强平)
    """

    SAFE = "安全"       # < 50%
    NORMAL = "正常"     # 50% - 70%
    WARNING = "预警"    # 70% - 85%
    DANGER = "危险"     # 85% - 100%
    CRITICAL = "临界"   # >= 100%


@dataclass(frozen=True)
class MarginConfig:
    """保证金监控配置.

    属性:
        safe_threshold: 安全阈值 (默认 0.50)
        normal_threshold: 正常阈值 (默认 0.70)
        warning_threshold: 预警阈值 (默认 0.85)
        danger_threshold: 危险阈值 (默认 1.00)
        min_available_margin: 最低可用保证金 (默认 10000.0)
        enable_alerts: 是否启用告警 (默认 True)
        history_size: 历史记录大小 (默认 1000)
    """

    safe_threshold: float = 0.50
    normal_threshold: float = 0.70
    warning_threshold: float = 0.85
    danger_threshold: float = 1.00
    min_available_margin: float = 10000.0
    enable_alerts: bool = True
    history_size: int = 1000


@dataclass
class MarginSnapshot:
    """保证金快照.

    属性:
        timestamp: 时间戳
        equity: 权益
        margin_used: 已用保证金
        margin_available: 可用保证金
        usage_ratio: 使用率
        level: 等级
    """

    timestamp: datetime
    equity: float
    margin_used: float
    margin_available: float
    usage_ratio: float
    level: MarginLevel

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "margin_used": self.margin_used,
            "margin_available": self.margin_available,
            "usage_ratio": self.usage_ratio,
            "level": self.level.value,
        }


@dataclass
class MarginAlert:
    """保证金告警事件.

    属性:
        timestamp: 时间戳
        alert_type: 告警类型
        level: 当前等级
        previous_level: 前一等级
        usage_ratio: 使用率
        message: 告警消息
    """

    timestamp: datetime
    alert_type: str
    level: MarginLevel
    previous_level: MarginLevel | None
    usage_ratio: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "alert_type": self.alert_type,
            "level": self.level.value,
            "previous_level": self.previous_level.value if self.previous_level else None,
            "usage_ratio": self.usage_ratio,
            "message": self.message,
        }


@dataclass
class OpenPositionCheckResult:
    """开仓检查结果.

    属性:
        allowed: 是否允许开仓
        reason: 原因说明
        available_margin: 可用保证金
        required_margin: 所需保证金
        projected_usage: 开仓后预计使用率
        projected_level: 开仓后预计等级
    """

    allowed: bool
    reason: str
    available_margin: float = 0.0
    required_margin: float = 0.0
    projected_usage: float = 0.0
    projected_level: MarginLevel | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "available_margin": self.available_margin,
            "required_margin": self.required_margin,
            "projected_usage": self.projected_usage,
            "projected_level": self.projected_level.value if self.projected_level else None,
        }


@dataclass
class MarginStatus:
    """保证金状态 (当前状态快照).

    属性:
        equity: 权益
        margin_used: 已用保证金
        margin_available: 可用保证金
        usage_ratio: 使用率
        level: 等级
        last_update: 最后更新时间
    """

    equity: float = 0.0
    margin_used: float = 0.0
    margin_available: float = 0.0
    usage_ratio: float = 0.0
    level: MarginLevel = MarginLevel.SAFE
    last_update: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "equity": self.equity,
            "margin_used": self.margin_used,
            "margin_available": self.margin_available,
            "usage_ratio": self.usage_ratio,
            "level": self.level.value,
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }


class MarginMonitor:
    """保证金监控器 (军规级 v4.0).

    军规 M16: 保证金实时监控 - 保证金使用率必须实时计算

    V4 Scenarios:
    - CHINA.MARGIN.RATIO_CHECK: 保证金率检查
    - CHINA.MARGIN.USAGE_MONITOR: 保证金使用监控
    - CHINA.MARGIN.WARNING_LEVEL: 保证金预警等级

    功能:
    - 实时计算保证金使用率
    - 五级预警等级 (SAFE/NORMAL/WARNING/DANGER/CRITICAL)
    - 开仓前保证金检查
    - 可用保证金计算
    - 告警事件生成

    示例:
        >>> monitor = MarginMonitor()
        >>> level = monitor.update(equity=1000000.0, margin_used=600000.0)
        >>> print(level)  # MarginLevel.NORMAL
    """

    def __init__(self, config: MarginConfig | None = None) -> None:
        """初始化保证金监控器.

        参数:
            config: 保证金配置
        """
        self._config = config or MarginConfig()
        self._status = MarginStatus()
        self._history: list[MarginSnapshot] = []
        self._alerts: list[MarginAlert] = []
        self._update_count = 0
        self._level_change_count = 0

    @property
    def config(self) -> MarginConfig:
        """配置."""
        return self._config

    @property
    def status(self) -> MarginStatus:
        """当前状态."""
        return self._status

    @property
    def update_count(self) -> int:
        """更新次数."""
        return self._update_count

    @property
    def level_change_count(self) -> int:
        """等级变化次数."""
        return self._level_change_count

    def update(self, equity: float, margin_used: float) -> MarginLevel:
        """更新保证金状态.

        军规 M16: 保证金实时监控
        V4 Scenario: CHINA.MARGIN.USAGE_MONITOR

        参数:
            equity: 权益 (账户总资金)
            margin_used: 已用保证金

        返回:
            当前保证金等级
        """
        self._update_count += 1
        now = datetime.now()  # noqa: DTZ005

        # 计算使用率
        usage_ratio = margin_used / equity if equity > 0 else 1.0
        available = equity - margin_used

        # 计算等级
        # V4 Scenario: CHINA.MARGIN.RATIO_CHECK
        new_level = self._calculate_level(usage_ratio)

        # 检查等级变化, 生成告警
        previous_level = self._status.level
        if new_level != previous_level and self._update_count > 1:
            self._level_change_count += 1
            if self._config.enable_alerts:
                self._generate_alert(new_level, previous_level, usage_ratio, now)

        # 更新状态
        self._status = MarginStatus(
            equity=equity,
            margin_used=margin_used,
            margin_available=available,
            usage_ratio=usage_ratio,
            level=new_level,
            last_update=now,
        )

        # 保存历史记录
        self._add_to_history(now, equity, margin_used, available, usage_ratio, new_level)

        return new_level

    def get_level(self) -> MarginLevel:
        """获取当前保证金等级.

        V4 Scenario: CHINA.MARGIN.WARNING_LEVEL

        返回:
            当前保证金等级
        """
        return self._status.level

    def get_usage_ratio(self) -> float:
        """获取当前保证金使用率.

        返回:
            使用率 (0.0 - 1.0+)
        """
        return self._status.usage_ratio

    def get_available_margin(self) -> float:
        """获取可用保证金.

        返回:
            可用保证金金额
        """
        return self._status.margin_available

    def can_open_position(self, required_margin: float) -> tuple[bool, str]:
        """检查是否可以开仓.

        军规 M16: 保证金实时监控
        V4 Scenario: CHINA.MARGIN.RATIO_CHECK

        参数:
            required_margin: 开仓所需保证金

        返回:
            (是否允许, 原因说明)
        """
        result = self.check_open_position(required_margin)
        return result.allowed, result.reason

    def check_open_position(self, required_margin: float) -> OpenPositionCheckResult:
        """检查开仓并返回详细结果.

        参数:
            required_margin: 开仓所需保证金

        返回:
            开仓检查结果
        """
        available = self._status.margin_available
        equity = self._status.equity

        # 检查可用保证金是否足够
        if required_margin > available:
            return OpenPositionCheckResult(
                allowed=False,
                reason=f"可用保证金不足: 需要 {required_margin:.2f}, 可用 {available:.2f}",
                available_margin=available,
                required_margin=required_margin,
            )

        # 检查是否低于最低可用保证金要求
        remaining = available - required_margin
        if remaining < self._config.min_available_margin:
            return OpenPositionCheckResult(
                allowed=False,
                reason=f"开仓后可用保证金 {remaining:.2f} 低于最低要求 {self._config.min_available_margin:.2f}",
                available_margin=available,
                required_margin=required_margin,
            )

        # 计算开仓后的预计使用率和等级
        new_margin_used = self._status.margin_used + required_margin
        projected_usage = new_margin_used / equity if equity > 0 else 1.0
        projected_level = self._calculate_level(projected_usage)

        # 检查是否会进入危险区
        if projected_level == MarginLevel.CRITICAL:
            return OpenPositionCheckResult(
                allowed=False,
                reason=f"开仓后保证金使用率 {projected_usage:.2%} 将达到临界状态",
                available_margin=available,
                required_margin=required_margin,
                projected_usage=projected_usage,
                projected_level=projected_level,
            )

        # 允许开仓
        return OpenPositionCheckResult(
            allowed=True,
            reason="保证金检查通过",
            available_margin=available,
            required_margin=required_margin,
            projected_usage=projected_usage,
            projected_level=projected_level,
        )

    def is_safe(self) -> bool:
        """检查是否处于安全状态.

        返回:
            是否安全 (SAFE或NORMAL)
        """
        return self._status.level in (MarginLevel.SAFE, MarginLevel.NORMAL)

    def is_warning(self) -> bool:
        """检查是否处于预警状态.

        返回:
            是否预警 (WARNING或更高)
        """
        return self._status.level in (MarginLevel.WARNING, MarginLevel.DANGER, MarginLevel.CRITICAL)

    def is_critical(self) -> bool:
        """检查是否处于临界状态.

        返回:
            是否临界 (CRITICAL)
        """
        return self._status.level == MarginLevel.CRITICAL

    def get_history(self, limit: int | None = None) -> list[MarginSnapshot]:
        """获取历史记录.

        参数:
            limit: 返回记录数量限制

        返回:
            历史快照列表
        """
        if limit is None:
            return self._history.copy()
        return self._history[-limit:]

    def get_alerts(self, limit: int | None = None) -> list[MarginAlert]:
        """获取告警历史.

        参数:
            limit: 返回记录数量限制

        返回:
            告警列表
        """
        if limit is None:
            return self._alerts.copy()
        return self._alerts[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "update_count": self._update_count,
            "level_change_count": self._level_change_count,
            "current_level": self._status.level.value,
            "current_usage": self._status.usage_ratio,
            "alert_count": len(self._alerts),
            "history_size": len(self._history),
        }

    def reset(self) -> None:
        """重置监控器状态."""
        self._status = MarginStatus()
        self._history.clear()
        self._alerts.clear()
        self._update_count = 0
        self._level_change_count = 0

    def _calculate_level(self, usage_ratio: float) -> MarginLevel:
        """计算保证金等级.

        V4 Scenario: CHINA.MARGIN.WARNING_LEVEL

        参数:
            usage_ratio: 使用率

        返回:
            保证金等级
        """
        if usage_ratio >= self._config.danger_threshold:
            return MarginLevel.CRITICAL
        if usage_ratio >= self._config.warning_threshold:
            return MarginLevel.DANGER
        if usage_ratio >= self._config.normal_threshold:
            return MarginLevel.WARNING
        if usage_ratio >= self._config.safe_threshold:
            return MarginLevel.NORMAL
        return MarginLevel.SAFE

    def _add_to_history(
        self,
        timestamp: datetime,
        equity: float,
        margin_used: float,
        margin_available: float,
        usage_ratio: float,
        level: MarginLevel,
    ) -> None:
        """添加历史记录.

        参数:
            timestamp: 时间戳
            equity: 权益
            margin_used: 已用保证金
            margin_available: 可用保证金
            usage_ratio: 使用率
            level: 等级
        """
        snapshot = MarginSnapshot(
            timestamp=timestamp,
            equity=equity,
            margin_used=margin_used,
            margin_available=margin_available,
            usage_ratio=usage_ratio,
            level=level,
        )
        self._history.append(snapshot)

        # 限制历史记录大小
        if len(self._history) > self._config.history_size:
            self._history = self._history[-self._config.history_size :]

    def _generate_alert(
        self,
        new_level: MarginLevel,
        previous_level: MarginLevel,
        usage_ratio: float,
        timestamp: datetime,
    ) -> None:
        """生成告警事件.

        参数:
            new_level: 新等级
            previous_level: 旧等级
            usage_ratio: 使用率
            timestamp: 时间戳
        """
        # 确定告警类型
        level_order = [
            MarginLevel.SAFE,
            MarginLevel.NORMAL,
            MarginLevel.WARNING,
            MarginLevel.DANGER,
            MarginLevel.CRITICAL,
        ]
        old_idx = level_order.index(previous_level)
        new_idx = level_order.index(new_level)

        if new_idx > old_idx:
            alert_type = "LEVEL_UP"  # 风险上升
            message = f"保证金风险上升: {previous_level.value} -> {new_level.value}, 使用率 {usage_ratio:.2%}"
        else:
            alert_type = "LEVEL_DOWN"  # 风险下降
            message = f"保证金风险下降: {previous_level.value} -> {new_level.value}, 使用率 {usage_ratio:.2%}"

        alert = MarginAlert(
            timestamp=timestamp,
            alert_type=alert_type,
            level=new_level,
            previous_level=previous_level,
            usage_ratio=usage_ratio,
            message=message,
        )
        self._alerts.append(alert)


# 便捷函数

_default_monitor: MarginMonitor | None = None


def get_default_monitor() -> MarginMonitor:
    """获取默认保证金监控器 (单例).

    返回:
        默认的MarginMonitor实例
    """
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = MarginMonitor()
    return _default_monitor


def check_margin(equity: float, margin_used: float) -> MarginLevel:
    """检查保证金等级 (便捷函数).

    军规 M16: 保证金实时监控

    参数:
        equity: 权益
        margin_used: 已用保证金

    返回:
        保证金等级
    """
    monitor = get_default_monitor()
    return monitor.update(equity, margin_used)


def can_open(required_margin: float) -> tuple[bool, str]:
    """检查是否可以开仓 (便捷函数).

    参数:
        required_margin: 开仓所需保证金

    返回:
        (是否允许, 原因说明)
    """
    monitor = get_default_monitor()
    return monitor.can_open_position(required_margin)
