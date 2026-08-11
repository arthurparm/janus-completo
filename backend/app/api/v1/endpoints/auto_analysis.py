"""Evidence-backed operational self-analysis."""

from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.llm.pricing import get_provider_spend_snapshot
from app.services.feedback_service import FeedbackService, get_feedback_service
from app.services.observability_service import ObservabilityService, get_observability_service

router = APIRouter(tags=["Auto Analysis"])
logger = structlog.get_logger(__name__)


InsightSeverity = Literal["low", "medium", "high", "unknown"]
InsightStatus = Literal["ok", "warning", "critical", "insufficient_data", "unavailable"]
OverallHealth = Literal["healthy", "warning", "critical", "unknown"]


class HealthInsight(BaseModel):
    issue: str
    severity: InsightSeverity
    suggestion: str
    estimated_impact: str
    source: Literal["llm_cost_tracker", "observability_slo", "feedback"]
    status: InsightStatus
    evidence: dict[str, Any] = Field(default_factory=dict)


class AutoAnalysisResponse(BaseModel):
    timestamp: str
    overall_health: OverallHealth
    insights: list[HealthInsight]
    summary: str
    fun_fact: None = Field(default=None, deprecated=True)


@router.get("/health-check", response_model=AutoAnalysisResponse, summary="Janus se analisa")
async def auto_analyze(
    observability: ObservabilityService = Depends(get_observability_service),
    feedback: FeedbackService = Depends(get_feedback_service),
) -> AutoAnalysisResponse:
    """Summarize operational evidence without inferring unmeasured capabilities."""
    logger.info("auto_analysis_requested")
    insights = [
        await _analyze_api_costs(),
        await _analyze_performance(observability),
        _analyze_response_quality(feedback),
    ]
    overall_health = _calculate_overall_health(insights)
    unavailable = sum(item.status in {"insufficient_data", "unavailable"} for item in insights)
    summary = (
        f"Diagnóstico baseado em {len(insights) - unavailable} de {len(insights)} fontes "
        f"com evidência suficiente; estado geral: {overall_health}."
    )
    return AutoAnalysisResponse(
        timestamp=datetime.now(UTC).isoformat(),
        overall_health=overall_health,
        insights=insights,
        summary=summary,
    )


async def _analyze_api_costs() -> HealthInsight:
    """Assess tracked provider spend against configured budgets."""
    try:
        snapshot = await get_provider_spend_snapshot()
        usage = snapshot["budget_usage_pct"]
        if usage is None:
            return HealthInsight(
                issue="Orçamento de provedores LLM não configurado",
                severity="unknown",
                suggestion="Configure orçamentos positivos para avaliar o consumo relativo.",
                estimated_impact=f"Gasto rastreado: US$ {snapshot['total_spend_usd']:.4f}",
                source="llm_cost_tracker",
                status="insufficient_data",
                evidence=snapshot,
            )

        severity: Literal["low", "medium", "high"] = (
            "high" if usage >= 100.0 else "medium" if usage >= 90.0 else "low"
        )
        return HealthInsight(
            issue="Consumo do orçamento de provedores LLM",
            severity=severity,
            suggestion=(
                "Interrompa novos gastos e revise os limites por provedor."
                if severity == "high"
                else "Revise a projeção antes de atingir o limite."
                if severity == "medium"
                else "Mantenha o acompanhamento do consumo."
            ),
            estimated_impact=f"{usage:.2f}% do orçamento configurado consumido",
            source="llm_cost_tracker",
            status=(
                "critical" if severity == "high" else "warning" if severity == "medium" else "ok"
            ),
            evidence=snapshot,
        )
    except Exception as exc:
        logger.exception("auto_analysis_cost_unavailable", error=str(exc))
        return HealthInsight(
            issue="Métricas de custo indisponíveis",
            severity="unknown",
            suggestion="Restaure o tracker de uso e repita a análise.",
            estimated_impact="O consumo de orçamento não foi avaliado.",
            source="llm_cost_tracker",
            status="unavailable",
        )


async def _analyze_performance(observability: ObservabilityService) -> HealthInsight:
    """Assess actual audited SLO observations."""
    try:
        report = await observability.get_domain_slo_report()
        domains = report.get("domains") or []
        if report.get("status") == "insufficient_data":
            return HealthInsight(
                issue="Performance sem amostra suficiente",
                severity="unknown",
                suggestion="Aguarde o mínimo de eventos auditados por domínio.",
                estimated_impact="Nenhuma conclusão de latência ou disponibilidade foi emitida.",
                source="observability_slo",
                status="insufficient_data",
                evidence=report,
            )

        breaches = sum(len(item.get("breaches") or []) for item in domains)
        return HealthInsight(
            issue="SLOs operacionais por domínio",
            severity="medium" if breaches else "low",
            suggestion=(
                "Investigue os domínios em violação antes de ampliar carga."
                if breaches
                else "Mantenha os limites e a coleta de eventos auditados."
            ),
            estimated_impact=f"{breaches} violação(ões) ativa(s) em {len(domains)} domínios",
            source="observability_slo",
            status="warning" if breaches else "ok",
            evidence=report,
        )
    except Exception as exc:
        logger.exception("auto_analysis_performance_unavailable", error=str(exc))
        return HealthInsight(
            issue="SLOs operacionais indisponíveis",
            severity="unknown",
            suggestion="Restaure a consulta ao ledger de auditoria e repita a análise.",
            estimated_impact="Performance e disponibilidade não foram avaliadas.",
            source="observability_slo",
            status="unavailable",
        )


def _analyze_response_quality(feedback: FeedbackService) -> HealthInsight:
    """Assess response quality only from persisted explicit feedback."""
    try:
        stats = feedback.get_stats()
        total = int(stats.get("total_feedbacks") or 0)
        satisfaction = stats.get("satisfaction_rate")
        if total == 0 or satisfaction is None:
            return HealthInsight(
                issue="Qualidade sem feedback suficiente",
                severity="unknown",
                suggestion="Colete feedback explícito antes de inferir satisfação.",
                estimated_impact="Nenhuma afirmação sobre qualidade foi emitida.",
                source="feedback",
                status="insufficient_data",
                evidence=stats,
            )

        score = float(satisfaction)
        severity: Literal["low", "medium", "high"] = (
            "low" if score >= 0.7 else "medium" if score >= 0.4 else "high"
        )
        return HealthInsight(
            issue="Qualidade medida por feedback explícito",
            severity=severity,
            suggestion=(
                "Analise os feedbacks negativos e priorize correções."
                if severity != "low"
                else "Continue coletando feedback para preservar a validade da amostra."
            ),
            estimated_impact=f"Satisfação {score * 100:.1f}% em {total} feedback(s)",
            source="feedback",
            status=(
                "critical" if severity == "high" else "warning" if severity == "medium" else "ok"
            ),
            evidence=stats,
        )
    except Exception as exc:
        logger.exception("auto_analysis_feedback_unavailable", error=str(exc))
        return HealthInsight(
            issue="Feedback de qualidade indisponível",
            severity="unknown",
            suggestion="Restaure o repositório de feedback e repita a análise.",
            estimated_impact="Qualidade das respostas não foi avaliada.",
            source="feedback",
            status="unavailable",
        )


def _calculate_overall_health(insights: list[HealthInsight]) -> OverallHealth:
    """Calculate health without treating missing evidence as healthy."""
    if not insights:
        return "unknown"
    severities = {insight.severity for insight in insights}
    if severities == {"unknown"}:
        return "unknown"
    if "high" in severities:
        return "critical"
    if "medium" in severities or "unknown" in severities:
        return "warning"
    return "healthy"
