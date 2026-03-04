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
async def test_sse_slot_limit_per_channel_user(monkeypatch):
    monkeypatch.setenv("CHAT_SSE_MAX_CONNECTIONS_PER_USER", "1")
    monkeypatch.setenv("CHAT_SSE_MAX_CHAT_STREAMS_PER_USER", "1")
    monkeypatch.setenv("CHAT_SSE_MAX_AGENT_EVENT_STREAMS_PER_USER", "1")
    monkeypatch.setenv("CHAT_SSE_MAX_GLOBAL_CONNECTIONS", "10")

    event_slot = await acquire_sse_slot("subrouter-user", channel="agent_events")
    chat_slot = await acquire_sse_slot("subrouter-user", channel="chat_stream")
    try:
        with pytest.raises(HTTPException) as exc:
            await acquire_sse_slot("subrouter-user", channel="chat_stream")
        assert exc.value.status_code == 429
    finally:
        await release_sse_slot(chat_slot, channel="chat_stream")
        await release_sse_slot(event_slot, channel="agent_events")


@pytest.mark.asyncio
async def test_sse_slot_limit_global_across_channels(monkeypatch):
    monkeypatch.setenv("CHAT_SSE_MAX_CHAT_STREAMS_PER_USER", "5")
    monkeypatch.setenv("CHAT_SSE_MAX_AGENT_EVENT_STREAMS_PER_USER", "5")
    monkeypatch.setenv("CHAT_SSE_MAX_GLOBAL_CONNECTIONS", "1")

    slot = await acquire_sse_slot("subrouter-user-1", channel="agent_events")
    try:
        with pytest.raises(HTTPException) as exc:
            await acquire_sse_slot("subrouter-user-2", channel="chat_stream")
        assert exc.value.status_code == 429
    finally:
        await release_sse_slot(slot, channel="agent_events")
