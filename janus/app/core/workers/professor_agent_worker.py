"""
Professor Agent Worker

Consome a fila JANUS.tasks.agent.professor, revisa código com LLM e decide
se retorna ao CodeAgent para correções ou segue para Sandbox.
"""

import json
import logging
import re
from datetime import datetime

from app.core.infrastructure.message_broker import get_broker
from app.core.agents.utils import parse_json_strict
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def _build_review_prompt(state: TaskState) -> str:
    code = state.data_payload.script_code or ""
    prompt = [
        "ATUE COMO: Engenheiro de Software Sênior e Especialista em Segurança.",
        "TAREFA: Revisar rigorosamente o código Python abaixo.",
        "",
        "CRITÉRIOS DE AVALIAÇÃO:",
        "1. CORREÇÃO: O código faz o que deve fazer? Existem bugs lógicos?",
        "2. SEGURANÇA: Existem vulnerabilidades (injection, paths inseguros)?",
        "3. QUALIDADE: O código segue PEP 8? Tem docstrings? Usa type hints?",
        "",
        "CÓDIGO PARA REVISÃO:",
        code,
        "",
        "FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):",
        "Retorne APENAS um objeto JSON válido (sem markdown, sem texto extra) com a seguinte estrutura:",
        "{",
        '    "status": "APPROVED" | "REJECTED",',
        '    "critical_issues": ["lista de problemas que impedem a aprovação"],',
        '    "suggestions": ["sugestões de melhoria (não bloqueantes)"],',
        '    "security_score": 1-10',
        "}",
        "Se status for APPROVED, 'critical_issues' deve estar vazio."
    ]
    return "\n".join(prompt)


def _parse_review_json(review_text: str) -> dict[str, Any]:
    """Parse JSON response from LLM using strict mode + regex fallback."""
    try:
        return parse_json_strict(review_text)
    except Exception:
        # Fallback para parsing manual "sujo" ou rejeição por padrão em caso de erro grave
        logger.warning(f"Falha ao parsear JSON do Professor: {review_text[:100]}...")
        # Se falhar o parse, assumimos rejeição para segurança
        return {
            "status": "REJECTED",
            "critical_issues": ["Falha no formato da revisão (JSON inválido)."],
            "suggestions": []
        }


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_PROFESSOR.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_professor_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        state.current_agent_role = "professor"

        code = state.data_payload.script_code
        if not code:
            # Sem código para revisar, encaminhar ao coder
            state.next_agent_role = "coder"
            service = CollaborationService(CollaborationRepository())
            await service.pass_task(state)
            return

        llm_service = LLMService(LLMRepository())
        prompt = _build_review_prompt(state)
        result = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.KNOWLEDGE_CURATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=None,
        )
        review_text = result.get("response", "")
        # Parse JSON
        review_data = _parse_review_json(review_text)

        # Add metadata to payload
        state.data_payload.review_notes = json.dumps(review_data, indent=2, ensure_ascii=False)

        has_errors = review_data.get("status") == "REJECTED"

        state.history.append(
            {
                "agent_role": "professor",
                "action": "code_reviewed",
                "notes": f"status={review_data.get('status')}, score={review_data.get('security_score')}",
                "timestamp": datetime.utcnow().timestamp(),
            }
        )

        if has_errors:
            if state.retries < 10:
                state.retries += 1
                state.next_agent_role = "coder"

                # Format feedback for Coder
                issues = "\n- ".join(review_data.get("critical_issues", []))
                state.data_payload.review_notes = f"REJEITADO PELO PROFESSOR:\nIssues:\n- {issues}"

                logger.info(
                    f"Deep Reflexion: Retrying task ({state.retries}/10)",
                    extra={"task_id": state.task_id, "attempt": state.retries}
                )
            else:
                logger.warning("Deep Reflexion: Max retries (10) reached. Forcing Sandbox.")
                state.data_payload.review_notes += "\n[SYSTEM] MAX RETRIES REACHED. PROCEEDING WITH CAUTION."
                state.next_agent_role = "sandbox"
        else:
            state.next_agent_role = "sandbox"

        service = CollaborationService(CollaborationRepository())
        await service.pass_task(state)
        logger.info(
            "ProfessorAgent revisou e encaminhou",
            extra={"task_id": state.task_id, "next": state.next_agent_role},
        )
    except Exception as e:
        logger.error(f"ProfessorAgent falhou: {e}", exc_info=True)
        raise


async def start_professor_agent_worker():
    logger.info("Iniciando Professor Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_PROFESSOR.value,
        callback=process_professor_task,
        prefetch_count=5,
    )
    logger.info("✓ Professor Agent Worker iniciado.")
    return consumer_task
