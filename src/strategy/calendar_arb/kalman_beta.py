"""Kalman Filter Beta Estimator for Calendar Arbitrage (Military-Grade v3.0).

Implements Kalman filter for dynamic beta estimation between near and far
month contracts as specified in V2 SPEC 9.2.

The Kalman filter estimates:
- Beta: hedge ratio between near and far contracts
- Residual: spread deviation from fair value
- Z-score: standardized residual for signal generation

Required Scenarios:
- ARB.KALMAN.BETA_ESTIMATE: Kalman filter estimates beta correctly
- ARB.KALMAN.RESIDUAL_ZSCORE: Computes residual z-score
- ARB.KALMAN.BETA_BOUND: Beta stays within bounds [min_beta, max_beta]

Mathematical Model:
    spread_t = near_t - beta_t * far_t + residual_t
    beta_t = beta_{t-1} + process_noise
    residual_t ~ N(0, measurement_variance)

Example:
    from src.strategy.calendar_arb.kalman_beta import KalmanBetaEstimator, KalmanConfig

    config = KalmanConfig(min_beta=0.5, max_beta=1.5)
    estimator = KalmanBetaEstimator(config)

    # Update with new prices
    result = estimator.update(near_price=4500.0, far_price=4400.0)
    print(f"Beta: {result.beta}, Z-score: {result.z_score}")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KalmanConfig:
    """Configuration for Kalman beta estimator.

    Attributes:
        initial_beta: Initial beta estimate (hedge ratio)
        initial_variance: Initial estimate variance
        process_variance: Process noise variance (beta drift)
        measurement_variance: Measurement noise variance
        min_beta: Minimum allowed beta (for BETA_BOUND scenario)
        max_beta: Maximum allowed beta (for BETA_BOUND scenario)
        z_score_window: Window size for z-score rolling calculation
        min_samples: Minimum samples before valid z-score
    """

    initial_beta: float = 1.0
    initial_variance: float = 1.0
    process_variance: float = 0.0001  # Small drift
    measurement_variance: float = 0.01
    min_beta: float = 0.5
    max_beta: float = 1.5
    z_score_window: int = 60
    min_samples: int = 20


@dataclass
class KalmanResult:
    """Result of Kalman filter update.

    Attributes:
        beta: Current beta estimate
        beta_variance: Variance of beta estimate
        residual: Current residual (spread - predicted_spread)
        z_score: Standardized residual
        half_life: Estimated half-life of mean reversion (in samples)
        is_valid: Whether estimates are valid (enough samples)
        beta_bounded: Whether beta was bounded to [min, max]
    """

    beta: float
    beta_variance: float
    residual: float
    z_score: float
    half_life: float
    is_valid: bool
    beta_bounded: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for audit."""
        return {
            "beta": self.beta,
            "beta_variance": self.beta_variance,
            "residual": self.residual,
            "z_score": self.z_score,
            "half_life": self.half_life,
            "is_valid": self.is_valid,
            "beta_bounded": self.beta_bounded,
        }


class KalmanBetaEstimator:
    """Kalman filter for dynamic beta estimation.

    Implements one-dimensional Kalman filter to estimate the hedge ratio
    (beta) between near and far month contracts in calendar spreads.

    Required Scenarios Coverage:
    - ARB.KALMAN.BETA_ESTIMATE: update() estimates beta
    - ARB.KALMAN.RESIDUAL_ZSCORE: get_z_score() computes standardized residual
    - ARB.KALMAN.BETA_BOUND: _bound_beta() enforces limits
    """

    def __init__(self, config: KalmanConfig | None = None) -> None:
        """Initialize Kalman beta estimator.

        Args:
            config: Kalman configuration (defaults to KalmanConfig())
        """
        self._config = config or KalmanConfig()

        # Kalman state
        self._beta = self._config.initial_beta
        self._variance = self._config.initial_variance

        # Rolling statistics for z-score
        self._residuals: list[float] = []
        self._residual_sum: float = 0.0
        self._residual_sq_sum: float = 0.0
        self._sample_count: int = 0

        # Half-life estimation
        self._prev_residual: float = 0.0
        self._autocorr_sum: float = 0.0
        self._autocorr_count: int = 0

    def reset(self) -> None:
        """Reset estimator to initial state."""
        self._beta = self._config.initial_beta
        self._variance = self._config.initial_variance
        self._residuals.clear()
        self._residual_sum = 0.0
        self._residual_sq_sum = 0.0
        self._sample_count = 0
        self._prev_residual = 0.0
        self._autocorr_sum = 0.0
        self._autocorr_count = 0

    def update(self, near_price: float, far_price: float) -> KalmanResult:
        """Update Kalman filter with new prices.

        Scenario: ARB.KALMAN.BETA_ESTIMATE

        Args:
            near_price: Near month contract price
            far_price: Far month contract price

        Returns:
            KalmanResult with updated estimates
        """
        # Protect against zero far price
        if far_price <= 0:
            return KalmanResult(
                beta=self._beta,
                beta_variance=self._variance,
                residual=0.0,
                z_score=0.0,
                half_life=float("inf"),
                is_valid=False,
            )

        # === Kalman Filter Predict Step ===
        # Beta follows random walk: beta_t = beta_{t-1} + noise
        predicted_beta = self._beta
        predicted_variance = self._variance + self._config.process_variance

        # === Kalman Filter Update Step ===
        # Observation: spread = near - beta * far
        # H = -far (observation matrix derivative w.r.t. beta)
        H = -far_price

        # Innovation (measurement residual)
        predicted_spread = near_price - predicted_beta * far_price
        observed_spread = near_price - self._beta * far_price  # Using current beta
        innovation = predicted_spread  # Simplification: we observe spread directly

        # Innovation variance
        S = H * H * predicted_variance + self._config.measurement_variance

        # Kalman gain
        K = predicted_variance * H / S if S > 0 else 0

        # Update beta estimate
        # The innovation is the residual from OLS regression perspective
        # For calendar spread, we estimate beta such that spread = alpha + noise
        # Simplified update: adjust beta to minimize spread variance
        regression_update = innovation / far_price if far_price != 0 else 0
        self._beta = predicted_beta - K * regression_update

        # Update variance
        self._variance = (1 - K * H) * predicted_variance

        # Bound beta (ARB.KALMAN.BETA_BOUND)
        beta_bounded = self._bound_beta()

        # Calculate residual (spread deviation from equilibrium)
        residual = near_price - self._beta * far_price

        # Update rolling statistics
        self._update_rolling_stats(residual)

        # Calculate z-score (ARB.KALMAN.RESIDUAL_ZSCORE)
        z_score = self._compute_z_score(residual)

        # Update half-life estimation
        half_life = self._update_half_life(residual)

        # Check validity
        is_valid = self._sample_count >= self._config.min_samples

        return KalmanResult(
            beta=self._beta,
            beta_variance=self._variance,
            residual=residual,
            z_score=z_score,
            half_life=half_life,
            is_valid=is_valid,
            beta_bounded=beta_bounded,
        )

    def _bound_beta(self) -> bool:
        """Bound beta to configured range.

        Scenario: ARB.KALMAN.BETA_BOUND

        Returns:
            True if beta was bounded, False otherwise
        """
        original_beta = self._beta
        self._beta = max(self._config.min_beta, min(self._config.max_beta, self._beta))
        return self._beta != original_beta

    def _update_rolling_stats(self, residual: float) -> None:
        """Update rolling statistics for z-score calculation."""
        self._residuals.append(residual)
        self._residual_sum += residual
        self._residual_sq_sum += residual * residual
        self._sample_count += 1

        # Trim to window size
        if len(self._residuals) > self._config.z_score_window:
            old = self._residuals.pop(0)
            self._residual_sum -= old
            self._residual_sq_sum -= old * old

    def _compute_z_score(self, residual: float) -> float:
        """Compute z-score of current residual.

        Scenario: ARB.KALMAN.RESIDUAL_ZSCORE

        Args:
            residual: Current residual

        Returns:
            Z-score (standardized residual)
        """
        n = len(self._residuals)
        if n < self._config.min_samples:
            return 0.0

        mean = self._residual_sum / n
        variance = (self._residual_sq_sum / n) - (mean * mean)

        if variance <= 0:
            return 0.0

        std = math.sqrt(variance)
        if std < 1e-10:
            return 0.0

        return (residual - mean) / std

    def _update_half_life(self, residual: float) -> float:
        """Estimate half-life of mean reversion using AR(1) autocorrelation.

        Half-life = -ln(2) / ln(rho), where rho is AR(1) coefficient.

        Args:
            residual: Current residual

        Returns:
            Estimated half-life in samples
        """
        if self._sample_count > 1:
            # Running autocorrelation estimate
            self._autocorr_sum += self._prev_residual * residual
            self._autocorr_count += 1

        self._prev_residual = residual

        if self._autocorr_count < self._config.min_samples:
            return float("inf")

        # Estimate AR(1) coefficient
        var_estimate = self._residual_sq_sum / len(self._residuals)
        if var_estimate <= 0:
            return float("inf")

        rho = self._autocorr_sum / (self._autocorr_count * var_estimate)

        # Bound rho to valid range
        rho = max(-0.999, min(0.999, rho))

        # Calculate half-life
        if rho <= 0:
            return float("inf")  # No mean reversion

        try:
            half_life = -math.log(2) / math.log(rho)
            return max(1.0, half_life)  # At least 1 sample
        except (ValueError, ZeroDivisionError):
            return float("inf")

    @property
    def beta(self) -> float:
        """Current beta estimate."""
        return self._beta

    @property
    def variance(self) -> float:
        """Current variance estimate."""
        return self._variance

    @property
    def sample_count(self) -> int:
        """Number of samples processed."""
        return self._sample_count

    def get_state(self) -> dict[str, Any]:
        """Get current estimator state for serialization."""
        return {
            "beta": self._beta,
            "variance": self._variance,
            "sample_count": self._sample_count,
            "residual_mean": self._residual_sum / len(self._residuals)
            if self._residuals
            else 0.0,
        }

    def set_state(self, state: dict[str, Any]) -> None:
        """Restore estimator state from serialization."""
        self._beta = state.get("beta", self._config.initial_beta)
        self._variance = state.get("variance", self._config.initial_variance)
