import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.api.v1.endpoints.agent import get_agent_service
    from app.api.v1.endpoints.assistant import get_assistant_service
    from app.api.v1.endpoints.meta_agent import get_meta_agent_service
    from app.api.v1.endpoints.reflexion import get_reflexion_service
    from app.api.v1.endpoints.sandbox import get_sandbox_service
    from app.api.v1.endpoints.tools import get_tool_service
    
    class DummyAgentService:
        async def execute_agent(self, question, agent_type=None, **kwargs):
            if question == "fail":
                raise ValueError("Agent error")
            return {"result": "task done"}

    class DummyAssistantService:
        async def execute_request(self, user_request, risk_profile, allowlist, blocklist, max_steps, timeout_seconds, metrics):
            return {
                "request": user_request,
                "planned_steps": [],
                "transparent": [],
                "executions": [],
                "consolidated_output": "assistant reply",
                "telemetry": {}
            }

    class DummyMetaAgentService:
        async def run_analysis_cycle(self):
            class Report:
                def to_dict(self): return {"status": "analyzed"}
            return Report()
        def get_health_status(self):
            return {"status": "healthy"}
        async def start_heartbeat(self, interval):
            return True
        def stop_heartbeat(self):
            return True
        def get_latest_report(self):
            class Report:
                def to_dict(self): return {"report": "latest"}
            return Report()

    class DummyReflexionService:
        async def run_reflexion_cycle(self, task, overrides):
            if task == "fail":
                raise ValueError("Reflexion error")
            return {
                "success": True,
                "best_result": "ok",
                "best_score": 1.0,
                "iterations": 1,
                "lessons_learned": [],
                "elapsed_seconds": 1.0,
                "steps": []
            }
        def get_config(self):
            class Config:
                max_iterations = 5
                max_time_seconds = 300
                success_threshold = 0.8
            return Config()
        def get_health_status(self):
            return {"status": "healthy"}
        def reset_agent_breakers(self):
            return {"status": "reset"}

    class DummySandboxService:
        def get_capabilities(self):
            return {"capabilities": ["python", "bash"]}
        def evaluate_expression(self, expression, timeout=None, memory_limit=None):
            class Res:
                success = True
                output = "1"
                error = None
                execution_time = 1.0
                variables = {}
            return Res()
        def execute_code(self, code, context=None, timeout=None, memory_limit=None):
            class Res:
                success = True
                output = "hello"
                error = None
                execution_time = 1.0
                variables = {}
            return Res()

    class DummyToolService:
        def create_tool_from_api(self, payload):
            class ToolMeta:
                name = payload.get("name")
                description = "desc"
                class EnumVal:
                    value = "read"
                category = EnumVal()
                permission_level = EnumVal()
                rate_limit_per_minute = 10
                requires_confirmation = False
                tags = []
            return ToolMeta()
        def create_tool_from_function(self, payload):
            class ToolMeta:
                name = payload.get("name")
                description = "desc"
                class EnumVal:
                    value = "read"
                category = EnumVal()
                permission_level = EnumVal()
                rate_limit_per_minute = 10
                requires_confirmation = False
                tags = []
            return ToolMeta()
        def list_permissions(self):
            return ["read", "write"]
        def delete_tool(self, tool_name):
            if tool_name == "404":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            return True
        def get_tool_details(self, tool_name):
            if tool_name == "404":
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            class ToolMeta:
                name = tool_name
                description = "desc"
                class EnumVal:
                    value = "read"
                category = EnumVal()
                permission_level = EnumVal()
                rate_limit_per_minute = 10
                requires_confirmation = False
                tags = []
            return ToolMeta()

    app.dependency_overrides[get_agent_service] = lambda: DummyAgentService()
    app.dependency_overrides[get_assistant_service] = lambda: DummyAssistantService()
    app.dependency_overrides[get_meta_agent_service] = lambda: DummyMetaAgentService()
    app.dependency_overrides[get_reflexion_service] = lambda: DummyReflexionService()
    app.dependency_overrides[get_sandbox_service] = lambda: DummySandboxService()
    app.dependency_overrides[get_tool_service] = lambda: DummyToolService()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAgentEcosystemContract:

    # --- Agent ---
    async def test_agent_execute(self, async_client):
        resp = await async_client.post("/api/v1/agent/execute", json={"question": "test"})
        assert resp.status_code == 200

    async def test_agent_execute_error(self, async_client):
        resp = await async_client.post("/api/v1/agent/execute", json={"question": "fail"})
        assert resp.status_code in [400, 500]

    # --- Assistant ---
    async def test_assistant_execute(self, async_client):
        resp = await async_client.post("/api/v1/assistant/execute", json={"prompt": "hi"})
        assert resp.status_code == 200

    # --- Meta-Agent ---
    async def test_meta_agent_analyze(self, async_client):
        resp = await async_client.post("/api/v1/meta-agent/analyze")
        assert resp.status_code == 200

    async def test_meta_agent_health(self, async_client):
        resp = await async_client.get("/api/v1/meta-agent/health")
        assert resp.status_code == 200

    async def test_meta_agent_heartbeat_start(self, async_client):
        resp = await async_client.post("/api/v1/meta-agent/heartbeat/start", json={"interval_minutes": 60})
        assert resp.status_code == 200

    async def test_meta_agent_heartbeat_stop(self, async_client):
        resp = await async_client.post("/api/v1/meta-agent/heartbeat/stop")
        assert resp.status_code == 200

    async def test_meta_agent_report_latest(self, async_client):
        resp = await async_client.get("/api/v1/meta-agent/report/latest")
        assert resp.status_code == 200

    # --- Reflexion ---
    async def test_reflexion_execute(self, async_client):
        resp = await async_client.post("/api/v1/reflexion/execute", json={"task": "test"})
        assert resp.status_code == 200

    async def test_reflexion_config(self, async_client):
        resp = await async_client.get("/api/v1/reflexion/config")
        assert resp.status_code == 200

    async def test_reflexion_health(self, async_client):
        resp = await async_client.get("/api/v1/reflexion/health")
        assert resp.status_code == 200

    async def test_reflexion_reset_cb(self, async_client):
        resp = await async_client.post("/api/v1/reflexion/reset-circuit-breaker")
        assert resp.status_code == 200

    # --- Sandbox ---
    async def test_sandbox_capabilities(self, async_client):
        resp = await async_client.get("/api/v1/sandbox/capabilities")
        assert resp.status_code == 200

    async def test_sandbox_evaluate(self, async_client):
        resp = await async_client.post("/api/v1/sandbox/evaluate", json={"expression": "1"})
        assert resp.status_code == 200

    async def test_sandbox_execute(self, async_client):
        resp = await async_client.post("/api/v1/sandbox/execute", json={"code": "print(1)"})
        assert resp.status_code == 200

    # --- Tools ---
    async def test_tools_create_from_api(self, async_client):
        resp = await async_client.post("/api/v1/tools/create/from-api", json={"name": "test", "description": "desc", "endpoint_url": "http://api"})
        assert resp.status_code == 201

    async def test_tools_create_from_func(self, async_client):
        resp = await async_client.post("/api/v1/tools/create/from-function", json={"name": "test", "description": "desc", "code": "def execute(): pass"})
        assert resp.status_code == 201

    async def test_tools_permissions_list(self, async_client):
        resp = await async_client.get("/api/v1/tools/permissions/list")
        assert resp.status_code == 200

    async def test_tools_get_tool(self, async_client):
        _ = "/api/v1/tools/{tool_name}"
        resp = await async_client.get("/api/v1/tools/my_tool")
        assert resp.status_code == 200

    async def test_tools_get_tool_not_found(self, async_client):
        resp = await async_client.get("/api/v1/tools/404")
        assert resp.status_code == 404

    async def test_tools_delete_tool(self, async_client):
        _ = "/api/v1/tools/{tool_name}"
        resp = await async_client.delete("/api/v1/tools/my_tool")
        assert resp.status_code == 204

    async def test_tools_delete_tool_not_found(self, async_client):
        resp = await async_client.delete("/api/v1/tools/404")
        assert resp.status_code == 404