"""
ReplayVerifier - 回放验证器

V3PRO+ Platform Component - Phase 1
V2 SPEC: 7.3
V2 Scenarios: REPLAY.DETERMINISTIC.DECISION, REPLAY.DETERMINISTIC.GUARDIAN

军规级要求:
- 相同输入产生相同输出序列
- 输入哈希与原始一致
- 支持决策和 Guardian 事件验证
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ReplayResult:
    """回放验证结果.

    Attributes:
        is_deterministic: 是否确定性通过
        input_hash_match: 输入哈希是否匹配
        output_hash_match: 输出哈希是否匹配
        original_input_hash: 原始输入哈希
        replay_input_hash: 回放输入哈希
        original_output_hash: 原始输出哈希
        replay_output_hash: 回放输出哈希
        mismatches: 不匹配的事件索引列表
        details: 详细信息
    """

    is_deterministic: bool
    input_hash_match: bool
    output_hash_match: bool
    original_input_hash: str
    replay_input_hash: str
    original_output_hash: str
    replay_output_hash: str
    mismatches: list[int]
    details: dict[str, Any]


class ReplayVerifier:
    """回放验证器.

    V2 Scenarios:
    - REPLAY.DETERMINISTIC.DECISION: 决策确定性
    - REPLAY.DETERMINISTIC.GUARDIAN: Guardian 确定性

    验证相同输入是否产生相同的输出序列。
    """

    def __init__(self) -> None:
        """初始化验证器."""

    def compute_hash(self, data: Any) -> str:
        """计算数据哈希.

        Args:
            data: 要哈希的数据（可以是 dict、list 或 str）

        Returns:
            16 位十六进制哈希
        """
        if isinstance(data, str):
            json_str = data
        else:
            json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)

        hash_bytes = hashlib.sha256(json_str.encode("utf-8")).digest()
        return hash_bytes[:8].hex()

    def compute_sequence_hash(self, events: list[dict[str, Any]]) -> str:
        """计算事件序列哈希.

        Args:
            events: 事件列表

        Returns:
            序列哈希
        """
        # 只对关键字段哈希，忽略时间戳等可变字段
        key_fields = ["event_type", "strategy_id", "target_portfolio", "mode_from", "mode_to"]

        filtered_events = []
        for event in events:
            filtered = {k: v for k, v in event.items() if k in key_fields}
            filtered_events.append(filtered)

        return self.compute_hash(filtered_events)

    def verify_determinism(
        self,
        original_inputs: list[dict[str, Any]],
        original_outputs: list[dict[str, Any]],
        replay_inputs: list[dict[str, Any]],
        replay_outputs: list[dict[str, Any]],
    ) -> ReplayResult:
        """验证回放确定性.

        V2 Scenarios:
        - REPLAY.DETERMINISTIC.DECISION
        - REPLAY.DETERMINISTIC.GUARDIAN

        Args:
            original_inputs: 原始输入序列
            original_outputs: 原始输出序列
            replay_inputs: 回放输入序列
            replay_outputs: 回放输出序列

        Returns:
            验证结果
        """
        # 计算输入哈希
        original_input_hash = self.compute_hash(original_inputs)
        replay_input_hash = self.compute_hash(replay_inputs)
        input_hash_match = original_input_hash == replay_input_hash

        # 计算输出哈希
        original_output_hash = self.compute_sequence_hash(original_outputs)
        replay_output_hash = self.compute_sequence_hash(replay_outputs)
        output_hash_match = original_output_hash == replay_output_hash

        # 找出不匹配的事件
        mismatches: list[int] = []
        min_len = min(len(original_outputs), len(replay_outputs))
        for i in range(min_len):
            if not self._events_match(original_outputs[i], replay_outputs[i]):
                mismatches.append(i)

        # 长度不同也记录
        if len(original_outputs) != len(replay_outputs):
            mismatches.extend(range(min_len, max(len(original_outputs), len(replay_outputs))))

        is_deterministic = input_hash_match and output_hash_match and len(mismatches) == 0

        return ReplayResult(
            is_deterministic=is_deterministic,
            input_hash_match=input_hash_match,
            output_hash_match=output_hash_match,
            original_input_hash=original_input_hash,
            replay_input_hash=replay_input_hash,
            original_output_hash=original_output_hash,
            replay_output_hash=replay_output_hash,
            mismatches=mismatches,
            details={
                "original_output_count": len(original_outputs),
                "replay_output_count": len(replay_outputs),
                "mismatch_count": len(mismatches),
            },
        )

    def _events_match(self, e1: dict[str, Any], e2: dict[str, Any]) -> bool:
        """比较两个事件是否匹配.

        忽略时间戳等可变字段。

        Args:
            e1: 事件 1
            e2: 事件 2

        Returns:
            是否匹配
        """
        # 忽略时间戳
        ignore_fields = {"ts", "timestamp"}

        for key in set(e1.keys()) | set(e2.keys()):
            if key in ignore_fields:
                continue
            if e1.get(key) != e2.get(key):
                return False

        return True

    def verify_decision_determinism(
        self,
        original_decisions: list[dict[str, Any]],
        replay_decisions: list[dict[str, Any]],
    ) -> ReplayResult:
        """验证决策确定性.

        V2 Scenario: REPLAY.DETERMINISTIC.DECISION

        Args:
            original_decisions: 原始决策事件列表
            replay_decisions: 回放决策事件列表

        Returns:
            验证结果
        """

        # 提取决策关键字段
        def extract_decision_key(d: dict[str, Any]) -> dict[str, Any]:
            return {
                "strategy_id": d.get("strategy_id"),
                "feature_hash": d.get("feature_hash"),
                "target_portfolio": d.get("target_portfolio"),
            }

        original_keys = [extract_decision_key(d) for d in original_decisions]
        replay_keys = [extract_decision_key(d) for d in replay_decisions]

        return self.verify_determinism(
            original_inputs=[],
            original_outputs=original_keys,
            replay_inputs=[],
            replay_outputs=replay_keys,
        )

    def verify_guardian_determinism(
        self,
        original_events: list[dict[str, Any]],
        replay_events: list[dict[str, Any]],
    ) -> ReplayResult:
        """验证 Guardian 确定性.

        V2 Scenario: REPLAY.DETERMINISTIC.GUARDIAN

        Args:
            original_events: 原始 Guardian 事件列表
            replay_events: 回放 Guardian 事件列表

        Returns:
            验证结果
        """

        # 提取 Guardian 关键字段
        def extract_guardian_key(e: dict[str, Any]) -> dict[str, Any]:
            return {
                "guardian_event_type": e.get("guardian_event_type"),
                "mode_from": e.get("mode_from"),
                "mode_to": e.get("mode_to"),
                "trigger": e.get("trigger"),
                "action": e.get("action"),
            }

        original_keys = [extract_guardian_key(e) for e in original_events]
        replay_keys = [extract_guardian_key(e) for e in replay_events]

        return self.verify_determinism(
            original_inputs=[],
            original_outputs=original_keys,
            replay_inputs=[],
            replay_outputs=replay_keys,
        )
