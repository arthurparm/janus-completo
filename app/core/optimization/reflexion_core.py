"""
Sprint 5: Sistema Reflexion - Auto-otimização e Aprendizado com Erros

Implementa o padrão Reflexion onde o agente:
1. Executa uma tarefa
2. Avalia criticamente o resultado
3. Identifica falhas e pontos de melhoria
4. Tenta novamente com insights adquiridos
5. Armazena lições aprendidas na memória
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable

from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.llm.llm_manager import get_llm_client, ModelRole
from app.core.memory.memory_core import memory_core
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

# Métricas
_REFLEXION_CYCLES = Counter(
    "reflexion_cycles_total",
    "Total de ciclos Reflexion executados",
    ["outcome"]
)
_REFLEXION_ITERATIONS = Histogram(
    "reflexion_iterations",
    "Número de iterações por ciclo Reflexion"
)
_REFLEXION_LATENCY = Histogram(
    "reflexion_latency_seconds",
    "Tempo total de execução de ciclo Reflexion"
)


@dataclass
class ReflexionConfig:
    """Configurações do ciclo Reflexion."""
    max_iterations: int = 3
    max_time_seconds: int = 180
    success_threshold: float = 0.8  # Score mínimo para considerar sucesso

    @staticmethod
    def from_settings() -> "ReflexionConfig":
        return ReflexionConfig(
            max_iterations=getattr(settings, "REFLEXION_MAX_ITERATIONS", 3),
            max_time_seconds=getattr(settings, "REFLEXION_MAX_TIME_SECONDS", 180),
            success_threshold=getattr(settings, "REFLEXION_SUCCESS_THRESHOLD", 0.8)
        )


@dataclass
class ReflexionStep:
    """Representa uma iteração do ciclo Reflexion."""
    iteration: int
    action: str
    observation: str
    reflection: str
    score: float
    improvements: List[str]
    timestamp: float


class ReflexionSession:
    """
    Executa um ciclo completo de Reflexion para uma tarefa.

    Fluxo:
    1. ACT: Executa a tarefa usando o agente
    2. EVALUATE: Avalia criticamente o resultado
    3. REFLECT: Identifica o que deu errado e como melhorar
    4. RETRY: Tenta novamente com os insights adquiridos
    5. LEARN: Armazena lições aprendidas na memória
    """

    def __init__(
            self,
            task: str,
            evaluator: Optional[Callable[[str, str], Dict[str, Any]]] = None,
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
        """Retorna tempo restante em segundos."""
        elapsed = time.perf_counter() - self._start_time
        return max(0.0, self.config.max_time_seconds - elapsed)

    def _default_evaluator(self, task: str, result: str) -> Dict[str, Any]:
        """
        Avaliador padrão usando LLM para criticar o resultado.

        Returns:
            Dict com 'score' (0.0-1.0), 'feedback' e 'issues'
        """
        prompt = f"""
Avalie criticamente o resultado da seguinte tarefa:

TAREFA: {task}

RESULTADO: {result}

Forneça uma avaliação estruturada:
1. Score (0.0 a 1.0): Quão bem a tarefa foi executada?
2. Pontos fortes: O que funcionou bem?
3. Problemas identificados: O que deu errado ou pode melhorar?
4. Sugestões específicas: Como melhorar na próxima tentativa?

Formato da resposta:
SCORE: <0.0-1.0>
FORTES: <lista>
PROBLEMAS: <lista>
SUGESTÕES: <lista>
"""

        try:
            evaluation = self._llm.send(prompt, timeout_s=30)

            # Parse da resposta
            score = 0.5  # default
            issues = []
            suggestions = []

            for line in evaluation.split('\n'):
                line = line.strip()
                if line.startswith('SCORE:'):
                    try:
                        score = float(line.split(':', 1)[1].strip())
                        score = max(0.0, min(1.0, score))
                    except:
                        pass
                elif line.startswith('PROBLEMAS:'):
                    issues.append(line.split(':', 1)[1].strip())
                elif line.startswith('SUGESTÕES:') or line.startswith('SUGESTOES:'):
                    suggestions.append(line.split(':', 1)[1].strip())
                elif line.startswith('-') and len(line) > 2:
                    # Assume que é um item de lista
                    if 'problema' in evaluation.lower()[:evaluation.lower().index(line)]:
                        issues.append(line[1:].strip())
                    else:
                        suggestions.append(line[1:].strip())

            return {
                "score": score,
                "feedback": evaluation,
                "issues": issues,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.error(f"Erro no avaliador: {e}", exc_info=True)
            return {
                "score": 0.3,
                "feedback": f"Erro na avaliação: {e}",
                "issues": ["Falha na avaliação"],
                "suggestions": ["Tente novamente com mais contexto"]
            }

    def _execute_action(self, iteration: int, previous_reflections: List[str]) -> str:
        """
        Executa a tarefa, incorporando reflexões anteriores.
        """
        # Monta contexto com reflexões prévias
        context = ""
        if previous_reflections:
            context = "\n\nAPRENDIZADOS DAS TENTATIVAS ANTERIORES:\n"
            for i, reflection in enumerate(previous_reflections, 1):
                context += f"\nTentativa {i}:\n{reflection}\n"

        enhanced_task = f"{self.task}{context}"

        try:
            logger.info(f"[Reflexion] Iteração {iteration}: Executando ação")
            result = agent_manager.run_agent(
                question=enhanced_task,
                request=None,
                agent_type=AgentType.TOOL_USER
            )
            return result.get("answer", "Sem resposta do agente.")

        except Exception as e:
            logger.error(f"[Reflexion] Erro na execução: {e}", exc_info=True)
            return f"ERRO: {e}"

    def _reflect(self, iteration: int, action: str, observation: str, evaluation: Dict[str, Any]) -> str:
        """
        Gera reflexão sobre o que funcionou/falhou e como melhorar.
        """
        score = evaluation.get("score", 0.0)
        issues = evaluation.get("issues", [])
        suggestions = evaluation.get("suggestions", [])

        reflection_prompt = f"""
Você é um agente reflexivo. Analise profundamente esta tentativa:

ITERAÇÃO: {iteration}
TAREFA ORIGINAL: {self.task}
AÇÃO EXECUTADA: {action}
RESULTADO OBTIDO: {observation}
SCORE: {score:.2f}/1.0

PROBLEMAS IDENTIFICADOS:
{chr(10).join(f'- {issue}' for issue in issues) if issues else '- Nenhum problema específico identificado'}

SUGESTÕES RECEBIDAS:
{chr(10).join(f'- {sug}' for sug in suggestions) if suggestions else '- Sem sugestões'}

REFLEXÃO SOLICITADA:
1. Por que obtive este resultado?
2. Quais foram minhas premissas incorretas?
3. O que especificamente devo fazer diferente na próxima tentativa?
4. Qual lição posso extrair para tarefas futuras similares?

Seja específico e acionável nas suas conclusões.
"""

        try:
            reflection = self._llm.send(reflection_prompt, timeout_s=30)
            logger.info(f"[Reflexion] Iteração {iteration}: Reflexão gerada")
            return reflection

        except Exception as e:
            logger.error(f"[Reflexion] Erro na reflexão: {e}", exc_info=True)
            return f"Reflexão falhou: {e}. Sugestões: {', '.join(suggestions)}"

    def run(self) -> Dict[str, Any]:
        """
        Executa o ciclo completo de Reflexion.

        Returns:
            Dict com resultado final, histórico de tentativas e lições aprendidas
        """
        iteration = 0
        best_result = None
        best_score = 0.0
        reflections: List[str] = []

        logger.info(f"[Reflexion] Iniciando ciclo para tarefa: {self.task[:100]}...")

        while iteration < self.config.max_iterations and self._time_remaining() > 10:
            iteration += 1
            iter_start = time.perf_counter()

            logger.info(f"[Reflexion] === ITERAÇÃO {iteration}/{self.config.max_iterations} ===")

            # 1. ACT: Executa ação
            action_result = self._execute_action(iteration, reflections)

            # 2. EVALUATE: Avalia resultado
            evaluation = self.evaluator(self.task, action_result)
            score = evaluation.get("score", 0.0)

            logger.info(f"[Reflexion] Score obtido: {score:.2f}")

            # 3. REFLECT: Gera reflexão
            reflection = self._reflect(iteration, self.task, action_result, evaluation)
            reflections.append(reflection)

            # 4. RECORD: Registra passo
            step = ReflexionStep(
                iteration=iteration,
                action=self.task,
                observation=action_result,
                reflection=reflection,
                score=score,
                improvements=evaluation.get("suggestions", []),
                timestamp=time.perf_counter()
            )
            self._steps.append(step)

            # Atualiza melhor resultado
            if score > best_score:
                best_score = score
                best_result = action_result

            # Memoriza experiência
            try:
                memory_core.memorize(Experience(
                    type="reflexion_iteration",
                    content=f"Tarefa: {self.task}\nScore: {score:.2f}\nReflexão: {reflection}",
                    metadata={
                        "iteration": iteration,
                        "score": score,
                        "origin": "reflexion_core"
                    }
                ))
            except Exception as e:
                logger.warning(f"Falha ao memorizar reflexão: {e}")

            # 5. CHECK: Verifica se atingiu sucesso
            if score >= self.config.success_threshold:
                logger.info(f"[Reflexion] ✓ Sucesso atingido na iteração {iteration}!")
                _REFLEXION_CYCLES.labels("success").inc()
                break

            elapsed_iter = time.perf_counter() - iter_start
            logger.info(f"[Reflexion] Iteração {iteration} concluída em {elapsed_iter:.2f}s")

        # 6. LEARN: Extrai lições aprendidas
        self._extract_lessons()

        # Métricas finais
        total_time = time.perf_counter() - self._start_time
        _REFLEXION_ITERATIONS.observe(iteration)
        _REFLEXION_LATENCY.observe(total_time)

        if best_score < self.config.success_threshold:
            _REFLEXION_CYCLES.labels("partial_success").inc()

        logger.info(f"[Reflexion] Ciclo concluído: {iteration} iterações, melhor score: {best_score:.2f}")

        return {
            "success": best_score >= self.config.success_threshold,
            "best_result": best_result,
            "best_score": best_score,
            "iterations": iteration,
            "steps": [
                {
                    "iteration": s.iteration,
                    "score": s.score,
                    "reflection": s.reflection,
                    "improvements": s.improvements
                }
                for s in self._steps
            ],
            "lessons_learned": self._lessons_learned,
            "elapsed_seconds": round(total_time, 2)
        }

    def _extract_lessons(self):
        """
        Analisa todas as reflexões e extrai lições gerais aprendidas.
        """
        if not self._steps:
            return

        all_reflections = "\n\n".join(
            f"Iteração {s.iteration} (score: {s.score:.2f}):\n{s.reflection}"
            for s in self._steps
        )

        lesson_prompt = f"""
Analise todas estas reflexões de tentativas de resolver uma tarefa:

{all_reflections}

Extraia 3-5 LIÇÕES GERAIS que podem ser aplicadas em tarefas futuras similares.
Seja conciso e específico. Formate como lista numerada.

LIÇÕES APRENDIDAS:
"""

        try:
            lessons_text = self._llm.send(lesson_prompt, timeout_s=30)

            # Parse lições
            for line in lessons_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    lesson = line.lstrip('0123456789.-) ').strip()
                    if lesson:
                        self._lessons_learned.append(lesson)

            # Memoriza lições
            if self._lessons_learned:
                memory_core.memorize(Experience(
                    type="lessons_learned",
                    content=f"Tarefa: {self.task}\n\nLições:\n" + "\n".join(
                        f"- {lesson}" for lesson in self._lessons_learned
                    ),
                    metadata={
                        "origin": "reflexion_core",
                        "iterations": len(self._steps),
                        "final_score": self._steps[-1].score if self._steps else 0.0
                    }
                ))

                logger.info(f"[Reflexion] {len(self._lessons_learned)} lições aprendidas extraídas e memorizadas")

        except Exception as e:
            logger.error(f"[Reflexion] Erro ao extrair lições: {e}", exc_info=True)


def run_with_reflexion(
        task: str,
        evaluator: Optional[Callable[[str, str], Dict[str, Any]]] = None,
        config: Optional[ReflexionConfig] = None
) -> Dict[str, Any]:
    """
    API simplificada para executar uma tarefa com o padrão Reflexion.

    Args:
        task: Tarefa a ser executada
        evaluator: Função customizada de avaliação (opcional)
        config: Configurações do Reflexion (opcional)

    Returns:
        Resultado da execução com reflexões e lições aprendidas
    """
    session = ReflexionSession(task=task, evaluator=evaluator, config=config)
    return session.run()
