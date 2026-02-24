import json
import re
from typing import Any

import structlog

from app.core.autonomy.goal_manager import Goal
from app.core.autonomy.policy_engine import PolicyEngine
from app.core.llm import ModelPriority, ModelRole
from app.core.tools.action_module import PermissionLevel, action_registry
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.services.llm_service import LLMService
from app.core.agents.utils import parse_json_strict

logger = structlog.get_logger(__name__)


def _goal_title(goal: Goal | None) -> str:
    if goal and goal.title:
        return goal.title
    return "No active goal"


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
    try:
        data = parse_json_strict(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "steps" in data and isinstance(data["steps"], list):
            return data["steps"]
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
async def _build_draft_prompt(
    goal: Goal, metrics: dict[str, Any], tools: list[str], max_steps: int
) -> str:
    goal_txt = f"Objetivo: {goal.title}\nDescrição: {goal.description}"
    sys_info = json.dumps(metrics or {}, ensure_ascii=False)
    tools_list = ", ".join(tools[:50])

    return await get_formatted_prompt(
        "autonomy_plan_draft",
        goal=goal_txt,
        metrics=sys_info,
        tools=tools_list,
        max_steps=max_steps,
    )


# === Stage 2: CRITIQUE ===
async def _build_critique_prompt(
    goal: Goal, draft_plan: list[dict[str, Any]], metrics: dict[str, Any]
) -> str:
    plan_str = json.dumps(draft_plan, indent=2, ensure_ascii=False)
    metrics_str = json.dumps(metrics or {}, ensure_ascii=False)
    return await get_formatted_prompt(
        "autonomy_plan_critique",
        goal=goal.title,
        plan=plan_str,
        metrics=metrics_str,
    )


# === Stage 3: REFINE ===
async def _build_refine_prompt(
    goal: Goal, draft_plan: list[dict[str, Any]], critique: str, tools: list[str], max_steps: int
) -> str:
    plan_str = json.dumps(draft_plan, indent=2, ensure_ascii=False)
    tools_list = ", ".join(tools[:50])
    return await get_formatted_prompt(
        "autonomy_plan_refine",
        goal=goal.title,
        critique=critique,
        plan=plan_str,
        tools=tools_list,
    )


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
        draft_prompt = await _build_draft_prompt(goal, metrics, tools, max_steps)
        draft_res = await llm_service.invoke_llm(
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
        critique_prompt = await _build_critique_prompt(goal, draft_plan, metrics)
        critique_res = await llm_service.invoke_llm(
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
        refine_prompt = await _build_refine_prompt(goal, draft_plan, critique_text, tools, max_steps)
        refine_res = await llm_service.invoke_llm(
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
async def _build_replanning_prompt(
    goal: Goal | None,
    failed_step: dict[str, Any],
    error_msg: str,
    remaining_steps: list[dict[str, Any]],
    tools: list[str],
) -> str:
    ctx = {
        "goal": _goal_title(goal),
        "failed_step": failed_step,
        "error": error_msg,
        "remaining_steps_count": len(remaining_steps),
    }
    tools_list = ", ".join(tools[:50])
    return await get_formatted_prompt(
        "autonomy_replanner",
        ctx=json.dumps(ctx, indent=2, ensure_ascii=False),
        tools_list=tools_list,
    )


async def replan_goal(
    goal: Goal | None,
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
    if goal is None:
        logger.warning("Replanejamento solicitado sem meta ativa; abortando por seguranca")
        return {"action": "ABORT", "reason": "missing_goal"}

    tools = _list_allowed_tools(policy)
    prompt = await _build_replanning_prompt(goal, failed_step, error_msg, remaining_steps, tools)

    try:
        res = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=30,
        )
        text = res.get("response", "")
        # Tenta extrair JSON (Strict)
        try:
            return parse_json_strict(text)
        except Exception:
             if "ABORT" in text:
                return {"action": "ABORT"}

    except Exception as e:
        logger.error("Falha ao replanear", exc_info=e)

    return {"action": "ABORT"}  # Fallback safe


# === Stage 5: OUTCOME VERIFICATION (Judge) ===
async def _build_verification_prompt(
    goal: Goal | None, step: dict[str, Any], result: str, error: str | None
) -> str:
    ctx = {
        "goal": _goal_title(goal),
        "step_tool": step.get("tool"),
        "step_args": step.get("args"),
        "result_preview": result[:1000] if result else "None",
        "error": error,
    }
    return await get_formatted_prompt(
        "autonomy_verifier",
        ctx=json.dumps(ctx, indent=2, ensure_ascii=False),
    )


async def verify_outcome(
    goal: Goal | None,
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
        if goal is None:
            return {"success": False, "reason": "Missing active goal"}

        # Se houve erro técnico explícito, nem chama LLM, já é falha.
        if error:
            return {"success": False, "reason": f"System Error: {error}"}

        prompt = await _build_verification_prompt(goal, step, str(result), error)
        res = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,  # Could be a specific JUDGE role
            priority=ModelPriority.DEFAULT,  # Keep it fast
            timeout_seconds=15,
        )
        text = res.get("response", "")
        try:
            result = parse_json_strict(text)
            if isinstance(result, dict) and "success" in result:
                return result
        except Exception:
             # Fallback: Check for clear "SUCCESS" indicator in unstructured text
             text_upper = text.upper()
             if "SUCCESS" in text_upper and "TRUE" in text_upper:
                 # Check for explicit failure markers that might confuse heuristic
                 if "NOT SUCCESS" in text_upper or "FAILED" in text_upper or "FALSE" in text_upper:
                     return {"success": False, "reason": "Ambiguous verification result"}
                 return {"success": True, "reason": "Heuristic validation (strong match)"}

        # Se não conseguiu validar com segurança, falha por precaução
        return {"success": False, "reason": "Verification inconclusive"}

    except Exception as e:
        logger.warning("Falha na verificação de resultado", exc_info=e)
        # Fallback SEGURO: Em caso de falha na verificação, assume falha para evitar falso-positivo.
        return {"success": False, "reason": "Verification inconclusive due to parsing error"}
