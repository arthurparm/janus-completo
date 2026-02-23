import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.repositories.deployment_repository import DeploymentRepository
from app.repositories.user_repository import UserRepository
from app.services.bias_check_service import BiasCheckService

router = APIRouter(tags=["Deployment"], prefix="/deployment")


def get_repo() -> DeploymentRepository:
    return DeploymentRepository()


class StageRequest(BaseModel):
    model_id: str
    rollout_percent: int


@router.post("/stage")
async def stage(
    req: StageRequest, request: Request, repo: DeploymentRepository = Depends(get_repo)
):
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
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            min_acc = float(getattr(settings, "MIN_DEPLOY_ACCURACY", 0.7))
            acc = float(meta.get("accuracy") or 0.0)
            if acc < min_acc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Accuracy below threshold"
                )
    except HTTPException:
        raise
    except Exception:
        pass
    try:
        svc = BiasCheckService()
        res = svc.run_precheck(model_id)
        if not res.get("precheck_passed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("safety_warnings") or "Precheck failed",
            )
    except HTTPException:
        raise
    except Exception:
        pass
    return repo.publish(model_id)


@router.post("/precheck")
async def precheck(model_id: str, request: Request, repo: DeploymentRepository = Depends(get_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    svc = BiasCheckService()
    res = svc.run_precheck(model_id)
    try:
        repo.stage(model_id, percent=0)
        # Atualiza campos de precheck no registro
        # Nota: em uma versão futura, usar método dedicado; aqui retornamos os dados para persistência externa
    except Exception:
        pass
    return res


@router.post("/rollback")
async def rollback(model_id: str, request: Request, repo: DeploymentRepository = Depends(get_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or not ur.is_admin(int(actor)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return repo.rollback(model_id)
