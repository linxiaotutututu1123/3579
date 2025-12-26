"""
限速控制器模块 - Throttle Controller.

V4PRO Platform Component - Phase 7/9 中国期货市场特化
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.THROTTLE: 限速控制
- CHINA.COMPLIANCE.HFT_DETECTION: 高频交易检测

军规覆盖:
- M3: 审计日志完整 - 必记字段/保留期限/存储要求
- M6: 熔断保护机制完整 - 与熔断系统联动
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 多级限速控制 (NONE/WARNING/SLOW/CRITICAL/BLOCK)
- 账户级别限速
- 自动恢复机制
- 与熔断系统联动 (M6)
- 审计日志记录 (M3)

限速级别:
- NONE: 无限速，正常交易
- WARNING: 预警，记录日志但允许交易
- SLOW: 减速，间隔100ms
- CRITICAL: 严重，间隔500ms
- BLOCK: 阻断，禁止下单

示例:
    >>> from src.compliance.hft_detector.throttle import (
    ...     ThrottleController,
    ...     ThrottleLevel,
    ... )
    >>> controller = ThrottleController()
    >>> controller.apply_throttle("acc_001", ThrottleLevel.SLOW)
    >>> if controller.can_submit_order("acc_001"):
    ...     # 提交订单
    ...     pass
    >>> wait_time = controller.get_wait_time_ms("acc_001")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


# ============================================================
# 常量定义
# ============================================================

# 限速延迟配置 (毫秒)
THROTTLE_DELAY_MS_NONE = 0  # 无延迟
THROTTLE_DELAY_MS_WARNING = 0  # 警告无延迟
THROTTLE_DELAY_MS_SLOW = 100  # 减速 100ms
THROTTLE_DELAY_MS_CRITICAL = 500  # 严重 500ms
THROTTLE_DELAY_MS_BLOCK = -1  # 阻断 (特殊值，表示禁止)

# 自动恢复配置
DEFAULT_AUTO_RECOVERY_SECONDS = 60  # 默认60秒后自动恢复
DEFAULT_RECOVERY_STEP_SECONDS = 10  # 每10秒降一级

# 熔断联动配置
CIRCUIT_BREAKER_THROTTLE_LEVEL = "CRITICAL"  # 熔断触发时的限速级别


class ThrottleLevel(Enum):
    """限速级别枚举.

    V4 SPEC: 多级限速控制
    """

    NONE = "NONE"  # 无限速，正常交易
    WARNING = "WARNING"  # 预警，记录日志但允许交易
    SLOW = "SLOW"  # 减速，间隔100ms
    CRITICAL = "CRITICAL"  # 严重，间隔500ms
    BLOCK = "BLOCK"  # 阻断，禁止下单

    @property
    def delay_ms(self) -> int:
        """获取该级别对应的延迟毫秒数.

        返回:
            延迟毫秒数，-1表示阻断
        """
        delays = {
            ThrottleLevel.NONE: THROTTLE_DELAY_MS_NONE,
            ThrottleLevel.WARNING: THROTTLE_DELAY_MS_WARNING,
            ThrottleLevel.SLOW: THROTTLE_DELAY_MS_SLOW,
            ThrottleLevel.CRITICAL: THROTTLE_DELAY_MS_CRITICAL,
            ThrottleLevel.BLOCK: THROTTLE_DELAY_MS_BLOCK,
        }
        return delays.get(self, 0)

    @property
    def severity(self) -> int:
        """获取该级别的严重程度 (0-4).

        返回:
            严重程度数值
        """
        severity_map = {
            ThrottleLevel.NONE: 0,
            ThrottleLevel.WARNING: 1,
            ThrottleLevel.SLOW: 2,
            ThrottleLevel.CRITICAL: 3,
            ThrottleLevel.BLOCK: 4,
        }
        return severity_map.get(self, 0)

    def is_blocking(self) -> bool:
        """是否阻断订单.

        返回:
            是否阻断
        """
        return self == ThrottleLevel.BLOCK

    def allows_trading(self) -> bool:
        """是否允许交易.

        返回:
            是否允许交易
        """
        return self != ThrottleLevel.BLOCK


class AuditCallback(Protocol):
    """审计日志回调协议.

    M3军规: 审计日志完整.
    """

    def __call__(
        self,
        event_type: str,
        account_id: str,
        details: dict[str, Any],
    ) -> None:
        """记录审计日志.

        参数:
            event_type: 事件类型
            account_id: 账户ID
            details: 详细信息
        """
        ...


class CircuitBreakerCallback(Protocol):
    """熔断器回调协议.

    M6军规: 熔断保护机制完整.
    """

    def __call__(self, account_id: str) -> bool:
        """检查熔断器状态.

        参数:
            account_id: 账户ID

        返回:
            是否处于熔断状态
        """
        ...


@dataclass(frozen=True)
class ThrottleConfig:
    """限速配置 (不可变).

    属性:
        slow_delay_ms: SLOW级别延迟 (默认100ms)
        critical_delay_ms: CRITICAL级别延迟 (默认500ms)
        auto_recovery_enabled: 是否启用自动恢复 (默认True)
        auto_recovery_seconds: 自动恢复时间 (默认60秒)
        recovery_step_seconds: 恢复步进时间 (默认10秒)
        circuit_breaker_integration: 是否与熔断系统联动 (默认True)
        audit_enabled: 是否启用审计日志 (默认True)
        max_throttled_accounts: 最大限速账户数 (默认1000)
    """

    slow_delay_ms: int = THROTTLE_DELAY_MS_SLOW
    critical_delay_ms: int = THROTTLE_DELAY_MS_CRITICAL
    auto_recovery_enabled: bool = True
    auto_recovery_seconds: float = DEFAULT_AUTO_RECOVERY_SECONDS
    recovery_step_seconds: float = DEFAULT_RECOVERY_STEP_SECONDS
    circuit_breaker_integration: bool = True
    audit_enabled: bool = True
    max_throttled_accounts: int = 1000


@dataclass
class ThrottleStatus:
    """限速状态.

    属性:
        account_id: 账户ID
        level: 当前限速级别
        start_time: 限速开始时间
        last_update_time: 最后更新时间
        reason: 限速原因
        can_submit: 是否可以提交订单
        wait_time_ms: 需要等待的毫秒数
        auto_recovery_time: 自动恢复时间 (None表示不自动恢复)
        is_circuit_breaker_triggered: 是否由熔断触发
        order_count_since_throttle: 限速后的订单计数
    """

    account_id: str
    level: ThrottleLevel
    start_time: float
    last_update_time: float
    reason: str = ""
    can_submit: bool = True
    wait_time_ms: int = 0
    auto_recovery_time: float | None = None
    is_circuit_breaker_triggered: bool = False
    order_count_since_throttle: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        返回:
            状态字典
        """
        return {
            "account_id": self.account_id,
            "level": self.level.value,
            "start_time": self.start_time,
            "last_update_time": self.last_update_time,
            "reason": self.reason,
            "can_submit": self.can_submit,
            "wait_time_ms": self.wait_time_ms,
            "auto_recovery_time": self.auto_recovery_time,
            "is_circuit_breaker_triggered": self.is_circuit_breaker_triggered,
            "order_count_since_throttle": self.order_count_since_throttle,
            "duration_seconds": time.time() - self.start_time,
        }


@dataclass
class _AccountThrottleState:
    """账户限速内部状态.

    内部类，用于跟踪单个账户的限速状态.
    """

    level: ThrottleLevel = field(default=ThrottleLevel.NONE)
    start_time: float = 0.0
    last_update_time: float = 0.0
    last_order_time: float = 0.0
    reason: str = ""
    auto_recovery_time: float | None = None
    is_circuit_breaker_triggered: bool = False
    order_count: int = 0

    def update_level(
        self,
        level: ThrottleLevel,
        reason: str,
        now: float,
        auto_recovery_time: float | None = None,
        is_circuit_breaker: bool = False,
    ) -> None:
        """更新限速级别.

        参数:
            level: 新级别
            reason: 原因
            now: 当前时间
            auto_recovery_time: 自动恢复时间
            is_circuit_breaker: 是否由熔断触发
        """
        if self.level == ThrottleLevel.NONE and level != ThrottleLevel.NONE:
            self.start_time = now
            self.order_count = 0
        self.level = level
        self.last_update_time = now
        self.reason = reason
        self.auto_recovery_time = auto_recovery_time
        self.is_circuit_breaker_triggered = is_circuit_breaker

    def record_order(self, now: float) -> None:
        """记录订单.

        参数:
            now: 当前时间
        """
        self.last_order_time = now
        if self.level != ThrottleLevel.NONE:
            self.order_count += 1


class ThrottleController:
    """限速控制器.

    V4 SPEC: 限速控制器 - 控制订单提交频率

    功能:
    - 多级限速控制 (NONE/WARNING/SLOW/CRITICAL/BLOCK)
    - 账户级别限速
    - 自动恢复机制
    - 与熔断系统联动 (M6)
    - 审计日志记录 (M3)

    示例:
        >>> controller = ThrottleController()
        >>> controller.apply_throttle("acc_001", ThrottleLevel.SLOW, reason="高频检测")
        >>> status = controller.check_throttle("acc_001")
        >>> if controller.can_submit_order("acc_001"):
        ...     # 等待必要时间后提交订单
        ...     wait_ms = controller.get_wait_time_ms("acc_001")
        ...     if wait_ms > 0:
        ...         time.sleep(wait_ms / 1000)
        ...     # 提交订单...
        >>> controller.release_throttle("acc_001")
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: ThrottleConfig | None = None,
        audit_callback: AuditCallback | None = None,
        circuit_breaker_callback: CircuitBreakerCallback | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        """初始化限速控制器.

        参数:
            config: 限速配置 (None使用默认配置)
            audit_callback: 审计日志回调函数 (M3军规)
            circuit_breaker_callback: 熔断器状态回调函数 (M6军规)
            time_func: 时间函数 (用于测试注入)
        """
        self._config = config or ThrottleConfig()
        self._audit_callback = audit_callback
        self._circuit_breaker_callback = circuit_breaker_callback
        self._time_func = time_func or time.time

        # 账户状态存储
        self._account_states: dict[str, _AccountThrottleState] = {}
        self._lock = threading.RLock()

        # 统计
        self._apply_count: int = 0
        self._release_count: int = 0
        self._block_count: int = 0
        self._auto_recovery_count: int = 0

    @property
    def config(self) -> ThrottleConfig:
        """获取配置.

        返回:
            限速配置
        """
        return self._config

    def apply_throttle(
        self,
        account_id: str,
        level: ThrottleLevel,
        reason: str = "",
        is_circuit_breaker: bool = False,
    ) -> None:
        """应用限速.

        将指定账户设置为指定的限速级别.

        参数:
            account_id: 账户ID
            level: 限速级别
            reason: 限速原因
            is_circuit_breaker: 是否由熔断触发

        示例:
            >>> controller.apply_throttle("acc_001", ThrottleLevel.SLOW, "订单频率过高")
        """
        now = self._time_func()

        # 计算自动恢复时间
        auto_recovery_time = None
        if self._config.auto_recovery_enabled and level != ThrottleLevel.BLOCK:
            auto_recovery_time = now + self._config.auto_recovery_seconds

        with self._lock:
            # 检查账户数量限制
            if (
                account_id not in self._account_states
                and len(self._account_states) >= self._config.max_throttled_accounts
            ):
                logger.warning(
                    f"限速账户数量已达上限 ({self._config.max_throttled_accounts}), "
                    f"无法添加账户 {account_id}"
                )
                return

            # 获取或创建账户状态
            if account_id not in self._account_states:
                self._account_states[account_id] = _AccountThrottleState()

            state = self._account_states[account_id]
            old_level = state.level

            # 更新状态
            state.update_level(
                level=level,
                reason=reason,
                now=now,
                auto_recovery_time=auto_recovery_time,
                is_circuit_breaker=is_circuit_breaker,
            )

            self._apply_count += 1
            if level == ThrottleLevel.BLOCK:
                self._block_count += 1

        # M3军规: 记录审计日志
        if self._config.audit_enabled:
            self._emit_audit(
                event_type="THROTTLE_APPLY",
                account_id=account_id,
                details={
                    "old_level": old_level.value,
                    "new_level": level.value,
                    "reason": reason,
                    "is_circuit_breaker": is_circuit_breaker,
                    "auto_recovery_time": auto_recovery_time,
                },
            )

        logger.info(
            f"账户 {account_id} 限速已应用: {old_level.value} -> {level.value}, "
            f"原因: {reason}"
        )

    def release_throttle(self, account_id: str, reason: str = "手动解除") -> None:
        """释放限速.

        将指定账户的限速级别恢复为 NONE.

        参数:
            account_id: 账户ID
            reason: 释放原因

        示例:
            >>> controller.release_throttle("acc_001", "频率恢复正常")
        """
        now = self._time_func()

        with self._lock:
            if account_id not in self._account_states:
                return

            state = self._account_states[account_id]
            old_level = state.level

            if old_level == ThrottleLevel.NONE:
                return

            # 更新状态为无限速
            state.update_level(
                level=ThrottleLevel.NONE,
                reason=reason,
                now=now,
                auto_recovery_time=None,
                is_circuit_breaker=False,
            )

            self._release_count += 1

        # M3军规: 记录审计日志
        if self._config.audit_enabled:
            self._emit_audit(
                event_type="THROTTLE_RELEASE",
                account_id=account_id,
                details={
                    "old_level": old_level.value,
                    "new_level": ThrottleLevel.NONE.value,
                    "reason": reason,
                    "duration_seconds": now - state.start_time,
                    "orders_during_throttle": state.order_count,
                },
            )

        logger.info(
            f"账户 {account_id} 限速已释放: {old_level.value} -> NONE, "
            f"原因: {reason}"
        )

    def check_throttle(self, account_id: str) -> ThrottleStatus:
        """检查限速状态.

        获取指定账户的当前限速状态.

        参数:
            account_id: 账户ID

        返回:
            限速状态

        示例:
            >>> status = controller.check_throttle("acc_001")
            >>> print(f"当前级别: {status.level.value}")
            >>> print(f"可以提交: {status.can_submit}")
        """
        now = self._time_func()

        # 先检查自动恢复
        self._check_auto_recovery(account_id, now)

        # M6军规: 检查熔断器状态
        if self._config.circuit_breaker_integration:
            self._check_circuit_breaker(account_id, now)

        with self._lock:
            if account_id not in self._account_states:
                # 无限速状态
                return ThrottleStatus(
                    account_id=account_id,
                    level=ThrottleLevel.NONE,
                    start_time=now,
                    last_update_time=now,
                    reason="",
                    can_submit=True,
                    wait_time_ms=0,
                    auto_recovery_time=None,
                    is_circuit_breaker_triggered=False,
                    order_count_since_throttle=0,
                )

            state = self._account_states[account_id]

            # 计算等待时间
            wait_time_ms = self._calculate_wait_time(state, now)

            return ThrottleStatus(
                account_id=account_id,
                level=state.level,
                start_time=state.start_time,
                last_update_time=state.last_update_time,
                reason=state.reason,
                can_submit=state.level.allows_trading(),
                wait_time_ms=wait_time_ms,
                auto_recovery_time=state.auto_recovery_time,
                is_circuit_breaker_triggered=state.is_circuit_breaker_triggered,
                order_count_since_throttle=state.order_count,
            )

    def can_submit_order(self, account_id: str) -> bool:
        """检查是否可以提交订单.

        参数:
            account_id: 账户ID

        返回:
            是否可以提交订单

        示例:
            >>> if controller.can_submit_order("acc_001"):
            ...     # 可以提交订单
            ...     pass
        """
        status = self.check_throttle(account_id)
        return status.can_submit

    def get_wait_time_ms(self, account_id: str) -> int:
        """获取需要等待的毫秒数.

        参数:
            account_id: 账户ID

        返回:
            需要等待的毫秒数，0表示无需等待，-1表示阻断

        示例:
            >>> wait_ms = controller.get_wait_time_ms("acc_001")
            >>> if wait_ms > 0:
            ...     time.sleep(wait_ms / 1000)
            >>> elif wait_ms < 0:
            ...     # 阻断，不能提交
            ...     pass
        """
        status = self.check_throttle(account_id)
        return status.wait_time_ms

    def record_order_submit(self, account_id: str) -> None:
        """记录订单提交.

        在订单实际提交后调用，用于计算下一次的等待时间.

        参数:
            account_id: 账户ID

        示例:
            >>> if controller.can_submit_order("acc_001"):
            ...     # 提交订单
            ...     submit_order(...)
            ...     controller.record_order_submit("acc_001")
        """
        now = self._time_func()

        with self._lock:
            if account_id in self._account_states:
                self._account_states[account_id].record_order(now)

    def get_throttled_accounts(self) -> list[str]:
        """获取所有被限速的账户列表.

        返回:
            被限速的账户ID列表
        """
        with self._lock:
            return [
                account_id
                for account_id, state in self._account_states.items()
                if state.level != ThrottleLevel.NONE
            ]

    def get_accounts_by_level(self, level: ThrottleLevel) -> list[str]:
        """获取指定限速级别的账户列表.

        参数:
            level: 限速级别

        返回:
            账户ID列表
        """
        with self._lock:
            return [
                account_id
                for account_id, state in self._account_states.items()
                if state.level == level
            ]

    def escalate_throttle(self, account_id: str, reason: str = "升级") -> ThrottleLevel:
        """升级限速级别.

        将账户的限速级别升一级 (如 NONE->WARNING, WARNING->SLOW 等).

        参数:
            account_id: 账户ID
            reason: 升级原因

        返回:
            新的限速级别

        示例:
            >>> new_level = controller.escalate_throttle("acc_001", "持续高频")
        """
        current_status = self.check_throttle(account_id)
        current_level = current_status.level

        # 升级映射
        escalation_map = {
            ThrottleLevel.NONE: ThrottleLevel.WARNING,
            ThrottleLevel.WARNING: ThrottleLevel.SLOW,
            ThrottleLevel.SLOW: ThrottleLevel.CRITICAL,
            ThrottleLevel.CRITICAL: ThrottleLevel.BLOCK,
            ThrottleLevel.BLOCK: ThrottleLevel.BLOCK,  # 已是最高级
        }

        new_level = escalation_map.get(current_level, ThrottleLevel.WARNING)

        if new_level != current_level:
            self.apply_throttle(
                account_id=account_id,
                level=new_level,
                reason=f"{reason} (升级: {current_level.value} -> {new_level.value})",
            )

        return new_level

    def deescalate_throttle(self, account_id: str, reason: str = "降级") -> ThrottleLevel:
        """降级限速级别.

        将账户的限速级别降一级 (如 BLOCK->CRITICAL, CRITICAL->SLOW 等).

        参数:
            account_id: 账户ID
            reason: 降级原因

        返回:
            新的限速级别

        示例:
            >>> new_level = controller.deescalate_throttle("acc_001", "频率降低")
        """
        current_status = self.check_throttle(account_id)
        current_level = current_status.level

        # 降级映射
        deescalation_map = {
            ThrottleLevel.NONE: ThrottleLevel.NONE,  # 已是最低级
            ThrottleLevel.WARNING: ThrottleLevel.NONE,
            ThrottleLevel.SLOW: ThrottleLevel.WARNING,
            ThrottleLevel.CRITICAL: ThrottleLevel.SLOW,
            ThrottleLevel.BLOCK: ThrottleLevel.CRITICAL,
        }

        new_level = deescalation_map.get(current_level, ThrottleLevel.NONE)

        if new_level == ThrottleLevel.NONE:
            self.release_throttle(account_id, reason)
        elif new_level != current_level:
            self.apply_throttle(
                account_id=account_id,
                level=new_level,
                reason=f"{reason} (降级: {current_level.value} -> {new_level.value})",
            )

        return new_level

    def tick(self) -> int:
        """时钟推进.

        检查所有账户的自动恢复状态，执行必要的恢复操作.
        建议定期调用此方法 (如每秒一次).

        返回:
            本次恢复的账户数量

        示例:
            >>> # 在定时任务中调用
            >>> recovered_count = controller.tick()
        """
        now = self._time_func()
        recovered_count = 0

        with self._lock:
            account_ids = list(self._account_states.keys())

        for account_id in account_ids:
            if self._check_auto_recovery(account_id, now):
                recovered_count += 1

        return recovered_count

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        with self._lock:
            level_counts = {}
            for level in ThrottleLevel:
                level_counts[level.value] = sum(
                    1 for s in self._account_states.values() if s.level == level
                )

            return {
                "apply_count": self._apply_count,
                "release_count": self._release_count,
                "block_count": self._block_count,
                "auto_recovery_count": self._auto_recovery_count,
                "current_throttled_count": sum(
                    1 for s in self._account_states.values()
                    if s.level != ThrottleLevel.NONE
                ),
                "level_distribution": level_counts,
                "config": {
                    "slow_delay_ms": self._config.slow_delay_ms,
                    "critical_delay_ms": self._config.critical_delay_ms,
                    "auto_recovery_enabled": self._config.auto_recovery_enabled,
                    "auto_recovery_seconds": self._config.auto_recovery_seconds,
                },
                "version": self.VERSION,
            }

    def reset(self) -> None:
        """重置控制器.

        清除所有账户的限速状态.
        """
        with self._lock:
            self._account_states.clear()
            self._apply_count = 0
            self._release_count = 0
            self._block_count = 0
            self._auto_recovery_count = 0

        logger.info("限速控制器已重置")

    def _calculate_wait_time(
        self,
        state: _AccountThrottleState,
        now: float,
    ) -> int:
        """计算等待时间.

        参数:
            state: 账户状态
            now: 当前时间

        返回:
            等待毫秒数
        """
        if state.level == ThrottleLevel.NONE:
            return 0

        if state.level == ThrottleLevel.BLOCK:
            return -1  # 阻断

        if state.level == ThrottleLevel.WARNING:
            return 0  # 警告无延迟

        # SLOW 或 CRITICAL
        delay_ms = (
            self._config.slow_delay_ms
            if state.level == ThrottleLevel.SLOW
            else self._config.critical_delay_ms
        )

        # 计算距上次订单的时间
        if state.last_order_time > 0:
            elapsed_ms = (now - state.last_order_time) * 1000
            remaining_ms = max(0, delay_ms - elapsed_ms)
            return int(remaining_ms)

        return 0

    def _check_auto_recovery(self, account_id: str, now: float) -> bool:
        """检查并执行自动恢复.

        参数:
            account_id: 账户ID
            now: 当前时间

        返回:
            是否执行了恢复
        """
        if not self._config.auto_recovery_enabled:
            return False

        with self._lock:
            if account_id not in self._account_states:
                return False

            state = self._account_states[account_id]

            # 熔断触发的限速不自动恢复
            if state.is_circuit_breaker_triggered:
                return False

            if state.level == ThrottleLevel.NONE:
                return False

            if state.auto_recovery_time is None:
                return False

            if now < state.auto_recovery_time:
                return False

        # 执行恢复 (渐进式降级)
        new_level = self.deescalate_throttle(
            account_id,
            reason="自动恢复"
        )

        if new_level == ThrottleLevel.NONE:
            self._auto_recovery_count += 1
            logger.info(f"账户 {account_id} 自动恢复完成")
            return True

        # 如果还未完全恢复，更新下次恢复时间
        with self._lock:
            if account_id in self._account_states:
                self._account_states[account_id].auto_recovery_time = (
                    now + self._config.recovery_step_seconds
                )

        return False

    def _check_circuit_breaker(self, account_id: str, now: float) -> None:
        """检查熔断器状态.

        M6军规: 与熔断系统联动.

        参数:
            account_id: 账户ID
            now: 当前时间
        """
        if not self._config.circuit_breaker_integration:
            return

        if self._circuit_breaker_callback is None:
            return

        try:
            is_triggered = self._circuit_breaker_callback(account_id)
        except Exception as e:
            logger.warning(f"熔断器回调失败: {e}")
            return

        with self._lock:
            if account_id in self._account_states:
                state = self._account_states[account_id]
                was_triggered = state.is_circuit_breaker_triggered
            else:
                was_triggered = False

        if is_triggered and not was_triggered:
            # 熔断触发，应用限速
            self.apply_throttle(
                account_id=account_id,
                level=ThrottleLevel.CRITICAL,
                reason="熔断器触发",
                is_circuit_breaker=True,
            )
            logger.warning(f"账户 {account_id} 因熔断器触发而限速")

        elif not is_triggered and was_triggered:
            # 熔断解除，释放限速
            self.release_throttle(
                account_id=account_id,
                reason="熔断器解除",
            )
            logger.info(f"账户 {account_id} 因熔断器解除而释放限速")

    def _emit_audit(
        self,
        event_type: str,
        account_id: str,
        details: dict[str, Any],
    ) -> None:
        """发送审计日志.

        M3军规: 审计日志完整.

        参数:
            event_type: 事件类型
            account_id: 账户ID
            details: 详细信息
        """
        if self._audit_callback:
            try:
                # 添加时间戳
                details["timestamp"] = datetime.now().isoformat()  # noqa: DTZ005
                details["military_rule"] = "M3"

                self._audit_callback(
                    event_type=event_type,
                    account_id=account_id,
                    details=details,
                )
            except Exception as e:
                logger.error(f"审计日志回调失败: {e}")


# ============================================================
# 便捷函数
# ============================================================


def create_throttle_controller(
    config: ThrottleConfig | None = None,
    audit_callback: AuditCallback | None = None,
    circuit_breaker_callback: CircuitBreakerCallback | None = None,
) -> ThrottleController:
    """创建限速控制器.

    参数:
        config: 限速配置
        audit_callback: 审计日志回调
        circuit_breaker_callback: 熔断器状态回调

    返回:
        限速控制器实例

    示例:
        >>> controller = create_throttle_controller()
    """
    return ThrottleController(
        config=config,
        audit_callback=audit_callback,
        circuit_breaker_callback=circuit_breaker_callback,
    )


def get_default_config() -> ThrottleConfig:
    """获取默认配置.

    返回:
        默认限速配置
    """
    return ThrottleConfig()
