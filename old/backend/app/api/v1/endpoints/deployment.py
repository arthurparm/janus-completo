import math

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.core.security.request_guard import require_service_actor
from app.services.bias_check_service import BiasCheckServiceError
from app.services.model_artifact_service import (
    MODEL_ID_PATTERN,
    ModelArtifactError,
    load_model_metadata,
    resolve_model_file,
)

router = APIRouter(tags=["Deployment"], prefix="/deployment")

def get_inference_facade(request: Request):
    return request.app.state.inference_facade


class StageRequest(BaseModel):
    model_id: str = Field(pattern=MODEL_ID_PATTERN.pattern)
    rollout_percent: int = Field(ge=0, le=100)


class DeploymentPrecheckEvidence(BaseModel):
    artifact_present: bool
    performance_metrics_present: bool
    fairness_metrics_present: bool


class DeploymentPrecheckResponse(BaseModel):
    precheck_passed: bool
    bias_score: float | None
    safety_warnings: list[str] | None
    evidence: DeploymentPrecheckEvidence


@router.post("/stage")
async def stage(
    req: StageRequest, request: Request, inference = Depends(get_inference_facade)
):
    require_service_actor(request)
    try:
        load_model_metadata(req.model_id)
        if not resolve_model_file(req.model_id, "model.json").is_file():
            raise ModelArtifactError("Model artifact model.json was not found")
    except ModelArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return inference.stage_model(model_id=req.model_id, rollout_percent=req.rollout_percent)


@router.post(
    "/publish",
    responses={
        status.HTTP_501_NOT_IMPLEMENTED: {
            "description": "No inference-runtime activation adapter is configured."
        }
    },
)
async def publish(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_service_actor(request)
    if not MODEL_ID_PATTERN.fullmatch(model_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model_id format",
        )
    try:
        meta = load_model_metadata(model_id)
    except ModelArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    min_acc = float(getattr(settings, "MIN_DEPLOY_ACCURACY", 0.7))
    try:
        acc = float(meta["accuracy"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model accuracy is missing or invalid",
        ) from exc
    if not math.isfinite(acc) or not 0.0 <= acc <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model accuracy must be a finite value between 0 and 1",
        )
    if acc < min_acc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Accuracy below threshold"
        )
    try:
        res = inference.precheck(model_id=model_id)
    except ModelArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BiasCheckServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deployment precheck is unavailable",
        ) from exc
    if not res.get("precheck_passed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("safety_warnings") or "Precheck failed",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Model activation is not connected to an inference runtime; "
            "the model was not published."
        ),
    )


@router.post("/precheck", response_model=DeploymentPrecheckResponse)
async def precheck(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_service_actor(request)
    try:
        if not MODEL_ID_PATTERN.fullmatch(model_id):
            raise ModelArtifactError("Invalid model_id format")
        return inference.precheck(model_id=model_id)
    except ModelArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BiasCheckServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deployment precheck is unavailable",
        ) from exc


@router.post("/rollback")
async def rollback(model_id: str, request: Request, inference = Depends(get_inference_facade)):
    require_service_actor(request)
    if not MODEL_ID_PATTERN.fullmatch(model_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model_id format",
        )
    return inference.rollback_model(model_id=model_id)
