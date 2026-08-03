from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.core.security.request_guard import require_admin_actor, require_authenticated_actor_id
from app.services.resource_manager import get_user_gpu_usage

router = APIRouter(tags=["Resources"], prefix="/resources")


@router.get("/gpu/usage/self")
async def gpu_usage_self(request: Request):
    return get_user_gpu_usage(require_authenticated_actor_id(request))


class BudgetSetRequest(BaseModel):
    budget: float = Field(ge=0)


@router.post("/gpu/budget")
async def set_own_gpu_budget(req: BudgetSetRequest, request: Request):
    actor = require_authenticated_actor_id(request)
    budgets = dict(getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}) or {})
    budgets[actor] = float(req.budget)
    settings.TRAINING_GPU_BUDGET_PER_USER = budgets
    return {"actor_id": actor, "budget": float(req.budget)}


@router.post("/gpu/budget/{target_actor_id}")
async def set_actor_gpu_budget(target_actor_id: str, req: BudgetSetRequest, request: Request):
    require_admin_actor(request)
    budgets = dict(getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}) or {})
    budgets[target_actor_id] = float(req.budget)
    settings.TRAINING_GPU_BUDGET_PER_USER = budgets
    return {"target_actor_id": target_actor_id, "budget": float(req.budget)}
