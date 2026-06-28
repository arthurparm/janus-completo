import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.security.request_guard import require_authenticated_actor_id
from app.services.sandbox_service import SandboxService, get_sandbox_service

router = APIRouter(tags=["Sandbox"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="Código Python a ser executado")
    context: dict = Field(default={}, description="Variáveis de contexto adicionais")


class ExpressionRequest(BaseModel):
    expression: str = Field(..., description="Expressão Python a ser avaliada")


# --- Endpoints ---


@router.post("/execute", summary="Executa código Python no sandbox")
async def execute_code(
    body: CodeExecutionRequest, request: Request, service: SandboxService = Depends(get_sandbox_service)
):
    require_authenticated_actor_id(request)
    result = service.execute_code(body.code, context=body.context)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "execution_time": result.execution_time,
        "variables": {k: str(v) for k, v in (result.variables or {}).items()}
        if result.variables
        else {},
    }


@router.post("/evaluate", summary="Avalia uma expressão Python")
async def evaluate_expression(
    body: ExpressionRequest, request: Request, service: SandboxService = Depends(get_sandbox_service)
):
    require_authenticated_actor_id(request)
    result = service.evaluate_expression(body.expression)
    return {
        "success": result.success,
        "result": result.output if result.success else None,
        "error": result.error,
        "execution_time": result.execution_time,
    }


@router.get("/capabilities", summary="Lista capacidades do sandbox")
async def get_sandbox_capabilities(service: SandboxService = Depends(get_sandbox_service)):
    """Retorna informações sobre as capacidades e restrições do sandbox."""
    return service.get_capabilities()
