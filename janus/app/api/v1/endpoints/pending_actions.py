from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
import json
from app.repositories.pending_action_repository import PendingActionRepository
from app.repositories.autonomy_repository import AutonomyRepository
from app.services.observability_service import ObservabilityService
from app.core.tools.action_module import action_registry
from app.core.autonomy.policy_engine import PolicyEngine, PolicyConfig
from app.repositories.user_repository import UserRepository, ConsentRepository

router = APIRouter(tags=["PendingActions"], prefix="/pending_actions")

def get_repo(request: Request) -> PendingActionRepository:
    return PendingActionRepository()

class PendingActionDTO(BaseModel):
    id: int
    user_id: str
    tool_name: str
    args_json: str
    run_id: Optional[int]
    cycle: Optional[int]
    status: str
    created_at: str
    decided_at: Optional[str]

@router.get("/", response_model=List[PendingActionDTO])
async def list_pending(user_id: Optional[str] = None, status: Optional[str] = "pending", repo: PendingActionRepository = Depends(get_repo)):
    items = repo.list(user_id=user_id, status=status, limit=100)
    return [PendingActionDTO(id=i.id, user_id=i.user_id, tool_name=i.tool_name, args_json=i.args_json, run_id=i.run_id, cycle=i.cycle, status=i.status, created_at=str(i.created_at), decided_at=str(i.decided_at) if i.decided_at else None) for i in items]

@router.post("/{action_id}/approve", response_model=PendingActionDTO)
async def approve(action_id: int, request: Request, repo: PendingActionRepository = Depends(get_repo)):
    item = repo.get(action_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação pendente não encontrada")
    try:
        actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
        ur = UserRepository()
        if not actor or (str(actor) != str(item.user_id) and not ur.is_admin(int(actor))):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        tool = action_registry.get_tool(item.tool_name)
        meta = action_registry.get_metadata(item.tool_name)
        args = json.loads(item.args_json or "{}")
        if not tool or not meta:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ferramenta inválida")
        policy = PolicyEngine(PolicyConfig())
        decision = policy.validate_tool_call(item.tool_name, args)
        if not decision.allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS if (decision.reason or "").lower().startswith("rate limit") else status.HTTP_403_FORBIDDEN, detail=decision.reason or "Blocked")
        scopes = [t.split(":", 1)[1] for t in (meta.tags or []) if t.startswith("scope:")]
        if scopes:
            cr = ConsentRepository()
            for sc in scopes:
                if not cr.has_consent(int(item.user_id), sc):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Consent required: {sc}")
        result = await tool.arun(**args) if hasattr(tool, "arun") else tool.run(**args)
    except Exception:
        pass
    item = repo.set_status(action_id, "approved")
    try:
        if item and item.run_id:
            ar = AutonomyRepository()
            payload_str = item.args_json
            input_preview = payload_str[:300] if isinstance(payload_str, str) else None
            input_length = len(payload_str) if isinstance(payload_str, str) else 0
            ar.add_step(run_id=item.run_id, cycle=int(item.cycle or 0), tool=item.tool_name, input_preview=input_preview, input_length=input_length, result_preview=str(result)[:500] if 'result' in locals() else None, result_length=len(str(result)) if 'result' in locals() else 0, success=True, error=None, duration_seconds=0.0)
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(item.user_id), "tool": item.tool_name, "status": "approved", "detail": {"args": item.args_json}})
    except Exception:
        pass
    return PendingActionDTO(id=item.id, user_id=item.user_id, tool_name=item.tool_name, args_json=item.args_json, run_id=item.run_id, cycle=item.cycle, status=item.status, created_at=str(item.created_at), decided_at=str(item.decided_at) if item.decided_at else None)

@router.post("/{action_id}/reject", response_model=PendingActionDTO)
async def reject(action_id: int, repo: PendingActionRepository = Depends(get_repo)):
    item = repo.set_status(action_id, "rejected")
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação pendente não encontrada")
    return PendingActionDTO(id=item.id, user_id=item.user_id, tool_name=item.tool_name, args_json=item.args_json, run_id=item.run_id, cycle=item.cycle, status=item.status, created_at=str(item.created_at), decided_at=str(item.decided_at) if item.decided_at else None)