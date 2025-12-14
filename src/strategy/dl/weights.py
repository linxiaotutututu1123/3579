"""Model loading and hashing utilities."""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from src.strategy.dl.model import TinyMLP

# Cache for loaded models
_model_cache: dict[str, tuple["TinyMLP", str]] = {}


def load_model_and_hash(model_path: str, feature_dim: int = 180) -> tuple["TinyMLP", str]:
    """
    Load model from path and compute hash of weights.

    Args:
        model_path: Path to state_dict file
        feature_dim: Feature dimension for model initialization

    Returns:
        (model, model_hash)
    """
    cache_key = f"{model_path}:{feature_dim}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    from src.strategy.dl.model import TinyMLP

    model = TinyMLP(feature_dim=feature_dim)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    # Compute hash of model weights
    model_hash = _compute_model_hash(model)

    _model_cache[cache_key] = (model, model_hash)
    return model, model_hash


def _compute_model_hash(model: "TinyMLP") -> str:
    """Compute SHA256 hash of model parameters."""
    hasher = hashlib.sha256()
    for param in model.parameters():
        hasher.update(param.data.cpu().numpy().tobytes())
    return hasher.hexdigest()


def clear_model_cache() -> None:
    """Clear the model cache."""
    _model_cache.clear()
