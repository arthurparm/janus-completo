# app/core/resilience.py
import logging
import random
import time
from enum import Enum
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


# --- MELHORIA: EXCEÇÃO DEDICADA ---
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
        logger.info(
            f"Circuit Breaker inicializado com threshold={failure_threshold} e timeout={recovery_timeout}s."
        )

    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time is not None and (
                        time.time() - self.last_failure_time > self.recovery_timeout):
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.warning(
                        "Circuit Breaker transitou para HALF_OPEN. Permitindo uma chamada de teste."
                    )
                else:
                    # --- MELHORIA: USA A EXCEÇÃO DEDICADA ---
                    raise CircuitOpenError("Circuit Breaker está ABERTO. Chamada bloqueada.")
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception:
                self._on_failure()
                raise

        return wrapper

    def _on_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Chamada de teste bem-sucedida. Circuit Breaker fechado.")
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.error("Chamada de teste falhou. Circuit Breaker voltou para OPEN.")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(
                f"Limite de falhas ({self.failure_threshold}) atingido. Circuit Breaker em OPEN."
            )


# --- MELHORIA: DECORADOR DE RETRY MAIS ROBUSTO ---
def resilient(
        max_attempts: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 10.0,
        circuit_breaker: CircuitBreaker = None,
        retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """
    Decorador que aplica retry com exponential backoff + jitter e, opcionalmente, Circuit Breaker.
    `retry_on`: Uma tupla de tipos de exceção que devem acionar uma nova tentativa.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    if circuit_breaker:
                        return circuit_breaker(func)(*args, **kwargs)
                    return func(*args, **kwargs)
                except CircuitOpenError as e:
                    # Circuito aberto: não retentar
                    logger.warning(f"Execução de '{func.__name__}' abortada pois o circuito está aberto.")
                    last_exception = e
                    break
                except Exception as e:
                    # Apenas retentar se o erro for de um tipo especificado em retry_on
                    if isinstance(e, retry_on):
                        last_exception = e
                        if attempt + 1 >= max_attempts:
                            break
                        backoff = min(max_backoff, initial_backoff * (2 ** attempt))
                        sleep_time = random.uniform(0, backoff)  # full jitter
                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_attempts} para '{func.__name__}' falhou: {e}. Retentando em {sleep_time:.2f}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Erro não-retriável
                        logger.error(f"Erro não-retriável em '{func.__name__}': {e}. Abortando.")
                        last_exception = e
                        break
            if last_exception:
                logger.error(f"'{func.__name__}' falhou após as tentativas. Último erro: {last_exception}")
                raise last_exception

        return wrapper

    return decorator
