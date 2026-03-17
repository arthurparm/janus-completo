import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.memory import router as memory_router
from app.services.memory_service import get_memory_service


class DummyMemoryService:
    async def recall_by_timeframe(self, *args, **kwargs):
        return []


class DummyPoint:
    def __init__(self, payload, score=None):
        self.payload = payload
        self.score = score


class DummyClient:
    async def scroll(self, *args, **kwargs):
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
        return points, None

    async def query_points(self, *args, **kwargs):
        return type("Res", (), {"points": []})()


@pytest.fixture()
def client(monkeypatch):
    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1/memory")
    app.dependency_overrides[get_memory_service] = lambda: DummyMemoryService()

    import app.api.v1.endpoints.memory as memory_module

    async def _fake_collection(name: str, *args, **kwargs):
        return name

    monkeypatch.setattr(memory_module, "aget_or_create_collection", _fake_collection)
    monkeypatch.setattr(memory_module, "get_async_qdrant_client", lambda: DummyClient())

    return TestClient(app)


def test_user_memory_timeline_sorted(client):
    resp = client.get("/api/v1/memory/timeline?user_id=u1&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["content"] == "newer"
    assert data[0]["ts_ms"] == 2000


def test_user_memory_timeline_filters_by_conversation_id(client):
    resp = client.get("/api/v1/memory/timeline?user_id=u1&conversation_id=c-1&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"] == "older"
