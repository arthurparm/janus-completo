import structlog
from typing import Dict, Any

from starlette.requests import Request

from app.core.agents.agent_manager import agent_manager, AgentType

logger = structlog.get_logger(__name__)


class AgentRepositoryError(Exception):
    """Base exception for agent repository errors."""
    pass


class AgentRepository:
    """
    Camada de Repositório para o Agent Manager.
    Abstrai todas as interações diretas com a infraestrutura de execução de agentes.
    """

    async def run_agent(
            self,
            question: str,
            agent_type: AgentType,
            http_request: Request
    ) -> Dict[str, Any]:
        """Executa um agente através do agent_manager."""
        logger.debug("Executando agente via repositório", agent_type=agent_type.name)
        try:
            return await agent_manager.arun_agent(
                question=question,
                request=http_request,
                agent_type=agent_type
            )
        except Exception as e:
            logger.error("Erro no repositório ao executar agente", exc_info=e)
            raise AgentRepositoryError("Falha ao executar agente no agent_manager.") from e


# Instância única do repositório
agent_repository = AgentRepository()
