from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConflictReport:
    conflict_type: str
    resource: str
    goal_a_id: str
    goal_b_id: str
    severity: str = "medium"
    description: str = ""


class GoalConflictDetector:
    CONFLICT_TYPES = frozenset({"same_resource", "opposite_intent", "resource_exhaustion"})

    def detect_conflicts(self, new_goal: Any, active_goals: list[Any]) -> list[ConflictReport]:
        reports = []
        new_resources = self._affected_resources(new_goal)

        for active in active_goals:
            active_resources = self._affected_resources(active)
            shared = new_resources & active_resources

            if shared:
                reports.append(ConflictReport(
                    conflict_type="same_resource",
                    resource=", ".join(sorted(shared)),
                    goal_a_id=new_goal.id,
                    goal_b_id=active.id,
                    severity="high",
                    description=f"Goals affect the same resources: {', '.join(sorted(shared))}",
                ))

            if self._has_opposite_intent(new_goal, active):
                reports.append(ConflictReport(
                    conflict_type="opposite_intent",
                    resource="",
                    goal_a_id=new_goal.id,
                    goal_b_id=active.id,
                    severity="critical",
                    description="Goals have opposing intents",
                ))

        return reports

    def _affected_resources(self, goal: Any) -> set[str]:
        resources = set()
        title = getattr(goal, "title", "")
        description = getattr(goal, "description", "")
        resource_keywords = {
            "graph", "knowledge", "neo4j", "qdrant", "memory", "memory_core",
            "tool", "tools", "agent", "worker", "deployment", "config",
            "security", "auth", "sandbox", "docker", "rabbitmq", "redis",
        }
        combined = f"{title} {description}".lower()
        for keyword in resource_keywords:
            if keyword in combined:
                resources.add(keyword)
        return resources

    def _has_opposite_intent(self, goal_a: Any, goal_b: Any) -> bool:
        opposites = {
            ("create", "delete"), ("delete", "create"),
            ("add", "remove"), ("remove", "add"),
            ("enable", "disable"), ("disable", "enable"),
            ("start", "stop"), ("stop", "start"),
            ("increase", "decrease"), ("decrease", "increase"),
            ("upgrade", "downgrade"), ("downgrade", "upgrade"),
        }
        text_a = f"{getattr(goal_a, 'title', '')} {getattr(goal_a, 'description', '')}".lower()
        text_b = f"{getattr(goal_b, 'title', '')} {getattr(goal_b, 'description', '')}".lower()
        for a, b in opposites:
            if a in text_a and b in text_b:
                return True
            if b in text_a and a in text_b:
                return True
        return False


goal_conflict_detector = GoalConflictDetector()
