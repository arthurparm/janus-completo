import asyncio
import logging
from app.core.memory.generative_memory import generative_memory_service

logger = logging.getLogger(__name__)

class MemoryMaintenanceWorker:
    def __init__(self, interval_seconds: int = 86400): # Once a day
        self.interval = interval_seconds
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("Memory Maintenance Worker started")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Memory Maintenance Worker stopped")

    async def _run_loop(self):
        while self.running:
            try:
                logger.info("Running memory maintenance...")
                await generative_memory_service.prune_memories()
                logger.info("Memory maintenance completed.")
            except Exception as e:
                logger.error(f"Error in memory maintenance: {e}")
            
            await asyncio.sleep(self.interval)

memory_maintenance_worker = MemoryMaintenanceWorker()
