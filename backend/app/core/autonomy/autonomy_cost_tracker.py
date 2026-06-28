from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Gauge
    AUTONOMY_TOKENS_USED = Counter(
        "autonomy_tokens_used_total",
        "Total LLM tokens used by autonomy",
        ["type"],
    )
    AUTONOMY_COST_USD = Gauge(
        "autonomy_cost_usd_total",
        "Total estimated USD cost of autonomy LLM usage"
    )
except ImportError:
    AUTONOMY_TOKENS_USED = None  # type: ignore
    AUTONOMY_COST_USD = None     # type: ignore

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input_per_1k": 0.00250, "output_per_1k": 0.01000},
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    "gpt-4": {"input_per_1k": 0.03000, "output_per_1k": 0.06000},
    "gpt-3.5-turbo": {"input_per_1k": 0.00050, "output_per_1k": 0.00150},
    "grok-2": {"input_per_1k": 0.00200, "output_per_1k": 0.00800},
}


class AutonomyCostTracker:
    def __init__(self, daily_token_budget: int = 500_000):
        self._daily_budget = daily_token_budget
        self._records: list[dict[str, Any]] = []
        self._daily_tokens = 0
        self._daily_cost = 0.0
        self._last_reset_date = datetime.now(timezone.utc).date()

    def record_usage(
        self,
        goal_id: str,
        action_type: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        self._reset_if_new_day()
        pricing = MODEL_PRICING.get(model, {"input_per_1k": 0.0, "output_per_1k": 0.0})
        cost = (tokens_in / 1000.0) * pricing["input_per_1k"] + (tokens_out / 1000.0) * pricing["output_per_1k"]

        self._daily_tokens += tokens_in + tokens_out
        self._daily_cost += cost

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal_id": goal_id,
            "action_type": action_type,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_estimate_usd": round(cost, 6),
        }
        self._records.append(record)

        if AUTONOMY_TOKENS_USED is not None:
            AUTONOMY_TOKENS_USED.labels(type="input").inc(tokens_in)
            AUTONOMY_TOKENS_USED.labels(type="output").inc(tokens_out)
        if AUTONOMY_COST_USD is not None:
            AUTONOMY_COST_USD.set(round(self._daily_cost, 4))

    def get_daily_total(self) -> dict:
        self._reset_if_new_day()
        return {
            "tokens_used": self._daily_tokens,
            "cost_usd": round(self._daily_cost, 4),
            "daily_budget": self._daily_budget,
        }

    def get_goal_cost(self, goal_id: str) -> dict:
        goal_records = [r for r in self._records if r["goal_id"] == goal_id]
        total_tokens = sum(r["tokens_in"] + r["tokens_out"] for r in goal_records)
        total_cost = sum(r["cost_estimate_usd"] for r in goal_records)
        return {
            "goal_id": goal_id,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "actions": len(goal_records),
        }

    def get_cost_report(self, days: int = 7) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [r for r in self._records if datetime.fromisoformat(r["timestamp"]) >= cutoff]
        by_action: dict[str, dict] = {}
        for r in recent:
            at = r["action_type"]
            if at not in by_action:
                by_action[at] = {"count": 0, "tokens": 0, "cost_usd": 0.0}
            by_action[at]["count"] += 1
            by_action[at]["tokens"] += r["tokens_in"] + r["tokens_out"]
            by_action[at]["cost_usd"] += r["cost_estimate_usd"]

        return {
            "period_days": days,
            "total_tokens": sum(v["tokens"] for v in by_action.values()),
            "total_cost_usd": round(sum(v["cost_usd"] for v in by_action.values()), 4),
            "by_action": by_action,
            "daily_budget": self._daily_budget,
        }

    def budget_remaining(self) -> int:
        self._reset_if_new_day()
        return max(0, self._daily_budget - self._daily_tokens)

    def budget_exhausted(self) -> bool:
        return self.budget_remaining() <= 0

    def budget_warning(self) -> bool:
        return self._daily_tokens >= self._daily_budget * 0.8

    def _reset_if_new_day(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._last_reset_date:
            self._daily_tokens = 0
            self._daily_cost = 0.0
            self._last_reset_date = today


autonomy_cost_tracker = AutonomyCostTracker()
