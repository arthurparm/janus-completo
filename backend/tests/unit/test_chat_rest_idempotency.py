from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.models.chat_rest_models import ChatRestRun
from app.repositories.chat_rest_repository import (
    ChatRestIdempotencyConflict,
    ChatRestRepository,
)
from app.services.chat_rest_run_service import (
    ChatRestRequestInProgress,
    ChatRestRunService,
    chat_rest_request_fingerprint,
    validate_chat_rest_idempotency_key,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def service() -> ChatRestRunService:
    engine = create_engine("sqlite:///:memory:")
    ChatRestRun.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    return ChatRestRunService(ChatRestRepository(session_factory=factory))


def test_rest_idempotency_executes_once_and_replays_completed_result(
    service: ChatRestRunService,
) -> None:
    fingerprint = chat_rest_request_fingerprint({"message": "Olá"})
    first = service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-0001",
        request_fingerprint=fingerprint,
    )

    with pytest.raises(ChatRestRequestInProgress):
        service.attach(
            owner_user_id="user-1",
            conversation_id="conv-1",
            request_id="request-0001",
            request_fingerprint=fingerprint,
        )

    service.complete(first, {"response": "ok", "conversation_id": "conv-1"})
    replay = service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-0001",
        request_fingerprint=fingerprint,
    )

    assert first.owns_execution is True
    assert replay.owns_execution is False
    assert replay.replay_result == {"response": "ok", "conversation_id": "conv-1"}


def test_rest_idempotency_rejects_same_key_with_different_payload(
    service: ChatRestRunService,
) -> None:
    service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-0002",
        request_fingerprint=chat_rest_request_fingerprint({"message": "A"}),
    )

    with pytest.raises(ChatRestIdempotencyConflict):
        service.attach(
            owner_user_id="user-1",
            conversation_id="conv-1",
            request_id="request-0002",
            request_fingerprint=chat_rest_request_fingerprint({"message": "B"}),
        )


def test_rest_idempotency_fault_injection_keeps_uncertain_crash_non_replayable(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    ChatRestRun.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    repository = ChatRestRepository(session_factory=factory)
    service = ChatRestRunService(repository)
    fingerprint = chat_rest_request_fingerprint({"message": "uncertain crash"})
    service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-crash-0001",
        request_fingerprint=fingerprint,
    )

    # Simulate process loss after execution ownership was claimed but before
    # the result was recorded. Even after the lease horizon, automatic replay
    # stays disabled so an uncertain LLM/tool execution cannot run twice.
    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
    monkeypatch.setattr(repository, "_utcnow", lambda: future)

    with pytest.raises(ChatRestRequestInProgress):
        service.attach(
            owner_user_id="user-1",
            conversation_id="conv-1",
            request_id="request-crash-0001",
            request_fingerprint=fingerprint,
        )


def test_rest_idempotency_cleanup_removes_only_expired_terminal_runs(
    monkeypatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    ChatRestRun.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    repository = ChatRestRepository(session_factory=factory)
    service = ChatRestRunService(repository)
    fingerprint = chat_rest_request_fingerprint({"message": "cleanup"})
    terminal = service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-cleanup-terminal",
        request_fingerprint=fingerprint,
    )
    service.complete(terminal, {"response": "ok"})
    service.attach(
        owner_user_id="user-1",
        conversation_id="conv-1",
        request_id="request-cleanup-running",
        request_fingerprint=fingerprint,
    )
    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=2)
    monkeypatch.setattr(repository, "_utcnow", lambda: future)

    assert service.cleanup_expired() == 1
    with pytest.raises(ChatRestRequestInProgress):
        service.attach(
            owner_user_id="user-1",
            conversation_id="conv-1",
            request_id="request-cleanup-running",
            request_fingerprint=fingerprint,
        )


@pytest.mark.parametrize("value", ["short", "contains spaces", "a" * 129])
def test_rest_idempotency_validates_client_key(value: str) -> None:
    with pytest.raises(ValueError):
        validate_chat_rest_idempotency_key(value)
