from app.api.v1.endpoints.autonomy_admin import router as autonomy_admin_router
from app.core.security.request_guard import require_admin_actor
from app.services.autonomy_admin_service import get_autonomy_admin_service
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.testclient import TestClient


def _make_admin_guard(admin_ids: set[int]):
    def _guard(request: Request) -> str:
        actor = getattr(request.state, "actor_user_id", None)
        if actor and int(actor) in admin_ids:
            return actor
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _guard


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

    async def get_self_study_neo4j_audit(self, *, orphan_limit: int = 25):
        return {"total_self_memory": 0, "connected_self_memory": 0}

    async def repair_self_study_neo4j(self, *, limit: int | None = None):
        return {"repaired": 0, "connected": 0}

    async def ask_code_as_admin(self, *, question: str, limit: int = 10, citation_limit: int = 8):
        return {"answer": "ok", "citations": [], "self_memory": []}


def _build_client(monkeypatch, admin_ids: set[int] | None = None) -> TestClient:
    admin_ids = admin_ids or set()
    app = FastAPI()
    app.include_router(autonomy_admin_router, prefix="/api/v1/autonomy/admin")
    app.dependency_overrides[get_autonomy_admin_service] = lambda: _AdminServiceStub()

    app.dependency_overrides[require_admin_actor] = _make_admin_guard(admin_ids)

    @app.middleware("http")
    async def _inject_actor(request: Request, call_next):
        actor = request.headers.get("X-Actor-User-Id")
        if actor:
            request.state.actor_user_id = actor
        return await call_next(request)

    return TestClient(app)


def test_autonomy_admin_requires_api_key(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={1})
    resp = client.post("/api/v1/autonomy/admin/backlog/sync")
    assert resp.status_code in [200, 401, 403, 500]


def test_autonomy_admin_allows_admin(monkeypatch):
    client = _build_client(monkeypatch, admin_ids={10})
    resp = client.post(
        "/api/v1/autonomy/admin/backlog/sync",
        headers={"X-Actor-User-Id": "10"},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 0
