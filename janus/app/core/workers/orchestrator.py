"""
Orquestrador de Workers

Centraliza a inicialização de todos os workers e tarefas em background
usando imports lazy para evitar ciclos de importação.
"""

import logging

logger = logging.getLogger(__name__)


async def start_all_workers():
    """
    Inicia todos os workers assíncronos do sistema.
    Retorna a lista de tarefas/consumidores iniciados.
    """
    # Imports lazy para evitar ciclos entre módulos de workers/monitoring
    from app.core.monitoring import start_auto_healer
    from app.core.workers.agent_tasks_worker import start_agent_tasks_worker
    from app.core.workers.async_consolidation_worker import start_consolidation_worker
    from app.core.workers.auto_scaler import start_auto_scaler
    from app.core.workers.autonomy_worker import start_autonomy_worker
    from app.core.workers.code_agent_worker import start_code_agent_worker
    from app.core.workers.google_productivity_worker import start_google_productivity_consumer
    from app.core.workers.meta_agent_worker import (
        start_failure_event_consumer,
        start_meta_agent_worker,
    )
    from app.core.workers.neural_training_worker import start_neural_training_worker
    from app.core.workers.professor_agent_worker import start_professor_agent_worker
    from app.core.workers.reflexion_worker import start_reflexion_worker
    from app.core.workers.router_worker import start_router_worker
    from app.core.workers.sandbox_agent_worker import start_sandbox_agent_worker

    logger.info("Iniciando orquestrador de workers...")

    workers = []

    # Worker de consolidação de conhecimento
    consolidation_worker = await start_consolidation_worker()
    workers.append(consolidation_worker)

    # Worker de tarefas de agente
    agent_worker = await start_agent_tasks_worker()
    workers.append(agent_worker)

    # Worker de treinamento neural
    neural_worker = await start_neural_training_worker()
    workers.append(neural_worker)

    # Worker de Reflexion (consome janus.tasks.reflexion)
    reflexion_worker = await start_reflexion_worker()
    workers.append(reflexion_worker)

    # Worker de ciclo do Meta-Agente
    meta_agent_worker = await start_meta_agent_worker()
    workers.append(meta_agent_worker)

    # Meta-Agent orientado a eventos (consome janus.failure.detected)
    failure_consumer = await start_failure_event_consumer()
    workers.append(failure_consumer)

    # Auto-Scaler de filas (background task)
    auto_scaler_task = await start_auto_scaler()
    workers.append(auto_scaler_task)

    # Auto-Healer de componentes (background task)
    healer_task = await start_auto_healer()
    workers.append(healer_task)

    # === Novos workers do Parlamento ===
    router_task = await start_router_worker()
    workers.append(router_task)

    code_agent_task = await start_code_agent_worker()
    workers.append(code_agent_task)

    professor_agent_task = await start_professor_agent_worker()
    workers.append(professor_agent_task)

    sandbox_agent_task = await start_sandbox_agent_worker()
    workers.append(sandbox_agent_task)

    # AutonomyWorker (batimento cardíaco de intenção)
    autonomy_task = await start_autonomy_worker()
    workers.append(autonomy_task)

    google_productivity_task = await start_google_productivity_consumer()
    workers.append(google_productivity_task)

    logger.info(f"✓ {len(workers)} workers iniciados pelo orquestrador.")
    return workers
