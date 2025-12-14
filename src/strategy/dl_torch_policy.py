"""Deep learning torch-based trading strategy (inference only)."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Sequence

import torch

from src.strategy.base import Strategy
from src.strategy.dl.features import build_features, get_feature_dim
from src.strategy.dl.policy import infer_score
from src.strategy.dl.weights import load_model_and_hash
from src.strategy.types import MarketState, TargetPortfolio
from src.trading.utils import stable_hash


# Default model path (relative to repo root)
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "dl", "assets", "dl_torch_v1_state_dict.pt"
)


class DlTorchPolicyStrategy(Strategy):
    """
    Deep learning strategy using PyTorch for inference.

    Features:
    - Inference only (no training)
    - CPU-compatible
    - Deterministic (fixed random seed, single thread)
    - Model hash included in features_hash for auditability
    """

    def __init__(
        self,
        symbols: Sequence[str],
        model_path: str | None = None,
        device: str = "cpu",
        window: int = 60,
        max_abs_qty_per_symbol: int = 2,
    ) -> None:
        self._symbols = list(symbols)
        self._model_path = model_path or DEFAULT_MODEL_PATH
        self._device = device
        self._window = window
        self._max_abs_qty = max_abs_qty_per_symbol

        # Ensure determinism
        torch.set_num_threads(1)
        with contextlib.suppress(Exception):
            torch.use_deterministic_algorithms(True)

        # Load model
        feature_dim = get_feature_dim(window)
        self._model, self._model_hash = load_model_and_hash(
            self._model_path, feature_dim=feature_dim
        )
        self._model.to(self._device)
        self._model.eval()

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        all_features: dict[str, object] = {
            "model_hash": self._model_hash,
            "params": {
                "window": self._window,
                "max_abs_qty": self._max_abs_qty,
                "device": self._device,
            },
            "symbols": self._symbols,
        }
        target_net_qty: dict[str, int] = {}

        for sym in self._symbols:
            bars = state.bars_1m.get(sym, [])
            features = build_features(bars, window=self._window)

            # Compute feature summary for audit (not full features)
            feature_summary = {
                "mean": float(features.mean()),
                "std": float(features.std()),
                "min": float(features.min()),
                "max": float(features.max()),
            }
            all_features[f"{sym}_feature_summary"] = feature_summary

            if len(bars) < self._window:
                all_features[f"{sym}_insufficient"] = True
                target_net_qty[sym] = 0
                continue

            # Run inference
            score = infer_score(self._model, features, device=self._device)

            # Score is already in [-1, 1] due to tanh
            qty = int(round(score * self._max_abs_qty))
            qty = max(-self._max_abs_qty, min(self._max_abs_qty, qty))
            target_net_qty[sym] = qty

            all_features[f"{sym}_score"] = score

        features_hash = stable_hash(all_features)

        return TargetPortfolio(
            target_net_qty=target_net_qty,
            model_version=f"dl-torch-v1:{self._model_hash[:8]}",
            features_hash=features_hash,
        )
