"""
Sprint 7: Despertar da Proatividade - Ciclo de Auto-Otimização

Sistema de auto-otimização que permite ao Janus tomar iniciativa para se aperfeiçoar
sem intervenção externa. O agente monitora continuamente seu desempenho, identifica
gargalos e aplica melhorias autonomamente.

Funcionalidades:
- Monitoramento contínuo de performance
- Detecção automática de gargalos e problemas
- Planejamento de melhorias
- Execução autônoma de otimizações
- Aprendizado com resultados de otimizações
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

from prometheus_client import Counter, Histogram, Gauge

from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.memory.memory_core import memory_core
from app.core.tools.action_module import action_registry
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

# ==================== MÉTRICAS ====================

_OPTIMIZATION_CYCLES = Counter(
    "self_optimization_cycles_total",
    "Total de ciclos de auto-otimização executados",
    ["outcome"]
)

_OPTIMIZATION_LATENCY = Histogram(
    "self_optimization_latency_seconds",
    "Duração de ciclos de auto-otimização"
)

_IMPROVEMENTS_APPLIED = Counter(
    "self_optimization_improvements_total",
    "Total de melhorias aplicadas",
    ["improvement_type"]
)

_SYSTEM_HEALTH_SCORE = Gauge(
    "self_optimization_health_score",
    "Score de saúde do sistema (0.0-1.0)"
)


# ==================== ENUMS ====================

class IssueType(Enum):
    """Tipos de problemas detectáveis."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    MEMORY_LEAK = "memory_leak"
    TOOL_FAILURE = "tool_failure"
    SLOW_RESPONSE = "slow_response"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class ImprovementType(Enum):
    """Tipos de melhorias aplicáveis."""
    OPTIMIZE_TOOL = "optimize_tool"
    ADD_CACHING = "add_caching"
    INCREASE_TIMEOUT = "increase_timeout"
    REDUCE_COMPLEXITY = "reduce_complexity"
    FIX_CONFIGURATION = "fix_configuration"
    REFACTOR_LOGIC = "refactor_logic"


# ==================== DATACLASSES ====================

@dataclass
class SystemMetrics:
    """Métricas agregadas do sistema."""
    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    memory_usage_mb: float
    active_tools_count: int
    failed_tools: List[str] = field(default_factory=list)
    slow_tools: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DetectedIssue:
    """Problema detectado no sistema."""
    issue_type: IssueType
    severity: float  # 0.0 (baixo) a 1.0 (crítico)
    description: str
    affected_component: str
    evidence: Dict[str, Any]
    detected_at: float = field(default_factory=time.time)


@dataclass
class PlannedImprovement:
    """Melhoria planejada."""
    improvement_type: ImprovementType
    target_component: str
    description: str
    expected_impact: str
    implementation_steps: List[str]
    risk_level: float  # 0.0 (seguro) a 1.0 (arriscado)


@dataclass
class AppliedImprovement:
    """Melhoria aplicada com resultado."""
    improvement: PlannedImprovement
    success: bool
    actual_impact: Optional[str] = None
    error: Optional[str] = None
    applied_at: float = field(default_factory=time.time)


# ==================== MONITOR DE SISTEMA ====================

class SystemMonitor:
    """
    Monitora continuamente a saúde e performance do sistema.

    Coleta métricas de:
    - Tempo de resposta de ferramentas
    - Taxa de erro
    - Uso de recursos
    - Padrões de falha
    """

    def __init__(self):
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = 100  # Últimas 100 medições

    async def collect_metrics(self) -> SystemMetrics:
        """Coleta métricas atuais do sistema."""
        try:
            # Obtém estatísticas do action_registry
            stats = action_registry.get_statistics()

            # Calcula métricas
            tool_usage = stats.get("tool_usage", {})

            # Tempo médio de resposta
            avg_response = 0.0
            if tool_usage:
                avg_response = sum(
                    tool["avg_duration"] for tool in tool_usage.values()
                ) / len(tool_usage)

            # Taxa de erro
            total_calls = stats.get("total_calls", 1)
            successful = stats.get("successful_calls", 0)
            error_rate = 1.0 - (successful / total_calls) if total_calls > 0 else 0.0

            # Ferramentas com problemas
            failed_tools = [
                name for name, usage in tool_usage.items()
                if usage["success"] < usage["total"] * 0.8  # <80% sucesso
            ]

            slow_tools = [
                name for name, usage in tool_usage.items()
                if usage["avg_duration"] > 2.0  # >2s média
            ]

            metrics = SystemMetrics(
                avg_response_time=avg_response,
                error_rate=error_rate,
                tool_success_rate=(successful / total_calls) if total_calls > 0 else 1.0,
                memory_usage_mb=0.0,  # Placeholder
                active_tools_count=stats.get("total_tools_registered", 0),
                failed_tools=failed_tools,
                slow_tools=slow_tools
            )

            # Armazena no histórico
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_history:
                self._metrics_history.pop(0)

            # Atualiza métrica Prometheus
            health_score = self._calculate_health_score(metrics)
            _SYSTEM_HEALTH_SCORE.set(health_score)

            return metrics

        except Exception as e:
            logger.error(f"[SelfOptimization] Erro ao coletar métricas: {e}", exc_info=True)
            return SystemMetrics(
                avg_response_time=0.0,
                error_rate=0.0,
                tool_success_rate=1.0,
                memory_usage_mb=0.0,
                active_tools_count=0
            )

    def _calculate_health_score(self, metrics: SystemMetrics) -> float:
        """
        Calcula score de saúde geral do sistema (0.0-1.0).

        Considera:
        - Taxa de sucesso (40%)
        - Tempo de resposta (30%)
        - Taxa de erro (30%)
        """
        success_score = metrics.tool_success_rate * 0.4

        # Penaliza tempos de resposta altos (>1s é ruim)
        response_score = max(0.0, 1.0 - (metrics.avg_response_time / 2.0)) * 0.3

        # Penaliza taxa de erro
        error_score = (1.0 - metrics.error_rate) * 0.3

        return min(1.0, success_score + response_score + error_score)

    def detect_issues(self) -> List[DetectedIssue]:
        """
        Analisa métricas e detecta problemas.

        Returns:
            Lista de problemas detectados
        """
        issues = []

        if not self._metrics_history:
            return issues

        latest = self._metrics_history[-1]

        # 1. Taxa de erro alta
        if latest.error_rate > 0.2:  # >20% de erros
            issues.append(DetectedIssue(
                issue_type=IssueType.HIGH_ERROR_RATE,
                severity=latest.error_rate,
                description=f"Taxa de erro elevada: {latest.error_rate:.1%}",
                affected_component="system",
                evidence={"error_rate": latest.error_rate}
            ))

        # 2. Ferramentas falhando
        if latest.failed_tools:
            for tool_name in latest.failed_tools:
                issues.append(DetectedIssue(
                    issue_type=IssueType.TOOL_FAILURE,
                    severity=0.7,
                    description=f"Ferramenta '{tool_name}' com alta taxa de falha",
                    affected_component=tool_name,
                    evidence={"tool": tool_name}
                ))

        # 3. Ferramentas lentas
        if latest.slow_tools:
            for tool_name in latest.slow_tools:
                issues.append(DetectedIssue(
                    issue_type=IssueType.SLOW_RESPONSE,
                    severity=0.5,
                    description=f"Ferramenta '{tool_name}' respondendo lentamente",
                    affected_component=tool_name,
                    evidence={"tool": tool_name}
                ))

        # 4. Degradação de performance (comparando com média histórica)
        if len(self._metrics_history) >= 10:
            avg_historical = sum(m.avg_response_time for m in self._metrics_history[:-1]) / (
                    len(self._metrics_history) - 1)

            if latest.avg_response_time > avg_historical * 1.5:  # 50% mais lento
                issues.append(DetectedIssue(
                    issue_type=IssueType.PERFORMANCE_DEGRADATION,
                    severity=0.6,
                    description=f"Performance degradou {((latest.avg_response_time / avg_historical) - 1) * 100:.0f}%",
                    affected_component="system",
                    evidence={
                        "current": latest.avg_response_time,
                        "historical_avg": avg_historical
                    }
                ))

        return issues


# ==================== PLANEJADOR DE MELHORIAS ====================

class ImprovementPlanner:
    """
    Analisa problemas detectados e planeja melhorias específicas.
    """

    async def plan_improvements(
            self,
            issues: List[DetectedIssue],
            metrics: SystemMetrics
    ) -> List[PlannedImprovement]:
        """
        Planeja melhorias baseadas nos problemas detectados.

        Args:
            issues: Problemas detectados
            metrics: Métricas atuais do sistema

        Returns:
            Lista de melhorias planejadas
        """
        improvements = []

        for issue in issues:
            if issue.issue_type == IssueType.TOOL_FAILURE:
                # Ferramenta falhando -> investigar e ajustar configuração
                improvements.append(PlannedImprovement(
                    improvement_type=ImprovementType.FIX_CONFIGURATION,
                    target_component=issue.affected_component,
                    description=f"Ajustar configuração da ferramenta '{issue.affected_component}'",
                    expected_impact="Reduzir taxa de falha em 50%",
                    implementation_steps=[
                        f"Analisar últimas falhas de '{issue.affected_component}'",
                        "Identificar causa raiz (timeout, parâmetros incorretos, etc)",
                        "Ajustar configuração apropriadamente",
                        "Validar com testes"
                    ],
                    risk_level=0.3  # Baixo risco
                ))

            elif issue.issue_type == IssueType.SLOW_RESPONSE:
                # Ferramenta lenta -> adicionar caching ou otimizar
                improvements.append(PlannedImprovement(
                    improvement_type=ImprovementType.ADD_CACHING,
                    target_component=issue.affected_component,
                    description=f"Adicionar caching para '{issue.affected_component}'",
                    expected_impact="Reduzir tempo de resposta em 70%",
                    implementation_steps=[
                        f"Identificar resultados cacheaveis de '{issue.affected_component}'",
                        "Implementar cache LRU com TTL apropriado",
                        "Validar que cache não afeta correção",
                        "Monitorar hit rate"
                    ],
                    risk_level=0.4  # Risco moderado-baixo
                ))

            elif issue.issue_type == IssueType.HIGH_ERROR_RATE:
                # Taxa de erro alta -> refatorar lógica
                improvements.append(PlannedImprovement(
                    improvement_type=ImprovementType.REFACTOR_LOGIC,
                    target_component=issue.affected_component,
                    description="Refatorar lógica de tratamento de erros",
                    expected_impact="Reduzir taxa de erro geral em 30%",
                    implementation_steps=[
                        "Analisar padrões de erro mais comuns",
                        "Implementar retry logic com backoff",
                        "Melhorar validação de inputs",
                        "Adicionar fallbacks apropriados"
                    ],
                    risk_level=0.6  # Risco moderado
                ))

            elif issue.issue_type == IssueType.PERFORMANCE_DEGRADATION:
                # Performance degradada -> otimizar componentes
                improvements.append(PlannedImprovement(
                    improvement_type=ImprovementType.REDUCE_COMPLEXITY,
                    target_component=issue.affected_component,
                    description="Otimizar componentes com performance degradada",
                    expected_impact="Restaurar performance ao nível histórico",
                    implementation_steps=[
                        "Profiling para identificar gargalos",
                        "Otimizar queries/operações mais pesadas",
                        "Reduzir complexidade algorítmica onde possível",
                        "Adicionar índices/otimizações de BD"
                    ],
                    risk_level=0.5  # Risco moderado
                ))

        # Ordena por severidade do problema e risco da solução
        improvements.sort(
            key=lambda imp: self._priority_score(imp, issues),
            reverse=True
        )

        return improvements

    def _priority_score(self, improvement: PlannedImprovement, issues: List[DetectedIssue]) -> float:
        """Calcula score de prioridade (maior = mais prioritário)."""
        # Encontra issue relacionada
        related_issues = [
            iss for iss in issues
            if iss.affected_component == improvement.target_component
        ]

        if not related_issues:
            return 0.0

        max_severity = max(iss.severity for iss in related_issues)

        # Prioridade = severidade - risco
        return max_severity - (improvement.risk_level * 0.3)


# ==================== EXECUTOR DE MELHORIAS ====================

class ImprovementExecutor:
    """
    Executa melhorias planejadas de forma autônoma e segura.
    """

    async def execute_improvement(
            self,
            improvement: PlannedImprovement
    ) -> AppliedImprovement:
        """
        Executa uma melhoria específica.

        Args:
            improvement: Melhoria a ser aplicada

        Returns:
            Resultado da execução
        """
        logger.info(f"[SelfOptimization] Executando melhoria: {improvement.description}")

        try:
            # Usa agente para executar os passos
            prompt = f"""
Você é o sistema de auto-otimização do Janus.

MELHORIA A APLICAR:
Tipo: {improvement.improvement_type.value}
Alvo: {improvement.target_component}
Descrição: {improvement.description}
Impacto Esperado: {improvement.expected_impact}

PASSOS DE IMPLEMENTAÇÃO:
{chr(10).join(f'{i + 1}. {step}' for i, step in enumerate(improvement.implementation_steps))}

TAREFA:
Execute os passos acima de forma sistemática e segura.
Documente cada etapa e o resultado obtido.
Se encontrar problemas, tente soluções alternativas.

IMPORTANTE:
- Seja conservador - não faça mudanças arriscadas
- Documente tudo claramente
- Valide cada mudança antes de prosseguir
"""

            result = await agent_manager.arun_agent(
                question=prompt,
                request=None,
                agent_type=AgentType.TOOL_USER
            )

            success = "answer" in result and "erro" not in result["answer"].lower()

            applied = AppliedImprovement(
                improvement=improvement,
                success=success,
                actual_impact=result.get("answer", "Sem resposta") if success else None,
                error=result.get("answer") if not success else None
            )

            # Registra métrica
            _IMPROVEMENTS_APPLIED.labels(improvement.improvement_type.value).inc()

            # Memoriza resultado
            try:
                memory_core.memorize(Experience(
                    type="self_optimization",
                    content=f"Melhoria aplicada: {improvement.description}\nSucesso: {success}\nResultado: {applied.actual_impact or applied.error}",
                    metadata={
                        "improvement_type": improvement.improvement_type.value,
                        "target": improvement.target_component,
                        "success": success,
                        "origin": "self_optimization"
                    }
                ))
            except Exception as e:
                logger.warning(f"Falha ao memorizar melhoria: {e}")

            return applied

        except Exception as e:
            logger.error(f"[SelfOptimization] Erro ao executar melhoria: {e}", exc_info=True)
            return AppliedImprovement(
                improvement=improvement,
                success=False,
                error=str(e)
            )


# ==================== CICLO DE AUTO-OTIMIZAÇÃO ====================

class SelfOptimizationCycle:
    """
    Ciclo principal de auto-otimização proativa.

    Fluxo:
    1. MONITOR: Coleta métricas do sistema
    2. DETECT: Identifica problemas e gargalos
    3. PLAN: Planeja melhorias específicas
    4. EXECUTE: Aplica melhorias de forma autônoma
    5. LEARN: Avalia resultado e atualiza conhecimento
    """

    def __init__(self):
        self.monitor = SystemMonitor()
        self.planner = ImprovementPlanner()
        self.executor = ImprovementExecutor()
        self._running = False

    async def run_cycle(self) -> Dict[str, Any]:
        """Executa um ciclo completo de auto-otimização."""
        cycle_start = time.perf_counter()

        try:
            logger.info("[SelfOptimization] === Iniciando ciclo de auto-otimização ===")

            # 1. MONITOR
            metrics = await self.monitor.collect_metrics()
            logger.info(
                f"[SelfOptimization] Métricas: health_score={self.monitor._calculate_health_score(metrics):.2f}, "
                f"error_rate={metrics.error_rate:.1%}, avg_response={metrics.avg_response_time:.2f}s")

            # 2. DETECT
            issues = self.monitor.detect_issues()
            logger.info(f"[SelfOptimization] Problemas detectados: {len(issues)}")

            if not issues:
                logger.info("[SelfOptimization] ✓ Sistema saudável - nenhuma melhoria necessária")
                _OPTIMIZATION_CYCLES.labels("success_no_issues").inc()
                return {
                    "success": True,
                    "issues_detected": 0,
                    "improvements_applied": 0,
                    "message": "Sistema saudável"
                }

            # 3. PLAN
            improvements = await self.planner.plan_improvements(issues, metrics)
            logger.info(f"[SelfOptimization] Melhorias planejadas: {len(improvements)}")

            # Limita a 3 melhorias por ciclo para evitar sobrecarga
            improvements = improvements[:3]

            # 4. EXECUTE
            applied_improvements = []
            for improvement in improvements:
                applied = await self.executor.execute_improvement(improvement)
                applied_improvements.append(applied)

                if not applied.success:
                    logger.warning(f"[SelfOptimization] Melhoria falhou: {applied.error}")

            # 5. LEARN
            successful = sum(1 for imp in applied_improvements if imp.success)
            logger.info(f"[SelfOptimization] Melhorias aplicadas: {successful}/{len(applied_improvements)}")

            elapsed = time.perf_counter() - cycle_start
            _OPTIMIZATION_LATENCY.observe(elapsed)
            _OPTIMIZATION_CYCLES.labels("success_with_improvements").inc()

            return {
                "success": True,
                "issues_detected": len(issues),
                "improvements_planned": len(improvements),
                "improvements_applied": successful,
                "elapsed_seconds": round(elapsed, 2)
            }

        except Exception as e:
            logger.error(f"[SelfOptimization] Erro no ciclo: {e}", exc_info=True)
            _OPTIMIZATION_CYCLES.labels("error").inc()
            return {
                "success": False,
                "error": str(e)
            }

    async def run_continuous(self, interval_seconds: int = 300):
        """
        Executa ciclo de auto-otimização continuamente.

        Args:
            interval_seconds: Intervalo entre ciclos (padrão: 5 minutos)
        """
        self._running = True
        logger.info(f"[SelfOptimization] Iniciando execução contínua (intervalo: {interval_seconds}s)")

        while self._running:
            await self.run_cycle()
            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Para execução contínua."""
        self._running = False
        logger.info("[SelfOptimization] Parando execução contínua")


# ==================== INSTÂNCIA GLOBAL ====================

self_optimization_cycle = SelfOptimizationCycle()
