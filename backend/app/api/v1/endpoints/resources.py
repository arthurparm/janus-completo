from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import settings
from app.core.security.request_guard import require_admin_actor
from app.services.resource_manager import get_user_gpu_usage

router = APIRouter(tags=["Resources"], prefix="/resources")


@router.get("/gpu/usage/{user_id}")
async def gpu_usage(user_id: str):
    return get_user_gpu_usage(user_id)


class BudgetSetRequest(BaseModel):
    user_id: str
    budget: float


@router.post("/gpu/budget")
async def set_gpu_budget(req: BudgetSetRequest, request: Request):
    require_admin_actor(request)
    b = dict(getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}) or {})
    b[str(req.user_id)] = float(req.budget)
    settings.TRAINING_GPU_BUDGET_PER_USER = b
    return {"user_id": req.user_id, "budget": float(req.budget)}
