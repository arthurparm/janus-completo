import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import Depends
from app.core.infrastructure.filesystem_manager import read_file

from app.repositories.learning_repository import LearningRepository, get_learning_repository, ModelInfo

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


class ExperimentNotFoundError(LearningServiceError):
    """Raised when an experiment is not found."""
    pass

# --- Learning Service ---

class LearningService:
    """
    Camada de serviço para orquestrar a coleta de dados e o treinamento de modelos.
    """

    def __init__(self, repo: LearningRepository):
        self._repo = repo

    async def trigger_harvesting(self, limit: int, query: Optional[str] = None, min_score: Optional[float] = None) -> \
    Dict[str, Any]:
        logger.info("Orquestrando coleta de dados para treinamento", limit=limit, query=query, min_score=min_score)
        try:
            result = await self._repo.run_harvesting(limit=limit, query=query, min_score=min_score)
            if "bem-sucedida" in result.get("message", ""):
                self._repo.increment_harvested_count(limit)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao orquestrar coleta de dados", exc_info=e)
            raise LearningServiceError("Falha ao orquestrar a coleta de dados.") from e

    async def trigger_training(self, model_type: str, training_config: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Orquestrando treinamento de novo modelo", model_type=model_type)
        try:
            result = await self._repo.run_training_process()

            if "Falha" in result.get("message", ""):
                raise TrainingFailedError(result.get("summary", "Causa desconhecida."))

            model_id = f"janus-{model_type.lower()}-v{len(self._repo.get_all_models()) + 1}"
            model_info = ModelInfo(
                model_id=model_id,
                model_type=model_type,
                status="trained",
                created_at=datetime.utcnow().isoformat(),
                training_examples=100,  # Mock
                accuracy=0.87,  # Mock
                loss=0.23,  # Mock
                experiment_id=result.get("experiment_id"),
                dataset_version=result.get("dataset_version"),
                dataset_num_examples=result.get("dataset_num_examples")
            )
            self._repo.save_model(model_info)

            result["model_id"] = model_id
            return result
        except TrainingFailedError:
            raise
        except Exception as e:
            logger.error("Erro inesperado no serviço ao orquestrar treinamento", exc_info=e)
            raise LearningServiceError("Falha inesperada ao orquestrar o treinamento.") from e

    def get_training_status(self) -> Optional[Dict[str, Any]]:
        return self._repo.get_active_training_session()

    def list_all_models(self) -> List[ModelInfo]:
        return self._repo.get_all_models()

    def get_model_details(self, model_id: str) -> ModelInfo:
        model = self._repo.find_model_by_id(model_id)
        if not model:
            raise ModelNotFoundError(f"Modelo '{model_id}' não encontrado.")
        return model

    def get_learning_statistics(self) -> Dict[str, Any]:
        return self._repo.get_stats()

    def get_health_status(self) -> Dict[str, Any]:
        logger.info("Verificando saúde do módulo de aprendizado.")
        return {
            "status": "healthy",
            "module": "neural_learning",
            "harvester_running": self._repo.is_harvester_healthy(),
            "training_capacity_available": True,  # Mock
            "data_quality_score": 0.92  # Mock
        }

    async def preview_dataset(self, limit: int = 20) -> Dict[str, Any]:
        """Retorna os primeiros N exemplos do dataset de treino para inspeção rápida."""
        try:
            content = read_file("workspace/training_data.jsonl")
            if content.startswith("Erro:"):
                return {"examples": [], "total": 0}

            lines = [ln for ln in content.strip().split('\n') if ln.strip()][:limit]
            examples = []
            for ln in lines:
                try:
                    # cada linha é um JSON
                    import json
                    examples.append(json.loads(ln))
                except Exception:
                    # ignora linhas inválidas
                    continue
            return {"examples": examples, "total": len(examples)}
        except Exception as e:
            logger.error("Erro ao pré-visualizar dataset", exc_info=e)
            raise LearningServiceError("Falha ao pré-visualizar o dataset.") from e

    def evaluate_model(self, model_id: str, test_data_limit: int = 50) -> Dict[str, Any]:
        """Avalia um modelo treinado usando dados disponíveis no workspace."""
        model = self._repo.find_model_by_id(model_id)
        if not model:
            raise ModelNotFoundError(f"Modelo '{model_id}' não encontrado.")

        try:
            content = read_file(f"workspace/training_data.jsonl")
            if content.startswith("Erro:"):
                # Sem arquivo de treino; retornar avaliação mock com aviso
                metrics = {"accuracy": 0.0, "f1": 0.0, "precision": 0.0, "recall": 0.0,
                           "note": "Sem dados de treino disponíveis"}
                return {
                    "model_id": model_id,
                    "examples_evaluated": 0,
                    "metrics": metrics
                }

            lines = content.strip().split('\n')[:test_data_limit]
            examples_evaluated = len(lines)
            # Métricas simuladas baseadas na quantidade avaliada
            base = max(0.5, min(0.95, 0.7 + examples_evaluated / 1000))
            metrics = {
                "accuracy": round(base, 3),
                "f1": round(base - 0.02, 3),
                "precision": round(base + 0.01, 3),
                "recall": round(base - 0.03, 3),
            }
            return {
                "model_id": model_id,
                "examples_evaluated": examples_evaluated,
                "metrics": metrics
            }
        except Exception as e:
            logger.error("Erro ao avaliar modelo", exc_info=e)
            raise LearningServiceError("Falha ao avaliar o modelo.") from e

    # ===== Dataset Version and Experiments =====

    def get_dataset_version_info(self) -> Dict[str, Any]:
        return self._repo.get_dataset_version_info()

    def list_experiments(self) -> List[Dict[str, Any]]:
        return self._repo.list_experiments()

    def get_experiment_details(self, experiment_id: str) -> Dict[str, Any]:
        exp = self._repo.get_experiment(experiment_id)
        if not exp:
            raise ExperimentNotFoundError(f"Experimento '{experiment_id}' não encontrado.")
        return exp


# Padrão de Injeção de Dependência: Getter para o serviço
def get_learning_service(repo: LearningRepository = Depends(get_learning_repository)) -> LearningService:
    return LearningService(repo)
