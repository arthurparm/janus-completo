"""
Auto-Healer (Sprint 12)

Tarefa de fundo que observa o HealthMonitor e executa ações de auto-healing
para componentes não cobertos por circuit breakers existentes.

Ações implementadas:
- Reconexão do Message Broker quando unhealthy
- Reconciliação da política/argumentos das filas conhecidas
- Limpeza de quarentena de poison pills (expiradas)
- Decaimento de penalizações de modelos LLM
- Reset oportunista de circuit breakers de provedores LLM abertos por muito tempo
- Disparo de ciclo do Meta-Agente quando saúde geral degradada
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from prometheus_client import Counter

from app.core.infrastructure.message_broker import get_broker
from app.core.monitoring.health_monitor import HealthStatus, get_health_monitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler
from app.models.schemas import QueueName

logger = structlog.get_logger(__name__)

AUTO_HEALER_STEP_FAILURES = Counter(
    "auto_healer_step_failures_total",
    "Total de falhas por etapa do Auto-Healer",
    ["step"],
)
AUTO_HEALER_STEP_ATTEMPTS = Counter(
    "auto_healer_step_attempts_total",
    "Total de tentativas por etapa do Auto-Healer",
    ["step"],
)
AUTO_HEALER_STEP_SUCCESSES = Counter(
    "auto_healer_step_successes_total",
    "Total de sucessos por etapa do Auto-Healer",
    ["step"],
)

# Flags/estado interno
_healer_task: asyncio.Task | None = None
_last_actions: dict[str, float] = {}

# Configuração via settings (com defaults seguros)
try:
    from app.config import settings

    _HEAL_INTERVAL = int(getattr(settings, "AUTO_HEALER_INTERVAL_SECONDS", 30) or 30)
    _LLM_CB_FORCE_RESET_SECONDS = float(
        getattr(settings, "LLM_CB_FORCE_RESET_SECONDS", 300) or 300.0
    )
    _LLM_PENALTY_DECAY = float(getattr(settings, "LLM_PENALTY_DECAY", 0.10) or 0.10)
    _META_AGENT_ON_DEGRADE = bool(getattr(settings, "AUTO_HEALER_META_AGENT_ON_DEGRADE", True))
except Exception:
    _HEAL_INTERVAL = 30
    _LLM_CB_FORCE_RESET_SECONDS = 300.0
    _LLM_PENALTY_DECAY = 0.10
    _META_AGENT_ON_DEGRADE = True


def _record_healing_failure(step_name: str, error: Exception, message: str | None = None) -> None:
    AUTO_HEALER_STEP_FAILURES.labels(step=step_name).inc()
    logger.error(
        "auto_healer_step_failed",
        step=step_name,
        error=str(error),
        message=message,
        exc_info=True,
    )


async def _heal_message_broker() -> None:
    """Tenta reconectar o broker quando unhealthy."""
    try:
        broker = await get_broker()
        ok = await broker.health_check()
        if not ok:
            await broker.connect()
            logger.info("Auto-Healer: reconexão do Message Broker executada.")
    except Exception as e:
        _record_healing_failure(
            "message_broker",
            e,
            f"Auto-Healer: falha ao reconectar broker: {e}",
        )


async def _reconcile_queue_policies() -> None:
    """Reconcilia políticas/argumentos das filas (TTL, max-length, etc.)."""
    try:
        broker = await get_broker()
        for q in [
            QueueName.KNOWLEDGE_CONSOLIDATION.value,
            QueueName.AGENT_TASKS.value,
            QueueName.NEURAL_TRAINING.value,
            QueueName.META_AGENT_CYCLE.value,
            QueueName.TASKS_CODEX_WORKER.value,
        ]:
            try:
                res = await broker.reconcile_queue_policy(q, force_delete=True)
                logger.info("log_info", message=f"Auto-Healer: reconciliada política da fila '{q}' (status={res.get('status', 'unknown')})."
                )
            except Exception as qe:
                _record_healing_failure(
                    "rabbitmq_consolidation_queue_policy",
                    qe,
                    f"Auto-Healer: erro ao reconciliar fila '{q}': {qe}",
                )
    except Exception as e:
        _record_healing_failure(
            "rabbitmq_consolidation_queue_policy",
            e,
            f"Auto-Healer: falha geral ao reconciliar filas: {e}",
        )


async def _heal_poison_pills() -> None:
    """Limpa mensagens expiradas na quarentena e libera quando aplicável."""
    try:
        handler = get_poison_pill_handler()
        removed = handler.cleanup_expired_quarantine()
        if removed > 0:
            logger.info("log_info", message=f"Auto-Healer: {removed} mensagens liberadas da quarentena (expiradas).")
    except Exception as e:
        _record_healing_failure(
            "poison_pill_handler",
            e,
            f"Auto-Healer: falha ao limpar quarentena de poison pills: {e}",
        )


async def _heal_llm_router() -> None:
    """Decai penalizações e reseta circuitos abertos por muito tempo."""
    try:
        # Import interno para evitar ciclos
        from app.core.llm.pricing import _model_penalty_factors
        from app.core.llm.resilience import force_reset_stale_open_circuit_breakers

        # Decaimento suave das penalizações (não abaixo de 1.0)
        try:
            for provider, models in _model_penalty_factors.items():
                for model, pf in list(models.items()):
                    if pf > 1.0:
                        new_pf = max(1.0, pf - _LLM_PENALTY_DECAY)
                        models[model] = new_pf
            logger.debug("Auto-Healer: penalizações de modelos LLM decaídas.")
        except Exception as e:
            _record_healing_failure(
                "llm_router",
                e,
                "Auto-Healer: erro ao decair penalizacoes de LLM.",
            )

        # Reset oportunista dos circuit breakers de provedores abertos por muito tempo
        for provider in force_reset_stale_open_circuit_breakers(_LLM_CB_FORCE_RESET_SECONDS):
            logger.warning("log_warning", message=f"Auto-Healer: CircuitBreaker de '{provider}' resetado (aberto há muito tempo)."
            )
    except Exception as e:
        _record_healing_failure(
            "llm_router",
            e,
            f"Auto-Healer: falha ao curar LLM Router: {e}",
        )


async def _maybe_trigger_meta_agent(system_status: dict[str, Any]) -> None:
    """Dispara um ciclo do Meta-Agente em caso de degradação do sistema."""
    try:
        if not _META_AGENT_ON_DEGRADE:
            return
        from app.core.workers.meta_agent_worker import publish_meta_agent_cycle

        status = system_status.get("status", "unknown")
        score = int(system_status.get("score", 0) or 0)
        if status in {"degraded", "unhealthy"}:
            # Rate-limit para evitar tempestade de ciclos
            last = _last_actions.get("meta_agent_cycle", 0.0)
            now = time.time()
            if now - last > max(60.0, _HEAL_INTERVAL * 2):
                _last_actions["meta_agent_cycle"] = now
                await publish_meta_agent_cycle(mode="auto_heal")
                logger.info("log_info", message=f"Auto-Healer: meta-agente acionado (status={status}, score={score}).")
    except Exception as e:
        _record_healing_failure(
            "meta_agent_cycle",
            e,
            f"Auto-Healer: falha ao acionar meta-agente: {e}",
        )


async def _heal_with_codex(system_status: dict[str, Any]) -> None:
    """
    Placeholder: Dispara tarefas de correção via Codex quando falhas recorrentes são detectadas.
    """
    # Implementação futura:
    # 1. Checar métricas de erro
    # 2. Se erro > threshold, montar contexto
    # 3. Publicar task 'codex_fix' na fila TASKS_CODEX_WORKER
    pass


async def _run_healing_step(step_name: str, action: Callable[[], Awaitable[None]]) -> None:
    """Executa uma etapa de cura sem deixar falhas invisiveis para operacao."""
    AUTO_HEALER_STEP_ATTEMPTS.labels(step=step_name).inc()
    try:
        await action()
    except Exception as e:
        _record_healing_failure(step_name, e)
    else:
        AUTO_HEALER_STEP_SUCCESSES.labels(step=step_name).inc()


async def start_auto_healer(interval_seconds: int | None = None) -> asyncio.Task:
    """
    Inicia a tarefa de auto-healing em background.

    Args:
        interval_seconds: Intervalo de execução (default configurado em settings)

    Returns:
        asyncio.Task com o loop de auto-healing
    """
    global _healer_task
    if _healer_task is not None and not _healer_task.done():
        return _healer_task

    if interval_seconds is None:
        interval_seconds = _HEAL_INTERVAL

    monitor = get_health_monitor()

    async def _loop() -> None:
        logger.info("log_info", message=f"Auto-Healer: iniciado (intervalo={interval_seconds}s).")
        while True:
            try:
                # Executa/atualiza health checks e obtém visão agregada
                await monitor.check_all_components()
                system = monitor.get_system_health()

                # Curar componentes específicos conforme estado
                # 1) Broker
                async def heal_broker_if_needed() -> None:
                    comp_broker = monitor.last_results.get("message_broker")
                    if comp_broker and comp_broker.status in {
                        HealthStatus.UNHEALTHY,
                        HealthStatus.DEGRADED,
                    }:
                        await _heal_message_broker()

                await _run_healing_step("message_broker", heal_broker_if_needed)

                # 2) Políticas de filas
                async def reconcile_queue_policies_if_needed() -> None:
                    comp_queue = monitor.last_results.get("rabbitmq_consolidation_queue_policy")
                    if comp_queue and comp_queue.status in {
                        HealthStatus.UNHEALTHY,
                        HealthStatus.DEGRADED,
                    }:
                        await _reconcile_queue_policies()

                await _run_healing_step(
                    "rabbitmq_consolidation_queue_policy",
                    reconcile_queue_policies_if_needed,
                )

                # 3) Poison Pills
                async def heal_poison_pills_if_needed() -> None:
                    comp_pp = monitor.last_results.get("poison_pill_handler")
                    if comp_pp and comp_pp.status in {
                        HealthStatus.UNHEALTHY,
                        HealthStatus.DEGRADED,
                    }:
                        await _heal_poison_pills()

                await _run_healing_step("poison_pill_handler", heal_poison_pills_if_needed)

                # 4) LLM Router (decay/reset)
                async def heal_llm_router_if_needed() -> None:
                    comp_llm = monitor.last_results.get("llm_router")
                    if comp_llm and comp_llm.status in {
                        HealthStatus.UNHEALTHY,
                        HealthStatus.DEGRADED,
                    }:
                        await _heal_llm_router()
                    else:
                        # Mesmo saudável, aplicamos um leve decaimento contínuo das penalizações
                        await _heal_llm_router()
                await _run_healing_step("llm_router", heal_llm_router_if_needed)

                # 5) Meta-Agente em degradação
                async def trigger_meta_agent_if_needed() -> None:
                    await _maybe_trigger_meta_agent(system)

                await _run_healing_step("meta_agent_cycle", trigger_meta_agent_if_needed)

                # 6) Codex Auto-Fix (Placeholder)
                async def heal_with_codex_if_needed() -> None:
                    await _heal_with_codex(system)

                await _run_healing_step("codex_auto_fix", heal_with_codex_if_needed)

                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error("log_error", message=f"Auto-Healer: erro no loop principal: {e}", exc_info=True)
                await asyncio.sleep(interval_seconds)

    _healer_task = asyncio.create_task(_loop())
    return _healer_task


class AutoHealerWorker:
    name = "auto_healer"

    def __init__(self, interval_seconds: int | None = None):
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._task = await start_auto_healer(self._interval_seconds)
        self._running = True
        logger.info("AutoHealerWorker started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("AutoHealerWorker stopped")

    def is_healthy(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def get_status(self) -> dict:
        return {"running": self._running}


async def start_auto_healer_worker():
    instance = AutoHealerWorker()
    await instance.start()
    return instance
