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
