"""
Pacote de workers: mantenha importações explícitas por módulo.

Evite reexportar funções/classes de workers neste __init__ para reduzir acoplamento
entre módulos e minimizar risco de importações cíclicas.

Use importações diretas dos módulos, por exemplo:
- from app.core.workers.agent_tasks_worker import start_agent_tasks_worker
- from app.core.workers.neural_training_worker import publish_neural_training_task
- from app.core.workers.meta_agent_worker import start_meta_agent_worker
- from app.core.workers.auto_scaler import start_auto_scaler
- from app.core.workers.async_consolidation_worker import publish_consolidation_task

Para iniciar todos os workers de forma centralizada, utilize o orquestrador:
- from app.core.workers.orchestrator import start_all_workers
"""

# Reexporta apenas o orquestrador central para conveniência
from .orchestrator import start_all_workers

__all__ = [
    "start_all_workers",
]
