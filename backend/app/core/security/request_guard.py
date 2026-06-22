from __future__ import annotations

from app.config import settings
from fastapi import HTTPException, Request, status


def get_request_actor_id(request: Request | None) -> str | None:
    """
    Extrai o actor_user_id do request.state.

    Este é o identificador de ator (usuário humano ou system actor) materializado
    pelo middleware de binding (ver app/main.py).
    """
    if request is None:
        return None
    try:
        actor = getattr(request.state, "actor_user_id", None)
        return str(actor) if actor else None
    except Exception:
        return None


def require_authenticated_actor_id(request: Request) -> str:
    """
    Garante que existe um ator autenticado no contexto da requisição.

    Regras:
    - valida a existência do actor_user_id
    - aplica validação de API key quando configurada
    """
    actor = get_request_actor_id(request)
    require_api_key(request)
    if actor:
        return actor
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_admin_actor(request: Request) -> str:
    """
    Guard administrativo (RBAC):
    - exige autenticação (actor_user_id)
    - exige role ADMIN no banco
    - bloqueia system actor (role SYSTEM) para separar identidade técnica de usuário humano
    """
    actor = require_authenticated_actor_id(request)
    try:
        actor_id = int(actor)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc

    try:
        from app.repositories.user_repository import UserRepository

        repo = UserRepository()
        if repo.has_role(actor_id, getattr(settings, "SYSTEM_USER_ROLE", "SYSTEM")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if repo.is_admin(actor_id):
            return actor
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authz check failed") from exc

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def require_same_user_or_admin(request: Request, target_user_id: str | int) -> str:
    """
    Guard para recursos por usuário:
    - permite acesso ao próprio usuário (owner)
    - permite acesso a admin (role ADMIN)
    """
    actor = require_authenticated_actor_id(request)
    if str(target_user_id) == str(actor):
        return actor

    try:
        actor_id = int(actor)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc

    try:
        from app.repositories.user_repository import UserRepository

        repo = UserRepository()
        if repo.is_admin(actor_id):
            return actor
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authz check failed") from exc

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def resolve_user_scope_id(request: Request | None, explicit_user_id: str | None) -> str | None:
    if explicit_user_id:
        return str(explicit_user_id)
    return get_request_actor_id(request)


def require_api_key(request: Request) -> None:
    expected_key = getattr(settings, "PUBLIC_API_KEY", None)
    if expected_key:
        provided_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if provided_key != expected_key and provided_key != f"Bearer {expected_key}":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

