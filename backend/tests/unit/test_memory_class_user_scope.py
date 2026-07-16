import pytest
from app.services import procedural_memory_service as procedural_module
from app.services import user_preference_memory_service as preference_module
from app.services.procedural_memory_service import ProceduralMemoryService
from app.services.user_preference_memory_service import UserPreferenceMemoryService


class _ScrollClient:
    def __init__(self):
        self.filter = None

    async def scroll(self, **kwargs):
        self.filter = kwargs["scroll_filter"]
        return [], None


async def _collection(name):
    return name


def _filter_values(qfilter):
    return {
        condition.key: condition.match.value
        for condition in qfilter.must
    }


@pytest.mark.asyncio
async def test_preference_lookup_requires_user_filter(monkeypatch):
    client = _ScrollClient()
    monkeypatch.setattr(preference_module, "aget_or_create_collection", _collection)
    monkeypatch.setattr(preference_module, "get_async_qdrant_client", lambda: client)

    await UserPreferenceMemoryService().list_preferences(user_id="user-1")

    assert _filter_values(client.filter) == {
        "metadata.user_id": "user-1",
        "metadata.type": "user_preference",
        "metadata.active": True,
    }


@pytest.mark.asyncio
async def test_procedural_lookup_requires_user_filter(monkeypatch):
    client = _ScrollClient()
    monkeypatch.setattr(procedural_module, "aget_or_create_collection", _collection)
    monkeypatch.setattr(procedural_module, "get_async_qdrant_client", lambda: client)

    await ProceduralMemoryService().list_rules(user_id="user-1")

    assert _filter_values(client.filter) == {
        "metadata.user_id": "user-1",
        "metadata.type": "procedural_rule",
        "metadata.active": True,
    }
