from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.memory.memory_core import MemoryCore
from app.models.schemas import Experience


@pytest.mark.asyncio
async def test_memory_core_dependency_injection():
    # 1. Mock dependencies
    mock_client = AsyncMock()
    mock_cb = MagicMock()

    # Mock settings using a simple class so getattr works with defaults
    class MockSettings:
        QDRANT_HOST = "localhost"
        QDRANT_PORT = 6333
        MEMORY_VECTOR_SIZE = 1536
        MEMORY_SHORT_TTL_SECONDS = 600
        MEMORY_SHORT_MAX_ITEMS = 512
        # Missing attributes will trigger defaults in MemoryCore

    mock_settings = MockSettings()

    # 2. Instantiate MemoryCore with mocks (DI)
    memory = MemoryCore(
        client=mock_client,
        circuit_breaker=mock_cb,
        config=mock_settings
    )

    # 3. Verify it uses the injected client
    assert memory.client is mock_client
    assert memory._cb is mock_cb
    assert memory.settings is mock_settings

    # 4. Attempt an operation that would normally require network
    # We expect this to call our mock, not the real network
    exp = Experience(
        id="test-id",
        type="episodic",
        content="Test content",
        timestamp="2023-01-01T00:00:00Z"
    )

    # We expect embeddings to fail if not mocked, so let's see if we can bypass or if it fails gracefully
    # The code attempts aembed_text(redacted_content). If that fails, it logs warning and uses zero vector.
    # So this test should pass even without mocking embedding_manager.

    await memory.amemorize(exp)

    # 5. Verify Qdrant upsert was called on our MOCK
    # Note: upsert is called in current implementation.
    # We might need to handle circuit breaker logic too.

    # Check if client.upsert called
    assert mock_client.upsert.called or mock_client.upsert.await_args is not None
    print("✅ Dependency Injection Test Passed: MemoryCore used mock client!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_memory_core_dependency_injection())
