"""
Unit tests for Prometheus metrics singleton pattern in memory module.
"""


def test_no_duplicate_metric_registration(monkeypatch):
    """
    Verify that creating multiple MemoryCore instances does not cause
    duplicate Prometheus metric registration errors.
    """

    # Patch the Qdrant client to avoid real network calls
    class DummyQdrantClient:
        async def get_collection(self, *args, **kwargs):
            raise Exception("no collection")

        async def create_collection(self, *args, **kwargs):
            pass

    import app.core.memory.memory_core as memory_module

    monkeypatch.setattr(memory_module, "AsyncQdrantClient", lambda *a, **k: DummyQdrantClient())

    from app.core.memory.memory_core import MemoryCore

    # First instance
    mc1 = MemoryCore()
    # Second instance – this should NOT raise ValueError from prometheus_client
    mc2 = MemoryCore()

    # Both instances should share the same singleton metric objects
    assert mc1._short_hits is mc2._short_hits
    assert mc1._short_misses is mc2._short_misses
    assert mc1._short_size is mc2._short_size
    assert mc1._quota_rejections is mc2._quota_rejections
    assert mc1._ops_total is mc2._ops_total

    # Call inc() to make sure metrics work
    mc1._short_hits.inc()
    mc2._short_hits.inc()


def test_metrics_module_exports():
    """
    Verify that the metrics module exports the expected metric objects.
    """
    from app.core.memory.metrics import (
        memory_operations_total,
        memory_quota_rejections_total,
        memory_short_cache_hits_total,
        memory_short_cache_misses_total,
        memory_short_cache_size,
    )

    # All should be non-None
    assert memory_short_cache_hits_total is not None
    assert memory_short_cache_misses_total is not None
    assert memory_short_cache_size is not None
    assert memory_quota_rejections_total is not None
    assert memory_operations_total is not None
