from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import auth


class _FakeRepo:
    def __init__(self):
        self._next_id = 1
        self._users_by_id: dict[int, SimpleNamespace] = {}
        self._users_by_email: dict[str, int] = {}
        self._users_by_username: dict[str, int] = {}
        self._users_by_cpf_hash: dict[str, int] = {}
        self._roles: dict[int, set[str]] = {}

    def create_user(
        self,
        email: str | None,
        display_name: str | None,
        external_id: str | None = None,
        username: str | None = None,
        password_hash: str | None = None,
        cpf_hash: str | None = None,
    ):
        user_id = self._next_id
        self._next_id += 1
        user = SimpleNamespace(
            id=user_id,
            email=email,
            display_name=display_name,
            external_id=external_id,
            username=username,
            password_hash=password_hash,
            cpf_hash=cpf_hash,
            password_reset_token_hash=None,
            password_reset_expires_at=None,
        )
        self._users_by_id[user_id] = user
        if email:
            self._users_by_email[email] = user_id
        if username:
            self._users_by_username[username] = user_id
        if cpf_hash:
            self._users_by_cpf_hash[cpf_hash] = user_id
        self._roles.setdefault(user_id, set())
        return user

    def get_by_email(self, email: str):
        uid = self._users_by_email.get(email)
        return self._users_by_id.get(uid) if uid else None

    def get_by_username(self, username: str):
        uid = self._users_by_username.get(username)
        return self._users_by_id.get(uid) if uid else None

    def get_by_cpf_hash(self, cpf_hash: str):
        uid = self._users_by_cpf_hash.get(cpf_hash)
        return self._users_by_id.get(uid) if uid else None

    def list_roles(self, user_id: int) -> list[str]:
        return list(self._roles.get(user_id, set()))

    def has_role(self, user_id: int, role_name: str) -> bool:
        return role_name in self._roles.get(user_id, set())

    def assign_role(self, user_id: int, role_name: str) -> bool:
        self._roles.setdefault(user_id, set()).add(role_name)
        return True

    def has_any_admin(self) -> bool:
        return any("ADMIN" in roles for roles in self._roles.values())

    def is_admin(self, user_id: int) -> bool:
        return "ADMIN" in self._roles.get(user_id, set())


def _build_client(monkeypatch, repo: _FakeRepo, consent_store: dict[int, list[SimpleNamespace]]):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")
    app.dependency_overrides[auth.get_user_repo] = lambda: repo

    class _ConsentRepo:
        def add_consent(self, user_id: int, scope: str, granted: bool = True, expires_at=None):
            entry = SimpleNamespace(scope=scope, granted=granted, expires_at=expires_at)
            consent_store.setdefault(user_id, []).append(entry)
            return entry

        def list_consents(self, user_id: int):
            return consent_store.get(user_id, [])

    monkeypatch.setattr(auth, "ConsentRepository", lambda: _ConsentRepo())
    monkeypatch.setattr(auth.settings, "AUTH_RATE_LIMIT_ENABLED", False)
    return TestClient(app)


def test_local_register_promotes_allowlisted_cpf_to_admin(monkeypatch):
    repo = _FakeRepo()
    consent_store: dict[int, list[SimpleNamespace]] = {}
    client = _build_client(monkeypatch, repo, consent_store)
    monkeypatch.setattr(auth.settings, "AUTH_ADMIN_CPF_ALLOWLIST", ["50302427830"])

    response = client.post(
        "/api/v1/auth/local/register",
        json={
            "email": "admincpf@example.com",
            "password": "Qw!12345678",
            "username": "admincpf",
            "full_name": "Admin CPF",
            "cpf": "503.024.278-30",
            "terms": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "admin" in payload["user"]["roles"]
    assert repo.is_admin(int(payload["user"]["id"]))


def test_local_login_promotes_existing_user_by_cpf_consent(monkeypatch):
    repo = _FakeRepo()
    consent_store: dict[int, list[SimpleNamespace]] = {}
    client = _build_client(monkeypatch, repo, consent_store)
    monkeypatch.setattr(auth.settings, "AUTH_ADMIN_CPF_ALLOWLIST", ["50302427830"])

    user = repo.create_user(
        email="usercpf@example.com",
        display_name="User CPF",
        username="usercpf",
        password_hash=auth.hash_password("Strong#1234Aa"),
    )
    repo.assign_role(int(user.id), "USER")
    consent_scope = auth._cpf_hash_scope("50302427830")
    consent_store.setdefault(int(user.id), []).append(
        SimpleNamespace(scope=consent_scope, granted=True, expires_at=None)
    )

    response = client.post(
        "/api/v1/auth/local/login",
        json={"email": "usercpf@example.com", "password": "Strong#1234Aa"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "admin" in payload["user"]["roles"]
    assert repo.is_admin(int(user.id))


def test_local_register_rejects_duplicate_cpf(monkeypatch):
    repo = _FakeRepo()
    consent_store: dict[int, list[SimpleNamespace]] = {}
    client = _build_client(monkeypatch, repo, consent_store)
    monkeypatch.setattr(auth.settings, "AUTH_ADMIN_CPF_ALLOWLIST", ["50302427830"])

    first = client.post(
        "/api/v1/auth/local/register",
        json={
            "email": "first@example.com",
            "password": "Qw!12345678",
            "username": "firstuser",
            "full_name": "First User",
            "cpf": "50302427830",
            "terms": True,
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/local/register",
        json={
            "email": "second@example.com",
            "password": "Qw!12345678",
            "username": "seconduser",
            "full_name": "Second User",
            "cpf": "503.024.278-30",
            "terms": True,
        },
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "CPF already registered"


def test_local_register_rejects_invalid_cpf(monkeypatch):
    repo = _FakeRepo()
    consent_store: dict[int, list[SimpleNamespace]] = {}
    client = _build_client(monkeypatch, repo, consent_store)
    monkeypatch.setattr(auth.settings, "AUTH_ADMIN_CPF_ALLOWLIST", ["50302427830"])

    response = client.post(
        "/api/v1/auth/local/register",
        json={
            "email": "invalidcpf@example.com",
            "password": "Qw!12345678",
            "username": "invalidcpf",
            "full_name": "Invalid CPF",
            "cpf": "111.111.111-11",
            "terms": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid CPF"
