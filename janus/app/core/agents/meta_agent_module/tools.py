import json
import logging
import statistics
import asyncio
from typing import Any
from datetime import datetime
from langchain_core.tools import tool

from app.core.monitoring.health_monitor import get_health_monitor, _latency_windows
from app.core.monitoring.error_tracker import GlobalErrorTracker

logger = logging.getLogger(__name__)


@tool
def analyze_memory_for_failures(time_window_hours: Any = 24, max_results: Any = 50) -> str:
    """
    Analisa a memória episódica em busca de padrões de falha.

    Args:
        time_window_hours: Janela de tempo para análise (horas) — aceita número ou JSON
        max_results: Número máximo de resultados — aceita número ou JSON

    Returns:
        JSON string com falhas encontradas e padrões identificados
    """
    try:
        # Normalização de inputs: suportar strings JSON ou strings numéricas
        try:
            if isinstance(time_window_hours, str):
                s = time_window_hours.strip()
                if s.startswith("{") and s.endswith("}"):
                    cfg = json.loads(s)
                    time_window_hours = cfg.get("time_window_hours", time_window_hours)
                    max_results = cfg.get("max_results", max_results)
            if isinstance(max_results, str):
                s2 = max_results.strip()
                if s2.startswith("{") and s2.endswith("}"):
                    cfg2 = json.loads(s2)
                    max_results = cfg2.get("max_results", max_results)
                    time_window_hours = cfg2.get("time_window_hours", time_window_hours)
            time_window_hours = int(time_window_hours)
            max_results = int(max_results)
        except Exception:
            time_window_hours = 24
            max_results = 50

        # Buscar experiências de falha usando MemoryCore (Qdrant)
        query = "error failure exception crash bug"

        import asyncio
        from app.core.memory.memory_core import get_memory_db

        async def _fetch_failures():
            mem = await get_memory_db()
            results = await mem.arecall_filtered(
                query=query, filters={"type": "action_failure"}, limit=max_results
            )
            return results

        try:
            # Try to get running loop to avoid "loop is already running" error if called within async context
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # We are likely in a sync wrapper of a tool called by LangChain or similar
                # For safety in this specific context (tool execution), we might need to rely on
                # the fact that this tool is often called in a thread pool by LangChain
                # But if invoked directly, we need robust handling.
                # For now, let's assume standard thread pool execution via asyncio.run if isolated,
                # or direct wait if we can. But 'tool' decorators usually imply sync interface often.
                # Let's inspect the context. The original code used asyncio.run() which is risky inside loops.
                # Refactoring to use a safe runner or assume thread pool.
                # Since this is a @tool, it might be running in a thread.
                results = asyncio.run_coroutine_threadsafe(_fetch_failures(), loop).result()
            else:
                results = asyncio.run(_fetch_failures())
        except RuntimeError:
            # Fallback if no loop is running (standard script execution)
            results = asyncio.run(_fetch_failures())

        if not results:
            return json.dumps(
                {
                    "status": "no_failures",
                    "message": "Nenhuma falha detectada no período",
                    "time_window_hours": time_window_hours,
                }
            )

        # Analisar padrões
        error_types = {}
        affected_components = {}

        for result in results:
            metadata = result.get("metadata", {})
            error_type = metadata.get("error_type", "unknown")
            component = metadata.get("component", "unknown")

            error_types[error_type] = error_types.get(error_type, 0) + 1
            affected_components[component] = affected_components.get(component, 0) + 1

        analysis = {
            "status": "failures_found",
            "total_failures": len(results),
            "time_window_hours": time_window_hours,
            "error_types": error_types,
            "affected_components": affected_components,
            "most_common_error": max(error_types, key=error_types.get) if error_types else None,
            "most_affected_component": (
                max(affected_components, key=affected_components.get)
                if affected_components
                else None
            ),
            "sample_failures": [
                {"content": r.get("content", "")[:200], "metadata": r.get("metadata", {})}
                for r in results[:5]
            ],
        }

        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Erro ao analisar memória: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_system_health_metrics() -> str:
    """
    Obtém métricas atuais de saúde do sistema.

    Returns:
        JSON string com métricas de saúde de todos os componentes
    """
    try:
        from app.core.agents.multi_agent_system import get_multi_agent_system
        from app.core.llm.llm_manager import _llm_pool, _provider_circuit_breakers
        from app.core.monitoring.poison_pill_handler import get_poison_pill_handler

        health_monitor = get_health_monitor()
        system_health = health_monitor.get_system_health()

        # Métricas adicionais
        ma_system = get_multi_agent_system()
        pp_handler = get_poison_pill_handler()

        error_stats = GlobalErrorTracker.get_instance().get_stats()

        # Task Statistics
        task_stats = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0, "blocked": 0}
        recent_failures = []

        if ma_system.workspace and ma_system.workspace.tasks:
            for t in ma_system.workspace.tasks.values():
                status_key = t.status.value.lower()
                if status_key in task_stats:
                    task_stats[status_key] += 1

                if t.status.value == "failed":
                    recent_failures.append(
                        {
                            "id": t.id,
                            "description": t.description,
                            "error": t.error,
                            "completed_at": str(t.completed_at),
                        }
                    )

        metrics = {
            "system_health": system_health,
            "error_tracking": error_stats,
            "llm_manager": {
                "pool_keys": len(_llm_pool),
                "pool_total_instances": sum(len(v) for v in _llm_pool.values()),
                "circuit_breakers": {
                    provider: {"state": cb.state.value, "failure_count": cb.failure_count}
                    for provider, cb in _provider_circuit_breakers.items()
                },
            },
            "multi_agent_system": {
                "active_agents": len(ma_system.agents),
                "workspace_tasks": len(ma_system.workspace.tasks) if ma_system.workspace else 0,
                "workspace_artifacts": (
                    len(ma_system.workspace.artifacts) if ma_system.workspace else 0
                ),
                "workspace_messages": (
                    len(ma_system.workspace.messages) if ma_system.workspace else 0
                ),
                "task_stats": task_stats,
                "recent_failures": recent_failures[-5:],  # Last 5
            },
            "poison_pills": pp_handler.get_health_status(),
        }

        return json.dumps(metrics, indent=2)

    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})


@tool
def analyze_performance_trends(metric_name: str, hours: int = 24) -> str:
    """
    Analisa tendências de performance de uma métrica específica baseada em dados em memória.

    Args:
        metric_name: Nome da métrica (ex: llm_latency, task_duration, component_health)
        hours: Janela de tempo para análise

    Returns:
        JSON string com análise de tendências
    """
    try:
        data_points = []

        # 1. Tentar obter dados de latência do HealthMonitor
        if "latency" in metric_name:
            # Tentar inferir o componente pelo nome da métrica ou usar todos
            component = None
            if "_" in metric_name:
                parts = metric_name.split("_")
                if parts[0] in _latency_windows:
                    component = parts[0]

            if component:
                vals = list(_latency_windows.get(component, []))
                data_points = vals
            else:
                # Agrega latências de todos os componentes se não especificado
                all_vals = []
                for q in _latency_windows.values():
                    all_vals.extend(list(q))
                data_points = all_vals

        # 2. Se for health score
        elif "health" in metric_name:
            monitor = get_health_monitor()
            # Health monitor armazena apenas último estado, então retornamos snapshot atual
            # Idealmente teríamos histórico, mas por enquanto usamos estado atual
            score = monitor.get_system_health().get("score", 0)
            data_points = [score]

        if not data_points:
            return json.dumps(
                {
                    "metric": metric_name,
                    "status": "no_data",
                    "message": f"Sem dados históricos para a métrica '{metric_name}' na memória.",
                }
            )

        # Calcular estatísticas básicas
        avg = statistics.mean(data_points) if data_points else 0
        p95 = (
            statistics.quantiles(data_points, n=20)[-1]
            if len(data_points) >= 20
            else max(data_points) if data_points else 0
        )

        # Simples detecção de tendência (comparar primeira e segunda metade)
        trend = "stable"
        if len(data_points) > 10:
            mid = len(data_points) // 2
            first_half = statistics.mean(data_points[:mid])
            second_half = statistics.mean(data_points[mid:])
            if second_half > first_half * 1.1:
                trend = "degrading"  # Aumento de latência/valor
            elif second_half < first_half * 0.9:
                trend = "improving"

        analysis = {
            "metric": metric_name,
            "data_points_count": len(data_points),
            "trend": trend,
            "average": round(avg, 4),
            "p95": round(p95, 4),
            "min": round(min(data_points), 4) if data_points else 0,
            "max": round(max(data_points), 4) if data_points else 0,
        }

        return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Erro ao analisar performance: {e}")
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_resource_usage() -> str:
    """
    Obtém informações detalhadas sobre uso de recursos do sistema via psutil.

    Returns:
        JSON string com uso de CPU, memória, disco e rede.
    """
    try:
        import os
        import psutil

        # Processo atual
        process = psutil.Process(os.getpid())

        resources = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent_total": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else "N/A",
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent_used": psutil.virtual_memory().percent,
                "swap_used_percent": psutil.swap_memory().percent,
            },
            "disk": {
                "total_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
                "free_gb": round(psutil.disk_usage("/").free / (1024**3), 2),
                "percent_used": psutil.disk_usage("/").percent,
            },
            "process": {
                "cpu_percent": process.cpu_percent(interval=None),
                "memory_info_mb": round(process.memory_info().rss / (1024 * 1024), 2),
                "threads": process.num_threads(),
            },
        }

        return json.dumps(resources, indent=2)

    except ImportError:
        return json.dumps({"status": "error", "message": "Biblioteca 'psutil' não instalada."})
    except Exception as e:
        logger.error(f"Erro ao obter recursos: {e}", exc_info=True)
        return json.dumps({"status": "error", "message": str(e)})
