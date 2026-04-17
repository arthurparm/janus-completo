import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.api.v1.endpoints.users import get_user_repo, get_consent_repo
    from app.api.v1.endpoints.profiles import get_profile_repo
    
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
            
        def assign_role(self, user_id, role_name):
            return True

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

    app.dependency_overrides[get_user_repo] = lambda: DummyUserRepository()
    app.dependency_overrides[get_consent_repo] = lambda: DummyConsentRepository()
    app.dependency_overrides[get_profile_repo] = lambda: DummyProfileRepository()

    # For any endpoint using X-Actor-User-Id middleware, we will pass it
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestUsersProfilesContract:

    async def test_create_user(self, async_client):
        resp = await async_client.post("/api/v1/users/", json={"email": "new@test.com", "display_name": "New"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@test.com"
        assert resp.json()["id"] == 1

    async def test_get_user(self, async_client):
        resp = await async_client.get("/api/v1/users/{user_id}".format(user_id=1))
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    async def test_get_user_not_found(self, async_client):
        resp = await async_client.get("/api/v1/users/{user_id}".format(user_id=404))
        assert resp.status_code == 404

    async def test_assign_role(self, async_client):
        resp = await async_client.post("/api/v1/users/{user_id}/roles".format(user_id=1), json={"role_name": "admin"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_add_consent(self, async_client):
        resp = await async_client.post("/api/v1/users/{user_id}/consents".format(user_id=1), json={"scope": "calendar.read", "granted": True})
        assert resp.status_code == 200
        assert resp.json()["scope"] == "calendar.read"

    async def test_list_consents(self, async_client):
        resp = await async_client.get("/api/v1/users/{user_id}/consents".format(user_id=1))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["scope"] == "marketing"

    async def test_revoke_consent(self, async_client):
        resp = await async_client.delete("/api/v1/users/{user_id}/consents/{scope}".format(user_id=1, scope="calendar.read"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    async def test_get_profile(self, async_client):
        resp = await async_client.get("/api/v1/profiles/{user_id}".format(user_id=1))
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 1
        assert resp.json()["timezone"] == "UTC"

    async def test_get_profile_not_found(self, async_client):
        resp = await async_client.get("/api/v1/profiles/{user_id}".format(user_id=404))
        assert resp.status_code == 404

    async def test_upsert_profile(self, async_client):
        resp = await async_client.post("/api/v1/profiles/", json={
            "user_id": 1,
            "timezone": "America/Sao_Paulo",
            "language": "pt-BR"
        })
        assert resp.status_code == 200
        assert resp.json()["timezone"] == "America/Sao_Paulo"
