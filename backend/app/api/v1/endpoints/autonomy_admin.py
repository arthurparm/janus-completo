from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
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


@router.post("/tools/{name}/rollback")
async def rollback_tool(name: str, request: Request):
    require_admin_actor(request)
    from app.core.tools.action_module import action_registry

    ok = action_registry.rollback_tool(name)
    if not ok:
        raise HTTPException(status_code=404, detail="Tool not found or no previous version")
    return {"status": "ok", "tool": name, "rolled_back": True}


class QuarantineReviewRequest(BaseModel):
    entity_names: list[str] = Field(..., min_length=1)
    action: str = Field("approve", pattern=r"^(approve|reject)$")


@router.post("/knowledge/quarantine/review")
async def review_quarantine(payload: QuarantineReviewRequest, request: Request):
    require_admin_actor(request)
    from app.db.graph import get_graph_db

    graph = await get_graph_db()
    if payload.action == "approve":
        for name in payload.entity_names:
            await graph.query(
                "MATCH (e:Quarantine:Entity {canonical_name: $name}) REMOVE e:Quarantine, e.quarantine_reason RETURN count(e) AS removed",
                {"name": name},
                operation="quarantine_approve",
            )
    return {
        "status": "ok",
        "action": payload.action,
        "entity_names": payload.entity_names,
    }


class ThrottleResetResponse(BaseModel):
    throttle_reset: bool
    timestamp: float
    action_counts: dict[str, Any]


@router.post("/throttle/reset", response_model=ThrottleResetResponse)
async def reset_autonomy_throttle(request: Request):
    require_admin_actor(request)
    from app.services.autonomy_service import get_autonomy_service
    service = get_autonomy_service(request)
    result = service.reset_throttle()
    return ThrottleResetResponse(**result)


@router.get("/tools/{name}/provenance")
async def get_tool_provenance(name: str, request: Request):
    require_admin_actor(request)
    from app.core.tools.action_module import action_registry
    prov = action_registry.get_tool_provenance(name)
    if prov is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found or no provenance data")
    return prov


class CostReportResponse(BaseModel):
    period_days: int
    total_tokens: int
    total_cost_usd: float
    by_action: dict
    daily_budget: int
    daily_total: dict


@router.get("/cost-report", response_model=CostReportResponse)
async def get_autonomy_cost_report(
    request: Request,
    days: int = 7,
):
    require_admin_actor(request)
    from app.core.autonomy.autonomy_cost_tracker import autonomy_cost_tracker
    report = autonomy_cost_tracker.get_cost_report(days=days)
    daily = autonomy_cost_tracker.get_daily_total()
    return CostReportResponse(**{**report, "daily_total": daily})
