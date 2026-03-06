from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, Field

from app.core.security.request_guard import require_admin_actor
from app.services.autonomy_admin_service import (
    AutonomyAdminService,
    get_autonomy_admin_service,
    maybe_trigger_self_study_on_goal_completion,
)

router = APIRouter(
    tags=["AutonomyAdmin"],
    dependencies=[Depends(require_admin_actor)],
)


class BacklogSyncResponse(BaseModel):
    created: int
    deduped: int
    capped: int
    closed: int
    fallback_used_count: int
    findings_total: int


class SelfStudyRunRequest(BaseModel):
    mode: str = Field("incremental", pattern=r"^(incremental|full)$")
    reason: str | None = None


class SelfStudyNeo4jRepairRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=5000)


class CodeQARequest(BaseModel):
    question: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)
    citation_limit: int = Field(8, ge=1, le=20)


class CodeQAResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    self_memory: list[dict[str, Any]]


@router.post("/backlog/sync", response_model=BacklogSyncResponse)
async def sync_backlog(service: AutonomyAdminService = Depends(get_autonomy_admin_service)):
    return BacklogSyncResponse(**(await service.sync_backlog()))


@router.get("/board")
async def get_board(
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    return {"items": service.get_board(status=status, limit=limit)}


@router.post("/self-study/run")
async def run_self_study(
    payload: SelfStudyRunRequest,
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    return await service.run_self_study(
        mode=payload.mode,
        reason=payload.reason,
        trigger_type="manual",
    )


@router.get("/self-study/status")
async def self_study_status(service: AutonomyAdminService = Depends(get_autonomy_admin_service)):
    return service.get_self_study_status()


@router.get("/self-study/runs")
async def self_study_runs(
    limit: int = Query(default=20, ge=1, le=200),
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    return {"items": service.list_self_study_runs(limit=limit)}


@router.get("/self-study/neo4j-audit")
async def self_study_neo4j_audit(
    orphan_limit: int = Query(default=25, ge=1, le=200),
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    return await service.get_self_study_neo4j_audit(orphan_limit=orphan_limit)


@router.post("/self-study/neo4j-repair")
async def self_study_neo4j_repair(
    payload: SelfStudyNeo4jRepairRequest,
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    return await service.repair_self_study_neo4j(limit=payload.limit)


@router.post("/code-qa", response_model=CodeQAResponse)
async def code_qa(
    payload: CodeQARequest,
    service: AutonomyAdminService = Depends(get_autonomy_admin_service),
):
    result = await service.ask_code_as_admin(
        question=payload.question,
        limit=payload.limit,
        citation_limit=payload.citation_limit,
    )
    return CodeQAResponse(
        answer=str(result.get("answer") or ""),
        citations=result.get("citations") or [],
        self_memory=result.get("self_memory") or [],
    )


@router.post("/self-study/trigger-on-goal-complete")
async def admin_manual_goal_completion_trigger(
    request: Request,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        maybe_trigger_self_study_on_goal_completion,
        app=request.app,
        reason="admin_manual_goal_completion_trigger",
        trigger_type="goal_completed",
    )
    return {"status": "queued"}
