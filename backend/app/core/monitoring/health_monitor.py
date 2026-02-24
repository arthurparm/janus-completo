"""
Sistema de Health Checks Avançado para monitoramento proativo (Sprint 12).

Monitora a saúde de todos os componentes do Janus e fornece
diagnósticos detalhados para operação contínua.
"""

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from prometheus_client import Gauge, Histogram, Info

from app.config import settings

logger = logging.getLogger(__name__)

# --- Métricas ---
COMPONENT_HEALTH = Gauge(
    "component_health_status",
    "Status de saúde do componente (1=healthy, 0.5=degraded, 0=unhealthy)",
    ["component"],
)

SYSTEM_HEALTH_SCORE = Gauge("system_health_score", "Score geral de saúde do sistema (0-100)")

HEALTH_CHECK_DURATION = Gauge(
    "health_check_duration_seconds", "Duração do último health check", ["component"]
)

SYSTEM_INFO = Info("janus_system", "Informações do sistema Janus")

OBSERVED_LATENCY = Histogram(
    "component_observed_latency_seconds", "Latência observada por componente", ["component"]
)
RECOMMENDED_TIMEOUT = Gauge(
    "component_recommended_timeout_seconds", "Timeout recomendado por componente", ["component"]
)

_latency_windows: dict[str, deque] = {}
_LATENCY_WINDOW_SIZE = 256


def record_latency(component: str, seconds: float) -> None:
    if seconds is None:
        return
    try:
        OBSERVED_LATENCY.labels(component=component).observe(float(seconds))
    except Exception:
        pass
    dq = _latency_windows.get(component)
    if dq is None:
        dq = deque(maxlen=_LATENCY_WINDOW_SIZE)
        _latency_windows[component] = dq
    dq.append(float(seconds))


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return sorted_values[0]
    if p >= 1:
        return sorted_values[-1]
    idx = int(round((len(sorted_values) - 1) * p))
    return sorted_values[idx]


def get_timeout_recommendation(component: str, default_seconds: float) -> float:
    auto = bool(getattr(settings, "TIMEOUT_AUTO_TUNE_ENABLED", False))
    perc = float(getattr(settings, "TIMEOUT_AUTO_TUNE_PERCENTILE", 0.95) or 0.95)
    pad = float(getattr(settings, "TIMEOUT_AUTO_TUNE_PAD_SECONDS", 0.5) or 0.0)
    min_map = getattr(settings, "TIMEOUT_MIN_SECONDS_MAP", {}) or {}
    max_map = getattr(settings, "TIMEOUT_MAX_SECONDS_MAP", {}) or {}
    base = float(default_seconds)
    if not auto:
        rec = base
    else:
        vals = list(_latency_windows.get(component, deque()))
        vals.sort()
        p95 = _percentile(vals, perc) if vals else 0.0
        rec = max(float(min_map.get(component, 0.0) or 0.0), base)
        if p95 > 0.0:
            rec = max(rec, p95 + pad)
    mx = max_map.get(component)
    if mx is not None:
        try:
            rec = min(rec, float(mx))
        except Exception:
            pass
    try:
        RECOMMENDED_TIMEOUT.labels(component=component).set(float(rec))
    except Exception:
        pass
    return float(rec)


class HealthStatus(Enum):
    """Status de saúde de um componente."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Resultado de um health check."""

    component: str
    status: HealthStatus
    message: str
    details: dict[str, Any]
    checked_at: datetime
    duration_seconds: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
            "duration_seconds": round(self.duration_seconds, 3),
            "error": self.error,
        }


class HealthMonitor:
    """
    Monitor centralizado de saúde do sistema.

    Executa health checks periódicos em todos os componentes
    e fornece visão agregada da saúde do sistema.
    """

    def __init__(self):
        self.health_checks: dict[str, Callable] = {}
        self.last_results: dict[str, HealthCheckResult] = {}
        self.check_interval_seconds = 30
        self._monitoring_task: asyncio.Task | None = None
        logger.info("HealthMonitor inicializado")

    def register_health_check(
        self, component: str, check_func: Callable[[], dict[str, Any]], is_critical: bool = True
    ):
        """
        Registra um health check para um componente.

        Args:
            component: Nome do componente
            check_func: Função assíncrona que retorna dict com status
            is_critical: Se True, falha afeta saúde geral do sistema
        """
        self.health_checks[component] = {"func": check_func, "is_critical": is_critical}
        logger.info(f"Health check registrado: {component} (critical={is_critical})")

    async def check_component(self, component: str) -> HealthCheckResult:
        """
        Executa health check de um componente específico.
        """
        if component not in self.health_checks:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNKNOWN,
                message="Health check não registrado",
                details={},
                checked_at=datetime.now(),
                duration_seconds=0.0,
            )

        check_info = self.health_checks[component]
        check_func = check_info["func"]

        start_time = asyncio.get_event_loop().time()
        try:
            # Executar check com timeout
            result = await asyncio.wait_for(
                asyncio.to_thread(check_func)
                if not asyncio.iscoroutinefunction(check_func)
                else check_func(),
                timeout=10.0,
            )

            duration = asyncio.get_event_loop().time() - start_time

            # Interpretar resultado
            status = HealthStatus(result.get("status", "healthy"))
            message = result.get("message", "OK")
            details = result.get("details", {})

            health_result = HealthCheckResult(
                component=component,
                status=status,
                message=message,
                details=details,
                checked_at=datetime.now(),
                duration_seconds=duration,
            )

            # Atualizar métricas
            status_value = {"healthy": 1.0, "degraded": 0.5, "unhealthy": 0.0}.get(
                status.value, 0.0
            )
            COMPONENT_HEALTH.labels(component=component).set(status_value)
            HEALTH_CHECK_DURATION.labels(component=component).set(duration)

            return health_result

        except TimeoutError:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f"Health check timeout para {component}")

            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message="Health check timeout",
                details={"timeout_seconds": 10.0},
                checked_at=datetime.now(),
                duration_seconds=duration,
                error="Timeout",
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            logger.error(f"Erro no health check de {component}: {e}", exc_info=True)

            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e!s}",
                details={},
                checked_at=datetime.now(),
                duration_seconds=duration,
                error=str(e),
            )

    async def check_all_components(self) -> dict[str, HealthCheckResult]:
        """
        Executa health checks de todos os componentes registrados.
        """
        results = {}

        # Executar checks em paralelo
        tasks = {
            component: self.check_component(component) for component in self.health_checks.keys()
        }

        completed = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for component, result in zip(tasks.keys(), completed):
            if isinstance(result, Exception):
                logger.error(f"Exceção ao verificar {component}: {result}")
                results[component] = HealthCheckResult(
                    component=component,
                    status=HealthStatus.UNHEALTHY,
                    message="Exception during check",
                    details={},
                    checked_at=datetime.now(),
                    duration_seconds=0.0,
                    error=str(result),
                )
            else:
                results[component] = result

        self.last_results = results
        return results

    def get_system_health(self) -> dict[str, Any]:
        """
        Retorna visão agregada da saúde do sistema.
        """
        if not self.last_results:
            return {
                "status": "unknown",
                "score": 0,
                "message": "Nenhum health check executado ainda",
                "components": {},
            }

        # Calcular score (0-100)
        total_components = len(self.last_results)
        healthy_count = sum(
            1 for r in self.last_results.values() if r.status == HealthStatus.HEALTHY
        )
        degraded_count = sum(
            1 for r in self.last_results.values() if r.status == HealthStatus.DEGRADED
        )

        score = int((healthy_count + degraded_count * 0.5) / total_components * 100)

        # Determinar status geral
        critical_components = [
            name for name, info in self.health_checks.items() if info["is_critical"]
        ]

        critical_unhealthy = any(
            self.last_results.get(
                comp,
                HealthCheckResult(
                    component=comp,
                    status=HealthStatus.UNKNOWN,
                    message="",
                    details={},
                    checked_at=datetime.now(),
                    duration_seconds=0.0,
                ),
            ).status
            == HealthStatus.UNHEALTHY
            for comp in critical_components
        )

        if critical_unhealthy:
            status = "unhealthy"
        elif score >= 80:
            status = "healthy"
        elif score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"

        # Atualizar métrica
        SYSTEM_HEALTH_SCORE.set(score)

        return {
            "status": status,
            "score": score,
            "message": f"{healthy_count}/{total_components} componentes saudáveis",
            "components": {name: result.to_dict() for name, result in self.last_results.items()},
            "last_check": max(
                (r.checked_at for r in self.last_results.values()), default=datetime.now()
            ).isoformat(),
            "suggested_timeouts": {
                "llm": get_timeout_recommendation(
                    "llm", float(getattr(settings, "LLM_DEFAULT_TIMEOUT_SECONDS", 60) or 60)
                ),
                "qdrant_search": get_timeout_recommendation(
                    "qdrant_search",
                    float(getattr(settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
                ),
                "neo4j_query": get_timeout_recommendation(
                    "neo4j_query",
                    float(getattr(settings, "NEO4J_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
                ),
                "rabbitmq_management": get_timeout_recommendation("rabbitmq_management", 5.0),
            },
        }

    async def start_monitoring(self, interval_seconds: int = 30):
        """
        Inicia monitoramento contínuo.

        Args:
            interval_seconds: Intervalo entre checks
        """
        self.check_interval_seconds = interval_seconds

        async def monitoring_loop():
            logger.info(f"Monitoramento iniciado (intervalo={interval_seconds}s)")

            while True:
                try:
                    await self.check_all_components()
                    await asyncio.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Erro no loop de monitoramento: {e}", exc_info=True)
                    await asyncio.sleep(interval_seconds)

        self._monitoring_task = asyncio.create_task(monitoring_loop())

    def stop_monitoring(self):
        """Para o monitoramento contínuo."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            logger.info("Monitoramento parado")


# --- Health Checks Padrão ---


async def check_llm_router_health() -> dict[str, Any]:
    """Health check do LLM Router."""
    try:
        from app.core.llm.resilience import get_circuit_breaker_snapshot, get_llm_pool_summary

        cb_snapshot = get_circuit_breaker_snapshot()
        pool_summary = get_llm_pool_summary()
        open_circuits = sum(1 for cb in cb_snapshot.values() if cb.get("state") == "OPEN")
        pool_instances = pool_summary["pool_total_instances"]
        total_circuits = len(cb_snapshot)

        if total_circuits > 0 and open_circuits >= total_circuits - 1:
            return {
                "status": "unhealthy",
                "message": "Todos os provedores com circuit breaker aberto",
                "details": {"open_circuits": open_circuits, "pool_instances": pool_instances},
            }
        elif open_circuits > 0:
            return {
                "status": "degraded",
                "message": f"{open_circuits} circuit breaker(s) aberto(s)",
                "details": {"open_circuits": open_circuits, "pool_instances": pool_instances},
            }
        else:
            return {
                "status": "healthy",
                "message": "Todos os provedores operacionais",
                "details": {"open_circuits": 0, "pool_instances": pool_instances},
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Erro ao verificar LLM Router: {e!s}",
            "details": {},
        }


async def check_multi_agent_system_health() -> dict[str, Any]:
    """Health check do sistema multi-agente."""
    try:
        from app.core.agents.multi_agent_system import get_multi_agent_system

        system = get_multi_agent_system()
        active_agents = len(system.agents)
        workspace_tasks = len(system.workspace.tasks)

        return {
            "status": "healthy",
            "message": f"{active_agents} agentes ativos",
            "details": {
                "active_agents": active_agents,
                "workspace_tasks": workspace_tasks,
                "pm_active": system.project_manager is not None,
            },
        }
    except Exception as e:
        return {
            "status": "degraded",
            "message": f"Erro ao verificar sistema multi-agente: {e!s}",
            "details": {},
        }


async def check_poison_pill_handler_health() -> dict[str, Any]:
    """Health check do poison pill handler."""
    try:
        from app.core.monitoring.poison_pill_handler import get_poison_pill_handler

        handler = get_poison_pill_handler()
        health_status = handler.get_health_status()

        return {
            "status": health_status["status"],
            "message": f"{health_status['total_quarantined']} mensagens em quarentena",
            "details": health_status,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "message": f"Erro ao verificar poison pill handler: {e!s}",
            "details": {},
        }


# --- Instância Global ---
_health_monitor: HealthMonitor | None = None


async def check_message_broker_health() -> dict[str, Any]:
    """Health check de conectividade do RabbitMQ (Message Broker)."""
    try:
        from app.core.infrastructure.message_broker import get_broker

        broker = await get_broker()
        ok = await broker.health_check()
        return {
            "status": "healthy" if ok else "unhealthy",
            "message": "Conexão com RabbitMQ está operacional" if ok else "RabbitMQ indisponível",
            "details": {},
        }
    except Exception as e:
        return {"status": "unhealthy", "message": f"Erro ao verificar broker: {e!s}", "details": {}}


async def check_consolidation_queue_policy_health() -> dict[str, Any]:
    """Valida a política/argumentos da fila de consolidação (TTL, max-length)."""
    try:
        from app.core.infrastructure.message_broker import get_broker
        from app.models.schemas import QueueName

        broker = await get_broker()
        await broker.get_queue_info(QueueName.KNOWLEDGE_CONSOLIDATION.value)
        result = await broker.validate_queue_policy(QueueName.KNOWLEDGE_CONSOLIDATION.value)
        return result
    except Exception as e:
        return {
            "status": "degraded",
            "message": f"Erro ao validar política da fila: {e!s}",
            "details": {},
        }


async def check_qdrant_health() -> dict[str, Any]:
    """Health check do Qdrant (Episodic Memory)."""
    try:
        from app.core.memory.memory_core import MemoryCore

        # Instancia temporária para checagem (o client é leve)
        mem = MemoryCore()

        # Tenta verificar coleção
        try:
            await mem.provider.client.get_collection(mem.collection_name)
            is_healthy = True
            msg = "Qdrant operacional"
        except Exception:
            # Tenta reviver (pode ser problema de conexão transiente)
            is_healthy = await mem._try_revive_connection()
            msg = "Qdrant recuperado" if is_healthy else "Qdrant indisponível"

        if is_healthy:
            return {
                "status": "healthy",
                "message": msg,
                "details": {"collection": mem.collection_name},
            }
        else:
            return {
                "status": "degraded",  # Degraded pois existe fallback de memória
                "message": "Qdrant offline (fallback memory-only ativo)",
                "details": {},
            }
    except Exception as e:
        return {"status": "unhealthy", "message": f"Erro crítico Qdrant: {e!s}", "details": {}}


def get_health_monitor() -> HealthMonitor:
    """Obtém a instância global do HealthMonitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()

        # Registrar health checks padrão
        _health_monitor.register_health_check(
            "llm_router", check_llm_router_health, is_critical=True
        )
        _health_monitor.register_health_check(
            "message_broker", check_message_broker_health, is_critical=True
        )
        _health_monitor.register_health_check(
            "episodic_memory_qdrant", check_qdrant_health, is_critical=True
        )
        _health_monitor.register_health_check(
            "multi_agent_system", check_multi_agent_system_health, is_critical=False
        )
        _health_monitor.register_health_check(
            "poison_pill_handler", check_poison_pill_handler_health, is_critical=False
        )
        _health_monitor.register_health_check(
            "rabbitmq_consolidation_queue_policy",
            check_consolidation_queue_policy_health,
            is_critical=False,
        )

    return _health_monitor
