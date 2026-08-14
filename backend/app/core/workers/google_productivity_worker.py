import asyncio
import base64
from datetime import UTC, datetime
from email.message import EmailMessage
from email.policy import SMTP
from typing import Any, cast
from uuid import uuid4

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
from app.services.productivity_task_service import (
    ProductivityTaskOperation,
    ProductivityTaskService,
)

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
    lifecycle = ProductivityTaskService()
    msg = TaskMessage(
        task_id=task_id,
        task_type="google_calendar_add_event",
        payload={"user_id": user_id, "event": event, "index": bool(index)},
        timestamp=__import__("time").time(),
    )
    try:
        lifecycle.create_queued(
            task_id=task_id,
            owner_user_id=user_id,
            operation="google_calendar_add_event",
        )
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
    except ProductivityQueueUnavailableError as exc:
        try:
            lifecycle.fail(
                task_id=task_id,
                owner_user_id=user_id,
                error_code="queue_unavailable",
            )
        except Exception as lifecycle_exc:
            logger.error(
                "Falha ao persistir indisponibilidade da fila",
                task_id=task_id,
                exc_info=lifecycle_exc,
            )
        logger.warning("Broker offline", task_id=task_id)
        raise exc
    except Exception as exc:
        try:
            lifecycle.fail(
                task_id=task_id,
                owner_user_id=user_id,
                error_code="queue_publish_error",
            )
        except Exception:
            pass
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
    lifecycle = ProductivityTaskService()
    msg = TaskMessage(
        task_id=task_id,
        task_type="google_mail_send",
        payload={"user_id": user_id, "message": message, "index": bool(index)},
        timestamp=__import__("time").time(),
    )
    try:
        lifecycle.create_queued(
            task_id=task_id,
            owner_user_id=user_id,
            operation="google_mail_send",
        )
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
    except ProductivityQueueUnavailableError as exc:
        try:
            lifecycle.fail(
                task_id=task_id,
                owner_user_id=user_id,
                error_code="queue_unavailable",
            )
        except Exception as lifecycle_exc:
            logger.error(
                "Falha ao persistir indisponibilidade da fila",
                task_id=task_id,
                exc_info=lifecycle_exc,
            )
        logger.warning("Broker offline", task_id=task_id)
        raise exc
    except Exception as exc:
        try:
            lifecycle.fail(
                task_id=task_id,
                owner_user_id=user_id,
                error_code="queue_publish_error",
            )
        except Exception:
            pass
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
    lifecycle = ProductivityTaskService()
    lifecycle_started = False
    user_id: int | None = None
    try:
        payload = task.payload or {}
        user_id = int(payload.get("user_id")) if payload.get("user_id") is not None else None
        if user_id is None or task.task_type not in {
            "google_calendar_add_event",
            "google_mail_send",
        }:
            raise ValueError("Invalid Google productivity task")
        should_execute = lifecycle.start_or_create(
            task_id=task.task_id,
            owner_user_id=user_id,
            operation=cast(ProductivityTaskOperation, task.task_type),
        )
        lifecycle_started = True
        if not should_execute:
            logger.info("Productivity task already completed", task_id=task.task_id)
            return
        provider_resource_id: str | None = None
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
                        reconciliation = await client.get(
                            allowed_calendar_url,
                            params={
                                "privateExtendedProperty": (
                                    f"janusTaskId={task.task_id}"
                                ),
                                "maxResults": 1,
                                "showDeleted": "false",
                            },
                            headers={"Authorization": f"Bearer {access}"},
                        )
                        reconciliation.raise_for_status()
                        reconciliation_payload = reconciliation.json()
                        existing_items = (
                            reconciliation_payload.get("items", [])
                            if isinstance(reconciliation_payload, dict)
                            else []
                        )
                        if not isinstance(existing_items, list):
                            raise RuntimeError(
                                "Invalid Google Calendar reconciliation response"
                            )
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
                            "extendedProperties": {
                                "private": {"janusTaskId": task.task_id}
                            },
                        }
                        existing_event = next(
                            (
                                item
                                for item in existing_items
                                if isinstance(item, dict)
                                and isinstance(item.get("id"), str)
                                and item.get("id")
                            ),
                            None,
                        )
                        if existing_event is not None:
                            provider_event_id = str(existing_event["id"])
                            effect_status = "reconciled"
                        else:
                            resp = await client.post(
                                allowed_calendar_url,
                                json=req,
                                headers={
                                    "Authorization": f"Bearer {access}",
                                    "Content-Type": "application/json",
                                },
                            )
                            resp.raise_for_status()
                            created_event = resp.json()
                            provider_event_id = (
                                str(created_event.get("id"))
                                if isinstance(created_event, dict)
                                and created_event.get("id")
                                else ""
                            )
                            if not provider_event_id:
                                raise RuntimeError(
                                    "Google Calendar response missing event id"
                                )
                            effect_status = "ok"
                    provider_resource_id = provider_event_id
                    try:
                        _PROD_WORKER_USER_EVENTS.labels(
                            str(user_id), "calendar_send", effect_status
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
                                "status": effect_status,
                                "latency_ms": None,
                                "trace_id": TRACE_ID.get(),
                                "detail": {
                                    "provider_event_id": provider_event_id,
                                    "task_id": task.task_id,
                                },
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
                            "provider_event_id": provider_event_id,
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
                    rfc_message_id = f"<janus.{task.task_id}@janus.invalid>"
                    email_message = EmailMessage(policy=SMTP)
                    email_message["To"] = to
                    email_message["Subject"] = subject
                    email_message["Message-ID"] = rfc_message_id
                    email_message.set_content(body)
                    raw = email_message.as_bytes()
                    b64 = base64.urlsafe_b64encode(raw).decode("ascii")
                    gmail_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
                    gmail_list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
                    allowed_gmail_url = enforce_worker_http_egress(
                        gmail_url, tool="google_productivity_worker"
                    )
                    allowed_gmail_list_url = enforce_worker_http_egress(
                        gmail_list_url, tool="google_productivity_worker"
                    )
                    if not allowed_gmail_url or not allowed_gmail_list_url:
                        raise RuntimeError("Egress blocked for gmail send")
                    async with httpx.AsyncClient(timeout=30) as client:
                        reconciliation = await client.get(
                            allowed_gmail_list_url,
                            params={
                                "q": f"in:sent rfc822msgid:{rfc_message_id}",
                                "maxResults": 1,
                                "includeSpamTrash": "false",
                            },
                            headers={"Authorization": f"Bearer {access}"},
                        )
                        reconciliation.raise_for_status()
                        reconciliation_payload = reconciliation.json()
                        existing_messages = (
                            reconciliation_payload.get("messages", [])
                            if isinstance(reconciliation_payload, dict)
                            else []
                        )
                        if not isinstance(existing_messages, list):
                            raise RuntimeError("Invalid Gmail reconciliation response")
                        existing_message = next(
                            (
                                item
                                for item in existing_messages
                                if isinstance(item, dict)
                                and isinstance(item.get("id"), str)
                                and item.get("id")
                            ),
                            None,
                        )
                        if existing_message is not None:
                            provider_resource_id = str(existing_message["id"])
                            effect_status = "reconciled"
                        else:
                            resp = await client.post(
                                allowed_gmail_url,
                                json={"raw": b64},
                                headers={
                                    "Authorization": f"Bearer {access}",
                                    "Content-Type": "application/json",
                                },
                            )
                            resp.raise_for_status()
                            sent_message = resp.json()
                            provider_resource_id = (
                                str(sent_message.get("id"))
                                if isinstance(sent_message, dict)
                                and sent_message.get("id")
                                else None
                            )
                            if not provider_resource_id:
                                raise RuntimeError("Gmail response missing message id")
                            effect_status = "ok"
                    try:
                        _GOOGLE_MAIL_SENT_TOTAL.inc()
                        _PROD_WORKER_USER_EVENTS.labels(
                            "[REDACTED_PII]", "mail_send", effect_status
                        ).inc()
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
                            "status": effect_status,
                            "latency_ms": None,
                            "trace_id": TRACE_ID.get(),
                            "detail": {
                                "provider_message_id": provider_resource_id,
                                "task_id": task.task_id,
                            },
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
                        pid = build_deterministic_point_id(
                            "google-mail-message",
                            user_id,
                            task.task_id,
                        )
                        payload_q = {
                            "content": content,
                            "type": "email_message",
                            "ts_ms": int(__import__("time").time() * 1000),
                            "composite_id": pid,
                            "metadata": {
                                "type": "email_message",
                                "origin": "google",
                                "scope": "mail.send",
                                "task_id": task.task_id,
                                "provider_message_id": provider_resource_id,
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
        lifecycle.succeed(
            task_id=task.task_id,
            owner_user_id=user_id,
            provider_resource_id=provider_resource_id,
        )
        try:
            getattr(__import__("builtins"), "app", None)
        except Exception:
            pass
    except Exception as exc:
        if lifecycle_started and user_id is not None:
            try:
                lifecycle.fail(
                    task_id=task.task_id,
                    owner_user_id=user_id,
                    error_code=exc.__class__.__name__,
                )
            except Exception as lifecycle_exc:
                logger.error(
                    "Falha ao persistir erro da tarefa de produtividade",
                    task_id=task.task_id,
                    exc_info=lifecycle_exc,
                )
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
