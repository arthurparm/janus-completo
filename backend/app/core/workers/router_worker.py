"""
Router Worker (Rececionista)

Consome a fila central JANUS.tasks.router e decide o próximo agente
para o TaskState usando o Planner na decomposição inicial.
"""

import logging
from datetime import datetime

import msgpack

from app.core.autonomy.planner import build_plan_for_goal
from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm.router import ModelPriority, ModelRole, get_llm
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.collaboration_service import CollaborationService

logger = logging.getLogger(__name__)


async def _decompose_complex_task(goal: str) -> str:
    """Usa o prompt task_decomposition para analisar requisições complexas."""
    try:
        llm = await get_llm(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY)
        prompt = await get_formatted_prompt(
            "task_decomposition",
            project_description=goal,
            request=goal,
            context="Nenhum contexto adicional",
            agents="THINKER, CODER, PROFESSOR, SANDBOX, RED_TEAM",
        )
        # Se for rastro LangChain, usar ainvoke ou similar. Aqui simplificamos.
        res = await llm.ainvoke(prompt)
        return res.content
    except Exception as e:
        logger.warning(f"Falha na decomposição de tarefa: {e}")
        return ""


def _infer_first_agent(original_goal: str) -> str:
    """Fallback heurístico para o primeiro agente; prefere 'thinker'."""
    return "thinker"


def _contains_knowledge_payload(state: TaskState) -> bool:
    """Heurística: decide se o TaskState contém conhecimento a ser consolidado."""
    payload = state.data_payload
    tool_text = (payload.tool_output or "").strip()
    sandbox_text = (payload.sandbox_output or "").strip()
    sandbox_err = (payload.sandbox_error or "").strip()
    # Palavras-chave no objetivo original (pt/en)
    goal = (state.original_goal or "").lower()
    goal_kws = [
        "pesquisar",
        "research",
        "buscar",
        "estudar",
        "study",
        "aprender",
        "learn",
        "ler",
        "read",
        "pdf",
        "document",
        "docs",
        "doc",
        "article",
        "artigo",
        "context",
    ]
    goal_match = any(k in goal for k in goal_kws)
    # Conteúdo suficiente vindo de ferramenta/sandbox
    has_tool = len(tool_text) >= 256
    has_sandbox = len(sandbox_text) >= 64 and not sandbox_err
    return has_tool or has_sandbox or goal_match


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_ROUTER.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_router_task(task: TaskMessage) -> None:
    """Processa mensagens de roteamento e encaminha para o próximo agente."""
    try:
        payload = task.payload or {}
        raw_state = payload.get("task_state") or {}
        state = TaskState(**raw_state)

        # Se não há próximo agente definido, inferir o primeiro
        if not state.next_agent_role:
            state.next_agent_role = _infer_first_agent(state.original_goal)
        state.current_agent_role = "router"

        # Nova lógica: se tarefa concluída com conhecimento, encaminhar ao consolidator
        status = (state.status or "").lower()
        success_like = status in ("success", "completed", "done")

        # 1. Knowledge Consolidation (Memory)
        should_consolidate = success_like and _contains_knowledge_payload(state)
        if should_consolidate:
            # Publica tarefa de consolidação em paralelo sem alterar o fluxo principal
            payload = state.data_payload
            content = (
                payload.tool_output or payload.sandbox_output or state.original_goal or ""
            ).strip()
            origin_agent = None
            try:
                for ev in reversed(state.history):
                    ar = ev.get("agent_role")
                    if ar and ar != "router":
                        origin_agent = ar
                        break
            except Exception:
                origin_agent = None
            meta = {
                "source_task_id": state.task_id,
                "original_goal": state.original_goal,
                "origin": "router",
                "source_agent": origin_agent,
                "status": state.status,
                "timestamp": datetime.utcnow().isoformat(),
            }
            side_msg = TaskMessage(
                task_id=state.task_id,
                task_type="knowledge_consolidation",
                payload={
                    "mode": "single",
                    "experience_id": state.task_id,
                    "experience_content": content,
                    "metadata": meta,
                },
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump()
            broker = await get_broker()
            await broker.publish(
                queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
                message=msgpack.packb(side_msg, use_bin_type=True),
                use_msgpack=True,
            )

        # 2. Knowledge Distillation (Fine-Tuning Dataset)
        # Se houve sucesso, enviamos para o DistillationWorker avaliar a qualidade do raciocínio
        if success_like:
            distill_msg = TaskMessage(
                task_id=state.task_id,
                task_type="knowledge_distillation",
                payload={"task_state": state.model_dump()},
                timestamp=datetime.utcnow().timestamp(),
            ).model_dump()

            # Reusando o broker (Singleton)
            broker = await get_broker()
            await broker.publish(
                queue_name=QueueName.TASKS_KNOWLEDGE_DISTILLATION.value,
                message=msgpack.packb(distill_msg, use_bin_type=True),
                use_msgpack=True,
            )

        if should_consolidate:
            route_note = f"next={state.next_agent_role} (memory side-published)"
        else:
            route_note = f"next={state.next_agent_role}"

        # Registrar no histórico
        state.history.append(
            {
                "agent_role": "router",
                "action": "routed",
                "notes": route_note,
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "Router encaminhou TaskState", task_id=state.task_id, next_role=state.next_agent_role
        )
    except Exception as e:
        logger.error(f"Router falhou ao processar TaskState: {e}", exc_info=True)
        raise


async def start_router_worker():
    """Inicia o consumidor da fila central do Router."""
    logger.info("Iniciando Router Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_ROUTER.value,
        callback=process_router_task,
        prefetch_count=10,
    )
    logger.info("✓ Router Worker iniciado.")
    return consumer_task
