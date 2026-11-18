from app.api.v1.endpoints.workspace import router as workspace_router
from app.core.security.request_guard import require_service_actor
from app.services.collaboration_service import get_collaboration_service
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient


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


def _make_service_guard(service_ids: set[str]):
    def _guard(request: Request) -> str:
        actor = request.headers.get("X-Test-Service-Id")
        if actor and actor in service_ids:
            return str(actor)
        if not actor:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _guard


def _build_client(monkeypatch, service_ids: set[str] | None = None) -> TestClient:
    service_ids = service_ids or set()
    app = FastAPI()
    app.include_router(workspace_router, prefix="/api/v1")
    app.dependency_overrides[get_collaboration_service] = lambda: _CollabStub()
    app.dependency_overrides[require_service_actor] = _make_service_guard(service_ids)

    return TestClient(app)


def test_workspace_requires_authenticated_actor(monkeypatch):
    client = _build_client(monkeypatch)
    response = client.post(
        "/api/v1/collaboration/workspace/artifacts/add",
        json={"key": "a", "value": {"v": 1}, "author": "x"},
    )
    assert response.status_code == 401


def test_workspace_add_artifact_allows_authenticated_actor(monkeypatch):
    client = _build_client(monkeypatch, service_ids={"janus-worker"})
    response = client.post(
        "/api/v1/collaboration/workspace/artifacts/add",
        json={"key": "a", "value": {"v": 1}, "author": "x"},
        headers={"X-Test-Service-Id": "janus-worker"},
    )
    assert response.status_code == 200


def test_workspace_shutdown_requires_admin(monkeypatch):
    client = _build_client(monkeypatch, service_ids={"janus-admin-facade"})
    response = client.post(
        "/api/v1/collaboration/system/shutdown",
        headers={"X-Test-Service-Id": "janus-worker"},
    )
    assert response.status_code == 403


def test_workspace_shutdown_allows_admin(monkeypatch):
    client = _build_client(monkeypatch, service_ids={"janus-admin-facade"})
    response = client.post(
        "/api/v1/collaboration/system/shutdown",
        headers={"X-Test-Service-Id": "janus-admin-facade"},
    )
    assert response.status_code == 200
