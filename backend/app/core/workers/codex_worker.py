"""
Codex Worker

Worker dedicado a executar tarefas do Codex CLI (execução e revisão)
de forma assíncrona, garantindo isolamento e controle de fluxo.
"""
import structlog
from datetime import datetime

from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine, RiskProfile
from app.core.infrastructure.message_broker import get_broker
from app.core.tools.external_cli_tools import register_external_cli_tools
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.services.collaboration_service import CollaborationService
from app.services.tool_executor_service import ToolExecutorService

logger = structlog.get_logger(__name__)


def _build_codex_policy(approved: bool) -> PolicyEngine:
    return PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.CONSERVATIVE,
            auto_confirm=approved,
            allowlist={"codex_exec", "codex_review"},
            blocklist=set(),
            max_actions_per_cycle=5,
            max_seconds_per_cycle=120,
        )
    )


async def process_codex_task(task: TaskMessage) -> None:
    try:
        task_type = task.task_type
        payload = task.payload or {}
        task_id = task.task_id

        # Se tiver task_state, extrai contexto dele, senão usa payload direto
        state_data = payload.get("task_state")
        if state_data:
            state = TaskState(**state_data)
            instruction = state.data_payload.context or "No instruction provided"
            original_goal = state.original_goal
            user_id = (state.meta or {}).get("user_id") or payload.get("user_id")
            approved = bool(
                payload.get("approved")
                or payload.get("auto_confirm")
                or (state.meta or {}).get("approved")
            )
        else:
            instruction = payload.get("instruction", "")
            original_goal = payload.get("goal", "Codex Fix")
            user_id = payload.get("user_id")
            approved = bool(payload.get("approved") or payload.get("auto_confirm"))

        logger.info("log_info", message=f"Processando task Codex: {task_id} (Tipo: {task_type})")

        # Garante que as ferramentas externas estejam registradas
        register_external_cli_tools()

        tool_executor = ToolExecutorService()
        policy = _build_codex_policy(approved=approved)

        if task_type == "codex_fix":
            # Executa o Codex
            # O prompt é montado combinando o objetivo e a instrução
            prompt = f"{original_goal}\n\nContexto:\n{instruction}"

            calls = [{"name": "codex_exec", "args": {"prompt": prompt, "model": payload.get("model")}}]
            outputs = await tool_executor.execute_tool_calls(
                calls,
                strict=True,
                policy=policy,
                user_id=str(user_id) if user_id else None,
            )
            result = outputs[0]["result"] if outputs else "Nenhum resultado retornado."

            # Salva resultado no workspace
            service = CollaborationService(CollaborationRepository())
            
            artifact_key = f"codex_fix_{task_id}_{int(datetime.now().timestamp())}"
            service.add_artifact(
                key=artifact_key,
                value={
                    "task_id": task_id,
                    "prompt": prompt,
                    "result": result,
                    "approved": approved,
                    "user_id": user_id,
                    "type": "codex_fix_result",
                },
                author="codex_worker"
            )
            
            logger.info("log_info", message=f"Codex task concluída. Artefato salvo: {artifact_key}")
        elif task_type == "codex_review":
            prompt = payload.get("prompt")
            args = {
                "prompt": prompt,
                "base": payload.get("base"),
                "commit": payload.get("commit"),
                "uncommitted": payload.get("uncommitted", True),
            }
            calls = [{"name": "codex_review", "args": args}]
            outputs = await tool_executor.execute_tool_calls(
                calls,
                strict=True,
                policy=policy,
                user_id=str(user_id) if user_id else None,
            )
            result = outputs[0]["result"] if outputs else "Nenhum resultado retornado."
            service = CollaborationService(CollaborationRepository())
            artifact_key = f"codex_review_{task_id}_{int(datetime.now().timestamp())}"
            service.add_artifact(
                key=artifact_key,
                value={
                    "task_id": task_id,
                    "prompt": prompt,
                    "result": result,
                    "approved": approved,
                    "user_id": user_id,
                    "type": "codex_review_result",
                },
                author="codex_worker",
            )
            logger.info("log_info", message=f"Codex review concluído. Artefato salvo: {artifact_key}")
        else:
            logger.warning("log_warning", message=f"Tipo de task desconhecido para Codex Worker: {task_type}")

    except Exception as e:
        logger.error("log_error", message=f"Codex Worker falhou na task {task.task_id}: {e}", exc_info=True)


async def start_codex_worker():
    logger.info("Iniciando Codex Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_CODEX_WORKER.value,
        callback=process_codex_task,
        prefetch_count=2,
    )
    logger.info("✓ Codex Worker iniciado.")
    return consumer_task
