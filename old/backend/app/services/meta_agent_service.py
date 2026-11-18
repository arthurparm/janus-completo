from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _load_meta_agent() -> Any:
    """Carrega o meta-agente real sob demanda, sem substituto ficticio."""
    from app.core.agents import get_meta_agent

    return get_meta_agent()


# --- Custom Service-Layer Exceptions ---


class MetaAgentServiceError(Exception):
    """Base exception for meta-agent service errors."""

    pass


class MetaAgentUnavailableError(MetaAgentServiceError):
    """Raised when the real meta-agent cannot be loaded or initialized."""

    pass


# --- Meta-Agent Service ---


class MetaAgentService:
    """
    Camada de serviço para o Meta-Agente de Auto-Otimização.
    Abstrai a lógica de controle do ciclo de vida do meta-agente da camada de API.
    """

    def __init__(self, agent_factory: Callable[[], Any] | None = None) -> None:
        self._agent_factory = agent_factory or _load_meta_agent

    def _get_agent(self) -> Any:
        try:
            return self._agent_factory()
        except MetaAgentUnavailableError:
            raise
        except Exception as exc:
            logger.error("meta_agent_unavailable", exception_type=type(exc).__name__)
            raise MetaAgentUnavailableError("Meta-agent dependencies are unavailable.") from exc

    async def run_analysis_cycle(self) -> Any:
        logger.info("Disparando ciclo de análise do meta-agente via serviço.")
        try:
            agent = self._get_agent()
            return await agent.run_analysis_cycle()
        except MetaAgentUnavailableError:
            raise
        except Exception as e:
            logger.error("Erro no serviço ao executar ciclo de análise do meta-agente", exc_info=e)
            raise MetaAgentServiceError("Falha ao executar o ciclo de análise.") from e

    def get_latest_report(self) -> Any | None:
        logger.info("Buscando último relatório do meta-agente via serviço.")
        return self._get_agent().last_report

    async def start_heartbeat(self, interval_minutes: int) -> bool:
        logger.info(
            "Iniciando heartbeat do meta-agente via serviço", interval_minutes=interval_minutes
        )
        agent = self._get_agent()
        heartbeat_task = getattr(agent, "_heartbeat_task", None)
        if heartbeat_task and not heartbeat_task.done():
            logger.warning("Tentativa de iniciar um heartbeat já ativo.")
            return False  # Indica que já estava ativo

        await agent.start_heartbeat(interval_minutes=interval_minutes)
        return True

    def stop_heartbeat(self) -> None:
        logger.info("Parando heartbeat do meta-agente via serviço.")
        self._get_agent().stop_heartbeat()

    def get_heartbeat_status(self) -> dict[str, Any]:
        logger.info("Buscando status do heartbeat do meta-agente.")
        agent = self._get_agent()
        heartbeat_task = getattr(agent, "_heartbeat_task", None)
        is_active = heartbeat_task is not None and not heartbeat_task.done()
        return {
            "heartbeat_active": is_active,
            "total_cycles_executed": agent.cycle_count,
            "last_analysis": agent.last_report.timestamp.isoformat() if agent.last_report else None,
        }

    def get_health_status(self) -> dict[str, Any]:
        logger.info("Buscando status de saúde do meta-agente.")
        try:
            agent = self._get_agent()
        except MetaAgentUnavailableError:
            return {
                "status": "unavailable",
                "reason_code": "META_AGENT_DEPENDENCY_UNAVAILABLE",
                "agent_id": None,
                "executor_initialized": False,
                "tools_count": 0,
                "cycles_executed": 0,
            }
        return {
            "status": "healthy",
            "agent_id": agent.agent_id,
            "executor_initialized": getattr(agent, "executor", None) is not None,
            "tools_count": len(agent.tools),
            "cycles_executed": agent.cycle_count,
        }


# Instância única do serviço
meta_agent_service = MetaAgentService()


# Padrão de Injeção de Dependência: Getter para o serviço
def get_meta_agent_service() -> MetaAgentService:
    return meta_agent_service
