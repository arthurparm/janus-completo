from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.routing import RouteDecision, RouteTarget
from app.services.code_hybrid_search_service import CodeHybridSearchService


class _FakeRepo:
    def __init__(self, db):
        self._db = db

    async def find_code_citations(self, tokens: list[str], limit: int = 10) -> list[dict]:
        assert tokens
        return [
            {
                "type": "Function",
                "name": "run",
                "file_path": "backend/app/main.py",
                "line": 42,
                "full_name": "backend/app/main.py::Engine.run",
                "relevance": 7,
            }
        ]

    async def find_related_concepts(self, concept: str, max_depth: int = 2, limit: int = 10) -> list[dict]:
        return [{"concept": "Qdrant", "relationship": "USES", "distance": 1}]


class _FakeMemory:
    async def arecall_filtered(self, **kwargs):
        return [
            SimpleNamespace(
                id="exp-1",
                content="Resumo vetorial de Engine.run no backend/app/main.py",
                score=0.81,
                metadata={"file_path": "backend/app/main.py", "origin": "self_study", "type": "code_summary"},
            )
        ]


@pytest.mark.asyncio
async def test_code_hybrid_search_merges_lexical_vector_and_graph():
    service = CodeHybridSearchService(
        graph_db_getter=lambda: _awaitable(object()),
        memory_db_getter=lambda: _awaitable(_FakeMemory()),
        knowledge_repo_factory=_FakeRepo,
    )

    result = await service.search(
        query="Engine run qdrant",
        limit=5,
        route_decision=RouteDecision(
            primary=RouteTarget.QDRANT,
            secondary=(RouteTarget.NEO4J,),
            reason="test",
            rule_id="test.hybrid",
        ),
    )

    assert result["metrics"]["lexical_count"] == 1
    assert result["metrics"]["vector_count"] == 1
    assert result["metrics"]["graph_count"] == 1
    assert result["citations"][0]["file_path"] == "backend/app/main.py"
    assert result["citations"][0]["source"] == "lexical"
    assert result["citations"][0]["sources"] == ["lexical", "vector"]
    assert "Resumo vetorial" in result["answer"]


@pytest.mark.asyncio
async def test_code_hybrid_search_skips_vector_when_route_disables_qdrant():
    service = CodeHybridSearchService(
        graph_db_getter=lambda: _awaitable(object()),
        memory_db_getter=lambda: _awaitable(_FakeMemory()),
        knowledge_repo_factory=_FakeRepo,
    )

    result = await service.search(
        query="Engine run",
        limit=5,
        route_decision=RouteDecision(
            primary=RouteTarget.NEO4J,
            secondary=tuple(),
            reason="test",
            rule_id="test.graph_only",
        ),
    )

    assert result["metrics"]["vector_count"] == 0
    assert all("vector" not in citation["sources"] for citation in result["citations"])


async def _awaitable(value):
    return value
