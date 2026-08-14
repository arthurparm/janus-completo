"""
Sprint 7: Despertar da Proatividade - Ciclo de Auto-Otimização

Sistema de auto-otimização que permite ao Janus monitorar seu desempenho, identificar
gargalos e planejar melhorias. A execução automática permanece indisponível até existir
um adaptador com autorização, efeitos auditáveis e verificação pós-condição.

Funcionalidades:
- Monitoramento contínuo de performance
- Detecção automática de gargalos e problemas
- Planejamento de melhorias
- Planejamento de otimizações para revisão
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram

from app.core.tools.action_module import action_registry

logger = structlog.get_logger(__name__)


class OptimizationMetricsUnavailableError(RuntimeError):
    """Não há telemetria suficiente para calcular métricas de otimização."""

# ==================== MÉTRICAS ====================

_OPTIMIZATION_CYCLES = Counter(
    "self_optimization_cycles_total", "Total de ciclos de auto-otimização executados", ["outcome"]
)

_OPTIMIZATION_LATENCY = Histogram(
    "self_optimization_latency_seconds", "Duração de ciclos de auto-otimização"
)

_SYSTEM_HEALTH_SCORE = Gauge(
    "self_optimization_health_score", "Score de saúde do sistema (0.0-1.0)"
)


# ==================== ENUMS ====================


class IssueType(str, Enum):
    """Tipos de problemas detectáveis."""

    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    MEMORY_LEAK = "memory_leak"
    TOOL_FAILURE = "tool_failure"
    SLOW_RESPONSE = "slow_response"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class IssueSeverity(str, Enum):
    """Faixas públicas de severidade usadas para filtrar problemas."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ImprovementType(Enum):
    """Tipos de melhorias aplicáveis."""

    OPTIMIZE_TOOL = "optimize_tool"
    ADD_CACHING = "add_caching"
    INCREASE_TIMEOUT = "increase_timeout"
    REDUCE_COMPLEXITY = "reduce_complexity"
    FIX_CONFIGURATION = "fix_configuration"
    REFACTOR_LOGIC = "refactor_logic"
    INVESTIGATE = "investigate"


# ==================== DATACLASSES ====================


@dataclass
class SystemMetrics:
    """Métricas agregadas do sistema."""

    avg_response_time: float
    error_rate: float
    tool_success_rate: float
    memory_usage_mb: float | None
    active_tools_count: int
    failed_tools: list[str] = field(default_factory=list)
    slow_tools: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DetectedIssue:
    """Problema detectado no sistema."""

    issue_type: IssueType
    severity: float  # 0.0 (baixo) a 1.0 (crítico)
    description: str
    affected_component: str
    evidence: dict[str, Any]
    detected_at: float = field(default_factory=time.time)


@dataclass
class PlannedImprovement:
    """Melhoria planejada."""

    improvement_type: ImprovementType
    target_component: str
    description: str
    hypothesis: str
    evidence: dict[str, Any]
    success_criteria: list[str]
    implementation_steps: list[str]
    risk_level: float  # 0.0 (seguro) a 1.0 (arriscado)
    priority_score: float = 0.0
    requires_human_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serializa o plano sem expor enums ou objetos internos."""
        return {
            "improvement_type": self.improvement_type.value,
            "target_component": self.target_component,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "evidence": self.evidence,
            "success_criteria": self.success_criteria,
            "implementation_steps": self.implementation_steps,
            "risk_level": self.risk_level,
            "priority_score": self.priority_score,
            "requires_human_approval": self.requires_human_approval,
        }


@dataclass
class AppliedImprovement:
    """Melhoria aplicada com resultado."""

    improvement: PlannedImprovement
    success: bool
    actual_impact: str | None = None
    error: str | None = None
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

    def __init__(self) -> None:
        self._metrics_history: list[SystemMetrics] = []
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
                avg_response = sum(tool["avg_duration"] for tool in tool_usage.values()) / len(
                    tool_usage
                )

            # Taxa de erro
            total_calls = int(stats.get("total_calls", 0))
            successful = stats.get("successful_calls", 0)
            if total_calls <= 0:
                raise OptimizationMetricsUnavailableError(
                    "Nenhuma chamada de ferramenta foi observada; saúde indisponível."
                )
            error_rate = 1.0 - (successful / total_calls)

            # Ferramentas com problemas
            failed_tools = [
                name
                for name, usage in tool_usage.items()
                if usage["success"] < usage["total"] * 0.8  # <80% sucesso
            ]

            slow_tools = [
                name
                for name, usage in tool_usage.items()
                if usage["avg_duration"] > 2.0  # >2s média
            ]

            # Uso de memória do processo (MB)
            memory_usage_mb: float | None = None
            try:
                import os

                import psutil

                process = psutil.Process(os.getpid())
                memory_usage_mb = round(process.memory_info().rss / (1024**2), 2)
            except Exception:
                logger.warning(
                    "[SelfOptimization] Uso de memória indisponível; "
                    "a amostra será registrada sem essa medida"
                )

            metrics = SystemMetrics(
                avg_response_time=avg_response,
                error_rate=error_rate,
                tool_success_rate=successful / total_calls,
                memory_usage_mb=memory_usage_mb,
                active_tools_count=stats.get("total_tools_registered", 0),
                failed_tools=failed_tools,
                slow_tools=slow_tools,
            )

            # Armazena no histórico
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > self._max_history:
                self._metrics_history.pop(0)

            # Atualiza métrica Prometheus
            health_score = self._calculate_health_score(metrics)
            _SYSTEM_HEALTH_SCORE.set(health_score)

            return metrics

        except OptimizationMetricsUnavailableError:
            raise
        except Exception as e:
            logger.error("log_error", message=f"[SelfOptimization] Erro ao coletar métricas: {e}", exc_info=True)
            raise RuntimeError("Falha ao coletar métricas de otimização.") from e

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

    def detect_issues(self) -> list[DetectedIssue]:
        """
        Analisa métricas e detecta problemas.

        Returns:
            Lista de problemas detectados
        """
        issues: list[DetectedIssue] = []

        if not self._metrics_history:
            return issues

        latest = self._metrics_history[-1]

        # 1. Taxa de erro alta
        if latest.error_rate > 0.2:  # >20% de erros
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.HIGH_ERROR_RATE,
                    severity=latest.error_rate,
                    description=f"Taxa de erro elevada: {latest.error_rate:.1%}",
                    affected_component="system",
                    evidence={"error_rate": latest.error_rate},
                )
            )

        # 2. Ferramentas falhando
        if latest.failed_tools:
            for tool_name in latest.failed_tools:
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.TOOL_FAILURE,
                        severity=0.7,
                        description=f"Ferramenta '{tool_name}' com alta taxa de falha",
                        affected_component=tool_name,
                        evidence={"tool": tool_name},
                    )
                )

        # 3. Ferramentas lentas
        if latest.slow_tools:
            for tool_name in latest.slow_tools:
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.SLOW_RESPONSE,
                        severity=0.5,
                        description=f"Ferramenta '{tool_name}' respondendo lentamente",
                        affected_component=tool_name,
                        evidence={"tool": tool_name},
                    )
                )

        # 4. Degradação de performance (comparando com média histórica)
        if len(self._metrics_history) >= 10:
            avg_historical = sum(m.avg_response_time for m in self._metrics_history[:-1]) / (
                len(self._metrics_history) - 1
            )

            if latest.avg_response_time > avg_historical * 1.5:  # 50% mais lento
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.PERFORMANCE_DEGRADATION,
                        severity=0.6,
                        description=f"Performance degradou {((latest.avg_response_time / avg_historical) - 1) * 100:.0f}%",
                        affected_component="system",
                        evidence={
                            "current": latest.avg_response_time,
                            "historical_avg": avg_historical,
                        },
                    )
                )

        # 5. Possível vazamento de memória (tendência ascendente)
        if len(self._metrics_history) >= 5 and all(
            m.memory_usage_mb is not None for m in self._metrics_history[-5:]
        ):
            window = [
                m.memory_usage_mb
                for m in self._metrics_history[-5:]
                if m.memory_usage_mb is not None
            ]
            diffs = [window[i + 1] - window[i] for i in range(len(window) - 1)]
            total_increase = window[-1] - window[0]

            if all(d > 0 for d in diffs) and total_increase >= 100.0:  # aumento >= 100MB
                severity = min(1.0, total_increase / 500.0)
                issues.append(
                    DetectedIssue(
                        issue_type=IssueType.MEMORY_LEAK,
                        severity=severity,
                        description=f"Tendência de aumento de memória ({total_increase:.0f}MB nas últimas medições)",
                        affected_component="system",
                        evidence={"last_5_memory_mb": window, "total_increase_mb": total_increase},
                    )
                )

        # 6. Exaustão de recursos (memória do sistema muito alta ou processo grande)
        proc_mem_mb: float | None
        sys_mem_percent: float | None
        sys_mem_total_mb: float | None
        try:
            import os

            import psutil

            vm = psutil.virtual_memory()
            process = psutil.Process(os.getpid())
            proc_mem_mb = round(process.memory_info().rss / (1024**2), 2)
            sys_mem_percent = vm.percent
            sys_mem_total_mb = round(vm.total / (1024**2), 2)
        except Exception:
            proc_mem_mb = latest.memory_usage_mb
            sys_mem_percent = None
            sys_mem_total_mb = None

        resource_exhausted = False
        description = None
        severity = 0.0
        if sys_mem_percent is not None and sys_mem_percent >= 85.0:
            resource_exhausted = True
            description = f"Uso de memória do sistema elevado ({sys_mem_percent:.0f}%)"
            severity = min(1.0, sys_mem_percent / 100.0)
        elif proc_mem_mb is not None and proc_mem_mb >= 2048.0:
            resource_exhausted = True
            description = f"Uso de memória do processo elevado ({proc_mem_mb:.0f}MB)"
            severity = 0.8

        if resource_exhausted:
            issues.append(
                DetectedIssue(
                    issue_type=IssueType.RESOURCE_EXHAUSTION,
                    severity=severity,
                    description=description or "Exaustão de recursos detectada",
                    affected_component="system",
                    evidence={
                        "process_memory_mb": proc_mem_mb,
                        "system_memory_percent": sys_mem_percent,
                        "system_memory_total_mb": sys_mem_total_mb,
                    },
                )
            )

        return issues


# ==================== PLANEJADOR DE MELHORIAS ====================


class ImprovementPlanner:
    """
    Analisa problemas detectados e planeja melhorias específicas.
    """

    async def plan_improvements(
        self, issues: list[DetectedIssue], metrics: SystemMetrics
    ) -> list[PlannedImprovement]:
        """
        Planeja melhorias baseadas nos problemas detectados.

        Args:
            issues: Problemas detectados
            metrics: Métricas atuais do sistema

        Returns:
            Lista de melhorias planejadas
        """
        improvements: list[PlannedImprovement] = []

        for issue in issues:
            evidence = {
                **issue.evidence,
                "issue_type": issue.issue_type.value,
                "issue_severity": issue.severity,
                "system_error_rate": metrics.error_rate,
                "system_avg_response_time": metrics.avg_response_time,
                "system_memory_usage_mb": metrics.memory_usage_mb,
            }
            if issue.issue_type == IssueType.TOOL_FAILURE:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component=issue.affected_component,
                        description=f"Investigar falhas da ferramenta '{issue.affected_component}'",
                        hypothesis=(
                            "Configuração, timeout ou argumentos podem explicar as falhas; "
                            "a causa ainda não foi confirmada."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Identificar causa raiz reproduzível com erro e entrada redigidos.",
                            "Validar a correção em novas chamadas sem elevar a taxa de erro do sistema.",
                        ],
                        implementation_steps=[
                            f"Analisar últimas falhas de '{issue.affected_component}'",
                            "Identificar causa raiz (timeout, parâmetros incorretos, etc)",
                            "Propor correção sujeita a revisão humana",
                            "Validar com testes e telemetria posterior",
                        ],
                        risk_level=0.3,
                    )
                )

            elif issue.issue_type == IssueType.SLOW_RESPONSE:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component=issue.affected_component,
                        description=f"Investigar latência de '{issue.affected_component}'",
                        hypothesis=(
                            "Trabalho repetido, dependência lenta ou falta de cache podem explicar "
                            "a latência; nenhuma causa foi confirmada."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Obter perfil reproduzível com baseline e principal gargalo.",
                            "Demonstrar redução de latência em amostra posterior sem alterar resultados.",
                        ],
                        implementation_steps=[
                            f"Medir operações internas de '{issue.affected_component}'",
                            "Classificar gargalo antes de escolher cache ou refatoração",
                            "Propor mudança sujeita a revisão humana",
                            "Comparar baseline e amostra posterior",
                        ],
                        risk_level=0.4,
                    )
                )

            elif issue.issue_type == IssueType.HIGH_ERROR_RATE:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component="system",
                        description="Investigar aumento da taxa de erro",
                        hypothesis=(
                            "Uma ou mais classes de falha recorrente podem explicar a taxa observada."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Identificar classes de erro responsáveis e sua frequência.",
                            "Comprovar redução da taxa de erro em nova janela com volume informado.",
                        ],
                        implementation_steps=[
                            "Analisar padrões de erro mais comuns",
                            "Separar causas transitórias de defeitos determinísticos",
                            "Propor correção específica sujeita a revisão humana",
                            "Comparar a taxa de erro antes e depois",
                        ],
                        risk_level=0.6,
                    )
                )

            elif issue.issue_type == IssueType.PERFORMANCE_DEGRADATION:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component=issue.affected_component,
                        description="Investigar degradação de performance",
                        hypothesis=(
                            "Uma regressão recente pode explicar a diferença entre a amostra atual "
                            "e o baseline histórico."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Localizar o gargalo com perfil e baseline reproduzíveis.",
                            "Demonstrar que a amostra posterior não excede o baseline histórico validado.",
                        ],
                        implementation_steps=[
                            "Profiling para identificar gargalos",
                            "Relacionar a regressão a mudança ou dependência específica",
                            "Propor correção sujeita a revisão humana",
                            "Executar comparação antes/depois",
                        ],
                        risk_level=0.5,
                    )
                )

            elif issue.issue_type == IssueType.MEMORY_LEAK:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component="system",
                        description="Investigar crescimento persistente de memória",
                        hypothesis=(
                            "Retenção não intencional pode explicar o crescimento observado; "
                            "cinco amostras ascendentes ainda não provam vazamento."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Reproduzir crescimento com carga e horizonte documentados.",
                            "Confirmar estabilização da memória após a correção proposta.",
                        ],
                        implementation_steps=[
                            "Coletar perfil de alocações em ambiente controlado",
                            "Identificar objetos ou caches responsáveis pela retenção",
                            "Propor correção sujeita a revisão humana",
                            "Repetir a carga e comparar a curva de memória",
                        ],
                        risk_level=0.5,
                    )
                )

            elif issue.issue_type == IssueType.RESOURCE_EXHAUSTION:
                improvements.append(
                    PlannedImprovement(
                        improvement_type=ImprovementType.INVESTIGATE,
                        target_component="system",
                        description="Investigar exaustão de recursos",
                        hypothesis=(
                            "Carga, retenção ou dimensionamento podem explicar o limite observado."
                        ),
                        evidence=evidence,
                        success_criteria=[
                            "Identificar recurso, consumidor e carga associados ao limite.",
                            "Validar margem operacional posterior sem relaxar limites de segurança.",
                        ],
                        implementation_steps=[
                            "Correlacionar consumo com carga e processos ativos",
                            "Distinguir pico transitório de crescimento persistente",
                            "Propor mitigação sujeita a revisão humana",
                            "Validar consumo e margem após a mudança",
                        ],
                        risk_level=0.7,
                    )
                )

        for improvement in improvements:
            improvement.priority_score = round(
                self._priority_score(improvement, issues), 4
            )
        improvements.sort(key=lambda imp: imp.priority_score, reverse=True)

        return improvements

    def _priority_score(
        self, improvement: PlannedImprovement, issues: list[DetectedIssue]
    ) -> float:
        """Calcula score de prioridade (maior = mais prioritário)."""
        # Encontra issue relacionada
        related_issues = [
            iss for iss in issues if iss.affected_component == improvement.target_component
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

    async def execute_improvement(self, improvement: PlannedImprovement) -> AppliedImprovement:
        """Recusa execução até existir um adaptador real e verificável."""
        del improvement
        raise NotImplementedError(
            "Execução automática de melhorias não possui adaptador auditável."
        )


# ==================== CICLO DE AUTO-OTIMIZAÇÃO ====================


class SelfOptimizationCycle:
    """
    Ciclo principal de auto-otimização proativa.

    Fluxo:
    1. MONITOR: Coleta métricas do sistema
    2. DETECT: Identifica problemas e gargalos
    3. PLAN: Planeja melhorias específicas
    4. REVIEW: Expõe propostas para revisão humana
    """

    def __init__(self) -> None:
        self.monitor = SystemMonitor()
        self.planner = ImprovementPlanner()
        self.executor = ImprovementExecutor()
        self._running = False
        self._stop_event: asyncio.Event | None = None

    async def run_cycle(
        self, enable_auto_execution: bool = False, max_improvements: int | None = None
    ) -> dict[str, Any]:
        """Executa um ciclo completo de auto-otimização."""
        if enable_auto_execution:
            raise NotImplementedError(
                "Execução automática de melhorias não possui adaptador auditável."
            )
        cycle_start = time.perf_counter()

        try:
            logger.info("[SelfOptimization] === Iniciando ciclo de auto-otimização ===")

            # 1. MONITOR
            metrics = await self.monitor.collect_metrics()
            logger.info("log_info", message=f"[SelfOptimization] Métricas: health_score={self.monitor._calculate_health_score(metrics):.2f}, "
                f"error_rate={metrics.error_rate:.1%}, avg_response={metrics.avg_response_time:.2f}s"
            )

            # 2. DETECT
            issues = self.monitor.detect_issues()
            logger.info("log_info", message=f"[SelfOptimization] Problemas detectados: {len(issues)}")

            if not issues:
                elapsed = time.perf_counter() - cycle_start
                logger.info(
                    "[SelfOptimization] Nenhum problema detectado na amostra atual"
                )
                _OPTIMIZATION_CYCLES.labels("success_no_issues").inc()
                return {
                    "success": True,
                    "issues_detected": 0,
                    "improvements_planned": 0,
                    "improvements_applied": 0,
                    "elapsed_seconds": round(elapsed, 2),
                    "plans": [],
                    "message": "Nenhum problema detectado na amostra atual.",
                }

            # 3. PLAN
            improvements = await self.planner.plan_improvements(issues, metrics)
            logger.info("log_info", message=f"[SelfOptimization] Melhorias planejadas: {len(improvements)}")

            # Limita melhorias por ciclo (padrão 3) para evitar sobrecarga
            effective_limit = max_improvements if (max_improvements is not None) else 3
            improvements = improvements[:effective_limit]

            logger.info(
                "[SelfOptimization] Melhorias apenas planejadas; "
                "nenhuma execução foi realizada"
            )

            elapsed = time.perf_counter() - cycle_start
            _OPTIMIZATION_LATENCY.observe(elapsed)
            _OPTIMIZATION_CYCLES.labels("success_planned_no_exec").inc()

            return {
                "success": True,
                "issues_detected": len(issues),
                "improvements_planned": len(improvements),
                "improvements_applied": 0,
                "elapsed_seconds": round(elapsed, 2),
                "plans": [improvement.to_dict() for improvement in improvements],
                "message": "Planos gerados para revisão humana; nenhuma melhoria foi aplicada.",
            }

        except Exception as e:
            logger.error("log_error", message=f"[SelfOptimization] Erro no ciclo: {e}", exc_info=True)
            _OPTIMIZATION_CYCLES.labels("error").inc()
            raise

    async def run_continuous(
        self,
        interval_seconds: float = 300,
        on_cycle_completed: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        """
        Executa ciclo de auto-otimização continuamente.

        Args:
            interval_seconds: Intervalo entre ciclos (padrão: 5 minutos)
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds deve ser maior que zero")
        if self._running:
            raise RuntimeError("O ciclo contínuo de otimização já está em execução.")

        self._running = True
        self._stop_event = asyncio.Event()
        logger.info(
            "log_info",
            message=(
                "[SelfOptimization] Iniciando execução contínua "
                f"(intervalo: {interval_seconds}s)"
            ),
        )

        try:
            while self._running:
                try:
                    cycle_result = await self.run_cycle()
                except asyncio.CancelledError:
                    raise
                except OptimizationMetricsUnavailableError as exc:
                    logger.warning(
                        "self_optimization_metrics_unavailable",
                        error=str(exc),
                    )
                except Exception as exc:
                    logger.error(
                        "self_optimization_cycle_failed",
                        error=str(exc),
                        exc_info=True,
                    )
                else:
                    if on_cycle_completed is not None:
                        await on_cycle_completed(cycle_result)

                if not self._running:
                    break
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=interval_seconds
                    )
                except TimeoutError:
                    pass
        finally:
            self._running = False
            self._stop_event = None
            logger.info("[SelfOptimization] Execução contínua encerrada")

    def stop(self) -> None:
        """Para execução contínua."""
        self._running = False
        if self._stop_event is not None:
            self._stop_event.set()
        logger.info("[SelfOptimization] Parando execução contínua")


# ==================== INSTÂNCIA GLOBAL ====================

self_optimization_cycle = SelfOptimizationCycle()
