from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.api.v1.endpoints import productivity
from app.core.security.actor_context import ActorContext, AuthMethod
from app.services.google_productivity_service import (
    GoogleProductivityProviderError,
    GoogleProductivityTokenUnavailableError,
)
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


class _ConsentRepository:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.checked: list[tuple[int, str]] = []

    def has_consent(self, user_id: int, scope: str) -> bool:
        self.checked.append((user_id, scope))
        return self.allowed


def _client(repo: _ConsentRepository, actor_id: int = 7) -> TestClient:
    app = FastAPI()

    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def inject_actor(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.actor_context = ActorContext.authenticated(
            actor_id=actor_id,
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="google-read-test",
            issuer="https://test-idp.invalid",
            subject=f"user-{actor_id}",
        )
        return await call_next(request)

    app.include_router(productivity.router, prefix="/api/v1")
    app.dependency_overrides[productivity.get_consent_repo] = lambda: repo
    return TestClient(app)


def test_calendar_read_requires_consent_before_google_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google_call = AsyncMock()
    monkeypatch.setattr(productivity, "list_google_calendar_events", google_call)
    repo = _ConsentRepository(allowed=False)

    response = _client(repo).get("/api/v1/productivity/calendar/events")

    assert response.status_code == 403
    assert repo.checked == [(7, "calendar.read")]
    google_call.assert_not_awaited()


def test_calendar_read_returns_normalized_actor_scoped_provider_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google_call = AsyncMock(
        return_value=[
            {
                "id": "event-1",
                "title": "Planejamento",
                "start": "2026-08-15T10:00:00Z",
                "end": "2026-08-15T11:00:00Z",
                "location": None,
                "status": "confirmed",
                "html_url": None,
            }
        ]
    )
    monkeypatch.setattr(productivity, "list_google_calendar_events", google_call)
    repo = _ConsentRepository(allowed=True)

    response = _client(repo).get(
        "/api/v1/productivity/calendar/events?max_results=10"
    )

    assert response.status_code == 200
    assert response.json()["events"][0]["id"] == "event-1"
    google_call.assert_awaited_once_with(user_id=7, max_results=10)


def test_mail_read_uses_its_own_consent_and_returns_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google_call = AsyncMock(
        return_value=[
            {
                "id": "mail-1",
                "thread_id": "thread-1",
                "sender": "sender@example.com",
                "subject": "Assunto",
                "date": "Fri, 14 Aug 2026",
                "snippet": "Trecho",
            }
        ]
    )
    monkeypatch.setattr(productivity, "list_google_mail_messages", google_call)
    repo = _ConsentRepository(allowed=True)

    response = _client(repo).get("/api/v1/productivity/mail/messages?max_results=5")

    assert response.status_code == 200
    assert repo.checked == [(7, "mail.read")]
    assert response.json()["messages"][0]["subject"] == "Assunto"
    google_call.assert_awaited_once_with(user_id=7, max_results=5)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("error", "expected_status"),
    [
        (GoogleProductivityTokenUnavailableError("connect"), 409),
        (GoogleProductivityProviderError("provider"), 502),
        (TimeoutError("deadline"), 504),
    ],
)
def test_google_read_failures_are_explicit_not_empty_success(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    monkeypatch.setattr(
        productivity,
        "list_google_calendar_events",
        AsyncMock(side_effect=error),
    )

    response = _client(_ConsentRepository(allowed=True)).get(
        "/api/v1/productivity/calendar/events"
    )

    assert response.status_code == expected_status
    assert response.json() != {"events": []}


def test_google_read_limits_are_validated_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google_call = AsyncMock()
    monkeypatch.setattr(productivity, "list_google_mail_messages", google_call)

    response = _client(_ConsentRepository(allowed=True)).get(
        "/api/v1/productivity/mail/messages?max_results=51"
    )

    assert response.status_code == 422
    google_call.assert_not_awaited()
