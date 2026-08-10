from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.repositories.chat_rest_repository import (
    ChatRestIdempotencyConflict,
    ChatRestRepository,
    ChatRestRunState,
)


class ChatRestRunServiceError(RuntimeError):
    pass


class ChatRestRequestInProgress(ChatRestRunServiceError):
    pass


_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def validate_chat_rest_idempotency_key(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    resolved = value.strip()
    if not _KEY_PATTERN.fullmatch(resolved):
        raise ValueError("Invalid Idempotency-Key")
    return resolved


def chat_rest_request_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChatRestAttachment:
    run: ChatRestRunState
    producer_token: str | None
    replay_result: dict[str, Any] | None

    @property
    def owns_execution(self) -> bool:
        return self.producer_token is not None


class ChatRestRunService:
    def __init__(self, repository: ChatRestRepository | None = None) -> None:
        self._repository = repository or ChatRestRepository()
        self._retention_hours = int(os.getenv("CHAT_REST_RUN_RETENTION_HOURS", "24"))
        self._lease_seconds = int(os.getenv("CHAT_REST_RUN_LEASE_SECONDS", "300"))

    def attach(
        self,
        *,
        owner_user_id: str,
        conversation_id: str,
        request_id: str,
        request_fingerprint: str,
    ) -> ChatRestAttachment:
        run, _created = self._repository.begin_or_get(
            owner_user_id=owner_user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            retention_hours=self._retention_hours,
        )
        if run.status == "completed" and run.result is not None:
            return ChatRestAttachment(run=run, producer_token=None, replay_result=run.result)
        if run.status in {"running", "failed"}:
            raise ChatRestRequestInProgress(
                "The idempotent request is already running or requires a new key"
            )
        producer_token = uuid4().hex
        if not self._repository.claim_pending(
            run_id=run.id,
            producer_token=producer_token,
            lease_seconds=self._lease_seconds,
        ):
            raise ChatRestRequestInProgress("The idempotent request is already running")
        return ChatRestAttachment(
            run=run,
            producer_token=producer_token,
            replay_result=None,
        )

    def complete(self, attachment: ChatRestAttachment, result: dict[str, Any]) -> None:
        if not attachment.producer_token:
            raise ChatRestRunServiceError("Cannot complete a replay attachment")
        if not self._repository.finish(
            run_id=attachment.run.id,
            producer_token=attachment.producer_token,
            status="completed",
            result=result,
        ):
            raise ChatRestRunServiceError("REST execution lease was lost")

    def fail(self, attachment: ChatRestAttachment, error_code: str) -> None:
        if not attachment.producer_token:
            return
        self._repository.finish(
            run_id=attachment.run.id,
            producer_token=attachment.producer_token,
            status="failed",
            error_code=error_code,
        )

    def cleanup_expired(self) -> int:
        return self._repository.cleanup_expired()


_chat_rest_run_service = ChatRestRunService()


def get_chat_rest_run_service() -> ChatRestRunService:
    return _chat_rest_run_service


__all__ = [
    "ChatRestAttachment",
    "ChatRestIdempotencyConflict",
    "ChatRestRequestInProgress",
    "ChatRestRunService",
    "chat_rest_request_fingerprint",
    "get_chat_rest_run_service",
    "validate_chat_rest_idempotency_key",
]
