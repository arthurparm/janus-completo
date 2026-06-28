import pytest
from app.core.infrastructure.auth import create_token
from httpx import ASGITransport, AsyncClient


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_token(user_id, expires_in=3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def async_client():
    from app.main import app
    from app.repositories.user_repository import UserRepository
    from app.services.observability_service import get_observability_service

    original_is_admin = UserRepository.is_admin
    original_has_role = UserRepository.has_role
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

    UserRepository.is_admin = lambda self, uid: str(uid) == "99"
    UserRepository.has_role = lambda self, uid, role_name: False
    app.dependency_overrides[get_observability_service] = lambda: DummyObservabilityService()

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    UserRepository.is_admin = original_is_admin
    UserRepository.has_role = original_has_role
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

    async def test_returns_admin_summary_payload(self, async_client):
        resp = await async_client.get(
            "/api/v1/observability/pending-actions/legacy-residue?limit=5",
            headers=_auth_headers(99),
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["total_without_owner"] == 2
        assert payload["pending_without_owner"] == 1
        assert payload["legacy_runtime_fallback_enabled"] is False
        assert payload["items"][0]["conversation_id"] == "conv-legacy-1"
