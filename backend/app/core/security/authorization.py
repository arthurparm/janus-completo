from __future__ import annotations

from dataclasses import dataclass

from app.core.security.actor_context import ActorContext, ActorType
from fastapi import HTTPException, status


@dataclass(frozen=True, slots=True)
class AuthorizationService:
    admin_role: str = "ADMIN"

    def require_authenticated(self, *, actor: ActorContext | None) -> ActorContext:
        if actor is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        return actor

    def require_human_admin(self, *, actor: ActorContext | None) -> ActorContext:
        resolved = self.require_authenticated(actor=actor)
        if resolved.actor_type is not ActorType.HUMAN or not resolved.has_role(self.admin_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return resolved

    def require_service(self, *, actor: ActorContext | None) -> ActorContext:
        resolved = self.require_authenticated(actor=actor)
        if resolved.actor_type is not ActorType.SERVICE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return resolved

authorization_service = AuthorizationService()
