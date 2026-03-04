from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security.request_guard import require_admin_actor, require_authenticated_actor_id
from app.services.collaboration_service import (
    AgentNotFoundError,
    CollaborationService,
    get_collaboration_service,
)

router = APIRouter(
    prefix="/collaboration",
    tags=["Collaboration - Workspace"],
    dependencies=[Depends(require_authenticated_actor_id)],
)


class AddArtifactRequest(BaseModel):
    key: str = Field(..., description="Identificador único do artefato")
    value: Any = Field(..., description="Conteúdo do artefato")
    author: str | None = Field(None, description="ID do agente autor")


@router.post("/workspace/artifacts/add")
def add_artifact(
    payload: AddArtifactRequest, service: CollaborationService = Depends(get_collaboration_service)
):
    try:
        result = service.add_artifact(
            key=payload.key, value=payload.value, author=payload.author or ""
        )
        return {"message": "Artifact added", "data": result}
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/workspace/artifacts/{key}")
def get_artifact(key: str, service: CollaborationService = Depends(get_collaboration_service)):
    value = service.get_artifact(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"key": key, "value": value}


class SendMessageRequest(BaseModel):
    from_agent: str = Field(..., description="ID do agente remetente")
    to_agent: str = Field(..., description="ID do agente destinatário")
    content: str = Field(..., description="Conteúdo da mensagem")


@router.post("/workspace/messages/send")
def send_message(
    payload: SendMessageRequest, service: CollaborationService = Depends(get_collaboration_service)
):
    try:
        msg = service.send_message(payload.from_agent, payload.to_agent, payload.content)
        return {"message": "Message sent", "data": msg}
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/workspace/messages/{agent_id}")
def get_messages_for(
    agent_id: str, service: CollaborationService = Depends(get_collaboration_service)
):
    try:
        msgs = service.get_messages_for(agent_id)
        return {"agent_id": agent_id, "messages": msgs}
    except AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/system/shutdown",
    tags=["Collaboration - System"],
    dependencies=[Depends(require_admin_actor)],
)
def shutdown_system(service: CollaborationService = Depends(get_collaboration_service)):
    service.shutdown_system()
    return {"message": "System shutdown initiated"}
