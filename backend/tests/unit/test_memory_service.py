from typing import Any, Dict, List, Optional

import pytest

from app.core.protocols import MemoryRepositoryProtocol
from app.models.schemas import Experience
from app.services.memory_service import MemoryService


class FakeMemoryRepository(MemoryRepositoryProtocol):
    def __init__(self):
        self.items: List[Experience] = []

    async def save_experience(self, experience: Any) -> None:
        # Armazena diretamente a experiência
        self.items.append(experience)

    async def search_experiences(self, query: str, limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        # Retorna itens cujo conteúdo contém o query
        results = []
        for exp in self.items:
            if query.lower() in exp.content.lower():
                results.append({
                    "id": exp.id,
                    "content": exp.content,
                    "metadata": exp.metadata,
                    "score": 0.9
                })
            if limit is not None and len(results) >= limit:
                break
        return results

    async def search_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        # Filtra por metadados simples: todos os pares devem estar presentes
        results = []
        for exp in self.items:
            # Query opcional
            if query and query.lower() not in exp.content.lower():
                continue
            # Filtros devem casar
            if all(exp.metadata.get(k) == v for k, v in filters.items()):
                results.append({
                    "id": exp.id,
                    "content": exp.content,
                    "metadata": exp.metadata,
                    "score": 0.8
                })
            if limit is not None and len(results) >= limit:
                break
        return results

    async def search_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        # Usa timestamps simulados em metadata["timestamp"]
        results = []
        for exp in self.items:
            ts = exp.metadata.get("timestamp")
            if ts is None:
                continue
            if start_ts_ms is not None and ts < start_ts_ms:
                continue
            if end_ts_ms is not None and ts > end_ts_ms:
                continue
            if query and query.lower() not in exp.content.lower():
                continue
            results.append({
                "id": exp.id,
                "content": exp.content,
                "metadata": exp.metadata,
                "score": 0.7
            })
            if limit is not None and len(results) >= limit:
                break
        return results

    async def search_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        # Filtra experiências com metadata["status"] == "failure"
        results = []
        for exp in self.items:
            if exp.metadata.get("status") == "failure":
                results.append({
                    "id": exp.id,
                    "content": exp.content,
                    "metadata": exp.metadata,
                    "score": 0.6
                })
            if limit is not None and len(results) >= limit:
                break
        return results

    async def search_recent_lessons(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        # Filtra experiências com metadata["type"] == "lesson"
        results = []
        for exp in self.items:
            if exp.metadata.get("type") == "lesson":
                results.append({
                    "id": exp.id,
                    "content": exp.content,
                    "metadata": exp.metadata,
                    "score": 0.65
                })
            if limit is not None and len(results) >= limit:
                break
        return results


@pytest.mark.asyncio
async def test_add_experience_delegates_to_repository():
    repo = FakeMemoryRepository()
    service = MemoryService(repo)

    exp = await service.add_experience(
        type="note",
        content="Aprendi asyncio ontem",
        metadata={"tags": ["python", "asyncio"], "timestamp": 1730000000000}
    )

    # O "General" deu a ordem ao "Coronel"?
    assert len(repo.items) == 1
    assert repo.items[0] is exp
    assert repo.items[0].content == "Aprendi asyncio ontem"


@pytest.mark.asyncio
async def test_recall_experiences_uses_repository_search():
    repo = FakeMemoryRepository()
    service = MemoryService(repo)

    # Prepara alguns dados
    await service.add_experience("note", "Dockerfile é simples", {"type": "lesson"})
    await service.add_experience("note", "Asyncio falhou na v7", {"status": "failure"})

    results = await service.recall_experiences("dockerfile")
    assert len(results) == 1
    assert "Dockerfile" in results[0]["content"].capitalize()


@pytest.mark.asyncio
async def test_recall_filtered_and_failures_and_lessons():
    repo = FakeMemoryRepository()
    service = MemoryService(repo)

    await service.add_experience("note", "Prompt v8 corrige asyncio", {"version": "v8", "type": "lesson"})
    await service.add_experience("note", "Prompt v7 falha com asyncio", {"version": "v7", "status": "failure"})

    filtered = await service.recall_filtered(query=None, filters={"version": "v8"})
    assert len(filtered) == 1
    assert filtered[0]["metadata"]["version"] == "v8"

    failures = await service.recall_recent_failures(limit=5)
    assert len(failures) == 1
    assert failures[0]["metadata"]["version"] == "v7"

    lessons = await service.recall_recent_lessons(limit=5)
    assert len(lessons) == 1
    assert lessons[0]["metadata"]["type"] == "lesson"
