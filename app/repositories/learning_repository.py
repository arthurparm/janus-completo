import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime

# Em um sistema de produção, os schemas seriam mais robustos (Pydantic, etc.)
ModelInfo = Dict[str, Any]
TrainingSession = Dict[str, Any]

logger = structlog.get_logger(__name__)


class LearningRepository:
    """
    Camada de Repositório para dados de aprendizado e treinamento.
    Abstrai a lógica de armazenamento (atualmente em memória) dos serviços.
    """

    def __init__(self):
        self._training_sessions: Dict[str, TrainingSession] = {}
        self._trained_models: Dict[str, ModelInfo] = {}
        self._stats = {
            "total_harvested": 0,
            "total_trained": 0,
            "last_harvest": None,
            "last_training": None
        }

    def get_all_models(self) -> List[ModelInfo]:
        logger.info("Buscando todos os modelos treinados.")
        return list(self._trained_models.values())

    def find_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        logger.info("Buscando modelo por ID", model_id=model_id)
        return self._trained_models.get(model_id)

    def save_model(self, model_info: ModelInfo) -> ModelInfo:
        model_id = model_info['model_id']
        logger.info("Salvando novo modelo treinado", model_id=model_id)
        self._trained_models[model_id] = model_info
        self._stats["total_trained"] += 1
        self._stats["last_training"] = datetime.utcnow().isoformat()
        return model_info

    def get_active_training_session(self) -> Optional[TrainingSession]:
        logger.info("Verificando sessões de treinamento ativas.")
        for session in self._training_sessions.values():
            if session.get("status") == "training":
                return session
        return None

    def get_stats(self) -> Dict[str, Any]:
        logger.info("Buscando estatísticas de aprendizado.")
        stats = self._stats.copy()
        stats["active_training_sessions"] = 1 if self.get_active_training_session() else 0
        stats["avg_training_time_minutes"] = 2.5  # Mock
        return stats

    def increment_harvested_count(self, count: int):
        logger.info("Incrementando contagem de dados coletados", count=count)
        self._stats["total_harvested"] += count
        self._stats["last_harvest"] = datetime.utcnow().isoformat()


# Instância única do repositório
learning_repository = LearningRepository()
