import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.chat import router
from app.api.v1.endpoints.chat.deps import acquire_sse_slot, release_sse_slot


def test_chat_router_preserves_expected_public_paths():
    paths = {route.path for route in router.routes}
    assert "/start" in paths
    assert "/message" in paths
    assert "/conversations" in paths
    assert "/{conversation_id}/history" in paths
    assert "/{conversation_id}/history/paginated" in paths
    assert "/stream/{conversation_id}" in paths
    assert "/{conversation_id}/trace" in paths
    assert "/{conversation_id}/events" in paths
    assert "/{conversation_id}/rename" in paths
    assert "/{conversation_id}" in paths
    assert "/health" in paths


@pytest.mark.asyncio
async def test_sse_slot_limit_per_user(monkeypatch):
    monkeypatch.setenv("CHAT_SSE_MAX_CONNECTIONS_PER_USER", "1")
    monkeypatch.setenv("CHAT_SSE_MAX_GLOBAL_CONNECTIONS", "10")

    slot = await acquire_sse_slot("subrouter-user")
    try:
        with pytest.raises(HTTPException) as exc:
            await acquire_sse_slot("subrouter-user")
        assert exc.value.status_code == 429
    finally:
        await release_sse_slot(slot)
