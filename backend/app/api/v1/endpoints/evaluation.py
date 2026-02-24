from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.repositories.ab_experiment_repository import ABExperimentRepository
from app.services.ab_testing_service import ABTestingService

router = APIRouter(tags=["Evaluation"], prefix="/evaluation")


def get_repo() -> ABExperimentRepository:
    return ABExperimentRepository()


class ExperimentCreateRequest(BaseModel):
    name: str
    user_id: str | None = None


class ExperimentResponse(BaseModel):
    id: int
    name: str
    user_id: str | None
    status: str


class ArmCreateRequest(BaseModel):
    name: str
    model_spec: str


class ArmResponse(BaseModel):
    id: int
    experiment_id: int
    name: str
    model_spec: str


class ResultCreateRequest(BaseModel):
    arm_id: int
    metric_name: str
    metric_value: float


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    req: ExperimentCreateRequest, repo: ABExperimentRepository = Depends(get_repo)
):
    exp = repo.create_experiment(req.name, req.user_id)
    return ExperimentResponse(id=exp.id, name=exp.name, user_id=exp.user_id, status=exp.status)


@router.post("/experiments/{experiment_id}/arms", response_model=ArmResponse)
async def add_arm(
    experiment_id: int, req: ArmCreateRequest, repo: ABExperimentRepository = Depends(get_repo)
):
    arm = repo.add_arm(experiment_id, req.name, req.model_spec)
    return ArmResponse(
        id=arm.id, experiment_id=arm.experiment_id, name=arm.name, model_spec=arm.model_spec
    )


@router.get("/experiments", response_model=list[ExperimentResponse])
async def list_experiments(
    user_id: str | None = None, repo: ABExperimentRepository = Depends(get_repo)
):
    items = repo.list_experiments(user_id=user_id, limit=100)
    return [
        ExperimentResponse(id=e.id, name=e.name, user_id=e.user_id, status=e.status) for e in items
    ]


@router.post("/experiments/{experiment_id}/results")
async def add_result(
    experiment_id: int, req: ResultCreateRequest, repo: ABExperimentRepository = Depends(get_repo)
):
    res = repo.add_result(experiment_id, req.arm_id, req.metric_name, req.metric_value)
    return {"id": res.id, "status": "ok"}


@router.get("/experiments/{experiment_id}/winner")
async def experiment_winner(experiment_id: int, metric_name: str = "accuracy"):
    svc = ABTestingService()
    return svc.compute_winner(experiment_id, metric_name)
