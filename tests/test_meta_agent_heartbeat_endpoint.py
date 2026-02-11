import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.api.v1.endpoints.meta_agent import router as meta_agent_router
from app.services.meta_agent_service import get_meta_agent_service


class DummyAgent:
    def __init__(self):
        self.cycle_count = 0
        self.last_report = None


class DummyMetaAgentService:
    def __init__(self):
        self._agent = DummyAgent()

    def get_heartbeat_status(self):
        # Match real service response shape
        return {
            "heartbeat_active": False,
            "total_cycles_executed": self._agent.cycle_count,
            "last_analysis": None,
        }


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(meta_agent_router, prefix="/api/v1/meta-agent")
    app.dependency_overrides[get_meta_agent_service] = lambda: DummyMetaAgentService()
    return TestClient(app)


def test_meta_agent_heartbeat_status(client):
    resp = client.get("/api/v1/meta-agent/heartbeat/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["heartbeat_active"] is False
