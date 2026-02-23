import asyncio
import types
from types import SimpleNamespace

import pytest

from app.core.workers.knowledge_consolidator_worker import KnowledgeConsolidator


@pytest.mark.asyncio
async def test_start_is_idempotent_and_stop_cleans_state():
    kc = KnowledgeConsolidator()
    kc._initialized = True

    async def fake_initialize():
        return None

    async def fake_cycle(self, *, limit: int, min_score: float):
        del limit, min_score
        while True:
            await asyncio.sleep(1)

    kc._initialize = fake_initialize  # type: ignore[method-assign]
    kc._consolidation_cycle = types.MethodType(fake_cycle, kc)  # type: ignore[method-assign]

    await kc.start(limit=10, min_score=0.0)
    first_task = kc._task
    await kc.start(limit=10, min_score=0.0)

    assert kc._task is first_task
    assert kc.is_running is True
    assert first_task is not None

    await kc.stop()
    assert kc.is_running is False
    assert kc._task is None
    assert first_task.cancelled()


@pytest.mark.asyncio
async def test_stop_without_running_is_noop():
    kc = KnowledgeConsolidator()
    await kc.stop()
    assert kc.is_running is False
    assert kc._task is None


@pytest.mark.asyncio
async def test_consolidate_batch_uses_lock_to_prevent_parallel_runs():
    kc = KnowledgeConsolidator()

    class FakeQdrantClient:
        async def scroll(self, **kwargs):
            del kwargs
            return (
                [SimpleNamespace(id="1", payload={"content": "x", "metadata": {}})],
                None,
            )

    async def fake_initialize():
        kc.qdrant_client = FakeQdrantClient()
        kc._initialized = True

    active = 0
    max_active = 0

    async def fake_consolidate_experience(self, experience_id: str, experience_content: str, metadata):
        del experience_id, experience_content, metadata
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        try:
            await asyncio.sleep(0.05)
            return {"entities_created": 1, "relationships_created": 1}
        finally:
            active -= 1

    kc._initialize = fake_initialize  # type: ignore[method-assign]
    kc.consolidate_experience = types.MethodType(  # type: ignore[method-assign]
        fake_consolidate_experience, kc
    )

    await asyncio.gather(
        kc.consolidate_batch(limit=1, min_score=0.0),
        kc.consolidate_batch(limit=1, min_score=0.0),
    )

    assert max_active == 1
