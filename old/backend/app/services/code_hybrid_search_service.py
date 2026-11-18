from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import structlog

from app.core.memory.memory_core import get_memory_db
from app.core.routing import RouteDecision, RouteIntent, RouteTarget, get_knowledge_routing_policy
from app.db.graph import get_graph_db
from app.repositories.knowledge_repository import KnowledgeRepository

logger = structlog.get_logger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{2,}")
_STOP_TOKENS = {
    "a",
    "and",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "for",
    "na",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "que",
    "qual",
    "quais",
    "the",
    "um",
    "uma",
}
_SOURCE_PRIORITY = {"lexical": 0, "vector": 1, "graph": 2}
_RRF_K = 60
_RRF_WEIGHTS = {"lexical": 1.0, "vector": 0.9, "graph": 0.6}


def _question_tokens(query: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in _TOKEN_RE.findall(str(query or "").lower()):
        if token in _STOP_TOKENS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:24]


def _coerce_score(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _primary_source(sources: set[str]) -> str:
    if not sources:
        return "graph"
    return min(sources, key=lambda item: _SOURCE_PRIORITY.get(item, 99))


@dataclass
class _AggregateCandidate:
    key: str
    file_path: str | None = None
    line: int | None = None
    content: str = ""
    concept: str | None = None
    relationship: str | None = None
    source_set: set[str] | None = None
    source_scores: dict[str, float] | None = None
    raw_items: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.source_set is None:
            self.source_set = set()
        if self.source_scores is None:
            self.source_scores = {}
        if self.raw_items is None:
            self.raw_items = []

    def add(
        self,
        *,
        source: str,
        rrf_score: float,
        raw_item: dict[str, Any],
        preferred_content: str | None = None,
        file_path: str | None = None,
        line: int | None = None,
        concept: str | None = None,
        relationship: str | None = None,
    ) -> None:
        self.source_set.add(source)
        self.source_scores[source] = self.source_scores.get(source, 0.0) + float(rrf_score)
        self.raw_items.append(raw_item)
        if file_path and not self.file_path:
            self.file_path = file_path
        if line and not self.line:
            self.line = int(line)
        if concept and not self.concept:
            self.concept = concept
        if relationship and not self.relationship:
            self.relationship = relationship
        if preferred_content and (
            not self.content
            or source == "vector"
            or _SOURCE_PRIORITY.get(source, 99) < _SOURCE_PRIORITY.get(_primary_source(self.source_set), 99)
        ):
            self.content = preferred_content

    @property
    def source_count(self) -> int:
        return len(self.source_set)

    @property
    def fused_score(self) -> float:
        return sum(self.source_scores.values())

    @property
    def primary_source(self) -> str:
        return _primary_source(self.source_set)


class CodeHybridSearchService:
    def __init__(
        self,
        *,
        graph_db_getter: Callable[[], Awaitable[Any]] = get_graph_db,
        memory_db_getter: Callable[[], Awaitable[Any]] = get_memory_db,
        knowledge_repo_factory: type[KnowledgeRepository] = KnowledgeRepository,
    ) -> None:
        self._graph_db_getter = graph_db_getter
        self._memory_db_getter = memory_db_getter
        self._knowledge_repo_factory = knowledge_repo_factory

    async def search(
        self,
        *,
        query: str,
        limit: int = 5,
        min_score: float | None = None,
        user_id: str | None = None,
        route_decision: RouteDecision | None = None,
    ) -> dict[str, Any]:
        cleaned_query = str(query or "").strip()
        if not cleaned_query:
            empty_route = route_decision or get_knowledge_routing_policy().resolve(
                RouteIntent.RAG_HYBRID_SEARCH,
                user_id=user_id,
                include_graph=True,
                query=cleaned_query,
            )
            return {
                "answer": "",
                "citations": [],
                "items": [],
                "route": empty_route,
                "metrics": {"lexical_count": 0, "vector_count": 0, "graph_count": 0},
                "errors": {},
            }

        limit = max(1, int(limit or 5))
        candidate_limit = max(limit * 3, limit)
        resolved_route = route_decision or get_knowledge_routing_policy().resolve(
            RouteIntent.RAG_HYBRID_SEARCH,
            user_id=user_id,
            include_graph=True,
            query=cleaned_query,
        )
        route_targets = {resolved_route.primary, *resolved_route.secondary}
        vector_enabled = RouteTarget.QDRANT in route_targets
        graph_enabled = RouteTarget.NEO4J in route_targets
        tokens = _question_tokens(cleaned_query)

        repo: KnowledgeRepository | None = None
        if graph_enabled:
            graph_db = await self._graph_db_getter()
            if graph_db is not None:
                repo = self._knowledge_repo_factory(graph_db)

        lexical_rows: list[dict[str, Any]] = []
        graph_rows: list[dict[str, Any]] = []
        vector_rows: list[dict[str, Any]] = []
        errors: dict[str, str] = {}

        if repo is not None and tokens:
            try:
                lexical_rows = await repo.find_code_citations(tokens=tokens, limit=candidate_limit)
            except Exception as exc:
                errors["lexical"] = type(exc).__name__
                logger.warning("code_hybrid_search_lexical_failed", error=str(exc))

        if vector_enabled:
            try:
                memory_db = await self._memory_db_getter()
                recalled = await memory_db.arecall_filtered(
                    query=cleaned_query,
                    filters={
                        "origin": "self_study",
                        "strong_memory": True,
                        "source_kind": "code_file",
                        "content_kind": "code_summary",
                    },
                    limit=candidate_limit,
                    min_score=min_score,
                )
                for item in recalled or []:
                    metadata = item.metadata or {}
                    vector_rows.append(
                        {
                            "id": item.id,
                            "content": str(item.content or "").strip(),
                            "score": _coerce_score(getattr(item, "score", 0.0)),
                            "file_path": str(metadata.get("file_path") or "").strip() or None,
                            "origin": metadata.get("origin"),
                            "type": metadata.get("type"),
                            "summary_version": metadata.get("summary_version"),
                        }
                    )
            except Exception as exc:
                errors["vector"] = type(exc).__name__
                logger.warning("code_hybrid_search_vector_failed", error=str(exc))

        if repo is not None:
            try:
                graph_rows = await repo.find_related_concepts(
                    concept=cleaned_query,
                    max_depth=2,
                    limit=candidate_limit,
                )
            except Exception as exc:
                errors["graph"] = type(exc).__name__
                logger.warning("code_hybrid_search_graph_failed", error=str(exc))

        aggregates: dict[str, _AggregateCandidate] = {}
        self._merge_lexical_rows(aggregates, lexical_rows)
        self._merge_vector_rows(aggregates, vector_rows)
        self._merge_graph_rows(aggregates, graph_rows)

        items = sorted(
            aggregates.values(),
            key=lambda item: (-item.source_count, -item.fused_score, item.file_path or item.key),
        )[:limit]

        citations: list[dict[str, Any]] = []
        answer_parts: list[str] = []
        for item in items:
            primary_source = item.primary_source
            citation: dict[str, Any] = {
                "source": primary_source,
                "sources": sorted(item.source_set),
                "score": round(item.fused_score, 6),
            }
            if item.file_path:
                citation["file_path"] = item.file_path
            if item.line:
                citation["line"] = item.line
            if item.concept:
                citation["concept"] = item.concept
            if item.relationship:
                citation["relationship"] = item.relationship
            citations.append(citation)

            snippet = str(item.content or "").strip()
            if not snippet and item.file_path:
                location = item.file_path
                if item.line:
                    location = f"{location}:{item.line}"
                snippet = f"Evidência em {location}."
            elif not snippet and item.concept:
                snippet = f"Conceito relacionado: {item.concept} via {item.relationship or 'RELATES_TO'}."
            if snippet:
                answer_parts.append(snippet[:320])

        if not answer_parts:
            answer = "Nenhuma evidência de código foi encontrada para a consulta."
        else:
            answer = "\n\n".join(answer_parts)

        return {
            "answer": answer,
            "citations": citations,
            "items": [
                {
                    "file_path": item.file_path,
                    "line": item.line,
                    "content": item.content,
                    "score": item.fused_score,
                    "source": item.primary_source,
                    "sources": sorted(item.source_set),
                    "concept": item.concept,
                    "relationship": item.relationship,
                }
                for item in items
            ],
            "route": resolved_route,
            "metrics": {
                "lexical_count": len(lexical_rows),
                "vector_count": len(vector_rows),
                "graph_count": len(graph_rows),
            },
            "errors": errors,
        }

    def _merge_lexical_rows(
        self,
        aggregates: dict[str, _AggregateCandidate],
        rows: list[dict[str, Any]],
    ) -> None:
        for index, row in enumerate(rows, start=1):
            file_path = str(row.get("file_path") or "").strip() or None
            line = row.get("line")
            name = str(row.get("full_name") or row.get("name") or "").strip()
            key = file_path or f"lexical:{name}:{index}"
            location = file_path or name or "código"
            if line:
                snippet = f"{location}:{line} ({name or 'match lexical'})"
            else:
                snippet = f"{location} ({name or 'match lexical'})"
            candidate = aggregates.setdefault(key, _AggregateCandidate(key=key))
            candidate.add(
                source="lexical",
                rrf_score=_RRF_WEIGHTS["lexical"] / (_RRF_K + index),
                raw_item=row,
                preferred_content=snippet,
                file_path=file_path,
                line=int(line) if line else None,
            )

    def _merge_vector_rows(
        self,
        aggregates: dict[str, _AggregateCandidate],
        rows: list[dict[str, Any]],
    ) -> None:
        for index, row in enumerate(rows, start=1):
            file_path = str(row.get("file_path") or "").strip() or None
            key = file_path or f"vector:{row.get('id') or index}"
            snippet = str(row.get("content") or "").strip()
            candidate = aggregates.setdefault(key, _AggregateCandidate(key=key))
            candidate.add(
                source="vector",
                rrf_score=_RRF_WEIGHTS["vector"] / (_RRF_K + index),
                raw_item=row,
                preferred_content=snippet,
                file_path=file_path,
            )

    def _merge_graph_rows(
        self,
        aggregates: dict[str, _AggregateCandidate],
        rows: list[dict[str, Any]],
    ) -> None:
        for index, row in enumerate(rows, start=1):
            concept = str(row.get("concept") or "").strip() or "conceito"
            relationship = str(row.get("relationship") or "").strip() or "RELATES_TO"
            key = f"graph:{concept}:{relationship}"
            snippet = f"Conceito relacionado: {concept} via {relationship}"
            candidate = aggregates.setdefault(key, _AggregateCandidate(key=key))
            candidate.add(
                source="graph",
                rrf_score=_RRF_WEIGHTS["graph"] / (_RRF_K + index),
                raw_item=row,
                preferred_content=snippet,
                concept=concept,
                relationship=relationship,
            )


_code_hybrid_search_service: CodeHybridSearchService | None = None


def get_code_hybrid_search_service() -> CodeHybridSearchService:
    global _code_hybrid_search_service
    if _code_hybrid_search_service is None:
        _code_hybrid_search_service = CodeHybridSearchService()
    return _code_hybrid_search_service
