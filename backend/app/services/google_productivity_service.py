from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from urllib.parse import quote

import httpx

from app.config import settings
from app.core.security.egress_policy import enforce_worker_http_egress
from app.repositories.user_repository import OAuthTokenRepository
from app.services.productivity_oauth_state_service import resolve_google_oauth_config


class GoogleProductivityTokenUnavailableError(Exception):
    """The actor has no usable Google token and cannot refresh one."""


class GoogleProductivityProviderError(Exception):
    """Google or the outbound policy prevented a productivity operation."""


class CalendarEventResult(TypedDict):
    id: str
    title: str
    start: str
    end: str
    location: str | None
    status: str | None
    html_url: str | None


class MailMessageResult(TypedDict):
    id: str
    thread_id: str | None
    sender: str | None
    subject: str | None
    date: str | None
    snippet: str | None


def _allowed_url(url: str) -> str:
    allowed = enforce_worker_http_egress(url, tool="google_productivity")
    if not allowed:
        raise GoogleProductivityProviderError("Google egress is not allowed")
    return str(allowed)


async def resolve_google_access_token(
    *, repo: OAuthTokenRepository, token: Any, user_id: int
) -> str:
    access = token.access_token if token else None
    now = datetime.now(UTC).replace(tzinfo=None)
    should_refresh = bool(
        token
        and token.refresh_token
        and (not access or (token.expires_at and token.expires_at <= now))
    )
    if not should_refresh:
        if access:
            return str(access)
        raise GoogleProductivityTokenUnavailableError("Google OAuth connection required")

    return await refresh_google_access_token(repo=repo, token=token, user_id=user_id)


async def refresh_google_access_token(
    *, repo: OAuthTokenRepository, token: Any, user_id: int
) -> str:
    if not token or not token.refresh_token:
        raise GoogleProductivityTokenUnavailableError("Google refresh token required")

    client_id, client_secret, _redirect_uri = resolve_google_oauth_config(settings)
    now = datetime.now(UTC).replace(tzinfo=None)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _allowed_url("https://oauth2.googleapis.com/token"),
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
    refreshed = data.get("access_token") if isinstance(data, dict) else None
    if not isinstance(refreshed, str) or not refreshed:
        raise GoogleProductivityProviderError(
            "Google OAuth refresh response missing access_token"
        )
    expires_in = data.get("expires_in")
    expires_at = now + timedelta(seconds=int(expires_in or 0)) if expires_in else None
    repo.upsert(
        user_id=user_id,
        provider="google",
        access_token=refreshed,
        refresh_token=token.refresh_token,
        expires_at=expires_at,
    )
    return refreshed


async def _actor_access_token(user_id: int) -> str:
    repo = OAuthTokenRepository()
    token = repo.get(user_id=user_id, provider="google")
    return await resolve_google_access_token(repo=repo, token=token, user_id=user_id)


async def list_google_calendar_events(
    *, user_id: int, max_results: int
) -> list[CalendarEventResult]:
    access = await _actor_access_token(user_id)
    url = _allowed_url(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            url,
            params={
                "maxResults": max_results,
                "singleEvents": "true",
                "orderBy": "startTime",
                "timeMin": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        response.raise_for_status()
        payload = response.json()
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise GoogleProductivityProviderError("Invalid Google Calendar response")
    results: list[CalendarEventResult] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        start_value = item.get("start")
        end_value = item.get("end")
        start: dict[str, Any] = start_value if isinstance(start_value, dict) else {}
        end: dict[str, Any] = end_value if isinstance(end_value, dict) else {}
        results.append(
            {
                "id": str(item["id"]),
                "title": str(item.get("summary") or "(sem título)"),
                "start": str(start.get("dateTime") or start.get("date") or ""),
                "end": str(end.get("dateTime") or end.get("date") or ""),
                "location": str(item["location"]) if item.get("location") else None,
                "status": str(item["status"]) if item.get("status") else None,
                "html_url": str(item["htmlLink"]) if item.get("htmlLink") else None,
            }
        )
    return results


async def list_google_mail_messages(
    *, user_id: int, max_results: int
) -> list[MailMessageResult]:
    access = await _actor_access_token(user_id)
    list_url = _allowed_url(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    )
    headers = {"Authorization": f"Bearer {access}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            list_url,
            params={"maxResults": max_results},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
        if not isinstance(messages, list):
            raise GoogleProductivityProviderError("Invalid Gmail response")
        semaphore = asyncio.Semaphore(5)

        async def fetch_metadata(message: object) -> MailMessageResult | None:
            if not isinstance(message, dict) or not message.get("id"):
                return None
            message_id = str(message["id"])
            async with semaphore:
                detail = await client.get(
                    _allowed_url(f"{list_url}/{quote(message_id, safe='')}"),
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["From", "Subject", "Date"],
                    },
                    headers=headers,
                )
            detail.raise_for_status()
            data = detail.json()
            if not isinstance(data, dict):
                raise GoogleProductivityProviderError("Invalid Gmail message response")
            provider_headers = (
                data.get("payload", {}).get("headers", [])
                if isinstance(data.get("payload"), dict)
                else []
            )
            header_map = {
                str(entry.get("name", "")).lower(): str(entry.get("value", ""))
                for entry in provider_headers
                if isinstance(entry, dict)
            }
            return {
                "id": message_id,
                "thread_id": str(data["threadId"]) if data.get("threadId") else None,
                "sender": header_map.get("from") or None,
                "subject": header_map.get("subject") or None,
                "date": header_map.get("date") or None,
                "snippet": str(data["snippet"]) if data.get("snippet") else None,
            }

        fetched = await asyncio.wait_for(
            asyncio.gather(*(fetch_metadata(message) for message in messages)),
            timeout=30,
        )
    return [message for message in fetched if message is not None]
