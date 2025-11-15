from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from app.repositories.autonomy_repository import AutonomyRepository

router = APIRouter(tags=["AutonomyHistory"]) 

def get_autonomy_repo(request: Request) -> AutonomyRepository:
    return AutonomyRepository()

class RunSummary(BaseModel):
    id: int
    user_id: Optional[str]
    project_id: Optional[str]
    status: str
    cycles: int
    started_at: Optional[str]
    stopped_at: Optional[str]

class StepItem(BaseModel):
    id: int
    cycle: int
    tool: str
    input_preview: Optional[str]
    input_length: int
    result_preview: Optional[str]
    result_length: int
    success: int
    error: Optional[str]
    duration_seconds: float
    created_at: Optional[str]

@router.get("/runs", response_model=List[RunSummary], summary="Lista execuções do AutonomyLoop")
async def list_runs(user_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50, repo: AutonomyRepository = Depends(get_autonomy_repo)):
    runs = repo.list_runs(user_id=user_id, project_id=project_id, limit=limit)
    return [RunSummary(id=r.id, user_id=r.user_id, project_id=r.project_id, status=r.status, cycles=int(r.cycles or 0), started_at=str(r.started_at), stopped_at=str(r.stopped_at) if r.stopped_at else None) for r in runs]

@router.get("/runs/{run_id}", response_model=RunSummary, summary="Obtém uma execução específica")
async def get_run(run_id: int, repo: AutonomyRepository = Depends(get_autonomy_repo)):
    r = repo.get_run(run_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run não encontrada")
    return RunSummary(id=r.id, user_id=r.user_id, project_id=r.project_id, status=r.status, cycles=int(r.cycles or 0), started_at=str(r.started_at), stopped_at=str(r.stopped_at) if r.stopped_at else None)

@router.get("/runs/{run_id}/steps", response_model=List[StepItem], summary="Lista passos de uma execução")
async def list_steps(run_id: int, cycle: Optional[int] = None, limit: int = 100, repo: AutonomyRepository = Depends(get_autonomy_repo)):
    steps = repo.list_steps(run_id=run_id, cycle=cycle, limit=limit)
    return [StepItem(id=s.id, cycle=int(s.cycle or 0), tool=s.tool, input_preview=s.input_preview, input_length=int(s.input_length or 0), result_preview=s.result_preview, result_length=int(s.result_length or 0), success=int(s.success or 0), error=s.error, duration_seconds=float(s.duration_seconds or 0), created_at=str(s.created_at)) for s in steps]