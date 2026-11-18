from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import structlog
from app.config import settings
from app.repositories.chat_stream_repository import (
    ChatStreamClaimLost,
    ChatStreamRepository,
    ChatStreamRunState,
)

logger = structlog.get_logger(__name__)

_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
_TERMINAL_EVENTS = frozenset({"done", "error"})


class ChatStreamRunServiceError(RuntimeError):
    pass


class InvalidChatStreamIdempotencyKey(ChatStreamRunServiceError):
    pass


@dataclass(frozen=True)
class ChatStreamAttachment:
    run: ChatStreamRunState
    created: bool
    producer_started: bool


def validate_chat_stream_idempotency_key(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not _IDEMPOTENCY_KEY.fullmatch(normalized):
        raise InvalidChatStreamIdempotencyKey(
            "Idempotency-Key must contain 16-128 safe opaque characters"
        )
    return normalized


def chat_stream_request_fingerprint(
    *,
    conversation_id: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "conversation_id": str(conversation_id),
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_name(payload: str) -> str | None:
    for line in payload.replace("\r\n", "\n").splitlines():
        if line.startswith("event:"):
            return line.split(":", 1)[1].strip() or "message"
    return None


def _complete_sse_blocks(payload: str) -> list[str]:
    normalized = str(payload or "").replace("\r\n", "\n")
    blocks = [block for block in normalized.split("\n\n") if block.strip()]
    return [f"{block}\n\n" for block in blocks]


def _with_event_id(payload: str, sequence: int) -> str:
    return f"id: {sequence}\n{payload.lstrip()}"


def _terminal_error_payload(*, code: str, message: str) -> str:
    body = json.dumps(
        {
            "code": code,
            "message": message,
            "category": "availability",
            "retryable": False,
            "http_status": None,
        },
        ensure_ascii=False,
    )
    return f"event: error\ndata: {body}\n\n"


class ChatStreamRunService:
    def __init__(self, repository: ChatStreamRepository | None = None) -> None:
        self._repository = repository or ChatStreamRepository()
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._tasks_lock = asyncio.Lock()

    @property
    def active_producer_count(self) -> int:
        return sum(1 for task in self._tasks.values() if not task.done())

    async def begin_or_attach(
        self,
        *,
        owner_user_id: int,
        session_id: int | str,
        request_id: str,
        request_fingerprint: str,
        producer_factory: Callable[[], AsyncIterator[str]],
    ) -> ChatStreamAttachment:
        run, created = await asyncio.to_thread(
            self._repository.begin_or_get,
            owner_user_id=owner_user_id,
            session_id=session_id,
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            retention_hours=int(settings.CHAT_STREAM_RUN_RETENTION_HOURS),
        )

        producer_started = False
        if run.status == "pending":
            producer_token = uuid4().hex
            claimed = await asyncio.to_thread(
                self._repository.claim_pending,
                run_id=run.id,
                producer_token=producer_token,
                lease_seconds=int(settings.CHAT_STREAM_RUN_LEASE_SECONDS),
            )
            if claimed:
                producer_started = True
                await self._track_producer(
                    run_id=run.id,
                    producer_token=producer_token,
                    producer_factory=producer_factory,
                )
                refreshed = await asyncio.to_thread(
                    self._repository.get_run,
                    run_id=run.id,
                    owner_user_id=owner_user_id,
                )
                if refreshed is not None:
                    run = refreshed

        logger.info(
            "chat_stream_run_attached",
            run_id=run.id,
            created=created,
            producer_started=producer_started,
            status=run.status,
            owner_user_id="[REDACTED_PII]",
        )
        return ChatStreamAttachment(
            run=run,
            created=created,
            producer_started=producer_started,
        )

    async def _track_producer(
        self,
        *,
        run_id: str,
        producer_token: str,
        producer_factory: Callable[[], AsyncIterator[str]],
    ) -> None:
        async with self._tasks_lock:
            current = self._tasks.get(run_id)
            if current is not None and not current.done():
                return
            task = asyncio.create_task(
                self._produce(
                    run_id=run_id,
                    producer_token=producer_token,
                    producer_factory=producer_factory,
                ),
                name=f"chat-stream-producer:{run_id}",
            )
            self._tasks[run_id] = task

            def producer_done(completed: asyncio.Task[None]) -> None:
                self._producer_done(run_id, completed)

            task.add_done_callback(producer_done)

    def _producer_done(self, run_id: str, task: asyncio.Task[None]) -> None:
        self._tasks.pop(run_id, None)
        if task.cancelled():
            logger.warning("chat_stream_producer_cancelled", run_id=run_id)
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "chat_stream_producer_failed",
                run_id=run_id,
                error_type=type(error).__name__,
            )

    async def _produce(
        self,
        *,
        run_id: str,
        producer_token: str,
        producer_factory: Callable[[], AsyncIterator[str]],
    ) -> None:
        consumer = asyncio.create_task(
            self._consume_source(
                run_id=run_id,
                producer_token=producer_token,
                producer_factory=producer_factory,
            ),
            name=f"chat-stream-source:{run_id}",
        )
        heartbeat = asyncio.create_task(
            self._heartbeat(run_id=run_id, producer_token=producer_token),
            name=f"chat-stream-lease:{run_id}",
        )
        try:
            done, _ = await asyncio.wait(
                {consumer, heartbeat},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if heartbeat in done:
                consumer.cancel()
                await asyncio.gather(consumer, return_exceptions=True)
                await heartbeat
                return
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            await consumer
        except asyncio.CancelledError:
            consumer.cancel()
            heartbeat.cancel()
            await asyncio.gather(consumer, heartbeat, return_exceptions=True)
            await self._fail_owned_run(
                run_id=run_id,
                producer_token=producer_token,
                code="CHAT_STREAM_PRODUCER_CANCELLED",
                message="Chat stream producer was interrupted",
            )
            raise

    async def _heartbeat(self, *, run_id: str, producer_token: str) -> None:
        lease_seconds = int(settings.CHAT_STREAM_RUN_LEASE_SECONDS)
        interval = max(1.0, lease_seconds / 3)
        while True:
            await asyncio.sleep(interval)
            renewed = await asyncio.to_thread(
                self._repository.renew_lease,
                run_id=run_id,
                producer_token=producer_token,
                lease_seconds=lease_seconds,
            )
            if not renewed:
                raise ChatStreamClaimLost("Chat stream producer lease was lost")

    async def _consume_source(
        self,
        *,
        run_id: str,
        producer_token: str,
        producer_factory: Callable[[], AsyncIterator[str]],
    ) -> None:
        terminal_event: str | None = None
        try:
            source = producer_factory()
            async for raw_chunk in source:
                for chunk in _complete_sse_blocks(raw_chunk):
                    await asyncio.to_thread(
                        self._repository.append_event,
                        run_id=run_id,
                        producer_token=producer_token,
                        payload=chunk,
                        lease_seconds=int(settings.CHAT_STREAM_RUN_LEASE_SECONDS),
                    )
                    event_name = _event_name(chunk)
                    if event_name in _TERMINAL_EVENTS:
                        terminal_event = event_name
            if terminal_event is None:
                await self._fail_owned_run(
                    run_id=run_id,
                    producer_token=producer_token,
                    code="CHAT_STREAM_ENDED_WITHOUT_TERMINAL_EVENT",
                    message="Chat stream ended before a terminal event",
                )
                return
            await asyncio.to_thread(
                self._repository.finish,
                run_id=run_id,
                producer_token=producer_token,
                status="completed" if terminal_event == "done" else "failed",
                error_code=None if terminal_event == "done" else "CHAT_STREAM_FAILED",
            )
        except asyncio.CancelledError:
            raise
        except ChatStreamClaimLost:
            logger.warning("chat_stream_claim_lost", run_id=run_id)
            raise
        except Exception as exc:
            logger.error(
                "chat_stream_source_failed",
                run_id=run_id,
                error_type=type(exc).__name__,
            )
            await self._fail_owned_run(
                run_id=run_id,
                producer_token=producer_token,
                code="CHAT_STREAM_INTERNAL_FAILURE",
                message="Chat stream failed",
            )

    async def _fail_owned_run(
        self,
        *,
        run_id: str,
        producer_token: str,
        code: str,
        message: str,
    ) -> None:
        payload = _terminal_error_payload(code=code, message=message)
        try:
            await asyncio.to_thread(
                self._repository.append_event,
                run_id=run_id,
                producer_token=producer_token,
                payload=payload,
                lease_seconds=int(settings.CHAT_STREAM_RUN_LEASE_SECONDS),
            )
        except ChatStreamClaimLost:
            return
        await asyncio.to_thread(
            self._repository.finish,
            run_id=run_id,
            producer_token=producer_token,
            status="failed",
            error_code=code,
        )

    async def stream_events(
        self,
        *,
        run_id: str,
        owner_user_id: int,
        after_sequence: int = 0,
    ) -> AsyncIterator[str]:
        cursor = max(0, int(after_sequence))
        poll_seconds = max(0.05, int(settings.CHAT_STREAM_EVENT_POLL_INTERVAL_MS) / 1000)
        heartbeat_seconds = max(1, int(settings.CHAT_STREAM_SUBSCRIBER_HEARTBEAT_SECONDS))
        elapsed_without_event = 0.0

        while True:
            run = await asyncio.to_thread(
                self._repository.get_run,
                run_id=run_id,
                owner_user_id=owner_user_id,
            )
            if run is None:
                raise ChatStreamRunServiceError("Chat stream run not found")

            if run.status == "running" and run.lease_until is not None:
                interrupted = await asyncio.to_thread(
                    self._repository.interrupt_stale_run,
                    run_id=run_id,
                    owner_user_id=owner_user_id,
                    error_payload=_terminal_error_payload(
                        code="CHAT_STREAM_INTERRUPTED",
                        message="Chat stream execution was interrupted and will not be replayed",
                    ),
                    error_code="CHAT_STREAM_INTERRUPTED",
                )
                if interrupted:
                    continue

            events = await asyncio.to_thread(
                self._repository.list_events,
                run_id=run_id,
                owner_user_id=owner_user_id,
                after_sequence=cursor,
            )
            if events:
                for event in events:
                    cursor = event.sequence
                    yield _with_event_id(event.payload, event.sequence)
                elapsed_without_event = 0.0
                continue

            if run.terminal and cursor >= run.last_event_sequence:
                return

            await asyncio.sleep(poll_seconds)
            elapsed_without_event += poll_seconds
            if elapsed_without_event >= heartbeat_seconds:
                elapsed_without_event = 0.0
                yield ": heartbeat\n\n"


_chat_stream_run_service = ChatStreamRunService()


def get_chat_stream_run_service() -> ChatStreamRunService:
    return _chat_stream_run_service
