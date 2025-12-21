"""
OrderIntent 与 client_order_id 幂等键体系.

V4PRO Platform Component - Mode 2 Trading Execution Pipeline
军规覆盖: M1(单一信号源), M2(幂等执行), M7(回放一致)

V4PRO Scenarios:
- MODE2.INTENT.IDEMPOTENT: intent_id 幂等键确保同一意图不重复执行
- MODE2.INTENT.REPLAY: 回放时相同输入产生相同 intent_id
- MODE2.INTENT.AUDIT_TRACE: 意图到订单完整追溯

intent_id 组成:
    SHA256(strategy_id + decision_hash + instrument + side + offset + target_qty + signal_ts)[:16]

军规级要求:
- intent_id 必须在系统重启后保持一致 (M7)
- 同一 intent_id 的重复提交必须被拒绝 (M2)
- 所有 intent 必须关联到策略信号源 (M1)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlgoType(str, Enum):
    """执行算法类型.

    支持的算法:
    - IMMEDIATE: 立即执行，一次性下单
    - TWAP: 时间加权平均价格算法
    - VWAP: 成交量加权平均价格算法
    - ICEBERG: 冰山单，分批隐藏显示量
    - POV: 参与率算法 (Percentage of Volume)
    - ADAPTIVE: 自适应算法，根据市场状态动态调整
    """

    IMMEDIATE = "IMMEDIATE"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    POV = "POV"
    ADAPTIVE = "ADAPTIVE"


class Urgency(str, Enum):
    """执行紧急程度.

    影响执行速度和滑点容忍度:
    - LOW: 低紧急度，优先最小化市场冲击
    - NORMAL: 正常紧急度，平衡冲击和速度
    - HIGH: 高紧急度，优先快速完成
    - CRITICAL: 关键紧急度，立即全量执行（风控触发等场景）
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Side(str, Enum):
    """交易方向."""

    BUY = "BUY"
    SELL = "SELL"


class Offset(str, Enum):
    """开平方向.

    中国期货市场特化:
    - OPEN: 开仓
    - CLOSE: 平仓（平昨）
    - CLOSETODAY: 平今仓
    - AUTO: 自动选择（优先平今，减少手续费）
    """

    OPEN = "OPEN"
    CLOSE = "CLOSE"
    CLOSETODAY = "CLOSETODAY"
    AUTO = "AUTO"


@dataclass(frozen=True)
class OrderIntent:
    """交易意图 - 策略层输出对象.

    OrderIntent 是策略层到执行层的唯一接口，封装了所有执行所需信息。

    V4PRO Scenarios:
    - MODE2.INTENT.IDEMPOTENT: intent_id 幂等键
    - MODE2.INTENT.REPLAY: 回放一致性
    - MODE2.INTENT.AUDIT_TRACE: 审计追溯

    军规级要求:
    - strategy_id 必须唯一标识信号来源 (M1)
    - decision_hash 必须与策略决策关联 (M3)
    - intent_id 必须确定性生成 (M7)

    Attributes:
        strategy_id: 策略唯一标识符，用于追溯信号来源
        decision_hash: 策略决策哈希，关联到具体决策日志
        instrument: 合约代码，如 "rb2501"
        side: 交易方向 (BUY/SELL)
        offset: 开平方向 (OPEN/CLOSE/CLOSETODAY/AUTO)
        target_qty: 目标数量（正整数）
        algo: 执行算法类型
        urgency: 紧急程度
        limit_price: 限价（None 表示市价）
        signal_ts: 信号时间戳（毫秒精度）
        expire_ts: 过期时间戳（毫秒精度，None 表示当日有效）
        parent_intent_id: 父意图ID（用于关联分拆订单）
        metadata: 扩展元数据
    """

    strategy_id: str
    decision_hash: str
    instrument: str
    side: Side
    offset: Offset
    target_qty: int
    algo: AlgoType = AlgoType.IMMEDIATE
    urgency: Urgency = Urgency.NORMAL
    limit_price: float | None = None
    signal_ts: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    expire_ts: int | None = None
    parent_intent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """验证参数合法性."""
        if self.target_qty <= 0:
            raise ValueError(f"target_qty 必须为正整数, 当前值: {self.target_qty}")
        if not self.strategy_id:
            raise ValueError("strategy_id 不能为空 (军规 M1)")
        if not self.decision_hash:
            raise ValueError("decision_hash 不能为空 (军规 M3)")
        if not self.instrument:
            raise ValueError("instrument 不能为空")

    @property
    def intent_id(self) -> str:
        """生成幂等键 intent_id.

        V4PRO Scenario: MODE2.INTENT.IDEMPOTENT

        组成: SHA256(strategy_id + decision_hash + instrument + side + offset + target_qty + signal_ts)[:16]

        Returns:
            16 字符的十六进制幂等键
        """
        return IntentIdGenerator.generate(
            strategy_id=self.strategy_id,
            decision_hash=self.decision_hash,
            instrument=self.instrument,
            side=self.side.value,
            offset=self.offset.value,
            target_qty=self.target_qty,
            signal_ts=self.signal_ts,
        )

    def is_expired(self, current_ts: int | None = None) -> bool:
        """检查意图是否已过期.

        Args:
            current_ts: 当前时间戳（毫秒），None 表示使用当前时间

        Returns:
            是否已过期
        """
        if self.expire_ts is None:
            return False
        now = current_ts or int(datetime.now().timestamp() * 1000)
        return now > self.expire_ts

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于审计日志）.

        Returns:
            包含所有字段的字典
        """
        return {
            "intent_id": self.intent_id,
            "strategy_id": self.strategy_id,
            "decision_hash": self.decision_hash,
            "instrument": self.instrument,
            "side": self.side.value,
            "offset": self.offset.value,
            "target_qty": self.target_qty,
            "algo": self.algo.value,
            "urgency": self.urgency.value,
            "limit_price": self.limit_price,
            "signal_ts": self.signal_ts,
            "expire_ts": self.expire_ts,
            "parent_intent_id": self.parent_intent_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrderIntent":
        """从字典创建 OrderIntent.

        Args:
            data: 字典数据

        Returns:
            OrderIntent 实例
        """
        return cls(
            strategy_id=data["strategy_id"],
            decision_hash=data["decision_hash"],
            instrument=data["instrument"],
            side=Side(data["side"]),
            offset=Offset(data["offset"]),
            target_qty=data["target_qty"],
            algo=AlgoType(data.get("algo", "IMMEDIATE")),
            urgency=Urgency(data.get("urgency", "NORMAL")),
            limit_price=data.get("limit_price"),
            signal_ts=data.get("signal_ts", int(datetime.now().timestamp() * 1000)),
            expire_ts=data.get("expire_ts"),
            parent_intent_id=data.get("parent_intent_id"),
            metadata=data.get("metadata", {}),
        )


class IntentIdGenerator:
    """幂等键生成器.

    V4PRO Scenarios:
    - MODE2.INTENT.IDEMPOTENT: intent_id 幂等键确保同一意图不重复执行
    - MODE2.INTENT.REPLAY: 回放时相同输入产生相同 intent_id

    军规级要求:
    - 生成算法必须确定性 (M7)
    - 必须使用密码学安全的哈希函数
    - 必须包含所有关键字段防止碰撞
    """

    # 分隔符，用于组合字段
    SEPARATOR = "|"

    # 哈希前缀长度（16 字符 = 64 bit）
    HASH_PREFIX_LENGTH = 16

    @classmethod
    def generate(
        cls,
        strategy_id: str,
        decision_hash: str,
        instrument: str,
        side: str,
        offset: str,
        target_qty: int,
        signal_ts: int,
    ) -> str:
        """生成 intent_id.

        V4PRO Scenario: MODE2.INTENT.IDEMPOTENT

        Args:
            strategy_id: 策略ID
            decision_hash: 决策哈希
            instrument: 合约代码
            side: 交易方向
            offset: 开平方向
            target_qty: 目标数量
            signal_ts: 信号时间戳

        Returns:
            16 字符的十六进制幂等键
        """
        # 组合所有关键字段
        components = [
            strategy_id,
            decision_hash,
            instrument,
            side,
            offset,
            str(target_qty),
            str(signal_ts),
        ]

        # 使用分隔符连接
        payload = cls.SEPARATOR.join(components)

        # SHA256 哈希
        hash_bytes = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        # 取前 16 字符
        return hash_bytes[:cls.HASH_PREFIX_LENGTH]

    @classmethod
    def generate_client_order_id(
        cls,
        intent_id: str,
        slice_index: int,
        retry_count: int = 0,
    ) -> str:
        """生成 client_order_id.

        用于实际下单时的订单标识，支持分片和重试。

        组成: {intent_id}_{slice_index:04d}_{retry_count:02d}

        Args:
            intent_id: 意图ID
            slice_index: 分片索引（0-9999）
            retry_count: 重试次数（0-99）

        Returns:
            client_order_id

        Raises:
            ValueError: 参数超出范围
        """
        if not 0 <= slice_index <= 9999:
            raise ValueError(f"slice_index 超出范围 [0, 9999]: {slice_index}")
        if not 0 <= retry_count <= 99:
            raise ValueError(f"retry_count 超出范围 [0, 99]: {retry_count}")

        return f"{intent_id}_{slice_index:04d}_{retry_count:02d}"

    @classmethod
    def parse_client_order_id(cls, client_order_id: str) -> tuple[str, int, int]:
        """解析 client_order_id.

        Args:
            client_order_id: 订单ID

        Returns:
            (intent_id, slice_index, retry_count)

        Raises:
            ValueError: 格式错误
        """
        parts = client_order_id.rsplit("_", 2)
        if len(parts) != 3:
            raise ValueError(f"client_order_id 格式错误: {client_order_id}")

        intent_id = parts[0]
        try:
            slice_index = int(parts[1])
            retry_count = int(parts[2])
        except ValueError as e:
            raise ValueError(f"client_order_id 解析失败: {client_order_id}") from e

        return intent_id, slice_index, retry_count


class IntentRegistry:
    """意图注册表.

    用于跟踪已提交的意图，防止重复执行。

    V4PRO Scenario: MODE2.INTENT.IDEMPOTENT

    军规级要求:
    - 必须在内存中维护已执行意图列表
    - 重启后应从审计日志恢复状态
    """

    def __init__(self) -> None:
        """初始化注册表."""
        self._intents: dict[str, OrderIntent] = {}
        self._completed: set[str] = set()
        self._failed: set[str] = set()

    def register(self, intent: OrderIntent) -> bool:
        """注册意图.

        Args:
            intent: 交易意图

        Returns:
            是否注册成功（False 表示已存在）
        """
        intent_id = intent.intent_id
        if intent_id in self._intents:
            return False

        self._intents[intent_id] = intent
        return True

    def is_registered(self, intent_id: str) -> bool:
        """检查意图是否已注册.

        Args:
            intent_id: 意图ID

        Returns:
            是否已注册
        """
        return intent_id in self._intents

    def get(self, intent_id: str) -> OrderIntent | None:
        """获取意图.

        Args:
            intent_id: 意图ID

        Returns:
            意图对象或 None
        """
        return self._intents.get(intent_id)

    def mark_completed(self, intent_id: str) -> None:
        """标记意图完成.

        Args:
            intent_id: 意图ID
        """
        self._completed.add(intent_id)

    def mark_failed(self, intent_id: str) -> None:
        """标记意图失败.

        Args:
            intent_id: 意图ID
        """
        self._failed.add(intent_id)

    def is_completed(self, intent_id: str) -> bool:
        """检查意图是否已完成.

        Args:
            intent_id: 意图ID

        Returns:
            是否已完成
        """
        return intent_id in self._completed

    def is_failed(self, intent_id: str) -> bool:
        """检查意图是否已失败.

        Args:
            intent_id: 意图ID

        Returns:
            是否已失败
        """
        return intent_id in self._failed

    def get_active_intents(self) -> list[OrderIntent]:
        """获取活动意图列表.

        Returns:
            活动意图列表
        """
        return [
            intent
            for intent_id, intent in self._intents.items()
            if intent_id not in self._completed and intent_id not in self._failed
        ]

    def clear(self) -> None:
        """清空注册表."""
        self._intents.clear()
        self._completed.clear()
        self._failed.clear()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于持久化）.

        Returns:
            包含所有状态的字典
        """
        return {
            "intents": {k: v.to_dict() for k, v in self._intents.items()},
            "completed": list(self._completed),
            "failed": list(self._failed),
        }

    def __len__(self) -> int:
        """返回注册的意图数量."""
        return len(self._intents)
