from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.v1.endpoints.collaboration import router as collaboration_router
from app.services.collaboration_service import get_collaboration_service


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


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(collaboration_router, prefix="/api/v1/collaboration")
    app.dependency_overrides[get_collaboration_service] = lambda: _CollabStub()

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_workspace_status_requires_authenticated_actor():
    client = _build_client()
    response = client.get("/api/v1/collaboration/workspace/status")
    assert response.status_code == 401


def test_workspace_status_allows_authenticated_actor():
    client = _build_client()
    response = client.get(
        "/api/v1/collaboration/workspace/status",
        headers={"X-Actor-User-Id": "10"},
    )
    assert response.status_code == 200
