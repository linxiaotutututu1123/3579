"""
ReplayVerifier 测试.

V2 Scenarios:
- REPLAY.DETERMINISTIC.DECISION: 决策确定性
- REPLAY.DETERMINISTIC.GUARDIAN: Guardian 确定性
"""

from src.audit.replay_verifier import ReplayResult, ReplayVerifier


class TestReplayVerifier:
    """ReplayVerifier 测试类."""

    def test_replay_deterministic_decision_pass(self) -> None:
        """REPLAY.DETERMINISTIC.DECISION: 决策确定性 - 通过."""
        verifier = ReplayVerifier()

        original_decisions = [
            {
                "ts": 1.0,
                "event_type": "DECISION",
                "strategy_id": "simple_ai",
                "feature_hash": "abc12345",
                "target_portfolio": {"AO2501": 10},
            },
            {
                "ts": 2.0,
                "event_type": "DECISION",
                "strategy_id": "simple_ai",
                "feature_hash": "def67890",
                "target_portfolio": {"AO2501": 5},
            },
        ]

        replay_decisions = [
            {
                "ts": 1.5,  # 时间戳不同，应忽略
                "event_type": "DECISION",
                "strategy_id": "simple_ai",
                "feature_hash": "abc12345",
                "target_portfolio": {"AO2501": 10},
            },
            {
                "ts": 2.5,
                "event_type": "DECISION",
                "strategy_id": "simple_ai",
                "feature_hash": "def67890",
                "target_portfolio": {"AO2501": 5},
            },
        ]

        result = verifier.verify_decision_determinism(
            original_decisions, replay_decisions
        )

        assert result.is_deterministic is True
        assert result.output_hash_match is True
        assert len(result.mismatches) == 0

    def test_replay_deterministic_decision_fail(self) -> None:
        """REPLAY.DETERMINISTIC.DECISION: 决策确定性 - 失败."""
        verifier = ReplayVerifier()

        original_decisions = [
            {
                "ts": 1.0,
                "strategy_id": "simple_ai",
                "feature_hash": "abc12345",
                "target_portfolio": {"AO2501": 10},
            },
        ]

        replay_decisions = [
            {
                "ts": 1.0,
                "strategy_id": "simple_ai",
                "feature_hash": "abc12345",
                "target_portfolio": {"AO2501": 5},  # 不同！
            },
        ]

        result = verifier.verify_decision_determinism(
            original_decisions, replay_decisions
        )

        assert result.is_deterministic is False
        assert len(result.mismatches) > 0

    def test_replay_deterministic_guardian_pass(self) -> None:
        """REPLAY.DETERMINISTIC.GUARDIAN: Guardian 确定性 - 通过."""
        verifier = ReplayVerifier()

        original_events = [
            {
                "ts": 1.0,
                "event_type": "GUARDIAN",
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "INIT",
                "mode_to": "RUNNING",
                "trigger": "init_success",
            },
            {
                "ts": 2.0,
                "event_type": "GUARDIAN",
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "RUNNING",
                "mode_to": "REDUCE_ONLY",
                "trigger": "quote_stale",
            },
        ]

        replay_events = [
            {
                "ts": 1.5,  # 时间戳不同
                "event_type": "GUARDIAN",
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "INIT",
                "mode_to": "RUNNING",
                "trigger": "init_success",
            },
            {
                "ts": 2.5,
                "event_type": "GUARDIAN",
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "RUNNING",
                "mode_to": "REDUCE_ONLY",
                "trigger": "quote_stale",
            },
        ]

        result = verifier.verify_guardian_determinism(original_events, replay_events)

        assert result.is_deterministic is True
        assert result.output_hash_match is True
        assert len(result.mismatches) == 0

    def test_replay_deterministic_guardian_fail(self) -> None:
        """REPLAY.DETERMINISTIC.GUARDIAN: Guardian 确定性 - 失败."""
        verifier = ReplayVerifier()

        original_events = [
            {
                "ts": 1.0,
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "RUNNING",
                "mode_to": "REDUCE_ONLY",
                "trigger": "quote_stale",
            },
        ]

        replay_events = [
            {
                "ts": 1.0,
                "guardian_event_type": "MODE_CHANGE",
                "mode_from": "RUNNING",
                "mode_to": "HALTED",  # 不同！
                "trigger": "quote_stale",
            },
        ]

        result = verifier.verify_guardian_determinism(original_events, replay_events)

        assert result.is_deterministic is False
        assert len(result.mismatches) > 0

    def test_compute_hash_deterministic(self) -> None:
        """测试哈希计算确定性."""
        verifier = ReplayVerifier()

        data = {"key": "value", "number": 123, "nested": {"a": 1}}

        hash1 = verifier.compute_hash(data)
        hash2 = verifier.compute_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 16  # 16 位十六进制

    def test_compute_hash_order_independent(self) -> None:
        """测试哈希顺序无关."""
        verifier = ReplayVerifier()

        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}

        hash1 = verifier.compute_hash(data1)
        hash2 = verifier.compute_hash(data2)

        assert hash1 == hash2

    def test_compute_hash_different_data(self) -> None:
        """测试不同数据产生不同哈希."""
        verifier = ReplayVerifier()

        hash1 = verifier.compute_hash({"x": 1})
        hash2 = verifier.compute_hash({"x": 2})

        assert hash1 != hash2

    def test_compute_hash_string_input(self) -> None:
        """测试字符串输入."""
        verifier = ReplayVerifier()

        hash1 = verifier.compute_hash("test string")
        hash2 = verifier.compute_hash("test string")

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_compute_sequence_hash(self) -> None:
        """测试序列哈希计算."""
        verifier = ReplayVerifier()

        events = [
            {"event_type": "DECISION", "strategy_id": "s1", "target_portfolio": {}},
            {"event_type": "DECISION", "strategy_id": "s2", "target_portfolio": {}},
        ]

        hash1 = verifier.compute_sequence_hash(events)
        hash2 = verifier.compute_sequence_hash(events)

        assert hash1 == hash2

    def test_verify_determinism_basic(self) -> None:
        """测试基本确定性验证."""
        verifier = ReplayVerifier()

        original_inputs = [{"input": 1}]
        original_outputs = [{"event_type": "TEST", "value": 100}]
        replay_inputs = [{"input": 1}]
        replay_outputs = [{"event_type": "TEST", "value": 100}]

        result = verifier.verify_determinism(
            original_inputs, original_outputs, replay_inputs, replay_outputs
        )

        assert result.is_deterministic is True
        assert result.input_hash_match is True
        assert result.output_hash_match is True
        assert len(result.mismatches) == 0

    def test_verify_determinism_input_mismatch(self) -> None:
        """测试输入不匹配."""
        verifier = ReplayVerifier()

        original_inputs = [{"input": 1}]
        original_outputs = [{"event_type": "TEST", "value": 100}]
        replay_inputs = [{"input": 2}]  # 不同！
        replay_outputs = [{"event_type": "TEST", "value": 100}]

        result = verifier.verify_determinism(
            original_inputs, original_outputs, replay_inputs, replay_outputs
        )

        assert result.input_hash_match is False

    def test_verify_determinism_output_mismatch(self) -> None:
        """测试输出不匹配."""
        verifier = ReplayVerifier()

        original_inputs = [{"input": 1}]
        original_outputs = [{"event_type": "TEST", "value": 100}]
        replay_inputs = [{"input": 1}]
        replay_outputs = [{"event_type": "TEST", "value": 200}]  # 不同！

        result = verifier.verify_determinism(
            original_inputs, original_outputs, replay_inputs, replay_outputs
        )

        assert result.is_deterministic is False
        assert len(result.mismatches) > 0

    def test_verify_determinism_length_mismatch(self) -> None:
        """测试长度不匹配."""
        verifier = ReplayVerifier()

        original_inputs: list[dict] = []
        original_outputs = [
            {"event_type": "TEST", "value": 1},
            {"event_type": "TEST", "value": 2},
        ]
        replay_inputs: list[dict] = []
        replay_outputs = [{"event_type": "TEST", "value": 1}]  # 少一个

        result = verifier.verify_determinism(
            original_inputs, original_outputs, replay_inputs, replay_outputs
        )

        assert result.is_deterministic is False
        assert result.details["original_output_count"] == 2
        assert result.details["replay_output_count"] == 1
        assert 1 in result.mismatches  # 索引 1 不匹配

    def test_events_match_ignore_timestamp(self) -> None:
        """测试事件匹配忽略时间戳."""
        verifier = ReplayVerifier()

        e1 = {"ts": 1.0, "event_type": "TEST", "value": 100}
        e2 = {"ts": 2.0, "event_type": "TEST", "value": 100}  # ts 不同

        assert verifier._events_match(e1, e2) is True

    def test_events_match_different_values(self) -> None:
        """测试事件不匹配."""
        verifier = ReplayVerifier()

        e1 = {"ts": 1.0, "event_type": "TEST", "value": 100}
        e2 = {"ts": 1.0, "event_type": "TEST", "value": 200}  # value 不同

        assert verifier._events_match(e1, e2) is False

    def test_replay_result_dataclass(self) -> None:
        """测试 ReplayResult 数据类."""
        result = ReplayResult(
            is_deterministic=True,
            input_hash_match=True,
            output_hash_match=True,
            original_input_hash="abc12345",
            replay_input_hash="abc12345",
            original_output_hash="def67890",
            replay_output_hash="def67890",
            mismatches=[],
            details={"test": "value"},
        )

        assert result.is_deterministic is True
        assert result.original_input_hash == "abc12345"
        assert result.mismatches == []
        assert result.details["test"] == "value"

    def test_empty_sequence(self) -> None:
        """测试空序列."""
        verifier = ReplayVerifier()

        result = verifier.verify_determinism(
            original_inputs=[],
            original_outputs=[],
            replay_inputs=[],
            replay_outputs=[],
        )

        assert result.is_deterministic is True
        assert result.input_hash_match is True
        assert result.output_hash_match is True
        assert len(result.mismatches) == 0

    def test_decision_determinism_empty(self) -> None:
        """测试空决策序列."""
        verifier = ReplayVerifier()

        result = verifier.verify_decision_determinism([], [])

        assert result.is_deterministic is True

    def test_guardian_determinism_empty(self) -> None:
        """测试空 Guardian 事件序列."""
        verifier = ReplayVerifier()

        result = verifier.verify_guardian_determinism([], [])

        assert result.is_deterministic is True

    def test_guardian_action_field(self) -> None:
        """测试 Guardian action 字段验证."""
        verifier = ReplayVerifier()

        original = [
            {
                "guardian_event_type": "ACTION_EXECUTED",
                "action": "cancel_all",
            }
        ]
        replay = [
            {
                "guardian_event_type": "ACTION_EXECUTED",
                "action": "cancel_all",
            }
        ]

        result = verifier.verify_guardian_determinism(original, replay)
        assert result.is_deterministic is True

        # 不同 action
        replay_different = [
            {
                "guardian_event_type": "ACTION_EXECUTED",
                "action": "flatten_all",
            }
        ]

        result2 = verifier.verify_guardian_determinism(original, replay_different)
        assert result2.is_deterministic is False
