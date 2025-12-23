import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable

import structlog
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.infrastructure.resilience import CircuitBreaker
from app.core.memory.memory_core import get_memory_db
from app.db.graph import graph_db
from app.core.infrastructure.prompt_loader import prompt_loader
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

class Phase(Enum):
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFINE = "refine"

_META_EVENTS = Counter("meta_agent_events_total", "Eventos do meta-agente por fase", ["phase", "outcome"])
_META_LAT = Histogram("meta_agent_phase_latency_seconds", "Latência por fase do meta-agente", ["phase", "outcome"])

_interrupt_event: Optional[asyncio.Event] = None
_meta_agent_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)

_MAX_CONSECUTIVE_FAILURES = 10
_PHASE_TIMEOUT = getattr(settings, "META_AGENT_PHASE_TIMEOUT", 180)

def request_stop_current_cycle():
    global _interrupt_event
    if _interrupt_event is not None:
        _interrupt_event.set()

async def _run_phase(phase: Phase, func: Callable, *args, **kwargs) -> Dict[str, Any]:
    phase_name = phase.value
    start = time.perf_counter()
    try:
        logger.info(f"META-AGENT: Iniciando fase {phase_name}")
        result = await asyncio.wait_for(func(*args, **kwargs), timeout=_PHASE_TIMEOUT)
        elapsed = time.perf_counter() - start
        _META_EVENTS.labels(phase.value, "success").inc()
        _META_LAT.labels(phase.value, "success").observe(elapsed)
        logger.info(f"META-AGENT: Fase {phase_name} concluída com sucesso em {elapsed:.2f}s.")
        return {"ok": True, "result": result}
    except asyncio.TimeoutError:
        elapsed = time.perf_counter() - start
        _META_EVENTS.labels(phase.value, "timeout").inc()
        _META_LAT.labels(phase.value, "timeout").observe(elapsed)
        logger.error(f"META-AGENT: Timeout na fase {phase_name} após {_PHASE_TIMEOUT}s")
        return {"ok": False, "error": "timeout", "result": None}
    except Exception as e:
        elapsed = time.perf_counter() - start
        _META_EVENTS.labels(phase.value, "error").inc()
        _META_LAT.labels(phase.value, "error").observe(elapsed)
        logger.error(f"META-AGENT: Erro na fase {phase_name}: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "result": None}

async def _execute_meta_cycle(shared: Dict[str, Any]) -> bool:
    iteration = shared.get("iteration", 0)

    async def _phase_plan() -> Dict[str, Any]:
        prompt = prompt_loader.get("meta_agent_plan")
        result = await agent_manager.arun_agent(question=prompt, request=None, agent_type=AgentType.META_AGENT)
        plan = result.get(
            "answer") if result and "answer" in result else "Plano padrão: Consultar o Grafo de Conhecimento por lições aprendidas (Reflections) e analisar padrões."
        return {"plan": plan}

    async def _phase_act() -> Dict[str, Any]:
        logger.info("Consultando Grafo de Conhecimento por lições aprendidas (Reflections).")
        reflections = []
        try:
            async with graph_db.get_driver().session() as session:
                # Esta consulta busca os 15 insights mais recentes dos nós de Reflexão.
                query = "MATCH (r:Reflection) RETURN r.insight as insight ORDER BY r.createdAt DESC LIMIT 15"
                result = await session.run(query)
                reflections = [record["insight"] for record in await result.list()]
        except Exception as e:
            logger.error(f"META-AGENT (ACT): Falha ao consultar o Grafo de Conhecimento: {e}", exc_info=True)
            return {"analysis": "Falha crítica ao acessar a Memória Semântica (Grafo de Conhecimento)."}

        if not reflections:
            analysis = "Nenhuma reflexão (lição aprendida) encontrada no Grafo de Conhecimento. O sistema parece estável ou ainda não consolidou novas falhas."
            logger.info(analysis)
            return {"analysis": analysis, "has_issue": False}

        reflections_str = "\n- ".join(reflections)
        prompt = prompt_loader.get("meta_agent_act", variables={"learning_lessons": reflections_str})
        
        result = await agent_manager.arun_agent(
            question=prompt,
            request=None,
            agent_type=AgentType.META_AGENT,
        )

        analysis = result.get("answer", "Falha ao analisar as reflexões.") if result else "Nenhuma resposta do agente."
        return {"analysis": analysis, "has_issue": True}

    async def _phase_observe(act_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not act_result:
            return {"has_issue": True, "analysis": "Fase ACT falhou, impossível observar."}

        analysis = act_result.get("analysis", "")
        # A decisão de 'has_issue' agora é primariamente determinada pela fase ACT.
        has_issue = act_result.get("has_issue", False)
        return {"has_issue": has_issue, "analysis": analysis}

    async def _phase_refine(obs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not obs:
            return {"refinement": "Fase OBSERVE falhou, impossível refinar."}
        if obs.get("has_issue"):
            refinement = f"Hipótese de problema detectada com base na análise do Grafo de Conhecimento. Análise: {obs.get('analysis', '')}. Recomendar investigação humana ou criação de um agente corretivo."
        else:
            refinement = "Nenhum problema crítico detectado na Memória Semântica. O sistema está operando conforme as lições aprendidas."
        return {"refinement": refinement}

    res_plan = await _run_phase(Phase.PLAN, _phase_plan)
    if res_plan.get("ok"): shared["hypothesis"] = res_plan.get("result", {}).get("plan")

    try:
        memory_db = await get_memory_db()
        await memory_db.amemorize(
            Experience(type="meta_agent_checkpoint", content=f"PLAN[{iteration}]: {shared.get('hypothesis')}",
                       metadata={"origin": "meta_agent"}))
    except Exception as e:
        logger.warning(f"Falha ao salvar checkpoint PLAN: {e}")

    res_act = await _run_phase(Phase.ACT, _phase_act)
    res_obs = await _run_phase(Phase.OBSERVE, _phase_observe, res_act.get("result"))
    if res_obs.get("ok"): shared["observations"].append(res_obs.get("result"))

    res_ref = await _run_phase(Phase.REFINE, _phase_refine, res_obs.get("result"))
    if res_ref.get("ok"): shared["refinements"].append(res_ref.get("result"))

    try:
        memory_db = await get_memory_db()
        await memory_db.amemorize(Experience(type="meta_agent_checkpoint", content=f"OBSERVE/REFINE[{iteration}]",
                                               metadata={"origin": "meta_agent"}))
    except Exception as e:
        logger.warning(f"Falha ao salvar checkpoint pós-ciclo: {e}")

    observe_result = res_obs.get("result")
    if observe_result and observe_result.get("has_issue") is False:
        logger.info("META-AGENT: Sistema saudável detectado. Encerrando ciclo antecipadamente.")
        return False

    return True

async def run_meta_agent_cycle():
    logger.info("Ciclo de vida do Meta-Agente iniciado.")
    global _interrupt_event
    consecutive_failures = 0
    while True:
        try:
            await asyncio.sleep(settings.META_AGENT_CYCLE_INTERVAL_SECONDS)
            _interrupt_event = asyncio.Event()
            if _meta_agent_breaker.is_open():
                logger.warning("META-AGENT: Circuit breaker OPEN. Aguardando recuperação...")
                await asyncio.sleep(60)
                continue

            logger.info("=" * 80)
            logger.info("META-AGENTE: Iniciando ciclo de auto-análise...")
            start_cycle = time.perf_counter()
            shared = {"hypothesis": None, "actions": [], "observations": [], "refinements": [], "iteration": 0}

            async def protected_cycle():
                iteration = 0
                while iteration < settings.META_AGENT_MAX_ITERATIONS and (
                        time.perf_counter() - start_cycle) < settings.META_AGENT_MAX_SECONDS:
                    if _interrupt_event.is_set():
                        logger.warning("META-AGENTE: Interrupção solicitada. Encerrando ciclo.")
                        break
                    iteration += 1
                    shared["iteration"] = iteration
                    logger.info({"event": "meta_agent_iteration_start", "iteration": iteration})
                    if not await _execute_meta_cycle(shared):
                        break
                return iteration

            iteration_count = await _meta_agent_breaker.call_async(protected_cycle)
            elapsed = time.perf_counter() - start_cycle
            logger.info(
                {"event": "meta_agent_cycle_end", "iterations": iteration_count, "elapsed_s": round(elapsed, 2)})

            final_refinement = (shared.get("refinements") or [{}])[-1]
            final_answer = final_refinement.get("refinement", "Sem conclusão.")
            logger.info(f"META-AGENTE: Conclusão: {final_answer}")
            logger.info("=" * 80)
            consecutive_failures = 0

        except asyncio.CancelledError:
            logger.info("META-AGENT: Task cancelada. Encerrando...")
            break
        except Exception as e:
            consecutive_failures += 1
            logger.critical(f"META-AGENT: Erro CRÍTICO ({consecutive_failures}/{_MAX_CONSECUTIVE_FAILURES}): {e}",
                            exc_info=True)
            if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.critical("META-AGENT: Limite de falhas consecutivas atingido. ENCERRANDO.")
                break
            backoff = min(600, settings.META_AGENT_CYCLE_INTERVAL_SECONDS * (2 ** consecutive_failures))
            logger.warning(f"META-AGENT: Aguardando {backoff}s antes de retry...")
            await asyncio.sleep(backoff)
