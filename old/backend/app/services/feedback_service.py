from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from app.models.feedback_models import FeedbackEntry
from app.repositories.feedback_repository import FeedbackRepository
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)
FEEDBACK_TOTAL = Counter("janus_feedback_total", "Total feedback received", ["rating", "type"])
FEEDBACK_SCORE_GAUGE = Gauge("janus_feedback_average_score", "Average feedback score")
FEEDBACK_RESPONSE_TIME = Histogram("janus_feedback_response_time_seconds", "Feedback latency")


class FeedbackRating(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FeedbackType(str, Enum):
    MESSAGE = "message"
    CONVERSATION = "conversation"
    TOOL = "tool"
    SUGGESTION = "suggestion"


@dataclass
class Feedback:
    id: str
    conversation_id: str
    message_id: str | None
    user_id: str
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
    total_feedbacks: int
    positive_count: int
    negative_count: int
    neutral_count: int
    satisfaction_rate: float
    nps_score: int | None
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
    def __init__(
        self,
        max_memory_size: int = 1000,
        repository: FeedbackRepository | None = None,
    ) -> None:
        self._max_memory_size = max_memory_size
        self._repository = repository or FeedbackRepository()

    @staticmethod
    def _from_entry(entry: FeedbackEntry) -> Feedback:
        return Feedback(
            id=str(entry.id),
            conversation_id=str(entry.conversation_id),
            message_id=str(entry.message_id) if entry.message_id is not None else None,
            user_id=str(entry.owner_user_id),
            rating=FeedbackRating(str(entry.rating)),
            feedback_type=FeedbackType(str(entry.feedback_type)),
            comment=entry.comment,
            context=dict(entry.context_json or {}),
            created_at=entry.created_at,
        )

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
        if user_id is None:
            raise ValueError("authenticated owner is required")
        entry = self._repository.create(
            feedback_id=str(uuid.uuid4()),
            owner_user_id=int(user_id),
            conversation_id=conversation_id,
            message_id=message_id,
            rating=rating.value,
            feedback_type=feedback_type.value,
            comment=comment,
            context=context or {},
        )
        FEEDBACK_TOTAL.labels(rating=rating.value, type=feedback_type.value).inc()
        self._update_satisfaction_gauge()
        return self._from_entry(entry)

    async def record_thumbs_up(self, **kwargs: Any) -> Feedback:
        return await self.record_feedback(rating=FeedbackRating.POSITIVE, **kwargs)

    async def record_thumbs_down(self, **kwargs: Any) -> Feedback:
        return await self.record_feedback(rating=FeedbackRating.NEGATIVE, **kwargs)

    def _update_satisfaction_gauge(self) -> None:
        feedbacks = [self._from_entry(item) for item in self._repository.list_global(limit=100)]
        if feedbacks:
            positive = sum(item.rating is FeedbackRating.POSITIVE for item in feedbacks)
            FEEDBACK_SCORE_GAUGE.set(positive / len(feedbacks))

    async def get_satisfaction_report(
        self, user_id: str | None = None, hours: int = 24
    ) -> SatisfactionReport:
        now = datetime.now()
        cutoff = now - timedelta(hours=hours)
        if user_id is None:
            entries = self._repository.list_global(limit=self._max_memory_size)
            entries = [entry for entry in entries if entry.created_at >= cutoff]
        else:
            entries = self._repository.list_for_owner(owner_user_id=int(user_id), since=cutoff)
        feedbacks = [self._from_entry(entry) for entry in entries]
        positive = sum(item.rating is FeedbackRating.POSITIVE for item in feedbacks)
        negative = sum(item.rating is FeedbackRating.NEGATIVE for item in feedbacks)
        neutral = sum(item.rating is FeedbackRating.NEUTRAL for item in feedbacks)
        denominator = positive + negative
        satisfaction = positive / denominator if denominator else 0.0
        total = len(feedbacks)
        nps = int(((positive - negative) / total) * 100) if total >= 10 else None
        issues = [
            item.comment
            for item in feedbacks
            if item.rating is FeedbackRating.NEGATIVE and item.comment
        ][:5]
        return SatisfactionReport(
            total_feedbacks=total,
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            satisfaction_rate=satisfaction,
            nps_score=nps,
            period_start=cutoff,
            period_end=now,
            top_issues=issues,
        )

    async def get_feedback_by_conversation(
        self, conversation_id: str, user_id: str
    ) -> list[Feedback]:
        return [
            self._from_entry(entry)
            for entry in self._repository.list_for_owner(
                owner_user_id=int(user_id), conversation_id=conversation_id
            )
        ]

    async def get_improvement_suggestions(self) -> list[dict[str, Any]]:
        negative = [
            self._from_entry(entry)
            for entry in self._repository.list_global(rating="negative", limit=50)
        ]
        by_provider: dict[str, int] = {}
        by_model: dict[str, int] = {}
        for item in negative:
            provider = str(item.context.get("provider", "unknown"))
            model = str(item.context.get("model", "unknown"))
            by_provider[provider] = by_provider.get(provider, 0) + 1
            by_model[model] = by_model.get(model, 0) + 1
        suggestions: list[dict[str, Any]] = []
        for kind, values in (("provider", by_provider), ("model", by_model)):
            suggestions.extend(
                {"type": f"{kind}_issue", kind: name, "occurrences": count}
                for name, count in values.items()
                if count >= 5
            )
        return suggestions

    def get_stats(self) -> dict[str, Any]:
        feedbacks = [
            self._from_entry(entry)
            for entry in self._repository.list_global(limit=self._max_memory_size)
        ]
        total = len(feedbacks)
        positive = sum(item.rating is FeedbackRating.POSITIVE for item in feedbacks)
        negative = sum(item.rating is FeedbackRating.NEGATIVE for item in feedbacks)
        denominator = positive + negative
        satisfaction = positive / denominator if denominator else None
        return {
            "total_feedbacks": total,
            "positive": positive,
            "negative": negative,
            "satisfaction_rate": round(satisfaction, 3) if satisfaction is not None else None,
            "status": "no_data" if total == 0 else "healthy" if satisfaction and satisfaction >= 0.7 else "needs_attention",
        }


_feedback_service: FeedbackService | None = None


def get_feedback_service() -> FeedbackService:
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service


def initialize_feedback_service(max_memory_size: int = 1000) -> FeedbackService:
    global _feedback_service
    _feedback_service = FeedbackService(max_memory_size=max_memory_size)
    return _feedback_service
