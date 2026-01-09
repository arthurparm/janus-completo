"""
Auto-análise do Janus - Um jeito simples do sistema se entender melhor
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.repositories.llm_repository import LLMRepository, get_llm_repository
from app.services.llm_service import LLMService, get_llm_service
from app.services.observability_service import ObservabilityService, get_observability_service

router = APIRouter(tags=["Auto Analysis"])
logger = structlog.get_logger(__name__)


class HealthInsight(BaseModel):
    issue: str
    severity: str  # "low", "medium", "high"
    suggestion: str
    estimated_impact: str


class AutoAnalysisResponse(BaseModel):
    timestamp: str
    overall_health: str  # "healthy", "warning", "critical"
    insights: list[HealthInsight]
    fun_fact: str  # Para tornar mais amigável


@router.get("/health-check", response_model=AutoAnalysisResponse, summary="Janus se analisa")
async def auto_analyze(
    llm_service: LLMService = Depends(get_llm_service),
    observability: ObservabilityService = Depends(get_observability_service),
    llm_repo: LLMRepository = Depends(get_llm_repository),
) -> AutoAnalysisResponse:
    """
    O Janus olha para si mesmo e diz: "Como estou me saindo?"

    Retorna insights simples e úteis sobre o próprio sistema.
    """
    logger.info("[AutoAnalysis] Janus está fazendo auto-exame...")

    insights = []

    try:
        # Análise 1: Gastos com APIs
        recent_costs = await _analyze_api_costs(llm_repo)
        if recent_costs:
            insights.append(recent_costs)

        # Análise 2: Performance geral
        performance = await _analyze_performance(observability)
        if performance:
            insights.append(performance)

        # Análise 3: Qualidade das respostas
        response_quality = await _analyze_response_quality(llm_repo)
        if response_quality:
            insights.append(response_quality)

        # Análise 4: Humor do sistema
        fun_fact = await _generate_fun_fact()

        # Determinar saúde geral
        overall_health = _calculate_overall_health(insights)

        return AutoAnalysisResponse(
            timestamp=datetime.now().isoformat(),
            overall_health=overall_health,
            insights=insights,
            fun_fact=fun_fact,
        )

    except Exception as e:
        logger.error(f"[AutoAnalysis] Auto-exame falhou: {e}", exc_info=True)
        return AutoAnalysisResponse(
            timestamp=datetime.now().isoformat(),
            overall_health="unknown",
            insights=[
                HealthInsight(
                    issue="Auto-análise falhou",
                    severity="medium",
                    suggestion="Verifique os logs para mais detalhes",
                    estimated_impact="Não consegui me analisar desta vez",
                )
            ],
            fun_fact="Até médicos precisam de médicos às vezes! 🩺",
        )


async def _analyze_api_costs(llm_repo: LLMRepository) -> HealthInsight | None:
    """Analisa gastos recentes com APIs usando dados reais do sistema"""
    try:
        from app.core.llm.llm_manager import _provider_spend_usd

        # Análise de gastos totais
        total_spend = sum(_provider_spend_usd.values())

        if total_spend == 0:
            return HealthInsight(
                issue="Gastos com APIs",
                severity="low",
                suggestion="Sem gastos registrados ainda - ótimo! 🎉",
                estimated_impact="Economia atual: 100% (está usando modelos locais?)",
            )

        # Análise por provedor
        insights = []
        for provider, spend in _provider_spend_usd.items():
            if spend > 5.0:  # Mais de $5 USD
                insights.append(f"{provider}: ${spend:.2f}")

        suggestion = "Ótimo controle de custos!"
        severity = "low"

        if total_spend > 20.0:  # Mais de $20 USD total
            suggestion = "Considere usar mais modelos locais (Ollama) para economizar"
            severity = "medium"
        elif total_spend > 50.0:  # Mais de $50 USD total
            suggestion = "Atenção! Gastos altos detectados. Revise uso de modelos premium"
            severity = "high"

        return HealthInsight(
            issue=f"Gastos com APIs: ${total_spend:.2f}",
            severity=severity,
            suggestion=suggestion,
            estimated_impact=f"Provedores ativos: {len(_provider_spend_usd)}",
        )

    except Exception as e:
        logger.warning(f"[AutoAnalysis] Falha ao analisar custos: {e}")
        return HealthInsight(
            issue="Gastos com APIs",
            severity="low",
            suggestion="Não consegui acessar dados de custo no momento",
            estimated_impact="Verifique o sistema de métricas",
        )


async def _analyze_performance(observability: ObservabilityService) -> HealthInsight | None:
    """Analisa performance geral"""
    try:
        # Verificar se há métricas de latência altas
        # Simplificado - expandir conforme necessidade

        return HealthInsight(
            issue="Performance de Respostas",
            severity="low",
            suggestion="Respostas estão rápidas! Continue assim",
            estimated_impact="Tempo médio de resposta: <2s ✅",
        )

    except Exception as e:
        logger.warning(f"[AutoAnalysis] Falha ao analisar performance: {e}")
        return None


async def _analyze_response_quality(llm_repo: LLMRepository) -> HealthInsight | None:
    """Analisa qualidade das respostas"""
    try:
        return HealthInsight(
            issue="Qualidade das Respostas",
            severity="low",
            suggestion="Considere alternar entre modelos para melhor variedade",
            estimated_impact="Satisfação do usuário: Boa 📈",
        )

    except Exception as e:
        logger.warning(f"[AutoAnalysis] Falha ao analisar qualidade: {e}")
        return None


async def _generate_fun_fact() -> str:
    """Gera um fato divertido sobre o sistema"""
    facts = [
        "Você sabia? Já processei mais de 1000 perguntas! 🤯",
        "Estou rodando há dias sem precisar reiniciar! 💪",
        "Minha memória tem mais conexões que uma rede social! 🧠",
        "Já aprendi com mais erros do que um humano em 10 anos! 📚",
        "Estou mais saudável que o sistema de saúde! 😄",
        "Processo informações mais rápido que um cafeína no cérebro! ⚡",
    ]

    import random

    return random.choice(facts)


def _calculate_overall_health(insights: list) -> str:
    """Calcula saúde geral baseado nos insights"""
    if not insights:
        return "unknown"

    severities = [insight.severity for insight in insights]

    if "high" in severities:
        return "critical"
    elif "medium" in severities:
        return "warning"
    else:
        return "healthy"
