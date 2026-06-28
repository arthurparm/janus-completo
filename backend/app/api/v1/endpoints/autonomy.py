from typing import Any, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError

from app.core.autonomy.goal_manager import GoalManager, GoalStatus, get_goal_manager
from app.core.autonomy.goal_metrics import goal_metrics_calculator
from app.core.autonomy.safety_plan_validator import safety_plan_validator
from app.core.security.request_guard import require_authenticated_actor_id
from app.core.tools.action_module import action_registry
from app.repositories.observability_repository import record_audit_event_direct
from app.services.autonomy_admin_service import maybe_trigger_self_study_on_goal_completion
from app.services.autonomy_service import (
    AutonomyConfig,
    AutonomyConflictError,
    AutonomyService,
    get_autonomy_service,
)

router = APIRouter(tags=["Autonomy"])
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---


class AutonomyStartRequest(BaseModel):
    interval_seconds: int = Field(60, ge=1, le=3600)
    project_id: str | None = None
    risk_profile: str = Field("balanced", description="conservative|balanced|aggressive")
    auto_confirm: bool = False
    allowlist: list[str] = []
    blocklist: list[str] = []
    max_actions_per_cycle: int = Field(20, ge=1, le=1000)
    max_seconds_per_cycle: int = Field(60, ge=1, le=3600)
    execution_mode: Literal["enqueue_router"] = "enqueue_router"
    plan: list[dict[str, Any]] = Field(
        default_factory=list, description="Lista de passos: {'tool': str, 'args': dict}"
    )


class AutonomyStatusResponse(BaseModel):
    active: bool
    cycle_count: int
    last_cycle_at: float | None
    config: dict[str, Any]
    runtime_lock: dict[str, Any] | None = None


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
    request: AutonomyStartRequest,
    http: Request,
    service: AutonomyService = Depends(get_autonomy_service),
):
    # Validação do plano (se fornecido), incluindo schema e políticas
    if request.plan:
        _validate_plan_steps(
            request.plan, allowlist=request.allowlist or [], blocklist=request.blocklist or []
        )

        ok, violations = safety_plan_validator.validate_plan(request.plan, policy=getattr(service, '_policy', None))
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Plan contains unsafe steps", "violations": violations},
            )

    config = AutonomyConfig(
        interval_seconds=request.interval_seconds,
        user_id=require_authenticated_actor_id(http),
        project_id=request.project_id,
        risk_profile=request.risk_profile,
        auto_confirm=request.auto_confirm,
        allowlist=request.allowlist,
        blocklist=request.blocklist,
        max_actions_per_cycle=request.max_actions_per_cycle,
        max_seconds_per_cycle=request.max_seconds_per_cycle,
        execution_mode=request.execution_mode,
        plan=request.plan,
    )
    try:
        ok = await service.start(config)
    except AutonomyConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "conflicts": [
                    {
                        "conflict_type": c.conflict_type,
                        "resource": c.resource,
                        "goal_a_id": c.goal_a_id,
                        "goal_b_id": c.goal_b_id,
                        "severity": c.severity,
                        "description": c.description,
                    }
                    for c in e.conflicts
                ],
            },
        )
    if not ok:
        status_payload = service.get_status()
        runtime_lock = status_payload.get("runtime_lock") or {}
        if not status_payload.get("active") and runtime_lock.get("owner_id"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="AutonomyLoop lease indisponível (outra instância está ativa neste escopo).",
            )
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
    goal_id: str,
    req: GoalStatusUpdateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    manager: GoalManager = Depends(get_goal_manager),
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
    if req.status == GoalStatus.COMPLETED:
        background_tasks.add_task(
            maybe_trigger_self_study_on_goal_completion,
            app=request.app,
            reason=f"goal_completed:{goal_id}",
            trigger_type="goal_completed",
        )
    return GoalResponse(**goal.__dict__)


@router.delete("/goals/{goal_id}", summary="Remove meta")
async def delete_goal(goal_id: str, manager: GoalManager = Depends(get_goal_manager)):
    ok = manager.delete_goal(goal_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta não encontrada")
    return {"status": "deleted", "goal_id": goal_id}


@router.get("/goals/{goal_id}/metrics")
async def get_goal_metrics(goal_id: str, request: Request, manager: GoalManager = Depends(get_goal_manager)):
    require_authenticated_actor_id(request)
    goal = manager.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    steps = manager.list_steps(goal_id) if hasattr(manager, 'list_steps') else []
    metrics = goal_metrics_calculator.compute(goal_id, steps)
    return metrics.__dict__


@router.get("/health", summary="Agregado de saúde de todos os subsistemas de autonomia")
async def get_autonomy_health(
    request: Request,
    service: AutonomyService = Depends(get_autonomy_service),
):
    require_authenticated_actor_id(request)
    import time
    now = time.time()

    status = service.get_status()
    domain_cb = getattr(service, '_domain_cb', None)

    domain_health = {}
    if domain_cb:
        domain_health = domain_cb.get_domain_health()

    active_goals_count = len(status.get("active_goals", []) if isinstance(status.get("active_goals"), list) else [])

    active_checks = {}

    # Audit ledger ping
    t0 = time.time()
    try:
        record_audit_event_direct(endpoint="autonomy_healthcheck", action="ping", status="check", details_json={})
        active_checks["audit_ledger_ping"] = {"pass": True, "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        active_checks["audit_ledger_ping"] = {"pass": False, "latency_ms": round((time.time() - t0) * 1000, 1)}

    # Evolution Sandbox importable
    t0 = time.time()
    try:
        import importlib
        importlib.import_module("app.core.evolution.evolution_sandbox")
        active_checks["evolution_sandbox_importable"] = {"pass": True, "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        active_checks["evolution_sandbox_importable"] = {"pass": False, "latency_ms": round((time.time() - t0) * 1000, 1)}

    # ActionRegistry has tools
    t0 = time.time()
    try:
        from app.core.tools.action_module import action_registry
        tools = getattr(action_registry, 'list_all', None)
        if tools:
            count = len(tools())
        else:
            count = len(getattr(action_registry, '_tools', {}))
        active_checks["action_registry_has_tools"] = {"pass": count > 0, "latency_ms": round((time.time() - t0) * 1000, 1), "tool_count": count}
    except Exception:
        active_checks["action_registry_has_tools"] = {"pass": False, "latency_ms": round((time.time() - t0) * 1000, 1)}

    # DomainCircuitBreaker response
    t0 = time.time()
    try:
        if domain_cb:
            domain_cb.get_domain_health()
            active_checks["domain_circuit_breaker_response"] = {"pass": True, "latency_ms": round((time.time() - t0) * 1000, 1)}
        else:
            active_checks["domain_circuit_breaker_response"] = {"pass": False, "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        active_checks["domain_circuit_breaker_response"] = {"pass": False, "latency_ms": round((time.time() - t0) * 1000, 1)}

    overall_status = "healthy"
    open_domains = [d for d, h in domain_health.items() if h.get("is_open")]
    if open_domains:
        overall_status = "degraded"
    if len(open_domains) >= 3:
        overall_status = "critical"
    active_flag = status.get("active", False)
    last_cycle = status.get("last_cycle_at")
    if active_flag and last_cycle and (now - float(last_cycle)) > 300:
        overall_status = "degraded"

    return {
        "overall_status": overall_status,
        "active": active_flag,
        "last_cycle_at": last_cycle,
        "cycle_count": status.get("cycle_count", 0),
        "domain_health": domain_health,
        "active_goals_count": active_goals_count,
        "throttle": {
            "action_count_minute": getattr(service, '_action_count_minute', 0),
            "action_count_hour": getattr(service, '_action_count_hour', 0),
            "max_per_minute": getattr(service, 'MAX_ACTIONS_PER_MINUTE', 20),
            "max_per_hour": getattr(service, 'MAX_ACTIONS_PER_HOUR', 200),
        },
        "active_checks": active_checks,
    }


@router.get("/maturity", summary="Autonomy maturity score based on implemented phases")
async def get_autonomy_maturity(request: Request):
    components = {
        "sandbox": ("backend.app.core.evolution.evolution_sandbox", 10),
        "namespace_isolation": ("backend.app.core.tools.action_module", 10),
        "governance": ("backend.app.core.autonomy.goal_conflict_detector", 10),
        "resilience": ("backend.app.core.autonomy.domain_circuit_breaker", 10),
        "observability": ("backend.app.core.autonomy.goal_metrics", 10),
        "scale": ("backend.app.core.autonomy.knowledge_federation", 10),
        "hardening": ("backend.app.core.autonomy.safety_plan_validator", 10),
        "tests": ("backend.tests.unit.test_evolution_sandbox", 10),
        "documentation": ("documentation.autonomy_architecture", 5),
        "intelligence": ("backend.app.core.autonomy.decision_quality_tracker", 10),
        "cost_governance": ("backend.app.core.autonomy.autonomy_cost_tracker", 5),
    }

    total = 0
    max_score = sum(score for _, score in components.values())
    breakdown = {}

    import importlib
    for name, (module_path, score) in components.items():
        try:
            importlib.import_module(module_path)
            present = True
            total += score
        except (ImportError, ModuleNotFoundError):
            present = False
        breakdown[name] = {"present": present, "score": score if present else 0}

    return {
        "maturity_score": total,
        "max_score": max_score,
        "phases_completed": 11,
        "components": breakdown,
    }
