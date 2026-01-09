"""
SchedulerService - Cron-like Task Scheduling for Janus
=======================================================

Provides a flexible scheduling system for automated recurring tasks.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from prometheus_client import Counter, Gauge

logger = structlog.get_logger(__name__)

# Prometheus metrics
SCHEDULER_JOBS_TOTAL = Counter(
    "scheduler_jobs_total", "Total de jobs executados pelo scheduler", ["job_name", "status"]
)

SCHEDULER_ACTIVE_JOBS = Gauge("scheduler_active_jobs", "Número de jobs ativos no scheduler")

SCHEDULER_LAST_RUN = Gauge(
    "scheduler_last_run_timestamp", "Timestamp da última execução de cada job", ["job_name"]
)


class ScheduleType(Enum):
    """Tipos de agendamento suportados."""

    INTERVAL = "interval"  # Executa a cada N segundos
    DAILY = "daily"  # Executa uma vez por dia
    HOURLY = "hourly"  # Executa uma vez por hora
    WEEKLY = "weekly"  # Executa uma vez por semana
    CRON = "cron"  # Expressão cron (futuro)


@dataclass
class ScheduledJob:
    """Representa um job agendado."""

    name: str
    callback: Callable[[], Awaitable[Any]]
    schedule_type: ScheduleType
    interval_seconds: int = 60
    hour: int = 0  # Para DAILY/WEEKLY
    minute: int = 0  # Para DAILY/WEEKLY/HOURLY
    weekday: int = 0  # Para WEEKLY (0=Monday)
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def calculate_next_run(self) -> datetime:
        """Calcula o próximo horário de execução."""
        now = datetime.now()

        if self.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(seconds=self.interval_seconds)

        elif self.schedule_type == ScheduleType.HOURLY:
            next_run = now.replace(minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run

        elif self.schedule_type == ScheduleType.DAILY:
            next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif self.schedule_type == ScheduleType.WEEKLY:
            days_ahead = self.weekday - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            return next_run

        # Default: interval
        return now + timedelta(seconds=self.interval_seconds)


class SchedulerService:
    """
    Serviço de agendamento de tarefas (Cron Jobs).

    Permite registrar e executar tarefas automatizadas em intervalos
    definidos ou horários específicos.
    """

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._background_tasks: list[asyncio.Task] = []
        self._check_interval = 10  # Verifica jobs a cada 10 segundos
        logger.info("SchedulerService inicializado")

    def register_job(
        self,
        name: str,
        callback: Callable[[], Awaitable[Any]],
        schedule_type: ScheduleType = ScheduleType.INTERVAL,
        interval_seconds: int = 60,
        hour: int = 0,
        minute: int = 0,
        weekday: int = 0,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        """
        Registra um novo job no scheduler.

        Args:
            name: Nome único do job
            callback: Função async a ser executada
            schedule_type: Tipo de agendamento
            interval_seconds: Intervalo em segundos (para INTERVAL)
            hour: Hora do dia (para DAILY/WEEKLY)
            minute: Minuto (para HOURLY/DAILY/WEEKLY)
            weekday: Dia da semana 0-6 (para WEEKLY)
            enabled: Se o job está ativo
            metadata: Metadados adicionais

        Returns:
            ScheduledJob registrado
        """
        job = ScheduledJob(
            name=name,
            callback=callback,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            hour=hour,
            minute=minute,
            weekday=weekday,
            enabled=enabled,
            metadata=metadata or {},
        )
        job.next_run = job.calculate_next_run()

        self._jobs[name] = job
        SCHEDULER_ACTIVE_JOBS.set(len([j for j in self._jobs.values() if j.enabled]))

        logger.info(
            f"Job '{name}' registrado",
            schedule_type=schedule_type.value,
            next_run=job.next_run.isoformat(),
        )

        return job

    def unregister_job(self, name: str) -> bool:
        """Remove um job do scheduler."""
        if name in self._jobs:
            del self._jobs[name]
            SCHEDULER_ACTIVE_JOBS.set(len([j for j in self._jobs.values() if j.enabled]))
            logger.info(f"Job '{name}' removido")
            return True
        return False

    def enable_job(self, name: str) -> bool:
        """Ativa um job."""
        if name in self._jobs:
            self._jobs[name].enabled = True
            self._jobs[name].next_run = self._jobs[name].calculate_next_run()
            SCHEDULER_ACTIVE_JOBS.set(len([j for j in self._jobs.values() if j.enabled]))
            return True
        return False

    def disable_job(self, name: str) -> bool:
        """Desativa um job."""
        if name in self._jobs:
            self._jobs[name].enabled = False
            SCHEDULER_ACTIVE_JOBS.set(len([j for j in self._jobs.values() if j.enabled]))
            return True
        return False

    def get_job(self, name: str) -> ScheduledJob | None:
        """Retorna um job pelo nome."""
        return self._jobs.get(name)

    def list_jobs(self) -> list[dict[str, Any]]:
        """Lista todos os jobs registrados."""
        return [
            {
                "name": job.name,
                "schedule_type": job.schedule_type.value,
                "enabled": job.enabled,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "run_count": job.run_count,
                "error_count": job.error_count,
                "last_error": job.last_error,
            }
            for job in self._jobs.values()
        ]

    async def start(self):
        """Inicia o scheduler."""
        if self._running:
            logger.warning("Scheduler já está em execução")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("SchedulerService iniciado")

    async def stop(self):
        """Para o scheduler."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        for task in list(self._background_tasks):
            task.cancel()
        self._background_tasks = [t for t in self._background_tasks if not t.done()]

        logger.info("SchedulerService parado")

    async def _scheduler_loop(self):
        """Loop principal do scheduler."""
        logger.info("Scheduler loop iniciado")

        while self._running:
            try:
                now = datetime.now()

                for job in self._jobs.values():
                    if not job.enabled:
                        continue

                    if job.next_run and job.next_run <= now:
                        # Executa o job em background
                        self._background_tasks.append(asyncio.create_task(self._execute_job(job)))

                        # Calcula próxima execução
                        job.next_run = job.calculate_next_run()

                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no scheduler loop: {e}")
                await asyncio.sleep(self._check_interval)

    async def _execute_job(self, job: ScheduledJob):
        """Executa um job específico."""
        try:
            logger.info(f"Executando job '{job.name}'")

            await job.callback()

            job.last_run = datetime.now()
            job.run_count += 1
            job.last_error = None

            SCHEDULER_JOBS_TOTAL.labels(job_name=job.name, status="success").inc()
            SCHEDULER_LAST_RUN.labels(job_name=job.name).set(job.last_run.timestamp())

            logger.info(f"Job '{job.name}' executado com sucesso", run_count=job.run_count)

        except Exception as e:
            job.error_count += 1
            job.last_error = str(e)

            SCHEDULER_JOBS_TOTAL.labels(job_name=job.name, status="error").inc()

            logger.error(f"Erro ao executar job '{job.name}': {e}")

    def get_status(self) -> dict[str, Any]:
        """Retorna o status do scheduler."""
        return {
            "running": self._running,
            "total_jobs": len(self._jobs),
            "active_jobs": len([j for j in self._jobs.values() if j.enabled]),
            "jobs": self.list_jobs(),
        }


# Singleton instance
_scheduler_instance: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    """Retorna a instância singleton do scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance


async def initialize_default_jobs(scheduler: SchedulerService):
    """
    Registra os jobs padrão do sistema.

    Chamado durante o startup do Kernel.
    """
    from app.core.agents.meta_agent import MetaAgent
    from app.core.memory.memory_core import get_memory_db

    # Job: MetaAgent Analysis (a cada 5 minutos)
    async def meta_agent_analysis():
        try:
            agent = MetaAgent()
            await agent.run_analysis_cycle()
        except Exception as e:
            logger.error(f"MetaAgent analysis failed: {e}")

    scheduler.register_job(
        name="meta_agent_analysis",
        callback=meta_agent_analysis,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=300,  # 5 minutos
        metadata={"description": "Análise proativa do sistema pelo MetaAgent"},
    )

    # Job: Memory Health Check (a cada 10 minutos)
    async def memory_health_check():
        try:
            memory = await get_memory_db()
            if memory:
                await memory.health_check()
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")

    scheduler.register_job(
        name="memory_health_check",
        callback=memory_health_check,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=600,  # 10 minutos
        metadata={"description": "Verificação de saúde do banco de memória vetorial"},
    )

    # Job: Daily Cleanup (diário às 3h)
    async def daily_cleanup():
        logger.info("Executando limpeza diária...")
        # Implementar limpeza de logs, cache, etc.

    scheduler.register_job(
        name="daily_cleanup",
        callback=daily_cleanup,
        schedule_type=ScheduleType.DAILY,
        hour=3,
        minute=0,
        metadata={"description": "Limpeza diária de logs e cache"},
    )

    # Job: Update Gemini Quotas (a cada 1 hora)
    async def update_gemini_quotas():
        try:
            from app.core.llm.gemini_quota import GeminiQuotaFetcher

            logger.info("Updating Gemini quotas...")
            fetcher = GeminiQuotaFetcher()
            fetcher.fetch_and_update_limits()
            logger.info("Gemini quotas updated successfully.")
        except Exception as e:
            logger.error(f"Failed to update Gemini quotas: {e}")

    scheduler.register_job(
        name="update_gemini_quotas",
        callback=update_gemini_quotas,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,  # 1 hora
        metadata={"description": "Atualização de cotas da API Gemini via Google Cloud Monitoring"},
    )

    logger.info(f"Jobs padrão registrados: {len(scheduler.list_jobs())}")
