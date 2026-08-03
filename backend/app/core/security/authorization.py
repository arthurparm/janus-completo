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

    def require_admin(self, *, actor: ActorContext | None) -> ActorContext:
        resolved = self.require_authenticated(actor=actor)
        if resolved.actor_type is ActorType.SYSTEM or not resolved.has_role(self.admin_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return resolved

    def require_owner_or_admin(
        self, *, actor: ActorContext | None, resource_owner: str | int
    ) -> ActorContext:
        resolved = self.require_authenticated(actor=actor).bind_resource_owner(resource_owner)
        if resolved.actor_id != resolved.resource_owner and not resolved.has_role(self.admin_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return resolved


authorization_service = AuthorizationService()
