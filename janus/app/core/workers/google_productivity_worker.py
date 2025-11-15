import structlog
from uuid import uuid4
from typing import Dict, Any
from datetime import datetime, timedelta
import base64
import httpx

from app.core.infrastructure.message_broker import get_broker
from app.models.schemas import TaskMessage
from app.db.vector_store import get_qdrant_client, get_or_create_collection
from app.core.embeddings.embedding_manager import embed_text
from app.services.observability_service import ObservabilityService
from app.repositories.observability_repository import record_audit_event_direct
from app.repositories.user_repository import OAuthTokenRepository
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID, PROJECT_ID
try:
    from prometheus_client import Counter, Histogram  # type: ignore
except Exception:
    class Counter:  # type: ignore
        def labels(self, *a, **k):
            return self
        def inc(self, *a, **k):
            pass
    class Histogram:  # type: ignore
        def labels(self, *a, **k):
            return self
        def observe(self, *a, **k):
            pass
try:
    from opentelemetry import trace  # type: ignore
    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext
    _tracer = None

logger = structlog.get_logger(__name__)

QUEUE_GOOGLE_CALENDAR = "janus.productivity.google.calendar"
QUEUE_GOOGLE_MAIL = "janus.productivity.google.mail"
_GOOGLE_PROD_EVENTS_PUBLISHED = Counter("google_productivity_events_published_total", "Eventos de produtividade publicados", ["type"])  # type: ignore
_GOOGLE_CALENDAR_EVENTS_INDEXED = Counter("google_calendar_events_indexed_total", "Eventos do calendário indexados")  # type: ignore
_GOOGLE_MAIL_SENT_TOTAL = Counter("google_mail_sent_total", "Mensagens de e-mail enviadas")  # type: ignore
_PROD_WORKER_LATENCY = Histogram("productivity_worker_latency_seconds", "Latência no worker de produtividade", ["op"])  # type: ignore
_PROD_WORKER_USER_EVENTS = Counter("productivity_worker_user_events_total", "Eventos por usuário no worker", ["user_id", "op", "status"])  # type: ignore
_PROD_WORKER_USER_LATENCY = Histogram("productivity_worker_user_latency_seconds", "Latência por usuário no worker de produtividade", ["user_id", "op"])  # type: ignore

async def publish_google_calendar_add_event(user_id: int, event: Dict[str, Any], index: bool) -> str:
    task_id = uuid4().hex
    msg = TaskMessage(task_id=task_id, task_type="google_calendar_add_event", payload={"user_id": user_id, "event": event, "index": bool(index)}, timestamp=__import__("time").time())
    try:
        cm = (_tracer.start_as_current_span("google.calendar.publish") if _OTEL else nullcontext())
        async with cm:  # type: ignore
            broker = await get_broker()
            await broker.publish(QUEUE_GOOGLE_CALENDAR, msg.to_msgpack(), use_msgpack=True, priority=5)
        try:
            _GOOGLE_PROD_EVENTS_PUBLISHED.labels("google_calendar_add_event").inc()
        except Exception:
            pass
    except Exception:
        logger.warning("Broker offline", task_id=task_id)
    try:
        record_audit_event_direct({
            "user_id": int(user_id),
            "endpoint": "productivity:google_calendar",
            "action": "publish_add_event",
            "tool": "google_calendar",
            "status": "queued",
            "latency_ms": None,
            "trace_id": TRACE_ID.get(),
        })
    except Exception:
        pass
    return task_id

async def publish_google_mail_send(user_id: int, message: Dict[str, Any], index: bool) -> str:
    task_id = uuid4().hex
    msg = TaskMessage(task_id=task_id, task_type="google_mail_send", payload={"user_id": user_id, "message": message, "index": bool(index)}, timestamp=__import__("time").time())
    try:
        cm = (_tracer.start_as_current_span("google.mail.publish") if _OTEL else nullcontext())
        async with cm:  # type: ignore
            broker = await get_broker()
            await broker.publish(QUEUE_GOOGLE_MAIL, msg.to_msgpack(), use_msgpack=True, priority=5)
        try:
            _GOOGLE_PROD_EVENTS_PUBLISHED.labels("google_mail_send").inc()
        except Exception:
            pass
    except Exception:
        logger.warning("Broker offline", task_id=task_id)
    try:
        record_audit_event_direct({
            "user_id": int(user_id),
            "endpoint": "productivity:google_mail",
            "action": "publish_mail_send",
            "tool": "google_mail",
            "status": "queued",
            "latency_ms": None,
            "trace_id": TRACE_ID.get(),
        })
    except Exception:
        pass
    return task_id

async def start_google_productivity_consumer():
    async def _handle(task: TaskMessage):
        try:
            payload = task.payload or {}
            user_id = int(payload.get("user_id")) if payload.get("user_id") is not None else None
            ev = payload.get("event") or {}
            msg = payload.get("message") or {}
            do_index = bool(payload.get("index"))
            if task.task_type == "google_calendar_add_event" and user_id is not None:
                try:
                    repo = OAuthTokenRepository()
                    tok = repo.get(user_id=int(user_id), provider="google")
                    access = tok.access_token if tok else None
                    if tok and tok.expires_at and tok.expires_at <= datetime.utcnow() and tok.refresh_token:
                        from app.config import settings
                        cid = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
                        cs = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)
                        if cid and cs:
                            async with httpx.AsyncClient(timeout=30) as client:
                                r = await client.post(
                                    "https://oauth2.googleapis.com/token",
                                    data={
                                        "client_id": str(cid),
                                        "client_secret": str(cs),
                                        "refresh_token": tok.refresh_token,
                                        "grant_type": "refresh_token",
                                    },
                                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                                )
                                r.raise_for_status()
                                data = r.json()
                                access = data.get("access_token") or access
                                exp_in = data.get("expires_in")
                                exp_at = datetime.utcnow() + timedelta(seconds=int(exp_in or 0)) if exp_in else None
                                repo.upsert(user_id=int(user_id), provider="google", access_token=str(access or tok.access_token), refresh_token=tok.refresh_token, expires_at=exp_at)
                    if access:
                        _t0 = __import__("time").perf_counter()
                        async with httpx.AsyncClient(timeout=30) as client:
                            req = {
                                "summary": ev.get("title"),
                                "start": {"dateTime": datetime.utcfromtimestamp(float(ev.get("start_ts"))).isoformat()+"Z"},
                                "end": {"dateTime": datetime.utcfromtimestamp(float(ev.get("end_ts"))).isoformat()+"Z"},
                                "location": ev.get("location") or None,
                                "description": ev.get("notes") or None,
                            }
                            resp = await client.post(
                                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                                json=req,
                                headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"}
                            )
                            resp.raise_for_status()
                        try:
                            _PROD_WORKER_USER_EVENTS.labels(str(user_id), "calendar_send", "ok").inc()
                            _PROD_WORKER_LATENCY.labels("calendar_send").observe(__import__("time").perf_counter() - _t0)
                            _PROD_WORKER_USER_LATENCY.labels(str(user_id), "calendar_send").observe(__import__("time").perf_counter() - _t0)
                        except Exception:
                            pass
                        try:
                            record_audit_event_direct({
                                "user_id": int(user_id),
                                "endpoint": "productivity:google_calendar",
                                "action": "calendar_add_event",
                                "tool": "google_calendar",
                                "status": "ok",
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                            })
                        except Exception:
                            pass
                except Exception:
                    try:
                        record_audit_event_direct({
                            "user_id": int(user_id) if user_id is not None else None,
                            "endpoint": "productivity:google_calendar",
                            "action": "calendar_add_event",
                            "tool": "google_calendar",
                            "status": "error",
                            "latency_ms": None,
                            "trace_id": TRACE_ID.get(),
                        })
                    except Exception:
                        pass
                    try:
                        _PROD_WORKER_USER_EVENTS.labels(str(user_id or ""), "calendar_send", "error").inc()
                    except Exception:
                        pass
                if do_index and user_id is not None:
                    try:
                        _t0 = __import__("time").perf_counter()
                        client = get_qdrant_client()
                        coll = get_or_create_collection(f"user_{user_id}")
                        title = str(ev.get("title", ""))
                        loc = str(ev.get("location", ""))
                        content = f"{title} @ {loc}"
                        vec = embed_text(content)
                        pid = f"calendar:{user_id}:{int(ev.get('start_ts', 0))}:{int(ev.get('end_ts', 0))}"
                        payload_q = {
                            "content": content,
                            "metadata": {
                                "type": "calendar_event",
                                "origin": "google",
                                "scope": "calendar.write",
                                "user_id": str(user_id),
                                "timestamp": int(ev.get("start_ts") or 0),
                            }
                        }
                        from qdrant_client import models as _m
                        point = _m.PointStruct(id=pid, vector=vec, payload=payload_q)
                        client.upsert(collection_name=coll, points=[point])
                        try:
                            _GOOGLE_CALENDAR_EVENTS_INDEXED.inc()
                            _PROD_WORKER_USER_EVENTS.labels(str(user_id), "calendar_index", "ok").inc()
                            _PROD_WORKER_LATENCY.labels("calendar_index").observe(__import__("time").perf_counter() - _t0)
                            _PROD_WORKER_USER_LATENCY.labels(str(user_id), "calendar_index").observe(__import__("time").perf_counter() - _t0)
                        except Exception:
                            pass
                        try:
                            record_audit_event_direct({
                                "user_id": int(user_id),
                                "endpoint": "productivity:google_calendar",
                                "action": "index_add_event",
                                "tool": "google_calendar",
                                "status": "indexed",
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                            })
                        except Exception:
                            pass
                except Exception:
                    pass
            if task.task_type == "google_mail_send" and user_id is not None:
                try:
                    repo = OAuthTokenRepository()
                    tok = repo.get(user_id=int(user_id), provider="google")
                    access = tok.access_token if tok else None
                    if tok and tok.expires_at and tok.expires_at <= datetime.utcnow() and tok.refresh_token:
                        from app.config import settings
                        cid = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
                        cs = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", None)
                        if cid and cs:
                            async with httpx.AsyncClient(timeout=30) as client:
                                r = await client.post(
                                    "https://oauth2.googleapis.com/token",
                                    data={
                                        "client_id": str(cid),
                                        "client_secret": str(cs),
                                        "refresh_token": tok.refresh_token,
                                        "grant_type": "refresh_token",
                                    },
                                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                                )
                                r.raise_for_status()
                                data = r.json()
                                access = data.get("access_token") or access
                                exp_in = data.get("expires_in")
                                exp_at = datetime.utcnow() + timedelta(seconds=int(exp_in or 0)) if exp_in else None
                                repo.upsert(user_id=int(user_id), provider="google", access_token=str(access or tok.access_token), refresh_token=tok.refresh_token, expires_at=exp_at)
                    if access:
                        _t0 = __import__("time").perf_counter()
                        to = str(msg.get("to",""))
                        subject = str(msg.get("subject",""))
                        body = str(msg.get("body",""))
                        raw = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode("utf-8")
                        b64 = base64.urlsafe_b64encode(raw).decode("ascii")
                        async with httpx.AsyncClient(timeout=30) as client:
                            resp = await client.post(
                                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                                json={"raw": b64},
                                headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"}
                            )
                            resp.raise_for_status()
                        try:
                            _GOOGLE_MAIL_SENT_TOTAL.inc()
                            _PROD_WORKER_USER_EVENTS.labels(str(user_id), "mail_send", "ok").inc()
                            _PROD_WORKER_LATENCY.labels("mail_send").observe(__import__("time").perf_counter() - _t0)
                            _PROD_WORKER_USER_LATENCY.labels(str(user_id), "mail_send").observe(__import__("time").perf_counter() - _t0)
                        except Exception:
                            pass
                try:
                    record_audit_event_direct({
                        "user_id": int(user_id),
                        "endpoint": "productivity:google_mail",
                        "action": "mail_send",
                        "tool": "google_mail",
                        "status": "ok",
                        "latency_ms": None,
                        "trace_id": TRACE_ID.get(),
                    })
                except Exception:
                    pass
                if do_index and user_id is not None:
                    try:
                        _t0 = __import__("time").perf_counter()
                        client = get_qdrant_client()
                        coll = get_or_create_collection(f"user_{user_id}")
                        content = f"To: {str(msg.get('to',''))}\nSubject: {str(msg.get('subject',''))}\n{str(msg.get('body',''))}"
                        vec = embed_text(content)
                        pid = f"mail:{user_id}:{hash(content)}"
                        payload_q = {
                            "content": content,
                            "metadata": {
                                "type": "email_message",
                                "origin": "google",
                                "scope": "mail.send",
                                "user_id": str(user_id),
                                "timestamp": int(__import__("time").time()),
                            }
                        }
                        from qdrant_client import models as _m
                        point = _m.PointStruct(id=pid, vector=vec, payload=payload_q)
                        client.upsert(collection_name=coll, points=[point])
                        try:
                            _PROD_WORKER_USER_EVENTS.labels(str(user_id), "mail_index", "ok").inc()
                            _PROD_WORKER_LATENCY.labels("mail_index").observe(__import__("time").perf_counter() - _t0)
                            _PROD_WORKER_USER_LATENCY.labels(str(user_id), "mail_index").observe(__import__("time").perf_counter() - _t0)
                        except Exception:
                            pass
                except Exception:
                    pass
                except Exception as e:
                    try:
                        _PROD_WORKER_USER_EVENTS.labels(str(user_id or ""), "mail_send", "error").inc()
                    except Exception:
                        pass
            try:
                svc: ObservabilityService = getattr(__import__("builtins"), "app", None)
            except Exception:
                svc = None
        except Exception:
            return
    broker = await get_broker()
    t1 = broker.start_consumer(QUEUE_GOOGLE_CALENDAR, _handle, prefetch_count=10)
    t2 = broker.start_consumer(QUEUE_GOOGLE_MAIL, _handle, prefetch_count=10)
    return t1, t2