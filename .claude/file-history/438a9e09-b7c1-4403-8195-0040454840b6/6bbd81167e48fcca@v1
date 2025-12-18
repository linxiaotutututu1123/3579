"""
DecisionEvent - 策略决策事件

V3PRO+ Platform Component - Phase 1
V2 SPEC: 7.1
V2 Scenarios:
- STRAT.AUDIT.DECISION_EVENT_PRESENT
- STRAT.AUDIT.DECISION_HAS_RUN_ID
- STRAT.AUDIT.DECISION_HAS_EXEC_ID
- STRAT.AUDIT.DECISION_HAS_STRATEGY_ID
- STRAT.AUDIT.DECISION_HAS_VERSION
- STRAT.AUDIT.DECISION_HAS_FEATURE_HASH

军规级要求:
- 每次 on_tick 必须产生 DecisionEvent
- 必须包含 strategy_id, version, feature_hash
- 必须可追溯到 run_id 和 exec_id
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DecisionEvent:
    """策略决策事件.

    V2 Scenarios:
    - STRAT.AUDIT.DECISION_EVENT_PRESENT: DecisionEvent 存在
    - STRAT.AUDIT.DECISION_HAS_RUN_ID: 包含 run_id
    - STRAT.AUDIT.DECISION_HAS_EXEC_ID: 包含 exec_id
    - STRAT.AUDIT.DECISION_HAS_STRATEGY_ID: 包含 strategy_id
    - STRAT.AUDIT.DECISION_HAS_VERSION: 包含 version
    - STRAT.AUDIT.DECISION_HAS_FEATURE_HASH: 包含 feature_hash

    Attributes:
        ts: 时间戳（Unix epoch）
        run_id: 运行 ID（UUID）
        exec_id: 执行 ID
        strategy_id: 策略 ID（如 simple_ai, linear_ai）
        strategy_version: 策略版本（semver 或 commit hash）
        feature_hash: 输入特征哈希（用于回放确定性验证）
        target_portfolio: 目标仓位 {symbol: qty}
        confidence: 置信度（可选）
        signals: 信号详情（可选）
        metadata: 额外元数据（可选）
    """

    ts: float
    run_id: str
    exec_id: str
    strategy_id: str
    strategy_version: str
    feature_hash: str
    target_portfolio: dict[str, int]
    confidence: float | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """事件类型."""
        return "DECISION"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        data = asdict(self)
        data["event_type"] = self.event_type
        return data

    @classmethod
    def create(
        cls,
        ts: float,
        run_id: str,
        exec_id: str,
        strategy_id: str,
        strategy_version: str,
        features: dict[str, Any],
        target_portfolio: dict[str, int],
        confidence: float | None = None,
        signals: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "DecisionEvent":
        """创建决策事件.

        自动计算 feature_hash。

        Args:
            ts: 时间戳
            run_id: 运行 ID
            exec_id: 执行 ID
            strategy_id: 策略 ID
            strategy_version: 策略版本
            features: 输入特征（用于计算哈希）
            target_portfolio: 目标仓位
            confidence: 置信度
            signals: 信号详情
            metadata: 额外元数据

        Returns:
            DecisionEvent 实例
        """
        feature_hash = compute_feature_hash(features)
        return cls(
            ts=ts,
            run_id=run_id,
            exec_id=exec_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            feature_hash=feature_hash,
            target_portfolio=target_portfolio,
            confidence=confidence,
            signals=signals or {},
            metadata=metadata or {},
        )


def compute_feature_hash(features: dict[str, Any]) -> str:
    """计算特征哈希.

    V2 Scenario: STRAT.AUDIT.DECISION_HAS_FEATURE_HASH

    使用 SHA256 哈希确保相同输入产生相同哈希。

    Args:
        features: 输入特征字典

    Returns:
        16 位十六进制哈希字符串
    """
    # 排序键以确保确定性
    sorted_json = json.dumps(features, sort_keys=True, ensure_ascii=False)
    hash_bytes = hashlib.sha256(sorted_json.encode("utf-8")).digest()
    return hash_bytes[:8].hex()  # 返回前 16 位十六进制


def validate_decision_event(event: DecisionEvent) -> list[str]:
    """验证决策事件完整性.

    检查所有军规级必备字段。

    Args:
        event: 决策事件

    Returns:
        错误列表（空列表表示验证通过）
    """
    errors: list[str] = []

    if not event.run_id:
        errors.append("STRAT.AUDIT.DECISION_HAS_RUN_ID: run_id is missing")
    if not event.exec_id:
        errors.append("STRAT.AUDIT.DECISION_HAS_EXEC_ID: exec_id is missing")
    if not event.strategy_id:
        errors.append("STRAT.AUDIT.DECISION_HAS_STRATEGY_ID: strategy_id is missing")
    if not event.strategy_version:
        errors.append("STRAT.AUDIT.DECISION_HAS_VERSION: strategy_version is missing")
    if not event.feature_hash:
        errors.append("STRAT.AUDIT.DECISION_HAS_FEATURE_HASH: feature_hash is missing")

    return errors
