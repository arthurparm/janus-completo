"""
Prometheus metrics for memory operations.

These metrics are defined at the module level to prevent duplicate registration
when multiple MemoryCore instances are created.
"""

# Fallback to no-op if prometheus_client is not available
try:
    from prometheus_client import Counter, Gauge
except Exception:
    class _Noop:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
    Counter = Gauge = _Noop  # type: ignore


# Short-term cache metrics
memory_short_cache_hits_total = Counter(
    "memory_short_cache_hits_total", "Cache curto prazo: hits"
)
memory_short_cache_misses_total = Counter(
    "memory_short_cache_misses_total", "Cache curto prazo: misses"
)
memory_short_cache_size = Gauge(
    "memory_short_cache_size", "Itens no cache curto prazo"
)

# Quota metrics
memory_quota_rejections_total = Counter(
    "memory_quota_rejections_total", "Rejeições por cota excedida"
)

# General memory operation metrics
memory_operations_total = Counter(
    "memory_operations_total", "Total de operações na memória", ["operation"]
)
