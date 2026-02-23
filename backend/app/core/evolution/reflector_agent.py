"""
ReflectorAgent: Janus Self-Analysis Component

This agent analyzes past experiences from memory to identify:
1. Failure patterns (repeated errors, timeouts, missing tools)
2. Slow response patterns (queries that took too long)
3. User dissatisfaction signals (negative feedback, corrections)
4. Missing capabilities (things Janus couldn't do)

The output is a structured "Reflection Report" that feeds into the Evolution system.
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """Represents a detected failure pattern."""

    pattern_type: str  # "tool_missing", "error", "timeout", "incorrect_response"
    description: str
    occurrences: int
    examples: list[str] = field(default_factory=list)
    suggested_improvement: str | None = None
    priority: int = 1  # 1-5, higher = more urgent


@dataclass
class ReflectionReport:
    """Complete self-analysis report."""

    generated_at: str
    experiences_analyzed: int
    failure_patterns: list[FailurePattern] = field(default_factory=list)
    slow_patterns: list[dict[str, Any]] = field(default_factory=list)
    improvement_suggestions: list[str] = field(default_factory=list)
    overall_health_score: float = 1.0  # 0-1, lower = needs improvement


class ReflectorAgent:
    """
    Analyzes Janus's past experiences to identify improvement opportunities.

    This is the "self-awareness" component of the Self-Study loop.
    It reads from MemoryCore and produces actionable insights.
    """

    # Keywords that indicate failures
    FAILURE_KEYWORDS = [
        "error",
        "failed",
        "não consegui",
        "não foi possível",
        "timeout",
        "exception",
        "falha",
        "problema",
        "tool not found",
        "ferramenta não encontrada",
        "command not found",
        "comando não encontrado",
    ]

    # Keywords that indicate user dissatisfaction
    DISSATISFACTION_KEYWORDS = [
        "errado",
        "incorreto",
        "wrong",
        "não era isso",
        "tente novamente",
        "try again",
        "não funcionou",
        "isso não ajudou",
        "didn't help",
    ]

    def __init__(self, memory_core):
        """
        Args:
            memory_core: Instance of MemoryCore for reading past experiences.
        """
        self.memory = memory_core

    async def analyze_recent_experiences(
        self, hours_back: int = 24, limit: int = 100
    ) -> ReflectionReport:
        """
        Analyze recent experiences and generate a reflection report.

        Args:
            hours_back: How many hours of history to analyze.
            limit: Maximum number of experiences to analyze.

        Returns:
            ReflectionReport with identified patterns and suggestions.
        """
        logger.info(f"[Reflector] Iniciando análise das últimas {hours_back} horas...")

        report = ReflectionReport(generated_at=datetime.now().isoformat(), experiences_analyzed=0)

        try:
            # Fetch recent experiences from memory
            experiences = await self._fetch_recent_experiences(hours_back, limit)
            report.experiences_analyzed = len(experiences)

            if not experiences:
                logger.info("[Reflector] Nenhuma experiência recente encontrada.")
                return report

            # Analyze for failure patterns
            report.failure_patterns = self._detect_failure_patterns(experiences)

            # Analyze for slow responses
            report.slow_patterns = self._detect_slow_patterns(experiences)

            # Generate improvement suggestions
            report.improvement_suggestions = self._generate_suggestions(report)

            # Calculate health score
            report.overall_health_score = self._calculate_health_score(report)

            logger.info(
                f"[Reflector] Análise completa. "
                f"Padrões de falha: {len(report.failure_patterns)}, "
                f"Score de saúde: {report.overall_health_score:.2f}"
            )

            return report

        except Exception as e:
            logger.error(f"[Reflector] Erro durante análise: {e}", exc_info=True)
            return report

    async def _fetch_recent_experiences(self, hours_back: int, limit: int) -> list[dict[str, Any]]:
        """Fetch experiences from memory within the time window."""
        try:
            # Use memory search to find recent experiences
            # We search for common interaction types
            experiences = []

            # Search for different experience types
            search_queries = [
                "user interaction response",
                "tool execution result",
                "error exception failure",
                "agent action completed",
            ]

            for query in search_queries:
                try:
                    results = await self.memory.arecall(
                        query=query, top_k=limit // len(search_queries)
                    )
                    if results:
                        experiences.extend(results)
                except Exception as e:
                    logger.debug(f"[Reflector] Query '{query}' falhou: {e}")
                    continue

            # Filter by time if possible (depends on metadata structure)
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            filtered = []
            for exp in experiences:
                # Try to extract timestamp from metadata
                if isinstance(exp, dict):
                    ts = exp.get("metadata", {}).get("timestamp")
                    if ts:
                        try:
                            exp_time = datetime.fromisoformat(ts)
                            if exp_time >= cutoff_time:
                                filtered.append(exp)
                                continue
                        except Exception:
                            pass
                    # If no timestamp or can't parse, include anyway
                    filtered.append(exp)

            return filtered[:limit]

        except Exception as e:
            logger.error(f"[Reflector] Erro ao buscar experiências: {e}")
            return []

    def _detect_failure_patterns(self, experiences: list[dict[str, Any]]) -> list[FailurePattern]:
        """Detect patterns of failures in experiences."""
        patterns = {}

        for exp in experiences:
            content = self._get_content(exp)
            if not content:
                continue

            content_lower = content.lower()

            # Check for failure keywords
            for keyword in self.FAILURE_KEYWORDS:
                if keyword in content_lower:
                    key = self._categorize_failure(content_lower, keyword)

                    if key not in patterns:
                        patterns[key] = {"type": key, "count": 0, "examples": []}

                    patterns[key]["count"] += 1
                    if len(patterns[key]["examples"]) < 3:
                        patterns[key]["examples"].append(content[:200])
                    break

        # Convert to FailurePattern objects
        result = []
        for key, data in patterns.items():
            if data["count"] >= 2:  # Only report if happened multiple times
                pattern = FailurePattern(
                    pattern_type=data["type"],
                    description=f"Detectadas {data['count']} ocorrências de '{key}'",
                    occurrences=data["count"],
                    examples=data["examples"],
                    suggested_improvement=self._suggest_improvement_for_pattern(key),
                    priority=min(5, data["count"]),
                )
                result.append(pattern)

        # Sort by priority (most urgent first)
        result.sort(key=lambda p: p.priority, reverse=True)
        return result

    def _detect_slow_patterns(self, experiences: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect patterns of slow responses."""
        slow_patterns = []

        for exp in experiences:
            metadata = exp.get("metadata", {}) if isinstance(exp, dict) else {}
            duration = metadata.get("duration_seconds") or metadata.get("latency")

            if duration and float(duration) > 10:  # Threshold: 10 seconds
                slow_patterns.append(
                    {
                        "query_type": metadata.get("type", "unknown"),
                        "duration_seconds": float(duration),
                        "context": self._get_content(exp)[:100],
                    }
                )

        return slow_patterns

    def _generate_suggestions(self, report: ReflectionReport) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions = []

        for pattern in report.failure_patterns:
            if pattern.suggested_improvement:
                suggestions.append(pattern.suggested_improvement)

        # Add suggestions for slow patterns
        if len(report.slow_patterns) > 3:
            suggestions.append(
                "Implementar cache para queries frequentes - muitas respostas lentas detectadas."
            )

        return suggestions

    def _calculate_health_score(self, report: ReflectionReport) -> float:
        """Calculate overall health score (0-1)."""
        if report.experiences_analyzed == 0:
            return 1.0

        # Start at 1.0 and subtract for issues
        score = 1.0

        # Deduct for failure patterns
        for pattern in report.failure_patterns:
            deduction = (pattern.occurrences / report.experiences_analyzed) * 0.5
            score -= min(0.2, deduction)

        # Deduct for slow patterns
        slow_ratio = len(report.slow_patterns) / report.experiences_analyzed
        score -= slow_ratio * 0.3

        return max(0.0, min(1.0, score))

    def _get_content(self, experience: Any) -> str:
        """Extract content string from experience."""
        if isinstance(experience, dict):
            return str(experience.get("content", experience.get("text", "")))
        elif hasattr(experience, "content"):
            return str(experience.content)
        return str(experience)

    def _categorize_failure(self, content: str, keyword: str) -> str:
        """Categorize the type of failure."""
        if "tool" in content or "ferramenta" in content:
            return "tool_missing"
        elif "timeout" in content:
            return "timeout"
        elif "connection" in content or "conexão" in content:
            return "connection_error"
        elif "not found" in content or "não encontr" in content:
            return "resource_not_found"
        else:
            return "general_error"

    def _suggest_improvement_for_pattern(self, pattern_type: str) -> str | None:
        """Suggest an improvement based on pattern type."""
        suggestions = {
            "tool_missing": "Criar ferramenta dinâmica para essa funcionalidade via EvolutionManager.",
            "timeout": "Aumentar timeout ou implementar cache para reduzir latência.",
            "connection_error": "Implementar retry com backoff exponencial.",
            "resource_not_found": "Verificar configuração de recursos e caminhos.",
            "general_error": "Analisar logs detalhados para identificar causa raiz.",
        }
        return suggestions.get(pattern_type)

    def to_dict(self, report: ReflectionReport) -> dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            "generated_at": report.generated_at,
            "experiences_analyzed": report.experiences_analyzed,
            "failure_patterns": [asdict(p) for p in report.failure_patterns],
            "slow_patterns": report.slow_patterns,
            "improvement_suggestions": report.improvement_suggestions,
            "overall_health_score": report.overall_health_score,
        }
