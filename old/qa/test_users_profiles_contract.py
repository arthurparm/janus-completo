import pytest
from httpx import ASGITransport, AsyncClient

USER_HEADERS = {"Authorization": "Bearer test-user"}
SERVICE_HEADERS = {"Authorization": "Bearer test-service"}


@pytest.fixture
def async_client(monkeypatch):
    from app.api.v1.endpoints.profiles import get_profile_repo
    from app.api.v1.endpoints.users import get_consent_repo, get_user_repo
    from app.core.security.actor_context import ActorContext, ActorType, AuthMethod
    from app.main import app

    class DummyUser:
        def __init__(self, id, email, display_name):
            self.id = id
            self.email = email
            self.display_name = display_name
            self.status = "active"

    class DummyConsent:
        def __init__(self, scope, granted):
            self.scope = scope
            self.granted = granted
            self.created_at = None
            self.expires_at = None

    class DummyProfile:
        def __init__(self, id, user_id, timezone):
            self.id = id
            self.user_id = user_id
            self.timezone = timezone
            self.language = "en"
            self.style_prefs = "{}"

    class DummyUserRepository:
        def create_user(self, email, display_name):
            return DummyUser(1, email, display_name)

        def get_user(self, user_id):
            if str(user_id) == "404":
                return None
            return DummyUser(user_id, "test@test.com", "Test")

    class DummyConsentRepository:
        def add_consent(self, user_id, scope, granted, expires_at=None):
            return DummyConsent(scope, granted)

        def list_consents(self, user_id):
            return [DummyConsent("marketing", True)]

        def revoke_consent(self, user_id, scope):
            return True

    class DummyProfileRepository:
        def get_by_user(self, user_id):
            if str(user_id) == "404":
                return None
            return DummyProfile(1, user_id, "UTC")

        def upsert(self, user_id, timezone=None, language=None, style_prefs=None):
            return DummyProfile(1, user_id, timezone)

    def actor_context(request):
        token = str(request.headers.get("Authorization") or "").removeprefix("Bearer ")
        if token == "test-user":
            return ActorContext.authenticated(
                actor_id=1,
                roles=("USER",),
                auth_method=AuthMethod.OIDC,
                trace_id="test-user",
                issuer="https://idp.test",
                subject="user-1",
            )
        if token == "test-service":
            return ActorContext.authenticated(
                actor_id="janus-admin-facade",
                actor_type=ActorType.SERVICE,
                roles=("SERVICE",),
                auth_method=AuthMethod.CLIENT_CREDENTIALS,
                trace_id="test-service",
                client_id="janus-admin-facade",
                scopes=(
                    "identity:admin",
                    "ops:read",
                    "ops:execute",
                    "deployment:write",
                    "workers:manage",
                    "governance:write",
                    "autonomy:admin",
                    "evaluation:ingest",
                    "observability:read",
                    "tools:admin",
                ),
            )
        return None

    app.dependency_overrides[get_user_repo] = lambda: DummyUserRepository()
    app.dependency_overrides[get_consent_repo] = lambda: DummyConsentRepository()
    app.dependency_overrides[get_profile_repo] = lambda: DummyProfileRepository()
    monkeypatch.setattr(
        "app.core.security.containment_middleware.get_actor_context", actor_context
    )
    monkeypatch.setattr(
        "app.core.security.containment_middleware.record_security_denial", lambda **_: None
    )

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestUsersProfilesContract:
    async def test_service_can_create_user(self, async_client):
        response = await async_client.post(
            "/api/v1/users/",
            json={"email": "new@test.com", "display_name": "New"},
            headers=SERVICE_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "new@test.com"

    async def test_service_can_get_user_and_unknown_user_is_404(self, async_client):
        response = await async_client.get("/api/v1/users/1", headers=SERVICE_HEADERS)
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert (
            await async_client.get("/api/v1/users/404", headers=SERVICE_HEADERS)
        ).status_code == 404

    async def test_local_role_assignment_endpoint_is_absent(self, async_client):
        response = await async_client.post(
            "/api/v1/users/1/roles",
            json={"role_name": "ADMIN"},
            headers=SERVICE_HEADERS,
        )
        assert response.status_code == 404

    async def test_service_manages_user_consents(self, async_client):
        created = await async_client.post(
            "/api/v1/users/1/consents",
            json={"scope": "calendar.read", "granted": True},
            headers=SERVICE_HEADERS,
        )
        assert created.status_code == 200
        listed = await async_client.get(
            "/api/v1/users/1/consents", headers=SERVICE_HEADERS
        )
        assert listed.status_code == 200
        assert listed.json()[0]["scope"] == "marketing"
        revoked = await async_client.delete(
            "/api/v1/users/1/consents/calendar.read", headers=SERVICE_HEADERS
        )
        assert revoked.status_code == 200

    async def test_user_profile_is_self_scoped(self, async_client):
        response = await async_client.get("/api/v1/profiles/me", headers=USER_HEADERS)
        assert response.status_code == 200
        assert response.json()["user_id"] == 1
        assert (
            await async_client.get("/api/v1/profiles/404", headers=USER_HEADERS)
        ).status_code == 404

    async def test_profile_body_cannot_supply_identity(self, async_client):
        forbidden = await async_client.post(
            "/api/v1/profiles/",
            json={"user_id": 1, "timezone": "America/Sao_Paulo"},
            headers=USER_HEADERS,
        )
        assert forbidden.status_code == 400
        response = await async_client.post(
            "/api/v1/profiles/",
            json={"timezone": "America/Sao_Paulo", "language": "pt-BR"},
            headers=USER_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["timezone"] == "America/Sao_Paulo"
