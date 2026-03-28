import os
import sys
import types
from contextlib import asynccontextmanager
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.tools.action_module import PermissionLevel, ToolCategory, ToolMetadata  # noqa: E402
from app.services.knowledge_service import get_knowledge_service  # noqa: E402
from app.services.llm_service import get_llm_service  # noqa: E402
from app.services.observability_service import get_observability_service  # noqa: E402
from app.services.optimization_service import get_optimization_service  # noqa: E402
from app.services.tool_service import get_tool_service  # noqa: E402


class DummyToolService:
    def list_tools(self, category=None, permission_level=None, tags=None):
        return [
            ToolMetadata(
                name="codex_exec",
                category=ToolCategory.SYSTEM,
                description="Exec Codex",
                permission_level=PermissionLevel.WRITE,
                rate_limit_per_minute=10,
                requires_confirmation=True,
                tags=["codex"],
            ),
            ToolMetadata(
                name="codex_review",
                category=ToolCategory.SYSTEM,
                description="Review Codex",
                permission_level=PermissionLevel.READ_ONLY,
                rate_limit_per_minute=10,
                requires_confirmation=True,
                tags=["codex"],
            ),
        ]

    def get_tool_details(self, tool_name: str):
        return ToolMetadata(
            name=tool_name,
            category=ToolCategory.SYSTEM,
            description="Tool",
            permission_level=PermissionLevel.SAFE,
            rate_limit_per_minute=10,
            requires_confirmation=False,
            tags=["test"],
        )

    def get_statistics(self):
        return {
            "total_tools_registered": 2,
            "total_calls": 3,
            "successful_calls": 2,
            "success_rate": 0.667,
            "tool_usage": {
                "codex_exec": {"total": 2, "success": 1, "avg_duration": 1.2},
                "codex_review": {"total": 1, "success": 1, "avg_duration": 0.5},
            },
        }


class DummyObservabilityService:
    def get_audit_events(self, *args, **kwargs):
        return [
            {
                "id": 1,
                "user_id": 1,
                "endpoint": "tool:codex_exec",
                "action": "tool_call",
                "tool": "codex_exec",
                "status": "success",
                "latency_ms": 123,
                "trace_id": "t1",
                "created_at": 1710000000.0,
            }
        ]

    def get_audit_events_count(self, *args, **kwargs):
        return 1

    def get_request_pipeline_dashboard(self, request_id: str, limit: int = 2000, include_details: bool = False):
        timeline = [
            {
                "id": 1,
                "timestamp": 1710000000.0,
                "offset_ms": 0,
                "endpoint": "tool:codex_exec",
                "action": "tool_call",
                "tool": "codex_exec",
                "status": "success",
                "latency_ms": 123,
                "stage": "tool_call",
            }
        ]
        if include_details:
            timeline[0]["details"] = {"stage": "tool_call", "source": "test"}
        return {
            "request_id": request_id,
            "found": True,
            "summary": {
                "total_events": 1,
                "start_ts": 1710000000.0,
                "end_ts": 1710000000.0,
                "duration_ms": 0,
                "status_counts": {"success": 1},
                "endpoint_counts": {"tool:codex_exec": 1},
                "action_counts": {"tool_call": 1},
                "tool_counts": {"codex_exec": 1},
            },
            "timeline": timeline,
        }

    async def get_multi_agent_system_health(self):
        return {"status": "ok", "details": {"active_agents": 1}}

    async def get_domain_slo_report(self, window_minutes=None, min_events=None):
        return {
            "status": "ok",
            "window": {"window_minutes": window_minutes or 15},
            "domains": [
                {
                    "domain": "chat",
                    "status": "ok",
                    "sli": {"total_events": 10, "error_rate_pct": 0.0, "latency_p95_ms": 120.0},
                    "slo": {"max_error_rate_pct": 5.0, "max_p95_latency_ms": 3500.0, "min_events": 3},
                    "breaches": [],
                }
            ],
            "active_alerts": [],
        }


class DummyKnowledgeService:
    async def get_health_status(self):
        return {"status": "ok", "total_nodes": 0}


class DummyLLMService:
    async def get_health_status(self):
        return {"status": "ok", "details": {"open_circuits": 0, "cached_llms": 1}}


class DummyOptimizationService:
    async def analyze_system(self, *args, **kwargs):
        return {"metrics_snapshot": {"memory_usage_mb": 256}}

    async def get_metrics_history(self, *args, **kwargs):
        return []


class DummyTask:
    def done(self):
        return False

    def cancelled(self):
        return False


class DummySession:
    async def execute(self, *args, **kwargs):
        class Result:
            def fetchall(self):
                return []

        return Result()


class DummyGraphState:
    next = True


class DummyGraph:
    def get_state(self, *args, **kwargs):
        return DummyGraphState()

    def update_state(self, *args, **kwargs):
        return None

    def invoke(self, *args, **kwargs):
        return None


@asynccontextmanager
async def dummy_session_cm():
    yield DummySession()


@pytest.fixture()
def client(monkeypatch):
    app = FastAPI()

    # Stub graph orchestrator before importing pending_actions
    stub_graph_module = types.ModuleType("app.core.agents.graph_orchestrator")
    stub_graph_module.get_graph = lambda: DummyGraph()
    sys.modules["app.core.agents.graph_orchestrator"] = stub_graph_module

    from app.api.v1.endpoints.observability import router as observability_router
    from app.api.v1.endpoints.pending_actions import router as pending_router
    from app.api.v1.endpoints.system_overview import router as system_overview_router
    from app.api.v1.endpoints.tools import router as tools_router

    app.include_router(tools_router, prefix="/api/v1/tools")
    app.include_router(observability_router, prefix="/api/v1/observability")
    app.include_router(pending_router, prefix="/api/v1")
    app.include_router(system_overview_router, prefix="/api/v1/system")

    app.dependency_overrides[get_tool_service] = lambda: DummyToolService()
    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()
    app.dependency_overrides[get_knowledge_service] = lambda: DummyKnowledgeService()
    app.dependency_overrides[get_llm_service] = lambda: DummyLLMService()
    app.dependency_overrides[get_optimization_service] = lambda: DummyOptimizationService()

    # Set worker list for system overview
    app.state.orchestrator_workers = [{"name": "codex_worker", "task": DummyTask()}]

    # Patch pending actions dependencies
    import app.api.v1.endpoints.pending_actions as pending_module
    import app.db.postgres_config as postgres_module

    monkeypatch.setattr(
        postgres_module,
        "postgres_db",
        type("DB", (), {"get_session_async": dummy_session_cm})(),
    )
    monkeypatch.setattr(pending_module, "get_graph", lambda: DummyGraph())
    monkeypatch.setattr(pending_module, "_resume_graph_execution", lambda *args, **kwargs: None)

    return TestClient(app)


def test_tools_list_endpoint(client):
    resp = client.get("/api/v1/tools/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert any(tool["name"] == "codex_exec" for tool in data["tools"])


def test_tools_stats_endpoint(client):
    resp = client.get("/api/v1/tools/stats/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert "tool_usage" in data
    assert data["total_calls"] == 3


def test_audit_events_endpoint(client):
    resp = client.get("/api/v1/observability/audit/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["tool"] == "codex_exec"


def test_request_pipeline_dashboard_endpoint(client):
    resp = client.get("/api/v1/observability/requests/t1/dashboard?include_details=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "t1"
    assert data["found"] is True
    assert data["summary"]["total_events"] == 1
    assert data["timeline"][0]["details"]["source"] == "test"


def test_domain_slo_endpoint(client):
    resp = client.get("/api/v1/observability/slo/domains?window_minutes=10&min_events=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["window"]["window_minutes"] == 10
    assert data["domains"][0]["domain"] == "chat"


def test_pending_actions_list(client):
    resp = client.get("/api/v1/pending_actions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_pending_actions_approve(client):
    resp = client.post("/api/v1/pending_actions/thread-1/approve")
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "approved"


def test_pending_actions_reject(client):
    resp = client.post("/api/v1/pending_actions/thread-2/reject")
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "rejected"


def test_pending_actions_list_sql_source(client, monkeypatch):
    import app.repositories.pending_action_repository as pending_repo_module

    class DummyPendingRow:
        id = 101
        user_id = "u-1"
        tool_name = "codex_exec"
        args_json = '{"prompt":"hello"}'
        simulation_summary_json = '{"summary":"dry-run ok","final_risk_level":"medium"}'
        simulation_generated_at = datetime(2026, 2, 12, 10, 29, 0)
        simulation_version = "v1"
        status = "pending"
        created_at = datetime(2026, 2, 12, 10, 30, 0)

    class DummyPendingRepo:
        def list(self, user_id=None, status="pending", limit=50):
            assert user_id is None
            assert status == "pending"
            assert limit == 50
            return [DummyPendingRow()]

    monkeypatch.setattr(
        pending_repo_module, "PendingActionRepository", lambda *args, **kwargs: DummyPendingRepo()
    )

    resp = client.get("/api/v1/pending_actions?include_sql=true&include_graph=false")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source"] == "sql"
    assert data[0]["action_id"] == 101
    assert data[0]["tool_name"] == "codex_exec"
    assert data[0]["status"] == "pending"
    assert data[0]["simulation"]["summary"] == "dry-run ok"
    assert data[0]["simulation"]["simulation_version"] == "v1"


def test_pending_actions_list_sql_redacts_sensitive_args(client, monkeypatch):
    import app.repositories.pending_action_repository as pending_repo_module

    class DummyPendingRow:
        id = 111
        user_id = "u-redact"
        tool_name = "execute_shell"
        args_json = '{"password":"super-secret-password","email":"person@example.com","command":"echo ok"}'
        status = "pending"
        created_at = datetime(2026, 2, 12, 10, 45, 0)

    class DummyPendingRepo:
        def list(self, user_id=None, status="pending", limit=50):
            return [DummyPendingRow()]

    monkeypatch.setattr(
        pending_repo_module, "PendingActionRepository", lambda *args, **kwargs: DummyPendingRepo()
    )

    resp = client.get("/api/v1/pending_actions?include_sql=true&include_graph=false")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    safe_args = str(data[0]["args_json"])
    assert "super-secret-password" not in safe_args
    assert "person@example.com" not in safe_args


def test_pending_actions_approve_sql_action(client, monkeypatch):
    import app.repositories.pending_action_repository as pending_repo_module

    class DummyPendingRow:
        def __init__(self):
            self.id = 202
            self.user_id = "u-2"
            self.tool_name = "codex_review"
            self.args_json = '{"commit":"abc123"}'
            self.status = "pending"
            self.created_at = datetime(2026, 2, 12, 11, 0, 0)

    row = DummyPendingRow()

    class DummyPendingRepo:
        def get(self, action_id):
            if action_id == 202:
                return row
            return None

        def set_status(self, action_id, status):
            if action_id != 202:
                return None
            row.status = status
            return row

    monkeypatch.setattr(
        pending_repo_module, "PendingActionRepository", lambda *args, **kwargs: DummyPendingRepo()
    )

    resp = client.post("/api/v1/pending_actions/action/202/approve")
    assert resp.status_code == 202
    data = resp.json()
    assert data["source"] == "sql"
    assert data["action_id"] == 202
    assert data["status"] == "approved"


def test_pending_actions_reject_sql_action(client, monkeypatch):
    import app.repositories.pending_action_repository as pending_repo_module

    class DummyPendingRow:
        def __init__(self):
            self.id = 303
            self.user_id = "u-3"
            self.tool_name = "codex_exec"
            self.args_json = '{"prompt":"bye"}'
            self.status = "pending"
            self.created_at = datetime(2026, 2, 12, 12, 0, 0)

    row = DummyPendingRow()

    class DummyPendingRepo:
        def get(self, action_id):
            if action_id == 303:
                return row
            return None

        def set_status(self, action_id, status):
            if action_id != 303:
                return None
            row.status = status
            return row

    monkeypatch.setattr(
        pending_repo_module, "PendingActionRepository", lambda *args, **kwargs: DummyPendingRepo()
    )

    resp = client.post("/api/v1/pending_actions/action/303/reject")
    assert resp.status_code == 202
    data = resp.json()
    assert data["source"] == "sql"
    assert data["action_id"] == 303
    assert data["status"] == "rejected"


def test_pending_actions_approve_returns_503_when_state_backend_unavailable(client, monkeypatch):
    import app.api.v1.endpoints.pending_actions as pending_module

    async def failing_get_state(*args, **kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(pending_module, "_get_state", failing_get_state)

    resp = client.post("/api/v1/pending_actions/thread-1/approve")
    assert resp.status_code == 503
    assert "backend is unavailable" in resp.json()["detail"]


def test_pending_actions_list_returns_503_when_checkpoint_backend_unavailable(client, monkeypatch):
    import app.api.v1.endpoints.pending_actions as pending_module

    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("connection refused")

    @asynccontextmanager
    async def broken_session_cm():
        yield BrokenSession()

    monkeypatch.setattr(
        pending_module,
        "_get_session_context_manager",
        lambda *_args, **_kwargs: broken_session_cm(),
    )

    resp = client.get("/api/v1/pending_actions")
    assert resp.status_code == 503
    assert "backend is unavailable" in resp.json()["detail"]


def test_system_overview_endpoint(client):
    resp = client.get("/api/v1/system/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_status" in data
    assert "workers_status" in data
    codex = next((worker for worker in data["workers_status"] if worker["id"] == "codex_worker"), None)
    assert codex is not None
    assert codex["status"] == "running"
