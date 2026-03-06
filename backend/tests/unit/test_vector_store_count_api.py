from types import SimpleNamespace

import pytest

from app.db import vector_store


@pytest.mark.asyncio
async def test_async_count_points_uses_canonical_count_api():
    captured: dict[str, object] = {}

    class FakeClient:
        async def count(self, *, collection_name, count_filter, exact):
            captured["collection_name"] = collection_name
            captured["count_filter"] = count_filter
            captured["exact"] = exact
            return SimpleNamespace(count=7)

    qfilter = object()
    result = await vector_store.async_count_points(FakeClient(), "user_1", qfilter, exact=False)

    assert result == 7
    assert captured == {
        "collection_name": "user_1",
        "count_filter": qfilter,
        "exact": False,
    }


@pytest.mark.asyncio
async def test_async_count_points_defaults_missing_count_to_zero():
    class FakeClient:
        async def count(self, **kwargs):
            return SimpleNamespace()

    result = await vector_store.async_count_points(FakeClient(), "user_1", object(), exact=True)
    assert result == 0


def test_user_collection_helpers_build_scoped_names():
    assert vector_store.build_user_chat_collection_name("9") == "user_chat_9"
    assert vector_store.build_user_docs_collection_name("9") == "user_docs_9"
    assert vector_store.build_user_memory_collection_name("9") == "user_memory_9"


def test_deterministic_point_id_is_stable():
    first = vector_store.build_deterministic_point_id("chat-msg", "1", "s1", "user", 123, "hello")
    second = vector_store.build_deterministic_point_id("chat-msg", "1", "s1", "user", 123, "hello")
    third = vector_store.build_deterministic_point_id("chat-msg", "1", "s1", "assistant", 123, "hello")

    assert first == second
    assert first != third
