from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.workers import data_harvester
from app.core.workers.neural_trainer import start_training_process

router = APIRouter()


# ==================== Schemas ====================

class HarvestRequest(BaseModel):
    query: str = Field(default="experiência do agente", description="Query para buscar experiências")
    limit: int = Field(default=100, ge=1, le=1000, description="Número de experiências a coletar")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Score mínimo de relevância")


class TrainingConfig(BaseModel):
    epochs: int = Field(default=3, ge=1, le=100)
    batch_size: int = Field(default=8, ge=1, le=128)
    learning_rate: float = Field(default=0.0001, ge=0.00001, le=0.1)


class TrainRequest(BaseModel):
    model_type: str = Field(default="CLASSIFIER", description="Tipo do modelo: LLM_FINETUNING ou CLASSIFIER")
    training_config: TrainingConfig = TrainingConfig()
    data_source: str = Field(default="episodic_memory", description="Fonte dos dados")


class EvaluateRequest(BaseModel):
    model_id: str = Field(..., description="ID do modelo a avaliar")
    test_data_limit: int = Field(default=50, ge=1, le=500)


class LearningResponse(BaseModel):
    message: str
    summary: str


class TrainingStatusResponse(BaseModel):
    is_training: bool
    current_model: Optional[str] = None
    progress: float = 0.0
    epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    estimated_completion: Optional[str] = None


class ModelInfo(BaseModel):
    model_id: str
    model_type: str
    status: str
    created_at: str
    training_examples: int
    accuracy: Optional[float] = None
    loss: Optional[float] = None


class ModelListResponse(BaseModel):
    total: int
    models: List[ModelInfo]


class EvaluationResult(BaseModel):
    model_id: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    test_samples: int
    timestamp: str


class StatsResponse(BaseModel):
    total_harvested_examples: int
    total_trained_models: int
    active_training_sessions: int
    avg_training_time_minutes: float
    last_harvest: Optional[str] = None
    last_training: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    module: str
    harvester_running: bool
    training_capacity_available: bool
    data_quality_score: Optional[float] = None


# ==================== Storage simulado ====================
# Em produção, usar banco de dados real

_training_sessions: Dict[str, Dict[str, Any]] = {}
_trained_models: Dict[str, ModelInfo] = {}
_stats = {
    "total_harvested": 0,
    "total_trained": 0,
    "last_harvest": None,
    "last_training": None
}


# ==================== Endpoints ====================

@router.post(
    "/harvest",
    response_model=LearningResponse,
    summary="Inicia a coleta de dados de experiência para treino",
    tags=["Neural Learning - Sprint 9"]
)
async def trigger_harvesting(request: HarvestRequest = HarvestRequest()):
    """
    Aciona o 'data_harvester' para recolher experiências da memória
    e prepará-las num ficheiro de dados para treino.
    """
    try:
        # Chama a função async corretamente
        result = await data_harvester.harvest_data_for_training(limit=request.limit)

        # Atualiza stats
        if "bem-sucedida" in result.get("message", ""):
            _stats["total_harvested"] += request.limit
            _stats["last_harvest"] = datetime.utcnow().isoformat()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/train",
    response_model=LearningResponse,
    summary="Inicia o processo de treino de um novo modelo neural",
    tags=["Neural Learning - Sprint 9"]
)
async def trigger_training(request: TrainRequest = TrainRequest()):
    """
    Aciona o 'neural_trainer' para iniciar um processo de treino
    utilizando os dados previamente coletados.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[Learning API] Iniciando treinamento: {request.model_type}")

        # Executa função síncrona em executor
        import asyncio
        loop = asyncio.get_event_loop()

        logger.info("[Learning API] Chamando start_training_process...")
        result = await loop.run_in_executor(None, start_training_process)

        logger.info(f"[Learning API] Resultado do treino: {result}")

        if "Falha" in result["message"]:
            logger.warning(f"[Learning API] Treino falhou: {result['summary']}")
            raise HTTPException(status_code=404, detail=result["summary"])

        # Registra modelo treinado
        model_id = f"janus-{request.model_type.lower()}-v{len(_trained_models) + 1}"
        logger.info(f"[Learning API] Registrando modelo: {model_id}")

        _trained_models[model_id] = ModelInfo(
            model_id=model_id,
            model_type=request.model_type,
            status="trained",
            created_at=datetime.utcnow().isoformat(),
            training_examples=100,  # Mock
            accuracy=0.87 if request.model_type == "CLASSIFIER" else None,
            loss=0.23
        )

        _stats["total_trained"] += 1
        _stats["last_training"] = datetime.utcnow().isoformat()

        logger.info(f"[Learning API] Treino concluído com sucesso: {model_id}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Learning API] ERRO no treinamento: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.get(
    "/training/status",
    response_model=TrainingStatusResponse,
    summary="Obtém status de treinamento em andamento",
    tags=["Neural Learning - Sprint 9"]
)
async def get_training_status():
    """
    Retorna o status atual do treinamento, se houver algum em execução.
    """
    # Mock: verificar se há sessão ativa
    active_sessions = [s for s in _training_sessions.values() if s.get("status") == "training"]

    if active_sessions:
        session = active_sessions[0]
        return TrainingStatusResponse(
            is_training=True,
            current_model=session.get("model_id"),
            progress=session.get("progress", 0.0),
            epoch=session.get("current_epoch"),
            total_epochs=session.get("total_epochs"),
            estimated_completion=session.get("eta")
        )

    return TrainingStatusResponse(
        is_training=False,
        current_model=None
    )


@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="Lista todos os modelos treinados",
    tags=["Neural Learning - Sprint 9"]
)
async def list_models():
    """
    Retorna a lista de todos os modelos treinados disponíveis.
    """
    return ModelListResponse(
        total=len(_trained_models),
        models=list(_trained_models.values())
    )


@router.get(
    "/models/{model_id}",
    response_model=ModelInfo,
    summary="Obtém detalhes de um modelo específico",
    tags=["Neural Learning - Sprint 9"]
)
async def get_model_details(model_id: str):
    """
    Retorna informações detalhadas sobre um modelo treinado.
    """
    if model_id not in _trained_models:
        raise HTTPException(status_code=404, detail=f"Modelo '{model_id}' não encontrado")

    return _trained_models[model_id]


@router.post(
    "/evaluate",
    response_model=EvaluationResult,
    summary="Avalia a performance de um modelo",
    tags=["Neural Learning - Sprint 9"]
)
async def evaluate_model(request: EvaluateRequest):
    """
    Executa avaliação de performance do modelo em dados de teste.
    """
    if request.model_id not in _trained_models:
        raise HTTPException(status_code=404, detail=f"Modelo '{request.model_id}' não encontrado")

    # Mock de avaliação
    return EvaluationResult(
        model_id=request.model_id,
        accuracy=0.87,
        precision=0.85,
        recall=0.89,
        f1_score=0.87,
        test_samples=request.test_data_limit,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Obtém estatísticas do sistema de treinamento",
    tags=["Neural Learning - Sprint 9"]
)
async def get_learning_stats():
    """
    Retorna estatísticas agregadas sobre coleta de dados e treinamento.
    """
    return StatsResponse(
        total_harvested_examples=_stats.get("total_harvested", 0),
        total_trained_models=_stats.get("total_trained", 0),
        active_training_sessions=len([s for s in _training_sessions.values() if s.get("status") == "training"]),
        avg_training_time_minutes=2.5,  # Mock
        last_harvest=_stats.get("last_harvest"),
        last_training=_stats.get("last_training")
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check do sistema de Neural Training",
    tags=["Neural Learning - Sprint 9"]
)
async def learning_health():
    """
    Verifica a saúde do módulo de aprendizagem neural.
    """
    try:
        # Verifica se harvester está funcional
        harvester_ok = hasattr(data_harvester, 'harvester')

        return HealthResponse(
            status="healthy",
            module="neural_learning",
            harvester_running=harvester_ok,
            training_capacity_available=True,
            data_quality_score=0.92
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )
