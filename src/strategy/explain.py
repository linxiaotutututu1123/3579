"""Explain/audit layer for strategy decisions.

Provides structured explanation of strategy outputs for debugging and audit trails.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExplainResult:
    """Structured explanation of a strategy decision."""

    strategy_name: str
    model_version: str
    features_hash: str
    signal_scores: dict[str, float] = field(default_factory=dict)
    raw_inputs: dict[str, Any] = field(default_factory=dict)
    decision_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "strategy_name": self.strategy_name,
            "model_version": self.model_version,
            "features_hash": self.features_hash,
            "signal_scores": dict(self.signal_scores),
            "raw_inputs": dict(self.raw_inputs),
            "decision_reason": self.decision_reason,
        }


def explain_portfolio_decision(
    strategy_name: str,
    model_version: str,
    features_hash: str,
    target_qty: dict[str, int],
    signal_scores: dict[str, float] | None = None,
) -> ExplainResult:
    """
    Generate an explanation for a portfolio decision.

    Args:
        strategy_name: Name of the strategy
        model_version: Version string of the model
        features_hash: Hash of the input features
        target_qty: Target quantities by symbol
        signal_scores: Optional signal scores by symbol

    Returns:
        ExplainResult with decision explanation
    """
    scores = signal_scores or {}

    # Build decision reason
    reasons = []
    for sym, qty in target_qty.items():
        score = scores.get(sym, 0.0)
        if qty > 0:
            reasons.append(f"{sym}: LONG {qty} (score={score:.4f})")
        elif qty < 0:
            reasons.append(f"{sym}: SHORT {qty} (score={score:.4f})")
        else:
            reasons.append(f"{sym}: FLAT (score={score:.4f})")

    decision_reason = "; ".join(reasons) if reasons else "No positions"

    return ExplainResult(
        strategy_name=strategy_name,
        model_version=model_version,
        features_hash=features_hash,
        signal_scores=scores,
        raw_inputs={"target_qty": target_qty},
        decision_reason=decision_reason,
    )
