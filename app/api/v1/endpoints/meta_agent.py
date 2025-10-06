"""
API endpoints para o Meta-Agente de Auto-Otimização (Sprint 13).
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.agents import get_meta_agent

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Schemas ---

class StartHeartbeatRequest(BaseModel):
    interval_minutes: int = 60


# --- Endpoints ---

@router.post("/analyze")
async def run_analysis():
    """
    Força execução imediata de um ciclo de análise do Meta-Agente.

    O Meta-Agente:
    1. Analisa a saúde de todos os componentes
    2. Busca padrões de falha na memória episódica
    3. Avalia uso de recursos
    4. Identifica problemas e gera recomendações
    """
    try:
        meta_agent = get_meta_agent()
        report = await meta_agent.run_analysis_cycle()

        return {
            "message": "Análise concluída com sucesso",
            "report": report.to_dict()
        }

    except Exception as e:
        logger.error(f"Erro ao executar análise: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/latest")
async def get_latest_report():
    """
    Retorna o relatório de estado mais recente do Meta-Agente.

    Inclui:
    - Status geral do sistema
    - Health score (0-100)
    - Problemas detectados
    - Recomendações de melhoria
    - Resumo executivo
    """
    try:
        meta_agent = get_meta_agent()

        if not meta_agent.last_report:
            return {
                "message": "Nenhum relatório disponível ainda",
                "report": None
            }

        return {
            "message": "Relatório recuperado com sucesso",
            "report": meta_agent.last_report.to_dict()
        }

    except Exception as e:
        logger.error(f"Erro ao obter relatório: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat/start")
async def start_heartbeat(request: StartHeartbeatRequest):
    """
    Inicia o ciclo de vida proativo do Meta-Agente (heartbeat).

    O Meta-Agente executará análises automaticamente no intervalo especificado.

    Args:
        interval_minutes: Intervalo entre análises (padrão: 60 minutos)
    """
    try:
        meta_agent = get_meta_agent()

        if meta_agent._heartbeat_task and not meta_agent._heartbeat_task.done():
            return {
                "message": "Heartbeat já está ativo",
                "interval_minutes": request.interval_minutes
            }

        await meta_agent.start_heartbeat(interval_minutes=request.interval_minutes)

        return {
            "message": "Heartbeat iniciado com sucesso",
            "interval_minutes": request.interval_minutes,
            "status": "active"
        }

    except Exception as e:
        logger.error(f"Erro ao iniciar heartbeat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat/stop")
async def stop_heartbeat():
    """
    Para o heartbeat do Meta-Agente.

    O Meta-Agente deixará de executar análises automáticas.
    """
    try:
        meta_agent = get_meta_agent()
        meta_agent.stop_heartbeat()

        return {
            "message": "Heartbeat parado com sucesso",
            "status": "stopped"
        }

    except Exception as e:
        logger.error(f"Erro ao parar heartbeat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heartbeat/status")
async def get_heartbeat_status():
    """
    Retorna o status do heartbeat do Meta-Agente.
    """
    try:
        meta_agent = get_meta_agent()

        is_active = (
                meta_agent._heartbeat_task is not None and
                not meta_agent._heartbeat_task.done()
        )

        return {
            "heartbeat_active": is_active,
            "total_cycles_executed": meta_agent.cycle_count,
            "last_analysis": (
                meta_agent.last_report.timestamp.isoformat()
                if meta_agent.last_report
                else None
            )
        }

    except Exception as e:
        logger.error(f"Erro ao obter status do heartbeat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_meta_agent_stats():
    """
    Retorna estatísticas do Meta-Agente.

    Inclui métricas sobre ciclos executados, problemas detectados, etc.
    """
    try:
        meta_agent = get_meta_agent()

        stats = {
            "total_cycles": meta_agent.cycle_count,
            "heartbeat_active": (
                    meta_agent._heartbeat_task is not None and
                    not meta_agent._heartbeat_task.done()
            ),
            "last_report_summary": None
        }

        if meta_agent.last_report:
            stats["last_report_summary"] = {
                "cycle_id": meta_agent.last_report.cycle_id,
                "timestamp": meta_agent.last_report.timestamp.isoformat(),
                "status": meta_agent.last_report.overall_status,
                "health_score": meta_agent.last_report.health_score,
                "issues_count": len(meta_agent.last_report.issues_detected),
                "recommendations_count": len(meta_agent.last_report.recommendations)
            }

        return stats

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check do Meta-Agente.
    """
    try:
        meta_agent = get_meta_agent()

        return {
            "status": "healthy",
            "agent_id": meta_agent.agent_id,
            "executor_initialized": meta_agent.executor is not None,
            "tools_count": len(meta_agent.tools),
            "cycles_executed": meta_agent.cycle_count
        }

    except Exception as e:
        logger.error(f"Erro no health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
