import json
import structlog
from typing import Any

from app.config import settings

logger = structlog.get_logger(__name__)


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def infer_llm_task_profile(prompt: str | None) -> dict[str, Any]:
    text = str(prompt or "").strip().lower()
    if not text:
        return {}

    complexity = "low"
    if len(text) > 2500 or any(
        token in text
        for token in (
            "arquitetura",
            "refator",
            "migra",
            "root cause",
            "deep dive",
            "step by step",
            "passo a passo",
            "incidente",
            "debug",
        )
    ):
        complexity = "high"
    elif len(text) > 900 or any(
        token in text
        for token in ("analise", "compare", "comparar", "planej", "estrateg", "investig")
    ):
        complexity = "medium"

    if any(
        token in text
        for token in ("security", "seguranca", "vulnerab", "threat", "exploit", "red team")
    ):
        return {
            "task_type": "security_review",
            "complexity": complexity,
            "role": "security_auditor",
            "priority": "high_quality",
        }

    if any(
        token in text
        for token in ("code", "codigo", "refactor", "bug", "stack trace", "typescript", "python", "sql")
    ):
        return {
            "task_type": "code_task",
            "complexity": complexity,
            "role": "code_generator",
            "priority": "high_quality" if complexity != "low" else "fast_and_cheap",
        }

    if any(
        token in text
        for token in ("document", "docs", "citation", "fonte", "knowledge", "manual", "pesquisa")
    ):
        return {
            "task_type": "knowledge_task",
            "complexity": complexity,
            "role": "knowledge_curator",
            "priority": "fast_and_cheap" if complexity == "low" else "high_quality",
        }

    if any(
        token in text
        for token in ("why", "por que", "analise", "compare", "comparar", "planeje", "plan")
    ):
        return {
            "task_type": "reasoning_task",
            "complexity": complexity,
            "role": "reasoner",
            "priority": "high_quality" if complexity != "low" else "fast_and_cheap",
        }

    return {
        "task_type": "general_task",
        "complexity": complexity,
        "role": "orchestrator",
        "priority": "fast_and_cheap" if complexity == "low" else "high_quality",
    }


def resolve_llm_task_policy(
    task_type: str | None = None,
    complexity: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = getattr(settings, "LLM_TASK_POLICY", None) or {}
    if isinstance(policy, str):
        try:
            policy = json.loads(policy)
        except Exception:
            policy = {}
    if not isinstance(policy, dict):
        return overrides or {}

    resolved: dict[str, Any] = {}

    base_cfg = policy.get("default")
    if isinstance(base_cfg, dict):
        resolved = _merge_dict(resolved, base_cfg)

    global_complexity = policy.get("complexity")
    if complexity and isinstance(global_complexity, dict):
        complexity_cfg = global_complexity.get(complexity)
        if isinstance(complexity_cfg, dict):
            resolved = _merge_dict(resolved, complexity_cfg)

    tasks_cfg = policy.get("tasks")
    if task_type and isinstance(tasks_cfg, dict):
        task_cfg = tasks_cfg.get(task_type)
        if isinstance(task_cfg, dict):
            task_complexity = (
                task_cfg.get("complexity") if isinstance(task_cfg.get("complexity"), dict) else {}
            )
            task_cfg_no_complexity = {k: v for k, v in task_cfg.items() if k != "complexity"}
            resolved = _merge_dict(resolved, task_cfg_no_complexity)

            if complexity and isinstance(task_complexity, dict):
                task_complexity_cfg = task_complexity.get(complexity)
                if isinstance(task_complexity_cfg, dict):
                    resolved = _merge_dict(resolved, task_complexity_cfg)

    if overrides:
        if not isinstance(overrides, dict):
            logger.warning("Invalid task policy overrides ignored (expected dict).")
        else:
            resolved = _merge_dict(resolved, overrides)

    return resolved
