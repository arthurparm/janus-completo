from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import app.core.security.request_guard as request_guard
from app.api.v1.endpoints.workspace import router as workspace_router
from app.services.collaboration_service import get_collaboration_service


class _CollabStub:
    def add_artifact(self, **kwargs):
        return {"ok": True, **kwargs}

    def get_artifact(self, key: str):
        return {"key": key}

    def send_message(self, from_agent: str, to_agent: str, content: str):
        return {"from": from_agent, "to": to_agent, "content": content}

    def get_messages_for(self, agent_id: str):
        return [{"agent_id": agent_id, "content": "hi"}]

    def shutdown_system(self):
        return None


def _build_client(monkeypatch, admin_ids: set[int] | None = None) -> TestClient:
    admin_ids = admin_ids or set()
    app = FastAPI()
    app.include_router(workspace_router, prefix="/api/v1")
    app.dependency_overrides[get_collaboration_service] = lambda: _CollabStub()

    class _Repo:
        def is_admin(self, user_id: int) -> bool:
            return user_id in admin_ids

    monkeypatch.setattr(request_guard, "UserRepository", lambda: _Repo())

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_workspace_requires_authenticated_actor(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.post(
        "/api/v1/collaboration/workspace/artifacts/add",
        json={"key": "a", "value": {"v": 1}, "author": "x"},
    )
    assert response.status_code == 401


def test_workspace_add_artifact_allows_authenticated_actor(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.post(
        "/api/v1/collaboration/workspace/artifacts/add",
        json={"key": "a", "value": {"v": 1}, "author": "x"},
        headers={"X-Actor-User-Id": "10"},
    )
    assert response.status_code == 200


def test_workspace_shutdown_requires_admin(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={99})
    response = client.post(
        "/api/v1/collaboration/system/shutdown",
        headers={"X-Actor-User-Id": "10"},
    )
    assert response.status_code == 403


def test_workspace_shutdown_allows_admin(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={10})
    response = client.post(
        "/api/v1/collaboration/system/shutdown",
        headers={"X-Actor-User-Id": "10"},
    )
    assert response.status_code == 200
