from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
import json
from app.repositories.pending_action_repository import PendingActionRepository
from app.repositories.autonomy_repository import AutonomyRepository
from app.core.tools.action_module import action_registry

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
async def approve(action_id: int, repo: PendingActionRepository = Depends(get_repo)):
    item = repo.get(action_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação pendente não encontrada")
    try:
        tool = action_registry.get_tool(item.tool_name)
        args = json.loads(item.args_json or "{}")
        result = await tool.arun(args) if hasattr(tool, "arun") else tool.run(args)
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
    except Exception:
        pass
    return PendingActionDTO(id=item.id, user_id=item.user_id, tool_name=item.tool_name, args_json=item.args_json, run_id=item.run_id, cycle=item.cycle, status=item.status, created_at=str(item.created_at), decided_at=str(item.decided_at) if item.decided_at else None)

@router.post("/{action_id}/reject", response_model=PendingActionDTO)
async def reject(action_id: int, repo: PendingActionRepository = Depends(get_repo)):
    item = repo.set_status(action_id, "rejected")
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ação pendente não encontrada")
    return PendingActionDTO(id=item.id, user_id=item.user_id, tool_name=item.tool_name, args_json=item.args_json, run_id=item.run_id, cycle=item.cycle, status=item.status, created_at=str(item.created_at), decided_at=str(item.decided_at) if item.decided_at else None)