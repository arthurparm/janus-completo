"""
Router Worker (Rececionista)

Consome a fila central JANUS.tasks.router e decide o próximo agente
para o TaskState usando o Planner na decomposição inicial.
"""
import structlog
from datetime import datetime

import msgpack

from app.core.autonomy.taskstate_status import (
    is_success_terminal_status,
    is_terminal_status,
    normalize_task_status,
)
from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm.router import ModelPriority, ModelRole, get_llm
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.collaboration_service import CollaborationService

logger = structlog.get_logger(__name__)


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
        logger.warning("router_task_decomposition_failed", error=str(e))
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

        state.current_agent_role = "router"
        state.status = normalize_task_status(state.status)

        # Router como sink de terminalização: se a tarefa já chegou terminal ao Router,
        # processa side-effects e encerra sem republish para evitar loop.
        router_targeted = (state.next_agent_role or "").lower() == "router"
        terminal = is_terminal_status(state.status)
        if (not state.next_agent_role and terminal) or (router_targeted and terminal):
            state.history.append(
                {
                    "agent_role": "router",
                    "action": "router_terminalized",
                    "notes": f"status={state.status}",
                    "timestamp": datetime.utcnow().timestamp(),
                }
            )
            logger.info(
                "router_terminal_sink",
                task_id=state.task_id,
                status=state.status,
            )
        else:
            # Se não há próximo agente definido, inferir o primeiro
            if not state.next_agent_role:
                state.next_agent_role = _infer_first_agent(state.original_goal)
            # Anti-loop: router não deve se republicar com status não-terminal
            elif router_targeted:
                inferred = _infer_first_agent(state.original_goal)
                logger.warning(
                    "router_next_role_self_loop_corrected",
                    task_id=state.task_id,
                    status=state.status,
                    previous_next_role="router",
                    inferred_next_role=inferred,
                )
                state.next_agent_role = inferred

        # Nova lógica: se tarefa concluída com conhecimento, encaminhar ao consolidator
        success_like = is_success_terminal_status(state.status)

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

        if terminal and ((state.next_agent_role or "").lower() == "router"):
            service = CollaborationService(CollaborationRepository())
            service.maybe_finalize_autonomy_goal(state)
            logger.info(
                "router_terminal_task_consumed",
                task_id=state.task_id,
                status=state.status,
            )
            return

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "Router encaminhou TaskState", task_id=state.task_id, next_role=state.next_agent_role
        )
    except Exception as e:
        logger.error("router_process_task_failed", error=str(e), exc_info=True)
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
