from typing import Any

import structlog

from app.core.agents.agent_manager import agent_circuit_breakers, get_agent_manager
from app.core.optimization import ReflexionConfig, arun_with_reflexion
from app.core.tools import get_faulty_tools
from app.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


class ReflexionRepositoryError(Exception):
    """Base exception for reflexion repository errors."""

    pass


class ReflexionRepository:
    """
    Camada de Repositório para o ciclo de auto-otimização Reflexion.
    Abstrai todas as interações diretas com a infraestrutura de otimização.
    """

    def __init__(self, memory_service: MemoryService):
        self._memory_service = memory_service

    async def run_cycle(self, task: str, config: ReflexionConfig) -> dict[str, Any]:
        """Executa o ciclo de Reflexion através da infraestrutura core."""
        logger.debug("Executando ciclo de Reflexion via repositório", task=task)
        try:
            return await arun_with_reflexion(
                task=task, memory_service=self._memory_service, evaluator=None, config=config
            )
        except Exception as e:
            logger.error("Erro no repositório ao executar ciclo de Reflexion", exc_info=e)
            raise ReflexionRepositoryError("Falha ao executar o ciclo de Reflexion.") from e

    def reset_breakers(self):
        """Reseta os circuit breakers dos agentes."""
        logger.debug("Resetando circuit breakers via repositório.")
        get_agent_manager().reset_circuit_breaker()

    def get_health(self) -> dict[str, Any]:
        """Coleta informações de saúde do módulo de Reflexion."""
        logger.debug("Buscando saúde do Reflexion via repositório.")
        cb_states = {
            agent_type.name: {"state": cb.state.value, "failures": cb.failure_count}
            for agent_type, cb in agent_circuit_breakers.items()
        }
        return {
            "status": "healthy",
            "module": "reflexion",
            "faulty_tools_count": len(get_faulty_tools()),
            "circuit_breakers": cb_states,
        }
