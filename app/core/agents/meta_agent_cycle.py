import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.memory.memory_core import memory_core
from app.core.infrastructure.resilience import CircuitBreaker, CircuitOpenError

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

# Circuit Breaker para proteger o ciclo do meta-agente
_meta_agent_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)

# Constantes configuráveis
_MAX_CONSECUTIVE_FAILURES = 10
_PHASE_TIMEOUT = getattr(settings, "META_AGENT_PHASE_TIMEOUT", 60)  # segundos


def request_stop_current_cycle():
    """Permite que outros componentes solicitem a interrupção segura do ciclo atual."""
    global _interrupt_event
    if _interrupt_event is not None:
        _interrupt_event.set()


async def _run_phase(phase: Phase, func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Executa uma fase do meta-agente com timeout e tratamento de erros robusto.

    Args:
        phase: Fase atual do ciclo
        func: Função a ser executada (sync ou async)
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados

    Returns:
        Dicionário com resultado ou erro
    """
    phase_name = phase.value
    start = time.perf_counter()

    try:
        logger.info(f"META-AGENT: Iniciando fase {phase_name}")

        # Determina se a função é assíncrona ou síncrona e executa adequadamente
        if asyncio.iscoroutinefunction(func):
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=_PHASE_TIMEOUT
            )
        else:
            # Executa função síncrona em thread separada para não bloquear event loop
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                timeout=_PHASE_TIMEOUT
            )

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

        logger.error(
            f"META-AGENT: Erro na fase {phase_name}: {e}",
            exc_info=True
        )
        return {"ok": False, "error": str(e), "result": None}


async def _execute_meta_cycle(shared: Dict[str, Any]) -> bool:
    """
    Executa um único ciclo completo do meta-agente (PLAN -> ACT -> OBSERVE -> REFINE).

    Args:
        shared: Dicionário compartilhado entre fases

    Returns:
        True se o ciclo deve continuar, False se deve parar
    """
    iteration = shared.get("iteration", 0)

    # === FASE: PLAN ===
    async def _phase_plan() -> Dict[str, Any]:
        prompt = (
            "Você é o supervisor. Crie um plano conciso para analisar logs/experiências "
            "recentes e detectar padrões de falha recorrentes."
        )
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent_manager.run_agent(
                question=prompt,
                request=None,
                agent_type=AgentType.META_AGENT,
            )
        )
        plan = result.get("answer") or "Analisar últimas experiências e métricas."
        return {"plan": plan}

    # === FASE: ACT ===
    async def _phase_act() -> Dict[str, Any]:
        query = "experiência do agente"
        loop = asyncio.get_event_loop()

        # Recall de memórias em thread separada
        experiences = await loop.run_in_executor(
            None,
            memory_core.recall,
            query,
            10
        )

        # Análise com agente em thread separada
        result = await loop.run_in_executor(
            None,
            lambda: agent_manager.run_agent(
                question=f"Analise estas experiências e aponte padrões de falha ou ineficiências. {experiences}",
                request=None,
                agent_type=AgentType.META_AGENT,
            )
        )
        return {"analysis": result.get("answer", "")}

    # === FASE: OBSERVE ===
    async def _phase_observe(act_result: Dict[str, Any]) -> Dict[str, Any]:
        analysis = act_result.get("analysis", "")
        has_issue = any(
            k in analysis.lower()
            for k in ["falha", "erro", "ineficiência", "caiu", "timeout"]
        )
        return {"has_issue": has_issue, "analysis": analysis}

    # === FASE: REFINE ===
    async def _phase_refine(obs: Dict[str, Any]) -> Dict[str, Any]:
        if obs.get("has_issue"):
            refinement = "Recomendar tarefa para TOOL_USER investigar e corrigir causa raiz."
        else:
            refinement = "Sem problemas críticos detectados; registrar status saudável."
        return {"refinement": refinement}

    # Executa PLAN
    res_plan = await _run_phase(Phase.PLAN, _phase_plan)
    if res_plan.get("ok"):
        shared["hypothesis"] = res_plan["result"].get("plan")

    # Checkpoint PLAN
    try:
        from app.models.schemas import Experience
        await asyncio.get_event_loop().run_in_executor(
            None,
            memory_core.memorize,
            Experience(
                type="meta_agent_checkpoint",
                content=f"PLAN[{iteration}]: {shared.get('hypothesis')}",
                metadata={"origin": "meta_agent"}
            )
        )
    except Exception as e:
        logger.warning(f"Falha ao salvar checkpoint PLAN: {e}")

    # Executa ACT
    res_act = await _run_phase(Phase.ACT, _phase_act)

    # Executa OBSERVE
    res_obs = await _run_phase(Phase.OBSERVE, _phase_observe, res_act.get("result", {}))
    shared["observations"].append(res_obs.get("result", {}))

    # Executa REFINE
    res_ref = await _run_phase(Phase.REFINE, _phase_refine, res_obs.get("result", {}))
    shared["refinements"].append(res_ref.get("result", {}))

    # Checkpoint pós-ciclo
    try:
        from app.models.schemas import Experience
        await asyncio.get_event_loop().run_in_executor(
            None,
            memory_core.memorize,
            Experience(
                type="meta_agent_checkpoint",
                content=f"OBSERVE/REFINE[{iteration}]",
                metadata={"origin": "meta_agent"}
            )
        )
    except Exception as e:
        logger.warning(f"Falha ao salvar checkpoint pós-ciclo: {e}")

    # Critério de parada antecipado: sistema saudável
    if res_obs.get("result", {}).get("has_issue") is False:
        logger.info("META-AGENT: Sistema saudável detectado. Encerrando ciclo antecipadamente.")
        return False  # Parar iterações

    return True  # Continuar iterações


async def run_meta_agent_cycle():
    """
    Executa o ciclo de vida proativo do Meta-Agente em um loop infinito com máquina de estados explícita.
    Estados: PLAN -> ACT -> OBSERVE -> REFINE (repete) até atingir limites de iteração/tempo.

    Inclui:
    - Circuit Breaker para proteção contra falhas em cascata
    - Backoff progressivo em caso de erros consecutivos
    - Conversão de operações síncronas para assíncronas
    - Timeouts por fase
    """
    logger.info("Ciclo de vida do Meta-Agente iniciado. Primeira verificação em breve.")
    global _interrupt_event

    consecutive_failures = 0

    while True:
        try:
            await asyncio.sleep(settings.META_AGENT_CYCLE_INTERVAL_SECONDS)
            _interrupt_event = asyncio.Event()

            # Verifica se o circuit breaker está aberto
            if _meta_agent_breaker.is_open():
                logger.warning(
                    "META-AGENT: Circuit breaker OPEN. Aguardando recuperação..."
                )
                await asyncio.sleep(60)
                continue

            logger.info("=" * 80)
            logger.info("META-AGENTE: Iniciando ciclo de auto-análise...")

            time_budget = settings.META_AGENT_MAX_SECONDS
            start_cycle = time.perf_counter()
            max_iter = max(1, settings.META_AGENT_MAX_ITERATIONS)

            # Estado compartilhado entre fases
            shared: Dict[str, Any] = {
                "hypothesis": None,
                "actions": [],
                "observations": [],
                "refinements": [],
                "iteration": 0,
            }

            # Executa ciclo protegido pelo Circuit Breaker
            async def protected_cycle():
                iteration = 0
                while iteration < max_iter and (time.perf_counter() - start_cycle) < time_budget:
                    if _interrupt_event.is_set():
                        logger.warning(
                            "META-AGENTE: Interrupção solicitada. Encerrando ciclo atual com segurança."
                        )
                        break

                    iteration += 1
                    shared["iteration"] = iteration
                    logger.info({"event": "meta_agent_iteration_start", "iteration": iteration})

                    # Executa ciclo completo
                    should_continue = await _execute_meta_cycle(shared)

                    if not should_continue:
                        break

                return iteration

            # Chama ciclo protegido
            try:
                iteration = await _meta_agent_breaker.call_async(protected_cycle)
            except CircuitOpenError:
                logger.error("META-AGENT: Circuit breaker aberto após múltiplas falhas.")
                consecutive_failures += 1
                await asyncio.sleep(300)
                continue

            elapsed = time.perf_counter() - start_cycle
            logger.info({
                "event": "meta_agent_cycle_end",
                "iterations": iteration,
                "elapsed_s": round(elapsed, 2)
            })

            # Relatório final
            final_answer = shared.get("refinements", [{}])[-1].get(
                "refinement", "Sem conclusão."
            )
            logger.info(f"META-AGENTE: Conclusão: {final_answer}")
            logger.info("=" * 80)

            # Reset contador de falhas em caso de sucesso
            consecutive_failures = 0

        except asyncio.CancelledError:
            logger.info("META-AGENT: Task cancelada. Encerrando gracefully...")
            break

        except (RuntimeError, ValueError) as e:
            consecutive_failures += 1
            logger.error(
                f"META-AGENT: Erro no ciclo ({consecutive_failures}/{_MAX_CONSECUTIVE_FAILURES}): {e}"
            )

            if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.critical(
                    "META-AGENT: Limite de falhas consecutivas atingido. ENCERRANDO."
                )
                break

            # Backoff progressivo
            backoff = min(600, settings.META_AGENT_CYCLE_INTERVAL_SECONDS * (2 ** consecutive_failures))
            logger.warning(f"META-AGENT: Aguardando {backoff}s antes de retry...")
            await asyncio.sleep(backoff)

        except Exception as e:
            consecutive_failures += 1
            logger.critical(
                f"META-AGENT: Erro CRÍTICO E INESPERADO ({consecutive_failures}/{_MAX_CONSECUTIVE_FAILURES}): {e}",
                exc_info=True
            )

            if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                logger.critical(
                    "META-AGENT: Limite de falhas consecutivas atingido. ENCERRANDO."
                )
                break

            # Espera mais longo para erros inesperados
            await asyncio.sleep(300)
