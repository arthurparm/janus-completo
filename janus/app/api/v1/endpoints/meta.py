import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.agents.meta_agent import StateReport, get_meta_agent

router = APIRouter()
logger = logging.getLogger(__name__)


class MetaAgentStatusResponse(BaseModel):
    """Resposta com o status atual do Meta-Agente."""

    is_heartbeat_active: bool
    cycle_count: int
    last_report: dict[str, Any] | None


@router.get(
    "/status",
    response_model=MetaAgentStatusResponse,
    summary="Obtém o status e o último relatório do Meta-Agente",
    tags=["Meta-Agent"],
)
def get_status():
    """
    Retorna o status operacional do Meta-Agente, incluindo se seu ciclo
    de 'heartbeat' está ativo e o conteúdo do seu último relatório de estado.
    """
    try:
        meta_agent = get_meta_agent()
        is_active = meta_agent._heartbeat_task is not None and not meta_agent._heartbeat_task.done()
        last_report_dict = meta_agent.last_report.to_dict() if meta_agent.last_report else None
        return MetaAgentStatusResponse(
            is_heartbeat_active=is_active,
            cycle_count=meta_agent.cycle_count,
            last_report=last_report_dict,
        )
    except Exception as e:
        logger.error(f"Erro ao obter status do Meta-Agente: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível recuperar o status do Meta-Agente.",
        )


@router.post(
    "/run-analysis",
    response_model=StateReport,
    summary="Dispara um ciclo de análise do Meta-Agente manualmente",
    tags=["Meta-Agent"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_analysis_cycle():
    """
    Solicita que o Meta-Agente execute um ciclo de análise do sistema sob demanda.
    Esta é uma operação assíncrona. A resposta imediata contém o relatório
    gerado pelo ciclo de análise recém-concluído.
    """
    try:
        meta_agent = get_meta_agent()
        # A execução é assíncrona, mas aguardamos o resultado para este endpoint
        report = await meta_agent.run_analysis_cycle()
        if "error" in report.summary.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Ciclo de análise executado com erro.",
                    "report": report.to_dict(),
                },
            )
        return report
    except Exception as e:
        logger.error(f"Erro ao tentar executar o ciclo do Meta-Agente: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível executar o ciclo de análise.",
        )
