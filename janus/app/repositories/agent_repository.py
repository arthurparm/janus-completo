from typing import Any

import structlog
from fastapi import Depends
from starlette.requests import Request

from app.core.agents.agent_manager import AgentManager, AgentType, get_agent_manager

logger = structlog.get_logger(__name__)


class AgentRepositoryError(Exception):
    """Base exception for agent repository errors."""

    pass


class AgentRepository:
    """
    Camada de Repositório para o Agent Manager.
    Recebe sua dependência de infraestrutura via DI.
    """

    def __init__(self, manager: AgentManager):
        self._manager = manager

    async def run_agent(
        self, question: str, agent_type: AgentType, http_request: Request
    ) -> dict[str, Any]:
        """Executa um agente através do agent_manager."""
        logger.debug("Executando agente via repositório", agent_type=agent_type.name)
        try:
            return await self._manager.arun_agent(
                question=question, request=http_request, agent_type=agent_type
            )
        except Exception as e:
            logger.error("Erro no repositório ao executar agente", exc_info=e)
            raise AgentRepositoryError("Falha ao executar agente no agent_manager.") from e


# Padrão de Injeção de Dependência: Getter para o repositório
def get_agent_repository(manager: AgentManager = Depends(get_agent_manager)) -> AgentRepository:
    return AgentRepository(manager)
