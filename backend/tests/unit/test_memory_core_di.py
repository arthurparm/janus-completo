from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.memory.memory_core as memory_core_module
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
    assert memory.provider.client is mock_client
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


@pytest.mark.asyncio
async def test_memory_core_applies_strong_metadata_contract(monkeypatch):
    mock_client = AsyncMock()
    mock_cb = MagicMock()

    class MockSettings:
        QDRANT_HOST = "localhost"
        QDRANT_PORT = 6333
        MEMORY_VECTOR_SIZE = 1536
        MEMORY_SHORT_TTL_SECONDS = 600
        MEMORY_SHORT_MAX_ITEMS = 512

    monkeypatch.setattr(memory_core_module, "aembed_text", AsyncMock(return_value=[0.1] * 1536))
    memory = MemoryCore(client=mock_client, circuit_breaker=mock_cb, config=MockSettings())

    exp = Experience(
        id="self-study-id",
        type="episodic",
        content="Arquivo backend/app/services/x.py",
        metadata={
            "origin": "self_study",
            "source_kind": "code_file",
            "strong_memory": True,
            "file_path": "backend/app/services/x.py",
        },
    )

    await memory.amemorize(exp)

    upsert_points = mock_client.upsert.await_args.kwargs["points"]
    payload = upsert_points[0].payload
    metadata = payload["metadata"]
    assert metadata["origin"] == "self_study"
    assert metadata["source_kind"] == "code_file"
    assert metadata["content_kind"] == "episodic"
    assert metadata["strong_memory"] is True
    assert metadata["consolidation_status"] == "pending"
    assert metadata["neo4j_sync_status"] == "pending"
    assert metadata["file_path"] == "backend/app/services/x.py"
    assert metadata["memory_key"] is None
    assert metadata["local_only"] is False
    assert metadata["consolidation_hash"]


@pytest.mark.asyncio
async def test_memory_core_can_patch_metadata_after_write(monkeypatch):
    mock_client = AsyncMock()
    mock_cb = MagicMock()

    class MockSettings:
        QDRANT_HOST = "localhost"
        QDRANT_PORT = 6333
        MEMORY_VECTOR_SIZE = 1536
        MEMORY_SHORT_TTL_SECONDS = 600
        MEMORY_SHORT_MAX_ITEMS = 512

    monkeypatch.setattr(memory_core_module, "aembed_text", AsyncMock(return_value=[0.1] * 1536))
    memory = MemoryCore(client=mock_client, circuit_breaker=mock_cb, config=MockSettings())

    exp = Experience(
        id="self-study-id",
        type="episodic",
        content="Arquivo backend/app/services/x.py",
        metadata={"origin": "self_study"},
    )

    await memory.amemorize(exp)
    mock_client.retrieve.return_value = [
        MagicMock(payload={"metadata": {"origin": "self_study", "file_path": "backend/app/services/x.py"}})
    ]
    await memory.aupdate_metadata(
        "self-study-id",
        {"memory_key": "mk-1", "neo4j_sync_status": "linked"},
    )

    assert len(mock_client.retrieve.await_args.kwargs["ids"]) == 1
    assert mock_client.set_payload.await_args.kwargs["payload"]["metadata"]["origin"] == "self_study"
    assert (
        mock_client.set_payload.await_args.kwargs["payload"]["metadata"]["file_path"]
        == "backend/app/services/x.py"
    )
    assert mock_client.set_payload.await_args.kwargs["payload"]["metadata"]["memory_key"] == "mk-1"
    assert (
        mock_client.set_payload.await_args.kwargs["payload"]["metadata"]["neo4j_sync_status"]
        == "linked"
    )


def test_memory_core_uses_relaxed_quota_for_self_study():
    class MockSettings:
        QDRANT_HOST = "localhost"
        QDRANT_PORT = 6333
        MEMORY_VECTOR_SIZE = 1536
        MEMORY_SHORT_TTL_SECONDS = 600
        MEMORY_SHORT_MAX_ITEMS = 512
        MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 200
        MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 5_000_000
        MEMORY_QUOTA_MAX_ITEMS_SELF_STUDY = 5000
        MEMORY_QUOTA_MAX_BYTES_SELF_STUDY = 25_000_000

    memory = MemoryCore(client=MagicMock(), circuit_breaker=MagicMock(), config=MockSettings())

    assert memory._get_quota_limits("chat") == (200, 5_000_000)
    assert memory._get_quota_limits("self_study") == (5000, 25_000_000)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_memory_core_dependency_injection())
