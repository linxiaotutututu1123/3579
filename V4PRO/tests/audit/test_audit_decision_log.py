"""
DecisionLog 测试.

V2 Scenarios:
- STRAT.AUDIT.DECISION_EVENT_PRESENT: DecisionEvent 存在
- STRAT.AUDIT.DECISION_HAS_RUN_ID: 包含 run_id
- STRAT.AUDIT.DECISION_HAS_EXEC_ID: 包含 exec_id
- STRAT.AUDIT.DECISION_HAS_STRATEGY_ID: 包含 strategy_id
- STRAT.AUDIT.DECISION_HAS_VERSION: 包含 version
- STRAT.AUDIT.DECISION_HAS_FEATURE_HASH: 包含 feature_hash
"""

from src.audit.decision_log import (
    DecisionEvent,
    compute_feature_hash,
    validate_decision_event,
)


class TestDecisionEvent:
    """DecisionEvent 测试类."""

    def test_strat_audit_decision_event_present(self) -> None:
        """STRAT.AUDIT.DECISION_EVENT_PRESENT: DecisionEvent 存在."""
        event = DecisionEvent(
            ts=1234567890.123,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="abc12345",
            target_portfolio={"AO2501": 10},
        )

        data = event.to_dict()

        assert data["event_type"] == "DECISION"
        assert data["ts"] == 1234567890.123

    def test_strat_audit_decision_has_run_id(self) -> None:
        """STRAT.AUDIT.DECISION_HAS_RUN_ID: 包含 run_id."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-test-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="abc12345",
            target_portfolio={},
        )

        data = event.to_dict()
        assert data["run_id"] == "run-test-001"

        errors = validate_decision_event(event)
        assert not any("run_id" in e for e in errors)

    def test_strat_audit_decision_has_exec_id(self) -> None:
        """STRAT.AUDIT.DECISION_HAS_EXEC_ID: 包含 exec_id."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-test-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="abc12345",
            target_portfolio={},
        )

        data = event.to_dict()
        assert data["exec_id"] == "exec-test-001"

        errors = validate_decision_event(event)
        assert not any("exec_id" in e for e in errors)

    def test_strat_audit_decision_has_strategy_id(self) -> None:
        """STRAT.AUDIT.DECISION_HAS_STRATEGY_ID: 包含 strategy_id."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="linear_ai",
            strategy_version="1.0.0",
            feature_hash="abc12345",
            target_portfolio={},
        )

        data = event.to_dict()
        assert data["strategy_id"] == "linear_ai"

        errors = validate_decision_event(event)
        assert not any("strategy_id" in e for e in errors)

    def test_strat_audit_decision_has_version(self) -> None:
        """STRAT.AUDIT.DECISION_HAS_VERSION: 包含 version."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="2.1.0",
            feature_hash="abc12345",
            target_portfolio={},
        )

        data = event.to_dict()
        assert data["strategy_version"] == "2.1.0"

        errors = validate_decision_event(event)
        assert not any("strategy_version" in e for e in errors)

    def test_strat_audit_decision_has_feature_hash(self) -> None:
        """STRAT.AUDIT.DECISION_HAS_FEATURE_HASH: 包含 feature_hash."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="0123456789abcdef",
            target_portfolio={},
        )

        data = event.to_dict()
        assert data["feature_hash"] == "0123456789abcdef"

        errors = validate_decision_event(event)
        assert not any("feature_hash" in e for e in errors)

    def test_validate_decision_event_all_valid(self) -> None:
        """测试验证完整事件."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="abc12345",
            target_portfolio={"AO2501": 10},
        )

        errors = validate_decision_event(event)
        assert len(errors) == 0

    def test_validate_decision_event_missing_fields(self) -> None:
        """测试验证缺失字段."""
        event = DecisionEvent(
            ts=1.0,
            run_id="",
            exec_id="",
            strategy_id="",
            strategy_version="",
            feature_hash="",
            target_portfolio={},
        )

        errors = validate_decision_event(event)
        assert len(errors) == 5  # 5 个必填字段

    def test_compute_feature_hash_deterministic(self) -> None:
        """测试特征哈希确定性."""
        features = {"price": 100.5, "volume": 1000, "symbol": "AO2501"}

        hash1 = compute_feature_hash(features)
        hash2 = compute_feature_hash(features)

        assert hash1 == hash2
        assert len(hash1) == 16  # 16 位十六进制

    def test_compute_feature_hash_order_independent(self) -> None:
        """测试特征哈希顺序无关."""
        features1 = {"a": 1, "b": 2, "c": 3}
        features2 = {"c": 3, "a": 1, "b": 2}

        hash1 = compute_feature_hash(features1)
        hash2 = compute_feature_hash(features2)

        assert hash1 == hash2

    def test_compute_feature_hash_different_values(self) -> None:
        """测试不同值产生不同哈希."""
        hash1 = compute_feature_hash({"x": 1})
        hash2 = compute_feature_hash({"x": 2})

        assert hash1 != hash2

    def test_decision_event_create_factory(self) -> None:
        """测试工厂方法创建事件."""
        features = {"price": 100.5, "volume": 1000}

        event = DecisionEvent.create(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            features=features,
            target_portfolio={"AO2501": 10},
            confidence=0.85,
            signals={"momentum": 0.5},
            metadata={"source": "test"},
        )

        assert event.feature_hash == compute_feature_hash(features)
        assert event.confidence == 0.85
        assert event.signals == {"momentum": 0.5}
        assert event.metadata == {"source": "test"}

    def test_decision_event_create_defaults(self) -> None:
        """测试工厂方法默认值."""
        event = DecisionEvent.create(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            features={},
            target_portfolio={},
        )

        assert event.confidence is None
        assert event.signals == {}
        assert event.metadata == {}

    def test_decision_event_type_property(self) -> None:
        """测试事件类型属性."""
        event = DecisionEvent(
            ts=1.0,
            run_id="run-001",
            exec_id="exec-001",
            strategy_id="simple_ai",
            strategy_version="1.0.0",
            feature_hash="abc",
            target_portfolio={},
        )

        assert event.event_type == "DECISION"
