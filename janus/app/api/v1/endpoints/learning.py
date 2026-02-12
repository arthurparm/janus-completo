from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.learning_service import (
    ExperimentNotFoundError,
    LearningService,
    LearningServiceError,
    ModelNotFoundError,
    TrainingFailedError,
    get_learning_service,
)

router = APIRouter(tags=["Learning"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---


class HarvestRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000)
    query: str | None = Field(None, description="Consulta para filtrar experiências")
    min_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Pontuação mínima opcional para filtrar"
    )
    user_id: str | None = Field(None, description="Filtrar por usuário (origin)")


class TrainingConfig(BaseModel):
    epochs: int = Field(3, ge=1, le=100)
    batch_size: int = Field(8, ge=1, le=128)
    learning_rate: float = Field(1e-4, ge=1e-5, le=0.1)
    validation_split: float = Field(0.2, ge=0.0, le=0.9)
    early_stopping: bool = True
    save_checkpoints: bool = True
    max_examples: int | None = Field(
        None, ge=1, description="Limite máximo de exemplos para treino"
    )


class TrainRequest(BaseModel):
    model_type: str = Field("CLASSIFIER")
    model_name: str | None = Field(None, description="Nome do modelo a ser treinado")
    training_config: TrainingConfig = Field(default_factory=TrainingConfig)
    user_id: str | None = Field(None)


class LearningResponse(BaseModel):
    message: str
    summary: str
    model_id: str | None = None


class TrainingAckResponse(BaseModel):
    message: str
    summary: str
    task_id: str
    status: str
    queued_at: str
    dataset_version: str | None = None
    dataset_num_examples: int | None = None
    model_name: str | None = None


class TrainingStatusResponse(BaseModel):
    is_training: bool
    current_model: str | None = None
    progress: float = 0.0


class ModelInfo(BaseModel):
    model_id: str
    model_type: str
    status: str
    created_at: str
    training_examples: int
    accuracy: float | None = None
    loss: float | None = None


class ModelListResponse(BaseModel):
    total: int
    models: list[ModelInfo]


class EvaluateRequest(BaseModel):
    model_id: str
    test_data_limit: int = Field(50, ge=1, le=1000)


class EvaluationResponse(BaseModel):
    model_id: str
    examples_evaluated: int
    metrics: dict[str, Any]


class DatasetVersionResponse(BaseModel):
    version: str | None
    num_examples: int
    hash: str | None
    last_modified: str | None


class ExperimentInfo(BaseModel):
    experiment_id: str
    status: str
    dataset_version: str | None = None
    num_examples: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    summary: str | None = None
    error: str | None = None
    duration_seconds: float | None = None


class ExperimentListResponse(BaseModel):
    total: int
    experiments: list[ExperimentInfo]


# --- Endpoints ---


@router.post(
    "/harvest", response_model=LearningResponse, summary="Inicia a coleta de dados para treino"
)
async def trigger_harvesting(
    request: HarvestRequest, learning_service: LearningService = Depends(get_learning_service)
):
    """Delega a coleta de dados de experiência para o LearningService."""
    try:
        result = await learning_service.trigger_harvesting(
            limit=request.limit,
            query=request.query,
            min_score=request.min_score,
            origin=request.user_id,
        )
        return result
    except LearningServiceError as e:
        logger.error("Erro no serviço de aprendizado ao coletar dados", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post(
    "/train", response_model=TrainingAckResponse, summary="Agenda o treino de um novo modelo"
)
async def trigger_training(
    request: TrainRequest, learning_service: LearningService = Depends(get_learning_service)
):
    """Agenda o processo de treinamento de modelo via fila e retorna ack com task_id."""
    try:
        # Injeta data_source na config se fornecido
        config_dict = request.training_config.dict()
        if request.data_source:
            config_dict["data_source"] = request.data_source

        result = await learning_service.trigger_training(
            request.model_type, config_dict, model_name=request.model_name, user_id=request.user_id
        )
        return result
    except TrainingFailedError as e:
        logger.warning("Falha no treinamento via serviço", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LearningServiceError as e:
        logger.error("Erro no serviço de aprendizado ao treinar modelo", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/training/status",
    response_model=TrainingStatusResponse,
    summary="Obtém status do treinamento atual",
)
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
async def get_model_details(
    model_id: str, learning_service: LearningService = Depends(get_learning_service)
):
    """Delega a busca de detalhes de um modelo para o LearningService."""
    try:
        return learning_service.get_model_details(model_id)
    except ModelNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats", summary="Obtém estatísticas do sistema de treinamento")
async def get_learning_stats(learning_service: LearningService = Depends(get_learning_service)):
    """Delega a busca de estatísticas para o LearningService."""
    return learning_service.get_learning_statistics()


@router.get("/dataset/preview", summary="Pré-visualiza exemplos do dataset de treino")
async def preview_dataset(
    limit: int = 20, learning_service: LearningService = Depends(get_learning_service)
):
    """Retorna os primeiros N exemplos do dataset de treino (JSONL)."""
    try:
        return await learning_service.preview_dataset(limit=limit)
    except LearningServiceError as e:
        logger.error("Erro ao pré-visualizar dataset", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post(
    "/evaluate", response_model=EvaluationResponse, summary="Avalia a performance de um modelo"
)
async def evaluate_model(
    request: EvaluateRequest, learning_service: LearningService = Depends(get_learning_service)
):
    """Delega a avaliação de um modelo para o LearningService."""
    try:
        result = learning_service.evaluate_model(request.model_id, request.test_data_limit)
        return result
    except ModelNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except LearningServiceError as e:
        logger.error("Erro no serviço de aprendizado ao avaliar modelo", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get(
    "/dataset/version",
    response_model=DatasetVersionResponse,
    summary="Obtém a versão atual do dataset de treino",
)
async def get_dataset_version(learning_service: LearningService = Depends(get_learning_service)):
    """Retorna metadados de versão do dataset de treino."""
    return learning_service.get_dataset_version_info()


@router.get(
    "/experiments",
    response_model=ExperimentListResponse,
    summary="Lista experimentos de treinamento",
)
async def list_experiments(learning_service: LearningService = Depends(get_learning_service)):
    """Lista os experimentos rastreados pelo repositório de aprendizado."""
    exps = learning_service.list_experiments()
    return ExperimentListResponse(total=len(exps), experiments=exps)


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentInfo,
    summary="Obtém detalhes de um experimento",
)
async def get_experiment_details(
    experiment_id: str, learning_service: LearningService = Depends(get_learning_service)
):
    """Detalhes de um experimento específico."""
    try:
        return learning_service.get_experiment_details(experiment_id)
    except ExperimentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/health", summary="Health check do sistema de treinamento")
async def learning_health(learning_service: LearningService = Depends(get_learning_service)):
    """Verifica a saúde do sistema de treinamento."""
    return learning_service.get_health_status()
