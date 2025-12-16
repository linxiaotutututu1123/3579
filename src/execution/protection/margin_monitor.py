"""
保证金监控模块 - MarginMonitor (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §19 保证金制度, §12.1 Phase 7文件清单

军规覆盖:
- M6: 熔断保护 - 保证金不足触发强平风险熔断
- M16: 保证金实时监控 - 保证金使用率必须实时计算

功能特性:
- 保证金使用率实时计算
- 五级预警等级 (安全/正常/预警/危险/临界)
- 开仓可用保证金检查
- 保证金快照历史记录
- 告警事件生成

中国期货市场保证金规则:
- 交易保证金: 开仓时缴纳，维持持仓
- 结算保证金: 每日结算时调整
- 追加保证金: 权益不足时追缴
- 强制平仓: 保证金使用率≥100%时触发

使用示例:
    from src.execution.protection.margin_monitor import (
        MarginMonitor,
        MarginConfig,
        MarginLevel,
    )

    # 创建监控器
    config = MarginConfig(
        warning_threshold=0.70,
        danger_threshold=0.85,
        critical_threshold=1.00,
    )
    monitor = MarginMonitor(config)

    # 更新保证金状态
    level = monitor.update(equity=1_000_000, margin_used=600_000)
    print(f"当前等级: {level.value}")  # 正常

    # 检查是否可开仓
    can, reason = monitor.can_open_position(required_margin=100_000)
    if not can:
        print(f"无法开仓: {reason}")
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar


class MarginLevel(Enum):
    """保证金使用率等级.

    军规M16: 保证金实时监控

    等级定义:
    - SAFE (安全): 使用率 < 50%，资金充裕
    - NORMAL (正常): 50% ≤ 使用率 < 70%，正常交易
    - WARNING (预警): 70% ≤ 使用率 < 85%，需要关注
    - DANGER (危险): 85% ≤ 使用率 < 100%，准备减仓
    - CRITICAL (临界): 使用率 ≥ 100%，触发强平风险
    """

    SAFE = "安全"
    NORMAL = "正常"
    WARNING = "预警"
    DANGER = "危险"
    CRITICAL = "临界"

    def is_safe(self) -> bool:
        """是否安全等级."""
        return self == MarginLevel.SAFE

    def is_tradeable(self) -> bool:
        """是否可交易等级 (安全/正常/预警)."""
        return self in (MarginLevel.SAFE, MarginLevel.NORMAL, MarginLevel.WARNING)

    def requires_action(self) -> bool:
        """是否需要采取行动 (危险/临界)."""
        return self in (MarginLevel.DANGER, MarginLevel.CRITICAL)

    def to_emoji(self) -> str:
        """转换为表情符号表示."""
        emoji_map = {
            MarginLevel.SAFE: "🟢",
            MarginLevel.NORMAL: "🔵",
            MarginLevel.WARNING: "🟡",
            MarginLevel.DANGER: "🟠",
            MarginLevel.CRITICAL: "🔴",
        }
        return emoji_map.get(self, "⚪")


class MarginStatus(Enum):
    """保证金监控状态."""

    ACTIVE = "监控中"
    PAUSED = "暂停"
    ERROR = "异常"


@dataclass(frozen=True)
class MarginConfig:
    """保证金监控配置.

    Attributes:
        safe_threshold: 安全阈值 (默认50%)
        warning_threshold: 预警阈值 (默认70%)
        danger_threshold: 危险阈值 (默认85%)
        critical_threshold: 临界阈值 (默认100%)
        min_available_margin: 最低可用保证金 (默认0)
        alert_cooldown_seconds: 告警冷却时间 (秒，默认300)
        history_max_size: 历史记录最大数量 (默认1000)
    """

    safe_threshold: float = 0.50
    warning_threshold: float = 0.70
    danger_threshold: float = 0.85
    critical_threshold: float = 1.00
    min_available_margin: float = 0.0
    alert_cooldown_seconds: int = 300
    history_max_size: int = 1000

    def __post_init__(self) -> None:
        """验证配置有效性."""
        if not (0 < self.safe_threshold < self.warning_threshold):
            msg = f"安全阈值 {self.safe_threshold} 必须小于预警阈值 {self.warning_threshold}"
            raise ValueError(msg)
        if not (self.warning_threshold < self.danger_threshold):
            msg = f"预警阈值 {self.warning_threshold} 必须小于危险阈值 {self.danger_threshold}"
            raise ValueError(msg)
        if not (self.danger_threshold < self.critical_threshold):
            msg = f"危险阈值 {self.danger_threshold} 必须小于临界阈值 {self.critical_threshold}"
            raise ValueError(msg)
        if self.min_available_margin < 0:
            msg = f"最低可用保证金不能为负数: {self.min_available_margin}"
            raise ValueError(msg)


@dataclass
class MarginSnapshot:
    """保证金快照.

    Attributes:
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

    def to_dict(self) -> dict[str, object]:
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

    Attributes:
        timestamp: 时间戳
        level: 当前等级
        previous_level: 之前等级
        usage_ratio: 使用率
        equity: 权益
        margin_used: 已用保证金
        message: 告警消息
        requires_action: 是否需要行动
    """

    timestamp: datetime
    level: MarginLevel
    previous_level: MarginLevel
    usage_ratio: float
    equity: float
    margin_used: float
    message: str
    requires_action: bool = False

    def to_dict(self) -> dict[str, object]:
        """转换为字典."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "previous_level": self.previous_level.value,
            "usage_ratio": self.usage_ratio,
            "equity": self.equity,
            "margin_used": self.margin_used,
            "message": self.message,
            "requires_action": self.requires_action,
        }


@dataclass
class OpenPositionCheckResult:
    """开仓检查结果.

    Attributes:
        can_open: 是否可以开仓
        reason: 原因说明
        current_level: 当前保证金等级
        usage_ratio: 当前使用率
        available_margin: 可用保证金
        required_margin: 需要保证金
        margin_after: 开仓后预计使用率
    """

    can_open: bool
    reason: str
    current_level: MarginLevel
    usage_ratio: float
    available_margin: float
    required_margin: float
    margin_after: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """转换为字典."""
        return {
            "can_open": self.can_open,
            "reason": self.reason,
            "current_level": self.current_level.value,
            "usage_ratio": self.usage_ratio,
            "available_margin": self.available_margin,
            "required_margin": self.required_margin,
            "margin_after": self.margin_after,
        }


@dataclass
class MarginMonitor:
    """保证金监控器.

    军规M16: 保证金实时监控
    V4 Scenario: CHINA.MARGIN.RATIO_CHECK, CHINA.MARGIN.USAGE_MONITOR, CHINA.MARGIN.WARNING_LEVEL

    核心功能:
    - update(): 更新保证金状态并返回等级
    - can_open_position(): 检查是否可以开仓
    - get_available_margin(): 获取可用保证金
    - get_snapshot(): 获取当前快照
    - get_alerts(): 获取告警历史

    使用示例:
        monitor = MarginMonitor()
        level = monitor.update(equity=1_000_000, margin_used=600_000)
        can, reason = monitor.can_open_position(50_000)
    """

    config: MarginConfig = field(default_factory=MarginConfig)

    # 内部状态
    _equity: float = field(default=0.0, init=False)
    _margin_used: float = field(default=0.0, init=False)
    _usage_ratio: float = field(default=0.0, init=False)
    _level: MarginLevel = field(default=MarginLevel.SAFE, init=False)
    _status: MarginStatus = field(default=MarginStatus.ACTIVE, init=False)
    _update_count: int = field(default=0, init=False)
    _last_update: datetime | None = field(default=None, init=False)
    _last_alert_time: datetime | None = field(default=None, init=False)

    # 历史记录
    _history: deque[MarginSnapshot] = field(init=False)
    _alerts: deque[MarginAlert] = field(init=False)

    # 类常量
    RULE_ID: ClassVar[str] = "CHINA.MARGIN"

    def __post_init__(self) -> None:
        """初始化历史记录."""
        # 使用object.__setattr__绕过frozen检查
        object.__setattr__(self, "_history", deque(maxlen=self.config.history_max_size))
        object.__setattr__(self, "_alerts", deque(maxlen=100))

    # ========== 属性 ==========

    @property
    def equity(self) -> float:
        """当前权益."""
        return self._equity

    @property
    def margin_used(self) -> float:
        """已用保证金."""
        return self._margin_used

    @property
    def margin_available(self) -> float:
        """可用保证金."""
        return max(0.0, self._equity - self._margin_used)

    @property
    def usage_ratio(self) -> float:
        """保证金使用率 (0.0 - 1.0+)."""
        return self._usage_ratio

    @property
    def level(self) -> MarginLevel:
        """当前保证金等级."""
        return self._level

    @property
    def status(self) -> MarginStatus:
        """监控状态."""
        return self._status

    @property
    def update_count(self) -> int:
        """更新次数."""
        return self._update_count

    @property
    def last_update(self) -> datetime | None:
        """最后更新时间."""
        return self._last_update

    # ========== 核心方法 ==========

    def update(
        self,
        equity: float,
        margin_used: float,
        *,
        timestamp: datetime | None = None,
    ) -> MarginLevel:
        """更新保证金状态.

        V4 Scenario: CHINA.MARGIN.USAGE_MONITOR
        军规M16: 保证金实时监控

        Args:
            equity: 当前权益
            margin_used: 已用保证金
            timestamp: 时间戳 (可选，默认当前时间)

        Returns:
            当前保证金等级

        Raises:
            ValueError: 参数无效
        """
        # 参数验证
        if equity < 0:
            msg = f"权益不能为负数: {equity}"
            raise ValueError(msg)
        if margin_used < 0:
            msg = f"已用保证金不能为负数: {margin_used}"
            raise ValueError(msg)

        ts = timestamp or datetime.now()  # noqa: DTZ005
        previous_level = self._level

        # 更新状态
        self._equity = equity
        self._margin_used = margin_used
        self._usage_ratio = self._calculate_usage_ratio(equity, margin_used)
        self._level = self._calculate_level(self._usage_ratio)
        self._update_count += 1
        self._last_update = ts

        # 创建快照
        snapshot = MarginSnapshot(
            timestamp=ts,
            equity=equity,
            margin_used=margin_used,
            margin_available=self.margin_available,
            usage_ratio=self._usage_ratio,
            level=self._level,
        )
        self._history.append(snapshot)

        # 检查是否需要告警
        if self._should_alert(previous_level, self._level):
            self._generate_alert(ts, previous_level)

        return self._level

    def can_open_position(
        self,
        required_margin: float,
        *,
        allow_warning: bool = True,
    ) -> OpenPositionCheckResult:
        """检查是否可以开仓.

        V4 Scenario: CHINA.MARGIN.RATIO_CHECK
        军规M16: 保证金实时监控

        Args:
            required_margin: 开仓所需保证金
            allow_warning: 是否允许在预警等级时开仓 (默认True)

        Returns:
            开仓检查结果
        """
        # 参数验证
        if required_margin < 0:
            return OpenPositionCheckResult(
                can_open=False,
                reason=f"所需保证金不能为负数: {required_margin}",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=self.margin_available,
                required_margin=required_margin,
            )

        # 检查当前等级
        if self._level == MarginLevel.CRITICAL:
            return OpenPositionCheckResult(
                can_open=False,
                reason="保证金已达临界等级，禁止开仓",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=self.margin_available,
                required_margin=required_margin,
            )

        if self._level == MarginLevel.DANGER:
            return OpenPositionCheckResult(
                can_open=False,
                reason="保证金处于危险等级，禁止开仓",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=self.margin_available,
                required_margin=required_margin,
            )

        if self._level == MarginLevel.WARNING and not allow_warning:
            return OpenPositionCheckResult(
                can_open=False,
                reason="保证金处于预警等级，不允许开仓",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=self.margin_available,
                required_margin=required_margin,
            )

        # 检查可用保证金
        available = self.margin_available
        if required_margin > available:
            return OpenPositionCheckResult(
                can_open=False,
                reason=f"可用保证金不足: 需要 {required_margin:.2f}, 可用 {available:.2f}",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=available,
                required_margin=required_margin,
            )

        # 检查最低可用保证金限制
        remaining = available - required_margin
        if remaining < self.config.min_available_margin:
            return OpenPositionCheckResult(
                can_open=False,
                reason=(
                    f"开仓后可用保证金 {remaining:.2f} 低于最低要求 "
                    f"{self.config.min_available_margin:.2f}"
                ),
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=available,
                required_margin=required_margin,
            )

        # 计算开仓后预计使用率
        new_margin_used = self._margin_used + required_margin
        new_usage_ratio = self._calculate_usage_ratio(self._equity, new_margin_used)
        new_level = self._calculate_level(new_usage_ratio)

        # 检查开仓后是否会超过危险等级
        if new_level in (MarginLevel.DANGER, MarginLevel.CRITICAL):
            return OpenPositionCheckResult(
                can_open=False,
                reason=f"开仓后保证金将达到{new_level.value}等级，禁止开仓",
                current_level=self._level,
                usage_ratio=self._usage_ratio,
                available_margin=available,
                required_margin=required_margin,
                margin_after=new_usage_ratio,
            )

        return OpenPositionCheckResult(
            can_open=True,
            reason="保证金充足，可以开仓",
            current_level=self._level,
            usage_ratio=self._usage_ratio,
            available_margin=available,
            required_margin=required_margin,
            margin_after=new_usage_ratio,
        )

    def get_available_margin(self) -> float:
        """获取可用保证金.

        Returns:
            可用保证金金额
        """
        return self.margin_available

    def get_snapshot(self) -> MarginSnapshot:
        """获取当前快照.

        Returns:
            当前保证金快照
        """
        return MarginSnapshot(
            timestamp=self._last_update or datetime.now(),  # noqa: DTZ005
            equity=self._equity,
            margin_used=self._margin_used,
            margin_available=self.margin_available,
            usage_ratio=self._usage_ratio,
            level=self._level,
        )

    def get_history(self, limit: int | None = None) -> list[MarginSnapshot]:
        """获取历史快照.

        Args:
            limit: 返回数量限制 (None表示全部)

        Returns:
            快照列表 (从新到旧)
        """
        history = list(self._history)
        history.reverse()
        if limit is not None:
            return history[:limit]
        return history

    def get_alerts(self, limit: int | None = None) -> list[MarginAlert]:
        """获取告警历史.

        Args:
            limit: 返回数量限制 (None表示全部)

        Returns:
            告警列表 (从新到旧)
        """
        alerts = list(self._alerts)
        alerts.reverse()
        if limit is not None:
            return alerts[:limit]
        return alerts

    def reset(self) -> None:
        """重置监控状态."""
        self._equity = 0.0
        self._margin_used = 0.0
        self._usage_ratio = 0.0
        self._level = MarginLevel.SAFE
        self._update_count = 0
        self._last_update = None
        self._last_alert_time = None
        self._history.clear()
        self._alerts.clear()

    def pause(self) -> None:
        """暂停监控."""
        self._status = MarginStatus.PAUSED

    def resume(self) -> None:
        """恢复监控."""
        self._status = MarginStatus.ACTIVE

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计字典
        """
        return {
            "status": self._status.value,
            "level": self._level.value,
            "equity": self._equity,
            "margin_used": self._margin_used,
            "margin_available": self.margin_available,
            "usage_ratio": self._usage_ratio,
            "update_count": self._update_count,
            "history_size": len(self._history),
            "alert_count": len(self._alerts),
            "last_update": (self._last_update.isoformat() if self._last_update else None),
        }

    # ========== 私有方法 ==========

    def _calculate_usage_ratio(self, equity: float, margin_used: float) -> float:
        """计算保证金使用率.

        Args:
            equity: 权益
            margin_used: 已用保证金

        Returns:
            使用率 (0.0 - 无穷大)
        """
        if equity <= 0:
            # 权益为0或负数，返回无穷大使用率
            return float("inf") if margin_used > 0 else 0.0
        return margin_used / equity

    def _calculate_level(self, usage_ratio: float) -> MarginLevel:
        """根据使用率计算等级.

        V4 Scenario: CHINA.MARGIN.WARNING_LEVEL

        Args:
            usage_ratio: 使用率

        Returns:
            保证金等级
        """
        if usage_ratio >= self.config.critical_threshold:
            return MarginLevel.CRITICAL
        if usage_ratio >= self.config.danger_threshold:
            return MarginLevel.DANGER
        if usage_ratio >= self.config.warning_threshold:
            return MarginLevel.WARNING
        if usage_ratio >= self.config.safe_threshold:
            return MarginLevel.NORMAL
        return MarginLevel.SAFE

    def _should_alert(
        self,
        previous_level: MarginLevel,
        current_level: MarginLevel,
    ) -> bool:
        """判断是否应该发送告警.

        Args:
            previous_level: 之前等级
            current_level: 当前等级

        Returns:
            是否应该告警
        """
        # 等级没变化不告警
        if previous_level == current_level:
            return False

        # 检查告警冷却
        if self._last_alert_time is not None:
            elapsed = (datetime.now() - self._last_alert_time).total_seconds()  # noqa: DTZ005
            if elapsed < self.config.alert_cooldown_seconds:
                return False

        # 等级变化需要告警
        return True

    def _generate_alert(
        self,
        timestamp: datetime,
        previous_level: MarginLevel,
    ) -> None:
        """生成告警事件.

        Args:
            timestamp: 时间戳
            previous_level: 之前等级
        """
        level_order = {
            MarginLevel.SAFE: 0,
            MarginLevel.NORMAL: 1,
            MarginLevel.WARNING: 2,
            MarginLevel.DANGER: 3,
            MarginLevel.CRITICAL: 4,
        }

        # 判断是升级还是降级
        prev_order = level_order[previous_level]
        curr_order = level_order[self._level]

        if curr_order > prev_order:
            direction = "升级"
        else:
            direction = "降级"

        message = (
            f"保证金等级{direction}: {previous_level.value} → {self._level.value}, "
            f"使用率 {self._usage_ratio:.2%}"
        )

        alert = MarginAlert(
            timestamp=timestamp,
            level=self._level,
            previous_level=previous_level,
            usage_ratio=self._usage_ratio,
            equity=self._equity,
            margin_used=self._margin_used,
            message=message,
            requires_action=self._level.requires_action(),
        )

        self._alerts.append(alert)
        self._last_alert_time = timestamp


# ========== 便捷函数 ==========

# 默认监控器实例 (单例模式)
_default_monitor: MarginMonitor | None = None


def get_default_monitor() -> MarginMonitor:
    """获取默认监控器实例.

    Returns:
        默认监控器
    """
    global _default_monitor  # noqa: PLW0603
    if _default_monitor is None:
        _default_monitor = MarginMonitor()
    return _default_monitor


def check_margin(
    equity: float,
    margin_used: float,
) -> MarginLevel:
    """快捷检查保证金等级.

    Args:
        equity: 权益
        margin_used: 已用保证金

    Returns:
        保证金等级
    """
    monitor = get_default_monitor()
    return monitor.update(equity=equity, margin_used=margin_used)


def can_open(
    required_margin: float,
    *,
    allow_warning: bool = True,
) -> tuple[bool, str]:
    """快捷检查是否可以开仓.

    Args:
        required_margin: 所需保证金
        allow_warning: 是否允许在预警等级时开仓

    Returns:
        (是否可开仓, 原因)
    """
    monitor = get_default_monitor()
    result = monitor.can_open_position(
        required_margin=required_margin,
        allow_warning=allow_warning,
    )
    return result.can_open, result.reason
