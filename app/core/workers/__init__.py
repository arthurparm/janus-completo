"""
Módulo de workers - Workers assíncronos e tarefas em background.
"""
from .async_consolidation_worker import AsyncConsolidationWorker, get_consolidation_worker
from .knowledge_consolidator_worker import KnowledgeConsolidatorWorker, get_knowledge_consolidator
from .data_harvester import DataHarvester, get_data_harvester
from .neural_trainer import NeuralTrainer, get_neural_trainer
from .neural_training_system import NeuralTrainingSystem, get_neural_training_system

__all__ = [
    "AsyncConsolidationWorker",
    "get_consolidation_worker",
    "KnowledgeConsolidatorWorker",
    "get_knowledge_consolidator",
    "DataHarvester",
    "get_data_harvester",
    "NeuralTrainer",
    "get_neural_trainer",
    "NeuralTrainingSystem",
    "get_neural_training_system"
]
