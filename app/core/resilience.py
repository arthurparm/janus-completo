# app/core/resilience.py
import time
import logging
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"  # O circuito está fechado, as chamadas são permitidas.
    OPEN = "OPEN"  # O circuito está aberto, as chamadas falham imediatamente.
    HALF_OPEN = "HALF_OPEN"  # O circuito permite uma única chamada de teste.


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 30):
        """
        Inicializa o Circuit Breaker.

        Args:
            failure_threshold (int): Número de falhas consecutivas para abrir o circuito.
            recovery_timeout (int): Tempo em segundos para esperar antes de tentar fechar o circuito (estado HALF_OPEN).
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info(
            f"Circuit Breaker inicializado com threshold={failure_threshold} e timeout={recovery_timeout}s."
        )

    def __call__(self, func: Callable) -> Callable:
        """Permite que o Circuit Breaker seja usado como um decorador."""

        def wrapper(*args, **kwargs) -> Any:
            if self.state == CircuitBreakerState.OPEN:
                # Se o tempo de recuperação já passou, transita para HALF_OPEN
                if self.last_failure_time is not None and (time.time() - self.last_failure_time > self.recovery_timeout):
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.warning(
                        "Circuit Breaker transitou para o estado HALF_OPEN. Permitindo uma chamada de teste."
                    )
                else:
                    # Se ainda não passou o tempo, falha imediatamente
                    error_msg = "Circuit Breaker está ABERTO. A chamada foi bloqueada."
                    logger.error(error_msg)
                    raise ConnectionError(error_msg)

            # No estado CLOSED ou HALF_OPEN, tenta executar a função
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                # Propaga a exceção original
                raise e

        return wrapper

    def _on_success(self):
        """Reseta o estado do circuito em caso de sucesso."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info(
                "Chamada de teste bem-sucedida. Circuit Breaker transitou para o estado CLOSED."
            )
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self):
        """Incrementa a contagem de falhas e abre o circuito se necessário."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            # A chamada de teste falhou, volta para OPEN e reinicia o timer
            self.state = CircuitBreakerState.OPEN
            logger.error(
                "Chamada de teste falhou. Circuit Breaker voltou para o estado OPEN."
            )
        elif self.failure_count >= self.failure_threshold:
            # Atingiu o limite de falhas, abre o circuito
            self.state = CircuitBreakerState.OPEN
            logger.error(
                f"Limite de falhas ({self.failure_threshold}) atingido. Circuit Breaker transitou para o estado OPEN."
            )
