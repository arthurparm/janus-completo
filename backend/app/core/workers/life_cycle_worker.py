import asyncio
import time

import structlog

from app.core.autonomy.goal_manager import GoalManager
from app.core.workers.async_consolidation_worker import publish_consolidation_task
from app.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


class LifeCycleWorker:
    """
    O 'Coração' do Janus (Life Loop).
    Executa periodicamente para garantir que o sistema tenha 'iniciativa'.

    Responsabilidades:
    1. Verificar metas pendentes (GoalManager).
    2. Disparar consolidação de memória se inativo.
    3. Auto-análise de falhas recentes.
    """

    def __init__(
        self, goal_manager: GoalManager, memory_service: MemoryService, interval_seconds: int = 30
    ):
        self._goal_manager = goal_manager
        self._memory_service = memory_service
        self._interval = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_consolidation_ts = 0.0
        self._consolidation_interval = 600  # 10 minutes

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("LifeCycleWorker started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("LifeCycleWorker stopped.")

    async def _loop(self):
        while self._running:
            try:
                await self._pulse()
            except Exception as e:
                logger.error("Error in LifeCycle pulse", exc_info=e)

            await asyncio.sleep(self._interval)

    async def _pulse(self):
        """Um único 'batimento' do ciclo de vida."""
        logger.debug("LifeCycle pulse...")

        # 1. Verificar Metas Pendentes (Placeholder)
        try:
            next_goal = self._goal_manager.get_next_goal()
            if next_goal:
                logger.info("log_info", message=f"Metas pendentes detectadas: {next_goal.title}.")
        except Exception:
            pass

        # 2. Consolidação de Memória Periódica (Batch)
        # Dispara a cada 10 minutos (600s)
        now = time.time()
        if (now - self._last_consolidation_ts) > self._consolidation_interval:
            logger.info("LifeCycle: Disparando consolidação periódica (Batch)...")
            try:
                # Payload correto para o worker
                payload = {"mode": "batch", "limit": 50, "min_score": 0.0}
                
                # FIX: publish_consolidation_task internamente chama get_broker()
                # e faz await broker.publish(). Não precisamos de um contexto manager aqui
                # se a função já lida com a conexão.
                
                # Se publish_consolidation_task estiver tentando usar 'async with get_broker()',
                # isso falharia pois get_broker retorna o objeto direto.
                # Verificamos que publish_consolidation_task usa 'broker = await get_broker()',
                # então a chamada direta é segura.
                
                await publish_consolidation_task(payload=payload)
                
                self._last_consolidation_ts = now
                logger.info("LifeCycle: Tarefa de consolidação enviada com sucesso.")
            except Exception as e:
                # Logar exceção completa para debug
                import traceback
                logger.error("log_error", message=f"LifeCycle: Falha ao enviar consolidação: {e}\n{traceback.format_exc()}")

        # 3. Auto-Check de Falhas (Resilience)
        try:
            failures = await self._memory_service.recall_recent_failures(
                limit=5, timeframe_seconds=600
            )
            if len(failures) >= 3:
                logger.warning("log_warning", message=f"ALERTA DE SISTEMA: {len(failures)} falhas recentes detectadas pelo LifeCycle."
                )
        except Exception:
            pass
