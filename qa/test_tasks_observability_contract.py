import pytest
from httpx import ASGITransport, AsyncClient

TASKS_QUEUE_INFO_REF = "/api/v1/tasks/queue/{queue_name}"
TASKS_QUEUE_POLICY_REF = "/api/v1/tasks/queue/{queue_name}/policy"
TASKS_QUEUE_POLICY_VALIDATE_REF = "/api/v1/tasks/queue/{queue_name}/policy/validate"
TASKS_QUEUE_POLICY_RECONCILE_REF = "/api/v1/tasks/queue/{queue_name}/policy/reconcile"
TASKS_CONSOLIDATION_REF = "/api/v1/tasks/consolidation"
TASKS_HEALTH_RABBITMQ_REF = "/api/v1/tasks/health/rabbitmq"
TASKS_OUTBOX_STATS_REF = "/api/v1/tasks/outbox/stats"
TASKS_OUTBOX_RECONCILE_REF = "/api/v1/tasks/outbox/reconcile"
OBS_REQUEST_DASHBOARD_REF = "/api/v1/observability/requests/{request_id}/dashboard"
OBS_HEALTH_SYSTEM_REF = "/api/v1/observability/health/system"
OBS_HEALTH_CHECK_ALL_REF = "/api/v1/observability/health/check-all"
OBS_HEALTH_LLM_ROUTER_REF = "/api/v1/observability/health/components/llm_router"
OBS_HEALTH_MULTI_AGENT_REF = "/api/v1/observability/health/components/multi_agent_system"
OBS_HEALTH_POISON_PILL_REF = "/api/v1/observability/health/components/poison_pill_handler"
OBS_POISON_PILLS_QUARANTINED_REF = "/api/v1/observability/poison-pills/quarantined"
OBS_POISON_PILLS_RELEASE_REF = "/api/v1/observability/poison-pills/release"
OBS_POISON_PILLS_CLEANUP_REF = "/api/v1/observability/poison-pills/cleanup"
OBS_POISON_PILLS_STATS_REF = "/api/v1/observability/poison-pills/stats"
OBS_METRICS_SUMMARY_REF = "/api/v1/observability/metrics/summary"
OBS_SLO_DOMAINS_REF = "/api/v1/observability/slo/domains"
OBS_ANOMALIES_PREDICTIVE_REF = "/api/v1/observability/anomalies/predictive"
OBS_LLM_USAGE_REF = "/api/v1/observability/llm/usage"
OBS_GRAPH_AUDIT_REF = "/api/v1/observability/graph/audit"
OBS_GRAPH_QUARANTINE_REF = "/api/v1/observability/graph/quarantine"
OBS_GRAPH_QUARANTINE_PROMOTE_REF = "/api/v1/observability/graph/quarantine/promote"
OBS_USER_SUMMARY_REF = "/api/v1/observability/user_summary"
OBS_AUDIT_EVENTS_REF = "/api/v1/observability/audit/events"
OBS_ERRORS_TAXONOMY_REF = "/api/v1/observability/errors/taxonomy"
OBS_AUDIT_EXPORT_REF = "/api/v1/observability/audit/export"
OBS_METRICS_USER_REF = "/api/v1/observability/metrics/user"
OBS_ACTIVITY_USER_REF = "/api/v1/observability/activity/user"
OBS_METRICS_UX_REF = "/api/v1/observability/metrics/ux"


@pytest.fixture
def async_client():
    from app.main import app
    from app.services.observability_service import get_observability_service
    from app.services.task_service import get_task_service

    class DummyTaskService:
        async def create_consolidation_task(self, **_kwargs):
            return "task_1"

        async def get_queue_details(self, queue_name: str):
            return {"name": queue_name, "messages": 1, "consumers": 1}

        async def get_queue_policy(self, queue_name: str):
            return {
                "name": queue_name,
                "durable": True,
                "messages": 1,
                "consumers": 1,
                "arguments": {"x-message-ttl": 1000},
            }

        async def validate_queue_policy(self, queue_name: str):
            return {"status": "ok", "message": "valid", "details": {"queue": queue_name}}

        async def reconcile_queue_policy(self, queue_name: str, force_delete: bool = True):
            return {
                "status": "ok",
                "message": "reconciled",
                "details": {"queue": queue_name, "force_delete": force_delete},
            }

        async def check_broker_health(self):
            return True

    class DummyObservabilityService:
        async def get_system_health(self):
            return {"status": "healthy"}

        async def check_all_components(self):
            return {"ok": {"status": "healthy"}}

        async def get_llm_router_health(self):
            return {"status": "healthy"}

        async def get_multi_agent_system_health(self):
            return {"status": "healthy"}

        async def get_poison_pill_handler_health(self):
            return {"status": "healthy"}

        def get_quarantined_messages(self, queue: str | None = None):
            class FailureRecord:
                failure_count = 1

            class Msg:
                def __init__(self, q: str):
                    self.message_id = "m1"
                    self.queue = q
                    self.reason = "r"
                    self.failure_record = FailureRecord()

                    class T:
                        @staticmethod
                        def isoformat():
                            return "2023-01-01T00:00:00"

                    self.quarantined_at = T()

            return [Msg(queue or "q")]

        def release_from_quarantine(self, message_id: str, allow_retry: bool):
            class Msg:
                def __init__(self, mid: str):
                    self.message_id = mid

            return Msg(message_id)

        def cleanup_expired_quarantine(self):
            return {"status": "ok"}

        def get_poison_pill_stats(self, queue: str | None = None):
            return {"queue": queue, "total": 0}

        def get_metrics_summary(self):
            return {"status": "ok"}

        async def get_domain_slo_report(self, window_minutes: int | None = None, min_events: int | None = None):
            return {"status": "ok", "domains": [], "active_alerts": []}

        async def get_predictive_anomaly_report(
            self,
            window_hours: int | None = None,
            bucket_minutes: int | None = None,
            min_events: int | None = None,
        ):
            return {"status": "ok", "anomalies": []}

        def get_llm_usage_summary(self, start_ts: float | None, end_ts: float | None):
            return {"status": "ok", "providers": []}

        async def get_graph_audit_report(self):
            return {"quarantine_count": 0, "mentions_count": 0}

        async def get_graph_quarantine_items(self, limit: int):
            return []

        async def promote_quarantine_item(self, node_id: int):
            return {"status": "ok", "node_id": node_id}

        def get_request_pipeline_dashboard(self, request_id: str, limit: int, include_details: bool):
            return {
                "found": True,
                "request_id": request_id,
                "summary": {"total_events": 1},
                "events": [] if not include_details else [{"id": 1}],
            }

        def get_audit_events(self, *args, **kwargs):
            return []

        def get_audit_events_count(self, *args, **kwargs):
            return 0

        async def get_user_metrics(self, user_id: str | None = None):
            return {
                "conversations": 0,
                "messages": 0,
                "approx_in_tokens": 0,
                "approx_out_tokens": 0,
                "vector_points": 0,
            }

        def get_user_activity(self, user_id: str | None = None):
            return {"autonomy_runs": 0, "autonomy_steps": 0, "avg_step_duration_seconds": 0.0}

    app.dependency_overrides[get_task_service] = lambda: DummyTaskService()
    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()
    original_outbox = getattr(app.state, "outbox_service", None)

    class DummyOutbox:
        def get_stats(self):
            return {"pending": 0, "retry": 0, "processing": 0, "sent": 0, "dead": 0}

        async def reconcile(self, limit: int, requeue_dead: bool):
            return {
                "requeued_dead": 0,
                "dispatch": {},
                "stats": self.get_stats(),
            }

    app.state.outbox_service = DummyOutbox()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    app.dependency_overrides.clear()
    if original_outbox is not None:
        app.state.outbox_service = original_outbox
    elif hasattr(app.state, "outbox_service"):
        delattr(app.state, "outbox_service")


@pytest.mark.asyncio
class TestTasksContract:
    async def test_consolidation_task(self, async_client):
        resp = await async_client.post("/api/v1/tasks/consolidation", json={"mode": "batch"})
        assert resp.status_code == 200

    async def test_queue_info(self, async_client):
        resp = await async_client.get("/api/v1/tasks/queue/q1")
        assert resp.status_code == 200

    async def test_queue_policy(self, async_client):
        resp = await async_client.get("/api/v1/tasks/queue/q1/policy")
        assert resp.status_code == 200

    async def test_queue_policy_validate(self, async_client):
        resp = await async_client.get("/api/v1/tasks/queue/q1/policy/validate")
        assert resp.status_code == 200

    async def test_queue_policy_reconcile(self, async_client):
        resp = await async_client.post(
            "/api/v1/tasks/queue/q1/policy/reconcile",
            json={"force_delete": True},
        )
        assert resp.status_code == 200

    async def test_rabbitmq_health(self, async_client):
        resp = await async_client.get("/api/v1/tasks/health/rabbitmq")
        assert resp.status_code == 200

    async def test_outbox_stats(self, async_client):
        resp = await async_client.get("/api/v1/tasks/outbox/stats")
        assert resp.status_code == 200

    async def test_outbox_reconcile(self, async_client):
        resp = await async_client.post(
            "/api/v1/tasks/outbox/reconcile",
            json={"limit": 1, "requeue_dead": True},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestObservabilityDashboardContract:
    async def test_request_dashboard(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/requests/req_1/dashboard?limit=10&include_details=false"
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestObservabilityContract:
    async def test_health_system(self, async_client):
        resp = await async_client.get("/api/v1/observability/health/system")
        assert resp.status_code == 200

    async def test_health_check_all(self, async_client):
        resp = await async_client.post("/api/v1/observability/health/check-all")
        assert resp.status_code == 200

    async def test_health_llm_router(self, async_client):
        resp = await async_client.get("/api/v1/observability/health/components/llm_router")
        assert resp.status_code == 200

    async def test_health_multi_agent(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/health/components/multi_agent_system"
        )
        assert resp.status_code == 200

    async def test_health_poison_pill_handler(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/health/components/poison_pill_handler"
        )
        assert resp.status_code == 200

    async def test_poison_pills_quarantined(self, async_client):
        resp = await async_client.get("/api/v1/observability/poison-pills/quarantined")
        assert resp.status_code == 200

    async def test_poison_pills_release(self, async_client):
        resp = await async_client.post(
            "/api/v1/observability/poison-pills/release",
            json={"message_id": "m1", "allow_retry": False},
        )
        assert resp.status_code == 200

    async def test_poison_pills_cleanup(self, async_client):
        resp = await async_client.post("/api/v1/observability/poison-pills/cleanup")
        assert resp.status_code == 200

    async def test_poison_pills_stats(self, async_client):
        resp = await async_client.get("/api/v1/observability/poison-pills/stats")
        assert resp.status_code == 200

    async def test_metrics_summary(self, async_client):
        resp = await async_client.get("/api/v1/observability/metrics/summary")
        assert resp.status_code == 200

    async def test_slo_domains(self, async_client):
        resp = await async_client.get("/api/v1/observability/slo/domains")
        assert resp.status_code == 200

    async def test_predictive_anomalies(self, async_client):
        resp = await async_client.get("/api/v1/observability/anomalies/predictive")
        assert resp.status_code == 200

    async def test_llm_usage(self, async_client):
        resp = await async_client.get("/api/v1/observability/llm/usage")
        assert resp.status_code == 200

    async def test_graph_audit(self, async_client):
        resp = await async_client.get("/api/v1/observability/graph/audit")
        assert resp.status_code == 200

    async def test_graph_quarantine(self, async_client):
        resp = await async_client.get("/api/v1/observability/graph/quarantine")
        assert resp.status_code == 200

    async def test_graph_quarantine_promote(self, async_client):
        resp = await async_client.post(
            "/api/v1/observability/graph/quarantine/promote",
            json={"node_id": 1},
        )
        assert resp.status_code == 200

    async def test_user_summary(self, async_client):
        resp = await async_client.get("/api/v1/observability/user_summary")
        assert resp.status_code == 200

    async def test_audit_events(self, async_client):
        resp = await async_client.get("/api/v1/observability/audit/events")
        assert resp.status_code == 200

    async def test_errors_taxonomy(self, async_client):
        resp = await async_client.get("/api/v1/observability/errors/taxonomy")
        assert resp.status_code == 200

    async def test_audit_export(self, async_client):
        resp = await async_client.get("/api/v1/observability/audit/export?format=json")
        assert resp.status_code == 200

    async def test_metrics_user(self, async_client):
        resp = await async_client.get("/api/v1/observability/metrics/user")
        assert resp.status_code == 200

    async def test_activity_user(self, async_client):
        resp = await async_client.get("/api/v1/observability/activity/user")
        assert resp.status_code == 200

    async def test_metrics_ux(self, async_client):
        resp = await async_client.post(
            "/api/v1/observability/metrics/ux",
            json={"outcome": "ok", "timestamp": 1.0},
        )
        assert resp.status_code == 200
