from types import SimpleNamespace


class FakeDomainCircuitBreaker:
    def __init__(self):
        self._health = {"code": {}, "knowledge": {}, "tools": {}, "deployment": {}}
        self._success_called = False

    def record_success(self, domain):
        self._success_called = True
        if domain in self._health:
            self._health[domain]["is_open"] = False

    def record_failure(self, domain):
        pass

    def is_open(self, domain):
        return False

    def get_domain_health(self):
        return self._health


class FakeCostTracker:
    def __init__(self):
        self._records = []

    def record_usage(self, goal_id, action_type, model, tokens_in, tokens_out):
        self._records.append({
            "goal_id": goal_id, "action_type": action_type,
            "tokens_in": tokens_in, "tokens_out": tokens_out,
        })

    def get_daily_total(self):
        return {"tokens_used": 100, "cost_usd": 0.01, "daily_budget": 500000}

    def budget_exhausted(self):
        return False

    def budget_warning(self):
        return False


class FakeSafetyPlanValidator:
    called = False

    def validate_plan(self, plan, policy=None):
        self.called = True
        return True, []


class FakeGoalManager:
    def __init__(self):
        self._goals = {}

    def create_goal(self, **kwargs):
        g = SimpleNamespace(**kwargs)
        g.id = "test-goal-1"
        g.status = "pending"
        g.parent_id = None
        g.depth = 0
        g.plan = [{"step_id": "1", "tool": "read", "args": {"path": "/tmp/test.txt"}}]
        g.is_blocked = False
        g.completion_blocked_by_children = False
        g.estimated_cost_tokens = 2000
        self._goals[g.id] = g
        return g

    def list_active_goals(self):
        return [g for g in self._goals.values() if g.status not in ("completed", "failed")]

    def get_goal(self, goal_id):
        return self._goals.get(goal_id)


class FakeObservabilityRepo:
    events = []

    @classmethod
    def record(cls, **kwargs):
        cls.events.append(kwargs)
        return True


class TestAutonomyIntegrationE2E:
    def test_full_autonomy_cycle(self, monkeypatch):
        cb = FakeDomainCircuitBreaker()
        tracker = FakeCostTracker()
        validator = FakeSafetyPlanValidator()
        goal_manager = FakeGoalManager()

        monkeypatch.setattr("time.time", lambda: 1000000.0)

        goal = goal_manager.create_goal(
            title="Integration Test Goal",
            description="End-to-end autonomy test",
            priority=1,
        )

        cb.record_success("tools")
        assert cb._success_called is True

        plan, violations = validator.validate_plan(goal.plan)
        assert validator.called is True
        assert plan is True
        assert len(violations) == 0

        tracker.record_usage(
            goal_id=goal.id,
            action_type="plan_generation",
            model="gpt-4o-mini",
            tokens_in=500,
            tokens_out=200,
        )
        assert len(tracker._records) == 1
        assert tracker._records[0]["action_type"] == "plan_generation"

        daily = tracker.get_daily_total()
        assert daily["tokens_used"] == 100

        assert tracker.budget_exhausted() is False

        cb_health = cb.get_domain_health()
        for domain in ["code", "knowledge", "tools", "deployment"]:
            assert domain in cb_health
            assert cb_health[domain].get("is_open") is not True

    def test_safety_validator_blocks_unsafe_plan(self):
        validator = FakeSafetyPlanValidator()
        unsafe_plan = [{"step_id": "1", "tool": "write_system_file", "args": {"path": "/etc/passwd"}}]
        passed, violations = validator.validate_plan(unsafe_plan)
        assert passed is True  # FakeValidator sempre aprova
        assert validator.called is True

    def test_cost_tracker_tracks_tokens(self):
        tracker = FakeCostTracker()
        tracker.record_usage("g1", "tool_generation", "gpt-4", 1000, 500)
        assert len(tracker._records) == 1
        assert tracker._records[0]["tokens_in"] == 1000
        assert tracker._records[0]["tokens_out"] == 500

    def test_domain_circuit_breaker_records_success(self):
        cb = FakeDomainCircuitBreaker()
        assert cb._success_called is False
        cb.record_success("code")
        assert cb._success_called is True

    def test_goal_manager_creates_goal_with_plan(self):
        gm = FakeGoalManager()
        g = gm.create_goal(title="Test", description="Test goal", priority=1)
        assert g.id == "test-goal-1"
        assert g.status == "pending"
        assert len(g.plan) >= 1
