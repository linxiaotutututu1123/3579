"""Replay验证器增强测试 (军规级 v4.0)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.replay.verifier import ReplayVerifier, VerifyResult, verify_replay_determinism


class TestVerifyResult:
    """验证结果测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        result = VerifyResult(
            is_match=True,
            hash_a="abc123",
            hash_b="abc123",
            length_a=10,
            length_b=10,
        )
        d = result.to_dict()
        assert d["is_match"] is True
        assert d["hash_a"] == "abc123"
        assert d["length_a"] == 10

    def test_to_dict_with_mismatch(self) -> None:
        """测试带不匹配的转字典."""
        result = VerifyResult(
            is_match=False,
            hash_a="abc",
            hash_b="def",
            length_a=5,
            length_b=6,
            first_mismatch_index=3,
            first_mismatch_a={"type": "decision"},
            first_mismatch_b={"type": "guardian"},
            details={"length_mismatch": True},
        )
        d = result.to_dict()
        assert d["is_match"] is False
        assert d["first_mismatch_index"] == 3
        assert d["details"]["length_mismatch"] is True


class TestReplayVerifierBasic:
    """Replay验证器基本测试."""

    def test_verify_decision_sequence_match(self) -> None:
        """测试决策序列匹配."""
        verifier = ReplayVerifier()
        events_a = [
            {"event_type": "decision", "action": "buy", "ts": "2025-01-01"},
            {"event_type": "decision", "action": "sell", "ts": "2025-01-02"},
        ]
        events_b = [
            {"event_type": "decision", "action": "buy", "ts": "2025-01-03"},
            {"event_type": "decision", "action": "sell", "ts": "2025-01-04"},
        ]
        result = verifier.verify_decision_sequence(events_a, events_b)
        assert result.is_match is True

    def test_verify_decision_sequence_mismatch(self) -> None:
        """测试决策序列不匹配."""
        verifier = ReplayVerifier()
        events_a = [{"event_type": "decision", "action": "buy"}]
        events_b = [{"event_type": "decision", "action": "sell"}]
        result = verifier.verify_decision_sequence(events_a, events_b)
        assert result.is_match is False
        assert result.first_mismatch_index == 0

    def test_verify_guardian_sequence_match(self) -> None:
        """测试守护序列匹配."""
        verifier = ReplayVerifier()
        events_a = [{"event_type": "guardian_mode_change", "mode": "normal"}]
        events_b = [{"event_type": "guardian_mode_change", "mode": "normal"}]
        result = verifier.verify_guardian_sequence(events_a, events_b)
        assert result.is_match is True

    def test_verify_guardian_sequence_mismatch(self) -> None:
        """测试守护序列不匹配."""
        verifier = ReplayVerifier()
        events_a = [{"event_type": "guardian", "mode": "normal"}]
        events_b = [{"event_type": "guardian", "mode": "panic"}]
        result = verifier.verify_guardian_sequence(events_a, events_b)
        assert result.is_match is False


class TestReplayVerifierFiltering:
    """事件过滤测试."""

    def test_filter_by_type_decision(self) -> None:
        """测试决策事件过滤."""
        verifier = ReplayVerifier()
        events = [
            {"event_type": "decision", "data": 1},
            {"event_type": "guardian", "data": 2},
            {"event_type": "decision_start", "data": 3},
        ]
        filtered = verifier._filter_by_type(events, "decision")
        assert len(filtered) == 2

    def test_filter_by_type_guardian(self) -> None:
        """测试守护事件过滤."""
        verifier = ReplayVerifier()
        events = [
            {"event_type": "decision", "data": 1},
            {"event_type": "guardian_alert", "data": 2},
            {"event_type": "mode_guardian_change", "data": 3},
        ]
        filtered = verifier._filter_by_type(events, "guardian")
        assert len(filtered) == 2

    def test_filter_empty_type(self) -> None:
        """测试空类型过滤."""
        verifier = ReplayVerifier()
        events = [{"data": 1}, {"event_type": "", "data": 2}]
        filtered = verifier._filter_by_type(events, "decision")
        assert len(filtered) == 0


class TestReplayVerifierEventsMatch:
    """事件匹配测试."""

    def test_events_match_both_none(self) -> None:
        """测试两个都为None."""
        verifier = ReplayVerifier()
        assert verifier._events_match(None, None) is True

    def test_events_match_one_none(self) -> None:
        """测试一个为None."""
        verifier = ReplayVerifier()
        assert verifier._events_match({"a": 1}, None) is False
        assert verifier._events_match(None, {"a": 1}) is False

    def test_events_match_identical(self) -> None:
        """测试完全相同."""
        verifier = ReplayVerifier()
        event = {"type": "test", "value": 123}
        assert verifier._events_match(event, event.copy()) is True

    def test_events_match_ignore_timestamp(self) -> None:
        """测试忽略时间戳."""
        verifier = ReplayVerifier()
        event_a = {"type": "test", "ts": "2025-01-01"}
        event_b = {"type": "test", "ts": "2025-01-02"}
        assert verifier._events_match(event_a, event_b) is True


class TestReplayVerifierNormalize:
    """事件规范化测试."""

    def test_normalize_simple(self) -> None:
        """测试简单规范化."""
        verifier = ReplayVerifier()
        event = {"type": "test", "ts": "2025-01-01", "value": 42}
        normalized = verifier._normalize_event(event)
        assert "ts" not in normalized
        assert normalized["type"] == "test"
        assert normalized["value"] == 42

    def test_normalize_nested_dict(self) -> None:
        """测试嵌套字典规范化."""
        verifier = ReplayVerifier()
        event = {
            "type": "test",
            "nested": {"ts": "ignored", "data": "kept"},
        }
        normalized = verifier._normalize_event(event)
        assert "ts" not in normalized["nested"]
        assert normalized["nested"]["data"] == "kept"

    def test_normalize_exclude_all_timestamp_fields(self) -> None:
        """测试排除所有时间戳字段."""
        verifier = ReplayVerifier()
        event = {
            "ts": "a",
            "timestamp": "b",
            "received_at": "c",
            "important": "d",
        }
        normalized = verifier._normalize_event(event)
        assert "ts" not in normalized
        assert "timestamp" not in normalized
        assert "received_at" not in normalized
        assert normalized["important"] == "d"


class TestReplayVerifierHash:
    """哈希计算测试."""

    def test_compute_hash_empty(self) -> None:
        """测试空列表哈希."""
        verifier = ReplayVerifier()
        h = verifier.compute_hash([])
        assert len(h) == 64  # SHA256 hex

    def test_compute_hash_deterministic(self) -> None:
        """测试哈希确定性."""
        verifier = ReplayVerifier()
        events = [{"type": "a", "value": 1}]
        h1 = verifier.compute_hash(events)
        h2 = verifier.compute_hash(events)
        assert h1 == h2

    def test_compute_hash_order_sensitive(self) -> None:
        """测试哈希顺序敏感."""
        verifier = ReplayVerifier()
        events_a = [{"type": "a"}, {"type": "b"}]
        events_b = [{"type": "b"}, {"type": "a"}]
        h1 = verifier.compute_hash(events_a)
        h2 = verifier.compute_hash(events_b)
        assert h1 != h2


class TestReplayVerifierSequence:
    """序列验证测试."""

    def test_verify_sequences_length_mismatch(self) -> None:
        """测试序列长度不匹配."""
        verifier = ReplayVerifier()
        events_a = [{"type": "a"}]
        events_b = [{"type": "a"}, {"type": "b"}]
        result = verifier._verify_sequences(events_a, events_b)
        assert result.is_match is False
        assert result.details.get("length_mismatch") is True

    def test_verify_sequences_find_mismatch(self) -> None:
        """测试找到不匹配位置."""
        verifier = ReplayVerifier()
        events_a = [{"type": "a"}, {"type": "b"}, {"type": "c"}]
        events_b = [{"type": "a"}, {"type": "x"}, {"type": "c"}]
        result = verifier._verify_sequences(events_a, events_b)
        assert result.is_match is False
        assert result.first_mismatch_index == 1


class TestReplayVerifierFileOps:
    """文件操作测试."""

    def test_load_events_from_jsonl_valid(self) -> None:
        """测试加载有效JSONL."""
        verifier = ReplayVerifier()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"type": "a"}\n')
            f.write('{"type": "b"}\n')
            f.write("\n")  # 空行
            f.write('{"type": "c"}\n')
            path = Path(f.name)

        events = verifier.load_events_from_jsonl(path)
        assert len(events) == 3
        path.unlink()

    def test_load_events_from_jsonl_invalid_json(self) -> None:
        """测试加载无效JSON."""
        verifier = ReplayVerifier()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"type": "a"}\n')
            f.write("invalid json\n")
            f.write('{"type": "b"}\n')
            path = Path(f.name)

        events = verifier.load_events_from_jsonl(path)
        assert len(events) == 2  # 跳过无效行
        path.unlink()

    def test_load_events_from_jsonl_not_exists(self) -> None:
        """测试加载不存在文件."""
        verifier = ReplayVerifier()
        events = verifier.load_events_from_jsonl(Path("/nonexistent/file.jsonl"))
        assert events == []

    def test_verify_files_decision(self) -> None:
        """测试验证决策文件."""
        verifier = ReplayVerifier()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f1, tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f2:
            f1.write('{"event_type": "decision", "value": 1}\n')
            f2.write('{"event_type": "decision", "value": 1}\n')
            path_a = Path(f1.name)
            path_b = Path(f2.name)

        result = verifier.verify_files(path_a, path_b, "decision")
        assert result.is_match is True
        path_a.unlink()
        path_b.unlink()

    def test_verify_files_guardian(self) -> None:
        """测试验证守护文件."""
        verifier = ReplayVerifier()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f1, tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f2:
            f1.write('{"event_type": "guardian", "mode": "normal"}\n')
            f2.write('{"event_type": "guardian", "mode": "normal"}\n')
            path_a = Path(f1.name)
            path_b = Path(f2.name)

        result = verifier.verify_files(path_a, path_b, "guardian")
        assert result.is_match is True
        path_a.unlink()
        path_b.unlink()

    def test_verify_files_all(self) -> None:
        """测试验证所有事件."""
        verifier = ReplayVerifier()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f1, tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f2:
            f1.write('{"type": "any", "value": 1}\n')
            f2.write('{"type": "any", "value": 1}\n')
            path_a = Path(f1.name)
            path_b = Path(f2.name)

        result = verifier.verify_files(path_a, path_b, "all")
        assert result.is_match is True
        path_a.unlink()
        path_b.unlink()


class TestVerifyReplayDeterminism:
    """回放确定性验证函数测试."""

    def test_verify_replay_determinism_both_match(self) -> None:
        """测试决策和守护都匹配."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f1, tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f2:
            content = (
                '{"event_type": "decision", "action": "buy"}\n'
                '{"event_type": "guardian", "mode": "normal"}\n'
            )
            f1.write(content)
            f2.write(content)
            path_orig = Path(f1.name)
            path_replay = Path(f2.name)

        decision_result, guardian_result = verify_replay_determinism(
            path_orig, path_replay
        )
        assert decision_result.is_match is True
        assert guardian_result.is_match is True
        path_orig.unlink()
        path_replay.unlink()

    def test_verify_replay_determinism_mismatch(self) -> None:
        """测试不匹配情况."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f1, tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f2:
            f1.write('{"event_type": "decision", "action": "buy"}\n')
            f2.write('{"event_type": "decision", "action": "sell"}\n')
            path_orig = Path(f1.name)
            path_replay = Path(f2.name)

        decision_result, guardian_result = verify_replay_determinism(
            path_orig, path_replay
        )
        assert decision_result.is_match is False
        path_orig.unlink()
        path_replay.unlink()
