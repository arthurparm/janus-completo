from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GoalMetrics:
    goal_id: str
    success_rate: float
    time_efficiency: float
    tool_accuracy: float
    recovery_rate: float
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    fallback_successes: int = 0
    estimated_duration: float = 0.0
    actual_duration: float = 0.0


class GoalMetricsCalculator:
    def compute(self, goal_id: str, steps: list[Any], repository: Any = None) -> GoalMetrics:
        total = len(steps) or 1
        completed = sum(1 for s in steps if getattr(s, "status", "") == "completed")
        failed = sum(1 for s in steps if getattr(s, "status", "") == "failed")
        fallback_success = sum(1 for s in steps if getattr(s, "fallback_used", False) and getattr(s, "status", "") == "completed")

        success_rate = completed / total
        time_efficiency = 1.0
        total_estimated = sum(float(getattr(s, "estimated_duration_seconds", 0) or 0) for s in steps)
        total_actual = sum(float(getattr(s, "actual_duration_seconds", 0) or 0) for s in steps)
        if total_estimated > 0:
            time_efficiency = min(total_estimated / max(total_actual, 0.001), 1.0)

        tool_accuracy = 1.0
        tool_steps = [s for s in steps if getattr(s, "tool_name", None)]
        if tool_steps:
            accurate = sum(1 for s in tool_steps if getattr(s, "status", "") == "completed")
            tool_accuracy = accurate / max(len(tool_steps), 1)

        recovery_rate = 0.0
        if failed > 0:
            recovery_rate = fallback_success / max(failed, 1)

        return GoalMetrics(
            goal_id=goal_id,
            success_rate=success_rate,
            time_efficiency=time_efficiency,
            tool_accuracy=tool_accuracy,
            recovery_rate=recovery_rate,
            total_steps=total,
            completed_steps=completed,
            failed_steps=failed,
            fallback_successes=fallback_success,
            estimated_duration=total_estimated,
            actual_duration=total_actual,
        )


goal_metrics_calculator = GoalMetricsCalculator()
