from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import productivity_oauth_state_registry_service as registry


class _RedisClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[dict[str, object]] = []

    async def set(self, key: str, value: str, **kwargs: object) -> bool:
        self.set_calls.append({"key": key, "value": value, **kwargs})
        if kwargs.get("nx") and key in self.values:
            return False
        self.values[key] = value
        return True

    async def eval(self, _script: str, _key_count: int, key: str) -> str | None:
        return self.values.pop(key, None)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_state_registry_stores_only_digest_and_consumes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RedisClient()
    monkeypatch.setattr(
        registry,
        "get_redis_manager",
        lambda: SimpleNamespace(client=client),
    )
    state = "signed-sensitive-oauth-state"

    await registry.register_google_oauth_state(state, ttl_seconds=600)
    await registry.consume_google_oauth_state(state)

    call = client.set_calls[0]
    assert state not in str(call["key"])
    assert call["value"] == "issued"
    assert call["ex"] == 600
    assert call["nx"] is True
    with pytest.raises(registry.OAuthStateAlreadyConsumedError):
        await registry.consume_google_oauth_state(state)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_state_registry_rejects_duplicate_issuance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _RedisClient()
    monkeypatch.setattr(
        registry,
        "get_redis_manager",
        lambda: SimpleNamespace(client=client),
    )

    await registry.register_google_oauth_state("same-state")

    with pytest.raises(registry.OAuthStateRegistryUnavailableError):
        await registry.register_google_oauth_state("same-state")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_state_registry_fails_closed_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _UnavailableClient:
        async def set(self, *_args: object, **_kwargs: object) -> None:
            raise ConnectionError("offline")

        async def eval(self, *_args: object, **_kwargs: object) -> None:
            raise ConnectionError("offline")

    monkeypatch.setattr(
        registry,
        "get_redis_manager",
        lambda: SimpleNamespace(client=_UnavailableClient()),
    )

    with pytest.raises(registry.OAuthStateRegistryUnavailableError):
        await registry.register_google_oauth_state("state")
    with pytest.raises(registry.OAuthStateRegistryUnavailableError):
        await registry.consume_google_oauth_state("state")
