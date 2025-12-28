import json
import re
from typing import List, Dict, Any, Optional

import structlog

from app.services.llm_service import LLMService
from app.core.autonomy.goal_manager import Goal
from app.core.autonomy.policy_engine import PolicyEngine
from app.core.llm import ModelRole, ModelPriority
from app.core.tools.action_module import action_registry, PermissionLevel

logger = structlog.get_logger(__name__)


def _list_allowed_tools(policy: Optional[PolicyEngine]) -> List[str]:
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
                    elif meta.permission_level == PermissionLevel.WRITE and n in (policy.config.allowlist or set()):
                        allowed.append(n)
                names = allowed
        return sorted(names)
    except Exception as e:
        logger.warning("Falha ao listar ferramentas para planner", exc_info=e)
        return []


def _build_planner_prompt(goal: Goal, metrics: Dict[str, Any], tools: List[str], max_steps: int) -> str:
    sys = (
        "Você é o ORCHESTRATOR do Janus. Planeje ações concretas usando APENAS as ferramentas disponíveis. "
        "Retorne um JSON puro (sem comentários) com uma lista de objetos no formato: "
        "[{\"tool\": string, \"args\": object}]. NUNCA inclua texto fora do JSON.\n"
    )
    goal_txt = f"Objetivo: {goal.title}\nDescrição: {goal.description}\n"
    if goal.success_criteria:
        goal_txt += f"Critérios de sucesso: {goal.success_criteria}\n"
    sys_info = json.dumps(metrics or {}, ensure_ascii=False)
    tools_list = ", ".join(tools[:50])  # limite razoável para prompt
    guidance = (
        f"Ferramentas disponíveis (use apenas estes nomes): {tools_list}.\n"
        f"Limite de passos: {max_steps}.\n"
        "Restrições: respeite permissões e segurança; não invente ferramentas. "
        "Se precisar consultar contexto, considere get_current_datetime, get_system_info, search_web, get_enriched_context.\n"
    )
    schema = (
        "Exemplo de saída: [{\"tool\": \"get_current_datetime\", \"args\": {}}, "
        "{\"tool\": \"search_web\", \"args\": {\"query\": \"status da aplicação Janus\"}}]"
    )
    return f"{sys}\n{goal_txt}\nEstado do sistema: {sys_info}\n{guidance}\n{schema}"


def _extract_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    # Tenta parsear diretamente
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    # Tenta extrair entre fences ```json ... ```
    try:
        m = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
        if m:
            arr = json.loads(m.group(1))
            if isinstance(arr, list):
                return arr
    except Exception:
        pass

    # Tenta extrair primeiro array
    try:
        m = re.search(r"(\[\s*{.*?}\s*\])", text, re.DOTALL)
        if m:
            arr = json.loads(m.group(1))
            if isinstance(arr, list):
                return arr
    except Exception:
        pass

    return None


def _validate_steps(raw_steps: List[Dict[str, Any]], policy: Optional[PolicyEngine], max_steps: int) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    allow = set(policy.config.allowlist) if policy else set()
    block = set(policy.config.blocklist) if policy else set()

    for step in raw_steps:
        if len(steps) >= max_steps:
            break
        try:
            tool_name = str(step.get("tool", "")).strip()
            args = step.get("args", {})
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
            steps.append({"tool": tool_name, "args": args})
        except Exception:
            continue
    return steps


async def build_plan_for_goal(
    goal: Goal,
    metrics: Dict[str, Any],
    llm_service: LLMService,
    policy: Optional[PolicyEngine] = None,
    max_steps: int = 10,
    timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    """
    Gera um plano de execução para o objetivo atual via ORCHESTRATOR.
    - Lista ferramentas disponíveis e aplica políticas básicas
    - Solicita ao LLM um JSON de passos (tool/args)
    - Valida e limita os passos
    """
    tools = _list_allowed_tools(policy)
    prompt = _build_planner_prompt(goal, metrics, tools, max_steps)

    try:
        result = llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=timeout_seconds,
            user_id=None,
            project_id=None,
        )
        text = result.get("response", "")
        arr = _extract_json_array(text) or []
        steps = _validate_steps(arr, policy, max_steps)
        if steps:
            logger.info("Planner gerou plano", steps=len(steps))
            return steps
    except Exception as e:
        logger.error("Falha ao gerar plano via ORCHESTRATOR", exc_info=e)

    # Fallback seguro
    fallback = [
        {"tool": "get_current_datetime", "args": {}},
        {"tool": "get_system_info", "args": {}},
    ]
    logger.info("Usando plano fallback", steps=len(fallback))
    return fallback