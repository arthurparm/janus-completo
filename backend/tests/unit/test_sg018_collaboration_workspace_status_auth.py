from app.api.v1.endpoints.collaboration import router as collaboration_router
from app.core.security.request_guard import require_service_actor
from app.services.collaboration_service import get_collaboration_service
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient


class _CollabStub:
    def get_workspace_status(self):
        return {
            "total_artifacts": 0,
            "total_messages": 0,
            "total_tasks": 0,
            "tasks_by_status": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0,
                "blocked": 0,
            },
        }


def _build_client(service_ids: set[str] | None = None) -> TestClient:
    service_ids = service_ids or set()
    app = FastAPI()
    app.include_router(collaboration_router, prefix="/api/v1/collaboration")
    app.dependency_overrides[get_collaboration_service] = lambda: _CollabStub()

    def _service_guard(request: Request) -> str:
        actor = request.headers.get("X-Test-Service-Id")
        if actor and actor in service_ids:
            return actor
        if not actor:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    app.dependency_overrides[require_service_actor] = _service_guard

    return TestClient(app)


def test_workspace_status_requires_authenticated_actor():
    client = _build_client()
    response = client.get("/api/v1/collaboration/workspace/status")
    assert response.status_code == 401


def test_workspace_status_allows_registered_service_identity():
    client = _build_client(service_ids={"janus-worker"})
    response = client.get(
        "/api/v1/collaboration/workspace/status",
        headers={"X-Test-Service-Id": "janus-worker"},
    )
    assert response.status_code == 200


def test_workspace_status_rejects_unregistered_service_identity():
    client = _build_client(service_ids={"janus-worker"})
    response = client.get(
        "/api/v1/collaboration/workspace/status",
        headers={"X-Test-Service-Id": "unknown-service"},
    )
    assert response.status_code == 403
