"""Fallback Manager for Strategy Degradation (Military-Grade v3.0).

Implements strategy fallback framework as specified in V2 SPEC 8.3:
- Chain-based fallback: each strategy has a defined fallback chain
- Exception fallback: catch strategy exceptions, fall to next in chain
- Timeout fallback: detect slow strategies, fall to faster alternatives
- Final fallback: simple_ai as ultimate fallback

Required Scenarios:
- STRAT.FALLBACK.ON_EXCEPTION: Exception triggers fallback
- STRAT.FALLBACK.ON_TIMEOUT: Timeout triggers fallback
- STRAT.FALLBACK.CHAIN_DEFINED: All chains properly defined

Example:
    from src.strategy.fallback import FallbackManager, FallbackConfig
    from src.strategy.simple_ai import SimpleAIStrategy

    config = FallbackConfig(timeout_s=1.0)
    manager = FallbackManager(config)
    manager.register("top_tier", top_tier_strategy)
    manager.register("simple_ai", simple_ai_strategy)

    # Execute with fallback protection
    result = manager.execute("top_tier", state)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from src.strategy.base import Strategy
    from src.strategy.types import MarketState, TargetPortfolio

logger = logging.getLogger(__name__)


class FallbackReason(str, Enum):
    """Reason for fallback activation."""

    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    NOT_REGISTERED = "not_registered"
    MANUAL = "manual"


@dataclass(frozen=True)
class FallbackEvent:
    """Event emitted when fallback occurs.

    Used for audit trail (STRAT.DEGRADE.MODE_TRANSITION_AUDIT).
    """

    ts: float
    original_strategy: str
    fallback_strategy: str
    reason: FallbackReason
    error_message: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for audit."""
        return {
            "ts": self.ts,
            "event_type": "fallback",
            "original_strategy": self.original_strategy,
            "fallback_strategy": self.fallback_strategy,
            "reason": self.reason.value,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
        }


@dataclass
class FallbackConfig:
    """Configuration for fallback manager.

    Attributes:
        timeout_s: Maximum execution time before timeout fallback
        max_chain_depth: Maximum fallback chain depth to prevent loops
        enable_timeout: Whether to enable timeout detection
        enable_exception: Whether to enable exception fallback
    """

    timeout_s: float = 1.0
    max_chain_depth: int = 5
    enable_timeout: bool = True
    enable_exception: bool = True


# Default fallback chains as specified in V3PRO_UPGRADE_PLAN 8.4
DEFAULT_FALLBACK_CHAINS: dict[str, list[str]] = {
    "top_tier": ["ensemble_moe", "linear_ai", "simple_ai"],
    "dl_torch": ["linear_ai", "simple_ai"],
    "ensemble_moe": ["linear_ai", "simple_ai"],
    "linear_ai": ["simple_ai"],
    "simple_ai": [],  # Self-fallback (ultimate fallback)
    "calendar_arb": ["top_tier", "ensemble_moe", "simple_ai"],
}

# Default final fallback strategy
DEFAULT_FINAL_FALLBACK = "simple_ai"


@dataclass
class FallbackResult:
    """Result of strategy execution with fallback info."""

    portfolio: TargetPortfolio | None
    strategy_used: str
    fallback_occurred: bool
    fallback_events: list[FallbackEvent] = field(default_factory=list)
    total_latency_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Whether execution succeeded (portfolio is not None)."""
        return self.portfolio is not None


class FallbackManager:
    """Manages strategy fallback chains.

    Implements military-grade fallback framework:
    1. Maintains registry of strategy instances
    2. Defines fallback chains per strategy
    3. Handles exceptions and timeouts gracefully
    4. Emits audit events for all fallbacks

    Required Scenarios Coverage:
    - STRAT.FALLBACK.ON_EXCEPTION: execute() catches exceptions
    - STRAT.FALLBACK.ON_TIMEOUT: execute() detects timeouts
    - STRAT.FALLBACK.CHAIN_DEFINED: get_chain() returns valid chains
    """

    def __init__(
        self,
        config: FallbackConfig | None = None,
        chains: Mapping[str, Sequence[str]] | None = None,
        final_fallback: str = DEFAULT_FINAL_FALLBACK,
    ) -> None:
        """Initialize fallback manager.

        Args:
            config: Fallback configuration
            chains: Custom fallback chains (defaults to DEFAULT_FALLBACK_CHAINS)
            final_fallback: Ultimate fallback strategy name
        """
        self._config = config or FallbackConfig()
        self._chains: dict[str, list[str]] = {
            k: list(v) for k, v in (chains or DEFAULT_FALLBACK_CHAINS).items()
        }
        self._final_fallback = final_fallback
        self._strategies: dict[str, Strategy] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fallback")
        self._fallback_counts: dict[str, int] = {}
        self._event_handlers: list[Callable[[FallbackEvent], None]] = []

    def register(self, name: str, strategy: Strategy) -> None:
        """Register a strategy instance.

        Args:
            name: Strategy name (must match chain definitions)
            strategy: Strategy instance
        """
        self._strategies[name] = strategy
        logger.debug("Registered strategy: %s", name)

    def unregister(self, name: str) -> bool:
        """Unregister a strategy.

        Args:
            name: Strategy name to remove

        Returns:
            True if strategy was registered and removed
        """
        if name in self._strategies:
            del self._strategies[name]
            return True
        return False

    def get_chain(self, strategy_name: str) -> list[str]:
        """Get fallback chain for a strategy.

        Scenario: STRAT.FALLBACK.CHAIN_DEFINED

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of fallback strategy names (may be empty for simple_ai)
        """
        return list(self._chains.get(strategy_name, [self._final_fallback]))

    def set_chain(self, strategy_name: str, chain: Sequence[str]) -> None:
        """Set custom fallback chain for a strategy.

        Args:
            strategy_name: Name of the strategy
            chain: List of fallback strategy names
        """
        self._chains[strategy_name] = list(chain)

    def add_event_handler(self, handler: Callable[[FallbackEvent], None]) -> None:
        """Add handler for fallback events (for audit integration).

        Args:
            handler: Callback function that receives FallbackEvent
        """
        self._event_handlers.append(handler)

    def execute(
        self,
        strategy_name: str,
        state: MarketState,
    ) -> FallbackResult:
        """Execute strategy with fallback protection.

        Scenarios:
        - STRAT.FALLBACK.ON_EXCEPTION: Catches exceptions, falls to next
        - STRAT.FALLBACK.ON_TIMEOUT: Detects timeout, falls to next

        Args:
            strategy_name: Name of the strategy to execute
            state: Current market state

        Returns:
            FallbackResult with portfolio and fallback info
        """
        start_time = time.time()
        fallback_events: list[FallbackEvent] = []

        # Build execution order: original + fallback chain
        execution_order = [strategy_name, *self.get_chain(strategy_name)]

        # Ensure final fallback is in the list
        if self._final_fallback not in execution_order:
            execution_order.append(self._final_fallback)

        # Limit chain depth
        execution_order = execution_order[: self._config.max_chain_depth]

        portfolio: TargetPortfolio | None = None
        strategy_used = strategy_name
        depth = 0

        for current_strategy in execution_order:
            depth += 1

            # Check if strategy is registered
            if current_strategy not in self._strategies:
                event = FallbackEvent(
                    ts=time.time(),
                    original_strategy=strategy_name,
                    fallback_strategy=current_strategy,
                    reason=FallbackReason.NOT_REGISTERED,
                    error_message=f"Strategy not registered: {current_strategy}",
                )
                fallback_events.append(event)
                self._emit_event(event)
                continue

            strategy = self._strategies[current_strategy]

            # Try to execute with timeout and exception handling
            try:
                portfolio = self._execute_with_timeout(strategy, state, current_strategy)
                strategy_used = current_strategy
                break  # Success, exit loop

            except FuturesTimeoutError:
                # STRAT.FALLBACK.ON_TIMEOUT
                if self._config.enable_timeout:
                    latency_ms = (time.time() - start_time) * 1000
                    event = FallbackEvent(
                        ts=time.time(),
                        original_strategy=strategy_name,
                        fallback_strategy=current_strategy,
                        reason=FallbackReason.TIMEOUT,
                        error_message=f"Timeout after {self._config.timeout_s}s",
                        latency_ms=latency_ms,
                    )
                    fallback_events.append(event)
                    self._emit_event(event)
                    self._increment_fallback_count(current_strategy)
                    logger.warning("Strategy %s timed out, trying fallback", current_strategy)

            except Exception as e:
                # STRAT.FALLBACK.ON_EXCEPTION
                if self._config.enable_exception:
                    latency_ms = (time.time() - start_time) * 1000
                    event = FallbackEvent(
                        ts=time.time(),
                        original_strategy=strategy_name,
                        fallback_strategy=current_strategy,
                        reason=FallbackReason.EXCEPTION,
                        error_message=str(e),
                        latency_ms=latency_ms,
                    )
                    fallback_events.append(event)
                    self._emit_event(event)
                    self._increment_fallback_count(current_strategy)
                    logger.warning(
                        "Strategy %s raised exception: %s, trying fallback",
                        current_strategy,
                        e,
                    )

        total_latency_ms = (time.time() - start_time) * 1000

        return FallbackResult(
            portfolio=portfolio,
            strategy_used=strategy_used,
            fallback_occurred=len(fallback_events) > 0,
            fallback_events=fallback_events,
            total_latency_ms=total_latency_ms,
        )

    def _execute_with_timeout(
        self,
        strategy: Strategy,
        state: MarketState,
        strategy_name: str,
    ) -> TargetPortfolio:
        """Execute strategy with timeout protection.

        Args:
            strategy: Strategy instance
            state: Market state
            strategy_name: Name for logging

        Returns:
            TargetPortfolio from strategy

        Raises:
            FuturesTimeoutError: If execution exceeds timeout
            Exception: Any exception from strategy
        """
        if not self._config.enable_timeout:
            # Direct execution without timeout
            return strategy.on_tick(state)

        future = self._executor.submit(strategy.on_tick, state)
        try:
            return future.result(timeout=self._config.timeout_s)
        except FuturesTimeoutError:
            future.cancel()
            raise

    def _emit_event(self, event: FallbackEvent) -> None:
        """Emit fallback event to all handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler error")

    def _increment_fallback_count(self, strategy_name: str) -> None:
        """Increment fallback count for a strategy."""
        self._fallback_counts[strategy_name] = self._fallback_counts.get(strategy_name, 0) + 1

    def get_fallback_counts(self) -> dict[str, int]:
        """Get fallback counts by strategy.

        Returns:
            Dictionary mapping strategy name to fallback count
        """
        return dict(self._fallback_counts)

    def reset_counts(self) -> None:
        """Reset all fallback counts."""
        self._fallback_counts.clear()

    def get_registered_strategies(self) -> list[str]:
        """Get list of registered strategy names."""
        return list(self._strategies.keys())

    def is_chain_valid(self, strategy_name: str) -> bool:
        """Check if fallback chain is valid (all strategies registered).

        Args:
            strategy_name: Strategy to check chain for

        Returns:
            True if all strategies in chain are registered
        """
        chain = self.get_chain(strategy_name)
        return all(s in self._strategies for s in chain)

    def close(self) -> None:
        """Shutdown executor and cleanup resources."""
        self._executor.shutdown(wait=False)

    def __enter__(self) -> FallbackManager:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
