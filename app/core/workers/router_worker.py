"""
Router Worker (Rececionista)

Consome a fila central JANUS.tasks.router e decide o próximo agente
para o TaskState usando o Planner na decomposição inicial.
"""
import logging
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.core.autonomy.planner import build_plan_for_goal
from app.services.collaboration_service import CollaborationService
from app.repositories.collaboration_repository import CollaborationRepository
from app.models.schemas import TaskMessage, TaskState, QueueName

logger = logging.getLogger(__name__)


def _infer_first_agent(original_goal: str) -> str:
    """Usa o Planner para sugerir o primeiro agente; fallback para 'coder'."""
    try:
        plan = build_plan_for_goal(original_goal)
        steps = plan.get("steps", []) if isinstance(plan, dict) else []
        # Heurística simples: primeira ação geralmente é escrever código
        return "coder"
    except Exception:
        return "coder"


def _contains_knowledge_payload(state: TaskState) -> bool:
    """Heurística: decide se o TaskState contém conhecimento a ser consolidado."""
    payload = state.data_payload or {}
    tool_text = (payload.get("tool_output") or "").strip()
    sandbox_text = (payload.get("sandbox_output") or "").strip()
    sandbox_err = (payload.get("sandbox_error") or "").strip()
    # Palavras-chave no objetivo original (pt/en)
    goal = (state.original_goal or "").lower()
    goal_kws = [
        "pesquisar", "research", "buscar", "estudar", "study", "aprender", "learn",
        "ler", "read", "pdf", "document", "docs", "doc", "article", "artigo", "context"
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
        should_consolidate = success_like and _contains_knowledge_payload(state)
        if should_consolidate:
            # Publica tarefa de consolidação em paralelo sem alterar o fluxo principal
            payload = state.data_payload or {}
            content = (payload.get("tool_output") or payload.get("sandbox_output") or state.original_goal or "").strip()
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
            ).model_dump_json()
            broker = await get_broker()
            await broker.publish(queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value, message=side_msg)
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
        logger.info("Router encaminhou TaskState", task_id=state.task_id, next_role=state.next_agent_role)
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
