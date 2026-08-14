import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.infrastructure.filesystem_manager import read_file
from app.db.vector_store import build_deterministic_point_id
from app.repositories.productivity_repository import (
    ProductivityNotesRepository,
    ProductivityRepositoryError,
)
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository, UserRepository
from app.services.observability_service import ObservabilityService
from app.services.productivity_consent_service import (
    ProductivityConsentRequiredError,
    require_productivity_consent,
)
from app.services.productivity_oauth_state_service import (
    GOOGLE_PRODUCTIVITY_CONSENTS,
    GOOGLE_PRODUCTIVITY_SCOPES,
    GoogleProductivityScope,
    OAuthConfigurationError,
    OAuthStateError,
    issue_google_oauth_state,
    resolve_google_oauth_config,
    verify_google_oauth_state,
)

try:
    from prometheus_client import Counter, Histogram  # type: ignore

    _PROD_REQUESTS_TOTAL = Counter(
        "productivity_requests_total", "Requests to productivity tools", ["tool", "status"]
    )  # type: ignore
    _PROD_REQUEST_LATENCY = Histogram(
        "productivity_request_latency_seconds", "Latency of productivity requests", ["tool"]
    )  # type: ignore
    _PROD_REQUESTS_USER_TOTAL = Counter(
        "productivity_requests_user_total",
        "Requests per user to productivity tools",
        ["user_id", "tool", "status"],
    )  # type: ignore
    _PROD_OAUTH_EVENTS_TOTAL = Counter(
        "productivity_oauth_events_total", "OAuth events", ["provider", "type", "status"]
    )  # type: ignore
except Exception:

    class _Noop:
        def labels(self, *a, **k):
            return self

        def inc(self, *a, **k):
            pass

        def observe(self, *a, **k):
            pass

    _PROD_REQUESTS_TOTAL = _Noop()
    _PROD_REQUEST_LATENCY = _Noop()
    _PROD_REQUESTS_USER_TOTAL = _Noop()
    _PROD_OAUTH_EVENTS_TOTAL = _Noop()
try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None
import time as _t
from urllib.parse import urlencode

from app.config import settings
from app.core.security.request_guard import require_authenticated_actor_id

router = APIRouter(tags=["Productivity"], prefix="/productivity")


class OAuthStartRequest(BaseModel):
    scope: GoogleProductivityScope


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str


class OAuthRefreshRequest(BaseModel):
    provider: str


def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()


def get_productivity_notes_repo() -> ProductivityNotesRepository:
    return ProductivityNotesRepository()

def get_knowledge_facade(request: Request):
    return request.app.state.knowledge_facade


def _is_unlimited_user(user_id: str | None = None) -> bool:
    unlimited = getattr(settings, "PRODUCTIVITY_UNLIMITED_USERS", []) or []
    if not unlimited:
        return False
    try:
        user = UserRepository().get_user(0)
        email = (user.email or "").strip().lower() if user else ""
        return bool(email) and email in {u.lower() for u in unlimited}
    except Exception:
        return False


def _require_consent(repo: ConsentRepository, user_id: str, scope: str) -> None:
    try:
        require_productivity_consent(repo, user_id=user_id, scope=scope)
    except ProductivityConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


def _google_oauth_config() -> tuple[str, str, str]:
    try:
        return resolve_google_oauth_config(settings)
    except OAuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _google_authorize_response(*, actor: str, scope: GoogleProductivityScope) -> OAuthStartResponse:
    client_id, client_secret, redirect_uri = _google_oauth_config()
    oauth_state = issue_google_oauth_state(
        signing_secret=client_secret,
        actor_id=actor,
        scope=scope,
    )
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_PRODUCTIVITY_SCOPES[scope],
        "access_type": "offline",
        "state": oauth_state,
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return OAuthStartResponse(authorize_url=url, state=oauth_state)


class CalendarEvent(BaseModel):
    title: str
    start_ts: float
    end_ts: float
    location: str | None = None
    notes: str | None = None


class CalendarAddRequest(BaseModel):
    event: CalendarEvent
    index: bool | None = False

@router.post("/calendar/events/add")
async def calendar_add_event(
    payload: CalendarAddRequest,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
    knowledge = Depends(get_knowledge_facade),
):
    actor = require_authenticated_actor_id(request)
    _require_consent(repo, actor, "calendar.write")
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user(actor):
            max_per_day = int(
                getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("calendar.write", 0)
            )
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    actor,
                    tool="calendar_add_event",
                    status="ok",
                    start_ts=start_ts,
                    end_ts=None,
                    limit=1000,
                    offset=0,
                )
                if len(evts) >= max_per_day:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily calendar.write quota exceeded",
                    )
    except HTTPException:
        raise
    except Exception:
        pass
    from app.core.workers.google_productivity_worker import (
        ProductivityQueueUnavailableError,
        publish_google_calendar_add_event,
    )

    cm = (
        _tracer.start_as_current_span("productivity.calendar_add_event") if _OTEL else nullcontext()
    )
    with cm:  # type: ignore
        try:
            task_id = await publish_google_calendar_add_event(
                user_id=actor,
                event=payload.event.model_dump(),
                index=bool(payload.index),
            )
        except ProductivityQueueUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        try:
            _PROD_REQUESTS_TOTAL.labels("calendar_add_event", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels(
                "[REDACTED_PII]", "calendar_add_event", "queued"
            ).inc()
        except Exception:
            pass
    try:
        if bool(payload.index):
            evt = payload.event.model_dump()
            content = f"{evt.get('title', '')} @ {evt.get('location', '')}"
            pid = f"calendar:{actor}:{int(evt.get('start_ts', 0))}:{int(evt.get('end_ts', 0))}"
            payload_q = {
                "content": content,
                "type": "calendar_event",
                "ts_ms": int(evt.get("start_ts") or 0),
                "composite_id": pid,
                "metadata": {
                    "type": "calendar_event",
                    "user_id": actor,
                    "timestamp": int(evt.get("start_ts") or 0),
                    "ts_ms": int(evt.get("start_ts") or 0),
                    "origin": "productivity.calendar.endpoint",
                },
            }
            await knowledge.index_memory_event(
                user_id=actor,
                content=content,
                point_id=pid,
                payload=payload_q,
            )
            try:
                _PROD_REQUESTS_TOTAL.labels("calendar_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels(
                    "[REDACTED_PII]", "calendar_index", "ok"
                ).inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": actor,
                "tool": "calendar_add_event",
                "status": "queued",
                "detail": {"task_id": task_id},
            }
        )
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("calendar_add_event").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "queued", "task_id": task_id}


@router.post("/oauth/google/start")
async def oauth_google_start(payload: OAuthStartRequest, request: Request):
    actor = require_authenticated_actor_id(request)
    try:
        _PROD_OAUTH_EVENTS_TOTAL.labels("google", "start", "queued").inc()
    except Exception:
        pass
    return _google_authorize_response(actor=actor, scope=payload.scope)


@router.get("/calendar/events")
async def calendar_list_events(
    request: Request, repo: ConsentRepository = Depends(get_consent_repo)
):
    require_authenticated_actor_id(request)
    path = "workspace/productivity/calendar_.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json

            return {"events": json.loads(raw)}
    except Exception:
        pass
    return {"events": []}


class MailMessage(BaseModel):
    to: str
    subject: str
    body: str


class MailSendRequest(BaseModel):
    message: MailMessage
    index: bool | None = False


@router.post("/mail/messages/send")
async def mail_send(
    payload: MailSendRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo)
):
    actor = require_authenticated_actor_id(request)
    _require_consent(repo, actor, "mail.send")
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user(actor):
            max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("mail.send", 0))
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    actor,
                    tool="mail_send",
                    status="ok",
                    start_ts=start_ts,
                    end_ts=None,
                    limit=1000,
                    offset=0,
                )
                if len(evts) >= max_per_day:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily mail.send quota exceeded",
                    )
    except HTTPException:
        raise
    except Exception:
        pass
    from app.core.workers.google_productivity_worker import (
        ProductivityQueueUnavailableError,
        publish_google_mail_send,
    )

    cm = _tracer.start_as_current_span("productivity.mail_send") if _OTEL else nullcontext()
    with cm:  # type: ignore
        try:
            task_id = await publish_google_mail_send(
                user_id=actor,
                message=payload.message.model_dump(),
                index=bool(payload.index),
            )
        except ProductivityQueueUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        try:
            _PROD_REQUESTS_TOTAL.labels("mail_send", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels("[REDACTED_PII]", "mail_send", "queued").inc()
        except Exception:
            pass
    # Indexação opcional será tratada pelo worker em uma versão futura
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": actor,
                "tool": "mail_send",
                "status": "queued",
                "detail": {"task_id": task_id},
            }
        )
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("mail_send").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "queued", "task_id": task_id}


@router.get("/mail/messages")
async def mail_list(
    request: Request, repo: ConsentRepository = Depends(get_consent_repo)
):
    require_authenticated_actor_id(request)
    path = "workspace/productivity/mail_.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json

            return {"messages": json.loads(raw)}
    except Exception:
        pass
    return {"messages": []}


class NoteItem(BaseModel):
    title: str
    content: str


class NoteAddRequest(BaseModel):
    note: NoteItem
    index: bool | None = False


@router.post("/notes/add")
async def notes_add(
    payload: NoteAddRequest,
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
    knowledge = Depends(get_knowledge_facade),
    notes_repo: ProductivityNotesRepository = Depends(get_productivity_notes_repo),
):
    actor = require_authenticated_actor_id(request)
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user(actor):
            max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("notes.write", 0))
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    actor,
                    tool="notes_add",
                    status="ok",
                    start_ts=start_ts,
                    end_ts=None,
                    limit=1000,
                    offset=0,
                )
                if len(evts) >= max_per_day:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Daily notes.write quota exceeded",
                    )
    except HTTPException:
        raise
    except Exception:
        pass
    cm = _tracer.start_as_current_span("productivity.notes_add") if _OTEL else nullcontext()
    with cm:  # type: ignore
        pass
    note = payload.note.model_dump()
    try:
        count = await asyncio.to_thread(notes_repo.add_note, actor, note)
    except ProductivityRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    try:
        if bool(payload.index):
            content = f"{note.get('title', '')}\n{note.get('content', '')}"
            now_ts_ms = int(__import__("time").time() * 1000)
            pid = build_deterministic_point_id(
                "productivity-note",
                actor,
                note.get("title", ""),
                content,
            )
            payload_q = {
                "content": content,
                "type": "note_item",
                "ts_ms": now_ts_ms,
                "composite_id": pid,
                "metadata": {
                    "type": "note_item",
                    "user_id": actor,
                    "timestamp": now_ts_ms,
                    "ts_ms": now_ts_ms,
                    "origin": "productivity.notes.endpoint",
                },
            }
            await knowledge.index_memory_event(
                user_id=actor,
                content=content,
                point_id=pid,
                payload=payload_q,
            )
            try:
                _PROD_REQUESTS_TOTAL.labels("notes_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels("[REDACTED_PII]", "notes_index", "ok").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": actor,
                "tool": "notes_add",
                "status": "ok",
                "detail": {"title": payload.note.title},
            }
        )
        try:
            _PROD_REQUESTS_TOTAL.labels("notes_add", "ok").inc()
            _PROD_REQUESTS_USER_TOTAL.labels("[REDACTED_PII]", "notes_add", "ok").inc()
        except Exception:
            pass
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("notes_add").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "ok", "count": count}


@router.get("/notes")
async def notes_list(
    request: Request,
    repo: ConsentRepository = Depends(get_consent_repo),
    notes_repo: ProductivityNotesRepository = Depends(get_productivity_notes_repo),
):
    actor = require_authenticated_actor_id(request)
    try:
        notes = await asyncio.to_thread(notes_repo.list_notes, actor)
    except ProductivityRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return {"notes": notes}


@router.get("/limits/status")
async def limits_status(request: Request):
    actor = require_authenticated_actor_id(request)
    try:
        actor_id = actor
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    svc: ObservabilityService = request.app.state.observability_service
    start_ts = float(__import__("time").time()) - 86400.0
    quotas = getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}) or {}
    mapping = {
        "calendar.write": "calendar_add_event",
        "mail.send": "mail_send",
        "notes.write": "notes_add",
    }
    usage: dict[str, Any] = {}
    unlimited = _is_unlimited_user()
    for scope, max_per_day in quotas.items():
        tool = mapping.get(scope)
        count = 0
        if tool:
            try:
                evts = svc.get_audit_events(
                    str(actor_id),
                    tool=tool,
                    status="ok",
                    start_ts=start_ts,
                    end_ts=None,
                    limit=1000,
                    offset=0,
                )
                count = len(evts)
            except Exception:
                count = 0
        if unlimited:
            usage[scope] = {
                "max_per_day": 0,
                "used": int(count),
                "remaining": 0,
                "unlimited": True,
            }
        else:
            usage[scope] = {
                "max_per_day": int(max_per_day),
                "used": int(count),
                "remaining": max(0, int(max_per_day) - int(count)),
            }
    return {"limits": usage}


@router.get("/oauth/google/start")
async def google_oauth_start(
    request: Request, scope: GoogleProductivityScope = "calendar"
) -> OAuthStartResponse:
    actor = require_authenticated_actor_id(request)
    response = _google_authorize_response(actor=actor, scope=scope)
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": actor,
                "tool": "google_oauth_start",
                "status": "ok",
                "detail": {"scope": scope},
            }
        )
    except Exception:
        pass
    return response


class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/oauth/google/callback")
async def google_oauth_callback(payload: GoogleOAuthCallbackRequest, request: Request):
    actor = require_authenticated_actor_id(request)
    # troca de código por token
    client_id, client_secret, redirect_uri = _google_oauth_config()
    try:
        verified_state = verify_google_oauth_state(
            payload.state,
            signing_secret=client_secret,
            actor_id=actor,
        )
    except OAuthStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    import httpx

    tokens = None
    try:
        from app.core.security.egress_policy import enforce_worker_http_egress

        token_url = "https://oauth2.googleapis.com/token"
        allowed_url = enforce_worker_http_egress(token_url, tool="google_oauth")
        if not allowed_url:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Egress blocked by policy")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                allowed_url,
                data={
                    "code": payload.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            tokens = resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token exchange failed")
    if not isinstance(tokens, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid token response",
        )
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Token response missing access_token",
        )
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    from datetime import UTC, datetime, timedelta

    expires_at = (
        datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=int(expires_in or 0))
        if expires_in
        else None
    )
    # persiste token
    repo_tok = OAuthTokenRepository()
    repo_tok.upsert(
        user_id=actor,
        provider="google",
        access_token=access_token,
        refresh_token=str(refresh_token or "") if refresh_token else None,
        expires_at=expires_at,
    )
    # registra consentimento para o escopo indicado no state
    scope = verified_state.scope
    cons_repo = ConsentRepository()
    for consent_scope in GOOGLE_PRODUCTIVITY_CONSENTS[scope]:
        cons_repo.add_consent(
            user_id=actor,
            scope=consent_scope,
            granted=True,
            expires_at=None,
        )
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": str(actor),
                "tool": "google_oauth_callback",
                "status": "ok",
                "detail": {"scope": scope},
            }
        )
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/oauth/google/refresh")
async def google_oauth_refresh(request: Request):
    actor = require_authenticated_actor_id(request)
    repo_tok = OAuthTokenRepository()
    tok = repo_tok.get(user_id=actor, provider="google")
    if not tok or not tok.refresh_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No refresh token")
    client_id, client_secret, _redirect_uri = _google_oauth_config()
    import httpx

    try:
        from app.core.security.egress_policy import enforce_worker_http_egress

        token_url = "https://oauth2.googleapis.com/token"
        allowed_url = enforce_worker_http_egress(token_url, tool="google_oauth")
        if not allowed_url:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Egress blocked by policy")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                allowed_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": tok.refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Token response missing access_token",
                )
            expires_in = data.get("expires_in")
            from datetime import UTC, datetime, timedelta

            expires_at = (
                datetime.now(UTC).replace(tzinfo=None)
                + timedelta(seconds=int(expires_in or 0))
                if expires_in
                else None
            )
            repo_tok.upsert(
                user_id=actor,
                provider="google",
                access_token=access_token,
                refresh_token=tok.refresh_token,
                expires_at=expires_at,
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh failed")
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {"user_id": actor, "tool": "google_oauth_refresh", "status": "ok"}
        )
    except Exception:
        pass
    return {"status": "ok"}
