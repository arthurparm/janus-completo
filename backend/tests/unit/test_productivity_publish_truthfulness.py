from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import SecretStr

from app.config import settings
from app.core.infrastructure.message_broker import MessageBroker
from app.core.workers import google_productivity_worker as worker


class _OfflineBroker:
    def __init__(self) -> None:
        self.publish = AsyncMock(return_value=False)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_message_broker_reports_offline_delivery() -> None:
    broker = MessageBroker.__new__(MessageBroker)
    broker.connect = AsyncMock()
    broker._connection = None

    delivered = await broker.publish("janus.test", b"payload")

    assert delivered is False


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("publisher", "payload"),
    [
        (worker.publish_google_calendar_add_event, {"event": {}, "index": False}),
        (worker.publish_google_mail_send, {"message": {}, "index": False}),
    ],
)
async def test_productivity_publishers_do_not_report_offline_queue_as_success(
    monkeypatch: pytest.MonkeyPatch,
    publisher: object,
    payload: dict[str, object],
) -> None:
    broker = _OfflineBroker()
    audit = Mock()
    monkeypatch.setattr(worker, "get_broker", AsyncMock(return_value=broker))
    monkeypatch.setattr(worker, "record_audit_event_direct", audit)

    with pytest.raises(worker.ProductivityQueueUnavailableError, match="não foi enfileirado"):
        await publisher(user_id=7, **payload)  # type: ignore[operator]

    broker.publish.assert_awaited_once()
    audit.assert_not_called()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_productivity_publisher_records_queue_only_after_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = _OfflineBroker()
    broker.publish.return_value = True
    audit = Mock()
    monkeypatch.setattr(worker, "get_broker", AsyncMock(return_value=broker))
    monkeypatch.setattr(worker, "record_audit_event_direct", audit)

    task_id = await worker.publish_google_mail_send(
        user_id=7,
        message={"to": "dest@example.com", "subject": "S", "body": "B"},
        index=False,
    )

    assert task_id
    broker.publish.assert_awaited_once()
    assert audit.call_args.args[0]["status"] == "queued"


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("current_access", "expires_at"),
    [
        (
            "old-access",
            datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
        ),
        (None, None),
    ],
)
async def test_worker_refreshes_google_token_with_unmasked_credentials(
    monkeypatch: pytest.MonkeyPatch,
    current_access: str | None,
    expires_at: datetime | None,
) -> None:
    captured: dict[str, object] = {}
    writes: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"access_token": "new-access", "expires_in": 120}

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> _Response:
            captured["url"] = url
            captured.update(kwargs)
            return _Response()

    class _Repository:
        def upsert(self, **kwargs: object) -> None:
            writes.append(kwargs)

    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", SecretStr("worker-client"))
    monkeypatch.setattr(
        settings,
        "GOOGLE_OAUTH_CLIENT_SECRET",
        SecretStr("worker-secret"),
    )
    monkeypatch.setattr(
        settings,
        "GOOGLE_OAUTH_REDIRECT_URI",
        "https://janus.example/oauth/google/callback",
    )
    monkeypatch.setattr(worker.httpx, "AsyncClient", lambda **_kwargs: _Client())
    monkeypatch.setattr(
        worker,
        "enforce_worker_http_egress",
        lambda url, **_kwargs: url,
    )
    token = SimpleNamespace(
        access_token=current_access,
        refresh_token="refresh-token",
        expires_at=expires_at,
    )

    access_token = await worker._resolve_google_access_token(
        repo=_Repository(),
        token=token,
        user_id=7,
    )

    assert access_token == "new-access"
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["data"] == {
        "client_id": "worker-client",
        "client_secret": "worker-secret",
        "refresh_token": "refresh-token",
        "grant_type": "refresh_token",
    }
    assert writes[0]["access_token"] == "new-access"
