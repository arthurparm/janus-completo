from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.api.v1.endpoints import productivity
from app.core.security.actor_context import ActorContext, AuthMethod
from app.services.productivity_task_service import (
    ProductivityTaskNotFoundError,
    ProductivityTaskPersistenceError,
    ProductivityTaskSnapshot,
)
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def _client(actor_id: int = 7) -> TestClient:
    app = FastAPI()

    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def inject_actor(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.actor_context = ActorContext.authenticated(
            actor_id=actor_id,
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="productivity-task-test",
            issuer="https://test-idp.invalid",
            subject=f"user-{actor_id}",
        )
        return await call_next(request)

    app.include_router(productivity.router, prefix="/api/v1")
    return TestClient(app)


def test_task_status_is_actor_scoped_and_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _Service:
        def get_owned(self, **kwargs: object) -> ProductivityTaskSnapshot:
            captured.update(kwargs)
            return ProductivityTaskSnapshot(
                task_id="task-1",
                operation="google_calendar_add_event",
                status="succeeded",
                provider_resource_id="event-1",
                error_code=None,
                error_message=None,
                created_at=datetime(2026, 8, 14, tzinfo=UTC),
                updated_at=datetime(2026, 8, 14, tzinfo=UTC),
                started_at=datetime(2026, 8, 14, tzinfo=UTC),
                completed_at=datetime(2026, 8, 14, tzinfo=UTC),
            )

    monkeypatch.setattr(productivity, "ProductivityTaskService", _Service)
    response = _client().get("/api/v1/productivity/tasks/task-1")

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["provider_resource_id"] == "event-1"
    assert captured == {"task_id": "task-1", "owner_user_id": 7}


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ProductivityTaskNotFoundError("task-1"), 404),
        (ProductivityTaskPersistenceError("offline"), 503),
    ],
)
def test_task_status_does_not_leak_other_owners_or_database_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    class _Service:
        def get_owned(self, **_kwargs: object) -> ProductivityTaskSnapshot:
            raise error

    monkeypatch.setattr(productivity, "ProductivityTaskService", _Service)
    response = _client().get("/api/v1/productivity/tasks/task-1")

    assert response.status_code == expected_status
    assert "offline" not in response.text
