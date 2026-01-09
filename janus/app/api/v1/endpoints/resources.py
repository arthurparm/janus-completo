from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.repositories.user_repository import UserRepository
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
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    b = dict(getattr(settings, "TRAINING_GPU_BUDGET_PER_USER", {}) or {})
    b[str(req.user_id)] = float(req.budget)
    settings.TRAINING_GPU_BUDGET_PER_USER = b
    return {"user_id": req.user_id, "budget": float(req.budget)}
