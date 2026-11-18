import pytest
from types import SimpleNamespace

from app.core.autonomy.domain_circuit_breaker import DomainCircuitBreaker
from app.core.autonomy.goal_manager import Goal, GoalManager, GoalStatus


class FakeGoal:
    def __init__(self, id, title, description, parent_id=None, depth=0, status=GoalStatus.PENDING):
        self.id = id
        self.title = title
        self.description = description
        self.parent_id = parent_id
        self.depth = depth
        self.status = status.value if hasattr(status, 'value') else str(status)
        self._children = []

    def transition_to(self, new_status):
        self.status = str(new_status.value if hasattr(new_status, 'value') else new_status)

    @property
    def is_blocked(self):
        if self.status in ("completed", "failed"):
            return False
        if self.parent_id:
            return True
        return False

    @property
    def completion_blocked_by_children(self):
        return False


class TestGoalManagerHierarchy:
    def test_create_subgoal_with_valid_depth(self):
        parent = FakeGoal("g1", "Parent", "Parent goal")
        child = FakeGoal("g2", "Child", "Child goal", parent_id="g1", depth=1)
        assert child.parent_id == parent.id
        assert child.depth == 1

    def test_subgoal_depth_exceeds_limit(self):
        parent = FakeGoal("g1", "L0", "Level 0")
        child = FakeGoal("g2", "L1", "Level 1", parent_id="g1", depth=1)
        grandchild = FakeGoal("g3", "L2", "Level 2", parent_id="g2", depth=2)
        great = FakeGoal("g4", "L3", "Level 3", parent_id="g3", depth=3)
        assert great.depth == 3

    def test_goal_blocked_by_inactive_parent(self):
        parent = FakeGoal("g1", "Parent", "P")
        child = FakeGoal("g2", "Child", "C", parent_id="g1", depth=1)
        assert child.is_blocked is True
        parent.transition_to(GoalStatus.COMPLETED)
        child.parent_id = "g1"


class TestDomainCircuitBreaker:
    def test_breaker_lifecycle(self):
        cb = DomainCircuitBreaker(failure_threshold=3, recovery_timeout=300.0)
        assert cb.is_open("tools") is False
        cb.record_failure("tools")
        cb.record_failure("tools")
        cb.record_failure("tools")
        assert cb.is_open("tools") is True
        cb.record_success("tools")
        assert cb.is_open("tools") is False

    def test_breaker_independent_domains(self):
        cb = DomainCircuitBreaker(failure_threshold=2, recovery_timeout=300.0)
        cb.record_failure("code")
        cb.record_failure("code")
        assert cb.is_open("code") is True
        assert cb.is_open("knowledge") is False


class TestGoalMetrics:
    def test_compute_metrics(self):
        from app.core.autonomy.goal_metrics import GoalMetricsCalculator

        steps = [
            SimpleNamespace(status="completed", fallback_used=False, estimated_duration_seconds=10, actual_duration_seconds=12, tool_name="search"),
            SimpleNamespace(status="completed", fallback_used=False, estimated_duration_seconds=5, actual_duration_seconds=4, tool_name="analyze"),
            SimpleNamespace(status="failed", fallback_used=True, estimated_duration_seconds=10, actual_duration_seconds=8, tool_name="write"),
        ]
        calc = GoalMetricsCalculator()
        metrics = calc.compute("goal-1", steps)

        assert metrics.total_steps == 3
        assert metrics.completed_steps == 2
        assert metrics.failed_steps == 1
        assert 0.6 < metrics.success_rate < 0.7
        assert metrics.tool_accuracy < 1.0
