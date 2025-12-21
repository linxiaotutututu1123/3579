"""
Single Signal Source Module (M1 Military Rule - Unified Entry Point).

V4PRO Platform Component - D7-P0 Single Signal Source Mechanism
V4 SPEC: M1 Military Rule - One trading signal can only come from one strategy instance

Military Rule Coverage:
- M1: Single Signal Source - Signal source uniqueness guarantee
- M3: Audit Log - Complete signal traceability
- M7: Scenario Replay - Signal replayable

Core Features:
1. SignalSource: Signal source registration and management
2. SignalValidator: Signal origin verification
3. ConflictResolver: Signal conflict resolution
4. SingleSignalSourceManager: Unified management interface

Design Principles:
- Each strategy instance produces unique signals with verifiable source ID
- Signal source ID validation mechanism prevents spoofing
- Conflict detection and resolution for multiple signals on same symbol
- Complete audit trail for all signal operations

Example Usage:
    >>> from src.strategy.single_signal_source import (
    ...     SingleSignalSourceManager,
    ...     SignalDirection,
    ...     SignalPriority,
    ... )
    >>> # Create manager
    >>> manager = SingleSignalSourceManager()
    >>> # Create and register signal source
    >>> source = manager.create_source(
    ...     strategy_id="kalman_arb",
    ...     instance_id="inst_001",
    ... )
    >>> # Create signal
    >>> signal = source.create_signal(
    ...     symbol="rb2501",
    ...     direction=SignalDirection.LONG,
    ...     strength=0.8,
    ...     confidence=0.9,
    ... )
    >>> # Validate signal
    >>> result = manager.validate_signal(signal)
    >>> if result.is_valid:
    ...     # Process validated signal
    ...     process_signal(signal)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

# Re-export from signal modules
from src.strategy.signal import (
    # Conflict resolver module exports
    ConflictInfo,
    ConflictSeverity,
    ConflictType,
    # Registry module exports
    RegistryEvent,
    RegistryEventType,
    ResolutionResult,
    ResolutionStrategy,
    SignalConflictResolver,
    # Source module exports
    SignalDirection,
    SignalPriority,
    SignalSource,
    SignalSourceID,
    SignalSourceRegistry,
    SignalType,
    # Validator module exports
    SignalValidator,
    SourceMetadata,
    SourceStatus,
    TradingSignal,
    ValidationErrorCode,
    ValidationResult,
    ValidationSeverity,
    create_conflict_resolver,
    create_signal_source,
    create_validator,
    generate_source_id,
    get_registry,
    get_source,
    register_source,
    resolve_conflicts,
    unregister_source,
)


if TYPE_CHECKING:
    from collections.abc import Callable


class SingleSignalSourceError(Exception):
    """Single Signal Source exception base class."""



class SignalSourceNotFoundError(SingleSignalSourceError):
    """Signal source not found exception."""



class SignalValidationError(SingleSignalSourceError):
    """Signal validation failed exception."""



class SignalConflictError(SingleSignalSourceError):
    """Signal conflict exception."""



class DuplicateSignalSourceError(SingleSignalSourceError):
    """Duplicate signal source registration exception."""



class ManagerStatus(Enum):
    """Manager status enumeration."""

    ACTIVE = "ACTIVE"  # Active
    PAUSED = "PAUSED"  # Paused
    STOPPED = "STOPPED"  # Stopped


@dataclass(frozen=True, slots=True)
class SignalProcessingResult:
    """Signal processing result (immutable).

    Attributes:
        success: Whether processing succeeded
        signal: Original signal
        validation_result: Validation result
        conflict_resolution: Conflict resolution result (if any)
        final_signal: Final signal after processing
        timestamp: Processing timestamp
        details: Additional details
    """

    success: bool
    signal: TradingSignal
    validation_result: ValidationResult
    conflict_resolution: ResolutionResult | None = None
    final_signal: TradingSignal | None = None
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "signal_id": self.signal.signal_id,
            "source_id": self.signal.source_id,
            "validation_passed": self.validation_result.is_valid,
            "had_conflict": self.conflict_resolution is not None,
            "final_signal_id": (
                self.final_signal.signal_id if self.final_signal else None
            ),
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(
                self.timestamp, tz=UTC
            ).isoformat(),
            "details": self.details,
        }

    def to_audit_record(self) -> dict[str, Any]:
        """Generate audit record (M3)."""
        return {
            "event_type": "SIGNAL_PROCESSED",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.to_dict(),
        }


@dataclass
class SingleSignalSourceManager:
    """Single Signal Source Manager (M1 Military Rule Unified Interface).

    This manager provides a unified interface for:
    - Signal source creation and registration
    - Signal validation with source ID verification
    - Signal conflict detection and resolution
    - Audit logging for all operations

    M1 Military Rule Implementation:
    - Each strategy instance has a unique signal source ID
    - All signals are validated against their declared source
    - Conflicts between signals are detected and resolved
    - Complete audit trail is maintained

    Attributes:
        registry: Signal source registry (singleton)
        validator: Signal validator
        resolver: Conflict resolver
        status: Manager status
    """

    # Default configuration
    DEFAULT_SIGNAL_TTL: ClassVar[float] = 60.0  # Default signal TTL (seconds)
    DEFAULT_CONFLICT_WINDOW: ClassVar[float] = 5.0  # Conflict detection window
    DEFAULT_RATE_LIMIT: ClassVar[int] = 100  # Max signals per second per source

    # Components
    validator: SignalValidator = field(default_factory=SignalValidator)
    resolver: SignalConflictResolver = field(default_factory=SignalConflictResolver)
    status: ManagerStatus = field(default=ManagerStatus.ACTIVE)

    # Configuration
    signal_ttl: float = field(default=60.0)
    strict_validation: bool = field(default=True)
    auto_register: bool = field(default=True)

    # Internal state
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _pending_signals: dict[str, list[TradingSignal]] = field(
        default_factory=dict, init=False, repr=False
    )
    _processing_callbacks: list[Callable[[SignalProcessingResult], None]] = field(
        default_factory=list, init=False, repr=False
    )
    _signal_counter: int = field(default=0, init=False, repr=False)
    _validation_pass_count: int = field(default=0, init=False, repr=False)
    _validation_fail_count: int = field(default=0, init=False, repr=False)
    _conflict_count: int = field(default=0, init=False, repr=False)

    @property
    def registry(self) -> SignalSourceRegistry:
        """Get the global signal source registry."""
        return get_registry()

    @property
    def is_active(self) -> bool:
        """Check if manager is active."""
        return self.status == ManagerStatus.ACTIVE

    @property
    def statistics(self) -> dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            return {
                "status": self.status.value,
                "signal_count": self._signal_counter,
                "validation_pass_count": self._validation_pass_count,
                "validation_fail_count": self._validation_fail_count,
                "validation_pass_rate": (
                    self._validation_pass_count / self._signal_counter
                    if self._signal_counter > 0
                    else 0.0
                ),
                "conflict_count": self._conflict_count,
                "registered_sources": self.registry.source_count,
                "active_sources": self.registry.active_source_count,
                "pending_signal_groups": len(self._pending_signals),
            }

    # ============================================================
    # Signal Source Management (M1: Single Signal Source)
    # ============================================================

    def create_source(
        self,
        strategy_id: str,
        instance_id: str | None = None,
        signal_ttl: float | None = None,
        tags: list[str] | None = None,
        auto_register: bool | None = None,
    ) -> SignalSource:
        """Create and optionally register a signal source.

        This method implements M1 military rule by ensuring each strategy
        instance has a unique signal source with verifiable ID.

        Args:
            strategy_id: Strategy identifier
            instance_id: Instance identifier (auto-generated if None)
            signal_ttl: Signal time-to-live in seconds
            tags: Optional tags for the source
            auto_register: Whether to auto-register (uses manager default if None)

        Returns:
            SignalSource instance

        Raises:
            DuplicateSignalSourceError: If source already registered
        """
        if not self.is_active:
            raise SingleSignalSourceError("Manager is not active")

        # Create signal source
        source = create_signal_source(
            strategy_id=strategy_id,
            instance_id=instance_id,
            signal_ttl=signal_ttl or self.signal_ttl,
        )

        # Auto-register if enabled
        should_register = auto_register if auto_register is not None else self.auto_register
        if should_register:
            success = self.register_source(source, tags)
            if not success:
                raise DuplicateSignalSourceError(
                    f"Signal source already registered: {source.full_source_id}"
                )

        return source

    def register_source(
        self,
        source: SignalSource,
        tags: list[str] | None = None,
    ) -> bool:
        """Register a signal source.

        Args:
            source: SignalSource instance to register
            tags: Optional tags for the source

        Returns:
            True if registered successfully, False if already registered
        """
        if not self.is_active:
            return False

        # Register in global registry
        success = register_source(source, tags)

        # Also register in validator for signature verification
        if success:
            self.validator.register_source(source)

        return success

    def unregister_source(self, source_id: str) -> bool:
        """Unregister a signal source.

        Args:
            source_id: Signal source ID to unregister

        Returns:
            True if unregistered successfully
        """
        # Unregister from global registry
        success = unregister_source(source_id)

        # Also unregister from validator
        if success:
            self.validator.unregister_source(source_id)

        return success

    def get_source(self, source_id: str) -> SignalSource | None:
        """Get a registered signal source.

        Args:
            source_id: Signal source ID

        Returns:
            SignalSource instance or None if not found
        """
        return get_source(source_id)

    def get_source_or_raise(self, source_id: str) -> SignalSource:
        """Get a registered signal source or raise exception.

        Args:
            source_id: Signal source ID

        Returns:
            SignalSource instance

        Raises:
            SignalSourceNotFoundError: If source not found
        """
        source = self.get_source(source_id)
        if source is None:
            raise SignalSourceNotFoundError(f"Signal source not found: {source_id}")
        return source

    def is_source_registered(self, source_id: str) -> bool:
        """Check if a signal source is registered.

        Args:
            source_id: Signal source ID

        Returns:
            True if registered
        """
        return self.registry.is_registered(source_id)

    def is_source_active(self, source_id: str) -> bool:
        """Check if a signal source is active.

        Args:
            source_id: Signal source ID

        Returns:
            True if active
        """
        return self.registry.is_active(source_id)

    def get_all_sources(self) -> list[SignalSource]:
        """Get all registered signal sources.

        Returns:
            List of all SignalSource instances
        """
        return self.registry.get_all_sources()

    def get_active_sources(self) -> list[SignalSource]:
        """Get all active signal sources.

        Returns:
            List of active SignalSource instances
        """
        return self.registry.get_active_sources()

    def get_sources_by_strategy(self, strategy_id: str) -> list[SignalSource]:
        """Get all signal sources for a strategy.

        Args:
            strategy_id: Strategy identifier

        Returns:
            List of SignalSource instances for the strategy
        """
        return self.registry.get_sources_by_strategy(strategy_id)

    # ============================================================
    # Signal Validation (M1: Signal Source ID Verification)
    # ============================================================

    def validate_signal(
        self,
        signal: TradingSignal,
        expected_symbol: str | None = None,
        strict_mode: bool | None = None,
    ) -> ValidationResult:
        """Validate a trading signal.

        This method implements M1 military rule by verifying:
        - Signal source ID format is valid
        - Signal source is registered and active
        - Signal signature is valid (in strict mode)
        - Signal is not expired or duplicate
        - Signal parameters are within valid ranges

        Args:
            signal: TradingSignal to validate
            expected_symbol: Expected symbol (optional)
            strict_mode: Whether to verify signature (uses manager default if None)

        Returns:
            ValidationResult with validation details
        """
        if not self.is_active:
            return ValidationResult.failure(
                signal_id=signal.signal_id,
                source_id=signal.source_id,
                error_code=ValidationErrorCode.SOURCE_INACTIVE,
                message="Manager is not active",
                severity=ValidationSeverity.ERROR,
            )

        # Use manager default for strict mode if not specified
        use_strict = strict_mode if strict_mode is not None else self.strict_validation

        # Perform validation
        result = self.validator.validate(
            signal=signal,
            expected_symbol=expected_symbol,
            strict_mode=use_strict,
        )

        # Update statistics
        with self._lock:
            if result.is_valid:
                self._validation_pass_count += 1
            else:
                self._validation_fail_count += 1

        return result

    def validate_source_ownership(
        self,
        signal: TradingSignal,
        expected_source_id: str,
    ) -> ValidationResult:
        """Validate that a signal comes from the expected source.

        This is a core M1 military rule check - ensuring signals
        are not spoofed from unauthorized sources.

        Args:
            signal: TradingSignal to validate
            expected_source_id: Expected signal source ID

        Returns:
            ValidationResult with ownership verification details
        """
        return self.validator.validate_source_ownership(signal, expected_source_id)

    def verify_signal_signature(
        self,
        signal: TradingSignal,
    ) -> bool:
        """Verify a signal's cryptographic signature.

        Args:
            signal: TradingSignal to verify

        Returns:
            True if signature is valid
        """
        source = self.get_source(signal.source_id)
        if source is None:
            return False
        return source.verify_signal(signal)

    # ============================================================
    # Conflict Detection and Resolution (M1: Prevent Duplicate Signals)
    # ============================================================

    def detect_conflicts(
        self,
        signals: list[TradingSignal],
    ) -> list[ConflictInfo]:
        """Detect conflicts between signals.

        Types of conflicts detected:
        - Direction conflict: LONG vs SHORT on same symbol
        - Source duplicate: Multiple signals from same source
        - Timing conflict: Signals too close in time with different directions

        Args:
            signals: List of signals to check

        Returns:
            List of ConflictInfo for detected conflicts
        """
        conflicts = self.resolver.detect_conflicts(signals)

        # Update statistics
        with self._lock:
            self._conflict_count += len(conflicts)

        return conflicts

    def resolve_signal_conflicts(
        self,
        signals: list[TradingSignal],
        strategy: ResolutionStrategy | None = None,
    ) -> ResolutionResult:
        """Resolve conflicts between signals.

        Resolution strategies:
        - PRIORITY_FIRST: Highest priority signal wins
        - CONFIDENCE_WEIGHTED: Highest confidence signal wins
        - STRENGTH_WEIGHTED: Highest strength signal wins
        - NEWEST_FIRST: Most recent signal wins
        - OLDEST_FIRST: Earliest signal wins
        - REJECT_ALL: Reject all conflicting signals
        - FLAT_ON_CONFLICT: Return flat (no position) on conflict

        Args:
            signals: List of conflicting signals
            strategy: Resolution strategy (uses resolver default if None)

        Returns:
            ResolutionResult with winning signal (if any)
        """
        return self.resolver.resolve(signals, strategy)

    def resolve_by_priority(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """Resolve conflicts by priority.

        Args:
            signals: List of signals

        Returns:
            Highest priority signal or None
        """
        return self.resolver.resolve_by_priority(signals)

    def resolve_by_confidence(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """Resolve conflicts by confidence.

        Args:
            signals: List of signals

        Returns:
            Highest confidence signal or None
        """
        return self.resolver.resolve_by_confidence(signals)

    def resolve_by_strength(
        self,
        signals: list[TradingSignal],
    ) -> TradingSignal | None:
        """Resolve conflicts by strength.

        Args:
            signals: List of signals

        Returns:
            Highest strength signal or None
        """
        return self.resolver.resolve_by_strength(signals)

    # ============================================================
    # Unified Signal Processing Pipeline
    # ============================================================

    def process_signal(
        self,
        signal: TradingSignal,
        check_conflicts: bool = True,
        conflict_strategy: ResolutionStrategy | None = None,
    ) -> SignalProcessingResult:
        """Process a signal through the full validation and conflict resolution pipeline.

        This is the main entry point for signal processing, implementing the
        complete M1 military rule workflow:
        1. Validate signal source and parameters
        2. Check for conflicts with pending signals (if enabled)
        3. Resolve conflicts if any
        4. Return final processed signal

        Args:
            signal: TradingSignal to process
            check_conflicts: Whether to check for conflicts
            conflict_strategy: Strategy for resolving conflicts

        Returns:
            SignalProcessingResult with processing details
        """
        if not self.is_active:
            validation_result = ValidationResult.failure(
                signal_id=signal.signal_id,
                source_id=signal.source_id,
                error_code=ValidationErrorCode.SOURCE_INACTIVE,
                message="Manager is not active",
            )
            return SignalProcessingResult(
                success=False,
                signal=signal,
                validation_result=validation_result,
                details={"error": "Manager is not active"},
            )

        with self._lock:
            self._signal_counter += 1

        # Step 1: Validate signal
        validation_result = self.validate_signal(signal)

        if not validation_result.is_valid:
            result = SignalProcessingResult(
                success=False,
                signal=signal,
                validation_result=validation_result,
                details={"validation_error": validation_result.error_code.value},
            )
            self._notify_processing_callbacks(result)
            return result

        # Step 2: Check for conflicts (if enabled)
        conflict_resolution = None
        final_signal = signal

        if check_conflicts:
            symbol = signal.symbol
            with self._lock:
                if symbol not in self._pending_signals:
                    self._pending_signals[symbol] = []
                pending = self._pending_signals[symbol]

                # Add current signal to pending
                pending.append(signal)

                # Detect and resolve conflicts if multiple signals
                if len(pending) > 1:
                    conflict_resolution = self.resolve_signal_conflicts(
                        pending, conflict_strategy
                    )

                    if conflict_resolution.resolved and conflict_resolution.winner_signal:
                        final_signal = conflict_resolution.winner_signal
                    else:
                        # No winner - clear pending and fail
                        self._pending_signals[symbol] = []
                        result = SignalProcessingResult(
                            success=False,
                            signal=signal,
                            validation_result=validation_result,
                            conflict_resolution=conflict_resolution,
                            details={"conflict_error": "No winner from conflict resolution"},
                        )
                        self._notify_processing_callbacks(result)
                        return result

                    # Clear resolved signals from pending
                    self._pending_signals[symbol] = [final_signal]

        # Step 3: Record signal in registry
        self.registry.record_signal(signal.source_id)

        # Build result
        result = SignalProcessingResult(
            success=True,
            signal=signal,
            validation_result=validation_result,
            conflict_resolution=conflict_resolution,
            final_signal=final_signal,
            details={
                "had_conflict": conflict_resolution is not None,
                "signal_unchanged": final_signal.signal_id == signal.signal_id,
            },
        )

        self._notify_processing_callbacks(result)
        return result

    def process_signals_batch(
        self,
        signals: list[TradingSignal],
        conflict_strategy: ResolutionStrategy | None = None,
    ) -> list[SignalProcessingResult]:
        """Process a batch of signals.

        Args:
            signals: List of signals to process
            conflict_strategy: Strategy for resolving conflicts

        Returns:
            List of SignalProcessingResult for each signal
        """
        results = []
        for signal in signals:
            result = self.process_signal(
                signal,
                check_conflicts=True,
                conflict_strategy=conflict_strategy,
            )
            results.append(result)
        return results

    def clear_pending_signals(self, symbol: str | None = None) -> None:
        """Clear pending signals.

        Args:
            symbol: Symbol to clear (all symbols if None)
        """
        with self._lock:
            if symbol:
                self._pending_signals.pop(symbol, None)
            else:
                self._pending_signals.clear()

    # ============================================================
    # Callback Management
    # ============================================================

    def register_processing_callback(
        self,
        callback: Callable[[SignalProcessingResult], None],
    ) -> None:
        """Register a callback for signal processing results.

        Args:
            callback: Callback function
        """
        with self._lock:
            self._processing_callbacks.append(callback)

    def unregister_processing_callback(
        self,
        callback: Callable[[SignalProcessingResult], None],
    ) -> None:
        """Unregister a processing callback.

        Args:
            callback: Callback function to remove
        """
        with self._lock:
            if callback in self._processing_callbacks:
                self._processing_callbacks.remove(callback)

    def _notify_processing_callbacks(
        self,
        result: SignalProcessingResult,
    ) -> None:
        """Notify all processing callbacks.

        Args:
            result: Processing result to notify
        """
        with self._lock:
            callbacks = list(self._processing_callbacks)

        for callback in callbacks:
            try:
                callback(result)
            except Exception:
                pass  # Ignore callback errors

    # ============================================================
    # Manager Lifecycle
    # ============================================================

    def pause(self) -> None:
        """Pause the manager."""
        self.status = ManagerStatus.PAUSED

    def resume(self) -> None:
        """Resume the manager."""
        self.status = ManagerStatus.ACTIVE

    def stop(self) -> None:
        """Stop the manager."""
        self.status = ManagerStatus.STOPPED
        self.clear_pending_signals()

    def reset(self) -> None:
        """Reset the manager state."""
        with self._lock:
            self._pending_signals.clear()
            self._processing_callbacks.clear()
            self._signal_counter = 0
            self._validation_pass_count = 0
            self._validation_fail_count = 0
            self._conflict_count = 0

        self.validator.reset()
        self.resolver.clear_history()
        self.status = ManagerStatus.ACTIVE

    # ============================================================
    # Statistics and Reporting
    # ============================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics.

        Returns:
            Dictionary with all statistics
        """
        return {
            "manager": self.statistics,
            "registry": self.registry.get_statistics(),
            "validator": self.validator.get_validation_statistics(),
            "resolver": self.resolver.get_statistics(),
        }

    def get_health_report(self) -> dict[str, Any]:
        """Get health report.

        Returns:
            Dictionary with health status
        """
        registry_health = self.registry.get_health_report()

        return {
            "manager_status": self.status.value,
            "manager_active": self.is_active,
            "registry_health": registry_health,
            "validation_pass_rate": (
                self._validation_pass_count / self._signal_counter
                if self._signal_counter > 0
                else 0.0
            ),
            "check_time": datetime.now(tz=UTC).isoformat(),
        }

    def to_audit_record(self) -> dict[str, Any]:
        """Generate audit record (M3).

        Returns:
            Dictionary for audit logging
        """
        return {
            "event_type": "SINGLE_SIGNAL_SOURCE_STATUS",
            "event_time": datetime.now(tz=UTC).isoformat(),
            **self.get_statistics(),
        }


# ============================================================
# Module-level Singleton Manager
# ============================================================

_default_manager: SingleSignalSourceManager | None = None
_manager_lock = threading.Lock()


def get_manager() -> SingleSignalSourceManager:
    """Get the default SingleSignalSourceManager instance.

    Returns:
        SingleSignalSourceManager singleton
    """
    global _default_manager
    with _manager_lock:
        if _default_manager is None:
            _default_manager = SingleSignalSourceManager()
        return _default_manager


def reset_manager() -> None:
    """Reset the default manager (for testing)."""
    global _default_manager
    with _manager_lock:
        if _default_manager is not None:
            _default_manager.reset()
        _default_manager = None
    # Also reset the registry
    SignalSourceRegistry.reset_instance()


# ============================================================
# Convenience Functions
# ============================================================


def create_and_register_source(
    strategy_id: str,
    instance_id: str | None = None,
    signal_ttl: float = 60.0,
    tags: list[str] | None = None,
) -> SignalSource:
    """Create and register a signal source using the default manager.

    Args:
        strategy_id: Strategy identifier
        instance_id: Instance identifier (auto-generated if None)
        signal_ttl: Signal time-to-live in seconds
        tags: Optional tags

    Returns:
        Registered SignalSource instance
    """
    return get_manager().create_source(
        strategy_id=strategy_id,
        instance_id=instance_id,
        signal_ttl=signal_ttl,
        tags=tags,
    )


def validate_signal(
    signal: TradingSignal,
    strict_mode: bool = True,
) -> ValidationResult:
    """Validate a signal using the default manager.

    Args:
        signal: TradingSignal to validate
        strict_mode: Whether to verify signature

    Returns:
        ValidationResult
    """
    return get_manager().validate_signal(signal, strict_mode=strict_mode)


def process_signal(
    signal: TradingSignal,
    check_conflicts: bool = True,
) -> SignalProcessingResult:
    """Process a signal using the default manager.

    Args:
        signal: TradingSignal to process
        check_conflicts: Whether to check for conflicts

    Returns:
        SignalProcessingResult
    """
    return get_manager().process_signal(signal, check_conflicts=check_conflicts)


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Exceptions
    "SingleSignalSourceError",
    "SignalSourceNotFoundError",
    "SignalValidationError",
    "SignalConflictError",
    "DuplicateSignalSourceError",
    # Manager
    "ManagerStatus",
    "SignalProcessingResult",
    "SingleSignalSourceManager",
    "get_manager",
    "reset_manager",
    # Source module re-exports
    "SignalDirection",
    "SignalPriority",
    "SignalSource",
    "SignalSourceID",
    "SignalType",
    "SourceStatus",
    "TradingSignal",
    "create_signal_source",
    "generate_source_id",
    # Validator module re-exports
    "SignalValidator",
    "ValidationErrorCode",
    "ValidationResult",
    "ValidationSeverity",
    "create_validator",
    # Registry module re-exports
    "RegistryEvent",
    "RegistryEventType",
    "SignalSourceRegistry",
    "SourceMetadata",
    "get_registry",
    "get_source",
    "register_source",
    "unregister_source",
    # Conflict resolver re-exports
    "ConflictInfo",
    "ConflictSeverity",
    "ConflictType",
    "ResolutionResult",
    "ResolutionStrategy",
    "SignalConflictResolver",
    "create_conflict_resolver",
    "resolve_conflicts",
    # Convenience functions
    "create_and_register_source",
    "validate_signal",
    "process_signal",
]
