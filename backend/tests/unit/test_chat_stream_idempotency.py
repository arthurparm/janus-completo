import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pytest
from app.config import settings
from app.models.chat_stream_models import ChatStreamEvent, ChatStreamRun
from app.repositories.chat_stream_repository import (
    ChatStreamIdempotencyConflict,
    ChatStreamRepository,
)
from app.services.chat_stream_run_service import ChatStreamRunService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def stream_repository(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'chat-stream.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    ChatStreamRun.__table__.create(engine)
    ChatStreamEvent.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    repository = ChatStreamRepository(session_factory=factory)
    yield repository, factory
    engine.dispose()


def test_repository_concurrent_begin_converges_on_one_run(stream_repository):
    repository, _ = stream_repository

    def begin():
        return repository.begin_or_get(
            owner_user_id=7,
            session_id=11,
            request_id="request-concurrent-0001",
            request_fingerprint="a" * 64,
            retention_hours=24,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: begin(), range(2)))

    assert len({run.id for run, _ in results}) == 1
    assert sorted(created for _, created in results) == [False, True]


def test_repository_rejects_key_reuse_with_different_fingerprint(stream_repository):
    repository, _ = stream_repository
    repository.begin_or_get(
        owner_user_id=7,
        session_id=11,
        request_id="request-conflict-0001",
        request_fingerprint="a" * 64,
        retention_hours=24,
    )

    with pytest.raises(ChatStreamIdempotencyConflict):
        repository.begin_or_get(
            owner_user_id=7,
            session_id=11,
            request_id="request-conflict-0001",
            request_fingerprint="b" * 64,
            retention_hours=24,
        )


def test_repository_claim_event_cursor_and_owner_isolation(stream_repository):
    repository, _ = stream_repository
    run, _ = repository.begin_or_get(
        owner_user_id=7,
        session_id=11,
        request_id="request-events-00001",
        request_fingerprint="a" * 64,
        retention_hours=24,
    )

    assert repository.claim_pending(
        run_id=run.id,
        producer_token="producer-a",
        lease_seconds=30,
    )
    assert not repository.claim_pending(
        run_id=run.id,
        producer_token="producer-b",
        lease_seconds=30,
    )
    first = repository.append_event(
        run_id=run.id,
        producer_token="producer-a",
        payload="event: token\ndata: one\n\n",
        lease_seconds=30,
    )
    second = repository.append_event(
        run_id=run.id,
        producer_token="producer-a",
        payload="event: done\ndata: {}\n\n",
        lease_seconds=30,
    )
    assert (first.sequence, second.sequence) == (1, 2)
    assert repository.finish(
        run_id=run.id,
        producer_token="producer-a",
        status="completed",
    )
    assert [event.sequence for event in repository.list_events(
        run_id=run.id,
        owner_user_id=7,
        after_sequence=1,
    )] == [2]
    assert repository.list_events(
        run_id=run.id,
        owner_user_id=8,
        after_sequence=0,
    ) == []


def test_repository_stale_run_becomes_terminal_without_reclaim(stream_repository):
    repository, factory = stream_repository
    run, _ = repository.begin_or_get(
        owner_user_id=7,
        session_id=11,
        request_id="request-stale-000001",
        request_fingerprint="a" * 64,
        retention_hours=24,
    )
    assert repository.claim_pending(
        run_id=run.id,
        producer_token="producer-a",
        lease_seconds=30,
    )
    with factory() as session:
        row = session.query(ChatStreamRun).filter(ChatStreamRun.id == run.id).one()
        row.lease_until = datetime.utcnow() - timedelta(seconds=1)
        session.commit()

    assert repository.interrupt_stale_run(
        run_id=run.id,
        owner_user_id=7,
        error_payload="event: error\ndata: interrupted\n\n",
        error_code="CHAT_STREAM_INTERRUPTED",
    )
    state = repository.get_run(run_id=run.id, owner_user_id=7)
    assert state is not None
    assert state.status == "failed"
    assert state.error_code == "CHAT_STREAM_INTERRUPTED"
    assert not repository.claim_pending(
        run_id=run.id,
        producer_token="producer-b",
        lease_seconds=30,
    )


@pytest.mark.asyncio
async def test_two_attachments_share_one_execution_and_event_ledger(
    stream_repository,
    monkeypatch,
):
    repository, _ = stream_repository
    monkeypatch.setattr(settings, "CHAT_STREAM_EVENT_POLL_INTERVAL_MS", 10)
    monkeypatch.setattr(settings, "CHAT_STREAM_RUN_LEASE_SECONDS", 30)
    service = ChatStreamRunService(repository)
    effects = 0

    async def source():
        nonlocal effects
        effects += 1
        yield "event: start\n\n"
        await asyncio.sleep(0.05)
        yield 'event: token\ndata: {"text":"ok"}\n\n'
        yield "event: done\ndata: {}\n\n"

    async def attach():
        return await service.begin_or_attach(
            owner_user_id=7,
            session_id=11,
            request_id="request-attach-00001",
            request_fingerprint="a" * 64,
            producer_factory=source,
        )

    first, second = await asyncio.gather(attach(), attach())
    assert first.run.id == second.run.id
    assert sum((first.producer_started, second.producer_started)) == 1

    async def collect():
        return [
            event
            async for event in service.stream_events(
                run_id=first.run.id,
                owner_user_id=7,
            )
        ]

    left, right = await asyncio.gather(collect(), collect())
    assert effects == 1
    assert left == right
    assert [line for line in left if line.startswith("id:")] == left
    assert "event: done" in left[-1]


@pytest.mark.asyncio
async def test_disconnect_then_resume_uses_cursor_without_reexecution(
    stream_repository,
    monkeypatch,
):
    repository, _ = stream_repository
    monkeypatch.setattr(settings, "CHAT_STREAM_EVENT_POLL_INTERVAL_MS", 10)
    monkeypatch.setattr(settings, "CHAT_STREAM_RUN_LEASE_SECONDS", 30)
    service = ChatStreamRunService(repository)
    effects = 0

    async def source():
        nonlocal effects
        effects += 1
        yield "event: start\n\n"
        await asyncio.sleep(0.03)
        yield 'event: token\ndata: {"text":"one"}\n\n'
        await asyncio.sleep(0.03)
        yield 'event: token\ndata: {"text":"two"}\n\n'
        yield "event: done\ndata: {}\n\n"

    first = await service.begin_or_attach(
        owner_user_id=7,
        session_id=11,
        request_id="request-resume-00001",
        request_fingerprint="a" * 64,
        producer_factory=source,
    )
    subscriber = service.stream_events(
        run_id=first.run.id,
        owner_user_id=7,
    )
    first_event = await anext(subscriber)
    await subscriber.aclose()
    assert first_event.startswith("id: 1")

    await asyncio.sleep(0.15)
    retry = await service.begin_or_attach(
        owner_user_id=7,
        session_id=11,
        request_id="request-resume-00001",
        request_fingerprint="a" * 64,
        producer_factory=source,
    )
    resumed = [
        event
        async for event in service.stream_events(
            run_id=retry.run.id,
            owner_user_id=7,
            after_sequence=1,
        )
    ]

    assert effects == 1
    assert resumed[0].startswith("id: 2")
    assert all(not event.startswith("id: 1") for event in resumed)
    assert "event: done" in resumed[-1]
