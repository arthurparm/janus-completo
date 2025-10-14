import structlog
from typing import Dict, Any, List, Optional
from fastapi import Depends

from app.core.monitoring import get_health_monitor, HealthMonitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler, PoisonPillHandler, QuarantinedMessage

logger = structlog.get_logger(__name__)


class ObservabilityRepositoryError(Exception):
    """Base exception for observability repository errors."""
    pass


class ObservabilityRepository:
    """
    Camada de Repositório para Observabilidade.
    Abstrai todas as interações diretas com os monitores de saúde e handlers de poison pill.
    """

    def __init__(self, monitor: HealthMonitor, pp_handler: PoisonPillHandler):
        self._monitor = monitor
        self._pp_handler = pp_handler

    async def get_system_health(self) -> Dict[str, Any]:
        logger.debug("Buscando saúde agregada do sistema via repositório.")
        try:
            return self._monitor.get_system_health()
        except Exception as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> Dict[str, Dict[str, Any]]:
        logger.debug("Disparando health check de todos os componentes via repositório.")
        try:
            results = await self._monitor.check_all_components()
            return {name: r.to_dict() for name, r in results.items()}
        except Exception as e:
            logger.error("Erro no repositório ao executar health checks", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao executar os health checks.") from e

    def get_quarantined_messages(self, queue: Optional[str] = None) -> List[QuarantinedMessage]:
        logger.debug("Buscando mensagens em quarentena via repositório", queue=queue)
        return self._pp_handler.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.debug("Liberando mensagem da quarentena via repositório", message_id=message_id)
        msg = self._pp_handler.release_from_quarantine(message_id, allow_retry)
        if not msg:
            raise ObservabilityRepositoryError(f"Mensagem com ID '{message_id}' não encontrada na quarentena.")
        return msg

    def get_poison_pill_stats(self, queue: Optional[str] = None) -> Dict[str, Any]:
        logger.debug("Buscando estatísticas de poison pills via repositório", queue=queue)
        return self._pp_handler.get_failure_stats(queue=queue)

    def get_metrics_summary(self) -> Dict[str, Any]:
        logger.debug("Coletando resumo de métricas do sistema via repositório.")
        from app.core.llm import _provider_circuit_breakers, _llm_cache
        from app.core.agents import get_multi_agent_system

        llm_stats = {
            "cached_llms": len(_llm_cache),
            "circuit_breakers": {
                provider: {"state": cb.state.value, "failure_count": cb.failure_count}
                for provider, cb in _provider_circuit_breakers.items()
            }
        }

        ma_system = get_multi_agent_system()
        ma_stats = {
            "active_agents": len(ma_system.agents),
            "workspace_tasks": len(ma_system.workspace.tasks),
            "workspace_artifacts": len(ma_system.workspace.artifacts)
        }

        pp_stats = self._pp_handler.get_health_status()

        return {
            "llm": llm_stats,
            "multi_agent": ma_stats,
            "poison_pills": pp_stats
        }


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

async def get_observability_repository(
        monitor: HealthMonitor = Depends(get_health_monitor),
        pp_handler: PoisonPillHandler = Depends(get_poison_pill_handler)
) -> ObservabilityRepository:
    return ObservabilityRepository(monitor, pp_handler)
