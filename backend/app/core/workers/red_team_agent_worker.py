import logging
import json
import re
from typing import Any

from app.core.infrastructure.message_broker import get_broker
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm import ModelPriority, ModelRole
from app.core.monitoring.poison_pill_handler import protect_against_poison_pills
from app.models.schemas import QueueName, TaskMessage, TaskState, TaskStateEvent
from app.repositories.collaboration_repository import CollaborationRepository
from app.repositories.llm_repository import LLMRepository
from app.services.collaboration_service import CollaborationService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

RED_TEAM_ROLE = "red_team"
BLOCKING_SEVERITIES = {"critical", "high"}


async def _build_security_prompt(goal: str, context: str, code_snippets: dict) -> str:
    code_block = "\n".join([f"Arquivo: {k}\n{v}" for k, v in code_snippets.items()])
    if not code_block:
        code_block = context  # Fallback when snippets are not structured.
    return await get_formatted_prompt("security_red_team_audit", goal=goal, code_block=code_block)


def _is_vulnerable(text: str) -> bool:
    return "VULNERABLE" in text.upper()


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None

    candidates: list[str] = []
    if raw.startswith("{") and raw.endswith("}"):
        candidates.append(raw)

    fenced_matches = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
    candidates.extend(fenced_matches)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return None


def _normalize_severity(value: Any) -> str:
    v = str(value or "medium").strip().lower()
    if v in {"critical", "high", "medium", "low", "info"}:
        return v
    return "medium"


def _normalize_findings(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    findings: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "id": str(item.get("id") or f"finding-{index + 1}"),
                "severity": _normalize_severity(item.get("severity")),
                "cwe": str(item.get("cwe") or "UNKNOWN"),
                "file": str(item.get("file") or item.get("file_path") or ""),
                "line": int(item.get("line") or item.get("line_start") or 0),
                "title": str(item.get("title") or item.get("issue") or "Security finding"),
                "evidence": str(item.get("evidence") or item.get("details") or ""),
                "fix_hint": str(item.get("fix_hint") or item.get("recommendation") or ""),
                "status": str(item.get("status") or "open"),
            }
        )
    return findings


def _parse_security_assessment(response_text: str) -> tuple[str, list[dict[str, Any]], str]:
    payload = _extract_json_payload(response_text)
    findings: list[dict[str, Any]] = []
    decision = "approved"
    summary = (response_text or "").strip()

    if payload:
        findings = _normalize_findings(payload.get("findings"))
        raw_decision = str(
            payload.get("decision") or payload.get("verdict") or payload.get("status") or ""
        ).strip().lower()
        if raw_decision in {"rejected", "reject", "fail", "failed", "vulnerable"}:
            decision = "rejected"
        elif raw_decision in {"approved", "approve", "pass", "passed", "safe"}:
            decision = "approved"

        summary = str(payload.get("summary") or payload.get("analysis") or summary)

    if not findings and _is_vulnerable(response_text):
        findings = [
            {
                "id": "heuristic-vulnerability-signal",
                "severity": "high",
                "cwe": "UNKNOWN",
                "file": "",
                "line": 0,
                "title": "Heuristic vulnerability signal detected",
                "evidence": response_text[:1000],
                "fix_hint": "",
                "status": "open",
            }
        ]

    if findings:
        decision = "rejected"

    return decision, findings, summary


@protect_against_poison_pills(
    queue_name=QueueName.TASKS_AGENT_RED_TEAM.value,
    extract_message_id=lambda task: task.task_id,
)
async def process_red_team_task(task: TaskMessage) -> None:
    try:
        raw_state = (task.payload or {}).get("task_state", {})
        state = TaskState(**raw_state)
        # Force the processing role at worker boundary, regardless of upstream payload.
        state.current_agent_role = RED_TEAM_ROLE

        logger.info(f"Red Team analisando tarefa {state.task_id}...")

        # Retrieve relevant context (generated code and fallback context).
        code_snippets = getattr(state.data_payload, "code_snippets", {})
        context = state.data_payload.context or ""
        collab_service = CollaborationService(CollaborationRepository())

        # If there is no code to audit, allow the flow to proceed.
        if not code_snippets and "def " not in context and "class " not in context:
            logger.info("Nenhum codigo detectado para auditoria. Aprovando automaticamente.")
            state.security_cycle_count += 1
            state.security_decision = "approved"
            state.blocked_reason = None
            state.data_payload.audit_passed = True
            state.data_payload.security_findings = []
            state.data_payload.security_audit = "Skipped: No code found."
            state.history.append(
                TaskStateEvent(
                    agent_role=RED_TEAM_ROLE,
                    action="security_audit_passed",
                    notes="Skipped: No code found.",
                )
            )
            state.next_agent_role = "professor"
            await collab_service.pass_task(state)
            return

        prompt = await _build_security_prompt(state.original_goal, context, code_snippets)

        llm_service = LLMService(LLMRepository())
        try:
            response_dict = await llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.SECURITY_AUDITOR,
                priority=ModelPriority.LOCAL_ONLY,
                timeout_seconds=120,
            )
            response_text = response_dict.get("response", "")
            reasoning = response_dict.get("reasoning", None)
            decision, findings, summary = _parse_security_assessment(response_text)
            has_blocking = any(
                str(finding.get("severity") or "").lower() in BLOCKING_SEVERITIES
                for finding in findings
            )

            state.security_cycle_count += 1
            state.security_decision = decision
            state.data_payload.security_findings = findings
            state.data_payload.security_audit = summary
            state.data_payload.audit_passed = decision == "approved"
            state.blocked_reason = "blocking_security_findings" if has_blocking else None

            if decision == "rejected":
                logger.warning(f"VULNERABILIDADE DETECTADA na tarefa {state.task_id}!")
                state.history.append(
                    TaskStateEvent(
                        agent_role=RED_TEAM_ROLE,
                        action="security_audit_failed",
                        notes=summary[:1000],  # Truncate logs
                        reasoning=reasoning,
                    )
                )
                state.data_payload.security_feedback = f"[RED TEAM FEEDBACK]\n{summary}"
                state.next_agent_role = "coder"
            else:
                logger.info(f"Codigo aprovado pelo Red Team na tarefa {state.task_id}.")
                state.history.append(
                    TaskStateEvent(
                        agent_role=RED_TEAM_ROLE,
                        action="security_audit_passed",
                        notes=summary[:500],
                        reasoning=reasoning,
                    )
                )
                state.data_payload.security_feedback = None
                state.next_agent_role = "professor"

            await collab_service.pass_task(state)

        except Exception as e:
            logger.error(f"Falha na auditoria de seguranca: {e}")
            # Fail closed: reject and route back to coder.
            state.security_cycle_count += 1
            state.security_decision = "error"
            state.blocked_reason = "security_audit_system_error"
            state.data_payload.audit_passed = False
            state.data_payload.security_findings = []
            state.history.append(
                TaskStateEvent(
                    agent_role=RED_TEAM_ROLE,
                    action="security_audit_failed_error",
                    notes=f"System error: {str(e)}",
                )
            )
            state.data_payload.security_feedback = f"[SYSTEM ERROR] Security audit failed: {e}"
            state.next_agent_role = "coder"
            await collab_service.pass_task(state)

    except Exception as e:
        logger.error(f"Erro critico no RedTeamAgentWorker: {e}", exc_info=True)
        raise


async def start_red_team_agent_worker():
    logger.info("Iniciando Red Team Agent Worker...")
    broker = await get_broker()
    consumer_task = broker.start_consumer(
        queue_name=QueueName.TASKS_AGENT_RED_TEAM.value,
        callback=process_red_team_task,
        prefetch_count=5,
    )
    logger.info("Red Team Agent Worker iniciado.")
    return consumer_task
