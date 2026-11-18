from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.core.security.request_guard import require_authenticated_actor_id
from app.repositories.ab_experiment_repository import ABExperimentRepository
from app.services.ab_testing_service import ABTestingService

router = APIRouter(tags=["Evaluation"], prefix="/evaluation")
control_router = APIRouter(tags=["Evaluation"], prefix="/evaluation")


def get_repo() -> ABExperimentRepository:
    return ABExperimentRepository()


class ExperimentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class ExperimentResponse(BaseModel):
    id: int
    name: str
    status: str


class ArmCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    model_spec: str = Field(..., min_length=1, max_length=200)


class ArmResponse(BaseModel):
    id: int
    experiment_id: int
    name: str
    model_spec: str


class ResultCreateRequest(BaseModel):
    arm_id: int
    metric_name: str = Field(..., min_length=1, max_length=50)
    metric_value: float


class AutomatedResultIngestRequest(ResultCreateRequest):
    experiment_id: int


def _owner(request: Request) -> int:
    return int(require_authenticated_actor_id(request))


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    payload: ExperimentCreateRequest,
    request: Request,
    repo: ABExperimentRepository = Depends(get_repo),
):
    experiment = repo.create_experiment(payload.name, _owner(request))
    return ExperimentResponse(id=experiment.id, name=experiment.name, status=experiment.status)


@router.get("/experiments", response_model=list[ExperimentResponse])
async def list_experiments(
    request: Request,
    repo: ABExperimentRepository = Depends(get_repo),
):
    return [
        ExperimentResponse(id=item.id, name=item.name, status=item.status)
        for item in repo.list_experiments(owner_user_id=_owner(request), limit=100)
    ]


@router.post("/experiments/{experiment_id}/arms", response_model=ArmResponse)
async def add_arm(
    experiment_id: int,
    payload: ArmCreateRequest,
    request: Request,
    repo: ABExperimentRepository = Depends(get_repo),
):
    arm = repo.add_arm(experiment_id, _owner(request), payload.name, payload.model_spec)
    if arm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return ArmResponse(
        id=arm.id, experiment_id=arm.experiment_id, name=arm.name, model_spec=arm.model_spec
    )


@router.post("/experiments/{experiment_id}/results")
async def add_result(
    experiment_id: int,
    payload: ResultCreateRequest,
    request: Request,
    repo: ABExperimentRepository = Depends(get_repo),
):
    result = repo.add_result(
        experiment_id,
        payload.arm_id,
        payload.metric_name,
        payload.metric_value,
        owner_user_id=_owner(request),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return {"id": result.id, "status": "ok"}


@router.get("/experiments/{experiment_id}/winner")
async def experiment_winner(
    experiment_id: int,
    request: Request,
    metric_name: str = Query("accuracy", min_length=1, max_length=50),
    repo: ABExperimentRepository = Depends(get_repo),
):
    if repo.get_owned_experiment(experiment_id, _owner(request)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return ABTestingService(repo).compute_winner(experiment_id, metric_name)


@control_router.post("/ingest", operation_id="ingest_evaluation_result")
async def ingest_automated_result(
    payload: AutomatedResultIngestRequest,
    repo: ABExperimentRepository = Depends(get_repo),
):
    result = repo.add_result(
        payload.experiment_id,
        payload.arm_id,
        payload.metric_name,
        payload.metric_value,
        owner_user_id=None,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return {"id": result.id, "status": "accepted"}
