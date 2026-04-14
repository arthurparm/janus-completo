from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.infrastructure.filesystem_manager import read_file, write_file
from app.db.vector_store import build_deterministic_point_id
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository, UserRepository
from app.services.observability_service import ObservabilityService

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
    scopes: list[str] | None = None


class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str


class OAuthRefreshRequest(BaseModel):
    provider: str


def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()

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


def _ensure_consent(repo: ConsentRepository, scope: str) -> None:
    if not repo.has_consent("default", scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Consent required: {scope}"
        )


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
    require_authenticated_actor_id(request)
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user("default"):
            max_per_day = int(
                getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("calendar.write", 0)
            )
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    "default",
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
    from app.core.workers.google_productivity_worker import publish_google_calendar_add_event

    cm = (
        _tracer.start_as_current_span("productivity.calendar_add_event") if _OTEL else nullcontext()
    )
    with cm:  # type: ignore
        task_id = await publish_google_calendar_add_event(
            user_id="default", event=payload.event.model_dump(), index=bool(payload.index)
        )
        try:
            _PROD_REQUESTS_TOTAL.labels("calendar_add_event", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels(
                "default", "calendar_add_event", "queued"
            ).inc()
        except Exception:
            pass
    try:
        if bool(payload.index):
            evt = payload.event.model_dump()
            content = f"{evt.get('title', '')} @ {evt.get('location', '')}"
            pid = f"calendar:default:{int(evt.get('start_ts', 0))}:{int(evt.get('end_ts', 0))}"
            payload_q = {
                "content": content,
                "type": "calendar_event",
                "ts_ms": int(evt.get("start_ts") or 0),
                "composite_id": pid,
                "metadata": {
                    "type": "calendar_event",
                    "user_id": "default",
                    "timestamp": int(evt.get("start_ts") or 0),
                    "ts_ms": int(evt.get("start_ts") or 0),
                    "origin": "productivity.calendar.endpoint",
                },
            }
            await knowledge.index_memory_event(
                user_id="default",
                content=content,
                point_id=pid,
                payload=payload_q,
            )
            try:
                _PROD_REQUESTS_TOTAL.labels("calendar_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels("default", "calendar_index", "ok").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": "default",
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
    require_authenticated_actor_id(request)
    try:
        _PROD_OAUTH_EVENTS_TOTAL.labels("google", "start", "queued").inc()
    except Exception:
        pass
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or ""
    if not client_id or not str(client_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured"
        )
    scope = " ".join(payload.scopes or [])
    params = {
        "client_id": str(client_id),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "state": "user:default:scope:custom",
        "include_granted_scopes": "true",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return OAuthStartResponse(authorize_url=url, state="default")


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
    require_authenticated_actor_id(request)
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user("default"):
            max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("mail.send", 0))
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    "default",
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
    from app.core.workers.google_productivity_worker import publish_google_mail_send

    cm = _tracer.start_as_current_span("productivity.mail_send") if _OTEL else nullcontext()
    with cm:  # type: ignore
        task_id = await publish_google_mail_send(
            user_id="default", message=payload.message.model_dump(), index=bool(payload.index)
        )
        try:
            _PROD_REQUESTS_TOTAL.labels("mail_send", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels("default", "mail_send", "queued").inc()
        except Exception:
            pass
    # Indexação opcional será tratada pelo worker em uma versão futura
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": "default",
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
):
    require_authenticated_actor_id(request)
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        if not _is_unlimited_user("default"):
            max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("notes.write", 0))
            if max_per_day > 0:
                evts = svc.get_audit_events(
                    "default",
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
    path = "workspace/productivity/notes_default.json"
    try:
        raw = read_file(path)
    except Exception:
        raw = ""
    items: list[dict[str, Any]] = []
    try:
        if raw and not raw.startswith("Erro:"):
            import json

            items = json.loads(raw)
    except Exception:
        items = []
    note = payload.note.model_dump()
    items.append(note)
    import json

    text = json.dumps(items, ensure_ascii=False)
    from asyncio import get_event_loop

    loop = get_event_loop()
    await loop.run_in_executor(None, write_file, path, text, False)
    try:
        if bool(payload.index):
            content = f"{note.get('title', '')}\n{note.get('content', '')}"
            now_ts_ms = int(__import__("time").time() * 1000)
            pid = build_deterministic_point_id(
                "productivity-note",
                "default",
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
                    "user_id": "default",
                    "timestamp": now_ts_ms,
                    "ts_ms": now_ts_ms,
                    "origin": "productivity.notes.endpoint",
                },
            }
            await knowledge.index_memory_event(
                user_id="default",
                content=content,
                point_id=pid,
                payload=payload_q,
            )
            try:
                _PROD_REQUESTS_TOTAL.labels("notes_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels("default", "notes_index", "ok").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": "default",
                "tool": "notes_add",
                "status": "ok",
                "detail": {"title": payload.note.title},
            }
        )
        try:
            _PROD_REQUESTS_TOTAL.labels("notes_add", "ok").inc()
            _PROD_REQUESTS_USER_TOTAL.labels("default", "notes_add", "ok").inc()
        except Exception:
            pass
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("notes_add").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "ok", "count": len(items)}


@router.get("/notes")
async def notes_list(
    request: Request, repo: ConsentRepository = Depends(get_consent_repo)
):
    require_authenticated_actor_id(request)
    path = "workspace/productivity/notes_default.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json

            return {"notes": json.loads(raw)}
    except Exception:
        pass
    return {"notes": []}


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
async def google_oauth_start(request: Request, scope: str = "calendar"):
    require_authenticated_actor_id(request)
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or ""
    if not client_id or not str(client_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured"
        )
    base = "https://accounts.google.com/o/oauth2/v2/auth"
    scopes_map = {
        "calendar": "https://www.googleapis.com/auth/calendar.events",
        "mail": "https://www.googleapis.com/auth/gmail.send",
        "notes": "https://www.googleapis.com/auth/drive.file",
    }
    params = {
        "client_id": str(client_id),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": f"user::scope:{scope}",
        "scope": scopes_map.get(scope, scopes_map["calendar"]),
        "prompt": "consent",
    }
    url = f"{base}?" + urlencode(params)
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": "default",
                "tool": "google_oauth_start",
                "status": "ok",
                "detail": {"scope": scope},
            }
        )
    except Exception:
        pass
    return {"authorize_url": url}


class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/oauth/google/callback")
async def google_oauth_callback(payload: GoogleOAuthCallbackRequest, request: Request):
    actor = require_authenticated_actor_id(request)
    # troca de código por token
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None) or None
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or ""
    if not client_id or not client_secret or not str(client_id) or not str(client_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured"
        )
    import httpx

    tokens = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": payload.code,
                    "client_id": str(client_id),
                    "client_secret": str(client_secret),
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            tokens = resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token exchange failed")
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    from datetime import datetime, timedelta

    expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in or 0)) if expires_in else None
    # persiste token
    repo_tok = OAuthTokenRepository()
    repo_tok.upsert(
        user_id=actor,
        provider="google",
        access_token=str(access_token or ""),
        refresh_token=str(refresh_token or "") if refresh_token else None,
        expires_at=expires_at,
    )
    # registra consentimento para o escopo indicado no state
    try:
        _, _, state_scope = str(payload.state).partition("scope:")
        scope = state_scope.strip() or ""
        if scope:
            cons_repo = ConsentRepository()
            cons_repo.add_consent(
                user_id=actor, scope=f"{scope}.read", granted=True, expires_at=None
            )
            if scope in ("calendar", "notes"):
                cons_repo.add_consent(
                    user_id=actor, scope=f"{scope}.write", granted=True, expires_at=None
                )
            if scope == "mail":
                cons_repo.add_consent(
                    user_id=actor, scope="mail.send", granted=True, expires_at=None
                )
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {
                "user_id": str(actor),
                "tool": "google_oauth_callback",
                "status": "ok",
                "detail": {"state": payload.state},
            }
        )
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/oauth/google/refresh")
async def google_oauth_refresh(request: Request):
    require_authenticated_actor_id(request)
    repo_tok = OAuthTokenRepository()
    tok = repo_tok.get(user_id=0, provider="google")
    if not tok or not tok.refresh_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No refresh token")
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None) or None
    if not client_id or not client_secret or not str(client_id) or not str(client_secret):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured"
        )
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": str(client_id),
                    "client_secret": str(client_secret),
                    "refresh_token": tok.refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in")
            from datetime import datetime, timedelta

            expires_at = (
                datetime.utcnow() + timedelta(seconds=int(expires_in or 0)) if expires_in else None
            )
            repo_tok.upsert(
                user_id=0,
                provider="google",
                access_token=str(access_token or ""),
                refresh_token=tok.refresh_token,
                expires_at=expires_at,
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh failed")
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event(
            {"user_id": "default", "tool": "google_oauth_refresh", "status": "ok"}
        )
    except Exception:
        pass
    return {"status": "ok"}
