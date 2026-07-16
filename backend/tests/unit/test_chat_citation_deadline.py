import asyncio

import pytest
from app.api.v1.endpoints.chat import chat_message


@pytest.mark.asyncio
async def test_citation_deadline_cancels_collection_coroutine(monkeypatch):
    cancelled = asyncio.Event()

    async def _blocking_collection(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(chat_message, "collect_chat_citations", _blocking_collection)
    monkeypatch.setattr(chat_message, "CITATION_COLLECTION_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(asyncio.TimeoutError):
        await chat_message._collect_chat_citations_with_deadline(
            message="arquivo",
            conversation_id="conv-1",
            memory=object(),
            limit=5,
        )

    await asyncio.wait_for(cancelled.wait(), timeout=0.1)
