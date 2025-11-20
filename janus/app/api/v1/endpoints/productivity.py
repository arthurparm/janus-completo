from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.repositories.user_repository import ConsentRepository, UserRepository, OAuthTokenRepository
from app.core.embeddings.embedding_manager import embed_text
from app.db.vector_store import get_qdrant_client, get_or_create_collection
from qdrant_client import models
from app.core.infrastructure.filesystem_manager import read_file, write_file
from app.services.observability_service import ObservabilityService
try:
    from prometheus_client import Counter, Histogram  # type: ignore
    _PROD_REQUESTS_TOTAL = Counter("productivity_requests_total", "Requests to productivity tools", ["tool", "status"])  # type: ignore
    _PROD_REQUEST_LATENCY = Histogram("productivity_request_latency_seconds", "Latency of productivity requests", ["tool"])  # type: ignore
    _PROD_REQUESTS_USER_TOTAL = Counter("productivity_requests_user_total", "Requests per user to productivity tools", ["user_id", "tool", "status"])  # type: ignore
    _PROD_OAUTH_EVENTS_TOTAL = Counter("productivity_oauth_events_total", "OAuth events", ["provider", "type", "status"])  # type: ignore
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
    from prometheus_client import Counter  # type: ignore
    _PROD_REQUESTS_TOTAL = Counter("productivity_requests_total", "Requests to productivity tools", ["tool", "status"])  # type: ignore
except Exception:
    class _Noop:
        def labels(self, *a, **k):
            return self
        def inc(self, *a, **k):
            pass
    _PROD_REQUESTS_TOTAL = _Noop()
try:
    from opentelemetry import trace  # type: ignore
    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext
    _tracer = None
from app.config import settings
import time as _t
from urllib.parse import urlencode
from app.services.observability_service import ObservabilityService

router = APIRouter(tags=["Productivity"], prefix="/productivity")

class OAuthStartRequest(BaseModel):
    user_id: int
    scopes: Optional[List[str]] = None

class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str

class OAuthCallbackRequest(BaseModel):
    user_id: int
    code: str

class OAuthRefreshRequest(BaseModel):
    user_id: int
    provider: str


def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()


def _ensure_consent(repo: ConsentRepository, user_id: int, scope: str) -> None:
    if not repo.has_consent(user_id, scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Consent required: {scope}")


class CalendarEvent(BaseModel):
    title: str
    start_ts: float
    end_ts: float
    location: Optional[str] = None
    notes: Optional[str] = None


class CalendarAddRequest(BaseModel):
    user_id: int
    event: CalendarEvent
    index: Optional[bool] = False

class OAuthStartRequest(BaseModel):
    user_id: int
    scopes: Optional[List[str]] = None

class OAuthStartResponse(BaseModel):
    authorize_url: str
    state: str

class OAuthCallbackRequest(BaseModel):
    user_id: int
    code: str

class OAuthRefreshRequest(BaseModel):
    user_id: int
    provider: str


@router.post("/calendar/events/add")
async def calendar_add_event(payload: CalendarAddRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, payload.user_id, "calendar.write")
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("calendar.write", 0))
        if max_per_day > 0:
            evts = svc.get_audit_events(str(payload.user_id), tool="calendar_add_event", status="ok", start_ts=start_ts, end_ts=None, limit=1000, offset=0)
            if len(evts) >= max_per_day:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily calendar.write quota exceeded")
    except HTTPException:
        raise
    except Exception:
        pass
    from app.core.workers.google_productivity_worker import publish_google_calendar_add_event
    cm = (_tracer.start_as_current_span("productivity.calendar_add_event") if _OTEL else nullcontext())
    async with cm:  # type: ignore
        task_id = await publish_google_calendar_add_event(user_id=payload.user_id, event=payload.event.model_dump(), index=bool(payload.index))
        try:
            _PROD_REQUESTS_TOTAL.labels("calendar_add_event", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels(str(payload.user_id), "calendar_add_event", "queued").inc()
        except Exception:
            pass
    try:
        if bool(payload.index):
            client = get_qdrant_client()
            coll = get_or_create_collection(f"user_{payload.user_id}")
            evt = payload.event.model_dump()
            content = f"{evt.get('title','')} @ {evt.get('location','')}"
            vec = embed_text(content)
            pid = f"calendar:{payload.user_id}:{int(evt.get('start_ts', 0))}:{int(evt.get('end_ts', 0))}"
            payload_q = {
                "content": content,
                "metadata": {
                    "type": "calendar_event",
                    "user_id": str(payload.user_id),
                    "timestamp": int(evt.get("start_ts") or 0),
                }
            }
            point = models.PointStruct(id=pid, vector=vec, payload=payload_q)
            client.upsert(collection_name=coll, points=[point])
            try:
                _PROD_REQUESTS_TOTAL.labels("calendar_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels(str(payload.user_id), "calendar_index", "ok").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(payload.user_id), "tool": "calendar_add_event", "status": "queued", "detail": {"task_id": task_id}})
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("calendar_add_event").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "queued", "task_id": task_id}

@router.post("/oauth/google/start")
async def oauth_google_start(payload: OAuthStartRequest, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    try:
        _PROD_OAUTH_EVENTS_TOTAL.labels("google", "start", "queued").inc()
    except Exception:
        pass
    client_id = str(getattr(settings, "PRODUCTIVITY_GOOGLE_OAUTH_CLIENT_ID", ""))
    redirect_uri = str(getattr(settings, "PRODUCTIVITY_GOOGLE_OAUTH_REDIRECT_URI", ""))
    scope = " ".join(payload.scopes or [])
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "state": str(payload.user_id),
        "include_granted_scopes": "true",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return OAuthStartResponse(authorize_url=url, state=str(payload.user_id))

@router.post("/oauth/google/callback")
async def oauth_google_callback(payload: OAuthCallbackRequest, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    repo = OAuthTokenRepository()
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(seconds=int(getattr(settings, "PRODUCTIVITY_OAUTH_DEFAULT_EXP", 3600)))
    tok = repo.upsert(payload.user_id, "google", access_token=payload.code, refresh_token="refresh", expires_at=expires_at)
    try:
        _PROD_OAUTH_EVENTS_TOTAL.labels("google", "callback", "ok").inc()
    except Exception:
        pass
    return {"status": "ok"}

@router.post("/oauth/google/refresh")
async def oauth_google_refresh(payload: OAuthRefreshRequest, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    repo = OAuthTokenRepository()
    tok = repo.get(payload.user_id, payload.provider)
    if tok is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(seconds=int(getattr(settings, "PRODUCTIVITY_OAUTH_DEFAULT_EXP", 3600)))
    out = repo.upsert(payload.user_id, payload.provider, access_token=tok.access_token, refresh_token=tok.refresh_token, expires_at=expires_at)
    try:
        _PROD_OAUTH_EVENTS_TOTAL.labels(payload.provider, "refresh", "ok").inc()
    except Exception:
        pass
    return {"status": "ok"}


@router.get("/calendar/events")
async def calendar_list_events(user_id: int, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, user_id, "calendar.read")
    path = f"workspace/productivity/calendar_{user_id}.json"
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
    user_id: int
    message: MailMessage
    index: Optional[bool] = False


@router.post("/mail/messages/send")
async def mail_send(payload: MailSendRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, payload.user_id, "mail.send")
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("mail.send", 0))
        if max_per_day > 0:
            evts = svc.get_audit_events(str(payload.user_id), tool="mail_send", status="ok", start_ts=start_ts, end_ts=None, limit=1000, offset=0)
            if len(evts) >= max_per_day:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily mail.send quota exceeded")
    except HTTPException:
        raise
    except Exception:
        pass
    from app.core.workers.google_productivity_worker import publish_google_mail_send
    cm = (_tracer.start_as_current_span("productivity.mail_send") if _OTEL else nullcontext())
    async with cm:  # type: ignore
        task_id = await publish_google_mail_send(user_id=payload.user_id, message=payload.message.model_dump(), index=bool(payload.index))
        try:
            _PROD_REQUESTS_TOTAL.labels("mail_send", "queued").inc()
            _PROD_REQUESTS_USER_TOTAL.labels(str(payload.user_id), "mail_send", "queued").inc()
        except Exception:
            pass
    # Indexação opcional será tratada pelo worker em uma versão futura
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(payload.user_id), "tool": "mail_send", "status": "queued", "detail": {"task_id": task_id}})
    except Exception:
        pass
    try:
        _PROD_REQUEST_LATENCY.labels("mail_send").observe(max(0.0, _t.time() - _t0))
    except Exception:
        pass
    return {"status": "queued", "task_id": task_id}


@router.get("/mail/messages")
async def mail_list(user_id: int, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, user_id, "mail.read")
    path = f"workspace/productivity/mail_{user_id}.json"
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
    user_id: int
    note: NoteItem
    index: Optional[bool] = False


@router.post("/notes/add")
async def notes_add(payload: NoteAddRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(payload.user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, payload.user_id, "notes.write")
    _t0 = _t.time()
    try:
        svc: ObservabilityService = request.app.state.observability_service
        start_ts = float(_t.time()) - 86400.0
        max_per_day = int(getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}).get("notes.write", 0))
        if max_per_day > 0:
            evts = svc.get_audit_events(str(payload.user_id), tool="notes_add", status="ok", start_ts=start_ts, end_ts=None, limit=1000, offset=0)
            if len(evts) >= max_per_day:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily notes.write quota exceeded")
    except HTTPException:
        raise
    except Exception:
        pass
    cm = (_tracer.start_as_current_span("productivity.notes_add") if _OTEL else nullcontext())
    async with cm:  # type: ignore
        pass
    path = f"workspace/productivity/notes_{payload.user_id}.json"
    try:
        raw = read_file(path)
    except Exception:
        raw = ""
    items: List[Dict[str, Any]] = []
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
            client = get_qdrant_client()
            coll = get_or_create_collection(f"user_{payload.user_id}")
            content = f"{note.get('title','')}\n{note.get('content','')}"
            vec = embed_text(content)
            pid = f"note:{payload.user_id}:{hash(content)}"
            payload_q = {
                "content": content,
                "metadata": {
                    "type": "note_item",
                    "user_id": str(payload.user_id),
                    "timestamp": int(__import__('time').time()),
                }
            }
            point = models.PointStruct(id=pid, vector=vec, payload=payload_q)
            client.upsert(collection_name=coll, points=[point])
            try:
                _PROD_REQUESTS_TOTAL.labels("notes_index", "ok").inc()
                _PROD_REQUESTS_USER_TOTAL.labels(str(payload.user_id), "notes_index", "ok").inc()
            except Exception:
                pass
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(payload.user_id), "tool": "notes_add", "status": "ok", "detail": {"title": payload.note.title}})
        try:
            _PROD_REQUESTS_TOTAL.labels("notes_add", "ok").inc()
            _PROD_REQUESTS_USER_TOTAL.labels(str(payload.user_id), "notes_add", "ok").inc()
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
async def notes_list(user_id: int, request: Request, repo: ConsentRepository = Depends(get_consent_repo)):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    _ensure_consent(repo, user_id, "notes.read")
    path = f"workspace/productivity/notes_{user_id}.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            return {"notes": json.loads(raw)}
    except Exception:
        pass
    return {"notes": []}


@router.get("/limits/status")
async def limits_status(user_id: int, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    from app.repositories.user_repository import UserRepository
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    svc: ObservabilityService = request.app.state.observability_service
    start_ts = float(__import__('time').time()) - 86400.0
    quotas = getattr(settings, "PRODUCTIVITY_DAILY_LIMITS", {}) or {}
    mapping = {
        "calendar.write": "calendar_add_event",
        "mail.send": "mail_send",
        "notes.write": "notes_add",
    }
    usage: Dict[str, Any] = {}
    for scope, max_per_day in quotas.items():
        tool = mapping.get(scope)
        count = 0
        if tool:
            try:
                evts = svc.get_audit_events(str(user_id), tool=tool, status="ok", start_ts=start_ts, end_ts=None, limit=1000, offset=0)
                count = len(evts)
            except Exception:
                count = 0
        usage[scope] = {
            "max_per_day": int(max_per_day),
            "used": int(count),
            "remaining": max(0, int(max_per_day) - int(count)),
        }
    return {"user_id": str(user_id), "limits": usage}


@router.get("/oauth/google/start")
async def google_oauth_start(user_id: int, request: Request, scope: str = "calendar"):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    from app.repositories.user_repository import UserRepository
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    client_id = (getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None)
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or ""
    if not client_id or not str(client_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured")
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
        "state": f"user:{user_id}:scope:{scope}",
        "scope": scopes_map.get(scope, scopes_map["calendar"]),
        "prompt": "consent",
    }
    url = f"{base}?" + urlencode(params)
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(user_id), "tool": "google_oauth_start", "status": "ok", "detail": {"scope": scope}})
    except Exception:
        pass
    return {"authorize_url": url}


class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    state: str

@router.post("/oauth/google/callback")
async def google_oauth_callback(payload: GoogleOAuthCallbackRequest, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    # troca de código por token
    client_id = (getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None)
    client_secret = (getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None) or None)
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", None) or ""
    if not client_id or not client_secret or not str(client_id) or not str(client_secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured")
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
                headers={"Content-Type": "application/x-www-form-urlencoded"}
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
    tok = repo_tok.upsert(user_id=int(actor), provider="google", access_token=str(access_token or ""), refresh_token=str(refresh_token or "") if refresh_token else None, expires_at=expires_at)
    # registra consentimento para o escopo indicado no state
    try:
        _, _, state_scope = str(payload.state).partition("scope:")
        scope = state_scope.strip() or ""
        if scope:
            cons_repo = ConsentRepository()
            cons_repo.add_consent(user_id=int(actor), scope=f"{scope}.read", granted=True, expires_at=None)
            if scope in ("calendar", "notes"):
                cons_repo.add_consent(user_id=int(actor), scope=f"{scope}.write", granted=True, expires_at=None)
            if scope == "mail":
                cons_repo.add_consent(user_id=int(actor), scope="mail.send", granted=True, expires_at=None)
    except Exception:
        pass
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(actor), "tool": "google_oauth_callback", "status": "ok", "detail": {"state": payload.state}})
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/oauth/google/refresh")
async def google_oauth_refresh(user_id: int, request: Request):
    actor = getattr(request.state, "actor_user_id", None) or request.headers.get("X-User-Id")
    from app.repositories.user_repository import UserRepository
    ur = UserRepository()
    if not actor or (int(actor) != int(user_id) and not ur.is_admin(int(actor))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    repo_tok = OAuthTokenRepository()
    tok = repo_tok.get(user_id=int(user_id), provider="google")
    if not tok or not tok.refresh_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No refresh token")
    client_id = (getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None) or None)
    client_secret = (getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None) or None)
    if not client_id or not client_secret or not str(client_id) or not str(client_secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client not configured")
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
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in")
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in or 0)) if expires_in else None
            repo_tok.upsert(user_id=int(user_id), provider="google", access_token=str(access_token or ""), refresh_token=tok.refresh_token, expires_at=expires_at)
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh failed")
    try:
        svc: ObservabilityService = request.app.state.observability_service
        svc.record_audit_event({"user_id": str(user_id), "tool": "google_oauth_refresh", "status": "ok"})
    except Exception:
        pass
    return {"status": "ok"}
