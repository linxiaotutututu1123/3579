"""Tiny MLP model for DL strategy."""

from __future__ import annotations

import torch
from torch import nn


class TinyMLP(nn.Module):
    """
    Simple MLP for trading signal generation.

    Architecture:
    - Input: feature_dim
    - Hidden: 32 units with ReLU
    - Hidden: 16 units with ReLU
    - Output: 1 (score)
    """

    def __init__(self, feature_dim: int = 180) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(feature_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Tanh(),  # Output in [-1, 1]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        result: torch.Tensor = self.net(x)
        return result
