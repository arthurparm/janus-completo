from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.memory.memory_core as memory_core_module
from app.core.memory.memory_core import MemoryCore
from app.models.schemas import Experience


class _Settings:
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    MEMORY_VECTOR_SIZE = 1536
    MEMORY_SHORT_TTL_SECONDS = 600
    MEMORY_SHORT_MAX_ITEMS = 512
    MEMORY_QUOTA_WINDOW_SECONDS = 3600
    MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 2
    MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 1024
    MEMORY_QUOTA_MAX_ITEMS_SELF_STUDY = 1
    MEMORY_QUOTA_MAX_BYTES_SELF_STUDY = 1024
    MEMORY_MAX_CONTENT_CHARS = 20000


def _exp(
    *,
    exp_id: str,
    content: str,
    origin: str,
    retention_policy: str = "rolling_window",
    strong_memory: bool = False,
    stability_score: float = 0.3,
    timestamp: str = "2026-03-17T10:00:00+00:00",
) -> Experience:
    return Experience(
        id=exp_id,
        type="episodic",
        content=content,
        timestamp=timestamp,
        metadata={
            "origin": origin,
            "retention_policy": retention_policy,
            "strong_memory": strong_memory,
            "stability_score": stability_score,
        },
    )


@pytest.mark.asyncio
async def test_smart_eviction_removes_oldest_chat_memory(monkeypatch):
    mock_client = AsyncMock()
    monkeypatch.setattr(memory_core_module, "aembed_text", AsyncMock(return_value=[0.1] * 1536))

    settings = _Settings()
    settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 1
    memory = MemoryCore(client=mock_client, circuit_breaker=MagicMock(), config=settings)

    first = _exp(
        exp_id="chat-1",
        content="old item",
        origin="chat.index_interaction",
        timestamp="2026-03-17T10:00:00+00:00",
    )
    second = _exp(
        exp_id="chat-2",
        content="new item",
        origin="chat.index_interaction",
        timestamp="2026-03-17T10:01:00+00:00",
    )

    await memory.amemorize(first)
    await memory.amemorize(second)

    delete_args = mock_client.delete.await_args.kwargs
    assert delete_args["collection_name"] == memory.collection_name
    assert delete_args["points_selector"].points == [memory._ensure_valid_point_id("chat-1")]
    assert memory._quota["chat.index_interaction"]["items"] == 1


@pytest.mark.asyncio
async def test_smart_eviction_prefers_rolling_window_over_persistent(monkeypatch):
    mock_client = AsyncMock()
    monkeypatch.setattr(memory_core_module, "aembed_text", AsyncMock(return_value=[0.1] * 1536))

    memory = MemoryCore(client=mock_client, circuit_breaker=MagicMock(), config=_Settings())

    persistent = _exp(
        exp_id="chat-persistent",
        content="keep me",
        origin="chat.index_interaction",
        retention_policy="persistent",
        stability_score=0.95,
        timestamp="2026-03-17T10:00:00+00:00",
    )
    rolling = _exp(
        exp_id="chat-rolling",
        content="drop me",
        origin="chat.index_interaction",
        retention_policy="rolling_window",
        stability_score=0.2,
        timestamp="2026-03-17T10:01:00+00:00",
    )
    incoming = _exp(
        exp_id="chat-new",
        content="incoming",
        origin="chat.index_interaction",
        retention_policy="rolling_window",
        stability_score=0.2,
        timestamp="2026-03-17T10:02:00+00:00",
    )

    await memory.amemorize(persistent)
    await memory.amemorize(rolling)
    await memory.amemorize(incoming)

    delete_args = mock_client.delete.await_args.kwargs
    assert delete_args["points_selector"].points == [memory._ensure_valid_point_id("chat-rolling")]


@pytest.mark.asyncio
async def test_smart_eviction_protects_self_study_strong_memory(monkeypatch):
    mock_client = AsyncMock()
    monkeypatch.setattr(memory_core_module, "aembed_text", AsyncMock(return_value=[0.1] * 1536))

    memory = MemoryCore(client=mock_client, circuit_breaker=MagicMock(), config=_Settings())

    protected = _exp(
        exp_id="study-1",
        content="indexed code memory",
        origin="self_study",
        retention_policy="persistent",
        strong_memory=True,
        stability_score=0.99,
    )
    incoming = _exp(
        exp_id="study-2",
        content="new indexed code memory",
        origin="self_study",
        retention_policy="rolling_window",
        strong_memory=True,
        stability_score=0.95,
        timestamp="2026-03-17T10:01:00+00:00",
    )

    await memory.amemorize(protected)
    with pytest.raises(ValueError, match="item quota exceeded"):
        await memory.amemorize(incoming)

    assert mock_client.delete.await_count == 0
