"""
API endpoints para observabilidade e resiliência (Sprint 12).
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.health_monitor import get_health_monitor
from app.core.poison_pill_handler import get_poison_pill_handler

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Schemas ---

class ReleaseQuarantineRequest(BaseModel):
    message_id: str
    allow_retry: bool = False


# --- Endpoints ---

@router.get("/health/system")
async def get_system_health():
    """
    Retorna visão agregada da saúde de todos os componentes do sistema.

    Inclui:
    - Status geral (healthy/degraded/unhealthy)
    - Score de saúde (0-100)
    - Status individual de cada componente
    """
    try:
        monitor = get_health_monitor()
        return monitor.get_system_health()
    except Exception as e:
        logger.error(f"Erro ao obter saúde do sistema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/components/{component}")
async def check_component_health(component: str):
    """
    Executa health check de um componente específico.
    """
    try:
        monitor = get_health_monitor()
        result = await monitor.check_component(component)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Erro ao verificar componente {component}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/check-all")
async def check_all_components():
    """
    Força execução imediata de health checks em todos os componentes.
    """
    try:
        monitor = get_health_monitor()
        results = await monitor.check_all_components()
        return {
            "total_components": len(results),
            "results": {name: r.to_dict() for name, r in results.items()}
        }
    except Exception as e:
        logger.error(f"Erro ao executar health checks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poison-pills/quarantined")
async def get_quarantined_messages(queue: Optional[str] = None):
    """
    Retorna mensagens em quarentena.

    Query params:
    - queue: Filtrar por fila específica
    """
    try:
        handler = get_poison_pill_handler()
        messages = handler.get_quarantined_messages(queue=queue)

        return {
            "total_quarantined": len(messages),
            "messages": [
                {
                    "message_id": msg.message_id,
                    "queue": msg.queue,
                    "reason": msg.reason,
                    "failure_count": msg.failure_record.failure_count,
                    "quarantined_at": msg.quarantined_at.isoformat(),
                    "first_failure": msg.failure_record.first_failure.isoformat(),
                    "last_failure": msg.failure_record.last_failure.isoformat()
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Erro ao obter mensagens em quarentena: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poison-pills/release")
async def release_from_quarantine(request: ReleaseQuarantineRequest):
    """
    Remove uma mensagem da quarentena.

    Útil para liberar manualmente mensagens após correção do problema.
    """
    try:
        handler = get_poison_pill_handler()
        msg = handler.release_from_quarantine(
            request.message_id,
            allow_retry=request.allow_retry
        )

        if not msg:
            raise HTTPException(
                status_code=404,
                detail=f"Mensagem {request.message_id} não encontrada em quarentena"
            )

        return {
            "message": "Mensagem liberada da quarentena",
            "message_id": msg.message_id,
            "queue": msg.queue,
            "allow_retry": request.allow_retry
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao liberar mensagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poison-pills/cleanup")
async def cleanup_expired_quarantine():
    """
    Remove mensagens expiradas da quarentena.

    Mensagens que ultrapassaram o tempo de quarentena são automaticamente liberadas.
    """
    try:
        handler = get_poison_pill_handler()
        removed_count = handler.cleanup_expired_quarantine()

        return {
            "message": "Limpeza de quarentena concluída",
            "removed_count": removed_count
        }
    except Exception as e:
        logger.error(f"Erro ao limpar quarentena: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/poison-pills/stats")
async def get_poison_pill_stats(queue: Optional[str] = None):
    """
    Retorna estatísticas de poison pills.

    Query params:
    - queue: Filtrar por fila específica
    """
    try:
        handler = get_poison_pill_handler()
        stats = handler.get_failure_stats(queue=queue)
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    Retorna resumo de métricas chave do sistema.

    Agrega métricas de:
    - LLM usage
    - Circuit breakers
    - Multi-agent tasks
    - Poison pills
    """
    try:
        from app.core.llm_manager import _provider_circuit_breakers, _llm_cache
        from app.core.multi_agent_system import get_multi_agent_system

        # LLM metrics
        llm_stats = {
            "cached_llms": len(_llm_cache),
            "circuit_breakers": {
                provider: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count
                }
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
        pp_handler = get_poison_pill_handler()
        pp_stats = pp_handler.get_health_status()

        return {
            "timestamp": "now",
            "llm": llm_stats,
            "multi_agent": ma_stats,
            "poison_pills": pp_stats
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo de métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
