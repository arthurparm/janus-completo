from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ActorType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"
    SYSTEM = "system"  # Internal non-HTTP actor envelopes only.


class AuthMethod(StrEnum):
    OIDC = "oidc"
    CLIENT_CREDENTIALS = "client_credentials"
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
    issuer: str | None = None
    subject: str | None = None
    client_id: str | None = None
    scopes: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    delegated_subject: str | None = None
    delegation_id: str | None = None

    def __init__(
        self,
        *,
        actor_id: str,
        actor_type: ActorType,
        roles: tuple[str, ...],
        auth_method: str,
        trace_id: str,
        resource_owner: str | None = None,
        issuer: str | None = None,
        subject: str | None = None,
        client_id: str | None = None,
        scopes: tuple[str, ...] = (),
        groups: tuple[str, ...] = (),
        delegated_subject: str | None = None,
        delegation_id: str | None = None,
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
        object.__setattr__(self, "issuer", issuer)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "client_id", client_id)
        object.__setattr__(self, "scopes", tuple(sorted(set(scopes))))
        object.__setattr__(self, "groups", tuple(sorted(set(groups))))
        object.__setattr__(self, "delegated_subject", delegated_subject)
        object.__setattr__(self, "delegation_id", delegation_id)

    @classmethod
    def authenticated(
        cls,
        *,
        actor_id: str | int,
        roles: Iterable[str],
        auth_method: str,
        trace_id: str,
        actor_type: ActorType = ActorType.HUMAN,
        issuer: str | None = None,
        subject: str | None = None,
        client_id: str | None = None,
        scopes: Iterable[str] = (),
        groups: Iterable[str] = (),
        delegated_subject: str | None = None,
        delegation_id: str | None = None,
    ) -> ActorContext:
        normalized_roles = tuple(sorted({str(role).upper() for role in roles if str(role).strip()}))
        return cls(
            actor_id=str(actor_id),
            actor_type=actor_type,
            roles=normalized_roles,
            auth_method=str(auth_method),
            trace_id=str(trace_id),
            issuer=issuer,
            subject=subject,
            client_id=client_id,
            scopes=tuple(str(scope) for scope in scopes),
            groups=tuple(str(group) for group in groups),
            delegated_subject=delegated_subject,
            delegation_id=delegation_id,
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
            issuer=self.issuer,
            subject=self.subject,
            client_id=self.client_id,
            scopes=self.scopes,
            groups=self.groups,
            delegated_subject=self.delegated_subject,
            delegation_id=self.delegation_id,
            _factory_token=_ACTOR_FACTORY_TOKEN,
        )

    def has_role(self, role: str) -> bool:
        return str(role).upper() in self.roles

    def has_scopes(self, required: Iterable[str]) -> bool:
        return set(required).issubset(self.scopes)


CURRENT_ACTOR_CONTEXT: ContextVar[ActorContext | None] = ContextVar(
    "current_actor_context", default=None
)


def get_current_actor_context() -> ActorContext | None:
    return CURRENT_ACTOR_CONTEXT.get()
