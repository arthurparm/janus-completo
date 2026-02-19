import asyncio
import random
import time
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any

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
    """
    Circuit Breaker com suporte a operações síncronas e assíncronas.

    Previne cascata de falhas bloqueando chamadas quando um threshold de falhas é atingido.
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        """
        Inicializa o Circuit Breaker.

        Args:
            failure_threshold: Número de falhas antes de abrir o circuito
            recovery_timeout: Tempo em segundos antes de tentar recuperação

        Raises:
            ValueError: Se parâmetros forem inválidos
        """
        if failure_threshold < 1:
            raise ValueError(f"failure_threshold deve ser >= 1, recebido: {failure_threshold}")
        if recovery_timeout < 1:
            raise ValueError(f"recovery_timeout deve ser >= 1, recebido: {recovery_timeout}")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self._open_since: float | None = None
        self._last_operation = "unknown"

        logger.info(
            "circuit_breaker_initialized",
            threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def is_open(self) -> bool:
        """
        Verifica se o circuito está aberto.

        Returns:
            True se o circuito está OPEN
        """
        result = self.state == CircuitBreakerState.OPEN
        if result:
            import traceback

            logger.warning(
                f"[CircuitBreaker] is_open=True! state={self.state.value}, failures={self.failure_count}, last_failure={self.last_failure_time}"
            )
            logger.warning(
                f"[CircuitBreaker] Call stack:\n{''.join(traceback.format_stack()[-5:])}"
            )
        return result

    def get_health_status(self) -> dict[str, Any]:
        """
        Retorna métricas de saúde do Circuit Breaker.
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
            "open_since": self._open_since,
            "is_open": self.state == CircuitBreakerState.OPEN,
        }

    def __call__(self, func: Callable) -> Callable:
        """
        Decorador para proteger funções síncronas.

        Args:
            func: Função a ser protegida

        Returns:
            Função decorada
        """

        def wrapper(*args, **kwargs) -> Any:
            operation = getattr(func, "__name__", "unknown")
            self._last_operation = operation

            # Update OPEN time gauge if currently open
            if self.state == CircuitBreakerState.OPEN and self._open_since:
                _OPEN_TIME_GAUGE.labels(operation=operation).set(
                    max(0.0, time.time() - self._open_since)
                )

            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time is not None and (
                    time.time() - self.last_failure_time > self.recovery_timeout
                ):
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._set_state_gauges(operation)
                    logger.warning("circuit_half_open", operation=operation)
                else:
                    # keep gauges reflecting OPEN
                    self._set_state_gauges(operation)
                    raise CircuitOpenError(
                        f"Circuit Breaker está ABERTO para '{operation}'. Chamada bloqueada."
                    )

            try:
                result = func(*args, **kwargs)
                self._on_success(operation)
                return result
            except Exception:
                self._on_failure(operation)
                raise

        return wrapper

    async def call_async(
        self, coro_func: Callable[..., Coroutine], operation: str | None = None
    ) -> Any:
        """
        Executa uma função assíncrona protegida pelo circuit breaker com logging detalhado.

        Args:
            coro_func: Função assíncrona a ser executada
            operation: Nome da operação para logs e métricas

        Returns:
            Resultado da função

        Raises:
            CircuitOpenError: Se o circuito estiver aberto
        """
        operation = operation or getattr(coro_func, "__name__", "async_operation")
        self._last_operation = operation
        start_time = time.time()

        # Update OPEN time gauge if currently open
        if self.state == CircuitBreakerState.OPEN and self._open_since:
            open_duration = time.time() - self._open_since
            _OPEN_TIME_GAUGE.labels(operation=operation).set(max(0.0, open_duration))

            # Log detailed circuit breaker state when attempting call
            logger.warning(
                "circuit_breaker_call_attempt_while_open",
                operation=operation,
                state=self.state.value,
                open_duration_seconds=open_duration,
                recovery_timeout=self.recovery_timeout,
                failure_count=self.failure_count,
                failure_threshold=self.failure_threshold,
                last_failure_time=self.last_failure_time,
                time_since_last_failure=(
                    time.time() - self.last_failure_time if self.last_failure_time else None
                ),
            )

        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time is not None and (
                time.time() - self.last_failure_time > self.recovery_timeout
            ):
                old_state = self.state
                self.state = CircuitBreakerState.HALF_OPEN
                self._set_state_gauges(operation)
                logger.warning(
                    "circuit_transition_to_half_open",
                    operation=operation,
                    state_transition=f"{old_state.value} -> {self.state.value}",
                    open_duration=time.time() - self._open_since if self._open_since else 0,
                    recovery_timeout=self.recovery_timeout,
                    failure_count=self.failure_count,
                )
            else:
                self._set_state_gauges(operation)
                rejection_time = time.time() - start_time
                recovery_remaining = (
                    max(0, self.recovery_timeout - (time.time() - self.last_failure_time))
                    if self.last_failure_time
                    else self.recovery_timeout
                )

                logger.error(
                    "circuit_breaker_rejected_call",
                    operation=operation,
                    state=self.state.value,
                    rejection_time_seconds=rejection_time,
                    recovery_timeout_remaining=recovery_remaining,
                    failure_count=self.failure_count,
                    failure_threshold=self.failure_threshold,
                )

                raise CircuitOpenError(
                    f"Circuit Breaker está ABERTO para '{operation}'. "
                    f"Falhas: {self.failure_count}/{self.failure_threshold}. "
                    f"Tempo de recuperação restante: {recovery_remaining:.1f}s"
                )

        try:
            result = await coro_func()
            execution_time = time.time() - start_time
            self._on_success(operation)

            # Log successful execution with timing
            logger.info(
                "circuit_breaker_call_success",
                operation=operation,
                state=self.state.value,
                execution_time_seconds=execution_time,
                failure_count=self.failure_count,
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self._on_failure(operation)

            # Log failure with detailed context
            logger.error(
                "circuit_breaker_call_failed",
                operation=operation,
                state=self.state.value,
                execution_time_seconds=execution_time,
                exception_type=type(e).__name__,
                exception_message=str(e),
                failure_count=self.failure_count,
                failure_threshold=self.failure_threshold,
            )

            raise

    def _set_state_gauges(self, operation: str) -> None:
        """Atualiza métricas Prometheus com estado atual."""
        # set 1 for current state and 0 for others
        for state in (
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        ):
            _CIRCUIT_STATE_GAUGE.labels(operation=operation, state=state.value).set(
                1.0 if self.state == state else 0.0
            )

        # update OPEN time gauge
        if self.state == CircuitBreakerState.OPEN and self._open_since:
            _OPEN_TIME_GAUGE.labels(operation=operation).set(
                max(0.0, time.time() - self._open_since)
            )
        else:
            _OPEN_TIME_GAUGE.labels(operation=operation).set(0.0)

    def _on_success(self, operation: str):
        """Trata sucesso da operação."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("circuit_closed_after_test", operation=operation)

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self._open_since = None

        _FAILURE_COUNT_GAUGE.labels(operation=operation).set(self.failure_count)
        self._set_state_gauges(operation)

    def _on_failure(self, operation: str):
        """Trata falha da operação com logging detalhado."""
        old_state = self.state
        self.failure_count += 1
        self.last_failure_time = time.time()

        _FAILURE_COUNT_GAUGE.labels(operation=operation).set(self.failure_count)

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self._open_since = time.time()
            logger.error(
                "circuit_back_to_open_after_failed_test",
                operation=operation,
                failure_count=self.failure_count,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                state_transition=f"{old_state.value} -> {self.state.value}",
                open_since=self._open_since,
                last_failure_time=self.last_failure_time,
            )
            import traceback

            logger.warning(
                f"[CircuitBreaker] State changed to OPEN from HALF_OPEN after failed test. "
                f"Failures: {self.failure_count}/{self.failure_threshold}, "
                f"Recovery timeout: {self.recovery_timeout}s. "
                f"Stack:\n{''.join(traceback.format_stack()[-8:])}"
            )
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self._open_since = time.time()
            logger.error(
                "circuit_open_threshold_reached",
                operation=operation,
                failure_count=self.failure_count,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                state_transition=f"{old_state.value} -> {self.state.value}",
                open_since=self._open_since,
                last_failure_time=self.last_failure_time,
            )
            import traceback

            logger.warning(
                f"[CircuitBreaker] CRITICAL: Circuit breaker OPENED due to threshold reached. "
                f"Failures: {self.failure_count}/{self.failure_threshold}, "
                f"Recovery timeout: {self.recovery_timeout}s. "
                f"All calls to '{operation}' will be blocked for {self.recovery_timeout} seconds. "
                f"Stack:\n{''.join(traceback.format_stack()[-8:])}"
            )

        self._set_state_gauges(operation)

    def reset(self):
        """
        Reseta o circuit breaker para estado CLOSED.

        Útil para testes ou recuperação manual.
        """
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self._open_since = None

        if self._last_operation != "unknown":
            _FAILURE_COUNT_GAUGE.labels(operation=self._last_operation).set(0)
            self._set_state_gauges(self._last_operation)

        logger.info("circuit_breaker_reset", operation=self._last_operation)

    def update_params(
        self, failure_threshold: int | None = None, recovery_timeout: int | None = None
    ) -> None:
        if failure_threshold is not None:
            try:
                ft = int(failure_threshold)
                if ft >= 1:
                    self.failure_threshold = ft
            except Exception:
                pass
        if recovery_timeout is not None:
            try:
                rt = int(recovery_timeout)
                if rt >= 1:
                    self.recovery_timeout = rt
            except Exception:
                pass
        if self._last_operation != "unknown":
            _FAILURE_COUNT_GAUGE.labels(operation=self._last_operation).set(self.failure_count)
            self._set_state_gauges(self._last_operation)


def resilient(
    max_attempts: int = 3,
    initial_backoff: float = 1.0,
    max_backoff: float = 10.0,
    circuit_breaker: CircuitBreaker | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    operation_name: str | None = None,
) -> Callable:
    """
    Decorador que aplica retry com exponential backoff + jitter e, opcionalmente, Circuit Breaker.

    Suporta funções síncronas e assíncronas.

    Args:
        max_attempts: Número máximo de tentativas
        initial_backoff: Backoff inicial em segundos
        max_backoff: Backoff máximo em segundos
        circuit_breaker: Circuit breaker opcional
        retry_on: Tupla de exceções que devem acionar retry
        operation_name: Nome da operação para métricas

    Returns:
        Decorador configurado

    Raises:
        ValueError: Se parâmetros forem inválidos
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts deve ser >= 1, recebido: {max_attempts}")
    if initial_backoff <= 0:
        raise ValueError(f"initial_backoff deve ser > 0, recebido: {initial_backoff}")
    if max_backoff < initial_backoff:
        raise ValueError(
            f"max_backoff ({max_backoff}) deve ser >= initial_backoff ({initial_backoff})"
        )

    def decorator(func: Callable) -> Callable:
        operation = operation_name or getattr(func, "__name__", "unknown")

        # Detecta se é uma função assíncrona
        if asyncio.iscoroutinefunction(func):

            async def async_wrapper(*args, **kwargs):
                last_exception = None

                # Aplica circuit breaker se fornecido
                if circuit_breaker:

                    async def protected_call():
                        return await func(*args, **kwargs)

                    def call():
                        # Preserve configured operation_name in circuit breaker events/errors.
                        return circuit_breaker.call_async(protected_call, operation=operation)

                else:

                    def call():
                        return func(*args, **kwargs)

                for attempt in range(max_attempts):
                    start = time.perf_counter()

                    try:
                        result = await call()
                        elapsed = time.perf_counter() - start

                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="success", exception_type=""
                        ).observe(elapsed)

                        logger.info(
                            "resilient_attempt_success",
                            operation=operation,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            elapsed_ms=int(elapsed * 1000),
                        )

                        return result

                    except CircuitOpenError as e:
                        elapsed = time.perf_counter() - start
                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="failure", exception_type=type(e).__name__
                        ).observe(elapsed)

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
                        elapsed = time.perf_counter() - start
                        exc_type = type(e).__name__

                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="failure", exception_type=exc_type
                        ).observe(elapsed)

                        # Apenas retentar se o erro for de um tipo especificado em retry_on
                        if isinstance(e, retry_on):
                            last_exception = e

                            if attempt + 1 >= max_attempts:
                                break

                            backoff = min(max_backoff, initial_backoff * (2**attempt))
                            sleep_time = random.uniform(0, backoff)  # full jitter

                            _RETRIES_COUNTER.labels(
                                operation=operation, exception_type=exc_type
                            ).inc()

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

                            await asyncio.sleep(sleep_time)
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

            return async_wrapper

        else:
            # Função síncrona
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                call = circuit_breaker(func) if circuit_breaker else func

                for attempt in range(max_attempts):
                    start = time.perf_counter()

                    try:
                        result = call(*args, **kwargs)
                        elapsed = time.perf_counter() - start

                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="success", exception_type=""
                        ).observe(elapsed)

                        logger.info(
                            "resilient_attempt_success",
                            operation=operation,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            elapsed_ms=int(elapsed * 1000),
                        )

                        return result

                    except CircuitOpenError as e:
                        elapsed = time.perf_counter() - start
                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="failure", exception_type=type(e).__name__
                        ).observe(elapsed)

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
                        elapsed = time.perf_counter() - start
                        exc_type = type(e).__name__

                        _ATTEMPT_LATENCY_HIST.labels(
                            operation=operation, outcome="failure", exception_type=exc_type
                        ).observe(elapsed)

                        # Apenas retentar se o erro for de um tipo especificado em retry_on
                        if isinstance(e, retry_on):
                            last_exception = e

                            if attempt + 1 >= max_attempts:
                                break

                            backoff = min(max_backoff, initial_backoff * (2**attempt))
                            sleep_time = random.uniform(0, backoff)  # full jitter

                            _RETRIES_COUNTER.labels(
                                operation=operation, exception_type=exc_type
                            ).inc()

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

            return sync_wrapper

    return decorator
