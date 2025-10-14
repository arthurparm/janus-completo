import asyncio
import structlog
from typing import Dict, Any
from fastapi import Depends

from starlette.requests import Request

from app.repositories.agent_repository import AgentRepository, get_agent_repository, AgentRepositoryError
from app.core.infrastructure import AgentType

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---

class AgentServiceError(Exception):
    """Base exception for agent service errors."""
    pass

class AgentTimeoutError(AgentServiceError):
    """Raised when agent execution exceeds the time limit."""
    pass

class AgentExecutionError(AgentServiceError):
    """Raised for general errors during agent execution."""
    pass

# --- Agent Service ---

class AgentService:
    """
    Camada de serviço para orquestrar a execução de agentes.
    Recebe sua dependência de repositório via DI.
    """
    AGENT_EXECUTION_TIMEOUT = 120  # segundos

    def __init__(self, repo: AgentRepository):
        self._repo = repo

    async def execute_agent(
            self,
            question: str,
            agent_type: AgentType,
            http_request: Request
    ) -> Dict[str, Any]:
        """
        Orquestra a execução de um agente com um timeout, delegando a chamada
        para o repositório.
        """
        correlation_id = getattr(http_request.state, "correlation_id", "no-id")
        logger.info("Orquestrando execução do agente via serviço", agent_type=agent_type.name,
                    correlation_id=correlation_id)

        try:
            result = await asyncio.wait_for(
                self._repo.run_agent(
                    question=question,
                    request=http_request,
                    agent_type=agent_type
                ),
                timeout=self.AGENT_EXECUTION_TIMEOUT
            )

            if result and "error" in result:
                error_msg = result["error"]
                logger.error("Erro retornado pelo repositório do agente", error_message=error_msg,
                             correlation_id=correlation_id)
                raise AgentExecutionError(error_msg)

            if not result:
                raise AgentExecutionError("A execução do agente retornou um resultado vazio.")

            logger.info("Execução do agente orquestrada com sucesso", correlation_id=correlation_id)
            return result

        except asyncio.TimeoutError as e:
            logger.error(f"Timeout no serviço ao executar agente após {self.AGENT_EXECUTION_TIMEOUT}s",
                         correlation_id=correlation_id)
            raise AgentTimeoutError(
                f"A execução excedeu o tempo limite de {self.AGENT_EXECUTION_TIMEOUT} segundos.") from e
        except AgentRepositoryError as e:
            logger.error("Erro no repositório de agente", exc_info=e, correlation_id=correlation_id)
            raise AgentExecutionError("Ocorreu um erro na camada de execução do agente.") from e
        except AgentExecutionError:
            raise
        except Exception as e:
            logger.critical("Erro inesperado no serviço de agente", exc_info=e, correlation_id=correlation_id)
            raise AgentServiceError("Ocorreu um erro inesperado no serviço de agente.") from e


# Padrão de Injeção de Dependência: Getter para o serviço
def get_agent_service(repo: AgentRepository = Depends(get_agent_repository)) -> AgentService:
    return AgentService(repo)
