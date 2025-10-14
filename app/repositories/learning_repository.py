import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from fastapi import Depends

from app.core.workers import data_harvester
from app.core.workers.neural_trainer import start_training_process

ModelInfo = Dict[str, Any]
TrainingSession = Dict[str, Any]

logger = structlog.get_logger(__name__)

class LearningRepository:
    """
    Camada de Repositório para dados de aprendizado e treinamento.
    Abstrai a lógica de armazenamento e a execução de workers.
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
        return list(self._trained_models.values())

    def find_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        return self._trained_models.get(model_id)

    def save_model(self, model_info: ModelInfo) -> ModelInfo:
        model_id = model_info['model_id']
        self._trained_models[model_id] = model_info
        self._stats["total_trained"] += 1
        self._stats["last_training"] = datetime.utcnow().isoformat()
        return model_info

    def get_active_training_session(self) -> Optional[TrainingSession]:
        for session in self._training_sessions.values():
            if session.get("status") == "training":
                return session
        return None

    def get_stats(self) -> Dict[str, Any]:
        stats = self._stats.copy()
        stats["active_training_sessions"] = 1 if self.get_active_training_session() else 0
        stats["avg_training_time_minutes"] = 2.5  # Mock
        return stats

    def increment_harvested_count(self, count: int):
        self._stats["total_harvested"] += count
        self._stats["last_harvest"] = datetime.utcnow().isoformat()

    async def run_training_process(self) -> Dict[str, Any]:
        """Abstrai a execução da tarefa de treinamento síncrona."""
        logger.debug("Executando processo de treinamento síncrono via repositório.")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, start_training_process)

    async def run_harvesting(self, limit: int) -> Dict[str, Any]:
        """Abstrai a execução do worker de coleta de dados."""
        logger.debug("Executando coleta de dados via repositório.")
        return await data_harvester.harvest_data_for_training(limit=limit)

    def is_harvester_healthy(self) -> bool:
        """Verifica a saúde do worker de coleta de dados."""
        return hasattr(data_harvester, 'harvester')


# Padrão de Injeção de Dependência: Getter para o repositório
def get_learning_repository() -> LearningRepository:
    return LearningRepository()
