import asyncio
import base64
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import structlog

from app.core.infrastructure.logging_config import TRACE_ID
from app.core.infrastructure.message_broker import get_broker
from app.core.security.egress_policy import enforce_worker_http_egress
from app.db.vector_store import build_deterministic_point_id
from app.models.schemas import TaskMessage
from app.planes.knowledge import get_knowledge_facade
from app.repositories.observability_repository import record_audit_event_direct
from app.repositories.user_repository import ConsentRepository, OAuthTokenRepository
from app.services.google_productivity_service import (
    GoogleProductivityTokenUnavailableError,
    resolve_google_access_token,
)
from app.services.productivity_consent_service import require_productivity_consent

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


def _google_utc_datetime(timestamp: object) -> str:
    return (
        datetime.fromtimestamp(float(timestamp), UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


class ProductivityQueueUnavailableError(Exception):
    """The broker did not durably accept a requested external effect."""

QUEUE_GOOGLE_CALENDAR = "janus.productivity.google.calendar"
QUEUE_GOOGLE_MAIL = "janus.productivity.google.mail"
_GOOGLE_PROD_EVENTS_PUBLISHED = Counter(
    "google_productivity_events_published_total", "Eventos de produtividade publicados", ["type"]
)  # type: ignore
_GOOGLE_CALENDAR_EVENTS_INDEXED = Counter(
    "google_calendar_events_indexed_total", "Eventos do calendário indexados"
)  # type: ignore
_GOOGLE_MAIL_SENT_TOTAL = Counter("google_mail_sent_total", "Mensagens de e-mail enviadas")  # type: ignore
_PROD_WORKER_ERRORS = Counter(
    "productivity_worker_errors_total", "Erros no worker de produtividade", ["op", "cause"]
)  # type: ignore
_PROD_WORKER_LATENCY = Histogram(
    "productivity_worker_latency_seconds", "Latência no worker de produtividade", ["op"]
)  # type: ignore
_PROD_WORKER_USER_EVENTS = Counter(
    "productivity_worker_user_events_total",
    "Eventos por usuário no worker",
    ["user_id", "op", "status"],
)  # type: ignore
_PROD_WORKER_USER_LATENCY = Histogram(
    "productivity_worker_user_latency_seconds",
    "Latência por usuário no worker de produtividade",
    ["user_id", "op"],
)  # type: ignore


async def publish_google_calendar_add_event(
    user_id: int, event: dict[str, Any], index: bool
) -> str:
    task_id = uuid4().hex
    msg = TaskMessage(
        task_id=task_id,
        task_type="google_calendar_add_event",
        payload={"user_id": user_id, "event": event, "index": bool(index)},
        timestamp=__import__("time").time(),
    )
    try:
        cm = _tracer.start_as_current_span("google.calendar.publish") if _OTEL else nullcontext()
        with cm:  # type: ignore
            broker = await get_broker()
            delivered = await broker.publish(
                QUEUE_GOOGLE_CALENDAR, msg.to_msgpack(), use_msgpack=True, priority=5
            )
            if not delivered:
                raise ProductivityQueueUnavailableError(
                    "Broker indisponível; evento de calendário não foi enfileirado."
                )
        try:
            _GOOGLE_PROD_EVENTS_PUBLISHED.labels("google_calendar_add_event").inc()
        except Exception:
            pass
    except ProductivityQueueUnavailableError:
        logger.warning("Broker offline", task_id=task_id)
        raise
    except Exception as exc:
        logger.error("Falha ao publicar evento de calendário", task_id=task_id, exc_info=exc)
        raise ProductivityQueueUnavailableError(
            "Falha ao enfileirar evento de calendário."
        ) from exc
    try:
        record_audit_event_direct(
            {
                "user_id": int(user_id),
                "endpoint": "productivity:google_calendar",
                "action": "publish_add_event",
                "tool": "google_calendar",
                "status": "queued",
                "latency_ms": None,
                "trace_id": TRACE_ID.get(),
            }
        )
    except Exception:
        pass
    return task_id


async def publish_google_mail_send(user_id: int, message: dict[str, Any], index: bool) -> str:
    task_id = uuid4().hex
    msg = TaskMessage(
        task_id=task_id,
        task_type="google_mail_send",
        payload={"user_id": user_id, "message": message, "index": bool(index)},
        timestamp=__import__("time").time(),
    )
    try:
        cm = _tracer.start_as_current_span("google.mail.publish") if _OTEL else nullcontext()
        with cm:  # type: ignore
            broker = await get_broker()
            delivered = await broker.publish(
                QUEUE_GOOGLE_MAIL, msg.to_msgpack(), use_msgpack=True, priority=5
            )
            if not delivered:
                raise ProductivityQueueUnavailableError(
                    "Broker indisponível; e-mail não foi enfileirado."
                )
        try:
            _GOOGLE_PROD_EVENTS_PUBLISHED.labels("google_mail_send").inc()
        except Exception:
            pass
    except ProductivityQueueUnavailableError:
        logger.warning("Broker offline", task_id=task_id)
        raise
    except Exception as exc:
        logger.error("Falha ao publicar e-mail", task_id=task_id, exc_info=exc)
        raise ProductivityQueueUnavailableError("Falha ao enfileirar e-mail.") from exc
    try:
        record_audit_event_direct(
            {
                "user_id": int(user_id),
                "endpoint": "productivity:google_mail",
                "action": "publish_mail_send",
                "tool": "google_mail",
                "status": "queued",
                "latency_ms": None,
                "trace_id": TRACE_ID.get(),
            }
        )
    except Exception:
        pass
    return task_id


async def _handle_google_productivity_task(task: TaskMessage) -> None:
    try:
        payload = task.payload or {}
        user_id = int(payload.get("user_id")) if payload.get("user_id") is not None else None
        ev = payload.get("event") or {}
        msg = payload.get("message") or {}
        do_index = bool(payload.get("index"))
        if task.task_type == "google_calendar_add_event" and user_id is not None:
            try:
                require_productivity_consent(
                    ConsentRepository(),
                    user_id=user_id,
                    scope="calendar.write",
                )
                repo = OAuthTokenRepository()
                tok = repo.get(user_id=int(user_id), provider="google")
                try:
                    access = await resolve_google_access_token(
                        repo=repo,
                        token=tok,
                        user_id=int(user_id),
                    )
                except GoogleProductivityTokenUnavailableError as exc:
                    raise RuntimeError(
                        "OAuth access token unavailable for Google Calendar"
                    ) from exc
                if access:
                    _t0 = __import__("time").perf_counter()
                    calendar_url = (
                        "https://www.googleapis.com/calendar/v3/calendars/primary/events"
                    )
                    allowed_calendar_url = enforce_worker_http_egress(
                        calendar_url, tool="google_productivity_worker"
                    )
                    if not allowed_calendar_url:
                        raise RuntimeError("Egress blocked for google calendar")
                    async with httpx.AsyncClient(timeout=30) as client:
                        req = {
                            "summary": ev.get("title"),
                            "start": {
                                "dateTime": _google_utc_datetime(ev.get("start_ts"))
                            },
                            "end": {
                                "dateTime": _google_utc_datetime(ev.get("end_ts"))
                            },
                            "location": ev.get("location") or None,
                            "description": ev.get("notes") or None,
                        }
                        resp = await client.post(
                            allowed_calendar_url,
                            json=req,
                            headers={
                                "Authorization": f"Bearer {access}",
                                "Content-Type": "application/json",
                            },
                        )
                        resp.raise_for_status()
                    try:
                        _PROD_WORKER_USER_EVENTS.labels(
                            str(user_id), "calendar_send", "ok"
                        ).inc()
                        _PROD_WORKER_LATENCY.labels("calendar_send").observe(
                            __import__("time").perf_counter() - _t0
                        )
                        _PROD_WORKER_USER_LATENCY.labels("[REDACTED_PII]", "calendar_send").observe(
                            __import__("time").perf_counter() - _t0
                        )
                    except Exception:
                        pass
                    try:
                        record_audit_event_direct(
                            {
                                "user_id": int(user_id),
                                "endpoint": "productivity:google_calendar",
                                "action": "calendar_add_event",
                                "tool": "google_calendar",
                                "status": "ok",
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                            }
                        )
                    except Exception:
                        pass
            except Exception as e:
                try:
                    _PROD_WORKER_ERRORS.labels("calendar_send", e.__class__.__name__).inc()
                except Exception:
                    pass
                try:
                    record_audit_event_direct(
                        {
                            "user_id": int(user_id) if user_id is not None else None,
                            "endpoint": "productivity:google_calendar",
                            "action": "calendar_add_event",
                            "tool": "google_calendar",
                            "status": "error",
                            "latency_ms": None,
                            "trace_id": TRACE_ID.get(),
                        }
                    )
                except Exception:
                    pass
                try:
                    _PROD_WORKER_USER_EVENTS.labels(
                        str(user_id or ""), "calendar_send", "error"
                    ).inc()
                except Exception:
                    pass
                raise
            if do_index and user_id is not None:
                try:
                    _t0 = __import__("time").perf_counter()
                    title = str(ev.get("title", ""))
                    loc = str(ev.get("location", ""))
                    content = f"{title} @ {loc}"
                    pid = build_deterministic_point_id(
                        "google-calendar-event",
                        user_id,
                        task.task_id,
                    )
                    payload_q = {
                        "content": content,
                        "type": "calendar_event",
                        "ts_ms": int(ev.get("start_ts") or 0),
                        "composite_id": pid,
                        "metadata": {
                            "type": "calendar_event",
                            "origin": "google",
                            "scope": "calendar.write",
                            "task_id": task.task_id,
                            "user_id": str(user_id),
                            "timestamp": int(ev.get("start_ts") or 0),
                            "ts_ms": int(ev.get("start_ts") or 0),
                        },
                    }
                    await get_knowledge_facade().index_memory_event(
                        user_id=str(user_id),
                        content=content,
                        point_id=pid,
                        payload=payload_q,
                    )
                    try:
                        _GOOGLE_CALENDAR_EVENTS_INDEXED.inc()
                        _PROD_WORKER_USER_EVENTS.labels(
                            str(user_id), "calendar_index", "ok"
                        ).inc()
                        _PROD_WORKER_LATENCY.labels("calendar_index").observe(
                            __import__("time").perf_counter() - _t0
                        )
                        _PROD_WORKER_USER_LATENCY.labels(
                            str(user_id), "calendar_index"
                        ).observe(__import__("time").perf_counter() - _t0)
                    except Exception:
                        pass
                    try:
                        record_audit_event_direct(
                            {
                                "user_id": int(user_id),
                                "endpoint": "productivity:google_calendar",
                                "action": "index_add_event",
                                "tool": "google_calendar",
                                "status": "indexed",
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                            }
                        )
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        _PROD_WORKER_ERRORS.labels("calendar_index", e.__class__.__name__).inc()
                    except Exception:
                        pass
                    try:
                        record_audit_event_direct(
                            {
                                "user_id": int(user_id),
                                "endpoint": "productivity:google_calendar",
                                "action": "index_add_event",
                                "tool": "google_calendar",
                                "status": "error",
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                            }
                        )
                    except Exception:
                        pass
        if task.task_type == "google_mail_send" and user_id is not None:
            try:
                require_productivity_consent(
                    ConsentRepository(),
                    user_id=user_id,
                    scope="mail.send",
                )
                repo = OAuthTokenRepository()
                tok = repo.get(user_id=int(user_id), provider="google")
                try:
                    access = await resolve_google_access_token(
                        repo=repo,
                        token=tok,
                        user_id=int(user_id),
                    )
                except GoogleProductivityTokenUnavailableError as exc:
                    raise RuntimeError(
                        "OAuth access token unavailable for Gmail"
                    ) from exc
                if access:
                    _t0 = __import__("time").perf_counter()
                    to = str(msg.get("to", ""))
                    subject = str(msg.get("subject", ""))
                    body = str(msg.get("body", ""))
                    raw = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}".encode()
                    b64 = base64.urlsafe_b64encode(raw).decode("ascii")
                    gmail_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                    allowed_gmail_url = enforce_worker_http_egress(
                        gmail_url, tool="google_productivity_worker"
                    )
                    if not allowed_gmail_url:
                        raise RuntimeError("Egress blocked for gmail send")
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.post(
                            allowed_gmail_url,
                            json={"raw": b64},
                            headers={
                                "Authorization": f"Bearer {access}",
                                "Content-Type": "application/json",
                            },
                        )
                        resp.raise_for_status()
                    try:
                        _GOOGLE_MAIL_SENT_TOTAL.inc()
                        _PROD_WORKER_USER_EVENTS.labels("[REDACTED_PII]", "mail_send", "ok").inc()
                        _PROD_WORKER_LATENCY.labels("mail_send").observe(
                            __import__("time").perf_counter() - _t0
                        )
                        _PROD_WORKER_USER_LATENCY.labels("[REDACTED_PII]", "mail_send").observe(
                            __import__("time").perf_counter() - _t0
                        )
                    except Exception:
                        pass
                try:
                    record_audit_event_direct(
                        {
                            "user_id": int(user_id),
                            "endpoint": "productivity:google_mail",
                            "action": "mail_send",
                            "tool": "google_mail",
                            "status": "ok",
                            "latency_ms": None,
                            "trace_id": TRACE_ID.get(),
                        }
                    )
                except Exception as e:
                    try:
                        _PROD_WORKER_ERRORS.labels("mail_send", e.__class__.__name__).inc()
                    except Exception:
                        pass
                if do_index and user_id is not None:
                    try:
                        _t0 = __import__("time").perf_counter()
                        content = f"To: {msg.get('to', '')!s}\nSubject: {msg.get('subject', '')!s}\n{msg.get('body', '')!s}"
                        composite_id = (
                            f"mail:{user_id}:{msg.get('to', '')!s}:{msg.get('subject', '')!s}:{content}"
                        )
                        pid = str(uuid5(NAMESPACE_URL, composite_id))
                        payload_q = {
                            "content": content,
                            "type": "email_message",
                            "ts_ms": int(__import__("time").time() * 1000),
                            "composite_id": composite_id,
                            "metadata": {
                                "type": "email_message",
                                "origin": "google",
                                "scope": "mail.send",
                                "user_id": str(user_id),
                                "timestamp": int(__import__("time").time() * 1000),
                                "ts_ms": int(__import__("time").time() * 1000),
                            },
                        }
                        await get_knowledge_facade().index_memory_event(
                            user_id=str(user_id),
                            content=content,
                            point_id=pid,
                            payload=payload_q,
                        )
                        try:
                            _PROD_WORKER_USER_EVENTS.labels(
                                str(user_id), "mail_index", "ok"
                            ).inc()
                            _PROD_WORKER_LATENCY.labels("mail_index").observe(
                                __import__("time").perf_counter() - _t0
                            )
                            _PROD_WORKER_USER_LATENCY.labels(
                                str(user_id), "mail_index"
                            ).observe(__import__("time").perf_counter() - _t0)
                        except Exception:
                            pass
                        try:
                            record_audit_event_direct(
                                {
                                    "user_id": int(user_id),
                                    "endpoint": "productivity:google_mail",
                                    "action": "index_sent_mail",
                                    "tool": "google_mail",
                                    "status": "indexed",
                                    "latency_ms": None,
                                    "trace_id": TRACE_ID.get(),
                                }
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        try:
                            _PROD_WORKER_ERRORS.labels("mail_index", e.__class__.__name__).inc()
                        except Exception:
                            pass
                        try:
                            record_audit_event_direct(
                                {
                                    "user_id": int(user_id),
                                    "endpoint": "productivity:google_mail",
                                    "action": "index_sent_mail",
                                    "tool": "google_mail",
                                    "status": "error",
                                    "latency_ms": None,
                                    "trace_id": TRACE_ID.get(),
                                }
                            )
                        except Exception:
                            pass
            except Exception as e:
                try:
                    _PROD_WORKER_ERRORS.labels("mail_send", e.__class__.__name__).inc()
                except Exception:
                    pass
                try:
                    record_audit_event_direct(
                        {
                            "user_id": int(user_id),
                            "endpoint": "productivity:google_mail",
                            "action": "mail_send",
                            "tool": "google_mail",
                            "status": "error",
                            "latency_ms": None,
                            "trace_id": TRACE_ID.get(),
                        }
                    )
                except Exception:
                    pass
                try:
                    _PROD_WORKER_USER_EVENTS.labels(
                        str(user_id or ""), "mail_send", "error"
                    ).inc()
                except Exception:
                    pass
                raise
        try:
            getattr(__import__("builtins"), "app", None)
        except Exception:
            pass
    except Exception:
        raise


class GoogleProductivityWorker:
    name = "google_productivity"

    def __init__(self, prefetch_count: int = 10):
        self._prefetch_count = prefetch_count
        self._consumer_tasks = []
        self._running = False

    async def start(self) -> None:
        broker = await get_broker()
        t1 = broker.start_consumer(
            QUEUE_GOOGLE_CALENDAR,
            _handle_google_productivity_task,
            prefetch_count=self._prefetch_count,
        )
        t2 = broker.start_consumer(
            QUEUE_GOOGLE_MAIL,
            _handle_google_productivity_task,
            prefetch_count=self._prefetch_count,
        )
        self._consumer_tasks = [t1, t2]
        self._running = True
        logger.info("GoogleProductivityWorker started")

    async def stop(self) -> None:
        self._running = False
        for task in self._consumer_tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._consumer_tasks = []
        logger.info("GoogleProductivityWorker stopped")

    def is_healthy(self) -> bool:
        return (
            self._running
            and bool(self._consumer_tasks)
            and all(t is not None and not t.done() for t in self._consumer_tasks)
        )

    def get_status(self) -> dict:
        return {"running": self._running}


async def start_google_productivity_consumer():
    instance = GoogleProductivityWorker()
    await instance.start()
    return instance
