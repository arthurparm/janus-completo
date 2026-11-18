from __future__ import annotations

import hashlib

from app.core.infrastructure.redis_manager import get_redis_manager

_STATE_KEY_PREFIX = "janus:oauth:state:"
_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if value then
  redis.call('DEL', KEYS[1])
end
return value
"""


class OAuthStateRegistryUnavailableError(RuntimeError):
    """The replay-protection registry is unavailable or rejected issuance."""


class OAuthStateAlreadyConsumedError(RuntimeError):
    """The OAuth state was not issued here, expired, or was already consumed."""


def _state_key(state: str) -> str:
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    return f"{_STATE_KEY_PREFIX}{digest}"


async def register_google_oauth_state(state: str, *, ttl_seconds: int = 600) -> None:
    if not state or ttl_seconds <= 0:
        raise OAuthStateRegistryUnavailableError("Invalid OAuth state registry request")
    try:
        created = await get_redis_manager().client.set(
            _state_key(state),
            "issued",
            ex=ttl_seconds,
            nx=True,
        )
    except Exception as exc:
        raise OAuthStateRegistryUnavailableError(
            "OAuth state registry unavailable"
        ) from exc
    if not created:
        raise OAuthStateRegistryUnavailableError("OAuth state could not be registered")


async def consume_google_oauth_state(state: str) -> None:
    if not state:
        raise OAuthStateAlreadyConsumedError("OAuth state was not issued")
    try:
        value = await get_redis_manager().client.eval(
            _CONSUME_SCRIPT,
            1,
            _state_key(state),
        )
    except Exception as exc:
        raise OAuthStateRegistryUnavailableError(
            "OAuth state registry unavailable"
        ) from exc
    if value is None:
        raise OAuthStateAlreadyConsumedError(
            "OAuth state expired, unknown, or already consumed"
        )
