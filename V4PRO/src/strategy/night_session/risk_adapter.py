"""
夜盘风控适配器 (军规级 v4.2).

V4PRO Platform Component - Phase 9 夜盘特化
V4 SPEC: M6 熔断保护, M15 夜盘跨日处理

军规覆盖:
- M6: 熔断保护机制 - 夜盘风控规则收紧
- M15: 夜盘跨日处理 - 仓位限制和止损调整

功能特性:
- 夜盘仓位限制检查 (50%仓位上限)
- 止损价格调整 (收紧1.5倍)
- 订单频率限制 (每分钟最大30单)
- 熔断事件响应
- Guardian系统集成

示例:
    >>> from src.strategy.night_session import NightSessionRiskAdapter
    >>> adapter = NightSessionRiskAdapter()
    >>> adjusted_signal = adapter.apply_night_risk_rules(signal)
    >>> if adapter.is_trading_allowed("account_001"):
    ...     # 执行交易逻辑
    ...     pass
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.guardian import CircuitBreaker, CircuitBreakerManager


# ============================================================
# 日志配置
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# 协议定义
# ============================================================


class GuardianProtocol(Protocol):
    """Guardian系统协议.

    定义与Guardian系统交互的接口.
    """

    def is_trading_allowed(self) -> bool:
        """检查是否允许交易."""
        ...

    @property
    def current_position_ratio(self) -> float:
        """获取当前仓位比例."""
        ...

    def get_breaker(self, name: str) -> CircuitBreaker | None:
        """获取熔断器."""
        ...


# ============================================================
# 数据结构
# ============================================================


class SignalDirection(Enum):
    """信号方向枚举."""

    LONG = "LONG"    # 多头
    SHORT = "SHORT"  # 空头
    FLAT = "FLAT"    # 平仓/观望


@dataclass(frozen=True, slots=True)
class NightRiskConfig:
    """夜盘风控配置 (不可变).

    属性:
        position_limit_ratio: 仓位限制比例 (默认0.5, 即50%)
        stop_loss_tighter_ratio: 止损收紧比例 (默认1.5倍)
        max_orders_per_minute: 每分钟最大订单数 (默认30)
        order_rate_window_seconds: 订单频率统计窗口 (默认60秒)
        circuit_breaker_cooldown_seconds: 熔断冷却时间 (默认300秒)
    """

    position_limit_ratio: float = 0.5
    stop_loss_tighter_ratio: float = 1.5
    max_orders_per_minute: int = 30
    order_rate_window_seconds: float = 60.0
    circuit_breaker_cooldown_seconds: float = 300.0

    def __post_init__(self) -> None:
        """验证配置参数."""
        if not 0 < self.position_limit_ratio <= 1.0:
            raise ValueError(
                f"position_limit_ratio必须在(0, 1]范围内: {self.position_limit_ratio}"
            )
        if self.stop_loss_tighter_ratio < 1.0:
            raise ValueError(
                f"stop_loss_tighter_ratio必须>=1.0: {self.stop_loss_tighter_ratio}"
            )
        if self.max_orders_per_minute <= 0:
            raise ValueError(
                f"max_orders_per_minute必须>0: {self.max_orders_per_minute}"
            )


@dataclass
class CircuitBreakerEventData:
    """熔断事件数据.

    属性:
        event_type: 事件类型
        timestamp: 事件时间戳
        account_id: 账户ID
        trigger_reason: 触发原因
        from_state: 原状态
        to_state: 目标状态
        details: 详细信息
    """

    event_type: str
    timestamp: float = field(default_factory=time.time)
    account_id: str = ""
    trigger_reason: str = ""
    from_state: str = ""
    to_state: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
            "account_id": self.account_id,
            "trigger_reason": self.trigger_reason,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "details": self.details,
        }


@dataclass
class StrategySignalAdapter:
    """策略信号适配器 (用于夜盘风控调整).

    封装原始信号并支持风控调整.

    属性:
        strategy_id: 策略ID
        symbol: 合约代码
        direction: 信号方向
        strength: 信号强度
        confidence: 置信度
        target_position: 目标仓位
        stop_loss_price: 止损价格
        original_stop_loss: 原始止损价格
        adjusted: 是否已调整
        adjustment_reason: 调整原因
        timestamp: 时间戳
        metadata: 元数据
    """

    strategy_id: str
    symbol: str
    direction: SignalDirection
    strength: float
    confidence: float
    target_position: float = 0.0
    stop_loss_price: float | None = None
    original_stop_loss: float | None = None
    adjusted: bool = False
    adjustment_reason: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "target_position": round(self.target_position, 4),
            "stop_loss_price": self.stop_loss_price,
            "original_stop_loss": self.original_stop_loss,
            "adjusted": self.adjusted,
            "adjustment_reason": self.adjustment_reason,
            "timestamp": self.timestamp,
        }


# ============================================================
# 辅助组件
# ============================================================


class OrderRateLimiter:
    """订单频率限制器 (线程安全).

    使用滑动窗口算法限制每分钟订单数量.

    属性:
        max_orders_per_minute: 每分钟最大订单数
        window_seconds: 统计窗口秒数
    """

    def __init__(
        self,
        max_orders_per_minute: int = 30,
        window_seconds: float = 60.0,
    ) -> None:
        """初始化订单频率限制器.

        参数:
            max_orders_per_minute: 每分钟最大订单数
            window_seconds: 统计窗口秒数
        """
        self._max_orders = max_orders_per_minute
        self._window_seconds = window_seconds
        self._order_timestamps: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def can_place_order(self, account_id: str) -> bool:
        """检查是否可以下单.

        参数:
            account_id: 账户ID

        返回:
            是否允许下单
        """
        now = time.time()

        with self._lock:
            if account_id not in self._order_timestamps:
                self._order_timestamps[account_id] = deque()

            timestamps = self._order_timestamps[account_id]
            cutoff = now - self._window_seconds

            # 移除过期的时间戳
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            return len(timestamps) < self._max_orders

    def record_order(self, account_id: str) -> None:
        """记录订单.

        参数:
            account_id: 账户ID
        """
        now = time.time()

        with self._lock:
            if account_id not in self._order_timestamps:
                self._order_timestamps[account_id] = deque()

            self._order_timestamps[account_id].append(now)

    def get_order_count(self, account_id: str) -> int:
        """获取当前窗口内订单数量.

        参数:
            account_id: 账户ID

        返回:
            订单数量
        """
        now = time.time()

        with self._lock:
            if account_id not in self._order_timestamps:
                return 0

            timestamps = self._order_timestamps[account_id]
            cutoff = now - self._window_seconds

            # 移除过期的时间戳
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            return len(timestamps)

    def get_remaining_capacity(self, account_id: str) -> int:
        """获取剩余订单容量.

        参数:
            account_id: 账户ID

        返回:
            剩余可下单数量
        """
        return max(0, self._max_orders - self.get_order_count(account_id))

    def reset(self, account_id: str | None = None) -> None:
        """重置订单记录.

        参数:
            account_id: 账户ID，为None时重置所有账户
        """
        with self._lock:
            if account_id is None:
                self._order_timestamps.clear()
            elif account_id in self._order_timestamps:
                self._order_timestamps[account_id].clear()


class PositionLimitChecker:
    """仓位限制检查器 (线程安全).

    检查夜盘仓位限制，确保不超过配置的比例.

    属性:
        position_limit_ratio: 仓位限制比例
    """

    def __init__(self, position_limit_ratio: float = 0.5) -> None:
        """初始化仓位限制检查器.

        参数:
            position_limit_ratio: 仓位限制比例 (0-1)
        """
        self._position_limit_ratio = position_limit_ratio
        self._account_limits: dict[str, float] = {}
        self._current_positions: dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def position_limit_ratio(self) -> float:
        """仓位限制比例."""
        return self._position_limit_ratio

    def set_account_limit(self, account_id: str, max_position: float) -> None:
        """设置账户最大仓位.

        参数:
            account_id: 账户ID
            max_position: 最大仓位值
        """
        with self._lock:
            self._account_limits[account_id] = max_position

    def update_position(self, account_id: str, current_position: float) -> None:
        """更新当前仓位.

        参数:
            account_id: 账户ID
            current_position: 当前仓位值
        """
        with self._lock:
            self._current_positions[account_id] = current_position

    def check_position_limit(
        self,
        account_id: str,
        new_position: float,
    ) -> bool:
        """检查是否超过仓位限制.

        参数:
            account_id: 账户ID
            new_position: 新仓位值

        返回:
            True表示允许，False表示超限
        """
        with self._lock:
            max_position = self._account_limits.get(account_id, float("inf"))
            night_limit = max_position * self._position_limit_ratio

            return abs(new_position) <= night_limit

    def get_allowed_position(self, account_id: str) -> float:
        """获取允许的最大仓位.

        参数:
            account_id: 账户ID

        返回:
            允许的最大仓位值
        """
        with self._lock:
            max_position = self._account_limits.get(account_id, float("inf"))
            return max_position * self._position_limit_ratio

    def get_current_position(self, account_id: str) -> float:
        """获取当前仓位.

        参数:
            account_id: 账户ID

        返回:
            当前仓位值
        """
        with self._lock:
            return self._current_positions.get(account_id, 0.0)


# ============================================================
# 核心适配器
# ============================================================


class NightSessionRiskAdapter:
    """夜盘风控适配器 (军规 M6, M15).

    功能:
    1. 夜盘特殊风控规则
    2. 仓位限制调整 (50%上限)
    3. 止损收紧机制 (1.5倍)
    4. 订单频率限制 (30单/分钟)
    5. 与Guardian系统联动

    军规合规:
    - M6: 熔断保护 - 响应Guardian熔断事件
    - M15: 夜盘跨日 - 特殊风控规则

    示例:
        >>> adapter = NightSessionRiskAdapter()
        >>> signal = StrategySignalAdapter(
        ...     strategy_id="night_trend",
        ...     symbol="rb2501",
        ...     direction=SignalDirection.LONG,
        ...     strength=0.8,
        ...     confidence=0.9,
        ...     target_position=10.0,
        ...     stop_loss_price=3500.0,
        ... )
        >>> adjusted = adapter.apply_night_risk_rules(signal)
        >>> print(adjusted.stop_loss_price)  # 收紧后的止损
    """

    # 默认风控乘数
    NIGHT_RISK_MULTIPLIERS: ClassVar[dict[str, float]] = {
        "position_limit": 0.5,       # 仓位限制50%
        "stop_loss_tighter": 1.5,    # 止损收紧1.5倍
        "max_orders_per_min": 30,    # 每分钟最大订单数
    }

    def __init__(
        self,
        guardian: GuardianProtocol | Any | None = None,
        config: NightRiskConfig | None = None,
        on_circuit_breaker: Callable[[CircuitBreakerEventData], None] | None = None,
    ) -> None:
        """初始化夜盘风控适配器.

        参数:
            guardian: Guardian系统实例
            config: 夜盘风控配置
            on_circuit_breaker: 熔断事件回调
        """
        self._guardian = guardian
        self._config = config or NightRiskConfig()
        self._on_circuit_breaker = on_circuit_breaker

        # 初始化辅助组件
        self._order_rate_limiter = OrderRateLimiter(
            max_orders_per_minute=self._config.max_orders_per_minute,
            window_seconds=self._config.order_rate_window_seconds,
        )
        self._position_checker = PositionLimitChecker(
            position_limit_ratio=self._config.position_limit_ratio,
        )

        # 熔断状态跟踪
        self._circuit_breaker_accounts: dict[str, float] = {}  # account_id -> 熔断时间
        self._lock = threading.Lock()

        # 统计
        self._adjusted_signal_count: int = 0
        self._blocked_order_count: int = 0
        self._circuit_breaker_count: int = 0

        logger.info(
            "夜盘风控适配器初始化完成: position_limit=%.2f, "
            "stop_loss_tighter=%.2f, max_orders=%d",
            self._config.position_limit_ratio,
            self._config.stop_loss_tighter_ratio,
            self._config.max_orders_per_minute,
        )

    @property
    def config(self) -> NightRiskConfig:
        """获取配置."""
        return self._config

    @property
    def guardian(self) -> GuardianProtocol | Any | None:
        """获取Guardian系统."""
        return self._guardian

    @property
    def adjusted_signal_count(self) -> int:
        """获取调整信号计数."""
        return self._adjusted_signal_count

    @property
    def blocked_order_count(self) -> int:
        """获取阻止订单计数."""
        return self._blocked_order_count

    def apply_night_risk_rules(
        self,
        signal: StrategySignalAdapter,
    ) -> StrategySignalAdapter:
        """应用夜盘风控规则.

        调整信号以符合夜盘风控要求:
        1. 收紧止损价格
        2. 限制仓位大小

        参数:
            signal: 原始策略信号

        返回:
            调整后的策略信号
        """
        adjustment_reasons: list[str] = []

        # 保存原始止损
        original_stop_loss = signal.stop_loss_price
        new_stop_loss = signal.stop_loss_price
        new_position = signal.target_position

        # 1. 调整止损价格 (收紧)
        if signal.stop_loss_price is not None:
            new_stop_loss = self.calculate_adjusted_stop_loss(
                base_stop=signal.stop_loss_price,
                direction=signal.direction.value,
            )
            if new_stop_loss != signal.stop_loss_price:
                adjustment_reasons.append(
                    f"止损收紧: {signal.stop_loss_price:.2f} -> {new_stop_loss:.2f}"
                )

        # 2. 限制仓位
        position_limit = self._config.position_limit_ratio
        if abs(signal.target_position) > 0:
            max_allowed = abs(signal.target_position) * position_limit
            if abs(signal.target_position) > max_allowed:
                # 按比例缩减仓位
                sign = 1 if signal.target_position > 0 else -1
                new_position = sign * max_allowed
                adjustment_reasons.append(
                    f"仓位限制: {signal.target_position:.2f} -> {new_position:.2f}"
                )

        # 3. 降低信号强度
        adjusted_strength = signal.strength * 0.9  # 夜盘信号强度降低10%

        # 创建调整后的信号
        adjusted = StrategySignalAdapter(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            direction=signal.direction,
            strength=adjusted_strength,
            confidence=signal.confidence,
            target_position=new_position,
            stop_loss_price=new_stop_loss,
            original_stop_loss=original_stop_loss,
            adjusted=bool(adjustment_reasons),
            adjustment_reason="; ".join(adjustment_reasons) if adjustment_reasons else "",
            timestamp=signal.timestamp,
            metadata={
                **signal.metadata,
                "night_session_adjusted": True,
                "adjustment_count": len(adjustment_reasons),
            },
        )

        if adjustment_reasons:
            self._adjusted_signal_count += 1
            logger.debug(
                "夜盘风控调整信号 [%s]: %s",
                signal.strategy_id,
                "; ".join(adjustment_reasons),
            )

        return adjusted

    def check_position_limit(
        self,
        account_id: str,
        new_position: float,
    ) -> bool:
        """检查仓位限制.

        验证新仓位是否符合夜盘仓位限制.

        参数:
            account_id: 账户ID
            new_position: 新仓位值

        返回:
            True表示允许，False表示超限
        """
        # 检查Guardian熔断状态
        if self._guardian is not None:
            try:
                if hasattr(self._guardian, "is_trading_allowed"):
                    if not self._guardian.is_trading_allowed:
                        logger.warning(
                            "Guardian禁止交易，拒绝仓位变更: account=%s",
                            account_id,
                        )
                        return False

                if hasattr(self._guardian, "current_position_ratio"):
                    guardian_ratio = self._guardian.current_position_ratio
                    if guardian_ratio < 1.0:
                        # Guardian限制仓位比例
                        effective_limit = (
                            self._config.position_limit_ratio * guardian_ratio
                        )
                        allowed = self._position_checker.get_allowed_position(account_id)
                        adjusted_limit = allowed * guardian_ratio
                        if abs(new_position) > adjusted_limit:
                            logger.warning(
                                "仓位超限 (Guardian调整): account=%s, "
                                "new_position=%.2f, limit=%.2f",
                                account_id,
                                new_position,
                                adjusted_limit,
                            )
                            return False
            except Exception as e:
                logger.error("Guardian检查失败: %s", e)

        # 检查夜盘仓位限制
        result = self._position_checker.check_position_limit(account_id, new_position)

        if not result:
            logger.warning(
                "夜盘仓位超限: account=%s, new_position=%.2f, limit=%.2f",
                account_id,
                new_position,
                self._position_checker.get_allowed_position(account_id),
            )

        return result

    def calculate_adjusted_stop_loss(
        self,
        base_stop: float,
        direction: str,
    ) -> float:
        """计算调整后的止损价格.

        夜盘止损收紧机制:
        - 多头: 止损价格上移 (更接近入场价)
        - 空头: 止损价格下移 (更接近入场价)

        参数:
            base_stop: 基础止损价格
            direction: 信号方向 ("LONG" 或 "SHORT")

        返回:
            调整后的止损价格
        """
        tighter_ratio = self._config.stop_loss_tighter_ratio

        # 计算止损距离
        # 假设止损距离 = abs(当前价 - 止损价)
        # 收紧后距离 = 原距离 / tighter_ratio

        # 由于没有当前价格信息，我们使用一个简化的方法
        # 对止损价格按比例调整
        if direction == "LONG":
            # 多头止损在下方，收紧意味着止损价上移
            # 新止损 = 基础止损 * (1 + (tighter_ratio - 1) * 调整系数)
            adjustment_factor = (tighter_ratio - 1) * 0.1  # 10%的距离调整
            adjusted_stop = base_stop * (1 + adjustment_factor)
        elif direction == "SHORT":
            # 空头止损在上方，收紧意味着止损价下移
            adjustment_factor = (tighter_ratio - 1) * 0.1
            adjusted_stop = base_stop * (1 - adjustment_factor)
        else:
            # FLAT或其他方向，不调整
            adjusted_stop = base_stop

        return round(adjusted_stop, 2)

    def is_trading_allowed(self, account_id: str) -> bool:
        """检查是否允许交易.

        综合检查:
        1. Guardian系统状态
        2. 账户熔断状态
        3. 订单频率限制

        参数:
            account_id: 账户ID

        返回:
            是否允许交易
        """
        # 1. 检查Guardian系统
        if self._guardian is not None:
            try:
                if hasattr(self._guardian, "is_trading_allowed"):
                    if not self._guardian.is_trading_allowed:
                        logger.debug(
                            "Guardian禁止交易: account=%s",
                            account_id,
                        )
                        return False
            except Exception as e:
                logger.error("Guardian检查失败: %s", e)

        # 2. 检查账户熔断状态
        with self._lock:
            if account_id in self._circuit_breaker_accounts:
                breaker_time = self._circuit_breaker_accounts[account_id]
                cooldown = self._config.circuit_breaker_cooldown_seconds

                if time.time() - breaker_time < cooldown:
                    remaining = cooldown - (time.time() - breaker_time)
                    logger.debug(
                        "账户处于熔断冷却期: account=%s, remaining=%.1fs",
                        account_id,
                        remaining,
                    )
                    return False
                else:
                    # 冷却期结束，移除熔断标记
                    del self._circuit_breaker_accounts[account_id]

        # 3. 检查订单频率限制
        if not self._order_rate_limiter.can_place_order(account_id):
            logger.debug(
                "订单频率超限: account=%s, count=%d/%d",
                account_id,
                self._order_rate_limiter.get_order_count(account_id),
                self._config.max_orders_per_minute,
            )
            self._blocked_order_count += 1
            return False

        return True

    def on_circuit_breaker_triggered(
        self,
        event: CircuitBreakerEventData,
    ) -> None:
        """响应熔断事件.

        处理Guardian系统发送的熔断事件.

        参数:
            event: 熔断事件数据
        """
        account_id = event.account_id or "global"

        logger.warning(
            "收到熔断事件: type=%s, account=%s, reason=%s",
            event.event_type,
            account_id,
            event.trigger_reason,
        )

        # 记录熔断状态
        with self._lock:
            self._circuit_breaker_accounts[account_id] = time.time()
            self._circuit_breaker_count += 1

        # 通知回调
        if self._on_circuit_breaker is not None:
            try:
                self._on_circuit_breaker(event)
            except Exception as e:
                logger.error("熔断事件回调失败: %s", e)

        logger.info(
            "夜盘风控响应熔断: account=%s 进入冷却期 %.0fs",
            account_id,
            self._config.circuit_breaker_cooldown_seconds,
        )

    def record_order(self, account_id: str) -> None:
        """记录订单.

        用于订单频率统计.

        参数:
            account_id: 账户ID
        """
        self._order_rate_limiter.record_order(account_id)

    def set_account_limit(self, account_id: str, max_position: float) -> None:
        """设置账户最大仓位.

        参数:
            account_id: 账户ID
            max_position: 最大仓位值
        """
        self._position_checker.set_account_limit(account_id, max_position)

    def update_position(self, account_id: str, current_position: float) -> None:
        """更新当前仓位.

        参数:
            account_id: 账户ID
            current_position: 当前仓位值
        """
        self._position_checker.update_position(account_id, current_position)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "config": {
                "position_limit_ratio": self._config.position_limit_ratio,
                "stop_loss_tighter_ratio": self._config.stop_loss_tighter_ratio,
                "max_orders_per_minute": self._config.max_orders_per_minute,
                "circuit_breaker_cooldown_seconds": (
                    self._config.circuit_breaker_cooldown_seconds
                ),
            },
            "statistics": {
                "adjusted_signal_count": self._adjusted_signal_count,
                "blocked_order_count": self._blocked_order_count,
                "circuit_breaker_count": self._circuit_breaker_count,
            },
            "circuit_breaker_accounts": list(self._circuit_breaker_accounts.keys()),
            "guardian_connected": self._guardian is not None,
        }

    def reset_statistics(self) -> None:
        """重置统计信息."""
        self._adjusted_signal_count = 0
        self._blocked_order_count = 0
        self._circuit_breaker_count = 0
        self._order_rate_limiter.reset()

        with self._lock:
            self._circuit_breaker_accounts.clear()

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式.

        返回:
            审计日志字典
        """
        return {
            "event_type": "NIGHT_RISK_ADAPTER_STATUS",
            "timestamp": time.time(),
            "timestamp_iso": datetime.now(tz=timezone.utc).isoformat(),
            **self.get_statistics(),
        }


# ============================================================
# 便捷函数
# ============================================================


def create_night_risk_adapter(
    guardian: GuardianProtocol | Any | None = None,
    position_limit_ratio: float = 0.5,
    stop_loss_tighter_ratio: float = 1.5,
    max_orders_per_minute: int = 30,
    on_circuit_breaker: Callable[[CircuitBreakerEventData], None] | None = None,
) -> NightSessionRiskAdapter:
    """创建夜盘风控适配器.

    参数:
        guardian: Guardian系统实例
        position_limit_ratio: 仓位限制比例
        stop_loss_tighter_ratio: 止损收紧比例
        max_orders_per_minute: 每分钟最大订单数
        on_circuit_breaker: 熔断事件回调

    返回:
        夜盘风控适配器实例
    """
    config = NightRiskConfig(
        position_limit_ratio=position_limit_ratio,
        stop_loss_tighter_ratio=stop_loss_tighter_ratio,
        max_orders_per_minute=max_orders_per_minute,
    )

    return NightSessionRiskAdapter(
        guardian=guardian,
        config=config,
        on_circuit_breaker=on_circuit_breaker,
    )
