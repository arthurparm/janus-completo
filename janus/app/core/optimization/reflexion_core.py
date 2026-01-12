"""
Sprint 5: Sistema Reflexion - Auto-otimização e Aprendizado com Erros (Async)

Implementa o padrão Reflexion de forma assíncrona.
"""

import json
import logging
import time
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.core.agents.agent_manager import AgentType, agent_manager
from app.core.llm.client import get_llm_client
from app.core.llm.router import ModelPriority, ModelRole
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# Métricas (placeholders para evitar erros de importação se não existirem no contexto global)
# Em produção, usaríamos prometheus_client
try:
    from prometheus_client import Counter, Histogram

    REFLEXION_LOOPS = Counter("reflexion_loops_total", "Total de loops de reflexion")
    REFLEXION_SUCCESS = Counter("reflexion_success_total", "Total de sucessos em reflexion")
    REFLEXION_DURATION = Histogram("reflexion_duration_seconds", "Duração do ciclo reflexion")
except ImportError:

    class MockMetric:
        def inc(self):
            pass

        def observe(self, x):
            pass

    REFLEXION_LOOPS = MockMetric()
    REFLEXION_SUCCESS = MockMetric()
    REFLEXION_DURATION = MockMetric()


@dataclass
class ReflexionConfig:
    max_iterations: int = 3
    max_time_seconds: int = 180
    success_threshold: float = 0.8

    @staticmethod
    def from_settings() -> "ReflexionConfig":
        return ReflexionConfig(
            max_iterations=settings.REFLEXION_MAX_ITERATIONS,
            max_time_seconds=settings.REFLEXION_MAX_TIME_SECONDS,
            success_threshold=settings.REFLEXION_SUCCESS_THRESHOLD,
        )


@dataclass
class ReflexionStep:
    iteration: int
    action: str
    observation: str
    reflection: str
    score: float
    improvements: list[str]
    timestamp: float


class ReflexionSession:
    """Executa um ciclo completo de Reflexion para uma tarefa de forma assíncrona."""

    def __init__(
        self,
        task: str,
        memory_service: MemoryService,
        evaluator: Callable[[str, str], Awaitable[dict[str, Any]]] | None = None,
        config: ReflexionConfig | None = None,
    ):
        self.task = task.strip()
        self.memory_service = memory_service
        self.evaluator = evaluator or self._default_evaluator
        self.config = config or ReflexionConfig.from_settings()
        self._llm = None  # Will be initialized in arun
        self._start_time = time.perf_counter()
        self._steps: list[ReflexionStep] = []
        self._lessons_learned: list[str] = []

    def _time_remaining(self) -> float:
        elapsed = time.perf_counter() - self._start_time
        return max(0.0, self.config.max_time_seconds - elapsed)

    async def _ensure_llm(self):
        if self._llm is None:
            self._llm = await get_llm_client(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.FAST_AND_CHEAP
            )

    def _extract_json(self, response: str) -> dict[str, Any]:
        """Extrai JSON da resposta do LLM de forma robusta."""
        text = response.strip()

        # 1. Tentar fazer parse direto
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Tentar extrair de blocos de código ```json ... ```
        code_block_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
        match = code_block_pattern.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Tentar encontrar qualquer objeto JSON {...}
        json_pattern = re.compile(r"(\{.*\})", re.DOTALL)
        match = json_pattern.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Não foi possível extrair JSON válido da resposta: {text[:100]}...")

    async def _default_evaluator(self, task: str, result: str) -> dict[str, Any]:
        await self._ensure_llm()
        prompt = get_formatted_prompt("reflexion_evaluate", task=task, result=result)
        try:
            evaluation_str = await self._llm.send(prompt, timeout_s=30)
            return self._extract_json(evaluation_str)
        except Exception as e:
            logger.error(f"Erro na avaliação padrão: {e}")
            # Fallback seguro
            return {
                "score": 0.5,
                "strengths": [],
                "issues": ["Erro na avaliação ou parsing"],
                "suggestions": [],
            }

    async def _reflect(
        self, task: str, result: str, evaluation: dict[str, Any], history: str = ""
    ) -> tuple[str, list[str]]:
        """Gera reflexão e lições aprendidas."""
        await self._ensure_llm()

        prompt = get_formatted_prompt(
            "reflexion_refine",
            task=task,
            previous_attempt=result,
            feedback=json.dumps(evaluation, ensure_ascii=False),
            history=history,
        )
        try:
            resp = await self._llm.send(prompt, timeout_s=30)
            data = self._extract_json(resp)
            return data.get("reflection", ""), data.get("lessons", [])
        except Exception as e:
            logger.error(f"Erro ao refletir: {e}")
            return "Falha na reflexão (erro de parsing ou LLM)", []

    async def arun(self) -> dict[str, Any]:
        """Executa o loop de Reflexion."""
        await self._ensure_llm()
        REFLEXION_LOOPS.inc()

        current_context = ""
        best_result = None
        best_score = -1.0

        try:
            for iteration in range(self.config.max_iterations):
                if self._time_remaining() <= 0:
                    logger.warning("Tempo limite do Reflexion excedido")
                    break

                logger.info(f"Reflexion Iteração {iteration + 1}/{self.config.max_iterations}")

                # 2. Executar (Gerar Solução)
                execution_prompt = f"""Execute a seguinte tarefa: {self.task}

Contexto/Lições de tentativas anteriores:
{current_context}

Responda com a solução completa."""

                try:
                    # Aqui usamos o LLM diretamente para simplicidade, mas o ideal é um agente
                    action_result = await self._llm.send(execution_prompt)
                except Exception as e:
                    logger.error(f"Erro na execução da tarefa: {e}")
                    action_result = f"Erro de execução: {str(e)}"

                # 3. Avaliar
                evaluation = await self.evaluator(self.task, action_result)
                score = evaluation.get("score", 0.0)

                step = ReflexionStep(
                    iteration=iteration + 1,
                    action=action_result[:200] + "...",
                    observation="Executed",
                    reflection="",
                    score=score,
                    improvements=evaluation.get("suggestions", []),
                    timestamp=time.time(),
                )

                if score > best_score:
                    best_score = score
                    best_result = action_result

                if score >= self.config.success_threshold:
                    logger.info(f"Reflexion atingiu threshold de sucesso: {score}")
                    step.reflection = "Sucesso atingido."
                    self._steps.append(step)
                    REFLEXION_SUCCESS.inc()

                    # Salvar lições antes de retornar
                    if self._lessons_learned:
                        await self._save_lessons()

                    return {
                        "success": True,
                        "result": best_result,
                        "score": best_score,
                        "steps": [s.iteration for s in self._steps],
                        "lessons": self._lessons_learned,
                    }

                # 4. Refletir
                if iteration < self.config.max_iterations - 1:
                    reflection, lessons = await self._reflect(
                        self.task, action_result, evaluation, current_context
                    )
                    step.reflection = reflection
                    self._lessons_learned.extend(lessons)

                    current_context += f"\nTentativa {iteration+1} falhou (Score: {score}).\nReflexão: {reflection}\nLições: {', '.join(lessons)}\n"

                self._steps.append(step)

            # Salvar lições mesmo em caso de falha parcial
            if self._lessons_learned:
                await self._save_lessons()

            return {
                "success": False,
                "result": best_result,
                "score": best_score,
                "steps": [s.iteration for s in self._steps],
                "lessons": self._lessons_learned,
            }

        except Exception as e:
            logger.error(f"Erro fatal no loop de reflexion: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _save_lessons(self):
        """Salva lições aprendidas na memória."""
        try:
            if not self._lessons_learned:
                return

            unique_lessons = list(set(self._lessons_learned))
            content = f"Tarefa: {self.task}\nLições Aprendidas: {json.dumps(unique_lessons, ensure_ascii=False)}"

            await self.memory_service.add_experience(
                type="lessons_learned",
                content=content,
                metadata={"origin": "reflexion_core", "task": self.task, "timestamp": time.time()},
            )
            logger.info(f"[Reflexion] {len(unique_lessons)} lições memorizadas.")
        except Exception as e:
            logger.error(f"[Reflexion] Erro ao salvar lições: {e}")
