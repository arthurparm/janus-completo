from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from app.services import google_productivity_service as service


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_calendar_list_uses_actor_token_and_normalizes_provider_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = AsyncMock(return_value="actor-token")
    captured: dict[str, object] = {}

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: object) -> _Response:
            captured["url"] = url
            captured.update(kwargs)
            return _Response(
                {
                    "items": [
                        {
                            "id": "event-1",
                            "summary": "Revisão",
                            "start": {"dateTime": "2026-08-15T10:00:00Z"},
                            "end": {"dateTime": "2026-08-15T11:00:00Z"},
                            "location": "Sala A",
                            "status": "confirmed",
                            "htmlLink": "https://calendar.google.com/event-1",
                        }
                    ]
                }
            )

    monkeypatch.setattr(service, "_actor_access_token", token)
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())

    events = await service.list_google_calendar_events(user_id=7, max_results=12)

    token.assert_awaited_once_with(7)
    assert captured["headers"] == {"Authorization": "Bearer actor-token"}
    assert captured["params"]["maxResults"] == 12  # type: ignore[index]
    assert events == [
        {
            "id": "event-1",
            "title": "Revisão",
            "start": "2026-08-15T10:00:00Z",
            "end": "2026-08-15T11:00:00Z",
            "location": "Sala A",
            "status": "confirmed",
            "html_url": "https://calendar.google.com/event-1",
        }
    ]


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_mail_list_fetches_metadata_without_message_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = AsyncMock(return_value="actor-token")
    calls: list[tuple[str, dict[str, object]]] = []

    class _Client:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: object) -> _Response:
            calls.append((url, kwargs))
            if url.endswith("/messages"):
                return _Response({"messages": [{"id": "mail-1"}]})
            return _Response(
                {
                    "id": "mail-1",
                    "threadId": "thread-1",
                    "snippet": "Trecho seguro",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "sender@example.com"},
                            {"name": "Subject", "value": "Assunto"},
                            {"name": "Date", "value": "Fri, 14 Aug 2026"},
                        ]
                    },
                }
            )

    monkeypatch.setattr(service, "_actor_access_token", token)
    monkeypatch.setattr(service, "enforce_worker_http_egress", lambda url, **_: url)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: _Client())

    messages = await service.list_google_mail_messages(user_id=9, max_results=5)

    token.assert_awaited_once_with(9)
    assert calls[0][1]["params"] == {"maxResults": 5}
    assert calls[1][1]["params"] == {
        "format": "metadata",
        "metadataHeaders": ["From", "Subject", "Date"],
    }
    assert messages == [
        {
            "id": "mail-1",
            "thread_id": "thread-1",
            "sender": "sender@example.com",
            "subject": "Assunto",
            "date": "Fri, 14 Aug 2026",
            "snippet": "Trecho seguro",
        }
    ]
