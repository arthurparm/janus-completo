import logging

from app.core.infrastructure.message_broker import get_broker
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState, TaskStateEvent
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

def _build_security_prompt(goal: str, context: str, code_snippets: dict) -> str:
    code_block = "\n".join([f"Arquivo: {k}\n{v}" for k, v in code_snippets.items()])
    if not code_block:
        code_block = context # Fallback se snippets não estiverem estruturados

    return (
        f"VOCÊ É UM HACKER ÉTICO E ESPECIALISTA EM SEGURANÇA DE SOFTWARE (RED TEAM).\n"
        f"Sua missão é destruir este código encontrando vulnerabilidades críticas.\n\n"
        f"OBJETIVO DO CÓDIGO: {goal}\n\n"
        f"CÓDIGO PARA AUDITORIA:\n"
        f"```\n{code_block}\n```\n\n"
        f"Analise procurando por:\n"
        f"- Injection (SQL, Command, etc)\n"
        f"- XSS / CSRF\n"
        f"- Hardcoded secrets\n"
        f"- Logic flaws\n"
        f"- Insegurança na manipulação de arquivos\n\n"
        f"Se encontrar ALGO critico, inicie sua resposta com 'VULNERABLE'.\n"
        f"Se estiver seguro, inicie com 'SAFE'.\n"
        f"Seja impiedoso. Explique o vetor de ataque."
    )

def _is_vulnerable(text: str) -> bool:
    return "VULNERABLE" in text.upper()

@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_RED_TEAM.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_red_team_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        # Fix current role
        state.current_agent_role = "red_team"

        logger.info(f"Red Team analisando tarefa {state.task_id}...")

        # Recupera o contexto relevante (código gerado)
        code_snippets = getattr(state.data_payload, "code_snippets", {})
        context = state.data_payload.context or ""

        collab_service = CollaborationService(CollaborationRepository())

        # Se não houver código, passa direto
        if not code_snippets and "def " not in context and "class " not in context:
            logger.info("Nenhum código detectado para auditoria. Aprovando automaticamente.")
            state.history.append(TaskStateEvent(
                agent_role="red_team",
                action="security_audit_passed",
                notes="Skipped: No code found.",
            ))
            state.next_agent_role = "professor"
            await collab_service.pass_task(state)
            return

        # Constroi o prompt adversarial
        prompt = _build_security_prompt(state.original_goal, context, code_snippets)

        # Invoca LLM LOCAL
        llm_service = LLMService(LLMRepository())
        try:
            response_dict = llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.SECURITY_AUDITOR,
                priority=ModelPriority.LOCAL_ONLY,
                timeout_seconds=120
            )
            response_text = response_dict.get("response", "")
            reasoning = response_dict.get("reasoning", None)

            if _is_vulnerable(response_text):
                logger.warning(f"VULNERABILIDADE DETECTADA na tarefa {state.task_id}!")
                state.history.append(TaskStateEvent(
                    agent_role="red_team",
                    action="security_audit_failed",
                    notes=response_text[:1000], # Trucate logs
                    reasoning=reasoning
                ))
                state.data_payload.security_feedback = f"[RED TEAM FEEDBACK]\n{response_text}"
                state.next_agent_role = "coder"
            else:
                logger.info(f"Código aprovado pelo Red Team na tarefa {state.task_id}.")
                state.history.append(TaskStateEvent(
                    agent_role="red_team",
                    action="security_audit_passed",
                    notes=response_text[:500],
                    reasoning=reasoning
                ))
                state.next_agent_role = "professor"

            await collab_service.pass_task(state)

        except Exception as e:
            logger.error(f"Falha na auditoria de segurança: {e}")
            # Fail closed: reject
            state.history.append(TaskStateEvent(
                agent_role="red_team",
                action="security_audit_failed_error",
                notes=f"System error: {str(e)}",
            ))
            state.data_payload.security_feedback = f"[SYSTEM ERROR] Security audit failed: {e}"
            state.next_agent_role = "coder"
            await collab_service.pass_task(state)

    except Exception as e:
        logger.error(f"Erro crítico no RedTeamAgentWorker: {e}", exc_info=True)
        raise

async def start_red_team_agent_worker():
    logger.info("Iniciando Red Team Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_RED_TEAM.value,
        callback=process_red_team_task,
        prefetch_count=5,
    )
    logger.info("✓ Red Team Agent Worker iniciado.")
    return consumer_task
