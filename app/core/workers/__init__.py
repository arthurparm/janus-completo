"""
Módulo de workers - Workers assíncronos e tarefas em background.
"""
from .async_consolidation_worker import publish_consolidation_task
from .data_harvester import DataHarvester
from .knowledge_consolidator_worker import KnowledgeConsolidator, knowledge_consolidator
from .neural_trainer import start_training_process
from .neural_training_system import NeuralTrainer, neural_trainer

__all__ = [
    "publish_consolidation_task",
    "KnowledgeConsolidator",
    "knowledge_consolidator",
    "DataHarvester",
    "NeuralTrainer",
    "neural_trainer",
    "start_training_process"
]
