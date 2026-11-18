from unittest.mock import AsyncMock

import pytest
from app.core.memory import generative_memory as memory_module
from app.core.memory.generative_memory import GenerativeMemoryService


@pytest.mark.asyncio
async def test_add_memory_persists_explicit_user_scope(monkeypatch):
    captured = {}

    class _MemoryCore:
        async def amemorize(self, experience):
            captured["experience"] = experience

    class _KnowledgeGraph:
        async def persist_experience_node(self, experience):
            captured["graph_experience"] = experience

    async def _memory_db():
        return _MemoryCore()

    monkeypatch.setattr(memory_module, "get_memory_db", _memory_db)
    monkeypatch.setattr(memory_module, "get_knowledge_graph_service", lambda: _KnowledgeGraph())

    service = GenerativeMemoryService()
    service._mirror_to_user_collection = AsyncMock()
    result = await service.add_memory(
        "preferencia auditavel",
        metadata={"importance": 8.0, "user_id": "untrusted-user"},
        user_id="user-1",
    )

    assert result.metadata["user_id"] == "user-1"
    assert captured["experience"].metadata["user_id"] == "user-1"
    assert captured["graph_experience"].metadata["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_add_memory_rejects_empty_user_scope():
    with pytest.raises(ValueError, match="user_id is required"):
        await GenerativeMemoryService().add_memory(
            "memoria sem proprietario",
            metadata={"importance": 8.0},
            user_id="",
        )
