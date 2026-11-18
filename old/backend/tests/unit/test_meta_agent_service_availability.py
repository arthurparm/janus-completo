import asyncio
from typing import NoReturn

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.exception_handlers import add_exception_handlers
from app.api.v1.endpoints.meta_agent import router as meta_agent_router
from app.services.meta_agent_service import (
    MetaAgentService,
    MetaAgentUnavailableError,
    get_meta_agent_service,
)


def _unavailable_agent_factory() -> NoReturn:
    raise ImportError("optional meta-agent dependency missing")


def test_health_reports_unavailable_without_fabricating_a_stub() -> None:
    service = MetaAgentService(agent_factory=_unavailable_agent_factory)

    health = service.get_health_status()

    assert health == {
        "status": "unavailable",
        "reason_code": "META_AGENT_DEPENDENCY_UNAVAILABLE",
        "agent_id": None,
        "executor_initialized": False,
        "tools_count": 0,
        "cycles_executed": 0,
    }


def test_analysis_fails_explicitly_when_real_agent_is_unavailable() -> None:
    service = MetaAgentService(agent_factory=_unavailable_agent_factory)

    with pytest.raises(MetaAgentUnavailableError, match="dependencies are unavailable"):
        asyncio.run(service.run_analysis_cycle())


def test_analysis_endpoint_returns_503_when_real_agent_is_unavailable() -> None:
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(meta_agent_router, prefix="/api/v1/meta-agent")
    app.dependency_overrides[get_meta_agent_service] = lambda: MetaAgentService(
        agent_factory=_unavailable_agent_factory
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/meta-agent/analyze")

    assert response.status_code == 503
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"
