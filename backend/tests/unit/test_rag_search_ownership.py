from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.rag import rag_search
from app.core.security.actor_context import ActorContext, AuthMethod


def _request(actor_id: str | None):
    actor = None
    if actor_id is not None:
        actor = ActorContext.authenticated(
            actor_id=actor_id,
            roles=("USER",),
            auth_method=AuthMethod.OIDC,
            trace_id="trace-rag",
        )
    return SimpleNamespace(state=SimpleNamespace(actor_context=actor))


class _MemoryService:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def recall_filtered(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return [
            {
                "id": "memory-1",
                "content": "owned fact",
                "score": 0.9,
                "metadata": {"user_id": "42", "type": "episodic"},
            }
        ]


@pytest.mark.asyncio
async def test_rag_search_applies_authenticated_owner_filter():
    service = _MemoryService()

    response = await rag_search(
        request=_request("42"),
        query="owned fact",
        type=None,
        origin=None,
        doc_id=None,
        file_path=None,
        limit=5,
        min_score=None,
        service=service,  # type: ignore[arg-type]
    )

    assert response.answer == "owned fact"
    assert service.calls[0]["filters"]["user_id"] == "42"  # type: ignore[index]


@pytest.mark.asyncio
async def test_rag_search_rejects_anonymous_request_before_retrieval():
    service = _MemoryService()

    with pytest.raises(HTTPException) as exc_info:
        await rag_search(
            request=_request(None),
            query="anything",
            type=None,
            origin=None,
            doc_id=None,
            file_path=None,
            limit=5,
            min_score=None,
            service=service,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 401
    assert service.calls == []


@pytest.mark.asyncio
async def test_rag_search_reports_backend_failure_instead_of_empty_success():
    service = _MemoryService(error=RuntimeError("qdrant unavailable"))

    with pytest.raises(HTTPException) as exc_info:
        await rag_search(
            request=_request("42"),
            query="owned fact",
            type=None,
            origin=None,
            doc_id=None,
            file_path=None,
            limit=5,
            min_score=None,
            service=service,  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Vector retrieval is temporarily unavailable."
