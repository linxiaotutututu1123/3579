"""Calendar Arbitrage Strategy (Military-Grade v3.0).

Implements calendar spread arbitrage strategy as specified in V2 SPEC Chapter 9.
Trades the spread between near and far month contracts using Kalman filter
for dynamic beta estimation and z-score based signal generation.

Required Scenarios:
- ARB.LEGS.FIXED_NEAR_FAR: Near/far leg contracts are fixed per product
- ARB.SIGNAL.HALF_LIFE_GATE: Half-life filter prevents non-mean-reverting trades
- ARB.SIGNAL.STOP_Z_BREAKER: Stop-loss on extreme z-score
- ARB.SIGNAL.EXPIRY_GATE: Near-expiry blocks new positions
- ARB.SIGNAL.CORRELATION_BREAK: Correlation collapse pauses strategy
- ARB.COST.ENTRY_GATE: Entry cost threshold check

Signal Logic (from V3PRO_UPGRADE_PLAN 8.5):
    z > entry_z (e.g. 2.5)  -> Spread too wide  -> Sell near, Buy far
    z < -entry_z            -> Spread too narrow -> Buy near, Sell far
    abs(z) < exit_z (e.g. 0.5) -> Mean reversion -> Close positions
    abs(z) > stop_z (e.g. 5-6)  -> Abnormal     -> Stop-loss + Cooldown

Example:
    from src.strategy.calendar_arb import CalendarArbStrategy, ArbConfig

    config = ArbConfig(entry_z=2.5, exit_z=0.5, stop_z=5.0)
    strategy = CalendarArbStrategy(config, product="AO")

    # On each tick
    portfolio = strategy.on_tick(market_state)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.strategy.base import Strategy
from src.strategy.calendar_arb.kalman_beta import (
    KalmanBetaEstimator,
    KalmanConfig,
    KalmanResult,
)
from src.strategy.types import MarketState, TargetPortfolio


class ArbSignal(Enum):
    """Arbitrage signal type."""

    FLAT = 0  # No position / Close position
    LONG_SPREAD = 1  # Buy near, Sell far (expect spread to widen)
    SHORT_SPREAD = -1  # Sell near, Buy far (expect spread to narrow)


class ArbState(Enum):
    """Arbitrage strategy state."""

    INIT = "init"  # Initializing, not trading
    ACTIVE = "active"  # Normal trading
    REDUCE_ONLY = "reduce_only"  # Only reducing positions
    STOPPED = "stopped"  # Stop-loss triggered, in cooldown
    PAUSED = "paused"  # Paused (correlation break, etc.)


@dataclass
class ArbConfig:
    """Configuration for calendar arbitrage strategy.

    Attributes:
        entry_z: Z-score threshold for entry (e.g., 2.5)
        exit_z: Z-score threshold for exit (e.g., 0.5)
        stop_z: Z-score threshold for stop-loss (e.g., 5.0)
        max_half_life_days: Maximum half-life for mean reversion (days)
        min_correlation: Minimum rolling correlation threshold
        correlation_window: Window for correlation calculation
        expiry_block_days: Days before expiry to block new positions
        cooldown_after_stop_s: Cooldown period after stop-loss (seconds)
        min_edge_bps: Minimum edge in basis points for entry
        max_position_per_leg: Maximum position per leg
        kalman_config: Kalman filter configuration
    """

    entry_z: float = 2.5
    exit_z: float = 0.5
    stop_z: float = 5.0
    max_half_life_days: int = 20
    min_correlation: float = 0.7
    correlation_window: int = 60
    expiry_block_days: int = 5
    cooldown_after_stop_s: float = 600.0
    min_edge_bps: float = 5.0  # 5 basis points minimum edge
    max_position_per_leg: int = 10
    kalman_config: KalmanConfig = field(default_factory=KalmanConfig)


@dataclass
class LegPair:
    """Near/far leg pair definition.

    Scenario: ARB.LEGS.FIXED_NEAR_FAR
    """

    product: str  # Product code (e.g., "AO")
    near_symbol: str  # Near month contract (e.g., "AO2501")
    far_symbol: str  # Far month contract (e.g., "AO2505")
    near_expiry: str  # Near month expiry date (YYYYMMDD)
    far_expiry: str  # Far month expiry date (YYYYMMDD)


@dataclass
class ArbSnapshot:
    """Snapshot of arbitrage state for audit."""

    ts: float
    state: ArbState
    signal: ArbSignal
    near_price: float
    far_price: float
    beta: float
    residual: float
    z_score: float
    half_life: float
    correlation: float
    position_near: int
    position_far: int
    stop_triggered: bool
    expiry_blocked: bool
    correlation_blocked: bool
    half_life_blocked: bool
    cost_blocked: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for audit."""
        return {
            "ts": self.ts,
            "state": self.state.value,
            "signal": self.signal.value,
            "near_price": self.near_price,
            "far_price": self.far_price,
            "beta": self.beta,
            "residual": self.residual,
            "z_score": self.z_score,
            "half_life": self.half_life,
            "correlation": self.correlation,
            "position_near": self.position_near,
            "position_far": self.position_far,
            "stop_triggered": self.stop_triggered,
            "expiry_blocked": self.expiry_blocked,
            "correlation_blocked": self.correlation_blocked,
            "half_life_blocked": self.half_life_blocked,
            "cost_blocked": self.cost_blocked,
        }


class CalendarArbStrategy(Strategy):
    """Calendar spread arbitrage strategy.

    Implements Kalman-filter based calendar spread trading between
    near and far month contracts of the same product.

    Required Scenarios Coverage:
    - ARB.LEGS.FIXED_NEAR_FAR: set_leg_pair() fixes near/far legs
    - ARB.SIGNAL.HALF_LIFE_GATE: _check_half_life_gate() filters
    - ARB.SIGNAL.STOP_Z_BREAKER: _check_stop_z() triggers stop-loss
    - ARB.SIGNAL.EXPIRY_GATE: _check_expiry_gate() blocks near-expiry
    - ARB.SIGNAL.CORRELATION_BREAK: _check_correlation() pauses
    - ARB.COST.ENTRY_GATE: _check_cost_gate() checks entry cost
    """

    VERSION = "3.0.0"

    def __init__(
        self,
        config: ArbConfig | None = None,
        product: str = "AO",
    ) -> None:
        """Initialize calendar arbitrage strategy.

        Args:
            config: Strategy configuration
            product: Product code for this strategy instance
        """
        self._config = config or ArbConfig()
        self._product = product

        # Leg pair (ARB.LEGS.FIXED_NEAR_FAR)
        self._leg_pair: LegPair | None = None

        # Kalman estimator
        self._kalman = KalmanBetaEstimator(self._config.kalman_config)

        # Strategy state
        self._state = ArbState.INIT
        self._signal = ArbSignal.FLAT

        # Position tracking
        self._position_near: int = 0
        self._position_far: int = 0

        # Correlation tracking
        self._near_prices: list[float] = []
        self._far_prices: list[float] = []

        # Stop-loss state
        self._stop_triggered_at: float | None = None

        # Latest snapshot for audit
        self._last_snapshot: ArbSnapshot | None = None

    def set_leg_pair(
        self,
        near_symbol: str,
        far_symbol: str,
        near_expiry: str,
        far_expiry: str,
    ) -> None:
        """Set the near/far leg pair.

        Scenario: ARB.LEGS.FIXED_NEAR_FAR

        Args:
            near_symbol: Near month contract symbol
            far_symbol: Far month contract symbol
            near_expiry: Near month expiry (YYYYMMDD)
            far_expiry: Far month expiry (YYYYMMDD)
        """
        self._leg_pair = LegPair(
            product=self._product,
            near_symbol=near_symbol,
            far_symbol=far_symbol,
            near_expiry=near_expiry,
            far_expiry=far_expiry,
        )
        self._state = ArbState.ACTIVE
        self._kalman.reset()

    def on_tick(self, state: MarketState) -> TargetPortfolio:
        """Process market tick and generate target portfolio.

        Args:
            state: Current market state

        Returns:
            Target portfolio with positions
        """
        # Not configured
        if self._leg_pair is None:
            return self._make_flat_portfolio(state)

        near_symbol = self._leg_pair.near_symbol
        far_symbol = self._leg_pair.far_symbol

        # Get prices
        near_price = state.prices.get(near_symbol, 0.0)
        far_price = state.prices.get(far_symbol, 0.0)

        # Invalid prices
        if near_price <= 0 or far_price <= 0:
            return self._make_flat_portfolio(state)

        # Update Kalman filter
        kalman_result = self._kalman.update(near_price, far_price)

        # Update correlation tracking
        self._update_correlation_tracking(near_price, far_price)
        correlation = self._compute_correlation()

        # Check gates and compute signal
        snapshot = self._process_signal(
            near_price=near_price,
            far_price=far_price,
            kalman_result=kalman_result,
            correlation=correlation,
        )
        self._last_snapshot = snapshot

        # Generate target portfolio
        target_near = self._compute_target_near(snapshot)
        target_far = self._compute_target_far(snapshot, kalman_result.beta)

        # Build portfolio
        target_qty: dict[str, int] = {}
        if target_near != 0:
            target_qty[near_symbol] = target_near
        if target_far != 0:
            target_qty[far_symbol] = target_far

        return TargetPortfolio(
            target_net_qty=target_qty,
            model_version=self.VERSION,
            features_hash=self._compute_features_hash(snapshot),
        )

    def _process_signal(
        self,
        near_price: float,
        far_price: float,
        kalman_result: KalmanResult,
        correlation: float,
    ) -> ArbSnapshot:
        """Process signal with all gates.

        Args:
            near_price: Near month price
            far_price: Far month price
            kalman_result: Kalman filter result
            correlation: Rolling correlation

        Returns:
            ArbSnapshot with signal and gate status
        """
        now = time.time()

        # Initialize gate flags
        stop_triggered = False
        expiry_blocked = False
        correlation_blocked = False
        half_life_blocked = False
        cost_blocked = False

        z_score = kalman_result.z_score
        half_life = kalman_result.half_life

        # === Check Stop-Loss (ARB.SIGNAL.STOP_Z_BREAKER) ===
        if self._check_stop_z(z_score):
            stop_triggered = True
            self._stop_triggered_at = now
            self._state = ArbState.STOPPED
            self._signal = ArbSignal.FLAT

        # === Check Cooldown ===
        if self._state == ArbState.STOPPED:
            if self._check_cooldown_expired(now):
                self._state = ArbState.ACTIVE
                self._stop_triggered_at = None
            else:
                # Still in cooldown
                return ArbSnapshot(
                    ts=now,
                    state=self._state,
                    signal=ArbSignal.FLAT,
                    near_price=near_price,
                    far_price=far_price,
                    beta=kalman_result.beta,
                    residual=kalman_result.residual,
                    z_score=z_score,
                    half_life=half_life,
                    correlation=correlation,
                    position_near=self._position_near,
                    position_far=self._position_far,
                    stop_triggered=True,
                    expiry_blocked=False,
                    correlation_blocked=False,
                    half_life_blocked=False,
                    cost_blocked=False,
                )

        # === Check Expiry Gate (ARB.SIGNAL.EXPIRY_GATE) ===
        if self._check_expiry_gate():
            expiry_blocked = True
            if self._state == ArbState.ACTIVE:
                self._state = ArbState.REDUCE_ONLY

        # === Check Correlation Break (ARB.SIGNAL.CORRELATION_BREAK) ===
        if self._check_correlation_break(correlation):
            correlation_blocked = True
            self._state = ArbState.PAUSED
            self._signal = ArbSignal.FLAT

        # === Check Half-Life Gate (ARB.SIGNAL.HALF_LIFE_GATE) ===
        if self._check_half_life_gate(half_life):
            half_life_blocked = True

        # === Check Cost Gate (ARB.COST.ENTRY_GATE) ===
        if self._check_cost_gate(z_score, near_price, far_price):
            cost_blocked = True

        # === Generate Signal ===
        if self._state == ArbState.ACTIVE:
            self._signal = self._generate_signal(
                z_score=z_score,
                half_life_blocked=half_life_blocked,
                cost_blocked=cost_blocked,
            )
        elif self._state == ArbState.REDUCE_ONLY:
            # Only allow closing positions
            if self._position_near != 0 or self._position_far != 0:
                self._signal = ArbSignal.FLAT
            else:
                self._signal = ArbSignal.FLAT
        else:
            self._signal = ArbSignal.FLAT

        return ArbSnapshot(
            ts=now,
            state=self._state,
            signal=self._signal,
            near_price=near_price,
            far_price=far_price,
            beta=kalman_result.beta,
            residual=kalman_result.residual,
            z_score=z_score,
            half_life=half_life,
            correlation=correlation,
            position_near=self._position_near,
            position_far=self._position_far,
            stop_triggered=stop_triggered,
            expiry_blocked=expiry_blocked,
            correlation_blocked=correlation_blocked,
            half_life_blocked=half_life_blocked,
            cost_blocked=cost_blocked,
        )

    def _check_stop_z(self, z_score: float) -> bool:
        """Check if stop-loss z-score threshold is breached.

        Scenario: ARB.SIGNAL.STOP_Z_BREAKER

        Args:
            z_score: Current z-score

        Returns:
            True if stop-loss triggered
        """
        return abs(z_score) > self._config.stop_z

    def _check_cooldown_expired(self, now: float) -> bool:
        """Check if cooldown period has expired.

        Args:
            now: Current timestamp

        Returns:
            True if cooldown expired
        """
        if self._stop_triggered_at is None:
            return True
        elapsed = now - self._stop_triggered_at
        return elapsed >= self._config.cooldown_after_stop_s

    def _check_expiry_gate(self) -> bool:
        """Check if near contract is close to expiry.

        Scenario: ARB.SIGNAL.EXPIRY_GATE

        Returns:
            True if near expiry gate triggered (should reduce only)
        """
        if self._leg_pair is None:
            return False

        try:
            # Parse expiry date (YYYYMMDD)
            expiry_str = self._leg_pair.near_expiry
            import datetime

            expiry_date = datetime.datetime.strptime(expiry_str, "%Y%m%d").date()
            today = datetime.date.today()
            days_to_expiry = (expiry_date - today).days

            return days_to_expiry <= self._config.expiry_block_days
        except (ValueError, AttributeError):
            return False

    def _check_correlation_break(self, correlation: float) -> bool:
        """Check if correlation has broken down.

        Scenario: ARB.SIGNAL.CORRELATION_BREAK

        Args:
            correlation: Rolling correlation

        Returns:
            True if correlation break detected
        """
        # Need enough samples
        if len(self._near_prices) < self._config.correlation_window:
            return False

        return correlation < self._config.min_correlation

    def _check_half_life_gate(self, half_life: float) -> bool:
        """Check if half-life is too long (not mean-reverting).

        Scenario: ARB.SIGNAL.HALF_LIFE_GATE

        Args:
            half_life: Estimated half-life in samples

        Returns:
            True if half-life gate triggered (no new entries)
        """
        # Convert samples to days (assuming ~240 samples per day for 1-min bars)
        samples_per_day = 240
        half_life_days = half_life / samples_per_day

        return half_life_days > self._config.max_half_life_days

    def _check_cost_gate(self, z_score: float, near_price: float, far_price: float) -> bool:
        """Check if entry cost exceeds edge.

        Scenario: ARB.COST.ENTRY_GATE

        Args:
            z_score: Current z-score
            near_price: Near month price
            far_price: Far month price

        Returns:
            True if cost gate triggered (insufficient edge)
        """
        # Estimate edge from z-score
        # Higher z-score = more edge
        edge_bps = abs(z_score) * 2.0  # Simplified: 1 z = 2 bps

        # Estimate cost (simplified)
        # Assume ~1 bps per leg for spread trading
        cost_bps = 2.0  # 1 bps per leg * 2 legs

        net_edge = edge_bps - cost_bps
        return net_edge < self._config.min_edge_bps

    def _generate_signal(
        self,
        z_score: float,
        half_life_blocked: bool,
        cost_blocked: bool,
    ) -> ArbSignal:
        """Generate trading signal from z-score.

        Args:
            z_score: Current z-score
            half_life_blocked: Whether half-life gate is triggered
            cost_blocked: Whether cost gate is triggered

        Returns:
            Trading signal
        """
        current_position = self._signal

        # Check exit condition
        if abs(z_score) < self._config.exit_z:
            return ArbSignal.FLAT

        # Check entry conditions (gates must pass for new entries)
        if current_position == ArbSignal.FLAT:
            if half_life_blocked or cost_blocked:
                return ArbSignal.FLAT

            if z_score > self._config.entry_z:
                # Spread too wide -> short spread (sell near, buy far)
                return ArbSignal.SHORT_SPREAD
            if z_score < -self._config.entry_z:
                # Spread too narrow -> long spread (buy near, sell far)
                return ArbSignal.LONG_SPREAD

        return current_position

    def _compute_target_near(self, snapshot: ArbSnapshot) -> int:
        """Compute target near leg position.

        Args:
            snapshot: Current snapshot

        Returns:
            Target position for near leg
        """
        if snapshot.signal == ArbSignal.LONG_SPREAD:
            return self._config.max_position_per_leg
        if snapshot.signal == ArbSignal.SHORT_SPREAD:
            return -self._config.max_position_per_leg
        return 0

    def _compute_target_far(self, snapshot: ArbSnapshot, beta: float) -> int:
        """Compute target far leg position (beta-weighted).

        Args:
            snapshot: Current snapshot
            beta: Hedge ratio

        Returns:
            Target position for far leg
        """
        near_target = self._compute_target_near(snapshot)
        if near_target == 0:
            return 0

        # Far leg is opposite of near, scaled by beta
        far_target = -int(round(near_target * beta))
        return far_target

    def _update_correlation_tracking(self, near_price: float, far_price: float) -> None:
        """Update correlation tracking buffers.

        Args:
            near_price: Near month price
            far_price: Far month price
        """
        self._near_prices.append(near_price)
        self._far_prices.append(far_price)

        # Trim to window size
        window = self._config.correlation_window
        if len(self._near_prices) > window:
            self._near_prices = self._near_prices[-window:]
            self._far_prices = self._far_prices[-window:]

    def _compute_correlation(self) -> float:
        """Compute rolling correlation between near and far prices.

        Returns:
            Pearson correlation coefficient
        """
        n = len(self._near_prices)
        if n < 2:
            return 1.0  # Assume perfect correlation initially

        # Compute means
        mean_near = sum(self._near_prices) / n
        mean_far = sum(self._far_prices) / n

        # Compute covariance and variances
        cov = 0.0
        var_near = 0.0
        var_far = 0.0

        for i in range(n):
            dn = self._near_prices[i] - mean_near
            df = self._far_prices[i] - mean_far
            cov += dn * df
            var_near += dn * dn
            var_far += df * df

        if var_near <= 0 or var_far <= 0:
            return 1.0

        corr = cov / math.sqrt(var_near * var_far)
        return max(-1.0, min(1.0, corr))

    def _compute_features_hash(self, snapshot: ArbSnapshot) -> str:
        """Compute hash of input features for audit.

        Args:
            snapshot: Current snapshot

        Returns:
            SHA256 hash of features
        """
        features = (
            f"{snapshot.near_price:.6f}|"
            f"{snapshot.far_price:.6f}|"
            f"{snapshot.beta:.6f}|"
            f"{snapshot.z_score:.6f}"
        )
        return hashlib.sha256(features.encode()).hexdigest()[:16]

    def _make_flat_portfolio(self, state: MarketState) -> TargetPortfolio:
        """Make a flat (no position) portfolio.

        Args:
            state: Market state (unused but required for signature)

        Returns:
            Empty target portfolio
        """
        return TargetPortfolio(
            target_net_qty={},
            model_version=self.VERSION,
            features_hash="flat",
        )

    # === Properties for external access ===

    @property
    def state(self) -> ArbState:
        """Current strategy state."""
        return self._state

    @property
    def signal(self) -> ArbSignal:
        """Current trading signal."""
        return self._signal

    @property
    def leg_pair(self) -> LegPair | None:
        """Current leg pair configuration."""
        return self._leg_pair

    @property
    def last_snapshot(self) -> ArbSnapshot | None:
        """Last computed snapshot."""
        return self._last_snapshot

    @property
    def config(self) -> ArbConfig:
        """Strategy configuration."""
        return self._config

    def get_state_dict(self) -> dict[str, Any]:
        """Get strategy state for serialization."""
        return {
            "state": self._state.value,
            "signal": self._signal.value,
            "position_near": self._position_near,
            "position_far": self._position_far,
            "stop_triggered_at": self._stop_triggered_at,
            "kalman": self._kalman.get_state(),
        }

    def update_position(self, near_qty: int, far_qty: int) -> None:
        """Update internal position tracking.

        Called after execution confirms fills.

        Args:
            near_qty: Near leg position
            far_qty: Far leg position
        """
        self._position_near = near_qty
        self._position_far = far_qty
