import random
import time
from enum import Enum
from typing import Callable, Any, Tuple, Type, Optional

import structlog

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore
    _PROM_ENABLED = True
except Exception:  # pragma: no cover - fallback if not installed
    _PROM_ENABLED = False

    class _NoopMetric:
        def labels(self, *_, **__):
            return self

        def inc(self, *_args, **_kwargs):
            return None

        def set(self, *_args, **_kwargs):
            return None

        def observe(self, *_args, **_kwargs):
            return None

    Counter = Gauge = Histogram = _NoopMetric  # type: ignore

PROM_ENABLED = _PROM_ENABLED
logger = structlog.get_logger(__name__)

# Metrics definitions
_CIRCUIT_STATE_GAUGE = Gauge(
    "janus_resilience_circuit_state",
    "Circuit breaker state (1 = current state, 0 otherwise)",
    ["operation", "state"],
)
_FAILURE_COUNT_GAUGE = Gauge(
    "janus_resilience_failure_count",
    "Current failure count tracked by the circuit breaker",
    ["operation"],
)
_OPEN_TIME_GAUGE = Gauge(
    "janus_resilience_open_time_seconds",
    "How long (in seconds) the circuit has been continuously OPEN",
    ["operation"],
)
_RETRIES_COUNTER = Counter(
    "janus_resilience_retries_total",
    "Total number of retries performed by the resilient decorator",
    ["operation", "exception_type"],
)
_ATTEMPT_LATENCY_HIST = Histogram(
    "janus_resilience_attempt_latency_seconds",
    "Latency per attempt of a resilient/circuit-breaker protected operation",
    ["operation", "outcome", "exception_type"],
)


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(ConnectionError):
    """Lançada quando o Circuit Breaker está ABERTO e bloqueia a chamada."""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self._open_since = None  # type: float | None
        self._last_operation = "unknown"
        logger.info(
            "circuit_breaker_initialized",
            threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            operation = getattr(func, "__name__", "unknown")
            self._last_operation = operation
            # Update OPEN time gauge if currently open
            if self.state == CircuitBreakerState.OPEN and self._open_since:
                _OPEN_TIME_GAUGE.labels(operation=operation).set(max(0.0, time.time() - self._open_since))
            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time is not None and (
                        time.time() - self.last_failure_time > self.recovery_timeout):
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._set_state_gauges(operation)
                    logger.warning(
                        "circuit_half_open",
                        operation=operation,
                    )
                else:
                    # keep gauges reflecting OPEN
                    self._set_state_gauges(operation)
                    raise CircuitOpenError("Circuit Breaker está ABERTO. Chamada bloqueada.")
            try:
                result = func(*args, **kwargs)
                self._on_success(operation)
                return result
            except Exception:
                self._on_failure(operation)
                raise

        return wrapper

    def _set_state_gauges(self, operation: str) -> None:
        # set 1 for current state and 0 for others
        for state in (CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN):
            _CIRCUIT_STATE_GAUGE.labels(operation=operation, state=state.value).set(1.0 if self.state == state else 0.0)
        # update OPEN time gauge
        if self.state == CircuitBreakerState.OPEN and self._open_since:
            _OPEN_TIME_GAUGE.labels(operation=operation).set(max(0.0, time.time() - self._open_since))
        else:
            _OPEN_TIME_GAUGE.labels(operation=operation).set(0.0)

    def _on_success(self, operation: str):
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("circuit_closed_after_test", operation=operation)
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self._open_since = None
        _FAILURE_COUNT_GAUGE.labels(operation=operation).set(self.failure_count)
        self._set_state_gauges(operation)

    def _on_failure(self, operation: str):
        self.failure_count += 1
        self.last_failure_time = time.time()
        _FAILURE_COUNT_GAUGE.labels(operation=operation).set(self.failure_count)
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self._open_since = time.time()
            logger.error("circuit_back_to_open_after_failed_test", operation=operation)
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self._open_since = time.time()
            logger.error(
                "circuit_open_threshold_reached",
                operation=operation,
                failure_threshold=self.failure_threshold,
            )
        self._set_state_gauges(operation)


def resilient(
        max_attempts: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 10.0,
        circuit_breaker: CircuitBreaker = None,
        retry_on: Tuple[Type[BaseException], ...] = (Exception,),
        operation_name: Optional[str] = None,
) -> Callable:
    """
    Decorador que aplica retry com exponential backoff + jitter e, opcionalmente, Circuit Breaker.
    `retry_on`: Uma tupla de tipos de exceção que devem acionar uma nova tentativa.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            operation = operation_name or getattr(func, "__name__", "unknown")
            last_exception = None
            call = circuit_breaker(func) if circuit_breaker else func
            for attempt in range(max_attempts):
                start = time.perf_counter()
                try:
                    result = call(*args, **kwargs)
                    elapsed = (time.perf_counter() - start)
                    _ATTEMPT_LATENCY_HIST.labels(operation=operation, outcome="success", exception_type="").observe(elapsed)
                    logger.info(
                        "resilient_attempt_success",
                        operation=operation,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        elapsed_ms=int(elapsed * 1000),
                    )
                    return result
                except CircuitOpenError as e:
                    elapsed = (time.perf_counter() - start)
                    _ATTEMPT_LATENCY_HIST.labels(operation=operation, outcome="failure", exception_type=type(e).__name__).observe(elapsed)
                    logger.warning(
                        "resilient_circuit_open_abort",
                        operation=operation,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        elapsed_ms=int(elapsed * 1000),
                        exception=type(e).__name__,
                        message=str(e),
                    )
                    last_exception = e
                    break  # não retentar com circuito aberto
                except Exception as e:
                    elapsed = (time.perf_counter() - start)
                    exc_type = type(e).__name__
                    _ATTEMPT_LATENCY_HIST.labels(operation=operation, outcome="failure", exception_type=exc_type).observe(elapsed)
                    # Apenas retentar se o erro for de um tipo especificado em retry_on
                    if isinstance(e, retry_on):
                        last_exception = e
                        if attempt + 1 >= max_attempts:
                            break
                        backoff = min(max_backoff, initial_backoff * (2 ** attempt))
                        sleep_time = random.uniform(0, backoff)  # full jitter
                        _RETRIES_COUNTER.labels(operation=operation, exception_type=exc_type).inc()
                        logger.warning(
                            "resilient_attempt_retry",
                            operation=operation,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            backoff_seconds=round(sleep_time, 3),
                            elapsed_ms=int(elapsed * 1000),
                            exception=exc_type,
                            message=str(e),
                        )
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Erro não-retriável
                        logger.error(
                            "resilient_non_retriable_error",
                            operation=operation,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            elapsed_ms=int(elapsed * 1000),
                            exception=exc_type,
                            message=str(e),
                        )
                        last_exception = e
                        break
            if last_exception:
                logger.error(
                    "resilient_failed_after_attempts",
                    operation=operation,
                    attempts=attempt + 1,
                    max_attempts=max_attempts,
                    exception=type(last_exception).__name__,
                    message=str(last_exception),
                )
                raise last_exception

        return wrapper

    return decorator
