"""
Sprint 5: Sistema Reflexion - Auto-otimização e Aprendizado com Erros (Async)

Implementa o padrão Reflexion de forma assíncrona.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable, Awaitable

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.llm.llm_manager import get_llm_client, ModelRole
from app.core.memory.memory_core import memory_core
from app.models.schemas import Experience

logger = logging.getLogger(__name__)


# (Omitted metrics for brevity)

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
            success_threshold=settings.REFLEXION_SUCCESS_THRESHOLD
        )

@dataclass
class ReflexionStep:
    iteration: int
    action: str
    observation: str
    reflection: str
    score: float
    improvements: List[str]
    timestamp: float

class ReflexionSession:
    """Executa um ciclo completo de Reflexion para uma tarefa de forma assíncrona."""

    def __init__(
            self,
            task: str,
            evaluator: Optional[Callable[[str, str], Awaitable[Dict[str, Any]]]] = None,
            config: Optional[ReflexionConfig] = None
    ):
        self.task = task.strip()
        self.evaluator = evaluator or self._default_evaluator
        self.config = config or ReflexionConfig.from_settings()
        self._llm = get_llm_client(role=ModelRole.ORCHESTRATOR)
        self._start_time = time.perf_counter()
        self._steps: List[ReflexionStep] = []
        self._lessons_learned: List[str] = []

    def _time_remaining(self) -> float:
        elapsed = time.perf_counter() - self._start_time
        return max(0.0, self.config.max_time_seconds - elapsed)

    async def _default_evaluator(self, task: str, result: str) -> Dict[str, Any]:
        prompt = f"""Avalie criticamente o resultado da seguinte tarefa:

TAREFA: {task}
RESULTADO: {result}

Forneça uma avaliação estruturada em JSON com as chaves: "score" (float 0.0-1.0), "strengths" (list[str]), "issues" (list[str]), "suggestions" (list[str])."""
        try:
            evaluation_str = await self._llm.send(prompt, timeout_s=30)
            # Basic parsing for JSON-like structures
            evaluation = json.loads(evaluation_str)
            return evaluation
        except Exception as e:
            logger.error(f"Erro no avaliador: {e}", exc_info=True)
            return {"score": 0.3, "issues": ["Falha na avaliação"], "suggestions": ["Tente novamente"]}

    async def _execute_action(self, iteration: int, previous_reflections: List[str]) -> str:
        context = ""
        if previous_reflections:
            context = "\n\nAPRENDIZADOS DAS TENTATIVAS ANTERIORES:\n" + "\n".join(previous_reflections)
        enhanced_task = f"{self.task}{context}"
        try:
            logger.info(f"[Reflexion] Iteração {iteration}: Executando ação")
            result = await agent_manager.arun_agent(question=enhanced_task, request=None,
                                                    agent_type=AgentType.TOOL_USER)
            return result.get("answer", "Sem resposta do agente.") if result else "Agente não retornou resultado."
        except Exception as e:
            logger.error(f"[Reflexion] Erro na execução: {e}", exc_info=True)
            return f"ERRO: {e}"

    async def _reflect(self, iteration: int, action: str, observation: str, evaluation: Dict[str, Any]) -> str:
        reflection_prompt = f"""Você é um agente reflexivo. Analise a tentativa:

ITERAÇÃO: {iteration}
TAREFA: {self.task}
RESULTADO: {observation}
AVALIAÇÃO: {evaluation}

REFLEXÃO: O que devo fazer diferente na próxima tentativa para melhorar o score? Seja específico e acionável."""
        try:
            reflection = await self._llm.send(reflection_prompt, timeout_s=30)
            logger.info(f"[Reflexion] Iteração {iteration}: Reflexão gerada")
            return reflection
        except Exception as e:
            logger.error(f"[Reflexion] Erro na reflexão: {e}", exc_info=True)
            return f"Reflexão falhou: {e}."

    async def arun(self) -> Dict[str, Any]:
        """Executa o ciclo completo de Reflexion de forma assíncrona."""
        iteration = 0
        best_result = None
        best_score = 0.0
        reflections: List[str] = []
        logger.info(f"[Reflexion] Iniciando ciclo para tarefa: {self.task[:100]}...")

        while iteration < self.config.max_iterations and self._time_remaining() > 10:
            iteration += 1
            logger.info(f"[Reflexion] === ITERAÇÃO {iteration}/{self.config.max_iterations} ===")

            action_result = await self._execute_action(iteration, reflections)
            evaluation = await self.evaluator(self.task, action_result)
            score = evaluation.get("score", 0.0)
            logger.info(f"[Reflexion] Score obtido: {score:.2f}")

            reflection = await self._reflect(iteration, self.task, action_result, evaluation)
            reflections.append(reflection)

            self._steps.append(
                ReflexionStep(iteration, self.task, action_result, reflection, score, evaluation.get("suggestions", []),
                              time.perf_counter()))

            if score > best_score:
                best_score = score
                best_result = action_result

            await memory_core.amemorize(Experience(type="reflexion_iteration",
                                                   content=f"Tarefa: {self.task}\nScore: {score:.2f}\nReflexão: {reflection}",
                                                   metadata={"iteration": iteration, "score": score,
                                                             "origin": "reflexion_core"}))

            if score >= self.config.success_threshold:
                logger.info(f"[Reflexion] ✓ Sucesso atingido na iteração {iteration}!")
                break

        await self._extract_lessons()
        # (Metrics and final logging omitted for brevity)
        return {"success": best_score >= self.config.success_threshold, "best_result": best_result,
                "best_score": best_score, "steps": self._steps, "lessons_learned": self._lessons_learned}

    async def _extract_lessons(self):
        if not self._steps: return
        all_reflections = "\n\n".join(
            [f"Iteração {s.iteration} (score: {s.score:.2f}):\n{s.reflection}" for s in self._steps])
        lesson_prompt = f"Analise estas reflexões e extraia 3-5 LIÇÕES GERAIS e acionáveis em formato de lista.

{all_reflections}

LIÇÕES
APRENDIDAS: "
        try:
            lessons_text = await self._llm.send(lesson_prompt, timeout_s=30)
            self._lessons_learned = [line.strip("- ") for line in lessons_text.split('\n') if
                                     line.strip().startswith("-")]
            if self._lessons_learned:
                await memory_core.amemorize(
                    Experience(type="lessons_learned", content=f"Tarefa: {self.task}\nLições: {self._lessons_learned}",
                               metadata={"origin": "reflexion_core"}))
                logger.info(f"[Reflexion] {len(self._lessons_learned)} lições aprendidas e memorizadas")
        except Exception as e:
            logger.error(f"[Reflexion] Erro ao extrair lições: {e}", exc_info=True)


async def arun_with_reflexion(task: str, evaluator: Optional[Callable[[str, str], Awaitable[Dict[str, Any]]]] = None,
                              config: Optional[ReflexionConfig] = None) -> Dict[str, Any]:
    """API assíncrona para executar uma tarefa com o padrão Reflexion."""
    session = ReflexionSession(task=task, evaluator=evaluator, config=config)
    return await session.arun()
