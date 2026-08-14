from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.core.infrastructure.message_broker import MessageBroker
from app.core.workers import google_productivity_worker as worker


class _OfflineBroker:
    def __init__(self) -> None:
        self.publish = AsyncMock(return_value=False)


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_message_broker_reports_offline_delivery() -> None:
    broker = MessageBroker.__new__(MessageBroker)
    broker.connect = AsyncMock()
    broker._connection = None

    delivered = await broker.publish("janus.test", b"payload")

    assert delivered is False


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("publisher", "payload"),
    [
        (worker.publish_google_calendar_add_event, {"event": {}, "index": False}),
        (worker.publish_google_mail_send, {"message": {}, "index": False}),
    ],
)
async def test_productivity_publishers_do_not_report_offline_queue_as_success(
    monkeypatch: pytest.MonkeyPatch,
    publisher: object,
    payload: dict[str, object],
) -> None:
    broker = _OfflineBroker()
    audit = Mock()
    monkeypatch.setattr(worker, "get_broker", AsyncMock(return_value=broker))
    monkeypatch.setattr(worker, "record_audit_event_direct", audit)

    with pytest.raises(worker.ProductivityQueueUnavailableError, match="não foi enfileirado"):
        await publisher(user_id=7, **payload)  # type: ignore[operator]

    broker.publish.assert_awaited_once()
    audit.assert_not_called()


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_productivity_publisher_records_queue_only_after_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = _OfflineBroker()
    broker.publish.return_value = True
    audit = Mock()
    monkeypatch.setattr(worker, "get_broker", AsyncMock(return_value=broker))
    monkeypatch.setattr(worker, "record_audit_event_direct", audit)

    task_id = await worker.publish_google_mail_send(
        user_id=7,
        message={"to": "dest@example.com", "subject": "S", "body": "B"},
        index=False,
    )

    assert task_id
    broker.publish.assert_awaited_once()
    assert audit.call_args.args[0]["status"] == "queued"
