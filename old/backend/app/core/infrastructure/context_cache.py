"""
Context Cache for Stateful Workers.

This module provides an in-memory cache for storing static context
from TaskState, enabling workers to send only deltas between hops.
"""
import hashlib
import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default TTL: 30 minutes (tasks older than this will have their context evicted)
DEFAULT_TTL_SECONDS = 1800


class ContextCache:
    """
    In-memory cache for static task context.
    
    Stores the static portions of TaskState (original_goal, meta, etc.)
    so workers can send only dynamic deltas (history updates, new outputs).
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._cache: dict[str, dict[str, Any]] = {}
        self._timestamps: dict[str, float] = {}
        self._ttl = ttl_seconds

    def store(self, task_id: str, static_context: dict[str, Any]) -> str:
        """
        Store static context for a task.
        
        Args:
            task_id: Unique task identifier.
            static_context: Static portions of TaskState to cache.
            
        Returns:
            Hash of the stored context for validation.
        """
        # Compute hash for integrity check
        context_hash = self._compute_hash(static_context)

        self._cache[task_id] = static_context
        self._timestamps[task_id] = time.time()

        logger.debug("Context cached", task_id=task_id, hash=context_hash[:8])
        return context_hash

    def retrieve(self, task_id: str) -> dict[str, Any] | None:
        """
        Retrieve cached static context for a task.
        
        Args:
            task_id: Unique task identifier.
            
        Returns:
            Cached static context, or None if not found/expired.
        """
        # Check if exists
        if task_id not in self._cache:
            logger.debug("Context cache miss", task_id=task_id)
            return None

        # Check TTL
        stored_time = self._timestamps.get(task_id, 0)
        if time.time() - stored_time > self._ttl:
            logger.debug("Context cache expired", task_id=task_id)
            self.invalidate(task_id)
            return None

        logger.debug("Context cache hit", task_id=task_id)
        return self._cache[task_id]

    def invalidate(self, task_id: str) -> None:
        """Remove cached context for a task."""
        self._cache.pop(task_id, None)
        self._timestamps.pop(task_id, None)
        logger.debug("Context invalidated", task_id=task_id)

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed items."""
        now = time.time()
        expired = [
            tid for tid, ts in self._timestamps.items()
            if now - ts > self._ttl
        ]
        for tid in expired:
            self.invalidate(tid)

        if expired:
            logger.info("Context cache cleanup", removed=len(expired))
        return len(expired)

    def _compute_hash(self, data: dict[str, Any]) -> str:
        """Compute a hash of the context for integrity validation."""
        import json
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "entries": len(self._cache),
            "ttl_seconds": self._ttl,
        }


# Singleton instance
_context_cache: ContextCache | None = None


def get_context_cache() -> ContextCache:
    """Get the singleton ContextCache instance."""
    global _context_cache
    if _context_cache is None:
        _context_cache = ContextCache()
    return _context_cache
