"""
Knowledge Consolidator Scheduler (Legacy Wrapper)

This module keeps the content of `knowledge_consolidator.py` for backward compatibility
with `bootstrap.py` and `kernel.py`, but delegates all actual logic to the new
`app.core.workers.knowledge_consolidator_worker.py` (Sprint 13).

It acts as a SCHEDULER that periodically triggers the batch consolidation.
"""

import asyncio
import logging
from typing import Any

from app.config import settings
from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator as worker_impl

logger = logging.getLogger(__name__)


class KnowledgeConsolidator:
    """
    [DEPRECATED LOGIC]
    Wrapper scheduler that triggers `knowledge_consolidator_worker.consolidate_batch`.
    Maintains the interface expected by Kernel/Bootstrap.
    """

    def __init__(
        self,
        agent_service: Any = None,
        memory_service: Any = None,
        knowledge_repo: Any = None,
        llm_service: Any = None,
    ):
        # We accept dependencies to satisfy the interface, but we don't use them.
        # The worker implementation (worker_impl) manages its own dependencies via DI/Functions.
        self.is_running = False
        self._task = None

    async def start(self):
        """Starts the periodic consolidation loop."""
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._consolidation_cycle())
            logger.info("Knowledge Consolidator Scheduler started (delegating to Worker).")

    async def stop(self):
        """Stops the scheduler."""
        if self.is_running and self._task:
            self.is_running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Knowledge Consolidator Scheduler stopped.")

    async def _consolidation_cycle(self):
        """Background loop that triggers batch consolidation."""
        while self.is_running:
            try:
                # Delegate to the new worker implementation
                await worker_impl.consolidate_batch(limit=10, min_score=0.0)
            except Exception as e:
                logger.error("Error during consolidation cycle (Scheduler):", exc_info=e)

            # Wait for next cycle
            interval = getattr(settings, "KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS", 60)
            await asyncio.sleep(interval)
