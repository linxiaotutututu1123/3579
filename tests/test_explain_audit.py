"""Tests for explain/audit layer."""

from __future__ import annotations

from src.strategy.explain import ExplainResult, explain_portfolio_decision


class TestExplainResult:
    """Tests for ExplainResult dataclass."""

    def test_creation(self) -> None:
        """ExplainResult can be created with required fields."""
        result = ExplainResult(
            strategy_name="test",
            model_version="v1",
            features_hash="abc123",
        )
        assert result.strategy_name == "test"
        assert result.model_version == "v1"
        assert result.features_hash == "abc123"
        assert result.signal_scores == {}
        assert result.raw_inputs == {}
        assert result.decision_reason == ""

    def test_to_dict(self) -> None:
        """to_dict returns complete dictionary."""
        result = ExplainResult(
            strategy_name="linear_ai",
            model_version="v2",
            features_hash="def456",
            signal_scores={"AO": 0.5, "SA": -0.3},
            decision_reason="AO: LONG 1",
        )
        d = result.to_dict()
        assert d["strategy_name"] == "linear_ai"
        assert d["signal_scores"]["AO"] == 0.5
        assert d["decision_reason"] == "AO: LONG 1"

    def test_immutable(self) -> None:
        """ExplainResult is frozen/immutable."""
        result = ExplainResult(
            strategy_name="test",
            model_version="v1",
            features_hash="abc",
        )
        try:
            result.strategy_name = "changed"  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass  # Expected


class TestExplainPortfolioDecision:
    """Tests for explain_portfolio_decision function."""

    def test_long_position(self) -> None:
        """Explains long position correctly."""
        result = explain_portfolio_decision(
            strategy_name="linear_ai",
            model_version="v1",
            features_hash="abc",
            target_qty={"AO": 2},
            signal_scores={"AO": 0.8},
        )
        assert "LONG 2" in result.decision_reason
        assert result.signal_scores["AO"] == 0.8

    def test_short_position(self) -> None:
        """Explains short position correctly."""
        result = explain_portfolio_decision(
            strategy_name="ensemble_moe",
            model_version="v2",
            features_hash="def",
            target_qty={"SA": -1},
            signal_scores={"SA": -0.5},
        )
        assert "SHORT -1" in result.decision_reason
        assert result.signal_scores["SA"] == -0.5

    def test_flat_position(self) -> None:
        """Explains flat position correctly."""
        result = explain_portfolio_decision(
            strategy_name="dl_torch",
            model_version="v3",
            features_hash="ghi",
            target_qty={"LC": 0},
            signal_scores={"LC": 0.1},
        )
        assert "FLAT" in result.decision_reason

    def test_multiple_positions(self) -> None:
        """Handles multiple symbols."""
        result = explain_portfolio_decision(
            strategy_name="test",
            model_version="v1",
            features_hash="xyz",
            target_qty={"AO": 1, "SA": -1, "LC": 0},
            signal_scores={"AO": 0.5, "SA": -0.5, "LC": 0.0},
        )
        assert "AO" in result.decision_reason
        assert "SA" in result.decision_reason
        assert "LC" in result.decision_reason

    def test_no_signal_scores(self) -> None:
        """Works without signal scores."""
        result = explain_portfolio_decision(
            strategy_name="test",
            model_version="v1",
            features_hash="abc",
            target_qty={"AO": 1},
        )
        assert result.signal_scores == {}
        assert "score=0.0000" in result.decision_reason
