from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.repositories.autonomy_repository import AutonomyRepository

router = APIRouter(tags=["AutonomyHistory"])


def get_autonomy_repo(request: Request) -> AutonomyRepository:
    return AutonomyRepository()


class RunSummary(BaseModel):
    id: int
    user_id: str | None
    project_id: str | None
    status: str
    cycles: int
    started_at: str | None
    stopped_at: str | None


class StepItem(BaseModel):
    id: int
    cycle: int
    tool: str
    input_preview: str | None
    input_length: int
    result_preview: str | None
    result_length: int
    success: int
    error: str | None
    duration_seconds: float
    created_at: str | None


class EnqueueLedgerItem(BaseModel):
    id: int
    run_id: int | None
    goal_id: str
    task_id: str | None
    cycle: int
    selected_tool: str | None
    idempotency_key: str
    publish_status: str
    publish_error: str | None
    created_at: str | None
    updated_at: str | None


@router.get("/runs", response_model=list[RunSummary], summary="Lista execuções do AutonomyLoop")
async def list_runs(
    user_id: str | None = None,
    project_id: str | None = None,
    limit: int = 50,
    repo: AutonomyRepository = Depends(get_autonomy_repo),
):
    runs = repo.list_runs(user_id=user_id, project_id=project_id, limit=limit)
    return [
        RunSummary(
            id=r.id,
            user_id=r.user_id,
            project_id=r.project_id,
            status=r.status,
            cycles=int(r.cycles or 0),
            started_at=str(r.started_at),
            stopped_at=str(r.stopped_at) if r.stopped_at else None,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=RunSummary, summary="Obtém uma execução específica")
async def get_run(run_id: int, repo: AutonomyRepository = Depends(get_autonomy_repo)):
    r = repo.get_run(run_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run não encontrada")
    return RunSummary(
        id=r.id,
        user_id=r.user_id,
        project_id=r.project_id,
        status=r.status,
        cycles=int(r.cycles or 0),
        started_at=str(r.started_at),
        stopped_at=str(r.stopped_at) if r.stopped_at else None,
    )


@router.get(
    "/runs/{run_id}/steps", response_model=list[StepItem], summary="Lista passos de uma execução"
)
async def list_steps(
    run_id: int,
    cycle: int | None = None,
    limit: int = 100,
    repo: AutonomyRepository = Depends(get_autonomy_repo),
):
    steps = repo.list_steps(run_id=run_id, cycle=cycle, limit=limit)
    return [
        StepItem(
            id=s.id,
            cycle=int(s.cycle or 0),
            tool=s.tool,
            input_preview=s.input_preview,
            input_length=int(s.input_length or 0),
            result_preview=s.result_preview,
            result_length=int(s.result_length or 0),
            success=int(s.success or 0),
            error=s.error,
            duration_seconds=float(s.duration_seconds or 0),
            created_at=str(s.created_at),
        )
        for s in steps
    ]


@router.get(
    "/runs/{run_id}/enqueues",
    response_model=list[EnqueueLedgerItem],
    summary="Lista enqueues de uma execução de autonomia",
)
async def list_enqueues(
    run_id: int,
    limit: int = 100,
    repo: AutonomyRepository = Depends(get_autonomy_repo),
):
    rows = repo.list_enqueues(run_id=run_id, limit=limit)
    return [
        EnqueueLedgerItem(
            id=int(r.id),
            run_id=int(r.run_id) if r.run_id is not None else None,
            goal_id=str(r.goal_id),
            task_id=str(r.task_id) if r.task_id else None,
            cycle=int(r.cycle or 0),
            selected_tool=str(r.selected_tool) if r.selected_tool else None,
            idempotency_key=str(r.idempotency_key),
            publish_status=str(r.publish_status),
            publish_error=str(r.publish_error) if r.publish_error else None,
            created_at=str(r.created_at) if r.created_at else None,
            updated_at=str(r.updated_at) if r.updated_at else None,
        )
        for r in rows
    ]
