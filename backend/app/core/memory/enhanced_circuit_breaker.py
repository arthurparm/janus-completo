"""
Enhanced circuit breaker with improved monitoring, recovery, and resilience features.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.infrastructure.resilience import CircuitBreaker, CircuitBreakerState, CircuitOpenError
from app.core.memory.circuit_config import RESILIENCE_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: list[dict[str, Any]] = field(default_factory=list)
    last_state_change: float | None = None
    average_response_time: float = 0.0
    p95_response_time: float = 0.0

    def record_call(self, success: bool, response_time: float = 0.0):
        """Record a circuit breaker call."""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        # Update response time metrics
        if response_time > 0:
            self.average_response_time = (
                self.average_response_time * (self.total_calls - 1) + response_time
            ) / self.total_calls
            # Simple P95 estimation (not exact but good enough for monitoring)
            if response_time > self.p95_response_time:
                self.p95_response_time = response_time * 0.95

    def record_rejection(self):
        """Record a rejected call when circuit is open."""
        self.rejected_calls += 1

    def record_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
        """Record a state change."""
        change_time = time.time()
        self.state_changes.append(
            {
                "timestamp": change_time,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "human_time": datetime.fromtimestamp(change_time).isoformat(),
            }
        )
        self.last_state_change = change_time


class EnhancedCircuitBreaker:
    """Enhanced circuit breaker with better monitoring and recovery features."""

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_max_calls: int | None = None,
        half_open_success_threshold: int | None = None,
        name: str = "unnamed",
    ):
        """
        Initialize enhanced circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
            half_open_max_calls: Max calls allowed in half-open state
            half_open_success_threshold: Success threshold for closing from half-open
            name: Name for identification in logs/metrics
        """
        config = RESILIENCE_CONFIG.circuit_breaker

        self.failure_threshold = failure_threshold or config.failure_threshold
        self.recovery_timeout = recovery_timeout or config.recovery_timeout
        self.half_open_max_calls = half_open_max_calls or config.half_open_max_calls
        self.half_open_success_threshold = (
            half_open_success_threshold or config.half_open_success_threshold
        )
        self.name = name

        # Initialize base circuit breaker
        self._cb = CircuitBreaker(
            failure_threshold=self.failure_threshold, recovery_timeout=self.recovery_timeout
        )

        # Enhanced state tracking
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._metrics = CircuitBreakerMetrics()
        self._response_times: list[float] = []

        logger.info(
            "enhanced_circuit_breaker_initialized",
            name=self.name,
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
            half_open_max_calls=self.half_open_max_calls,
            half_open_success_threshold=self.half_open_success_threshold,
        )

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._cb.state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._cb.failure_count

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        return self._metrics

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self._cb.is_open()

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "is_open": self.is_open(),
            "metrics": {
                "total_calls": self._metrics.total_calls,
                "successful_calls": self._metrics.successful_calls,
                "failed_calls": self._metrics.failed_calls,
                "rejected_calls": self._metrics.rejected_calls,
                "success_rate": self._get_success_rate(),
                "average_response_time": self._metrics.average_response_time,
                "p95_response_time": self._metrics.p95_response_time,
            },
            "state_changes": self._metrics.state_changes[-10:],  # Last 10 state changes
            "last_state_change": self._metrics.last_state_change,
        }

    def _get_success_rate(self) -> float:
        """Calculate success rate."""
        if self._metrics.total_calls == 0:
            return 0.0
        return self._metrics.successful_calls / self._metrics.total_calls

    def _record_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
        """Record state change and log it."""
        self._metrics.record_state_change(old_state, new_state)
        logger.warning(
            "circuit_breaker_state_changed",
            name=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
            failure_count=self.failure_count,
            metrics=self.get_health_status()["metrics"],
        )

    def _handle_half_open_logic(self, success: bool):
        """Handle half-open state logic."""
        if self.state != CircuitBreakerState.HALF_OPEN:
            return

        self._half_open_calls += 1
        if success:
            self._half_open_successes += 1

        # Check if we should close or reopen the circuit
        if self._half_open_calls >= self.half_open_max_calls:
            if self._half_open_successes >= self.half_open_success_threshold:
                # Success threshold met, close the circuit
                old_state = self.state
                self._cb.state = CircuitBreakerState.CLOSED
                self._cb.failure_count = 0
                self._cb.last_failure_time = None
                self._half_open_calls = 0
                self._half_open_successes = 0
                self._record_state_change(old_state, CircuitBreakerState.CLOSED)
                logger.info(
                    "circuit_breaker_closed_from_half_open",
                    name=self.name,
                    successes=self._half_open_successes,
                    total_calls=self._half_open_calls,
                )
            else:
                # Not enough successes, reopen the circuit
                old_state = self.state
                self._cb.state = CircuitBreakerState.OPEN
                self._cb._open_since = time.time()
                self._half_open_calls = 0
                self._half_open_successes = 0
                self._record_state_change(old_state, CircuitBreakerState.OPEN)
                logger.warning(
                    "circuit_breaker_reopened_from_half_open",
                    name=self.name,
                    successes=self._half_open_successes,
                    total_calls=self._half_open_calls,
                )

    async def call_async(self, coro_func: Callable, *args, **kwargs):
        """Enhanced async call with better monitoring."""
        start_time = time.time()

        # Check if circuit is open
        if self.is_open():
            self._metrics.record_rejection()
            raise CircuitOpenError(f"Circuit Breaker '{self.name}' está ABERTO. Chamada bloqueada.")

        try:
            # Execute the call
            result = await coro_func(*args, **kwargs)

            # Record success
            response_time = time.time() - start_time
            self._metrics.record_call(True, response_time)
            self._handle_half_open_logic(True)

            return result

        except Exception as e:
            # Record failure
            response_time = time.time() - start_time
            self._metrics.record_call(False, response_time)

            # Handle circuit breaker state
            old_state = self.state
            self._cb._on_failure("async_operation")

            # Check if state changed
            if self.state != old_state:
                self._record_state_change(old_state, self.state)

            self._handle_half_open_logic(False)

            logger.warning(
                "circuit_breaker_call_failed",
                name=self.name,
                exception_type=type(e).__name__,
                response_time=response_time,
                failure_count=self.failure_count,
                state=self.state.value,
            )

            raise

    def reset(self):
        """Reset circuit breaker with enhanced logging."""
        old_state = self.state
        self._cb.reset()
        self._half_open_calls = 0
        self._half_open_successes = 0

        logger.info(
            "circuit_breaker_reset",
            name=self.name,
            old_state=old_state.value,
            new_state=CircuitBreakerState.CLOSED.value,
        )

        if old_state != CircuitBreakerState.CLOSED:
            self._record_state_change(old_state, CircuitBreakerState.CLOSED)


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self):
        self._circuit_breakers: dict[str, EnhancedCircuitBreaker] = {}

    def get_circuit_breaker(self, name: str, **kwargs) -> EnhancedCircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = EnhancedCircuitBreaker(name=name, **kwargs)
        return self._circuit_breakers[name]

    def get_all_health_status(self) -> dict[str, Any]:
        """Get health status for all circuit breakers."""
        return {name: cb.get_health_status() for name, cb in self._circuit_breakers.items()}

    def reset_circuit_breaker(self, name: str):
        """Reset a specific circuit breaker."""
        if name in self._circuit_breakers:
            self._circuit_breakers[name].reset()

    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            cb.reset()


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()
