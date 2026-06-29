import asyncio
import math
from collections.abc import Mapping
from typing import Any

import structlog
from app.core.workers.orchestrator import DisabledWorkerHandle

logger = structlog.get_logger(__name__)

SERVICE_STATUS_ALIASES = {
    "ok": "ok",
    "healthy": "ok",
    "operational": "ok",
    "up": "ok",
    "ready": "ok",
    "success": "ok",
    "pass": "ok",
    "passing": "ok",
    "degraded": "degraded",
    "warning": "degraded",
    "warn": "degraded",
    "partial": "degraded",
    "error": "error",
    "critical": "error",
    "unhealthy": "error",
    "down": "error",
    "failed": "error",
    "fail": "error",
    "unavailable": "error",
    "unknown": "unknown",
}


def _normalize_service_status(raw_status: Any) -> str:
    if raw_status is None:
        return "unknown"

    normalized = str(raw_status).strip().lower()
    if not normalized:
        return "unknown"

    return SERVICE_STATUS_ALIASES.get(normalized, "unknown")


def _finite_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


HEALTH_IMPACT_BY_SERVICE = {
    "agent": {
        "capability": "Automacao e orquestracao",
        "ok": (
            "Agentes e automacoes estao disponiveis para apoiar tarefas internas.",
            "Manter monitoramento normal.",
        ),
        "degraded": (
            "Automacoes podem ficar lentas ou parcialmente indisponiveis.",
            "Verificar filas, workers e logs de agentes antes de acionar rotinas autonomas.",
        ),
        "error": (
            "Automacoes centrais podem falhar; priorize operacao manual.",
            "Investigar o sistema multiagente e pausar execucoes autonomas sensiveis.",
        ),
        "unknown": (
            "Nao ha sinal confiavel sobre automacoes e agentes.",
            "Revalidar telemetria de observabilidade antes de confiar na automacao.",
        ),
    },
    "knowledge": {
        "capability": "RAG, conhecimento e citacoes",
        "ok": (
            "Busca de conhecimento e contexto RAG estao disponiveis.",
            "Manter operacao normal.",
        ),
        "degraded": (
            "Respostas com contexto e citacoes podem perder cobertura ou precisao.",
            "Validar Qdrant/Neo4j e qualidade das fontes antes de decisões criticas.",
        ),
        "error": (
            "RAG e consultas de conhecimento podem falhar ou retornar contexto incompleto.",
            "Investigar servicos de conhecimento antes de confiar em respostas com citacoes.",
        ),
        "unknown": (
            "Nao ha sinal confiavel sobre RAG e conhecimento.",
            "Reexecutar health de conhecimento e checar telemetria de indexacao.",
        ),
    },
    "memory": {
        "capability": "Memoria operacional",
        "ok": (
            "Memoria e telemetria de uso estao dentro do esperado.",
            "Manter operacao normal.",
        ),
        "degraded": (
            "Memoria esta sob pressao; recuperacao de contexto pode degradar.",
            "Reduzir carga, revisar consumo e avaliar limpeza/retencao.",
        ),
        "error": (
            "Memoria esta em estado critico; contexto persistente pode falhar.",
            "Investigar consumo de memoria e priorizar estabilizacao antes de uso intenso.",
        ),
        "unknown": (
            "Nao ha telemetria confiavel de memoria; o Janus pode estar operando no escuro.",
            "Restaurar coleta de metricas antes de avaliar estabilidade de memoria.",
        ),
    },
    "llm": {
        "capability": "Chat, raciocinio e modelos",
        "ok": (
            "Gateway de modelos esta disponivel para chat e tarefas de IA.",
            "Manter monitoramento de custo, latencia e circuit breakers.",
        ),
        "degraded": (
            "Chat pode responder com latencia maior ou fallback de modelo.",
            "Verificar provedores, circuit breakers, rate limits e modelo local.",
        ),
        "error": (
            "Chat e raciocinio por IA podem ficar indisponiveis.",
            "Restaurar ao menos um provedor LLM funcional antes de uso central.",
        ),
        "unknown": (
            "Nao ha sinal confiavel do gateway LLM; respostas de IA podem ser imprevisiveis.",
            "Executar health do LLM router e validar Ollama/provedores configurados.",
        ),
    },
    "workers": {
        "capability": "Workers e operacoes assincronas",
        "ok": (
            "Workers acompanhados estao ativos para processar tarefas assincronas.",
            "Manter monitoramento de filas, retries e DLQ.",
        ),
        "degraded": (
            "Algumas rotinas assincronas podem atrasar ou ficar indisponiveis.",
            "Verificar workers parados/desabilitados e iniciar filas antes de cargas longas.",
        ),
        "error": (
            "Workers falharam; ingestao, consolidacao ou automacoes de fundo podem parar.",
            "Inspecionar excecoes dos workers, RabbitMQ e logs antes de depender de tarefas async.",
        ),
        "unknown": (
            "Nao ha telemetria confiavel dos workers; degradacao assincrona pode estar invisivel.",
            "Restaurar o registro de workers e validar /api/v1/workers/status.",
        ),
    },
}


def _apply_user_impact(item: dict[str, str]) -> dict[str, str]:
    service_impact = HEALTH_IMPACT_BY_SERVICE.get(item["key"], {})
    status = item["status"]
    impact, action = service_impact.get(
        status,
        (
            "Impacto operacional nao classificado para este componente.",
            "Investigar telemetria do componente antes de assumir saude operacional.",
        ),
    )
    return {
        **item,
        "capability": service_impact.get("capability", "Capacidade operacional"),
        "user_impact": impact,
        "recommended_action": action,
    }


def _unknown_item(key: str, name: str, metric_text: str) -> dict[str, str]:
    return _apply_user_impact({
        "key": key,
        "name": name,
        "status": "unknown",
        "metric_text": metric_text,
    })


async def _agent_health_item(observability: Any) -> dict[str, str]:
    try:
        agent_h = await observability.get_multi_agent_system_health()
        agent_status = _normalize_service_status(agent_h.get("status"))
        active_agents = agent_h.get("details", {}).get("active_agents")
        return _apply_user_impact({
            "key": "agent",
            "name": "Agent Service",
            "status": agent_status,
            "metric_text": f"Agentes: {active_agents if active_agents is not None else 'N/A'}",
        })
    except Exception:
        logger.warning("system_health_subsystem_unavailable", subsystem="agent", exc_info=True)
        return _unknown_item("agent", "Agent Service", "Agentes: indisponivel")


async def _knowledge_health_item(knowledge: Any) -> dict[str, str]:
    try:
        knowledge_h = await knowledge.get_health_status()
        knowledge_status = _normalize_service_status(knowledge_h.get("status"))
        total_nodes = knowledge_h.get("total_nodes")
        return _apply_user_impact({
            "key": "knowledge",
            "name": "Knowledge Service",
            "status": knowledge_status,
            "metric_text": (
                f"Ontologias: {total_nodes if isinstance(total_nodes, (int, float)) else 'N/A'}"
            ),
        })
    except Exception:
        logger.warning("system_health_subsystem_unavailable", subsystem="knowledge", exc_info=True)
        return _unknown_item("knowledge", "Knowledge Service", "Ontologias: indisponivel")


async def _llm_health_item(llm: Any) -> dict[str, str]:
    try:
        llm_h = await llm.get_health_status()
        llm_status = _normalize_service_status(llm_h.get("status"))
        llm_details = llm_h.get("details", {})
        open_cb = llm_details.get("open_circuits", 0)
        cached_llms = llm_details.get("cached_llms", 0)
        return _apply_user_impact({
            "key": "llm",
            "name": "LLM Gateway",
            "status": llm_status,
            "metric_text": f"CB Abertos: {open_cb}, Cache: {cached_llms}",
        })
    except Exception:
        logger.warning("system_health_subsystem_unavailable", subsystem="llm", exc_info=True)
        return _unknown_item("llm", "LLM Gateway", "CB Abertos: N/A, Cache: N/A")


async def _read_memory_usage_mb(optimization: Any) -> float | None:
    try:
        analysis = await optimization.analyze_system(analysis_type="performance", detailed=False)
        raw_mem_mb = analysis.get("metrics_snapshot", {}).get("memory_usage_mb")
        if raw_mem_mb is not None:
            mem_mb = _finite_float_or_none(raw_mem_mb)
            if mem_mb is not None:
                return mem_mb
    except Exception:
        pass
    return await _read_memory_usage_mb_from_history(optimization)


async def _read_memory_usage_mb_from_history(optimization: Any) -> float | None:
    try:
        history = await optimization.get_metrics_history(limit=1)
        if not history:
            return None
        last = history[-1]
        raw_mem_mb = getattr(last, "memory_usage_mb", None)
        if raw_mem_mb is None:
            return None
        return _finite_float_or_none(raw_mem_mb)
    except Exception:
        return None


def _memory_health_item(mem_mb: float | None) -> dict[str, str]:
    if mem_mb is None:
        return _unknown_item("memory", "Memory Service", "Uso: indisponivel")

    status = "ok"
    if mem_mb >= 8192:
        status = "degraded"
    if mem_mb >= 16384:
        status = "error"
    return _apply_user_impact({
        "key": "memory",
        "name": "Memory Service",
        "status": status,
        "metric_text": f"Uso: {int(round(mem_mb))}MB",
    })


def _worker_task_state(task: Any) -> str:
    if isinstance(task, DisabledWorkerHandle):
        return "disabled"

    if isinstance(task, (list, tuple)):
        child_states = [_worker_task_state(child) for child in task]
        if any(state == "error" for state in child_states):
            return "error"
        if any(state == "running" for state in child_states):
            return "running"
        if child_states and all(state == "disabled" for state in child_states):
            return "disabled"
        if any(state == "unknown" for state in child_states):
            return "unknown"
        return "stopped"

    try:
        if not hasattr(task, "done") or not hasattr(task, "cancelled"):
            return "unknown"

        if bool(task.cancelled()):
            return "stopped"

        if not bool(task.done()):
            return "running"

        try:
            exception = task.exception()
        except Exception:
            exception = None
        return "error" if exception else "stopped"
    except Exception:
        logger.warning("system_health_worker_state_unavailable", exc_info=True)
        return "unknown"


def build_workers_health_item(raw_workers: Any) -> dict[str, str]:
    if not isinstance(raw_workers, list):
        logger.warning(
            "system_health_invalid_workers_collection",
            collection_type=type(raw_workers).__name__,
        )
        return _unknown_item("workers", "Workers", "Workers: telemetria indisponivel")

    counts = {
        "running": 0,
        "stopped": 0,
        "disabled": 0,
        "error": 0,
        "unknown": 0,
        "ignored": 0,
    }

    for index, worker in enumerate(raw_workers):
        if not isinstance(worker, Mapping):
            counts["ignored"] += 1
            logger.warning(
                "system_health_invalid_worker_item",
                index=index,
                item_type=type(worker).__name__,
            )
            continue

        state = _worker_task_state(worker.get("task"))
        counts[state if state in counts else "unknown"] += 1

    tracked = len(raw_workers) - counts["ignored"]
    if counts["error"] > 0:
        status = "error"
    elif tracked <= 0:
        status = "degraded"
    elif counts["unknown"] > 0:
        status = "unknown"
    elif counts["stopped"] > 0 or counts["disabled"] > 0:
        status = "degraded"
    else:
        status = "ok"

    metric_parts = [
        f"ativos: {counts['running']}",
        f"parados: {counts['stopped']}",
        f"desabilitados: {counts['disabled']}",
        f"erros: {counts['error']}",
        f"desconhecidos: {counts['unknown']}",
    ]
    if counts["ignored"] > 0:
        metric_parts.append(f"ignorados: {counts['ignored']}")

    return _apply_user_impact({
        "key": "workers",
        "name": "Workers",
        "status": status,
        "metric_text": "Workers " + ", ".join(metric_parts),
    })


async def _memory_health_item_from_optimization(optimization: Any) -> dict[str, str]:
    return _memory_health_item(await _read_memory_usage_mb(optimization))


async def build_service_health_items(
    observability: Any,
    knowledge: Any,
    llm: Any,
    optimization: Any,
    workers: Any | None = None,
) -> list[dict[str, str]]:
    agent_item, knowledge_item, memory_item, llm_item = await asyncio.gather(
        _agent_health_item(observability),
        _knowledge_health_item(knowledge),
        _memory_health_item_from_optimization(optimization),
        _llm_health_item(llm),
    )
    items = [agent_item, knowledge_item, memory_item, llm_item]
    if workers is not None:
        items.append(build_workers_health_item(workers))
    return items
