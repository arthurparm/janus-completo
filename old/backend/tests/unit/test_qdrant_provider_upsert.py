from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.infrastructure import resilience
from app.core.infrastructure.resilience import CircuitBreaker
from app.core.memory.providers.qdrant_provider import QdrantProvider


@pytest.mark.asyncio
async def test_upsert_retries_transient_failure_with_shared_circuit_breaker(monkeypatch):
    client = AsyncMock()
    client.upsert.side_effect = [RuntimeError("temporary"), None]
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
    provider = QdrantProvider(client=client, circuit_breaker=circuit_breaker)
    monkeypatch.setattr(resilience.asyncio, "sleep", AsyncMock())

    await provider.upsert(uuid4(), [0.1], {"kind": "lesson"})

    assert client.upsert.await_count == 2
    assert provider.is_offline is False
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_upsert_marks_provider_offline_after_retry_budget_is_exhausted(monkeypatch):
    client = AsyncMock()
    client.upsert.side_effect = RuntimeError("unavailable")
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
    provider = QdrantProvider(client=client, circuit_breaker=circuit_breaker)
    monkeypatch.setattr(resilience.asyncio, "sleep", AsyncMock())

    await provider.upsert(uuid4(), [0.1], {"kind": "lesson"})

    assert client.upsert.await_count == 3
    assert provider.is_offline is True
    assert circuit_breaker.failure_count == 3
