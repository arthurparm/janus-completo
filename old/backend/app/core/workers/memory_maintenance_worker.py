import asyncio

import structlog

from app.core.memory.generative_memory import generative_memory_service

logger = structlog.get_logger(__name__)

class MemoryMaintenanceWorker:
    name: str = "memory_maintenance"

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

    def is_healthy(self) -> bool:
        return self.running and self.task is not None and not self.task.done()

    def get_status(self) -> dict:
        return {"running": self.running, "interval_seconds": self.interval}

    async def _run_loop(self):
        while self.running:
            try:
                logger.info("Running memory maintenance...")
                await generative_memory_service.prune_memories()
                logger.info("Memory maintenance completed.")
            except Exception as e:
                logger.error("log_error", message=f"Error in memory maintenance: {e}")

            await asyncio.sleep(self.interval)

memory_maintenance_worker = MemoryMaintenanceWorker()


async def start_memory_maintenance_worker():
    await memory_maintenance_worker.start()
    return memory_maintenance_worker
