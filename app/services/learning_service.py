import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from app.repositories.learning_repository import learning_repository, ModelInfo
from app.core.workers import data_harvester
from app.core.workers.neural_trainer import start_training_process

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class LearningServiceError(Exception):
    """Base exception for learning service errors."""
    pass


class ModelNotFoundError(LearningServiceError):
    """Raised when a model is not found."""
    pass


class TrainingFailedError(LearningServiceError):
    """Raised when the training process fails."""
    pass


# --- Learning Service ---

class LearningService:
    """
    Camada de serviço para orquestrar a coleta de dados e o treinamento de modelos.
    """

    async def trigger_harvesting(self, limit: int) -> Dict[str, Any]:
        logger.info("Disparando coleta de dados para treinamento", limit=limit)
        try:
            result = await data_harvester.harvest_data_for_training(limit=limit)
            if "bem-sucedida" in result.get("message", ""):
                learning_repository.increment_harvested_count(limit)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao disparar coleta de dados", exc_info=e)
            raise LearningServiceError("Falha ao disparar a coleta de dados.") from e

    async def trigger_training(self, model_type: str, training_config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Disparando treinamento de novo modelo", model_type=model_type)
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, start_training_process)

            if "Falha" in result.get("message", ""):
                raise TrainingFailedError(result.get("summary", "Causa desconhecida."))

            model_id = f"janus-{model_type.lower()}-v{len(learning_repository.get_all_models()) + 1}"
            model_info = ModelInfo(
                model_id=model_id,
                model_type=model_type,
                status="trained",
                created_at=datetime.utcnow().isoformat(),
                training_examples=100,  # Mock
                accuracy=0.87,  # Mock
                loss=0.23  # Mock
            )
            learning_repository.save_model(model_info)

            result["model_id"] = model_id  # Adiciona o ID do modelo ao resultado
            return result
        except TrainingFailedError:
            raise
        except Exception as e:
            logger.error("Erro inesperado no serviço ao disparar treinamento", exc_info=e)
            raise LearningServiceError("Falha inesperada ao disparar o treinamento.") from e

    def get_training_status(self) -> Optional[Dict[str, Any]]:
        return learning_repository.get_active_training_session()

    def list_all_models(self) -> List[ModelInfo]:
        return learning_repository.get_all_models()

    def get_model_details(self, model_id: str) -> ModelInfo:
        model = learning_repository.find_model_by_id(model_id)
        if not model:
            raise ModelNotFoundError(f"Modelo '{model_id}' não encontrado.")
        return model

    def get_learning_statistics(self) -> Dict[str, Any]:
        return learning_repository.get_stats()

    def get_health_status(self) -> Dict[str, Any]:
        logger.info("Verificando saúde do módulo de aprendizado.")
        harvester_ok = hasattr(data_harvester, 'harvester')
        return {
            "status": "healthy",
            "module": "neural_learning",
            "harvester_running": harvester_ok,
            "training_capacity_available": True,  # Mock
            "data_quality_score": 0.92  # Mock
        }


# Instância única do serviço
learning_service = LearningService()
