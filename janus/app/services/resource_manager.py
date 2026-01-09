from datetime import datetime
from typing import Any

from app.config import settings

_user_gpu_usage: dict[str, dict[str, Any]] = {}


def can_schedule_training(user_id: str | None) -> bool:
    if not user_id:
        return True
    budget = getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}).get(str(user_id))
    if budget is None:
        return True
    u = _user_gpu_usage.setdefault(
        str(user_id), {"used": 0.0, "updated_at": datetime.utcnow().isoformat()}
    )
    return float(u.get("used", 0.0)) < float(budget)


def record_training_usage(user_id: str | None, cost: float) -> None:
    if not user_id:
        return
    u = _user_gpu_usage.setdefault(
        str(user_id), {"used": 0.0, "updated_at": datetime.utcnow().isoformat()}
    )
    u["used"] = float(u.get("used", 0.0)) + float(cost)
    u["updated_at"] = datetime.utcnow().isoformat()


def get_user_gpu_usage(user_id: str) -> dict[str, Any]:
    return _user_gpu_usage.get(str(user_id), {"used": 0.0, "updated_at": None})


def compute_job_priority(user_id: str | None, model_type: str | None) -> int:
    try:
        if not user_id:
            return 3
        budget = getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}).get(str(user_id))
        usage = get_user_gpu_usage(str(user_id))
        used = float(usage.get("used", 0.0))
        if budget is None:
            return 4
        remaining = float(budget) - used
        if remaining <= 0:
            return 1
        if (model_type or "").lower() == "llm_finetuning":
            return 5 if remaining > (float(budget) * 0.5) else 3
        return 4 if remaining > (float(budget) * 0.25) else 2
    except Exception:
        return 3
