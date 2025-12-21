"""VaR 风险价值计算器 (军规级 v3.0).

提供风险价值 (VaR) 计算功能。

功能特性:
- 历史模拟法 VaR
- 参数法 VaR
- 蒙特卡洛模拟 VaR
- 预期尾部损失 (CVaR/ES)

示例:
    calculator = VaRCalculator()
    var_95 = calculator.historical_var(returns, confidence=0.95)
    cvar = calculator.expected_shortfall(returns, confidence=0.95)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class VaRResult:
    """VaR calculation result.

    Attributes:
        var: Value at Risk
        confidence: Confidence level
        method: Calculation method
        expected_shortfall: Expected shortfall (CVaR)
        sample_size: Number of samples used
        metadata: Additional metadata
    """

    var: float
    confidence: float
    method: str
    expected_shortfall: float = 0.0
    sample_size: int = 0
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "var": self.var,
            "confidence": self.confidence,
            "method": self.method,
            "expected_shortfall": self.expected_shortfall,
            "sample_size": self.sample_size,
            "metadata": self.metadata or {},
        }


class VaRCalculator:
    """Value at Risk calculator.

    Provides multiple methods for VaR calculation including
    historical, parametric, and Monte Carlo approaches.
    """

    def __init__(self, default_confidence: float = 0.95) -> None:
        """Initialize VaR calculator.

        Args:
            default_confidence: Default confidence level (0.95 = 95%)
        """
        self._default_confidence = default_confidence

    def historical_var(self, returns: list[float], confidence: float | None = None) -> VaRResult:
        """Calculate historical VaR.

        Uses empirical distribution of returns to estimate VaR.

        Args:
            returns: List of historical returns
            confidence: Confidence level (default: 0.95)

        Returns:
            VaR result
        """
        confidence = confidence or self._default_confidence

        if len(returns) < 2:
            return VaRResult(
                var=0.0,
                confidence=confidence,
                method="historical",
                sample_size=len(returns),
            )

        # Sort returns
        sorted_returns = sorted(returns)
        n = len(sorted_returns)

        # Find percentile index
        index = int((1 - confidence) * n)
        index = max(0, min(index, n - 1))

        var = -sorted_returns[index]  # VaR is typically positive

        # Calculate expected shortfall
        es = self._calculate_expected_shortfall(sorted_returns, index)

        return VaRResult(
            var=var,
            confidence=confidence,
            method="historical",
            expected_shortfall=es,
            sample_size=n,
        )

    def parametric_var(self, returns: list[float], confidence: float | None = None) -> VaRResult:
        """Calculate parametric (variance-covariance) VaR.

        Assumes normal distribution of returns.

        Args:
            returns: List of historical returns
            confidence: Confidence level (default: 0.95)

        Returns:
            VaR result
        """
        confidence = confidence or self._default_confidence

        if len(returns) < 2:
            return VaRResult(
                var=0.0,
                confidence=confidence,
                method="parametric",
                sample_size=len(returns),
            )

        # Calculate mean and std
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0

        # Z-score for confidence level
        z = self._norm_ppf(confidence)

        # VaR = -mean + z * std
        var = -mean + z * std

        # Expected shortfall for normal distribution
        # ES = mean + std * phi(z) / (1 - confidence)
        pdf_z = self._norm_pdf(z)
        es = -mean + std * pdf_z / (1 - confidence) if confidence < 1 else var

        return VaRResult(
            var=var,
            confidence=confidence,
            method="parametric",
            expected_shortfall=es,
            sample_size=len(returns),
            metadata={"mean": mean, "std": std, "z_score": z},
        )

    def monte_carlo_var(
        self,
        returns: list[float],
        confidence: float | None = None,
        simulations: int = 10000,
        horizon: int = 1,
    ) -> VaRResult:
        """Calculate Monte Carlo VaR.

        Simulates future returns based on historical distribution.

        Args:
            returns: List of historical returns
            confidence: Confidence level (default: 0.95)
            simulations: Number of simulations
            horizon: Time horizon (days)

        Returns:
            VaR result
        """
        confidence = confidence or self._default_confidence

        if len(returns) < 2:
            return VaRResult(
                var=0.0,
                confidence=confidence,
                method="monte_carlo",
                sample_size=len(returns),
            )

        # Calculate mean and std
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0

        # Scale for horizon
        mean_horizon = mean * horizon
        std_horizon = std * math.sqrt(horizon)

        # Simulate returns (using Box-Muller for normal random numbers)
        simulated_returns: list[float] = []
        for _ in range(simulations // 2 + 1):
            u1, u2 = self._random_uniform(), self._random_uniform()
            if u1 > 0 and u2 > 0:
                z1 = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
                z2 = math.sqrt(-2 * math.log(u1)) * math.sin(2 * math.pi * u2)
                simulated_returns.append(mean_horizon + std_horizon * z1)
                if len(simulated_returns) < simulations:
                    simulated_returns.append(mean_horizon + std_horizon * z2)

        # Truncate to exact number
        simulated_returns = simulated_returns[:simulations]

        # Sort and find VaR
        sorted_returns = sorted(simulated_returns)
        index = int((1 - confidence) * len(sorted_returns))
        index = max(0, min(index, len(sorted_returns) - 1))

        var = -sorted_returns[index]
        es = self._calculate_expected_shortfall(sorted_returns, index)

        return VaRResult(
            var=var,
            confidence=confidence,
            method="monte_carlo",
            expected_shortfall=es,
            sample_size=len(returns),
            metadata={"simulations": simulations, "horizon": horizon},
        )

    def expected_shortfall(self, returns: list[float], confidence: float | None = None) -> float:
        """Calculate Expected Shortfall (CVaR).

        Average of losses beyond VaR.

        Args:
            returns: List of historical returns
            confidence: Confidence level (default: 0.95)

        Returns:
            Expected shortfall value
        """
        result = self.historical_var(returns, confidence)
        return result.expected_shortfall

    def _calculate_expected_shortfall(self, sorted_returns: list[float], var_index: int) -> float:
        """Calculate expected shortfall from sorted returns.

        Args:
            sorted_returns: Sorted list of returns
            var_index: Index of VaR in sorted list

        Returns:
            Expected shortfall
        """
        if var_index <= 0:
            return -sorted_returns[0] if sorted_returns else 0.0

        # Average of returns below VaR
        tail_returns = sorted_returns[:var_index]
        if not tail_returns:
            return 0.0

        return -sum(tail_returns) / len(tail_returns)

    def _norm_ppf(self, p: float) -> float:
        """Normal distribution percent point function (inverse CDF).

        Approximate using rational approximation.

        Args:
            p: Probability (0-1)

        Returns:
            Z-score
        """
        if p <= 0:
            return float("-inf")
        if p >= 1:
            return float("inf")
        if p == 0.5:
            return 0.0

        # Approximation constants
        a = [
            -3.969683028665376e01,
            2.209460984245205e02,
            -2.759285104469687e02,
            1.383577518672690e02,
            -3.066479806614716e01,
            2.506628277459239e00,
        ]
        b = [
            -5.447609879822406e01,
            1.615858368580409e02,
            -1.556989798598866e02,
            6.680131188771972e01,
            -1.328068155288572e01,
        ]
        c = [
            -7.784894002430293e-03,
            -3.223964580411365e-01,
            -2.400758277161838e00,
            -2.549732539343734e00,
            4.374664141464968e00,
            2.938163982698783e00,
        ]
        d = [
            7.784695709041462e-03,
            3.224671290700398e-01,
            2.445134137142996e00,
            3.754408661907416e00,
        ]

        p_low = 0.02425
        p_high = 1 - p_low

        if p < p_low:
            q = math.sqrt(-2 * math.log(p))
            return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
                (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
            )
        if p <= p_high:
            q = p - 0.5
            r = q * q
            return (
                (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
                * q
                / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
            )
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )

    def _norm_pdf(self, x: float) -> float:
        """Normal distribution probability density function.

        Args:
            x: Value

        Returns:
            PDF value
        """
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

    def _random_uniform(self) -> float:
        """Generate pseudo-random uniform number.

        Simple LCG for reproducibility (not cryptographically secure).

        Returns:
            Random number in (0, 1)
        """
        import time

        # Use time-based seed
        seed = int(time.time() * 1000000) % (2**31)
        # LCG parameters
        seed = (1103515245 * seed + 12345) % (2**31)
        return (seed / (2**31 - 1)) * 0.9998 + 0.0001  # Avoid exact 0 or 1
