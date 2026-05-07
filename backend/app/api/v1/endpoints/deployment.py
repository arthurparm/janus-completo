import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.core.security.request_guard import require_admin_actor

router = APIRouter(tags=["Deployment"], prefix="/deployment")

MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _safe_model_file_path(model_id: str, filename: str) -> str:
    models_base_dir = os.path.realpath(os.path.join("/app", "workspace", "models"))
    candidate_path = os.path.realpath(os.path.join(models_base_dir, model_id, filename))
    if not (candidate_path == models_base_dir or candidate_path.startswith(models_base_dir + os.sep)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model_id path"
        )
    return candidate_path


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
    if not MODEL_ID_PATTERN.fullmatch(model_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model_id format",
        )
    try:
        meta_path = _safe_model_file_path(model_id, "metadata.json")

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
