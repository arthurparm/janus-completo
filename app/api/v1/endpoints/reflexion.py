"""
Sprint 5: Endpoint de Reflexion - Auto-otimização e Aprendizado com Erros

Expõe funcionalidades do sistema Reflexion via API REST.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.problem_details import ProblemDetails
from app.core.optimization import run_with_reflexion, ReflexionConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reflexion", tags=["reflexion"])


class ReflexionRequest(BaseModel):
    """Request para executar tarefa com Reflexion."""
    task: str = Field(..., description="Tarefa a ser executada com autocrítica e refinamento", min_length=1)
    max_iterations: Optional[int] = Field(None, description="Número máximo de iterações (padrão: 3)", ge=1, le=10)
    max_time_seconds: Optional[int] = Field(None, description="Tempo máximo em segundos (padrão: 180)", ge=30, le=600)
    success_threshold: Optional[float] = Field(None, description="Score mínimo para sucesso (0.0-1.0, padrão: 0.8)",
                                               ge=0.0, le=1.0)


class ReflexionResponse(BaseModel):
    """Resposta da execução Reflexion."""
    success: bool = Field(..., description="Se a tarefa atingiu o threshold de sucesso")
    best_result: str = Field(..., description="Melhor resultado obtido")
    best_score: float = Field(..., description="Melhor score alcançado (0.0-1.0)")
    iterations: int = Field(..., description="Número de iterações executadas")
    lessons_learned: list[str] = Field(..., description="Lições gerais extraídas do processo")
    elapsed_seconds: float = Field(..., description="Tempo total de execução")
    steps: list[dict] = Field(..., description="Histórico detalhado de todas as iterações")


@router.post(
    "/execute",
    response_model=ReflexionResponse,
    status_code=status.HTTP_200_OK,
    summary="Executa tarefa com Reflexion",
    description=(
            "Executa uma tarefa usando o padrão Reflexion: o agente tenta, avalia criticamente, "
            "reflete sobre erros e tenta novamente com melhorias até atingir sucesso ou limite de iterações."
    )
)
async def execute_with_reflexion(request: ReflexionRequest):
    """
    Executa uma tarefa com o ciclo completo de Reflexion.

    O sistema irá:
    1. Executar a tarefa
    2. Avaliar criticamente o resultado
    3. Refletir sobre o que deu errado
    4. Tentar novamente incorporando os aprendizados
    5. Repetir até atingir sucesso ou limite de iterações
    6. Extrair lições aprendidas para uso futuro

    Exemplo:
    ```json
    {
        "task": "Calcule a média de [10, 20, 30, 40] e explique o método usado",
        "max_iterations": 3,
        "success_threshold": 0.8
    }
    ```
    """
    try:
        logger.info(f"[Reflexion] Iniciando execução para tarefa: {request.task[:100]}...")

        # Monta configuração
        config = ReflexionConfig()
        if request.max_iterations is not None:
            config.max_iterations = request.max_iterations
        if request.max_time_seconds is not None:
            config.max_time_seconds = request.max_time_seconds
        if request.success_threshold is not None:
            config.success_threshold = request.success_threshold

        # Executa Reflexion
        result = run_with_reflexion(
            task=request.task,
            evaluator=None,  # Usa avaliador padrão
            config=config
        )

        logger.info(f"[Reflexion] Concluído: {result['iterations']} iterações, score: {result['best_score']:.2f}")

        return ReflexionResponse(
            success=result["success"],
            best_result=result["best_result"],
            best_score=result["best_score"],
            iterations=result["iterations"],
            lessons_learned=result["lessons_learned"],
            elapsed_seconds=result["elapsed_seconds"],
            steps=result["steps"]
        )

    except ValueError as e:
        logger.warning(f"[Reflexion] Erro de validação: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ProblemDetails(
                type="validation_error",
                title="Entrada Inválida",
                status=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
                instance="/api/v1/reflexion/execute"
            ).model_dump()
        )

    except TimeoutError as e:
        logger.error(f"[Reflexion] Timeout: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=ProblemDetails(
                type="timeout_error",
                title="Tempo Limite Excedido",
                status=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"A execução excedeu o tempo limite: {e}",
                instance="/api/v1/reflexion/execute"
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"[Reflexion] Erro inesperado: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ProblemDetails(
                type="internal_error",
                title="Erro Interno",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao executar Reflexion: {str(e)}",
                instance="/api/v1/reflexion/execute"
            ).model_dump()
        )


@router.get(
    "/config",
    summary="Obtém configuração atual do Reflexion",
    description="Retorna as configurações padrão do sistema Reflexion"
)
async def get_reflexion_config():
    """Retorna a configuração atual do sistema Reflexion."""
    config = ReflexionConfig.from_settings()
    return {
        "max_iterations": config.max_iterations,
        "max_time_seconds": config.max_time_seconds,
        "success_threshold": config.success_threshold
    }


@router.get(
    "/health",
    summary="Verifica saúde do módulo Reflexion",
    description="Endpoint de health check para o sistema de auto-otimização"
)
async def reflexion_health():
    """Health check do módulo Reflexion."""
    try:
        # Verifica se consegue importar módulos necessários
        from app.core.optimization import ReflexionSession
        from app.core.tools import get_faulty_tools

        return {
            "status": "healthy",
            "module": "reflexion",
            "faulty_tools_count": len(get_faulty_tools()),
            "sprint": 5
        }
    except Exception as e:
        logger.error(f"[Reflexion] Health check falhou: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "error": str(e)}
        )
