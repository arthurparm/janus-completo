from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.autonomy.policy_engine import RiskProfile
from app.services.assistant_service import AssistantService, get_assistant_service

router = APIRouter(tags=["Assistant"])
logger = structlog.get_logger(__name__)


class AssistantExecuteRequest(BaseModel):
    prompt: str = Field(..., description="Solicitação do usuário (pedido livre)")
    risk_profile: str | None = Field(
        RiskProfile.BALANCED, description="Perfil de risco: conservative, balanced, aggressive"
    )
    allowlist: list[str] | None = Field(
        default=None, description="Ferramentas explicitamente permitidas"
    )
    blocklist: list[str] | None = Field(default=None, description="Ferramentas a bloquear")
    max_steps: int | None = Field(default=8, ge=1, le=20, description="Máximo de passos planejados")
    timeout_seconds: int | None = Field(
        default=30, ge=5, le=120, description="Timeout para planejamento"
    )


class AssistantExecutionResult(BaseModel):
    request: str
    planned_steps: list[dict[str, Any]]
    transparent: list[dict[str, Any]]
    executions: list[dict[str, Any]]
    consolidated_output: str
    telemetry: dict[str, Any]


@router.post(
    "/assistant/execute",
    response_model=AssistantExecutionResult,
    summary="Executa pedido com seleção automática de ferramentas",
)
async def assistant_execute(
    body: AssistantExecuteRequest, assistant: AssistantService = Depends(get_assistant_service)
):
    try:
        result = await assistant.execute_request(
            user_request=body.prompt,
            risk_profile=body.risk_profile or RiskProfile.BALANCED,
            allowlist=body.allowlist,
            blocklist=body.blocklist,
            max_steps=body.max_steps or 8,
            timeout_seconds=body.timeout_seconds or 30,
            metrics={},
        )
        return result
    except Exception as e:
        logger.error("Falha na execução automática de ferramentas", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
