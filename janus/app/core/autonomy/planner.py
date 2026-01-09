import json
import re
from typing import Any

import structlog

from app.core.autonomy.goal_manager import Goal
from app.core.autonomy.policy_engine import PolicyEngine
from app.core.llm import ModelPriority, ModelRole
from app.core.tools.action_module import PermissionLevel, action_registry
from app.services.llm_service import LLMService

logger = structlog.get_logger(__name__)


def _list_allowed_tools(policy: PolicyEngine | None) -> list[str]:
    try:
        names = list(action_registry._tools.keys())
        if policy:
            # Blocklist enforcement
            names = [n for n in names if n not in (policy.config.blocklist or set())]
            # If conservative, prefer READ_ONLY/SAFE
            rp = (policy.config.risk_profile or "balanced").lower()
            if rp == "conservative":
                allowed = []
                for n in names:
                    meta = action_registry.get_metadata(n)
                    if not meta:
                        continue
                    if meta.permission_level in [PermissionLevel.READ_ONLY, PermissionLevel.SAFE]:
                        allowed.append(n)
                    elif meta.permission_level == PermissionLevel.WRITE and n in (
                        policy.config.allowlist or set()
                    ):
                        allowed.append(n)
                names = allowed
        return sorted(names)
    except Exception as e:
        logger.warning("Falha ao listar ferramentas para planner", exc_info=e)
        return []


def _extract_json_array(text: str) -> list[dict[str, Any]] | None:
    # Tenta parsear diretamente
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        # Se retornou um dict com chave "steps"
        if isinstance(data, dict) and "steps" in data and isinstance(data["steps"], list):
            return data["steps"]
    except Exception:
        pass

    # Tenta extrair entre fences ```json ... ```
    try:
        m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            content = m.group(1)
            data = json.loads(content)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "steps" in data and isinstance(data["steps"], list):
                return data["steps"]
    except Exception:
        pass

    # Tenta extrair primeiro array solto
    try:
        m = re.search(r"(\[\s*{.*?}\s*\])", text, re.DOTALL)
        if m:
            arr = json.loads(m.group(1))
            if isinstance(arr, list):
                return arr
    except Exception:
        pass

    return None


def _validate_steps(
    raw_steps: list[dict[str, Any]], policy: PolicyEngine | None, max_steps: int
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    block = set(policy.config.blocklist) if policy else set()

    for step in raw_steps:
        if len(steps) >= max_steps:
            break
        try:
            tool_name = str(step.get("tool", "")).strip()
            args = step.get("args", {})

            # Additional logic: robust parameters
            critical = bool(step.get("critical", True))
            retry = int(step.get("retry", 0))
            fallback = step.get("fallback_tool")
            if fallback:
                fallback = str(fallback).strip() or None

            if not tool_name:
                continue
            if tool_name in block:
                continue
            tool = action_registry.get_tool(tool_name)
            if not tool:
                continue

            # args must be dict
            if not isinstance(args, dict):
                args = {}

            plan_step = {
                "tool": tool_name,
                "args": args,
                "critical": critical,
                "retry": retry,
                "fallback_tool": fallback,
            }
            steps.append(plan_step)
        except Exception:
            continue
    return steps


# === Stage 1: DRAFT ===
def _build_draft_prompt(
    goal: Goal, metrics: dict[str, Any], tools: list[str], max_steps: int
) -> str:
    sys = (
        "Você é o PLANNER DRAFTER do Janus. Seu objetivo é criar um RASCUNHO de plano.\n"
        "Retorne um JSON com 'steps'. Não se preocupe com perfeição agora, apenas cubra o objetivo.\n"
    )
    goal_txt = f"Objetivo: {goal.title}\nDescrição: {goal.description}\n"
    sys_info = json.dumps(metrics or {}, ensure_ascii=False)
    tools_list = ", ".join(tools[:50])

    return f"{sys}\n{goal_txt}\nEstado: {sys_info}\nTools: {tools_list}\n"


# === Stage 2: CRITIQUE ===
def _build_critique_prompt(goal: Goal, draft_plan: list[dict[str, Any]], tools: list[str]) -> str:
    plan_str = json.dumps(draft_plan, indent=2, ensure_ascii=False)
    sys = (
        "Você é o PLANNER CRITIC do Janus. Analise o plano de rascunho abaixo.\n"
        "Identifique 3 pontos fracos:\n"
        "1. Falta de robustez (passos que podem falhar sem fallback)\n"
        "2. Segurança (uso de tools destrutivas sem checagem)\n"
        "3. Lógica (dependências erradas)\n"
        "Retorne APENAS um texto curto listando as críticas. Se estiver perfeito, diga 'OK'."
    )
    return f"{sys}\nObjetivo: {goal.title}\nRascunho:\n{plan_str}\n"


# === Stage 3: REFINE ===
def _build_refine_prompt(
    goal: Goal, draft_plan: list[dict[str, Any]], critique: str, tools: list[str], max_steps: int
) -> str:
    plan_str = json.dumps(draft_plan, indent=2, ensure_ascii=False)
    sys = (
        "Você é o PLANNER REFINER. Baseado no Rascunho e nas Críticas, gere o PLANO FINAL ROBUSTO.\n"
        "Use o schema JSON rigoroso com 'critical', 'retry', 'fallback_tool'.\n"
        "MELHORE o plano para resolver as críticas.\n"
    )
    schema = (
        "Exemplo de saída:\n"
        "[\n"
        '  {"tool": "get_system_info", "args": {}, "critical": true},\n'
        '  {"tool": "search_web", "args": {"query": "error 500"}, "retry": 2, "fallback_tool": "get_logs"}\n'
        "]"
    )
    tools_list = ", ".join(tools[:50])
    return f"{sys}\nObjetivo: {goal.title}\nCrítica: {critique}\nRascunho: {plan_str}\nTools: {tools_list}\n{schema}"


async def build_plan_for_goal(
    goal: Goal,
    metrics: dict[str, Any],
    llm_service: LLMService,
    policy: PolicyEngine | None = None,
    max_steps: int = 10,
    timeout_seconds: int = 60,
) -> list[dict[str, Any]]:
    """
    Gera um plano SOTA (State of the Art) usando Reflexion (Draft -> Critique -> Refine).
    """
    tools = _list_allowed_tools(policy)

    # 1. DRAFT
    try:
        draft_prompt = _build_draft_prompt(goal, metrics, tools, max_steps)
        draft_res = llm_service.invoke_llm(
            prompt=draft_prompt,
            role=ModelRole.ORCHESTRATOR,  # Drafter uses general orchestrator role
            priority=ModelPriority.DEFAULT,  # Draft can be fast
            timeout_seconds=20,
        )
        draft_plan = _extract_json_array(draft_res.get("response", "")) or []
        draft_plan = _validate_steps(draft_plan, policy, max_steps)

        if not draft_plan:
            raise ValueError("Rascunho vazio")

        logger.info("Planner: Rascunho gerado", steps=len(draft_plan))

        # 2. CRITIQUE (Self-Correction)
        critique_prompt = _build_critique_prompt(goal, draft_plan, tools)
        critique_res = llm_service.invoke_llm(
            prompt=critique_prompt,
            role=ModelRole.ORCHESTRATOR,  # Critic
            priority=ModelPriority.HIGH_QUALITY,  # Needs strict logic
            timeout_seconds=20,
        )
        critique_text = critique_res.get("response", "OK")
        logger.info("Planner: Crítica gerada", critique=critique_text[:100])

        if "OK" in critique_text.upper() and len(critique_text) < 10:
            # Se não há críticas, usa o draft como final
            return draft_plan

        # 3. REFINE
        refine_prompt = _build_refine_prompt(goal, draft_plan, critique_text, tools, max_steps)
        refine_res = llm_service.invoke_llm(
            prompt=refine_prompt,
            role=ModelRole.ORCHESTRATOR,  # Refiner
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=30,
        )
        final_plan = _extract_json_array(refine_res.get("response", "")) or []
        final_plan = _validate_steps(final_plan, policy, max_steps)

        if final_plan:
            logger.info("Planner: Plano refinado finalizado", steps=len(final_plan))
            return final_plan
        return draft_plan  # Fallback to draft if refine fails

    except Exception as e:
        logger.error("Falha ao gerar plano Reflexion", exc_info=e)

    # Fallback seguro
    fallback = [
        {
            "tool": "get_current_datetime",
            "args": {},
            "critical": True,
            "retry": 0,
            "fallback_tool": None,
        },
        {
            "tool": "get_system_info",
            "args": {},
            "critical": True,
            "retry": 0,
            "fallback_tool": None,
        },
    ]
    logger.info("Usando plano fallback", steps=len(fallback))
    return fallback


# === Stage 4: REPLANNING (Runtime) ===
def _build_replanning_prompt(
    goal: Goal,
    failed_step: dict[str, Any],
    error_msg: str,
    remaining_steps: list[dict[str, Any]],
    tools: list[str],
) -> str:
    from json import dumps

    sys = (
        "Você é o REPLANNER do Janus. A execução de um plano FALHOU.\n"
        "Sua tarefa: Decidir como recuperar a falha para ainda atingir o Objetivo.\n"
        "Analise o erro e escolha uma estratégia:\n"
        "1. IGNORE: O erro é irrelevante, pule esse passo.\n"
        "2. RETRY_WITH_ARGS: O passo é certo, mas os argumentos estavam errados (ex: query ruim).\n"
        "3. NEW_PLAN: O plano atual quebrou. Gere novos passos para substituir o restante.\n"
        "4. ABORT: Impossível continuar.\n"
    )

    ctx = {
        "goal": goal.title,
        "failed_step": failed_step,
        "error": error_msg,
        "remaining_steps_count": len(remaining_steps),
    }

    schema = (
        "Retorne JSON puro:\n"
        "{\n"
        '  "action": "IGNORE" | "RETRY_WITH_ARGS" | "NEW_PLAN" | "ABORT",\n'
        '  "new_args": { ... } (se action=RETRY_WITH_ARGS),\n'
        '  "new_steps": [ ... ] (se action=NEW_PLAN, lista de passos completa para terminar o goal)\n'
        "}"
    )

    tools_list = ", ".join(tools[:50])
    return f"{sys}\nContexto de Falha:\n{dumps(ctx, indent=2, ensure_ascii=False)}\nTools Disponíveis: {tools_list}\n{schema}"


async def replan_goal(
    goal: Goal,
    failed_step: dict[str, Any],
    error_msg: str,
    remaining_steps: list[dict[str, Any]],
    llm_service: LLMService,
    policy: PolicyEngine | None = None,
) -> dict[str, Any]:
    """
    Acionado quando um passo falha em tempo de execução (após retries).
    Decide dinamicamente o que fazer.
    """
    tools = _list_allowed_tools(policy)
    prompt = _build_replanning_prompt(goal, failed_step, error_msg, remaining_steps, tools)

    try:
        res = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=30,
        )
        text = res.get("response", "")
        # Tenta extrair JSON
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
            return data
        # Se falhar o parse, tenta interpretar texto simples ou abortar
        if "ABORT" in text:
            return {"action": "ABORT"}

    except Exception as e:
        logger.error("Falha ao replanear", exc_info=e)

    return {"action": "ABORT"}  # Fallback safe


# === Stage 5: OUTCOME VERIFICATION (Judge) ===
def _build_verification_prompt(
    goal: Goal, step: dict[str, Any], result: str, error: str | None
) -> str:
    sys = (
        "Você é o VERIFIER do Janus. Analise o resultado da execução de um passo.\n"
        "Seu objetivo é dizer se o resultado é ÚTIL para o objetivo ou se foi uma falha semântica "
        "(ex: retornou vazio, erro disfarçado, ou não respondeu a pergunta).\n"
        'Retorne JSON: {"success": boolean, "reason": string}'
    )
    ctx = {
        "goal": goal.title,
        "step_tool": step.get("tool"),
        "step_args": step.get("args"),
        "result_preview": result[:1000] if result else "None",
        "error": error,
    }
    return f"{sys}\nContexto:\n{json.dumps(ctx, indent=2, ensure_ascii=False)}"


async def verify_outcome(
    goal: Goal,
    step: dict[str, Any],
    result: Any,
    error: str | None,
    llm_service: LLMService,
) -> dict[str, Any]:
    """
    Verifica semanticamente se o resultado do passo foi satisfatório.
    Retorna {"success": bool, "reason": str}
    """
    try:
        # Se houve erro técnico explícito, nem chama LLM, já é falha.
        if error:
            return {"success": False, "reason": f"System Error: {error}"}

        prompt = _build_verification_prompt(goal, step, str(result), error)
        res = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,  # Could be a specific JUDGE role
            priority=ModelPriority.DEFAULT,  # Keep it fast
            timeout_seconds=15,
        )
        text = res.get("response", "")
        # Extract JSON
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))

        # Fallback heuristic: if text contains "success": true
        if "true" in text.lower() and "success" in text.lower():
            return {"success": True, "reason": "Heuristic validation"}

        # Se não conseguiu parsear, assume sucesso para não bloquear demais (False Positive preferred to False Negative here?)
        # Or better: Assume success unless explicitly failed.
        return {"success": True, "reason": "Verification inconclusive"}

    except Exception as e:
        logger.warning("Falha na verificação de resultado", exc_info=e)
        return {"success": True, "reason": "Verification failed"}
