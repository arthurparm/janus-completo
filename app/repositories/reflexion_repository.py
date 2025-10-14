import structlog
from typing import Dict, Any

from app.core.optimization import arun_with_reflexion, ReflexionConfig
from app.core.agents.agent_manager import get_agent_manager, agent_circuit_breakers  # Modified import
from app.core.tools import get_faulty_tools

logger = structlog.get_logger(__name__)

class ReflexionRepositoryError(Exception):
    """Base exception for reflexion repository errors."""
    pass

class ReflexionRepository:
    """
    Camada de Repositório para o ciclo de auto-otimização Reflexion.
    Abstrai todas as interações diretas com a infraestrutura de otimização.
    """

    async def run_cycle(self, task: str, config: ReflexionConfig) -> Dict[str, Any]:
        """Executa o ciclo de Reflexion através da infraestrutura core."""
        logger.debug("Executando ciclo de Reflexion via repositório", task=task)
        try:
            return await arun_with_reflexion(task=task, evaluator=None, config=config)
        except Exception as e:
            logger.error("Erro no repositório ao executar ciclo de Reflexion", exc_info=e)
            raise ReflexionRepositoryError("Falha ao executar o ciclo de Reflexion.") from e

    def reset_breakers(self):
        """Reseta os circuit breakers dos agentes."""
        logger.debug("Resetando circuit breakers via repositório.")
        # Call the method on the agent_manager instance
        get_agent_manager().reset_circuit_breaker()

    def get_health(self) -> Dict[str, Any]:
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


# Padrão de Injeção de Dependência: Getter para o repositório
def get_reflexion_repository() -> ReflexionRepository:
    return ReflexionRepository()
