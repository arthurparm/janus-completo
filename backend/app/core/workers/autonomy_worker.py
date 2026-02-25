import asyncio
import json
from typing import Any

import structlog

from app.config import settings
from app.core.autonomy.goal_manager import Goal, GoalManager, GoalStatus
from app.core.autonomy.planner import build_plan_for_goal
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine
from app.core.memory.memory_core import get_memory_db
from app.models.schemas import TaskState, TaskStateEvent
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.optimization_repository import OptimizationRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.optimization_service import OptimizationService

logger = structlog.get_logger(__name__)

# Instâncias locais (lazy init)
_memory_service: MemoryService | None = None
_goal_manager: GoalManager | None = None
_llm_service: LLMService | None = None
_optimization_service: OptimizationService | None = None
_collab_service: CollaborationService | None = None
_policy: PolicyEngine | None = None

_DEFAULT_INTERVAL: int = 300  # 5 minutos por padrão


async def _ensure_services_initialized() -> None:
    global \
        _memory_service, \
        _goal_manager, \
        _llm_service, \
        _optimization_service, \
        _collab_service, \
        _policy
    if _memory_service is None:
        db = await get_memory_db()
        mem_repo = MemoryRepository(db)
        _memory_service = MemoryService(mem_repo)
    if _goal_manager is None:
        _goal_manager = GoalManager(_memory_service)
    if _llm_service is None:
        _llm_service = LLMService(LLMRepository())
    if _optimization_service is None:
        _optimization_service = OptimizationService(OptimizationRepository())
    if _collab_service is None:
        _collab_service = CollaborationService(CollaborationRepository())
    if _policy is None:
        _policy = PolicyEngine(PolicyConfig())


def _select_step_for_auto_enqueue(plan: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Seleciona o melhor passo do plano para auto-enfileirar como uma intenção.
    Heurística:
    - Preferir passos de descoberta/consulta (search_web, get_enriched_context)
    - Caso contrário, escolher o último passo como fallback
    """
    if not plan:
        return None
    # Preferir ferramentas de busca/contexto
    preferred = ("search_web", "get_enriched_context")
    for step in plan:
        try:
            tool = str(step.get("tool", ""))
            if tool in preferred:
                return step
        except Exception:
            continue
    # Caso não encontrado, usar o último passo
    return plan[-1]


def _to_original_goal_text(goal: Goal, step: dict[str, Any]) -> str:
    tool = str(step.get("tool", "")).strip()
    args = step.get("args", {}) or {}
    # Formata intenções legíveis
    if tool == "search_web":
        q = args.get("query") or args.get("q") or goal.title
        return f"Pesquisar '{q}' no Tavily"
    if tool == "get_enriched_context":
        topic = args.get("topic") or goal.title
        return f"Obter contexto enriquecido sobre '{topic}'"
    if tool == "get_system_info":
        return "Coletar informações do sistema"
    if tool == "get_current_datetime":
        return "Obter data/hora atual"
    # Fallback genérico
    cleaned = json.dumps(args, ensure_ascii=False)
    return f"Executar '{tool}' com argumentos {cleaned}"


async def _autonomy_heartbeat_loop(interval_seconds: int | None = None) -> None:
    await _ensure_services_initialized()
    interval = int(
        interval_seconds
        or getattr(settings, "AUTONOMY_HEARTBEAT_INTERVAL_SECONDS", _DEFAULT_INTERVAL)
    )
    logger.info("[AutonomyWorker] Iniciado", interval_seconds=interval)

    while True:
        try:
            # 1) Perceber: métricas de saúde (ajuda o planner)
            metrics = (
                await _optimization_service.get_system_health() if _optimization_service else {}
            )
            logger.info("[AutonomyWorker] Perceber: métricas", **(metrics or {}))

            # 2) Consultar desejos/metas pendentes
            current_goal: Goal | None = None
            try:
                current_goal = _goal_manager.get_next_goal() if _goal_manager else None
            except Exception as e:
                logger.warning("[AutonomyWorker] Falha ao consultar metas", exc_info=e)
                current_goal = None

            if not current_goal:
                logger.info(
                    "[AutonomyWorker] Nenhum objetivo proativo pendente. Dormindo…",
                    sleep_seconds=interval,
                )
                await asyncio.sleep(interval)
                continue

            # Marcar como in_progress para refletir intenção ativa
            try:
                _goal_manager.update_goal_status(current_goal.id, GoalStatus.IN_PROGRESS)
            except Exception:
                pass

            # 3) Planejar próximo passo via ORCHESTRATOR (Planner)
            plan: list[dict[str, Any]] = []
            try:
                plan = await build_plan_for_goal(
                    goal=current_goal,
                    metrics=metrics or {},
                    llm_service=_llm_service,
                    policy=_policy,
                    max_steps=20,
                    timeout_seconds=60,
                )
            except Exception as e:
                logger.error("[AutonomyWorker] Falha ao gerar plano", exc_info=e)
                plan = [
                    {"tool": "get_current_datetime", "args": {}},
                    {"tool": "get_system_info", "args": {}},
                ]

            # 4) Selecionar passo e auto-enfileirar no Parlamento (router)
            step = _select_step_for_auto_enqueue(plan)
            if not step:
                logger.info("[AutonomyWorker] Plano vazio. Dormindo…", sleep_seconds=interval)
                await asyncio.sleep(interval)
                continue

            original_goal = _to_original_goal_text(current_goal, step)
            task_state = TaskState(
                original_goal=original_goal,
                next_agent_role="router",
                data_payload={
                    "autonomy": {
                        "goal": {
                            "id": current_goal.id,
                            "title": current_goal.title,
                            "description": current_goal.description,
                            "priority": current_goal.priority,
                        },
                        "selected_step": step,
                        "plan": plan,
                        "metrics": metrics,
                    }
                },
                history=[
                    TaskStateEvent(
                        agent_role="autonomy",
                        action="auto_enqueue",
                        notes=f"Gerado do objetivo '{current_goal.title}'",
                    )
                ],
                meta={"source": "autonomy_worker"},
            )

            try:
                await _collab_service.pass_task(task_state)
                logger.info(
                    "[AutonomyWorker] TaskState auto-enfileirado",
                    task_id=task_state.task_id,
                    goal=current_goal.title,
                    next_role=task_state.next_agent_role,
                )
            except Exception as e:
                logger.error("[AutonomyWorker] Falha ao publicar TaskState", exc_info=e)
                # Marca meta de volta como pendente para tentar novamente
                try:
                    _goal_manager.update_goal_status(current_goal.id, GoalStatus.PENDING)
                except Exception:
                    pass

            # Dormir até próximo ciclo
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("[AutonomyWorker] Cancelado; encerrando loop.")
            break
        except Exception as e:
            logger.error("[AutonomyWorker] Erro no loop", exc_info=e)
            await asyncio.sleep(interval)


async def start_autonomy_worker(interval_seconds: int | None = None) -> asyncio.Task:
    """
    Inicia o AutonomyWorker em background com batimento cardíaco.
    Retorna a asyncio.Task do loop contínuo.
    """
    logger.warning(
        "[AutonomyWorker] LEGACY/DEPRECATED: use AutonomyService (/api/v1/autonomy/*) em modo enqueue_router"
    )
    task = asyncio.create_task(_autonomy_heartbeat_loop(interval_seconds=interval_seconds))
    return task
