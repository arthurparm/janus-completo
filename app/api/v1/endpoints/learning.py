from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
import structlog

from app.services.learning_service import (
    LearningService,
    get_learning_service,
    LearningServiceError,
    ModelNotFoundError,
    TrainingFailedError
)

router = APIRouter(prefix="/learning", tags=["Learning"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class HarvestRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000)

class TrainingConfig(BaseModel):
    epochs: int = Field(3, ge=1, le=100)
    batch_size: int = Field(8, ge=1, le=128)
    learning_rate: float = Field(1e-4, ge=1e-5, le=0.1)

class TrainRequest(BaseModel):
    model_type: str = Field("CLASSIFIER")
    training_config: TrainingConfig = Field(default_factory=TrainingConfig)

class LearningResponse(BaseModel):
    message: str
    summary: str
    model_id: Optional[str] = None

class TrainingStatusResponse(BaseModel):
    is_training: bool
    current_model: Optional[str] = None
    progress: float = 0.0

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


# --- Endpoints ---

@router.post("/harvest", response_model=LearningResponse, summary="Inicia a coleta de dados para treino")
async def trigger_harvesting(request: HarvestRequest,
                             learning_service: LearningService = Depends(get_learning_service)):
    """Delega a coleta de dados de experiência para o LearningService."""
    try:
        result = await learning_service.trigger_harvesting(limit=request.limit)
        return result
    except LearningServiceError as e:
        logger.error("Erro no serviço de aprendizado ao coletar dados", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/train", response_model=LearningResponse, summary="Inicia o treino de um novo modelo")
async def trigger_training(request: TrainRequest, learning_service: LearningService = Depends(get_learning_service)):
    """Delega o processo de treinamento de modelo para o LearningService."""
    try:
        result = await learning_service.trigger_training(request.model_type, request.training_config.dict())
        return result
    except TrainingFailedError as e:
        logger.warning("Falha no treinamento via serviço", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LearningServiceError as e:
        logger.error("Erro no serviço de aprendizado ao treinar modelo", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/training/status", response_model=TrainingStatusResponse, summary="Obtém status do treinamento atual")
async def get_training_status(learning_service: LearningService = Depends(get_learning_service)):
    """Busca o status de qualquer sessão de treinamento ativa via LearningService."""
    session = learning_service.get_training_status()
    if session:
        return TrainingStatusResponse(is_training=True, **session)
    return TrainingStatusResponse(is_training=False)


@router.get("/models", response_model=ModelListResponse, summary="Lista todos os modelos treinados")
async def list_models(learning_service: LearningService = Depends(get_learning_service)):
    """Delega a listagem de modelos para o LearningService."""
    models = learning_service.list_all_models()
    return ModelListResponse(total=len(models), models=models)


@router.get("/models/{model_id}", response_model=ModelInfo, summary="Obtém detalhes de um modelo")
async def get_model_details(model_id: str, learning_service: LearningService = Depends(get_learning_service)):
    """Delega a busca de detalhes de um modelo para o LearningService."""
    try:
        return learning_service.get_model_details(model_id)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats", summary="Obtém estatísticas do sistema de treinamento")
async def get_learning_stats(learning_service: LearningService = Depends(get_learning_service)):
    """Delega a busca de estatísticas para o LearningService."""
    return learning_service.get_learning_statistics()


@router.get("/health", summary="Health check do sistema de treinamento")
async def learning_health(learning_service: LearningService = Depends(get_learning_service)):
    """Delega a verificação de saúde para o LearningService."""
    return learning_service.get_health_status()
