from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.core.autonomy.goal_manager import GoalManager, GoalStatus, get_goal_manager
from app.core.tools.action_module import action_registry
from app.services.autonomy_service import AutonomyConfig, AutonomyService, get_autonomy_service

router = APIRouter(tags=["Autonomy"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---


class AutonomyStartRequest(BaseModel):
    interval_seconds: int = Field(60, ge=1, le=3600)
    user_id: str | None = None
    project_id: str | None = None
    risk_profile: str = Field("balanced", description="conservative|balanced|aggressive")
    auto_confirm: bool = False
    allowlist: list[str] = []
    blocklist: list[str] = []
    max_actions_per_cycle: int = Field(20, ge=1, le=1000)
    max_seconds_per_cycle: int = Field(60, ge=1, le=3600)
    plan: list[dict[str, Any]] = Field(
        default_factory=list, description="Lista de passos: {'tool': str, 'args': dict}"
    )


class AutonomyStatusResponse(BaseModel):
    active: bool
    cycle_count: int
    last_cycle_at: float | None
    config: dict[str, Any]


class PlanUpdateRequest(BaseModel):
    plan: list[dict[str, Any]]


def _validate_plan_steps(
    plan: list[dict[str, Any]],
    allowlist: list[str] | None = None,
    blocklist: list[str] | None = None,
) -> None:
    """Valida cada passo do plano: shape, existência da ferramenta, args_schema e listas de permissão.

    Levanta HTTPException 422 em caso de erro.
    """
    allowlist = allowlist or []
    blocklist = blocklist or []
    for idx, step in enumerate(plan):
        if not isinstance(step, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Passo {idx} do plano inválido: deve ser um objeto.",
            )
        tool_name = step.get("tool")
        args = step.get("args", {})
        if not tool_name or not isinstance(tool_name, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Passo {idx} inválido: campo 'tool' ausente ou não é string.",
            )
        if not isinstance(args, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Passo {idx} inválido: campo 'args' deve ser um objeto.",
            )

        # Listas de permissão/bloqueio
        if blocklist and tool_name in blocklist:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Ferramenta '{tool_name}' bloqueada pela blocklist.",
            )
        if allowlist and tool_name not in allowlist:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Ferramenta '{tool_name}' não permitida pela allowlist.",
            )

        tool = action_registry.get_tool(tool_name)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Ferramenta '{tool_name}' não encontrada no registro.",
            )

        # Validação de schema de argumentos (se disponível)
        args_schema = getattr(tool, "args_schema", None)
        if args_schema:
            try:
                # Pydantic v1: instanciar o modelo
                args_schema(**args)
            except ValidationError as e:
                # Erros detalhados de validação
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "message": f"Passo {idx} inválido: argumentos não compatíveis com schema de '{tool_name}'.",
                        "errors": e.errors() if hasattr(e, "errors") else str(e),
                    },
                )


class GoalCreateRequest(BaseModel):
    title: str
    description: str
    priority: int = Field(5, ge=1, le=10)
    success_criteria: str | None = None
    deadline_ts: float | None = None


class GoalStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="pending|in_progress|completed|failed")


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: int
    status: str
    success_criteria: str | None
    deadline_ts: float | None
    created_at: float
    updated_at: float


# --- Autonomy Loop Endpoints ---


@router.post("/start", summary="Inicia o AutonomyLoop contínuo")
async def start_autonomy(
    request: AutonomyStartRequest, service: AutonomyService = Depends(get_autonomy_service)
):
    # Validação do plano (se fornecido), incluindo schema e políticas
    if request.plan:
        _validate_plan_steps(
            request.plan, allowlist=request.allowlist or [], blocklist=request.blocklist or []
        )

    config = AutonomyConfig(
        interval_seconds=request.interval_seconds,
        user_id=request.user_id,
        project_id=request.project_id,
        risk_profile=request.risk_profile,
        auto_confirm=request.auto_confirm,
        allowlist=request.allowlist,
        blocklist=request.blocklist,
        max_actions_per_cycle=request.max_actions_per_cycle,
        max_seconds_per_cycle=request.max_seconds_per_cycle,
        plan=request.plan,
    )
    ok = await service.start(config)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="AutonomyLoop já está ativo."
        )
    return {"status": "started", "interval_seconds": request.interval_seconds}


@router.post("/stop", summary="Para o AutonomyLoop")
async def stop_autonomy(service: AutonomyService = Depends(get_autonomy_service)):
    ok = await service.stop()
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="AutonomyLoop não está ativo."
        )
    return {"status": "stopped"}


@router.get(
    "/status", response_model=AutonomyStatusResponse, summary="Obtém status do AutonomyLoop"
)
async def autonomy_status(service: AutonomyService = Depends(get_autonomy_service)):
    return service.get_status()


@router.put("/plan", summary="Atualiza o plano de execução do AutonomyLoop")
async def update_autonomy_plan(
    request: PlanUpdateRequest, service: AutonomyService = Depends(get_autonomy_service)
):
    # Validação do plano contra configuração atual (allowlist/blocklist e schema)
    status_payload = service.get_status()
    config = status_payload.get("config", {})
    _validate_plan_steps(
        request.plan,
        allowlist=config.get("allowlist", []) or [],
        blocklist=config.get("blocklist", []) or [],
    )

    service.update_plan(request.plan)
    return {"status": "updated", "steps_count": len(request.plan)}


class PolicyUpdateRequest(BaseModel):
    risk_profile: str | None = Field(None, description="conservative|balanced|aggressive")
    auto_confirm: bool | None = None
    allowlist: list[str] | None = None
    blocklist: list[str] | None = None
    max_actions_per_cycle: int | None = Field(None, ge=1, le=1000)
    max_seconds_per_cycle: int | None = Field(None, ge=1, le=3600)


@router.put("/policy", summary="Atualiza configurações de políticas do AutonomyLoop")
async def update_policy(
    request: PolicyUpdateRequest, service: AutonomyService = Depends(get_autonomy_service)
):
    service.update_policy_config(
        risk_profile=request.risk_profile,
        auto_confirm=request.auto_confirm,
        allowlist=request.allowlist,
        blocklist=request.blocklist,
        max_actions_per_cycle=request.max_actions_per_cycle,
        max_seconds_per_cycle=request.max_seconds_per_cycle,
    )
    return {"status": "updated", "policy": service.get_status().get("config")}


@router.get("/plan", summary="Obtém o plano de execução atual do AutonomyLoop")
async def get_autonomy_plan(service: AutonomyService = Depends(get_autonomy_service)):
    status_payload = service.get_status()
    plan = status_payload.get("config", {}).get("plan", [])
    return {
        "status": "ok",
        "active": status_payload.get("active", False),
        "steps_count": len(plan),
        "plan": plan,
    }


# --- Goals CRUD ---


@router.post("/goals", response_model=GoalResponse, summary="Cria uma nova meta")
async def create_goal(req: GoalCreateRequest, manager: GoalManager = Depends(get_goal_manager)):
    goal = manager.create_goal(
        title=req.title,
        description=req.description,
        priority=req.priority,
        success_criteria=req.success_criteria,
        deadline_ts=req.deadline_ts,
    )
    return GoalResponse(**goal.__dict__)


@router.get("/goals", summary="Lista metas", response_model=list[GoalResponse])
async def list_goals(status: str | None = None, manager: GoalManager = Depends(get_goal_manager)):
    goals = manager.list_goals(status=status)
    return [GoalResponse(**g.__dict__) for g in goals]


@router.get("/goals/{goal_id}", response_model=GoalResponse, summary="Obtém meta por ID")
async def get_goal(goal_id: str, manager: GoalManager = Depends(get_goal_manager)):
    goal = manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta não encontrada")
    return GoalResponse(**goal.__dict__)


@router.patch(
    "/goals/{goal_id}/status", response_model=GoalResponse, summary="Atualiza status da meta"
)
async def update_goal_status(
    goal_id: str, req: GoalStatusUpdateRequest, manager: GoalManager = Depends(get_goal_manager)
):
    if req.status not in {
        GoalStatus.PENDING,
        GoalStatus.IN_PROGRESS,
        GoalStatus.COMPLETED,
        GoalStatus.FAILED,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Status inválido"
        )
    goal = manager.update_goal_status(goal_id, req.status)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta não encontrada")
    return GoalResponse(**goal.__dict__)


@router.delete("/goals/{goal_id}", summary="Remove meta")
async def delete_goal(goal_id: str, manager: GoalManager = Depends(get_goal_manager)):
    ok = manager.delete_goal(goal_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta não encontrada")
    return {"status": "deleted", "goal_id": goal_id}
