"""
信号源定义模块 (军规级 v4.2).

V4PRO Platform Component - D7-P0 单一信号源机制
V4 SPEC: M1军规 - 一个交易信号只能来自一个策略实例

军规覆盖:
- M1: 单一信号源 - 信号源唯一性保证
- M3: 审计日志 - 信号源追溯
- M7: 场景回放 - 信号可重放

功能特性:
- 信号源唯一ID生成
- 信号源签名和验证
- 信号源生命周期管理
- 审计日志支持

示例:
    >>> from src.strategy.signal import SignalSource, TradingSignal
    >>> source = SignalSource(strategy_id="kalman_arb", instance_id="inst_001")
    >>> signal = source.create_signal(
    ...     symbol="rb2501",
    ...     direction=SignalDirection.LONG,
    ...     strength=0.8,
    ...     confidence=0.9
    ... )
    >>> signal.source_id  # 唯一信号源ID
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    pass


class SignalDirection(Enum):
    """信号方向枚举."""

    LONG = "LONG"  # 多头
    SHORT = "SHORT"  # 空头
    FLAT = "FLAT"  # 平仓/观望


class SignalType(Enum):
    """信号类型枚举."""

    ENTRY = "ENTRY"  # 入场信号
    EXIT = "EXIT"  # 出场信号
    ADJUST = "ADJUST"  # 调整信号
    HEDGE = "HEDGE"  # 对冲信号


class SignalPriority(Enum):
    """信号优先级枚举."""

    CRITICAL = 1  # 最高优先级 (紧急止损)
    HIGH = 2  # 高优先级 (风控信号)
    NORMAL = 3  # 普通优先级
    LOW = 4  # 低优先级 (观察信号)


class SourceStatus(Enum):
    """信号源状态枚举."""

    ACTIVE = "ACTIVE"  # 活跃
    SUSPENDED = "SUSPENDED"  # 暂停
    DISABLED = "DISABLED"  # 禁用
    EXPIRED = "EXPIRED"  # 过期


@dataclass(frozen=True, slots=True)
class SignalSourceID:
    """信号源唯一标识符 (不可变).

    格式: {strategy_id}:{instance_id}:{nonce}

    属性:
        strategy_id: 策略ID
        instance_id: 实例ID
        nonce: 随机数 (防止碰撞)
        created_at: 创建时间戳
    """

    strategy_id: str
    instance_id: str
    nonce: str
    created_at: float

    @classmethod
    def generate(cls, strategy_id: str, instance_id: str) -> SignalSourceID:
        """生成新的信号源ID.

        参数:
            strategy_id: 策略ID
            instance_id: 实例ID

        返回:
            新的SignalSourceID实例
        """
        return cls(
            strategy_id=strategy_id,
            instance_id=instance_id,
            nonce=secrets.token_hex(4),
            created_at=time.time(),
        )

    @property
    def full_id(self) -> str:
        """获取完整ID字符串."""
        return f"{self.strategy_id}:{self.instance_id}:{self.nonce}"

    def __str__(self) -> str:
        """字符串表示."""
        return self.full_id

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "instance_id": self.instance_id,
            "nonce": self.nonce,
            "created_at": self.created_at,
            "full_id": self.full_id,
        }


@dataclass(frozen=True, slots=True)
class TradingSignal:
    """交易信号 (不可变) - M1军规核心数据结构.

    属性:
        signal_id: 信号唯一ID
        source_id: 信号源ID (M1: 唯一来源)
        symbol: 合约代码
        direction: 信号方向
        signal_type: 信号类型
        strength: 信号强度 (0-1)
        confidence: 置信度 (0-1)
        priority: 优先级
        timestamp: 时间戳
        expire_at: 过期时间戳
        signature: 数字签名 (防篡改)
        metadata: 元数据
    """

    signal_id: str
    source_id: str
    symbol: str
    direction: SignalDirection
    signal_type: SignalType
    strength: float
    confidence: float
    priority: SignalPriority
    timestamp: float
    expire_at: float
    signature: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查信号是否过期."""
        return time.time() > self.expire_at

    def is_valid(self) -> bool:
        """检查信号是否有效."""
        return (
            not self.is_expired()
            and 0 <= self.strength <= 1
            and 0 <= self.confidence <= 1
            and self.source_id
            and self.symbol
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典 (用于审计)."""
        return {
            "signal_id": self.signal_id,
            "source_id": self.source_id,
            "symbol": self.symbol,
            "direction": self.direction.value,
            "signal_type": self.signal_type.value,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=UTC
            ).isoformat(),
            "expire_at": self.expire_at,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "SIGNAL_CREATED",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.to_dict(),
        }


@dataclass
class SignalSource:
    """信号源 (M1军规核心组件).

    负责:
    - 生成具有唯一源ID的交易信号
    - 信号签名和验证
    - 信号生命周期管理
    - 审计追踪

    属性:
        strategy_id: 策略ID
        instance_id: 实例ID
        source_id: 信号源ID
        status: 源状态
        signal_ttl: 信号生存时间(秒)
        secret_key: 签名密钥
        signal_counter: 信号计数器
        last_signal_time: 最后信号时间
    """

    # 默认配置
    DEFAULT_SIGNAL_TTL: ClassVar[float] = 60.0  # 信号默认60秒有效
    MIN_SIGNAL_INTERVAL: ClassVar[float] = 0.1  # 最小信号间隔100ms

    strategy_id: str
    instance_id: str
    source_id: SignalSourceID = field(init=False)
    status: SourceStatus = field(default=SourceStatus.ACTIVE)
    signal_ttl: float = field(default=60.0)
    secret_key: str = field(default_factory=lambda: secrets.token_hex(16))

    # 内部状态
    _signal_counter: int = field(default=0, init=False, repr=False)
    _last_signal_time: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        """初始化后处理."""
        self.source_id = SignalSourceID.generate(self.strategy_id, self.instance_id)

    @property
    def full_source_id(self) -> str:
        """获取完整信号源ID."""
        return self.source_id.full_id

    @property
    def signal_counter(self) -> int:
        """获取信号计数."""
        return self._signal_counter

    @property
    def last_signal_time(self) -> float:
        """获取最后信号时间."""
        return self._last_signal_time

    def is_active(self) -> bool:
        """检查信号源是否活跃."""
        return self.status == SourceStatus.ACTIVE

    def suspend(self) -> None:
        """暂停信号源."""
        self.status = SourceStatus.SUSPENDED

    def activate(self) -> None:
        """激活信号源."""
        self.status = SourceStatus.ACTIVE

    def disable(self) -> None:
        """禁用信号源."""
        self.status = SourceStatus.DISABLED

    def can_emit_signal(self) -> bool:
        """检查是否可以发射信号."""
        if not self.is_active():
            return False

        # 检查最小信号间隔
        now = time.time()
        if now - self._last_signal_time < self.MIN_SIGNAL_INTERVAL:
            return False

        return True

    def create_signal(
        self,
        symbol: str,
        direction: SignalDirection,
        strength: float,
        confidence: float,
        signal_type: SignalType = SignalType.ENTRY,
        priority: SignalPriority = SignalPriority.NORMAL,
        ttl: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TradingSignal:
        """创建交易信号.

        参数:
            symbol: 合约代码
            direction: 信号方向
            strength: 信号强度 (0-1)
            confidence: 置信度 (0-1)
            signal_type: 信号类型
            priority: 优先级
            ttl: 信号生存时间
            metadata: 元数据

        返回:
            TradingSignal实例

        异常:
            ValueError: 信号源未激活或参数无效
        """
        if not self.is_active():
            raise ValueError(f"Signal source {self.full_source_id} is not active")

        if not self.can_emit_signal():
            raise ValueError("Signal emission rate limit exceeded")

        # 验证参数
        strength = max(0.0, min(1.0, strength))
        confidence = max(0.0, min(1.0, confidence))

        # 生成信号ID
        now = time.time()
        self._signal_counter += 1
        signal_id = self._generate_signal_id(now)

        # 计算过期时间
        actual_ttl = ttl if ttl is not None else self.signal_ttl
        expire_at = now + actual_ttl

        # 生成签名
        signature = self._sign_signal(
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            strength=strength,
            timestamp=now,
        )

        # 构建元数据
        signal_metadata = {
            "strategy_id": self.strategy_id,
            "instance_id": self.instance_id,
            "signal_sequence": self._signal_counter,
            **(metadata or {}),
        }

        # 更新最后信号时间
        self._last_signal_time = now

        return TradingSignal(
            signal_id=signal_id,
            source_id=self.full_source_id,
            symbol=symbol,
            direction=direction,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            priority=priority,
            timestamp=now,
            expire_at=expire_at,
            signature=signature,
            metadata=signal_metadata,
        )

    def _generate_signal_id(self, timestamp: float) -> str:
        """生成信号ID.

        格式: sig_{source_short}_{counter}_{uuid_short}
        """
        source_short = hashlib.sha256(self.full_source_id.encode()).hexdigest()[:8]
        uuid_short = uuid.uuid4().hex[:8]
        return f"sig_{source_short}_{self._signal_counter}_{uuid_short}"

    def _sign_signal(
        self,
        signal_id: str,
        symbol: str,
        direction: SignalDirection,
        strength: float,
        timestamp: float,
    ) -> str:
        """签名信号 (防篡改).

        参数:
            signal_id: 信号ID
            symbol: 合约代码
            direction: 信号方向
            strength: 信号强度
            timestamp: 时间戳

        返回:
            签名字符串
        """
        payload = f"{signal_id}:{self.full_source_id}:{symbol}:{direction.value}:{strength}:{timestamp}"
        signature_input = f"{payload}:{self.secret_key}"
        return hashlib.sha256(signature_input.encode()).hexdigest()[:16]

    def verify_signal(self, signal: TradingSignal) -> bool:
        """验证信号签名.

        参数:
            signal: 待验证的信号

        返回:
            验证是否通过
        """
        if signal.source_id != self.full_source_id:
            return False

        expected_signature = self._sign_signal(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            direction=signal.direction,
            strength=signal.strength,
            timestamp=signal.timestamp,
        )

        return signal.signature == expected_signature

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        return {
            "source_id": self.full_source_id,
            "strategy_id": self.strategy_id,
            "instance_id": self.instance_id,
            "status": self.status.value,
            "signal_count": self._signal_counter,
            "last_signal_time": self._last_signal_time,
            "signal_ttl": self.signal_ttl,
            "created_at": self.source_id.created_at,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """生成审计记录 (M3)."""
        return {
            "event_type": "SIGNAL_SOURCE_STATUS",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.get_statistics(),
        }


# ============================================================
# 便捷函数
# ============================================================


def create_signal_source(
    strategy_id: str,
    instance_id: str | None = None,
    signal_ttl: float = 60.0,
) -> SignalSource:
    """创建信号源.

    参数:
        strategy_id: 策略ID
        instance_id: 实例ID (可选, 自动生成)
        signal_ttl: 信号生存时间

    返回:
        SignalSource实例
    """
    if instance_id is None:
        instance_id = f"inst_{uuid.uuid4().hex[:8]}"

    return SignalSource(
        strategy_id=strategy_id,
        instance_id=instance_id,
        signal_ttl=signal_ttl,
    )


def generate_source_id(strategy_id: str, instance_id: str) -> SignalSourceID:
    """生成信号源ID.

    参数:
        strategy_id: 策略ID
        instance_id: 实例ID

    返回:
        SignalSourceID实例
    """
    return SignalSourceID.generate(strategy_id, instance_id)
