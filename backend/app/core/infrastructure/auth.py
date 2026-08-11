from __future__ import annotations

import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import jwt
import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request
from jwt import PyJWKClient

from app.config import settings
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)
_ALGORITHM = "RS256"
_REQUIRED_CLAIMS = ("sub", "iss", "aud", "exp", "iat", "nbf", "jti", "typ")
_REJECTED_KEY_HEADERS = frozenset({"jku", "x5u", "jwk"})


class TokenValidationError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__("token validation failed")
        self.reason = reason


def _deployed() -> bool:
    return str(settings.ENVIRONMENT).strip().lower() in {
        "production",
        "staging",
        "homologation",
    }


def _canonical_issuer(value: str) -> str:
    return str(value).strip().rstrip("/")


@lru_cache(maxsize=8)
def _jwks_client(url: str, cache_seconds: int) -> PyJWKClient:
    parsed = urlparse(url)
    local_development_http = (
        not _deployed()
        and parsed.scheme.lower() == "http"
        and (parsed.hostname or "").lower()
        in {"localhost", "127.0.0.1", "::1", "janus-dev-idp"}
    )
    if parsed.scheme.lower() != "https" and not local_development_http:
        raise TokenValidationError("jwks_url_not_https")
    return PyJWKClient(
        url,
        cache_keys=True,
        max_cached_keys=16,
        cache_jwk_set=True,
        lifespan=max(30, int(cache_seconds)),
    )


def _header(token: str) -> dict[str, Any]:
    try:
        header = cast(dict[str, Any], jwt.get_unverified_header(token))
    except jwt.PyJWTError as exc:
        raise TokenValidationError("malformed_header") from exc
    if header.get("alg") != _ALGORITHM:
        raise TokenValidationError("algorithm_not_allowed")
    if not isinstance(header.get("kid"), str) or not str(header["kid"]).strip():
        raise TokenValidationError("kid_required")
    if _REJECTED_KEY_HEADERS.intersection(header):
        raise TokenValidationError("untrusted_key_reference")
    return header


def _decode_external(
    token: str,
    *,
    issuer: str,
    audience: str,
    jwks_url: str,
    max_ttl_seconds: int,
) -> dict[str, Any]:
    _header(token)
    try:
        signing_key = _jwks_client(jwks_url, settings.OIDC_JWKS_CACHE_SECONDS).get_signing_key_from_jwt(
            token
        )
        claims = cast(
            dict[str, Any],
            jwt.decode(
                token,
                signing_key.key,
                algorithms=[_ALGORITHM],
                issuer=str(issuer).strip(),
                audience=audience,
                leeway=int(settings.OIDC_CLOCK_SKEW_SECONDS),
                options={"require": list(_REQUIRED_CLAIMS), "strict_aud": True},
            ),
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError(type(exc).__name__) from exc
    if claims.get("typ") != "at+jwt":
        raise TokenValidationError("invalid_token_type")
    if str(claims.get("iss", "")) != str(issuer).strip():
        raise TokenValidationError("invalid_issuer")
    try:
        issued_at = int(claims["iat"])
        expires_at = int(claims["exp"])
    except (TypeError, ValueError) as exc:
        raise TokenValidationError("invalid_time_claim") from exc
    if expires_at - issued_at > int(max_ttl_seconds):
        raise TokenValidationError("token_ttl_exceeded")
    if issued_at > int(time.time()) + int(settings.OIDC_CLOCK_SKEW_SECONDS):
        raise TokenValidationError("issued_in_future")
    if not str(claims.get("sub", "")).strip():
        raise TokenValidationError("invalid_subject")
    if not isinstance(claims.get("jti"), str) or not str(claims["jti"]).strip():
        raise TokenValidationError("invalid_jti")
    return claims


def _claim_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(item for item in value.split() if item)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item).strip())
    return ()


def _authenticate_user(token: str, *, trace_id: str) -> ActorContext:
    claims = _decode_external(
        token,
        issuer=settings.OIDC_ISSUER,
        audience=settings.OIDC_USER_AUDIENCE,
        jwks_url=settings.OIDC_JWKS_URL,
        max_ttl_seconds=settings.OIDC_USER_MAX_TTL_SECONDS,
    )
    groups = _claim_values(claims.get(settings.OIDC_GROUPS_CLAIM))
    email_verified = claims.get("email_verified") is True
    user, jit_created = UserRepository().resolve_or_provision_external_identity(
        issuer=str(claims["iss"]),
        subject=str(claims["sub"]),
        email=str(claims["email"]) if claims.get("email") else None,
        email_verified=email_verified,
        display_name=str(claims.get("name") or claims.get("preferred_username") or "") or None,
        admin_group_authorized=bool(
            settings.OIDC_ADMIN_GROUP and settings.OIDC_ADMIN_GROUP in groups
        ),
    )
    roles = {"USER"}
    if settings.OIDC_ADMIN_GROUP and settings.OIDC_ADMIN_GROUP in groups:
        roles.add("ADMIN")
    if jit_created:
        try:
            from app.repositories.observability_repository import record_audit_event_direct

            record_audit_event_direct(
                endpoint="oidc_jit",
                action="external_identity_provisioned",
                status="success",
                user_id=int(user.id),
                details_json={
                    "issuer": _canonical_issuer(str(claims["iss"])),
                    "admin_group_authorized": "ADMIN" in roles,
                },
            )
        except Exception:
            logger.error("oidc_jit_audit_failed", user_id=int(user.id), exc_info=True)
    return ActorContext.authenticated(
        actor_id=int(user.id),
        actor_type=ActorType.HUMAN,
        roles=roles,
        auth_method=AuthMethod.OIDC,
        trace_id=trace_id,
        issuer=_canonical_issuer(str(claims["iss"])),
        subject=str(claims["sub"]),
        scopes=_claim_values(claims.get("scope")),
        groups=groups,
    )


def _authenticate_service(token: str, *, trace_id: str, request: Request) -> ActorContext:
    claims = _decode_external(
        token,
        issuer=settings.OIDC_SERVICE_ISSUER,
        audience=settings.OIDC_SERVICE_AUDIENCE,
        jwks_url=settings.OIDC_SERVICE_JWKS_URL,
        max_ttl_seconds=settings.OIDC_SERVICE_MAX_TTL_SECONDS,
    )
    subject = str(claims["sub"])
    client_id = str(claims.get("client_id") or claims.get("azp") or "").strip()
    if not client_id:
        raise TokenValidationError("client_id_required")
    if claims.get("client_id") and claims.get("azp") and claims["client_id"] != claims["azp"]:
        raise TokenValidationError("client_id_azp_mismatch")
    token_scopes = set(_claim_values(claims.get("scope") or claims.get("scp")))

    configured = settings.OIDC_SERVICE_PRINCIPALS.get(client_id)
    if configured is not None:
        if subject != client_id:
            raise TokenValidationError("service_subject_mismatch")
        granted_scopes = set(configured)
    else:
        resolved = UserRepository().get_active_service_principal(
            issuer=_canonical_issuer(str(claims["iss"])), subject=subject, client_id=client_id
        )
        if resolved is None:
            raise TokenValidationError("service_not_registered")
        _, granted_scopes = resolved
    if not token_scopes.issubset(granted_scopes):
        raise TokenValidationError("unregistered_service_scope")

    delegated_subject = None
    delegation_id = None
    if client_id == settings.ADMIN_FACADE_CLIENT_ID:
        delegated_subject = request.headers.get("X-Janus-Delegated-Subject") or None
        delegation_id = request.headers.get("X-Janus-Delegation-ID") or None
        if not delegated_subject or not delegation_id:
            raise TokenValidationError("delegation_context_required")
        try:
            uuid.UUID(delegation_id)
        except ValueError as exc:
            raise TokenValidationError("invalid_delegation_id") from exc
        policy = getattr(request.state, "endpoint_policy", None)
        if policy is None or not UserRepository().has_active_admin_delegation(
            delegation_id=delegation_id,
            human_subject=delegated_subject,
            service_client_id=client_id,
            operation_id=str(policy.operation_id),
            trace_id=trace_id,
        ):
            raise TokenValidationError("delegation_not_registered")
    elif request.headers.get("X-Janus-Delegated-Subject"):
        raise TokenValidationError("delegation_not_allowed")
    return ActorContext.authenticated(
        actor_id=subject,
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id=trace_id,
        issuer=_canonical_issuer(str(claims["iss"])),
        subject=subject,
        client_id=client_id,
        scopes=token_scopes,
        delegated_subject=delegated_subject,
        delegation_id=delegation_id,
    )


def get_actor_context(request: Request) -> ActorContext | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    trace_id = str(getattr(request.state, "trace_id", "") or uuid.uuid4().hex)
    errors: list[str] = []
    for validator in (_authenticate_user,):
        try:
            return validator(token, trace_id=trace_id)
        except Exception as exc:
            errors.append(getattr(exc, "reason", type(exc).__name__))
    try:
        return _authenticate_service(token, trace_id=trace_id, request=request)
    except Exception as exc:
        errors.append(getattr(exc, "reason", type(exc).__name__))
    logger.info("jwt_rejected", reasons=errors, trace_id=trace_id)
    return None


_INTERNAL_TEST_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_INTERNAL_TEST_PUBLIC_KEY = _INTERNAL_TEST_PRIVATE_KEY.public_key()


def _internal_keys() -> tuple[Any, Any]:
    private_path = settings.INTERNAL_ACTOR_PRIVATE_KEY_PATH
    public_path = settings.INTERNAL_ACTOR_PUBLIC_KEY_PATH
    if private_path and public_path:
        private_key = serialization.load_pem_private_key(Path(private_path).read_bytes(), password=None)
        public_key = serialization.load_pem_public_key(Path(public_path).read_bytes())
        return private_key, public_key
    if _deployed():
        raise RuntimeError("Internal actor RS256 keypair is required in deployed environments")
    return _INTERNAL_TEST_PRIVATE_KEY, _INTERNAL_TEST_PUBLIC_KEY


def create_actor_envelope(actor: ActorContext, *, audience: str) -> str:
    private_key, _ = _internal_keys()
    now = int(time.time())
    return cast(
        str,
        jwt.encode(
            {
                "sub": actor.actor_id,
                "iss": settings.INTERNAL_ACTOR_ISSUER,
                "aud": audience,
                "exp": now + settings.ACTOR_CONTEXT_ENVELOPE_TTL_SECONDS,
                "iat": now,
                "nbf": now,
                "jti": uuid.uuid4().hex,
                "typ": "actor-context+jwt",
                "actor_type": actor.actor_type.value,
                "roles": list(actor.roles),
                "trace_id": actor.trace_id,
                "resource_owner": actor.resource_owner,
            },
            private_key,
            algorithm=_ALGORITHM,
            headers={"kid": settings.INTERNAL_ACTOR_KEY_ID},
        ),
    )


def verify_actor_envelope(token: str, *, audience: str) -> ActorContext | None:
    try:
        header = _header(token)
        if header["kid"] != settings.INTERNAL_ACTOR_KEY_ID and header["kid"] != "janus-development":
            return None
        _, public_key = _internal_keys()
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[_ALGORITHM],
            audience=audience,
            issuer=settings.INTERNAL_ACTOR_ISSUER,
            options={"require": list(_REQUIRED_CLAIMS)},
        )
        if claims.get("typ") != "actor-context+jwt":
            return None
        actor = ActorContext.authenticated(
            actor_id=claims["sub"],
            roles=claims.get("roles") or (),
            auth_method=AuthMethod.INTERNAL,
            trace_id=claims["trace_id"],
            actor_type=ActorType(str(claims.get("actor_type") or ActorType.SYSTEM)),
        )
        return actor.bind_resource_owner(claims["resource_owner"]) if claims.get(
            "resource_owner"
        ) is not None else actor
    except Exception:
        return None


def get_actor_user_id(request: Request) -> int | None:
    actor = getattr(getattr(request, "state", None), "actor_context", None)
    try:
        if actor is not None and actor.actor_type is ActorType.HUMAN:
            return int(actor.actor_id)
        return None
    except (TypeError, ValueError):
        return None
