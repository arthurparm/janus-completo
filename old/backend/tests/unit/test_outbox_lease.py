from datetime import datetime, timedelta

import pytest
from app.models.outbox_models import OutboxEvent
from app.repositories import outbox_repository as repository_module
from app.repositories.outbox_repository import OutboxRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def outbox(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    OutboxEvent.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(repository_module.db, "get_session_direct", sessions)
    return OutboxRepository(), sessions


def test_processing_event_is_reclaimed_only_after_lease_expiry(outbox):
    repo, sessions = outbox
    event_id = repo.enqueue(event_type="document_ingestion", payload_json={"id": 7})

    first = repo.claim_pending(worker_id="worker-a", lease_seconds=60)

    assert len(first) == 1
    assert first[0].id == event_id
    assert first[0].message_id
    assert repo.claim_pending(worker_id="worker-b", lease_seconds=60) == []

    with sessions() as session:
        row = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).one()
        row.lease_until = datetime.utcnow() - timedelta(seconds=1)
        session.commit()

    reclaimed = repo.claim_pending(worker_id="worker-b", lease_seconds=60)

    assert len(reclaimed) == 1
    assert reclaimed[0].claim_token != first[0].claim_token
    assert repo.mark_sent(event_id, claim_token=first[0].claim_token) is False
    assert repo.mark_sent(event_id, claim_token=reclaimed[0].claim_token) is True


def test_retry_requires_current_claim_and_releases_lease(outbox):
    repo, sessions = outbox
    event_id = repo.enqueue(event_type="knowledge_consolidation", payload_json={"id": 9})
    claimed = repo.claim_pending(worker_id="worker-a", lease_seconds=60)[0]

    assert repo.mark_retry(event_id, claim_token="stale-token", error="boom") == "stale"
    assert repo.mark_retry(event_id, claim_token=claimed.claim_token, error="boom") == "retry"

    with sessions() as session:
        row = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).one()
        assert row.status == "retry"
        assert row.attempts == 1
        assert row.claimed_by is None
        assert row.claim_token is None
        assert row.claimed_at is None
        assert row.lease_until is None
