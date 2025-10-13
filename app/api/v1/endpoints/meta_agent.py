import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.meta_agent_service import meta_agent_service, MetaAgentServiceError

router = APIRouter(prefix="/meta-agent", tags=["Meta-Agent"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class StartHeartbeatRequest(BaseModel):
    interval_minutes: int = 60

# --- Endpoints ---

@router.post("/analyze", summary="Força a execução de um ciclo de análise do Meta-Agente")
async def run_analysis():
    """Delega a execução do ciclo de análise para o MetaAgentService."""
    try:
        report = await meta_agent_service.run_analysis_cycle()
        return {"message": "Análise concluída com sucesso", "report": report.to_dict()}
    except MetaAgentServiceError as e:
        logger.error("Erro no serviço do meta-agente ao executar análise", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/report/latest", summary="Retorna o último relatório de saúde do sistema")
async def get_latest_report():
    """Delega a busca do último relatório para o MetaAgentService."""
    report = meta_agent_service.get_latest_report()
    if not report:
        return {"message": "Nenhum relatório disponível ainda", "report": None}
    return {"message": "Relatório recuperado com sucesso", "report": report.to_dict()}


@router.post("/heartbeat/start", summary="Inicia o ciclo de vida proativo (heartbeat) do Meta-Agente")
async def start_heartbeat(request: StartHeartbeatRequest):
    """Delega o início do heartbeat para o MetaAgentService."""
    try:
        was_started = await meta_agent_service.start_heartbeat(request.interval_minutes)
        if not was_started:
            return {"message": "Heartbeat já está ativo", "interval_minutes": request.interval_minutes}
        return {"message": "Heartbeat iniciado com sucesso", "interval_minutes": request.interval_minutes}
    except MetaAgentServiceError as e:
        logger.error("Erro no serviço ao iniciar heartbeat", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/heartbeat/stop", summary="Para o heartbeat do Meta-Agente")
async def stop_heartbeat():
    """Delega a parada do heartbeat para o MetaAgentService."""
    try:
        meta_agent_service.stop_heartbeat()
        return {"message": "Heartbeat parado com sucesso"}
    except MetaAgentServiceError as e:
        logger.error("Erro no serviço ao parar heartbeat", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/heartbeat/status", summary="Retorna o status do heartbeat")
async def get_heartbeat_status():
    """Delega a busca do status do heartbeat para o MetaAgentService."""
    return meta_agent_service.get_heartbeat_status()


@router.get("/health", summary="Health check do Meta-Agente")
async def health_check():
    """Delega a verificação de saúde do meta-agente para o MetaAgentService."""
    return meta_agent_service.get_health_status()
