import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.meta_agent_service import MetaAgentService, get_meta_agent_service

router = APIRouter(prefix="/meta-agent", tags=["Meta-Agent"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class StartHeartbeatRequest(BaseModel):
    interval_minutes: int = 60

# --- Endpoints ---

@router.post("/analyze", summary="Força a execução de um ciclo de análise do Meta-Agente")
async def run_analysis(service: MetaAgentService = Depends(get_meta_agent_service)):
    """Delega a execução do ciclo de análise para o MetaAgentService."""
    # MetaAgentServiceError é tratado pelo exception handler central -> 500
    report = await service.run_analysis_cycle()
    return {"message": "Análise concluída com sucesso", "report": report.to_dict()}

@router.get("/report/latest", summary="Retorna o último relatório de saúde do sistema")
async def get_latest_report(service: MetaAgentService = Depends(get_meta_agent_service)):
    """Delega a busca do último relatório para o MetaAgentService."""
    report = service.get_latest_report()
    if not report:
        return {"message": "Nenhum relatório disponível ainda", "report": None}
    return {"message": "Relatório recuperado com sucesso", "report": report.to_dict()}

@router.post("/heartbeat/start", summary="Inicia o ciclo de vida proativo (heartbeat) do Meta-Agente")
async def start_heartbeat(
        request: StartHeartbeatRequest,
        service: MetaAgentService = Depends(get_meta_agent_service)
):
    """Delega o início do heartbeat para o MetaAgentService."""
    was_started = await service.start_heartbeat(request.interval_minutes)
    if not was_started:
        return {"message": "Heartbeat já está ativo", "interval_minutes": request.interval_minutes}
    return {"message": "Heartbeat iniciado com sucesso", "interval_minutes": request.interval_minutes}

@router.post("/heartbeat/stop", summary="Para o heartbeat do Meta-Agente")
async def stop_heartbeat(service: MetaAgentService = Depends(get_meta_agent_service)):
    """Delega a parada do heartbeat para o MetaAgentService."""
    service.stop_heartbeat()
    return {"message": "Heartbeat parado com sucesso"}

@router.get("/heartbeat/status", summary="Retorna o status do heartbeat")
async def get_heartbeat_status(service: MetaAgentService = Depends(get_meta_agent_service)):
    """Delega a busca do status do heartbeat para o MetaAgentService."""
    return service.get_heartbeat_status()

@router.get("/health", summary="Health check do Meta-Agente")
async def health_check(service: MetaAgentService = Depends(get_meta_agent_service)):
    """Delega a verificação de saúde do meta-agente para o MetaAgentService."""
    return service.get_health_status()
