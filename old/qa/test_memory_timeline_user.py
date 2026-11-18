import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.memory import router as memory_router
from app.core.security.actor_context import ActorContext, AuthMethod
from app.services.memory_service import get_memory_service


class DummyMemoryService:
    async def recall_by_timeframe(self, *args, **kwargs):
        return []


class DummyPoint:
    def __init__(self, payload, score=None):
        self.payload = payload
        self.score = score


class DummyKnowledgeFacade:
    async def load_user_timeline_points(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        query: str | None,
        start_ts: int | None,
        end_ts: int | None,
        limit: int,
    ):
        assert user_id == "42"
        points = [
            DummyPoint(
                {
                    "content": "older",
                    "ts_ms": 1000,
                    "metadata": {"timestamp": 1000, "conversation_id": "c-1"},
                }
            ),
            DummyPoint(
                {
                    "content": "newer",
                    "ts_ms": 2000,
                    "metadata": {"timestamp": 2000, "conversation_id": "c-2"},
                }
            ),
        ]
        if conversation_id:
            points = [
                point
                for point in points
                if (point.payload.get("metadata") or {}).get("conversation_id") == conversation_id
            ]
        return points[:limit]


@pytest.fixture()
def client(monkeypatch):
    app = FastAPI()

    @app.middleware("http")
    async def bind_authenticated_actor(request, call_next):
        request.state.actor_context = ActorContext.authenticated(
            actor_id="42",
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="test-actor",
            issuer="https://test-idp.invalid",
            subject="42",
        )
        return await call_next(request)

    app.include_router(memory_router, prefix="/api/v1/memory")
    app.dependency_overrides[get_memory_service] = lambda: DummyMemoryService()
    app.state.knowledge_facade = DummyKnowledgeFacade()

    return TestClient(app)


def test_memory_timeline_sorted(client):
    resp = client.get("/api/v1/memory/timeline?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["content"] == "newer"
    assert data[0]["ts_ms"] == 2000


def test_memory_timeline_filters_by_conversation_id(client):
    resp = client.get("/api/v1/memory/timeline?conversation_id=c-1&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"] == "older"
