from types import SimpleNamespace

import pytest
from app.planes.knowledge import adapters as adapters_module
from app.planes.knowledge.adapters import QdrantKnowledgeAdapter
from app.planes.knowledge.experimental_index import _point_matches_filters


@pytest.mark.asyncio
async def test_qdrant_chat_search_requires_user_filter(monkeypatch):
    captured = {}

    class _Client:
        async def query_points(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(points=[])

    async def _collection(name):
        return name

    async def _embed(_query):
        return [0.1]

    monkeypatch.setattr(adapters_module, "aget_or_create_collection", _collection)
    monkeypatch.setattr(adapters_module, "aembed_text", _embed)
    monkeypatch.setattr(adapters_module, "get_async_qdrant_client", lambda: _Client())

    await QdrantKnowledgeAdapter().search_user_chat(
        query="contexto",
        user_id="user-1",
        session_id=None,
        role=None,
        limit=5,
        min_score=None,
    )

    conditions = {
        condition.key: condition.match.value
        for condition in captured["query_filter"].must
    }
    assert conditions == {"metadata.user_id": "user-1"}


def test_experimental_filter_rejects_other_or_unowned_users():
    owned = {"metadata": {"user_id": "user-1", "type": "chat_msg"}}
    other = {"metadata": {"user_id": "user-2", "type": "chat_msg"}}
    legacy = {"metadata": {"type": "chat_msg"}}

    assert _point_matches_filters(owned, {"user_id": "user-1"}) is True
    assert _point_matches_filters(other, {"user_id": "user-1"}) is False
    assert _point_matches_filters(legacy, {"user_id": "user-1"}) is False
