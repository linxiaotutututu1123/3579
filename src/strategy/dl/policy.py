"""Inference policy for DL strategy."""
from __future__ import annotations

import numpy as np
import torch

from src.strategy.dl.model import TinyMLP


def infer_score(
    model: TinyMLP,
    features: np.ndarray,
    device: str = "cpu",
) -> float:
    """
    Run inference to get trading score.

    Args:
        model: The TinyMLP model
        features: Feature vector (numpy array)
        device: Device to run inference on

    Returns:
        Score in [-1, 1]
    """
    # Ensure determinism
    torch.set_num_threads(1)

    with torch.inference_mode():
        x = torch.from_numpy(features).float().to(device)
        if x.dim() == 1:
            x = x.unsqueeze(0)  # Add batch dimension

        output = model(x)
        score = float(output.squeeze().cpu().numpy())

    return score
