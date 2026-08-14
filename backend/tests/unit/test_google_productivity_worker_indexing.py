from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.workers import google_productivity_worker as worker
from app.db.vector_store import build_deterministic_point_id
from app.models.schemas import TaskMessage


def _calendar_task() -> TaskMessage:
    return TaskMessage(
        task_id="calendar-task",
        task_type="google_calendar_add_event",
        payload={
            "user_id": 7,
            "index": True,
            "event": {
                "title": "Review",
                "start_ts": 10.0,
                "end_ts": 20.0,
                "location": "Room A",
            },
        },
        timestamp=1.0,
    )


def _mail_task() -> TaskMessage:
    return TaskMessage(
        task_id="mail-task",
        task_type="google_mail_send",
        payload={
            "user_id": 7,
            "index": False,
            "message": {
                "to": "dest@example.com",
                "subject": "Review",
                "body": "Ready",
            },
        },
        timestamp=1.0,
    )


def test_google_datetime_is_explicitly_utc() -> None:
    assert worker._google_utc_datetime(0) == "1970-01-01T00:00:00Z"


def _configure_worker_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider_error: Exception | None = None,
    index_error: Exception | None = None,
    existing_event_id: str | None = None,
) -> tuple[
    list[str],
    AsyncMock,
    list[dict[str, object]],
    list[dict[str, object]],
]:
    order: list[str] = []
    audits: list[dict[str, object]] = []
    requests: list[dict[str, object]] = []

    class _Lifecycle:
        def start_or_create(self, **_kwargs: object) -> bool:
            order.append("lifecycle_start")
            return True

        def succeed(self, **_kwargs: object) -> None:
            order.append(f"lifecycle_succeed:{_kwargs['provider_resource_id']}")

        def fail(self, **_kwargs: object) -> None:
            order.append("lifecycle_fail")

    class _ConsentRepository:
        def has_consent(self, _user_id: int, _scope: str) -> bool:
            return True

    class _TokenRepository:
        def get(self, **_kwargs: object) -> object:
            return SimpleNamespace(access_token="encrypted-at-rest")

    class _Response:
        def __init__(self, payload: object) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> object:
            return self._payload

    class _Client:
        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, *_args: object, **kwargs: object) -> _Response:
            order.append("reconcile")
            requests.append(kwargs)
            items = [{"id": existing_event_id}] if existing_event_id else []
            return _Response({"items": items})

        async def post(self, *_args: object, **kwargs: object) -> _Response:
            order.append("provider")
            requests.append(kwargs)
            if provider_error:
                raise provider_error
            return _Response({"id": "created-event"})

    async def index_memory_event(**_kwargs: object) -> None:
        order.append("index")
        if index_error:
            raise index_error

    index = AsyncMock(side_effect=index_memory_event)
    monkeypatch.setattr(worker, "ConsentRepository", _ConsentRepository)
    monkeypatch.setattr(worker, "ProductivityTaskService", _Lifecycle)
    monkeypatch.setattr(worker, "OAuthTokenRepository", _TokenRepository)
    monkeypatch.setattr(
        worker,
        "resolve_google_access_token",
        AsyncMock(return_value="access"),
    )
    monkeypatch.setattr(worker, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())
    monkeypatch.setattr(
        worker,
        "get_knowledge_facade",
        lambda: SimpleNamespace(index_memory_event=index),
    )
    monkeypatch.setattr(worker, "record_audit_event_direct", audits.append)
    return order, index, audits, requests


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_calendar_is_indexed_only_after_provider_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order, index, _audits, requests = _configure_worker_dependencies(monkeypatch)

    await worker._handle_google_productivity_task(_calendar_task())

    assert order == [
        "lifecycle_start",
        "reconcile",
        "provider",
        "index",
        "lifecycle_succeed:created-event",
    ]
    index.assert_awaited_once()
    assert index.await_args is not None
    indexed = index.await_args.kwargs
    assert indexed["point_id"] == build_deterministic_point_id(
        "google-calendar-event", 7, "calendar-task"
    )
    assert indexed["payload"]["metadata"]["origin"] == "google"
    assert indexed["payload"]["metadata"]["task_id"] == "calendar-task"
    assert indexed["payload"]["metadata"]["provider_event_id"] == "created-event"
    assert requests[0]["params"] == {
        "privateExtendedProperty": "janusTaskId=calendar-task",
        "maxResults": 1,
        "showDeleted": "false",
    }
    insert_payload = requests[1]["json"]
    assert isinstance(insert_payload, dict)
    assert insert_payload["extendedProperties"] == {
        "private": {"janusTaskId": "calendar-task"}
    }


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_provider_failure_never_creates_calendar_knowledge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://www.googleapis.com/calendar/v3/events")
    error = httpx.ConnectError("provider unavailable", request=request)
    order, index, audits, _requests = _configure_worker_dependencies(
        monkeypatch,
        provider_error=error,
    )

    with pytest.raises(httpx.ConnectError):
        await worker._handle_google_productivity_task(_calendar_task())

    assert order == ["lifecycle_start", "reconcile", "provider", "lifecycle_fail"]
    index.assert_not_awaited()
    assert any(event.get("status") == "error" for event in audits)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_index_failure_is_audited_without_replaying_confirmed_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order, index, audits, _requests = _configure_worker_dependencies(
        monkeypatch,
        index_error=RuntimeError("knowledge unavailable"),
    )

    await worker._handle_google_productivity_task(_calendar_task())

    assert order == [
        "lifecycle_start",
        "reconcile",
        "provider",
        "index",
        "lifecycle_succeed:created-event",
    ]
    index.assert_awaited_once()
    assert any(
        event.get("action") == "index_add_event" and event.get("status") == "error"
        for event in audits
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_redelivery_reconciles_existing_event_without_duplicate_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order, index, audits, _requests = _configure_worker_dependencies(
        monkeypatch,
        existing_event_id="existing-event",
    )

    await worker._handle_google_productivity_task(_calendar_task())

    assert order == [
        "lifecycle_start",
        "reconcile",
        "index",
        "lifecycle_succeed:existing-event",
    ]
    index.assert_awaited_once()
    assert index.await_args is not None
    assert (
        index.await_args.kwargs["payload"]["metadata"]["provider_event_id"]
        == "existing-event"
    )
    assert any(event.get("status") == "reconciled" for event in audits)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_mail_completion_persists_provider_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order, index, _audits, _requests = _configure_worker_dependencies(monkeypatch)

    await worker._handle_google_productivity_task(_mail_task())

    assert order == [
        "lifecycle_start",
        "provider",
        "lifecycle_succeed:created-event",
    ]
    index.assert_not_awaited()
