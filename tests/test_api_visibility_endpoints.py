import os
import sys
import types
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.core.tools.action_module import PermissionLevel, ToolCategory, ToolMetadata
from app.services.tool_service import get_tool_service
from app.services.observability_service import get_observability_service
from app.services.knowledge_service import get_knowledge_service
from app.services.llm_service import get_llm_service
from app.services.optimization_service import get_optimization_service


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

    async def get_multi_agent_system_health(self):
        return {"status": "ok", "details": {"active_agents": 1}}


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

    from app.api.v1.endpoints.tools import router as tools_router
    from app.api.v1.endpoints.observability import router as observability_router
    from app.api.v1.endpoints.pending_actions import router as pending_router
    from app.api.v1.endpoints.system_overview import router as system_overview_router

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


def test_system_overview_endpoint(client):
    resp = client.get("/api/v1/system/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_status" in data
    assert "workers_status" in data
    codex = next((worker for worker in data["workers_status"] if worker["id"] == "codex_worker"), None)
    assert codex is not None
    assert codex["status"] == "running"
