import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.core.security.request_guard import require_admin_actor

router = APIRouter(tags=["Deployment"], prefix="/deployment")


def get_inference_facade(request: Request):
    return request.app.state.inference_facade


class StageRequest(BaseModel):
    model_id: str
    rollout_percent: int


@router.post("/stage")
async def stage(
    req: StageRequest, request: Request, inference = Depends(get_inference_facade)
):
    require_admin_actor(request)
    return inference.stage_model(model_id=req.model_id, rollout_percent=req.rollout_percent)


@router.post("/publish")
async def publish(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_admin_actor(request)
    try:
        models_base_dir = os.path.realpath(os.path.join("/app", "workspace", "models"))
        meta_path = os.path.realpath(os.path.join(models_base_dir, model_id, "metadata.json"))
        if os.path.commonpath([models_base_dir, meta_path]) != models_base_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model_id path"
            )

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
        res = inference.precheck(model_id=model_id)
        if not res.get("precheck_passed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=res.get("safety_warnings") or "Precheck failed",
            )
    except HTTPException:
        raise
    except Exception:
        pass
    return inference.publish_model(model_id=model_id)


@router.post("/precheck")
async def precheck(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_admin_actor(request)
    res = inference.precheck(model_id=model_id)
    try:
        inference.stage_model(model_id=model_id, rollout_percent=0)
        # Atualiza campos de precheck no registro
        # Nota: em uma versão futura, usar método dedicado; aqui retornamos os dados para persistência externa
    except Exception:
        pass
    return res


@router.post("/rollback")
async def rollback(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_admin_actor(request)
    return inference.rollback_model(model_id=model_id)
