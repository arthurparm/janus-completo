"""
Sprint 5: Sistema Reflexion - Auto-otimização e Aprendizado com Erros (Async)

Implementa o padrão Reflexion de forma assíncrona.
"""

import logging
import time
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable, Awaitable

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.llm.llm_manager import get_llm_client, ModelRole, ModelPriority
from app.services.memory_service import MemoryService
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

# (Métricas omitidas para brevidade)

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
            memory_service: MemoryService,
            evaluator: Optional[Callable[[str, str], Awaitable[Dict[str, Any]]]] = None,
            config: Optional[ReflexionConfig] = None
    ):
        self.task = task.strip()
        self.memory_service = memory_service
        self.evaluator = evaluator or self._specialized_evaluator
        self.config = config or ReflexionConfig.from_settings()
        self._llm = get_llm_client(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.FAST_AND_CHEAP)
        self._start_time = time.perf_counter()
        self._steps: List[ReflexionStep] = []
        self._lessons_learned: List[str] = []

    def _time_remaining(self) -> float:
        elapsed = time.perf_counter() - self._start_time
        return max(0.0, self.config.max_time_seconds - elapsed)

    async def _default_evaluator(self, task: str, result: str) -> Dict[str, Any]:
        prompt = f"""Avalie criticamente o resultado da seguinte tarefa.

TAREFA: {task}
RESULTADO: {result}

Responda APENAS com um objeto JSON válido (sem markdown, sem explicações). Use este formato exato:
{{"score": 0.8, "strengths": ["lista de pontos fortes"], "issues": ["lista de problemas"], "suggestions": ["lista de sugestões"]}}

Seu JSON:"""
        try:
            evaluation_str = await self._llm.asend(prompt, timeout_s=30)
            evaluation_str = evaluation_str.strip()
            if evaluation_str.startswith('```'):
                lines = evaluation_str.split('\n')
                evaluation_str = '\n'.join([l for l in lines if not l.startswith('```')])
            evaluation_str = evaluation_str.strip()

            evaluation = json.loads(evaluation_str)
            if "score" not in evaluation: evaluation["score"] = 0.5
            if "strengths" not in evaluation: evaluation["strengths"] = []
            if "issues" not in evaluation: evaluation["issues"] = []
            if "suggestions" not in evaluation: evaluation["suggestions"] = []
            return evaluation
        except Exception as e:
            logger.error(f"Erro no avaliador: {e}. Response: {evaluation_str if 'evaluation_str' in locals() else 'N/A'}", exc_info=False)
            return {"score": 0.3, "issues": ["Falha na avaliação"], "suggestions": ["Tente novamente"], "strengths": []}

    async def _execute_action(self, iteration: int, previous_reflections: List[str]) -> str:
        context = ""
        if previous_reflections:
            context = "\n\nAPRENDIZADOS DAS TENTATIVAS ANTERIORES:\n" + "\n".join(previous_reflections)
        enhanced_task = f"{self.task}{context}"
        try:
            logger.info(f"[Reflexion] Iteração {iteration}: Executando ação")
            result = await agent_manager.arun_agent(question=enhanced_task, request=None, agent_type=AgentType.TOOL_USER)
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
            reflection = await self._llm.asend(reflection_prompt, timeout_s=30)
            logger.info(f"[Reflexion] Iteração {iteration}: Reflexão gerada")
            return reflection
        except Exception as e:
            logger.error(f"[Reflexion] Erro na reflexão: {e}", exc_info=True)
            return f"Reflexão falhou: {e}."

    async def _specialized_evaluator(self, task: str, observation: str) -> Dict[str, Any]:
        """Seleciona avaliador especializado com base na natureza da tarefa."""
        task_type = self._classify_task_type(task)
        if task_type == "coding":
            return await self._evaluate_coding(observation)
        elif task_type == "research":
            return await self._evaluate_research(observation)
        else:
            return await self._default_evaluator(task, observation)

    def _classify_task_type(self, task: str) -> str:
        t = task.lower()
        coding_keywords = ["code", "python", "bug", "function", "refactor", "test", "error", "compile", "lint"]
        research_keywords = ["research", "web", "search", "explain", "summarize", "document", "compare", "source"]
        if any(k in t for k in coding_keywords):
            return "coding"
        if any(k in t for k in research_keywords):
            return "research"
        return "general"

    async def _evaluate_coding(self, observation: str) -> Dict[str, Any]:
        """Heurística rápida para avaliação de tarefas de código sem depender do LLM."""
        obs = observation.lower()
        has_error = any(x in obs for x in ["traceback", "error", "exception", "failed", "cannot", "undefined"])
        passed_tests = any(x in obs for x in ["tests passed", "all tests", "success", "ok"])
        runtime_ok = any(x in obs for x in ["executed", "ran", "output", "result"]) and not has_error
        score = 0.2
        suggestions: List[str] = []
        if has_error:
            score = 0.2
            suggestions.append("Inspecione logs e mensagens de exceção para root cause.")
            suggestions.append("Adicione testes unitários cobrindo o caso que falhou.")
            suggestions.append("Verifique dependências e importações ausentes.")
        elif passed_tests:
            score = 0.95
            suggestions.append("Consolidar cobertura de testes e revisar performance.")
        elif runtime_ok:
            score = 0.7
            suggestions.append("Validar saída com casos de borda e entradas maiores.")
        else:
            score = 0.5
            suggestions.append("Executar testes básicos e checar tratamentos de erro.")
        return {"score": score, "suggestions": suggestions}

    async def _evaluate_research(self, observation: str) -> Dict[str, Any]:
        """Heurística para avaliação de pesquisas: verifica relevância e fontes."""
        length = len(observation)
        has_links = observation.count("http://") + observation.count("https://")
        mentions_date = any(x in observation.lower() for x in ["202", "today", "recent", "latest"])
        score = 0.3
        suggestions: List[str] = []
        if length > 500:
            score += 0.3
        if has_links >= 2:
            score += 0.3
            suggestions.append("Inclua 2-3 fontes confiáveis com URLs.")
        if mentions_date:
            score += 0.1
        score = min(score, 0.9)
        if score < 0.6:
            suggestions.append("Aumente a profundidade e adicione evidências com citações.")
        else:
            suggestions.append("Resuma pontos-chave e destaque contradições entre fontes.")
        return {"score": score, "suggestions": suggestions}

    async def arun(self) -> Dict[str, Any]:
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

            await self.memory_service.add_experience(
                type="reflexion_iteration",
                content=f"Tarefa: {self.task}\nScore: {score:.2f}\nReflexão: {reflection}",
                metadata={"iteration": iteration, "score": score, "origin": "reflexion_core"}
            )

            if score >= self.config.success_threshold:
                logger.info(f"[Reflexion] ✓ Sucesso atingido na iteração {iteration}!")
                break

        await self._extract_lessons()
        elapsed_time = time.perf_counter() - self._start_time
        return {
            "success": best_score >= self.config.success_threshold,
            "best_result": best_result,
            "best_score": best_score,
            "steps": self._steps,
            "lessons_learned": self._lessons_learned,
            "elapsed_seconds": elapsed_time
        }

    async def _extract_lessons(self):
        if not self._steps: return
        all_reflections = "\n\n".join(
            [f"Iteração {s.iteration} (score: {s.score:.2f}):\n{s.reflection}" for s in self._steps])
        lesson_prompt = f"""Analise estas reflexões e extraia 3-5 LIÇÕES GERAIS e acionáveis em formato de lista.

{all_reflections}

LIÇÕES APRENDIDAS:"""
        try:
            lessons_text = await self._llm.asend(lesson_prompt, timeout_s=30)
            self._lessons_learned = [line.strip("- ") for line in lessons_text.split('\n') if
                                     line.strip().startswith("-")]
            if self._lessons_learned:
                await self.memory_service.add_experience(
                    type="lessons_learned",
                    content=f"Tarefa: {self.task}\nLições: {self._lessons_learned}",
                    metadata={"origin": "reflexion_core"}
                )
                logger.info(f"[Reflexion] {len(self._lessons_learned)} lições aprendidas e memorizadas")
        except Exception as e:
            logger.error(f"[Reflexion] Erro ao extrair lições: {e}", exc_info=True)


async def arun_with_reflexion(task: str, memory_service: MemoryService, evaluator: Optional[Callable[[str, str], Awaitable[Dict[str, Any]]]] = None,
                              config: Optional[ReflexionConfig] = None) -> Dict[str, Any]:
    session = ReflexionSession(task=task, memory_service=memory_service, evaluator=evaluator, config=config)
    return await session.arun()
