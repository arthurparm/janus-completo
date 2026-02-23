"""
Feedback Service - Coleta e análise de feedback do usuário.

Implementa o Quick Win de feedback loop (👍/👎) para começar a coletar
dados de satisfação e melhorar continuamente as respostas do Janus.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)

# --- Métricas ---
FEEDBACK_TOTAL = Counter("janus_feedback_total", "Total de feedbacks recebidos", ["rating", "type"])

FEEDBACK_SCORE_GAUGE = Gauge(
    "janus_feedback_average_score", "Score médio de satisfação (últimas 100 respostas)"
)

FEEDBACK_RESPONSE_TIME = Histogram(
    "janus_feedback_response_time_seconds",
    "Tempo entre resposta e feedback",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)


class FeedbackRating(str, Enum):
    """Tipos de rating de feedback."""

    POSITIVE = "positive"  # 👍
    NEGATIVE = "negative"  # 👎
    NEUTRAL = "neutral"  # 😐


class FeedbackType(str, Enum):
    """Tipos de feedback."""

    MESSAGE = "message"  # Feedback em mensagem específica
    CONVERSATION = "conversation"  # Feedback geral da conversa
    TOOL = "tool"  # Feedback sobre uso de ferramenta
    SUGGESTION = "suggestion"  # Sugestão do usuário


@dataclass
class Feedback:
    """Representa um feedback do usuário."""

    id: str
    conversation_id: str
    message_id: str | None
    user_id: str | None
    rating: FeedbackRating
    feedback_type: FeedbackType
    comment: str | None
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "rating": self.rating.value,
            "feedback_type": self.feedback_type.value,
            "comment": self.comment,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SatisfactionReport:
    """Relatório de satisfação."""

    total_feedbacks: int
    positive_count: int
    negative_count: int
    neutral_count: int
    satisfaction_rate: float  # 0.0 a 1.0
    nps_score: int | None  # -100 a 100
    period_start: datetime
    period_end: datetime
    top_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_feedbacks": self.total_feedbacks,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "satisfaction_rate": round(self.satisfaction_rate, 3),
            "nps_score": self.nps_score,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "top_issues": self.top_issues,
        }


class FeedbackService:
    """
    Serviço de coleta e análise de feedback.

    Funcionalidades:
    - Registrar feedback positivo/negativo
    - Calcular métricas de satisfação
    - Identificar padrões de insatisfação
    - Gerar relatórios para o Meta-Agent
    """

    def __init__(self, max_memory_size: int = 1000):
        self._feedbacks: list[Feedback] = []
        self._max_memory_size = max_memory_size
        self._lock = asyncio.Lock()
        logger.info("FeedbackService inicializado", max_memory_size=max_memory_size)

    async def record_feedback(
        self,
        conversation_id: str,
        rating: FeedbackRating,
        message_id: str | None = None,
        user_id: str | None = None,
        comment: str | None = None,
        feedback_type: FeedbackType = FeedbackType.MESSAGE,
        context: dict[str, Any] | None = None,
    ) -> Feedback:
        """
        Registra um feedback do usuário.

        Args:
            conversation_id: ID da conversa
            rating: Rating do feedback (positive/negative/neutral)
            message_id: ID da mensagem específica (opcional)
            user_id: ID do usuário
            comment: Comentário adicional
            feedback_type: Tipo do feedback
            context: Contexto adicional (ex: provider, model, latency)

        Returns:
            Feedback registrado
        """
        import uuid

        feedback = Feedback(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment,
            context=context or {},
        )

        async with self._lock:
            self._feedbacks.append(feedback)

            # Manter tamanho máximo
            if len(self._feedbacks) > self._max_memory_size:
                self._feedbacks = self._feedbacks[-self._max_memory_size :]

        # Atualizar métricas
        FEEDBACK_TOTAL.labels(rating=rating.value, type=feedback_type.value).inc()
        self._update_satisfaction_gauge()

        logger.info(
            "Feedback registrado",
            feedback_id=feedback.id,
            rating=rating.value,
            conversation_id=conversation_id,
            message_id=message_id,
        )

        return feedback

    async def record_thumbs_up(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str | None = None,
        comment: str | None = None,
    ) -> Feedback:
        """Atalho para registrar feedback positivo (👍)."""
        return await self.record_feedback(
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            rating=FeedbackRating.POSITIVE,
            comment=comment,
        )

    async def record_thumbs_down(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str | None = None,
        comment: str | None = None,
    ) -> Feedback:
        """Atalho para registrar feedback negativo (👎)."""
        return await self.record_feedback(
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            rating=FeedbackRating.NEGATIVE,
            comment=comment,
        )

    def _update_satisfaction_gauge(self) -> None:
        """Atualiza o gauge de satisfação com base nos últimos feedbacks."""
        recent = self._feedbacks[-100:] if self._feedbacks else []
        if not recent:
            return

        positive = sum(1 for f in recent if f.rating == FeedbackRating.POSITIVE)
        total = len(recent)

        satisfaction = positive / total if total > 0 else 0.5
        FEEDBACK_SCORE_GAUGE.set(satisfaction)

    async def get_satisfaction_report(
        self,
        user_id: str | None = None,
        hours: int = 24,
    ) -> SatisfactionReport:
        """
        Gera relatório de satisfação.

        Args:
            user_id: Filtrar por usuário (opcional)
            hours: Janela de tempo em horas

        Returns:
            SatisfactionReport com métricas
        """
        now = datetime.now()
        cutoff = now - timedelta(hours=hours)

        async with self._lock:
            feedbacks = [
                f
                for f in self._feedbacks
                if f.created_at >= cutoff and (user_id is None or f.user_id == user_id)
            ]

        if not feedbacks:
            return SatisfactionReport(
                total_feedbacks=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                satisfaction_rate=0.0,
                nps_score=None,
                period_start=cutoff,
                period_end=now,
                top_issues=[],
            )

        positive = sum(1 for f in feedbacks if f.rating == FeedbackRating.POSITIVE)
        negative = sum(1 for f in feedbacks if f.rating == FeedbackRating.NEGATIVE)
        neutral = sum(1 for f in feedbacks if f.rating == FeedbackRating.NEUTRAL)
        total = len(feedbacks)

        # Taxa de satisfação: positivos / (positivos + negativos)
        pn_total = positive + negative
        satisfaction_rate = positive / pn_total if pn_total > 0 else 0.5

        # NPS simplificado: % promotores - % detratores
        nps_score = None
        if total >= 10:  # Mínimo para NPS significativo
            promoters = (positive / total) * 100
            detractors = (negative / total) * 100
            nps_score = int(promoters - detractors)

        # Top issues: comentários de feedbacks negativos
        top_issues = [
            f.comment for f in feedbacks if f.rating == FeedbackRating.NEGATIVE and f.comment
        ][:5]

        return SatisfactionReport(
            total_feedbacks=total,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            satisfaction_rate=satisfaction_rate,
            nps_score=nps_score,
            period_start=cutoff,
            period_end=now,
            top_issues=top_issues,
        )

    async def get_feedback_by_conversation(
        self,
        conversation_id: str,
    ) -> list[Feedback]:
        """Retorna todos os feedbacks de uma conversa."""
        async with self._lock:
            return [f for f in self._feedbacks if f.conversation_id == conversation_id]

    async def get_improvement_suggestions(self) -> list[dict[str, Any]]:
        """
        Analisa feedbacks negativos e gera sugestões de melhoria.
        Usado pelo Meta-Agent para auto-otimização.
        """
        async with self._lock:
            negative_feedbacks = [
                f for f in self._feedbacks if f.rating == FeedbackRating.NEGATIVE
            ][-50:]  # Últimos 50 negativos

        suggestions = []

        # Agrupar por contexto (provider, model, etc.)
        by_provider: dict[str, int] = {}
        by_model: dict[str, int] = {}

        for f in negative_feedbacks:
            provider = f.context.get("provider", "unknown")
            model = f.context.get("model", "unknown")

            by_provider[provider] = by_provider.get(provider, 0) + 1
            by_model[model] = by_model.get(model, 0) + 1

        # Identificar problemas recorrentes
        for provider, count in by_provider.items():
            if count >= 5:
                suggestions.append(
                    {
                        "type": "provider_issue",
                        "provider": provider,
                        "occurrences": count,
                        "suggestion": f"Considerar ajustar prioridade ou configuração do provider '{provider}'",
                    }
                )

        for model, count in by_model.items():
            if count >= 5:
                suggestions.append(
                    {
                        "type": "model_issue",
                        "model": model,
                        "occurrences": count,
                        "suggestion": f"Avaliar qualidade das respostas do modelo '{model}'",
                    }
                )

        return suggestions

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas rápidas do serviço."""
        total = len(self._feedbacks)
        if total == 0:
            return {
                "total_feedbacks": 0,
                "positive": 0,
                "negative": 0,
                "satisfaction_rate": None,
                "status": "no_data",
            }

        positive = sum(1 for f in self._feedbacks if f.rating == FeedbackRating.POSITIVE)
        negative = sum(1 for f in self._feedbacks if f.rating == FeedbackRating.NEGATIVE)

        pn_total = positive + negative
        satisfaction = positive / pn_total if pn_total > 0 else 0.5

        return {
            "total_feedbacks": total,
            "positive": positive,
            "negative": negative,
            "satisfaction_rate": round(satisfaction, 3),
            "status": "healthy" if satisfaction >= 0.7 else "needs_attention",
        }


# Singleton instance
_feedback_service: FeedbackService | None = None


def get_feedback_service() -> FeedbackService:
    """Retorna instância singleton do FeedbackService."""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service


def initialize_feedback_service(max_memory_size: int = 1000) -> FeedbackService:
    """Inicializa o FeedbackService com configurações customizadas."""
    global _feedback_service
    _feedback_service = FeedbackService(max_memory_size=max_memory_size)
    return _feedback_service
