from types import SimpleNamespace

import pytest

from app.core.memory.generative_memory import GenerativeMemoryService


@pytest.mark.asyncio
async def test_retrieve_memories_reads_user_scoped_collection(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_embed_text(query: str) -> list[float]:
        assert query == "objetivas"
        return [0.25, 0.75]

    async def fake_aget_or_create_collection(name: str) -> str:
        captured["collection_name"] = name
        return name

    class FakeClient:
        async def query_points(self, **kwargs):
            captured["query_kwargs"] = kwargs
            return SimpleNamespace(
                points=[
                    SimpleNamespace(
                        id="exp-9-1",
                        score=0.91,
                        payload={
                            "content": "Admin validacao: usuario prefere respostas objetivas e com checklist final.",
                            "type": "episodic",
                            "timestamp": "2026-03-06T17:00:00+00:00",
                            "ts_ms": 1772787600000,
                            "metadata": {
                                "conversation_id": "6",
                                "importance": 8,
                                "last_accessed_at": 1772787600000,
                                "access_count": 1,
                                "origin": "frontend.generative_memory_panel",
                            },
                        })
                ]
            )

    monkeypatch.setattr(
        "app.core.memory.generative_memory.aembed_text",
        fake_embed_text)
    monkeypatch.setattr(
        "app.core.memory.generative_memory.aget_or_create_collection",
        fake_aget_or_create_collection)
    monkeypatch.setattr(
        "app.core.memory.generative_memory.get_async_qdrant_client",
        lambda: FakeClient())

    service = GenerativeMemoryService()
    result = await service.retrieve_memories(
        "objetivas",
        conversation_id="6",
        limit=5)

    assert captured["collection_name"] == "global_memory"
    query_kwargs = captured["query_kwargs"]
    assert query_kwargs["collection_name"] == "global_memory"
    assert query_kwargs["limit"] == 25

    must = query_kwargs["query_filter"].must
    filter_keys = {condition.key for condition in must}
    assert filter_keys == { "metadata.conversation_id"}

    assert len(result) == 1
    memory = result[0]
    assert memory.id == "exp-9-1"
    assert memory.metadata["origin"] == "frontend.generative_memory_panel"
    assert memory.score is not None
    assert memory.score > 0.91
