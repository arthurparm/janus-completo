from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.planes.knowledge.adapters import ExperimentalQuantizedRetrievalAdapter, QdrantKnowledgeAdapter
from app.planes.knowledge.facade import KnowledgeFacade
from app.planes.knowledge.experimental_index import (
    ExperimentalIndexManager,
    ExperimentalIndexNotReadyError,
)


def _point(point_id: str, vector: list[float], payload: dict):
    return SimpleNamespace(id=point_id, vector=vector, payload=payload)


@pytest.mark.asyncio
async def test_build_index_dry_run_persists_report(monkeypatch, tmp_path):
    manager = ExperimentalIndexManager(root_dir=tmp_path)

    async def _fake_read_points(*, collection_name: str):
        assert collection_name == "global_docs"
        return [
            _point(
                "doc-1",
                [0.1, 0.2, 0.3],
                {"metadata": {"type": "doc_chunk", "doc_id": "d1", "timestamp": 10}},
            )
        ]

    monkeypatch.setattr(manager, "_read_points", _fake_read_points)

    result = await manager.build_index(domain="docs", dry_run=True)

    assert result.dry_run is True
    assert (tmp_path / "docs" / "v1" / "global" / "build_report.json").exists()


@pytest.mark.asyncio
async def test_build_index_and_search_round_trip(monkeypatch, tmp_path):
    manager = ExperimentalIndexManager(root_dir=tmp_path)

    async def _fake_read_points(*, collection_name: str):
        assert collection_name == "global_memory"
        return [
            _point(
                "mem-1",
                [0.2, 0.1, 0.0],
                {
                    "content": "calendar item",
                    "metadata": {"type": "calendar_event", "origin": "google", "timestamp": 11},
                },
            ),
            _point(
                "mem-2",
                [0.9, 0.8, 0.7],
                {
                    "content": "note item",
                    "metadata": {"type": "note_item", "origin": "notes", "timestamp": 12},
                },
            ),
        ]

    monkeypatch.setattr(manager, "_read_points", _fake_read_points)

    await manager.build_index(domain="memory", dry_run=False)
    results = manager.search(
        domain="memory",
        query_vector=[0.9, 0.8, 0.7],
        limit=2,
        filters={"memory_type": "note_item"},
    )

    assert results[0].id == "mem-2"
    assert results[0].score >= 0.5


def test_load_index_raises_when_missing(tmp_path):
    manager = ExperimentalIndexManager(root_dir=tmp_path)

    with pytest.raises(ExperimentalIndexNotReadyError):
        manager.load_index(domain="chat")


@pytest.mark.asyncio
async def test_experimental_backend_fails_clearly_when_index_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.planes.knowledge.facade.settings",
        SimpleNamespace(
            KNOWLEDGE_RETRIEVAL_BACKEND="experimental_quantized_retrieval",
            KNOWLEDGE_RETRIEVAL_SHADOW_MODE=False,
            KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX="-turboquant",
            KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED=True,
            KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION="v1",
            KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL=False,
            KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ=False,
            KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED=False,
        ),
    )
    facade = KnowledgeFacade(
        memory_service=SimpleNamespace(recall_filtered=None, index_interaction=None),
        knowledge_service=SimpleNamespace(),
        document_service=SimpleNamespace(),
        qdrant_adapter=QdrantKnowledgeAdapter(),
        experimental_adapter=ExperimentalQuantizedRetrievalAdapter(
            index_manager=ExperimentalIndexManager(root_dir=tmp_path)
        ),
        experimental_index_manager=ExperimentalIndexManager(root_dir=tmp_path),
    )

    with pytest.raises(ExperimentalIndexNotReadyError):
        await facade.search_documents(query="janus", user_id="u1", limit=3)
