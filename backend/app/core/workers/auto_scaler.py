"""
Queue Auto-Scaler

Monitora backlog das filas e ajusta dinamicamente o número de consumidores
por fila (scale up/down), usando o MessageBroker start_consumer.
"""

import asyncio
import structlog
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import settings
from app.core.infrastructure.message_broker import get_broker
from app.core.workers.agent_tasks_worker import process_agent_task
from app.core.workers.async_consolidation_worker import process_consolidation_task
from app.core.workers.meta_agent_worker import process_meta_agent_cycle
from app.core.workers.neural_training_worker import process_neural_training_task
from app.models.schemas import QueueName

logger = structlog.get_logger(__name__)


class _QueueRule:
    def __init__(
        self,
        queue_name: str,
        callback: Callable[[Any], Awaitable[Any]],
        min_consumers: int = 1,
        max_consumers: int = 4,
        prefetch_per_consumer: int = 5,
        scale_up_backlog: int = 25,
        scale_down_backlog: int = 5,
        enabled: bool = True,
    ) -> None:
        self.queue_name = queue_name
        self.callback = callback
        self.min_consumers = max(1, int(min_consumers))
        self.max_consumers = max(self.min_consumers, int(max_consumers))
        self.prefetch_per_consumer = max(1, int(prefetch_per_consumer))
        self.scale_up_backlog = max(1, int(scale_up_backlog))
        self.scale_down_backlog = max(0, int(scale_down_backlog))
        self.enabled = enabled


# Regras por fila (com defaults, podem ser sobrescritas por settings.QUEUE_AUTOSCALER_CONFIG)
_DEF_RULES: dict[str, _QueueRule] = {
    QueueName.AGENT_TASKS.value: _QueueRule(
        queue_name=QueueName.AGENT_TASKS.value,
        callback=process_agent_task,
        min_consumers=int(getattr(settings, "AGENT_TASKS_MIN_CONSUMERS", 1) or 1),
        max_consumers=int(getattr(settings, "AGENT_TASKS_MAX_CONSUMERS", 6) or 6),
        prefetch_per_consumer=int(getattr(settings, "AGENT_TASKS_PREFETCH", 10) or 10),
        scale_up_backlog=int(getattr(settings, "AGENT_TASKS_SCALE_UP_BACKLOG", 50) or 50),
        scale_down_backlog=int(getattr(settings, "AGENT_TASKS_SCALE_DOWN_BACKLOG", 10) or 10),
    ),
    QueueName.NEURAL_TRAINING.value: _QueueRule(
        queue_name=QueueName.NEURAL_TRAINING.value,
        callback=process_neural_training_task,
        min_consumers=int(getattr(settings, "NEURAL_TRAIN_MIN_CONSUMERS", 1) or 1),
        max_consumers=int(getattr(settings, "NEURAL_TRAIN_MAX_CONSUMERS", 3) or 3),
        prefetch_per_consumer=int(getattr(settings, "NEURAL_TRAIN_PREFETCH", 2) or 2),
        scale_up_backlog=int(getattr(settings, "NEURAL_TRAIN_SCALE_UP_BACKLOG", 10) or 10),
        scale_down_backlog=int(getattr(settings, "NEURAL_TRAIN_SCALE_DOWN_BACKLOG", 3) or 3),
    ),
    QueueName.KNOWLEDGE_CONSOLIDATION.value: _QueueRule(
        queue_name=QueueName.KNOWLEDGE_CONSOLIDATION.value,
        callback=process_consolidation_task,
        min_consumers=int(getattr(settings, "CONSOLIDATION_MIN_CONSUMERS", 1) or 1),
        max_consumers=int(getattr(settings, "CONSOLIDATION_MAX_CONSUMERS", 4) or 4),
        prefetch_per_consumer=int(getattr(settings, "CONSOLIDATION_PREFETCH", 5) or 5),
        scale_up_backlog=int(getattr(settings, "CONSOLIDATION_SCALE_UP_BACKLOG", 25) or 25),
        scale_down_backlog=int(getattr(settings, "CONSOLIDATION_SCALE_DOWN_BACKLOG", 5) or 5),
    ),
    QueueName.META_AGENT_CYCLE.value: _QueueRule(
        queue_name=QueueName.META_AGENT_CYCLE.value,
        callback=process_meta_agent_cycle,
        min_consumers=int(getattr(settings, "META_AGENT_MIN_CONSUMERS", 1) or 1),
        max_consumers=int(getattr(settings, "META_AGENT_MAX_CONSUMERS", 2) or 2),
        prefetch_per_consumer=int(getattr(settings, "META_AGENT_PREFETCH", 2) or 2),
        scale_up_backlog=int(getattr(settings, "META_AGENT_SCALE_UP_BACKLOG", 5) or 5),
        scale_down_backlog=int(getattr(settings, "META_AGENT_SCALE_DOWN_BACKLOG", 2) or 2),
    ),
}


_active_consumers: dict[str, list[asyncio.Task]] = {}


def _apply_settings_overrides() -> None:
    cfg = getattr(settings, "QUEUE_AUTOSCALER_CONFIG", {}) or {}
    try:
        for qname, overrides in cfg.items():
            rule = _DEF_RULES.get(qname)
            if not rule:
                continue
            # Operadores seguros para overrides parciais
            rule.min_consumers = int(
                overrides.get("min_consumers", rule.min_consumers) or rule.min_consumers
            )
            rule.max_consumers = int(
                overrides.get("max_consumers", rule.max_consumers) or rule.max_consumers
            )
            rule.prefetch_per_consumer = int(
                overrides.get("prefetch", rule.prefetch_per_consumer) or rule.prefetch_per_consumer
            )
            rule.scale_up_backlog = int(
                overrides.get("scale_up_backlog", rule.scale_up_backlog) or rule.scale_up_backlog
            )
            rule.scale_down_backlog = int(
                overrides.get("scale_down_backlog", rule.scale_down_backlog)
                or rule.scale_down_backlog
            )
            rule.enabled = bool(overrides.get("enabled", rule.enabled))
    except Exception:
        # Ignora erros de configuração dinâmica
        pass


async def _ensure_consumers(queue_name: str, target_ours: int, rule: _QueueRule) -> None:
    broker = await get_broker()
    lst = _active_consumers.setdefault(queue_name, [])

    # Limpa tasks concluídas
    lst = [t for t in lst if not t.done()]
    _active_consumers[queue_name] = lst

    if len(lst) < target_ours:
        to_start = target_ours - len(lst)
        for _ in range(to_start):
            t = broker.start_consumer(
                queue_name=queue_name,
                callback=rule.callback,
                prefetch_count=rule.prefetch_per_consumer,
            )
            lst.append(t)
        logger.info("log_info", message=f"Auto-Scaler: adicionados {to_start} consumidores em '{queue_name}' (prefetch={rule.prefetch_per_consumer})."
        )
    elif len(lst) > target_ours:
        to_stop = len(lst) - target_ours
        for _ in range(to_stop):
            t = lst.pop()
            t.cancel()
        logger.info("log_info", message=f"Auto-Scaler: removidos {to_stop} consumidores próprios em '{queue_name}'.")


async def _scale_once() -> None:
    broker = await get_broker()
    _apply_settings_overrides()

    for qname, rule in _DEF_RULES.items():
        if not rule.enabled:
            continue
        try:
            info = await broker.get_queue_info(qname)
            if not info:
                continue
            messages = int(info.get("messages", 0) or 0)
            total_consumers = int(info.get("consumers", 0) or 0)
            ours = len(_active_consumers.get(qname, []))
            others = max(0, total_consumers - ours)

            # Calcula desejado por heurística simples (backlog por consumidor)
            current = max(1, total_consumers) if total_consumers > 0 else rule.min_consumers
            backlog_per_cons = messages / max(1, current)
            desired_total = current
            if messages == 0 and current > rule.min_consumers:
                desired_total = rule.min_consumers
            elif backlog_per_cons > rule.scale_up_backlog and current < rule.max_consumers:
                desired_total = min(rule.max_consumers, current + 1)
            elif backlog_per_cons < rule.scale_down_backlog and current > rule.min_consumers:
                desired_total = max(rule.min_consumers, current - 1)

            target_ours = max(0, desired_total - others)
            await _ensure_consumers(qname, target_ours, rule)
        except Exception as e:
            logger.error("log_error", message=f"Auto-Scaler: erro ao escalar fila '{qname}': {e}", exc_info=True)


async def start_auto_scaler(poll_interval_seconds: int | None = None) -> asyncio.Task:
    """Inicia o auto-escalador em background."""
    interval = int(
        poll_interval_seconds or getattr(settings, "QUEUE_AUTOSCALER_POLL_INTERVAL", 10) or 10
    )

    async def _loop():
        logger.info("log_info", message=f"Iniciando Auto-Scaler de filas (intervalo={interval}s)...")
        try:
            while True:
                await _scale_once()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Auto-Scaler cancelado.")
            # Cancela consumidores próprios
            for qname, tasks in _active_consumers.items():
                for t in tasks:
                    t.cancel()
            _active_consumers.clear()

    return asyncio.create_task(_loop())
