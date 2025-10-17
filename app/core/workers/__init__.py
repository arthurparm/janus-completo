"""
Módulo de workers - Workers assíncronos e tarefas em background.
"""
from .async_consolidation_worker import publish_consolidation_task
from .data_harvester import DataHarvester
from .knowledge_consolidator_worker import KnowledgeConsolidator, knowledge_consolidator
from .neural_trainer import start_training_process
from .neural_training_system import NeuralTrainer, neural_trainer
from .agent_tasks_worker import publish_agent_task, start_agent_tasks_worker
from .neural_training_worker import publish_neural_training_task, start_neural_training_worker

__all__ = [
    "publish_consolidation_task",
    "KnowledgeConsolidator",
    "knowledge_consolidator",
    "DataHarvester",
    "NeuralTrainer",
    "neural_trainer",
    "start_training_process",
    "publish_agent_task",
    "start_agent_tasks_worker",
    "publish_neural_training_task",
    "start_neural_training_worker",
]
