import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.sandbox_service import sandbox_service, SandboxError, InvalidInputError

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class CodeExecutionRequest(BaseModel):
    code: str = Field(..., description="Código Python a ser executado")
    context: dict = Field(default={}, description="Variáveis de contexto adicionais")

class ExpressionRequest(BaseModel):
    expression: str = Field(..., description="Expressão Python a ser avaliada")


# --- Endpoints ---

@router.post("/execute", summary="Executa código Python no sandbox", tags=["Sandbox"])
async def execute_code(request: CodeExecutionRequest):
    """Delega a execução de código de forma segura para o SandboxService."""
    try:
        result = sandbox_service.execute_code(request.code, context=request.context)
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "variables": {k: str(v) for k, v in (result.variables or {}).items()} if result.variables else {}
        }
    except InvalidInputError as e:
        logger.warning("Entrada inválida para execução de código", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SandboxError as e:
        logger.error("Erro no serviço de sandbox ao executar código", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/evaluate", summary="Avalia uma expressão Python", tags=["Sandbox"])
async def evaluate_expression(request: ExpressionRequest):
    """Delega a avaliação de uma expressão para o SandboxService."""
    try:
        result = sandbox_service.evaluate_expression(request.expression)
        return {
            "success": result.success,
            "result": result.output if result.success else None,
            "error": result.error,
            "execution_time": result.execution_time
        }
    except InvalidInputError as e:
        logger.warning("Entrada inválida para avaliação de expressão", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SandboxError as e:
        logger.error("Erro no serviço de sandbox ao avaliar expressão", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/capabilities", summary="Lista capacidades do sandbox", tags=["Sandbox"])
async def get_sandbox_capabilities():
    """Retorna informações sobre as capacidades e restrições do sandbox."""
    # Esta lógica é simples e pode permanecer aqui, mas por consistência,
    # delegamos para o serviço.
    return sandbox_service.get_capabilities()
