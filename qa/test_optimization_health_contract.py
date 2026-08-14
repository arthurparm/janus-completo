from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from qa.auth_test_support import (
    issue_test_service_token,
    service_actor_from_test_request,
)


def _service_headers(scopes: tuple[str, ...]) -> dict[str, str]:
    token = issue_test_service_token("optimization-health", scopes)
    return {"Authorization": f"Bearer {token}"}


class _OptimizationHealthService:
    async def get_system_health(self) -> dict[str, object]:
        return {
            "health_score": 0.95,
            "avg_response_time": 0.2,
            "error_rate": 0.01,
            "tool_success_rate": 0.99,
            "active_tools_count": 3,
            "failed_tools": [],
            "slow_tools": [],
        }


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_optimization_health_uses_real_typed_payload_and_current_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security import containment_middleware
    from app.main import app
    from app.services.optimization_service import get_optimization_service

    monkeypatch.setattr(
        containment_middleware,
        "get_actor_context",
        service_actor_from_test_request,
    )
    original_override = app.dependency_overrides.get(get_optimization_service)
    app.dependency_overrides[get_optimization_service] = _OptimizationHealthService

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/optimization/health",
                headers=_service_headers(("ops:execute",)),
            )
            read_only = await client.get(
                "/api/v1/optimization/health",
                headers=_service_headers(("ops:read",)),
            )
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_optimization_service, None)
        else:
            app.dependency_overrides[get_optimization_service] = original_override

    assert response.status_code == 200
    assert response.json() == {
        "health_score": 0.95,
        "avg_response_time": 0.2,
        "error_rate": 0.01,
        "tool_success_rate": 0.99,
        "active_tools_count": 3,
        "failed_tools": [],
        "slow_tools": [],
    }
    assert read_only.status_code == 403


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_optimization_health_reports_missing_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.security import containment_middleware
    from app.main import app
    from app.services.optimization_service import (
        OptimizationMetricsUnavailableError,
        get_optimization_service,
    )

    class _UnavailableHealthService(_OptimizationHealthService):
        async def get_system_health(self) -> dict[str, object]:
            raise OptimizationMetricsUnavailableError("sem amostras reais")

    monkeypatch.setattr(
        containment_middleware,
        "get_actor_context",
        service_actor_from_test_request,
    )
    original_override = app.dependency_overrides.get(get_optimization_service)
    app.dependency_overrides[get_optimization_service] = _UnavailableHealthService

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/optimization/health",
                headers=_service_headers(("ops:execute",)),
            )
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_optimization_service, None)
        else:
            app.dependency_overrides[get_optimization_service] = original_override

    assert response.status_code == 503
    assert response.json()["error_code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["detail"] == "sem amostras reais"
