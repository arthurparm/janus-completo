from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.models.chat_study_models import ChatStudyRun
from app.repositories.chat_study_repository import (
    ChatStudyRepository,
    ChatStudyTransitionConflict,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def repository() -> ChatStudyRepository:
    engine = create_engine("sqlite:///:memory:")
    ChatStudyRun.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    return ChatStudyRepository(session_factory=factory)


def test_study_state_machine_persists_idempotent_lifecycle(
    repository: ChatStudyRepository,
) -> None:
    pending = repository.create_pending(
        job_id="job-1",
        owner_user_id="user-1",
        conversation_id="conv-1",
        message_id="message-1",
        question="Onde está a documentação?",
        request_fingerprint="fingerprint-1",
        placeholder_message="Estudando",
    )
    duplicate = repository.create_pending(
        job_id="ignored-id",
        owner_user_id="user-1",
        conversation_id="conv-1",
        message_id="message-1",
        question="Onde está a documentação?",
        request_fingerprint="fingerprint-1",
        placeholder_message="Estudando",
    )

    assert pending.status == "pending"
    assert duplicate.job_id == pending.job_id

    running = repository.transition(
        job_id=pending.job_id,
        from_states={"pending"},
        to_state="running",
        progress=25,
    )
    completed = repository.transition(
        job_id=pending.job_id,
        from_states={"running"},
        to_state="completed",
        progress=100,
        final_response={"response": "Concluído", "citations": []},
    )
    repeated = repository.transition(
        job_id=pending.job_id,
        from_states={"running"},
        to_state="completed",
        progress=100,
    )

    assert running.version == 2
    assert completed.status == "completed"
    assert completed.final_response == {"response": "Concluído", "citations": []}
    assert repeated.version == completed.version


def test_study_state_machine_rejects_invalid_terminal_transition(
    repository: ChatStudyRepository,
) -> None:
    repository.create_pending(
        job_id="job-2",
        owner_user_id="user-1",
        conversation_id="conv-1",
        message_id="message-2",
        question="Pergunta",
        request_fingerprint="fingerprint-2",
        placeholder_message="Estudando",
    )

    with pytest.raises(ChatStudyTransitionConflict):
        repository.transition(
            job_id="job-2",
            from_states={"running"},
            to_state="completed",
        )


def test_expired_study_lease_can_be_reclaimed_without_concurrent_owner(
    repository: ChatStudyRepository,
    monkeypatch,
) -> None:
    repository.create_pending(
        job_id="job-lease",
        owner_user_id="user-1",
        conversation_id="conv-1",
        message_id="message-lease",
        question="Pergunta",
        request_fingerprint="fingerprint-lease",
        placeholder_message="Estudando",
    )
    first = repository.claim(
        job_id="job-lease",
        worker_token="worker-1",
        lease_seconds=30,
    )

    assert first is not None
    assert first.worker_token == "worker-1"
    assert repository.claim(
        job_id="job-lease",
        worker_token="worker-2",
        lease_seconds=30,
    ) is None

    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=1)
    monkeypatch.setattr(repository, "_utcnow", lambda: future)
    reclaimed = repository.claim(
        job_id="job-lease",
        worker_token="worker-2",
        lease_seconds=30,
    )

    assert reclaimed is not None
    assert reclaimed.worker_token == "worker-2"
    with pytest.raises(ChatStudyTransitionConflict):
        repository.transition(
            job_id="job-lease",
            from_states={"running"},
            to_state="completed",
            worker_token="worker-1",
        )
