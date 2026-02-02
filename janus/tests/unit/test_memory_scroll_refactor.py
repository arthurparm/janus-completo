from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.memory.memory_core import MemoryCore


@pytest.mark.asyncio
async def test_search_recent_failures_uses_scroll():
    """
    Verify that search_recent_failures calls client.scroll instead of client.search.
    """
    mock_client = MagicMock()
    mock_client.scroll = AsyncMock(return_value=([], None))
    mock_client.search = AsyncMock(return_value=[])

    # Explicit async side effect for robust mocking
    async def call_async_side_effect(func, *args, **kwargs):
        return await func(*args, **kwargs)

    mock_cb = MagicMock()
    # Mocking the decorator usage if needed (though resilient uses call_async internally usually)
    mock_cb.side_effect = lambda f: f
    mock_cb.call_async = AsyncMock(side_effect=call_async_side_effect)

    # Simple Config
    class MockSettings:
        MEMORY_VECTOR_SIZE = 1536
        QDRANT_HOST = "mock"
        QDRANT_PORT = 6333

    memory = MemoryCore(client=mock_client, circuit_breaker=mock_cb, config=MockSettings())

    await memory.arecall_recent_failures(limit=5)

    # Assert scroll was called
    mock_client.scroll.assert_called_once()
    assert mock_client.scroll.call_args[1]["limit"] == 5
    assert mock_client.scroll.call_args[1]["with_payload"] is True

    # Assert search was NOT called (providing clear proof of refactor)
    mock_client.search.assert_not_called()


@pytest.mark.asyncio
async def test_search_recent_lessons_uses_scroll():
    """
    Verify that search_recent_lessons calls client.scroll instead of client.search.
    """
    mock_client = MagicMock()
    mock_client.scroll = AsyncMock(return_value=([], None))
    mock_client.search = AsyncMock(return_value=[])

    async def call_async_side_effect(func, *args, **kwargs):
        return await func(*args, **kwargs)

    mock_cb = MagicMock()
    mock_cb.side_effect = lambda f: f
    mock_cb.call_async = AsyncMock(side_effect=call_async_side_effect)

    class MockSettings:
        MEMORY_VECTOR_SIZE = 1536
        QDRANT_HOST = "mock"
        QDRANT_PORT = 6333

    memory = MemoryCore(client=mock_client, circuit_breaker=mock_cb, config=MockSettings())

    await memory.arecall_recent_lessons(limit=10)

    mock_client.scroll.assert_called_once()
    mock_client.search.assert_not_called()
