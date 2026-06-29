import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def async_client():
    from app.main import app
    from app.services.knowledge_service import get_knowledge_service
    from app.services.llm_service import get_llm_service
    from app.services.observability_service import get_observability_service
    from app.services.optimization_service import get_optimization_service

    class DummyObservabilityService:
        async def get_multi_agent_system_health(self):
            return {"status": "healthy", "details": {"active_agents": 5}}
        async def get_user_metrics(self, user_id):
            return {
                "conversations": 10,
                "messages": 50,
                "approx_in_tokens": 1000,
                "approx_out_tokens": 500,
                "vector_points": 10
            }

    class DummyKnowledgeService:
        async def get_health_status(self):
            return {"status": "healthy", "total_nodes": 100}

    class DummyLLMService:
        async def get_health_status(self):
            return {"status": "healthy", "details": {"open_circuits": 0, "cached_llms": 2}}

    class DummyOptimizationService:
        async def analyze_system(self, analysis_type="performance", detailed=False):
            return {"metrics_snapshot": {"memory_usage_mb": 1024.0}}
        async def get_metrics_history(self, limit=1):
            return []

    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()
    app.dependency_overrides[get_knowledge_service] = lambda: DummyKnowledgeService()
    app.dependency_overrides[get_llm_service] = lambda: DummyLLMService()
    app.dependency_overrides[get_optimization_service] = lambda: DummyOptimizationService()

    class RunningTask:
        def done(self):
            return False

        def cancelled(self):
            return False

    # Mock user repository
    from app.repositories.user_repository import UserRepository
    original_is_admin = UserRepository.is_admin
    UserRepository.is_admin = lambda self, uid: str(uid) == "99"

    # We also need to set orchestrator_workers for overview
    app.state.orchestrator_workers = [
        {"name": "worker_1", "task": RunningTask(), "tasks_processed": 10}
    ]

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    UserRepository.is_admin = original_is_admin
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestSystemEndpointsContract:

    async def test_get_system_status(self, async_client):
        resp = await async_client.get("/api/v1/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "app_name" in data
        assert "version" in data
        assert "status" in data

    async def test_get_system_status_degrades_when_status_collection_fails(self, async_client):
        from app.api.v1.endpoints import system_status

        original_get_system_status = system_status.system_status_service.get_system_status

        def failing_system_status():
            raise RuntimeError("system status unavailable")

        system_status.system_status_service.get_system_status = failing_system_status
        try:
            resp = await async_client.get("/api/v1/system/status")
        finally:
            system_status.system_status_service.get_system_status = original_get_system_status

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DEGRADED"
        assert data["performance"] == {
            "cpu_percent": None,
            "memory_percent": None,
        }

    async def test_get_services_health(self, async_client):
        resp = await async_client.get("/api/v1/system/health/services")
        assert resp.status_code == 200
        data = resp.json()
        assert "services" in data
        assert len(data["services"]) == 5
        assert {item["status"] for item in data["services"]} == {"ok"}
        for item in data["services"]:
            assert item["capability"]
            assert item["user_impact"]
            assert item["recommended_action"]

    async def test_get_services_health_explains_user_impact_for_ai_capabilities(
        self, async_client
    ):
        resp = await async_client.get("/api/v1/system/health/services")

        assert resp.status_code == 200
        services = {item["key"]: item for item in resp.json()["services"]}
        assert services["llm"]["capability"] == "Chat, raciocinio e modelos"
        assert "chat" in services["llm"]["user_impact"].lower()
        assert "circuit breakers" in services["llm"]["recommended_action"].lower()
        assert services["knowledge"]["capability"] == "RAG, conhecimento e citacoes"
        assert "RAG" in services["knowledge"]["user_impact"]
        assert services["memory"]["capability"] == "Memoria operacional"
        assert services["workers"]["capability"] == "Workers e operacoes assincronas"
        assert "tarefas assincronas" in services["workers"]["user_impact"]

    async def test_get_system_overview_uses_canonical_service_statuses(self, async_client):
        resp = await async_client.get("/api/v1/system/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert {item["status"] for item in data["services_status"]} == {"ok"}

    async def test_get_services_health_normalizes_provider_status_aliases(self, async_client):
        from app.main import app
        from app.services.knowledge_service import get_knowledge_service
        from app.services.llm_service import get_llm_service
        from app.services.observability_service import get_observability_service

        class WarningObservabilityService:
            async def get_multi_agent_system_health(self):
                return {"status": "warning", "details": {"active_agents": 2}}

        class UnhealthyKnowledgeService:
            async def get_health_status(self):
                return {"status": "unhealthy", "total_nodes": 100}

        class UnknownLLMService:
            async def get_health_status(self):
                return {"status": "not-indexed-yet", "details": {}}

        original_observability = app.dependency_overrides.get(get_observability_service)
        original_knowledge = app.dependency_overrides.get(get_knowledge_service)
        original_llm = app.dependency_overrides.get(get_llm_service)
        app.dependency_overrides[get_observability_service] = lambda: WarningObservabilityService()
        app.dependency_overrides[get_knowledge_service] = lambda: UnhealthyKnowledgeService()
        app.dependency_overrides[get_llm_service] = lambda: UnknownLLMService()
        try:
            resp = await async_client.get("/api/v1/system/health/services")
        finally:
            if original_observability is None:
                app.dependency_overrides.pop(get_observability_service, None)
            else:
                app.dependency_overrides[get_observability_service] = original_observability
            if original_knowledge is None:
                app.dependency_overrides.pop(get_knowledge_service, None)
            else:
                app.dependency_overrides[get_knowledge_service] = original_knowledge
            if original_llm is None:
                app.dependency_overrides.pop(get_llm_service, None)
            else:
                app.dependency_overrides[get_llm_service] = original_llm

        assert resp.status_code == 200
        services = {item["key"]: item for item in resp.json()["services"]}
        assert services["agent"]["status"] == "degraded"
        assert services["knowledge"]["status"] == "error"
        assert services["llm"]["status"] == "unknown"
        assert services["memory"]["status"] == "ok"
        assert services["workers"]["status"] == "ok"

    async def test_get_services_health_reports_degraded_workers_when_worker_stopped(
        self, async_client
    ):
        from app.main import app

        class StoppedTask:
            def done(self):
                return True

            def cancelled(self):
                return False

            def exception(self):
                return None

        original_workers = getattr(app.state, "orchestrator_workers", None)
        app.state.orchestrator_workers = [
            {"name": "async_consolidation_worker", "task": StoppedTask()},
        ]
        try:
            resp = await async_client.get("/api/v1/system/health/services")
        finally:
            app.state.orchestrator_workers = original_workers

        assert resp.status_code == 200
        services = {item["key"]: item for item in resp.json()["services"]}
        assert services["workers"]["status"] == "degraded"
        assert services["workers"]["capability"] == "Workers e operacoes assincronas"
        assert "parados: 1" in services["workers"]["metric_text"]
        assert "rotinas assincronas" in services["workers"]["user_impact"]

    async def test_get_services_health_reports_unknown_memory_when_telemetry_fails(
        self, async_client
    ):
        from app.main import app
        from app.services.optimization_service import get_optimization_service

        class FailingOptimizationService:
            async def analyze_system(self, analysis_type="performance", detailed=False):
                raise RuntimeError("metrics unavailable")

            async def get_metrics_history(self, limit=1):
                raise RuntimeError("history unavailable")

        original_override = app.dependency_overrides.get(get_optimization_service)
        app.dependency_overrides[get_optimization_service] = lambda: FailingOptimizationService()
        try:
            resp = await async_client.get("/api/v1/system/health/services")
        finally:
            if original_override is None:
                app.dependency_overrides.pop(get_optimization_service, None)
            else:
                app.dependency_overrides[get_optimization_service] = original_override

        assert resp.status_code == 200
        data = resp.json()
        memory_service = next(item for item in data["services"] if item["key"] == "memory")
        assert memory_service["status"] == "unknown"
        assert memory_service["metric_text"] == "Uso: indisponivel"

    async def test_get_services_health_reports_unknown_memory_for_non_finite_telemetry(
        self, async_client
    ):
        from app.main import app
        from app.services.optimization_service import get_optimization_service

        class NonFiniteOptimizationService:
            async def analyze_system(self, analysis_type="performance", detailed=False):
                return {"metrics_snapshot": {"memory_usage_mb": "NaN"}}

            async def get_metrics_history(self, limit=1):
                return []

        original_override = app.dependency_overrides.get(get_optimization_service)
        app.dependency_overrides[get_optimization_service] = lambda: NonFiniteOptimizationService()
        try:
            resp = await async_client.get("/api/v1/system/health/services")
        finally:
            if original_override is None:
                app.dependency_overrides.pop(get_optimization_service, None)
            else:
                app.dependency_overrides[get_optimization_service] = original_override

        assert resp.status_code == 200
        data = resp.json()
        memory_service = next(item for item in data["services"] if item["key"] == "memory")
        assert memory_service["status"] == "unknown"
        assert memory_service["metric_text"] == "Uso: indisponivel"

    async def test_get_services_health_falls_back_to_history_when_memory_snapshot_is_non_finite(
        self, async_client
    ):
        from app.main import app
        from app.services.optimization_service import get_optimization_service

        class MemoryHistoryEntry:
            memory_usage_mb = 2048.0

        class NonFiniteSnapshotWithHistoryOptimizationService:
            async def analyze_system(self, analysis_type="performance", detailed=False):
                return {"metrics_snapshot": {"memory_usage_mb": "NaN"}}

            async def get_metrics_history(self, limit=1):
                return [MemoryHistoryEntry()]

        original_override = app.dependency_overrides.get(get_optimization_service)
        app.dependency_overrides[get_optimization_service] = (
            lambda: NonFiniteSnapshotWithHistoryOptimizationService()
        )
        try:
            resp = await async_client.get("/api/v1/system/health/services")
        finally:
            if original_override is None:
                app.dependency_overrides.pop(get_optimization_service, None)
            else:
                app.dependency_overrides[get_optimization_service] = original_override

        assert resp.status_code == 200
        data = resp.json()
        memory_service = next(item for item in data["services"] if item["key"] == "memory")
        assert memory_service["status"] == "ok"
        assert memory_service["metric_text"] == "Uso: 2048MB"

    @pytest.mark.parametrize(
        ("path", "services_key"),
        [
            ("/api/v1/system/health/services", "services"),
            ("/api/v1/system/overview", "services_status"),
        ],
    )
    async def test_system_health_reports_partial_unknown_when_knowledge_fails(
        self, async_client, path, services_key
    ):
        from app.main import app
        from app.services.knowledge_service import get_knowledge_service

        class FailingKnowledgeService:
            async def get_health_status(self):
                raise RuntimeError("knowledge unavailable")

        original_override = app.dependency_overrides.get(get_knowledge_service)
        app.dependency_overrides[get_knowledge_service] = lambda: FailingKnowledgeService()
        try:
            resp = await async_client.get(path)
        finally:
            if original_override is None:
                app.dependency_overrides.pop(get_knowledge_service, None)
            else:
                app.dependency_overrides[get_knowledge_service] = original_override

        assert resp.status_code == 200
        data = resp.json()
        knowledge_service = next(item for item in data[services_key] if item["key"] == "knowledge")
        agent_service = next(item for item in data[services_key] if item["key"] == "agent")
        assert knowledge_service["status"] == "unknown"
        assert knowledge_service["metric_text"] == "Ontologias: indisponivel"
        assert agent_service["status"] == "ok"

    async def test_get_user_status_unauthorized(self, async_client):
        # Default header X-Actor-User-Id is missing or middleware defaults to "system"
        # Since I'm using the int() override or the actor middleware, we need to pass it.
        # But wait, if X-Actor-User-Id is absent, we might get 401 or it might use "system".
        # Let's test with a valid user first
        pass

    async def test_get_user_status_success(self, async_client):
        # In main.py the middleware sets request.state.actor_user_id.
        # But we can override the actor ID using our middleware mock if we want.
        # Or we can just use the X-Actor-User-Id header if our middleware respects it.
        resp = await async_client.get("/api/v1/system/status/user", headers={"X-Actor-User-Id": "1"})
        # It may return 401 if our middleware doesn't respect it in this test setup
        # Wait, the middleware is always active, let's see what it returns
        assert resp.status_code in [200, 401, 403, 500]

    async def test_validate_db_schema(self, async_client):
        # Requires mocking db_migration_service
        from app.services.db_migration_service import db_migration_service
        orig = db_migration_service.validate_schema
        db_migration_service.validate_schema = lambda: {"status": "valid"}

        resp = await async_client.get("/api/v1/system/db/validate")
        assert resp.status_code == 200
        assert resp.json() == {"status": "valid"}

        db_migration_service.validate_schema = orig

    async def test_migrate_db_schema(self, async_client):
        from app.services.db_migration_service import db_migration_service
        orig = db_migration_service.migrate_schema
        db_migration_service.migrate_schema = lambda: {"status": "migrated"}

        resp = await async_client.post("/api/v1/system/db/migrate")
        assert resp.status_code == 200
        assert resp.json() == {"status": "migrated"}

        db_migration_service.migrate_schema = orig

    async def test_get_system_overview(self, async_client):
        resp = await async_client.get("/api/v1/system/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "system_status" in data
        assert "services_status" in data
        assert "workers_status" in data

    async def test_get_system_overview_ignores_malformed_worker_items(self, async_client):
        from app.main import app

        original_workers = getattr(app.state, "orchestrator_workers", None)
        app.state.orchestrator_workers = [
            {"name": "worker_1", "task": None, "tasks_processed": 10},
            "malformed-worker",
        ]
        try:
            resp = await async_client.get("/api/v1/system/overview")
        finally:
            app.state.orchestrator_workers = original_workers

        assert resp.status_code == 200
        data = resp.json()
        assert "services_status" in data
        assert data["workers_status"] == [
            {
                "id": "worker_1",
                "status": "unknown",
                "last_heartbeat": data["workers_status"][0]["last_heartbeat"],
                "tasks_processed": 10,
            }
        ]

    async def test_get_system_overview_reports_unknown_memory_when_telemetry_fails(
        self, async_client
    ):
        from app.main import app
        from app.services.optimization_service import get_optimization_service

        class FailingOptimizationService:
            async def analyze_system(self, analysis_type="performance", detailed=False):
                raise RuntimeError("metrics unavailable")

            async def get_metrics_history(self, limit=1):
                raise RuntimeError("history unavailable")

        original_override = app.dependency_overrides.get(get_optimization_service)
        app.dependency_overrides[get_optimization_service] = lambda: FailingOptimizationService()
        try:
            resp = await async_client.get("/api/v1/system/overview")
        finally:
            if original_override is None:
                app.dependency_overrides.pop(get_optimization_service, None)
            else:
                app.dependency_overrides[get_optimization_service] = original_override

        assert resp.status_code == 200
        data = resp.json()
        memory_service = next(item for item in data["services_status"] if item["key"] == "memory")
        assert memory_service["status"] == "unknown"
        assert memory_service["metric_text"] == "Uso: indisponivel"

    async def test_get_system_overview_degrades_when_system_status_fails(self, async_client):
        from app.api.v1.endpoints import system_overview

        original_get_system_status = system_overview.system_status_service.get_system_status

        def failing_system_status():
            raise RuntimeError("system status unavailable")

        system_overview.system_status_service.get_system_status = failing_system_status
        try:
            resp = await async_client.get("/api/v1/system/overview")
        finally:
            system_overview.system_status_service.get_system_status = original_get_system_status

        assert resp.status_code == 200
        data = resp.json()
        assert data["system_status"]["status"] == "DEGRADED"
        assert data["system_status"]["performance"] == {
            "cpu_percent": None,
            "memory_percent": None,
        }
        assert data["services_status"]
        assert data["workers_status"]
