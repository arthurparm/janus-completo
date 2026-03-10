import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.v1.endpoints.memory import router as memory_router
from app.services.memory_service import get_memory_service


class _DummyMemoryService:
    async def recall_by_timeframe(self, *args, **kwargs):
        return []


def test_memory_secrets_endpoint_returns_masked_items(monkeypatch):
    app = FastAPI()
    app.include_router(memory_router, prefix="/api/v1/memory")
    app.dependency_overrides[get_memory_service] = lambda: _DummyMemoryService()

    async def _fake_list_secrets(**kwargs):
        return [
            {
                "id": "sec-1",
                "secret_label": "senha do wi-fi",
                "secret_type": "password",
                "secret_scope": "network",
                "masked_value": "Ab****45",
                "memory_class": "secret",
                "retention_policy": "persistent",
                "recall_policy": "explicit_only",
                "sensitivity": "secret",
                "stability_score": 0.98,
                "active": True,
                "metadata": {"memory_class": "secret"},
            }
        ]

    monkeypatch.setattr(
        "app.api.v1.endpoints.memory.secret_memory_service.list_secrets",
        _fake_list_secrets,
    )

    client = TestClient(app)
    resp = client.get("/api/v1/memory/secrets?user_id=u1")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["secret_label"] == "senha do wi-fi"
    assert data[0]["masked_value"] == "Ab****45"
    assert data[0]["sensitivity"] == "secret"
