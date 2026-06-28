import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Gauge
    AUTONOMY_DECISION_ACCURACY = Gauge(
        "autonomy_decision_accuracy",
        "Rolling 7-day accuracy of autonomy decisions (correct / total)"
    )
    AUTONOMY_DECISION_TOTAL = Counter(
        "autonomy_decision_total",
        "Total autonomy decisions recorded",
        ["outcome"]
    )
except ImportError:
    AUTONOMY_DECISION_ACCURACY = None  # type: ignore
    AUTONOMY_DECISION_TOTAL = None     # type: ignore


class DecisionQualityTracker:
    def __init__(self):
        pass

    def record_decision(
        self,
        goal_id: str,
        decision_type: str,
        predicted_outcome: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        decision_id = f"dec-{uuid.uuid4().hex[:12]}"
        record_audit_event_direct(
            endpoint="autonomy_decision",
            action="decision_recorded",
            status="pending_outcome",
            details_json={
                "decision_id": decision_id,
                "goal_id": goal_id,
                "decision_type": decision_type,
                "predicted_outcome": predicted_outcome,
                "context": context or {},
            },
        )
        return decision_id

    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        was_correct: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        record_audit_event_direct(
            endpoint="autonomy_decision",
            action="decision_outcome",
            status="success" if was_correct else "failure",
            details_json={
                "decision_id": decision_id,
                "actual_outcome": actual_outcome,
                "was_correct": was_correct,
                "details": details or {},
            },
        )
        if AUTONOMY_DECISION_TOTAL is not None:
            AUTONOMY_DECISION_TOTAL.labels(outcome="correct" if was_correct else "incorrect").inc()
        self._update_accuracy_gauge()

    def get_accuracy(self, days: int = 7) -> float:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return self._compute_accuracy_since(cutoff)

    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        return self._query_recent_decisions(limit)

    def _compute_accuracy_since(self, cutoff_iso: str) -> float:
        total = 0
        correct = 0
        decisions = self._query_recent_decisions(100)
        for d in decisions:
            timestamp = d.get("timestamp") or d.get("created_at", "")
            if timestamp < cutoff_iso:
                continue
            if d.get("action") == "decision_outcome":
                total += 1
                if d.get("details", {}).get("was_correct"):
                    correct += 1
        return correct / max(total, 1)

    def _query_recent_decisions(self, limit: int) -> list[dict]:
        return []

    def _update_accuracy_gauge(self) -> None:
        if AUTONOMY_DECISION_ACCURACY is not None:
            try:
                accuracy = self.get_accuracy(days=7)
                AUTONOMY_DECISION_ACCURACY.set(accuracy)
            except Exception:
                pass


decision_quality_tracker = DecisionQualityTracker()
