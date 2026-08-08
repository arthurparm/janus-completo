import pytest
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod
from httpx import ASGITransport, AsyncClient

from qa.auth_test_support import actor_from_test_request, issue_test_actor_token


def _auth_headers(user_id: int) -> dict[str, str]:
    token = issue_test_actor_token(user_id)
    return {"Authorization": f"Bearer {token}"}


SERVICE_HEADERS = {"Authorization": "Bearer test-service"}


@pytest.fixture
def async_client(monkeypatch):
    from app.main import app

    def actor_for_request(request):
        if request.headers.get("Authorization") == "Bearer test-service":
            return ActorContext.authenticated(
                actor_id="janus-observability",
                actor_type=ActorType.SERVICE,
                roles=("SERVICE",),
                auth_method=AuthMethod.CLIENT_CREDENTIALS,
                trace_id="test-service",
                client_id="janus-observability",
                scopes=("observability:read",),
            )
        return actor_from_test_request(request)

    monkeypatch.setattr(
        "app.core.security.containment_middleware.get_actor_context",
        actor_for_request,
    )
    from app.services.observability_service import get_observability_service

    original_override = app.dependency_overrides.get(get_observability_service)

    class DummyObservabilityService:
        def get_pending_actions_legacy_residue_summary(self, limit: int = 20):
            assert limit == 5
            return {
                "total_without_owner": 2,
                "pending_without_owner": 1,
                "sample_limit": 5,
                "legacy_runtime_fallback_enabled": False,
                "message": (
                    "Operational legacy is extinct. Historical pending_actions without persisted "
                    "owner remain blocked as administrative backlog until controlled sanitation; "
                    "new ownerless records are rejected."
                ),
                "items": [
                    {
                        "action_id": 41,
                        "status": "pending",
                        "tool_name": "tool_x",
                        "created_at": "2026-06-22T12:00:00",
                        "conversation_id": "conv-legacy-1",
                    }
                ],
            }

    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    if original_override is None:
        app.dependency_overrides.pop(get_observability_service, None)
    else:
        app.dependency_overrides[get_observability_service] = original_override


@pytest.mark.asyncio
class TestObservabilityPendingActionsLegacyResidueContract:
    async def test_requires_authentication(self, async_client):
        resp = await async_client.get("/api/v1/observability/pending-actions/legacy-residue?limit=5")
        assert resp.status_code == 401

    async def test_requires_admin(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/pending-actions/legacy-residue?limit=5",
            headers=_auth_headers(1),
        )
        assert resp.status_code == 403

    async def test_returns_service_summary_payload(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/pending-actions/legacy-residue?limit=5",
            headers=SERVICE_HEADERS,
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total_without_owner"] == 2
        assert payload["pending_without_owner"] == 1
        assert payload["legacy_runtime_fallback_enabled"] is False
        assert payload["items"][0]["conversation_id"] == "conv-legacy-1"
