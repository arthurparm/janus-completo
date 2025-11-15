from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from app.repositories.deployment_repository import DeploymentRepository
from app.repositories.user_repository import UserRepository
import json
import os
from app.config import settings

router = APIRouter(tags=["Deployment"], prefix="/deployment")

def get_repo() -> DeploymentRepository:
    return DeploymentRepository()

class StageRequest(BaseModel):
    model_id: str
    rollout_percent: int

@router.post("/stage")
async def stage(req: StageRequest, request: Request, repo: DeploymentRepository = Depends(get_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return repo.stage(req.model_id, req.rollout_percent)

@router.post("/publish")
async def publish(model_id: str, request: Request, repo: DeploymentRepository = Depends(get_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    try:
        meta_path = os.path.join("/app", "workspace", "models", model_id, "metadata.json")
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            min_acc = float(getattr(settings, "MIN_DEPLOY_ACCURACY", 0.7))
            acc = float(meta.get("accuracy") or 0.0)
            if acc < min_acc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Accuracy below threshold")
    except HTTPException:
        raise
    except Exception:
        pass
    return repo.publish(model_id)

@router.post("/rollback")
async def rollback(model_id: str, request: Request, repo: DeploymentRepository = Depends(get_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return repo.rollback(model_id)
