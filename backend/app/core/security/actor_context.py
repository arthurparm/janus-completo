from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ActorType(StrEnum):
    HUMAN = "human"
    SYSTEM = "system"


class AuthMethod(StrEnum):
    LOCAL = "local"
    FIREBASE = "firebase"
    SUPABASE = "supabase"
    INTERNAL = "internal"


_ACTOR_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True, init=False)
class ActorContext:
    """Authenticated request identity. This is the only identity authority."""

    actor_id: str
    actor_type: ActorType
    roles: tuple[str, ...]
    auth_method: str
    trace_id: str
    resource_owner: str | None = None

    def __init__(
        self,
        *,
        actor_id: str,
        actor_type: ActorType,
        roles: tuple[str, ...],
        auth_method: str,
        trace_id: str,
        resource_owner: str | None = None,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _ACTOR_FACTORY_TOKEN:
            raise TypeError("ActorContext must be created by an authenticated factory")
        object.__setattr__(self, "actor_id", actor_id)
        object.__setattr__(self, "actor_type", actor_type)
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "auth_method", auth_method)
        object.__setattr__(self, "trace_id", trace_id)
        object.__setattr__(self, "resource_owner", resource_owner)

    @classmethod
    def authenticated(
        cls,
        *,
        actor_id: str | int,
        roles: Iterable[str],
        auth_method: str,
        trace_id: str,
        actor_type: ActorType = ActorType.HUMAN,
    ) -> ActorContext:
        normalized_roles = tuple(sorted({str(role).upper() for role in roles if str(role).strip()}))
        return cls(
            actor_id=str(actor_id),
            actor_type=actor_type,
            roles=normalized_roles,
            auth_method=str(auth_method),
            trace_id=str(trace_id),
            _factory_token=_ACTOR_FACTORY_TOKEN,
        )

    @classmethod
    def system(
        cls,
        *,
        actor_id: str,
        roles: Iterable[str],
        trace_id: str,
    ) -> ActorContext:
        return cls.authenticated(
            actor_id=actor_id,
            roles=roles,
            auth_method=AuthMethod.INTERNAL,
            trace_id=trace_id,
            actor_type=ActorType.SYSTEM,
        )

    def bind_resource_owner(self, owner_id: str | int) -> ActorContext:
        return ActorContext(
            actor_id=self.actor_id,
            actor_type=self.actor_type,
            roles=self.roles,
            auth_method=self.auth_method,
            trace_id=self.trace_id,
            resource_owner=str(owner_id),
            _factory_token=_ACTOR_FACTORY_TOKEN,
        )

    def has_role(self, role: str) -> bool:
        return str(role).upper() in self.roles


CURRENT_ACTOR_CONTEXT: ContextVar[ActorContext | None] = ContextVar(
    "current_actor_context", default=None
)


def get_current_actor_context() -> ActorContext | None:
    return CURRENT_ACTOR_CONTEXT.get()
