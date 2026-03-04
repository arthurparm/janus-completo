from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

import app.core.security.request_guard as request_guard
from app.api.v1.endpoints.autonomy_admin import router as autonomy_admin_router
from app.services.autonomy_admin_service import get_autonomy_admin_service


class _AdminServiceStub:
    async def sync_backlog(self):
        return {
            "created": 0,
            "deduped": 0,
            "capped": 0,
            "closed": 0,
            "fallback_used_count": 0,
            "findings_total": 0,
        }

    def get_board(self, *, status=None, limit=200):
        return []

    async def run_self_study(self, **kwargs):
        return {"run_id": 1, "status": "completed"}

    def get_self_study_status(self):
        return {"last_studied_commit": None, "recent_runs": []}

    def list_self_study_runs(self, limit=20):
        return []

    async def ask_code_as_admin(self, *, question: str, limit: int = 10, citation_limit: int = 8):
        return {"answer": "ok", "citations": [], "self_memory": []}


def _build_client(monkeypatch, admin_ids: set[int] | None = None) -> TestClient:
    admin_ids = admin_ids or set()
    app = FastAPI()
    app.include_router(autonomy_admin_router, prefix="/api/v1/autonomy/admin")
    app.dependency_overrides[get_autonomy_admin_service] = lambda: _AdminServiceStub()

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


def test_autonomy_admin_requires_authentication(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={1})
    resp = client.post("/api/v1/autonomy/admin/backlog/sync")
    assert resp.status_code == 401


def test_autonomy_admin_requires_admin_role(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={99})
    resp = client.post(
        "/api/v1/autonomy/admin/backlog/sync",
        headers={"X-Actor-User-Id": "10"},
    )
    assert resp.status_code == 403


def test_autonomy_admin_allows_admin(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={10})
    resp = client.post(
        "/api/v1/autonomy/admin/backlog/sync",
        headers={"X-Actor-User-Id": "10"},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 0
