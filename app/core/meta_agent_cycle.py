import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agent_manager import agent_manager, AgentType
from app.core.memory_core import memory_core

logger = logging.getLogger(__name__)


class Phase(Enum):
    PLAN = "plan"
    ACT = "act"
    OBSERVE = "observe"
    REFINE = "refine"


# Métricas do ciclo
_META_EVENTS = Counter(
    "meta_agent_events_total", "Eventos do meta-agente por fase", ["phase", "outcome"]
)
_META_LAT = Histogram(
    "meta_agent_phase_latency_seconds", "Latência por fase do meta-agente", ["phase", "outcome"]
)

# Hook de interrupção do ciclo atual
_interrupt_event: Optional[asyncio.Event] = None


def request_stop_current_cycle():
    """Permite que outros componentes solicitem a interrupção segura do ciclo atual."""
    global _interrupt_event
    if _interrupt_event is not None:
        _interrupt_event.set()


async def _run_phase(phase: Phase, coro_or_func, *args, **kwargs) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        if asyncio.iscoroutinefunction(coro_or_func):
            result = await coro_or_func(*args, **kwargs)
        else:
            result = coro_or_func(*args, **kwargs)
        _META_EVENTS.labels(phase.value, "success").inc()
        _META_LAT.labels(phase.value, "success").observe(time.perf_counter() - start)
        return {"ok": True, "result": result}
    except Exception as e:
        _META_EVENTS.labels(phase.value, "error").inc()
        _META_LAT.labels(phase.value, "error").observe(time.perf_counter() - start)
        logger.error({"event": "meta_agent_phase_error", "phase": phase.value, "error": str(e)}, exc_info=True)
        return {"ok": False, "error": str(e)}


async def run_meta_agent_cycle():
    """
    Executa o ciclo de vida proativo do Meta-Agente em um loop infinito com máquina de estados explícita.
    Estados: PLAN -> ACT -> OBSERVE -> REFINE (repete) até atingir limites de iteração/tempo.
    """
    logger.info("Ciclo de vida do Meta-Agente iniciado. Primeira verificação em breve.")
    global _interrupt_event

    while True:
        try:
            await asyncio.sleep(settings.META_AGENT_CYCLE_INTERVAL_SECONDS)
            _interrupt_event = asyncio.Event()
            logger.info("=" * 80)
            logger.info("META-AGENTE: Iniciando ciclo de auto-análise...")

            time_budget = settings.META_AGENT_MAX_SECONDS
            start_cycle = time.perf_counter()
            max_iter = max(1, settings.META_AGENT_MAX_ITERATIONS)
            iteration = 0

            # Estado compartilhado entre fases
            shared: Dict[str, Any] = {
                "hypothesis": None,
                "actions": [],
                "observations": [],
                "refinements": [],
            }

            async def _phase_plan() -> Dict[str, Any]:
                prompt = "Você é o supervisor. Crie um plano conciso para analisar logs/experiências recentes e detectar padrões de falha recorrentes."
                result = agent_manager.run_agent(
                    question=prompt,
                    request=None,
                    agent_type=AgentType.META_AGENT,
                )
                plan = result.get("answer") or "Analisar últimas experiências e métricas."
                return {"plan": plan}

            def _phase_act() -> Dict[str, Any]:
                # Ação principal: solicitar ao meta-agente a análise usando ferramenta de memória
                query = "experiência do agente"
                experiences = memory_core.recall(query=query, n_results=10)
                result = agent_manager.run_agent(
                    question=f"Analise estas experiências e aponte padrões de falha ou ineficiências. {experiences}",
                    request=None,
                    agent_type=AgentType.META_AGENT,
                )
                return {"analysis": result.get("answer", "")}

            def _phase_observe(act_result: Dict[str, Any]) -> Dict[str, Any]:
                analysis = act_result.get("analysis", "")
                # Observa se há sinais claros de problema
                has_issue = any(k in analysis.lower() for k in ["falha", "erro", "ineficiência", "caiu", "timeout"])
                return {"has_issue": has_issue, "analysis": analysis}

            def _phase_refine(obs: Dict[str, Any]) -> Dict[str, Any]:
                if obs.get("has_issue"):
                    refinement = "Recomendar tarefa para TOOL_USER investigar e corrigir causa raiz."
                else:
                    refinement = "Sem problemas críticos detectados; registrar status saudável."
                return {"refinement": refinement}

            while iteration < max_iter and (time.perf_counter() - start_cycle) < time_budget:
                if _interrupt_event.is_set():
                    logger.warning("META-AGENTE: Interrupção solicitada. Encerrando ciclo atual com segurança.")
                    break
                iteration += 1
                logger.info({"event": "meta_agent_iteration_start", "iteration": iteration})

                # PLAN
                res_plan = await _run_phase(Phase.PLAN, _phase_plan)
                if res_plan.get("ok"):
                    shared["hypothesis"] = res_plan["result"].get("plan")
                # checkpoint
                try:
                    from app.models.schemas import Experience
                    memory_core.memorize(Experience(type="meta_agent_checkpoint", content=f"PLAN[{iteration}]: {shared.get('hypothesis')}", metadata={"origin": "meta_agent"}))
                except Exception:
                    pass

                # ACT
                res_act = await _run_phase(Phase.ACT, _phase_act)
                # OBSERVE
                res_obs = await _run_phase(Phase.OBSERVE, _phase_observe, res_act.get("result", {}))
                shared["observations"].append(res_obs.get("result", {}))
                # REFINE
                res_ref = await _run_phase(Phase.REFINE, _phase_refine, res_obs.get("result", {}))
                shared["refinements"].append(res_ref.get("result", {}))

                # checkpoint pós-ciclo
                try:
                    from app.models.schemas import Experience
                    memory_core.memorize(Experience(type="meta_agent_checkpoint", content=f"OBSERVE/REFINE[{iteration}]", metadata={"origin": "meta_agent"}))
                except Exception:
                    pass

                # critério de parada antecipado
                if res_obs.get("result", {}).get("has_issue") is False:
                    # se estiver saudável, pode parar mais cedo
                    break

            elapsed = time.perf_counter() - start_cycle
            logger.info({"event": "meta_agent_cycle_end", "iterations": iteration, "elapsed_s": round(elapsed, 2)})

            # Relatório final
            final_answer = shared.get("refinements", [{}])[-1].get("refinement", "Sem conclusão.")
            logger.info(f"META-AGENTE: Conclusão: {final_answer}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Ocorreu um erro crítico no ciclo do Meta-Agente: {e}", exc_info=True)
            # Espera um intervalo mais longo antes de tentar novamente para evitar loops de erro rápidos.
            await asyncio.sleep(settings.META_AGENT_CYCLE_INTERVAL_SECONDS * 2)
