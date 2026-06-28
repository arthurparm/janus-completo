from fastapi import HTTPException, Request, status

from app.planes.knowledge import KnowledgeFacade


def get_knowledge_facade(request: Request) -> KnowledgeFacade:
    return request.app.state.knowledge_facade


def resolve_knowledge_user_id(request: Request | None, explicit_user_id: str | None) -> str:
    if request is not None:
        actor = getattr(request.state, "actor_user_id", None)
        actor_str = str(actor).strip() if actor is not None else ""
        explicit = str(explicit_user_id).strip() if explicit_user_id is not None else ""
        if actor_str:
            return explicit if explicit and explicit == actor_str else actor_str

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
