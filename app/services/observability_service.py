import structlog
from typing import Dict, Any, List, Optional

from app.core.monitoring import get_health_monitor, HealthMonitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler, PoisonPillHandler, QuarantinedMessage
# Imports para o novo método de sumário
from app.core.llm import _provider_circuit_breakers, _llm_cache
from app.core.agents import get_multi_agent_system

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class ObservabilityServiceError(Exception):
    """Base exception for observability service errors."""
    pass


class MessageNotFoundError(ObservabilityServiceError):
    """Raised when a message is not found in quarantine."""
    pass


# --- Observability Service ---

class ObservabilityService:
    """
    Camada de serviço para observabilidade, saúde do sistema e resiliência.
    Abstrai o acesso aos monitores e handlers da camada de API.
    """

    def __init__(self, monitor: HealthMonitor, pp_handler: PoisonPillHandler):
        self._monitor = monitor
        self._pp_handler = pp_handler

    async def get_system_health(self) -> Dict[str, Any]:
        logger.info("Buscando saúde agregada do sistema via serviço.")
        try:
            return self._monitor.get_system_health()
        except Exception as e:
            logger.error("Erro no serviço ao buscar saúde do sistema", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> Dict[str, Dict[str, Any]]:
        logger.info("Disparando health check de todos os componentes via serviço.")
        try:
            results = await self._monitor.check_all_components()
            return {name: r.to_dict() for name, r in results.items()}
        except Exception as e:
            logger.error("Erro no serviço ao executar health checks", exc_info=e)
            raise ObservabilityServiceError("Falha ao executar os health checks.") from e

    def get_quarantined_messages(self, queue: Optional[str] = None) -> List[QuarantinedMessage]:
        logger.info("Buscando mensagens em quarentena via serviço", queue=queue)
        return self._pp_handler.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.info("Liberando mensagem da quarentena via serviço", message_id=message_id)
        msg = self._pp_handler.release_from_quarantine(message_id, allow_retry)
        if not msg:
            raise MessageNotFoundError(f"Mensagem com ID '{message_id}' não encontrada na quarentena.")
        return msg

    def get_poison_pill_stats(self, queue: Optional[str] = None) -> Dict[str, Any]:
        logger.info("Buscando estatísticas de poison pills via serviço", queue=queue)
        return self._pp_handler.get_failure_stats(queue=queue)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Coleta e retorna um resumo de métricas chave de múltiplos componentes."""
        logger.info("Coletando resumo de métricas do sistema via serviço.")
        try:
            # LLM metrics
            llm_stats = {
                "cached_llms": len(_llm_cache),
                "circuit_breakers": {
                    provider: {"state": cb.state.value, "failure_count": cb.failure_count}
                    for provider, cb in _provider_circuit_breakers.items()
                }
            }

            # Multi-agent metrics
            ma_system = get_multi_agent_system()
            ma_stats = {
                "active_agents": len(ma_system.agents),
                "workspace_tasks": len(ma_system.workspace.tasks),
                "workspace_artifacts": len(ma_system.workspace.artifacts)
            }

            # Poison pill metrics
            pp_stats = self._pp_handler.get_health_status()

            return {
                "llm": llm_stats,
                "multi_agent": ma_stats,
                "poison_pills": pp_stats
            }
        except Exception as e:
            logger.error("Erro no serviço ao gerar resumo de métricas", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar o resumo de métricas.") from e


# Instância única do serviço, injetando as dependências
observability_service = ObservabilityService(
    monitor=get_health_monitor(),
    pp_handler=get_poison_pill_handler()
)
