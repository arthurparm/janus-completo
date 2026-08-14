from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from qa.auth_test_support import actor_from_test_request, issue_test_actor_token


def _headers(user_id: int = 7) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_test_actor_token(user_id)}"}


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_external_productivity_effects_require_consent_before_queueing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.endpoints.productivity import (
        get_consent_repo,
        get_knowledge_facade,
    )
    from app.core.security import containment_middleware
    from app.core.workers import google_productivity_worker
    from app.main import app

    class _ConsentRepository:
        def __init__(self, allowed: bool) -> None:
            self.allowed = allowed

        def has_consent(self, _user_id: int, _scope: str) -> bool:
            return self.allowed

    class _Observability:
        def get_audit_events(self, *_args: object, **_kwargs: object) -> list[object]:
            return []

        def record_audit_event(self, _event: object) -> None:
            return None

    calendar_publish = AsyncMock(return_value="calendar-task")
    mail_publish = AsyncMock(return_value="mail-task")
    monkeypatch.setattr(
        google_productivity_worker,
        "publish_google_calendar_add_event",
        calendar_publish,
    )
    monkeypatch.setattr(
        google_productivity_worker,
        "publish_google_mail_send",
        mail_publish,
    )
    monkeypatch.setattr(
        containment_middleware,
        "get_actor_context",
        actor_from_test_request,
    )
    original_overrides = dict(app.dependency_overrides)
    original_observability = getattr(app.state, "observability_service", None)
    consent = _ConsentRepository(False)
    speculative_index = AsyncMock()
    app.dependency_overrides[get_consent_repo] = lambda: consent
    app.dependency_overrides[get_knowledge_facade] = lambda: SimpleNamespace(
        index_memory_event=speculative_index
    )
    app.state.observability_service = _Observability()

    calendar_payload = {
        "event": {"title": "reunião", "start_ts": 10.0, "end_ts": 20.0},
        "index": True,
    }
    mail_payload = {
        "message": {"to": "dest@example.com", "subject": "S", "body": "B"}
    }
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            denied_calendar = await client.post(
                "/api/v1/productivity/calendar/events/add",
                json=calendar_payload,
                headers=_headers(),
            )
            denied_mail = await client.post(
                "/api/v1/productivity/mail/messages/send",
                json=mail_payload,
                headers=_headers(),
            )
            consent.allowed = True
            allowed_calendar = await client.post(
                "/api/v1/productivity/calendar/events/add",
                json=calendar_payload,
                headers=_headers(),
            )
            allowed_mail = await client.post(
                "/api/v1/productivity/mail/messages/send",
                json=mail_payload,
                headers=_headers(),
            )
            calendar_publish.side_effect = (
                google_productivity_worker.ProductivityQueueUnavailableError(
                    "calendário não enfileirado"
                )
            )
            mail_publish.side_effect = (
                google_productivity_worker.ProductivityQueueUnavailableError(
                    "e-mail não enfileirado"
                )
            )
            failed_calendar = await client.post(
                "/api/v1/productivity/calendar/events/add",
                json=calendar_payload,
                headers=_headers(),
            )
            failed_mail = await client.post(
                "/api/v1/productivity/mail/messages/send",
                json=mail_payload,
                headers=_headers(),
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        if original_observability is None:
            del app.state.observability_service
        else:
            app.state.observability_service = original_observability

    assert denied_calendar.status_code == 403
    assert denied_mail.status_code == 403
    assert allowed_calendar.json() == {"status": "queued", "task_id": "calendar-task"}
    assert allowed_mail.json() == {"status": "queued", "task_id": "mail-task"}
    assert failed_calendar.status_code == 503
    assert failed_calendar.json()["detail"] == "calendário não enfileirado"
    assert failed_mail.status_code == 503
    assert failed_mail.json()["detail"] == "e-mail não enfileirado"
    assert calendar_publish.await_count == 2
    assert mail_publish.await_count == 2
    speculative_index.assert_not_awaited()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("task_type", "payload"),
    [
        ("google_calendar_add_event", {"event": {"title": "blocked"}}),
        ("google_mail_send", {"message": {"to": "blocked@example.com"}}),
    ],
)
async def test_worker_rechecks_revoked_consent_before_external_effect(
    monkeypatch: pytest.MonkeyPatch,
    task_type: str,
    payload: dict[str, object],
) -> None:
    from app.core.workers import google_productivity_worker as worker
    from app.models.schemas import TaskMessage
    from app.services.productivity_consent_service import (
        ProductivityConsentRequiredError,
    )

    class _RevokedConsentRepository:
        def has_consent(self, _user_id: int, _scope: str) -> bool:
            return False

    oauth_repository = Mock(side_effect=AssertionError("OAuth token must not be read"))
    monkeypatch.setattr(worker, "ConsentRepository", _RevokedConsentRepository)
    monkeypatch.setattr(worker, "OAuthTokenRepository", oauth_repository)
    task = TaskMessage(
        task_id="revoked-consent",
        task_type=task_type,
        payload={"user_id": 7, **payload},
        timestamp=1.0,
    )

    with pytest.raises(ProductivityConsentRequiredError):
        await worker._handle_google_productivity_task(task)

    oauth_repository.assert_not_called()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("task_type", "payload", "provider"),
    [
        ("google_calendar_add_event", {"event": {}}, "Google Calendar"),
        ("google_mail_send", {"message": {}}, "Gmail"),
    ],
)
async def test_worker_sends_missing_oauth_token_to_failure_path(
    monkeypatch: pytest.MonkeyPatch,
    task_type: str,
    payload: dict[str, object],
    provider: str,
) -> None:
    from app.core.workers import google_productivity_worker as worker
    from app.models.schemas import TaskMessage

    class _AllowedConsentRepository:
        def has_consent(self, _user_id: int, _scope: str) -> bool:
            return True

    class _MissingTokenRepository:
        def get(self, *, user_id: int, provider: str) -> None:
            return None

    monkeypatch.setattr(worker, "ConsentRepository", _AllowedConsentRepository)
    monkeypatch.setattr(worker, "OAuthTokenRepository", _MissingTokenRepository)
    task = TaskMessage(
        task_id="missing-token",
        task_type=task_type,
        payload={"user_id": 7, **payload},
        timestamp=1.0,
    )

    with pytest.raises(RuntimeError, match=provider):
        await worker._handle_google_productivity_task(task)
